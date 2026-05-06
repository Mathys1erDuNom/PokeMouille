import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
from discord.ext import commands
import discord

from new_db import get_new_captures, add_xp, evolve_pokemon

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur  = conn.cursor()

# ──────────────────────────────────────────────
# TABLE
# ──────────────────────────────────────────────

cur.execute("""
CREATE TABLE IF NOT EXISTS chenil (
    user_id      TEXT PRIMARY KEY,
    pokemon_name TEXT NOT NULL
);
""")
conn.commit()


# ──────────────────────────────────────────────
# FONCTIONS INTERNES
# ──────────────────────────────────────────────

def get_chenil_pokemon(user_id: str) -> str | None:
    """Retourne le nom du Pokémon dans le chenil, ou None s'il est vide."""
    cur.execute("SELECT pokemon_name FROM chenil WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None


def set_chenil_pokemon(user_id: str, pokemon_name: str):
    """Place un Pokémon dans le chenil (upsert)."""
    cur.execute("""
        INSERT INTO chenil (user_id, pokemon_name)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET pokemon_name = EXCLUDED.pokemon_name
    """, (user_id, pokemon_name))
    conn.commit()


def remove_chenil_pokemon(user_id: str):
    """Retire le Pokémon du chenil."""
    cur.execute("DELETE FROM chenil WHERE user_id = %s", (user_id,))
    conn.commit()


# ──────────────────────────────────────────────
# FONCTION APPELÉE PAR LA BOUCLE PRINCIPALE
# ──────────────────────────────────────────────

async def tick_chenil_xp(members_in_vc: list, xp_counters: dict, xp_amount: int = 20, threshold: int = 20):
    """
    À appeler chaque minute depuis auto_event_loop.

    - members_in_vc : liste des discord.Member présents dans le vocal (sans bots)
    - xp_counters   : dict { user_id (int): nb_checks (int) } — modifié en place
    - xp_amount     : XP à donner quand le seuil est atteint
    - threshold     : nombre de checks avant de donner l'XP (1 check = 1 min)
    """
    

    ids_presents = {m.id for m in members_in_vc}

    # Retire les utilisateurs qui ont quitté
    for uid in list(xp_counters.keys()):
        if uid not in ids_presents:
            print(f"[CHENIL] {uid} a quitté le vocal — retiré du compteur.")
            del xp_counters[uid]

    # Ajoute les nouveaux ou incrémente les existants
    for member in members_in_vc:
        xp_counters[member.id] = xp_counters.get(member.id, 0) + 1
        print(f"[CHENIL] {member.display_name} — checks: {xp_counters[member.id]}/{threshold}")

    # Vérifie si quelqu'un atteint le seuil
    for uid, checks in list(xp_counters.items()):
        if checks < threshold:
            continue

        xp_counters[uid] = 0  # reset avant de donner l'XP

        pokemon_name = get_chenil_pokemon(str(uid))
        if not pokemon_name:
            print(f"[CHENIL] {uid} aurait pu gagner {xp_amount} XP mais n'a pas de Pokémon dans le chenil.")
            continue

        captures = get_new_captures(str(uid))
        pokemon  = next((p for p in captures if p["name"].lower() == pokemon_name.lower()), None)

        if not pokemon:
            print(f"[CHENIL] Pokémon '{pokemon_name}' de {uid} introuvable dans new_captures.")
            continue

        can_evolve = add_xp(str(uid), pokemon["name"], xp_amount)
        print(f"[CHENIL] +{xp_amount} XP pour {pokemon['name']} de {uid}.")

        if can_evolve:
            result = evolve_pokemon(str(uid), pokemon)
            if result["success"]:
                print(f"[CHENIL] {pokemon['name']} de {uid} a évolué en {result['evo_name']} !")
                set_chenil_pokemon(str(uid), result["evo_name"])
            else:
                print(f"[CHENIL] Évolution impossible : {result['reason']}")


# ──────────────────────────────────────────────
# COMMANDES DISCORD
# ──────────────────────────────────────────────

def setup_chenil(bot):

    @bot.command(name="chenil")
    async def chenil_cmd(ctx, pokemon_name: str):
        """!chenil <nom_pokemon> — Place un Pokémon dans le chenil (1 seul à la fois)."""
    

        uid      = str(ctx.author.id)
        captures = get_new_captures(uid)
        pokemon  = next((p for p in captures if p["name"].lower() == pokemon_name.lower()), None)

        if not pokemon:
            await ctx.send(f"❌ **{pokemon_name}** introuvable dans ta collection.")
            return

        current = get_chenil_pokemon(uid)
        if current:
            await ctx.send(
                f"⚠️ Tu as déjà **{current}** dans le chenil. "
                f"Utilise `!retirer_chenil` avant d'en mettre un autre."
            )
            return

        set_chenil_pokemon(uid, pokemon["name"])
        await ctx.send(
            f"🏠 **{pokemon['name']}** a été placé dans le chenil ! "
            f"Il gagnera de l'XP tant que tu seras dans le salon vocal."
        )

    @bot.command(name="retirer_chenil")
    async def retirer_chenil_cmd(ctx):
        """!retirer_chenil — Retire votre Pokémon du chenil."""
        uid     = str(ctx.author.id)
        current = get_chenil_pokemon(uid)

        if not current:
            await ctx.send("❌ Tu n'as pas de Pokémon dans le chenil.")
            return

        remove_chenil_pokemon(uid)
        await ctx.send(f"✅ **{current}** a été retiré du chenil.")

    @bot.command(name="add_chenil_xp")
    @commands.has_permissions(administrator=True)
    async def add_chenil_xp_cmd(ctx, member: discord.Member, xp: int):
        """!add_chenil_xp @utilisateur <xp> — (Admin) Ajoute manuellement de l'XP au chenil."""
     

        uid          = str(member.id)
        pokemon_name = get_chenil_pokemon(uid)

        if not pokemon_name:
            await ctx.send(f"❌ {member.mention} n'a pas de Pokémon dans le chenil.")
            return

        captures = get_new_captures(uid)
        pokemon  = next((p for p in captures if p["name"].lower() == pokemon_name.lower()), None)

        if not pokemon:
            await ctx.send(f"❌ Pokémon **{pokemon_name}** introuvable dans new_captures.")
            return

        can_evolve = add_xp(uid, pokemon["name"], xp)

        if not can_evolve:
            updated    = next((p for p in get_new_captures(uid) if p["name"] == pokemon["name"]), None)
            current_xp = updated["current_xp"] if updated else "?"
            xp_evo     = updated["xp_evo"]     if updated else "?"
            await ctx.send(
                f"✅ **+{xp} XP** ajouté à **{pokemon['name']}** de {member.mention} !\n"
                f"📊 XP actuel : `{current_xp} / {xp_evo}`"
            )
            return

        result = evolve_pokemon(uid, pokemon)
        if result["success"]:
            set_chenil_pokemon(uid, result["evo_name"])
            await ctx.send(
                f"🎉 **{pokemon['name']}** de {member.mention} a évolué en **{result['evo_name']}** !\n"
                f"✨ IV hérités **+4** sur toutes les stats."
            )
        else:
            await ctx.send(
                f"✅ **+{xp} XP** ajouté à **{pokemon['name']}** de {member.mention}.\n"
                f"⚠️ Évolution impossible : {result['reason']}"
            )