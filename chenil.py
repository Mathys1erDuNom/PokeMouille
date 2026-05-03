"""
chenil.py
─────────
Système de chenil pour bot Discord Pokémon.

Commandes :
  !chenil <nom_pokemon>   → Dépose un Pokémon au chenil
  !retirer_chenil         → Retire le Pokémon du chenil
  !voir_chenil            → Affiche le Pokémon actuellement au chenil

Fonctionnement :
  - 1 seul Pokémon au chenil à la fois par utilisateur
  - Le Pokémon gagne 10 XP pour chaque heure passée en vocal
  - L'XP est calculé en temps réel selon le temps vocal accumulé
  - Si le seuil d'évolution est atteint, l'évolution est déclenchée automatiquement
"""

import os
import time
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — modifie ces valeurs pour ajuster le système
# ──────────────────────────────────────────────────────────────────────────────

SECONDES_PAR_TRANCHE = 60   # Temps vocal (en secondes) pour gagner de l'XP (3600 = 1h)
XP_PAR_TRANCHE       = 100     # XP gagné à chaque tranche complète
TICK_MINUTES         = 1      # Fréquence (en minutes) de la tâche de fond

# ──────────────────────────────────────────────────────────────────────────────

# ── Import des fonctions du bot principal ─────────────────────────────────────
from new_db import (
    get_new_captures,
    add_xp,
    evolve_pokemon,
)

# ── Connexion base de données ─────────────────────────────────────────────────
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# ── Création de la table chenil ───────────────────────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS chenil (
    user_id         TEXT PRIMARY KEY,
    pokemon_name    TEXT NOT NULL,
    vocal_seconds   INTEGER DEFAULT 0
);
""")
conn.commit()


# ──────────────────────────────────────────────────────────────────────────────
# FONCTIONS BASE DE DONNÉES
# ──────────────────────────────────────────────────────────────────────────────

def get_chenil(user_id):
    """Retourne le Pokémon au chenil pour un utilisateur, ou None."""
    cur.execute("""
        SELECT pokemon_name, vocal_seconds FROM chenil
        WHERE user_id = %s
    """, (str(user_id),))
    row = cur.fetchone()
    if row:
        return {"pokemon_name": row[0], "vocal_seconds": row[1]}
    return None


def set_chenil(user_id, pokemon_name):
    """Dépose un Pokémon au chenil (remplace si déjà un)."""
    cur.execute("""
        INSERT INTO chenil (user_id, pokemon_name, vocal_seconds)
        VALUES (%s, %s, 0)
        ON CONFLICT (user_id) DO UPDATE
            SET pokemon_name = EXCLUDED.pokemon_name,
                vocal_seconds = 0
    """, (str(user_id), pokemon_name))
    conn.commit()


def remove_chenil(user_id):
    """Retire le Pokémon du chenil."""
    cur.execute("DELETE FROM chenil WHERE user_id = %s", (str(user_id),))
    conn.commit()


def add_vocal_seconds(user_id, seconds):
    """
    Ajoute des secondes vocales au compteur du chenil.
    Calcule combien d'heures complètes ont été accumulées depuis le dernier don d'XP,
    donne 10 XP par heure complète et conserve le reste.

    Retourne le nombre d'heures complètes écoulées (peut être 0).
    """
    entry = get_chenil(user_id)
    if not entry:
        return 0

    new_seconds    = entry["vocal_seconds"] + seconds
    full_hours     = new_seconds // SECONDES_PAR_TRANCHE
    remainder      = new_seconds % SECONDES_PAR_TRANCHE

    # Sauvegarde uniquement le reste (les heures complètes sont consommées)
    cur.execute("""
        UPDATE chenil SET vocal_seconds = %s
        WHERE user_id = %s
    """, (remainder, str(user_id)))
    conn.commit()

    return int(full_hours)


# ──────────────────────────────────────────────────────────────────────────────
# SUIVI VOCAL EN TEMPS RÉEL
# ──────────────────────────────────────────────────────────────────────────────

# Dict en mémoire : user_id (int) → timestamp d'entrée en vocal
_vocal_start: dict[int, float] = {}


def setup_chenil(bot):

    # ── Tâche de fond : vérifie toutes les 5 min les membres déjà en vocal ──
    @tasks.loop(minutes=TICK_MINUTES)
    async def tick_vocal():
        """
        Toutes les 5 minutes, ajoute 300 secondes aux membres actuellement
        en vocal et qui ont un Pokémon au chenil.
        """
        for guild in bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    entry = get_chenil(member.id)
                    if not entry:
                        continue

                    hours = add_vocal_seconds(member.id, TICK_MINUTES * 60)
                    if hours > 0:
                        xp_gained  = hours * XP_PAR_TRANCHE
                        pokemon    = next(
                            (p for p in get_new_captures(str(member.id))
                             if p["name"].lower() == entry["pokemon_name"].lower()),
                            None
                        )
                        if not pokemon:
                            continue

                        can_evolve = add_xp(str(member.id), pokemon["name"], xp_gained)

                        # Notifie le membre en DM
                        try:
                            msg = (
                                f"🐾 **{pokemon['name']}** au chenil a gagné "
                                f"**+{xp_gained} XP** grâce à ton temps en vocal !"
                            )
                            if can_evolve:
                                result = evolve_pokemon(str(member.id), pokemon)
                                if result["success"]:
                                    msg += (
                                        f"\n🎉 Il a évolué en **{result['evo_name']}** ! "
                                        f"Il a été retiré du chenil automatiquement."
                                    )
                                    remove_chenil(member.id)
                            await member.send(msg)
                        except discord.Forbidden:
                            pass  # DM désactivés

    # ── Événement : entrée en vocal ──────────────────────────────────────────
    @bot.event
    async def on_voice_state_update(member, before, after):
        if member.bot:
            return

        # Entrée dans un salon vocal
        if before.channel is None and after.channel is not None:
            _vocal_start[member.id] = time.time()

        # Sortie d'un salon vocal
        elif before.channel is not None and after.channel is None:
            start = _vocal_start.pop(member.id, None)
            if start is None:
                return

            entry = get_chenil(member.id)
            if not entry:
                return

            elapsed_seconds = int(time.time() - start)
            hours = add_vocal_seconds(member.id, elapsed_seconds)

            if hours > 0:
                xp_gained = hours * XP_PAR_TRANCHE
                pokemon   = next(
                    (p for p in get_new_captures(str(member.id))
                     if p["name"].lower() == entry["pokemon_name"].lower()),
                    None
                )
                if not pokemon:
                    return

                can_evolve = add_xp(str(member.id), pokemon["name"], xp_gained)

                try:
                    msg = (
                        f"🐾 **{pokemon['name']}** au chenil a gagné "
                        f"**+{xp_gained} XP** grâce à ton temps en vocal !"
                    )
                    if can_evolve:
                        result = evolve_pokemon(str(member.id), pokemon)
                        if result["success"]:
                            msg += (
                                f"\n🎉 Il a évolué en **{result['evo_name']}** ! "
                                f"Il a été retiré du chenil automatiquement."
                            )
                            remove_chenil(member.id)
                    await member.send(msg)
                except discord.Forbidden:
                    pass

    # ── Commande : déposer au chenil ─────────────────────────────────────────
    @bot.command(name="chenil")
    async def chenil_cmd(ctx, *, pokemon_name: str = None):
        """
        !chenil <nom_pokemon>
        Dépose un Pokémon au chenil. Il gagnera 10 XP par heure passée en vocal.
        """
        if pokemon_name is None:
            await ctx.send(
                "❌ Précise le nom du Pokémon.\n"
                "Usage : `!chenil <nom_pokemon>`"
            )
            return

        user_id  = str(ctx.author.id)
        captures = get_new_captures(user_id)
        pokemon  = next(
            (p for p in captures if p["name"].lower() == pokemon_name.lower()),
            None
        )

        if not pokemon:
            await ctx.send(
                f"❌ Tu ne possèdes pas de **{pokemon_name}**."
            )
            return

        # Vérifie si un Pokémon est déjà au chenil
        existing = get_chenil(user_id)
        if existing:
            await ctx.send(
                f"⚠️ **{existing['pokemon_name']}** est déjà au chenil.\n"
                f"Utilise `!retirer_chenil` pour le récupérer d'abord."
            )
            return

        set_chenil(user_id, pokemon["name"])

        xp_evo = pokemon.get("xp_evo", 0)
        seuil  = f"`{pokemon.get('current_xp', 0)} / {xp_evo} XP`" if xp_evo > 0 else "pas d'évolution"

        await ctx.send(
            f"🏠 **{pokemon['name']}** a été déposé au chenil !\n"
            f"⚡ Il gagnera **{XP_PAR_TRANCHE} XP** toutes les **{SECONDES_PAR_TRANCHE // 3600}h** de vocal.\n"
            f"📊 XP actuel : {seuil}"
        )

    # ── Commande : retirer du chenil ─────────────────────────────────────────
    @bot.command(name="retirer_chenil")
    async def retirer_chenil_cmd(ctx):
        """
        !retirer_chenil
        Retire le Pokémon actuellement au chenil.
        """
        user_id = str(ctx.author.id)
        entry   = get_chenil(user_id)

        if not entry:
            await ctx.send("❌ Tu n'as aucun Pokémon au chenil.")
            return

        remove_chenil(user_id)

        # Récupère l'XP à jour pour l'affichage
        pokemon = next(
            (p for p in get_new_captures(user_id)
             if p["name"].lower() == entry["pokemon_name"].lower()),
            None
        )
        xp_info = ""
        if pokemon:
            xp_info = f"\n📊 XP actuel : `{pokemon['current_xp']} / {pokemon['xp_evo']}`"

        await ctx.send(
            f"✅ **{entry['pokemon_name']}** a été retiré du chenil.{xp_info}"
        )

    # ── Commande : voir le chenil ─────────────────────────────────────────────
    @bot.command(name="voir_chenil")
    async def voir_chenil_cmd(ctx):
        """
        !voir_chenil
        Affiche le Pokémon actuellement au chenil et son XP.
        """
        user_id = str(ctx.author.id)
        entry   = get_chenil(user_id)

        if not entry:
            await ctx.send("🏠 Ton chenil est vide. Utilise `!chenil <nom>` pour y déposer un Pokémon.")
            return

        pokemon = next(
            (p for p in get_new_captures(user_id)
             if p["name"].lower() == entry["pokemon_name"].lower()),
            None
        )

        minutes_restantes = entry["vocal_seconds"] // 60
        minutes_par_tranche = SECONDES_PAR_TRANCHE // 60
        heures_restantes = ""
        if entry["vocal_seconds"] > 0:
            heures_restantes = f"\n⏱️ Temps vocal en cours : `{minutes_restantes} min / {minutes_par_tranche} min`"

        if pokemon:
            xp_evo = pokemon.get("xp_evo", 0)
            seuil  = f"`{pokemon['current_xp']} / {xp_evo} XP`" if xp_evo > 0 else "pas d'évolution"
            await ctx.send(
                f"🏠 Au chenil : **{pokemon['name']}**\n"
                f"📊 XP : {seuil}{heures_restantes}\n"
                f"⚡ Gain : **{XP_PAR_TRANCHE} XP** toutes les **{SECONDES_PAR_TRANCHE // 3600}h** de vocal"
            )
        else:
            await ctx.send(
                f"🏠 Au chenil : **{entry['pokemon_name']}**\n"
                f"⚠️ Pokémon introuvable dans ta collection.{heures_restantes}"
            )

    # Démarre la tâche de fond
    tick_vocal.start()