import asyncio
import os
import json
import random
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

script_dir = os.path.dirname(os.path.abspath(__file__))

# ──────────────────────────────────────────────
# TABLE
# ──────────────────────────────────────────────

cur.execute("""
CREATE TABLE IF NOT EXISTS chenil (
    user_id      TEXT PRIMARY KEY,
    pokemon_name TEXT NOT NULL,
    is_egg       BOOLEAN DEFAULT FALSE,
    egg_xp       INTEGER DEFAULT 0,
    egg_xp_evo   INTEGER DEFAULT 400
);
""")

# Ajout des colonnes si elles n'existent pas encore (migration douce)
for col, definition in [
    ("is_egg",     "BOOLEAN DEFAULT FALSE"),
    ("egg_xp",     "INTEGER DEFAULT 0"),
    ("egg_xp_evo", "INTEGER DEFAULT 400"),
]:
    try:
        cur.execute(f"ALTER TABLE chenil ADD COLUMN IF NOT EXISTS {col} {definition};")
        conn.commit()
    except Exception:
        conn.rollback()


# ──────────────────────────────────────────────
# FONCTIONS INTERNES
# ──────────────────────────────────────────────

def get_chenil_pokemon(user_id: str) -> dict | None:
    """Retourne un dict avec toutes les infos du chenil, ou None s'il est vide."""
    cur.execute(
        "SELECT pokemon_name, is_egg, egg_xp, egg_xp_evo FROM chenil WHERE user_id = %s",
        (user_id,)
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "name":       row[0],
        "is_egg":     row[1],
        "egg_xp":     row[2],
        "egg_xp_evo": row[3],
    }


def set_chenil_pokemon(user_id: str, pokemon_name: str, is_egg: bool = False, egg_xp_evo: int = 400):
    """Place un Pokémon ou un œuf dans le chenil (upsert)."""
    cur.execute("""
        INSERT INTO chenil (user_id, pokemon_name, is_egg, egg_xp, egg_xp_evo)
        VALUES (%s, %s, %s, 0, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            pokemon_name = EXCLUDED.pokemon_name,
            is_egg       = EXCLUDED.is_egg,
            egg_xp       = 0,
            egg_xp_evo   = EXCLUDED.egg_xp_evo
    """, (user_id, pokemon_name, is_egg, egg_xp_evo))
    conn.commit()


def remove_chenil_pokemon(user_id: str):
    """Retire le Pokémon ou l'œuf du chenil."""
    cur.execute("DELETE FROM chenil WHERE user_id = %s", (user_id,))
    conn.commit()


def add_egg_xp(user_id: str, amount: int) -> bool:
    """
    Ajoute de l'XP à l'œuf en chenil.
    Retourne True si l'œuf est prêt à éclore (egg_xp >= egg_xp_evo).
    """
    cur.execute(
        "UPDATE chenil SET egg_xp = egg_xp + %s WHERE user_id = %s",
        (amount, user_id)
    )
    conn.commit()
    cur.execute(
        "SELECT egg_xp, egg_xp_evo FROM chenil WHERE user_id = %s",
        (user_id,)
    )
    row = cur.fetchone()
    return bool(row and row[0] >= row[1])


def get_random_egg_pokemon() -> str | None:
    """
    Tire aléatoirement un Pokémon dans /json/marche_noir/oeuf.json.
    Retourne le nom du Pokémon, ou None si le fichier est introuvable.
    """
    oeuf_json_path = os.path.join(script_dir, "json", "marche_noir", "oeuf.json")
    try:
        with open(oeuf_json_path, "r", encoding="utf-8") as f:
            pool = json.load(f)
        if not pool:
            print("[CHENIL] oeuf.json est vide.")
            return None
        chosen = random.choice(pool)
        # Le JSON peut contenir "name" ou "pokemon_name"
        return chosen.get("name") or chosen.get("pokemon_name")
    except Exception as e:
        print(f"[CHENIL] Erreur lecture oeuf.json : {e}")
        return None


# ──────────────────────────────────────────────
# GLOBALS (injectés par setup_chenil)
# ──────────────────────────────────────────────

_bot             = None
_text_channel_id = None


# ──────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ──────────────────────────────────────────────

async def tick_chenil_xp(
    members_in_vc: list,
    xp_counters:   dict,
    xp_amount:     int = 10,
    threshold:     int = 30,
):
    """
    À appeler chaque minute depuis auto_event_loop.

    - members_in_vc : liste des discord.Member présents dans le vocal (sans bots)
    - xp_counters   : dict { user_id (int): nb_checks (int) } — modifié en place
    - xp_amount     : XP à donner quand le seuil est atteint
    - threshold     : nombre de checks avant de donner l'XP (1 check = 1 min)
    """
    channel = _bot.get_channel(_text_channel_id)
    ids_presents = {m.id for m in members_in_vc}

    # Retire les utilisateurs qui ont quitté le vocal
    for uid in list(xp_counters.keys()):
        if uid not in ids_presents:
            print(f"[CHENIL] {uid} a quitté le vocal — retiré du compteur.")
            del xp_counters[uid]

    # Incrémente les compteurs
    for member in members_in_vc:
        xp_counters[member.id] = xp_counters.get(member.id, 0) + 1
        print(f"[CHENIL] {member.display_name} — checks: {xp_counters[member.id]}/{threshold}")

    # Vérifie si quelqu'un atteint le seuil
    for uid, checks in list(xp_counters.items()):
        if checks < threshold:
            continue

        xp_counters[uid] = 0  # reset

        chenil_data = get_chenil_pokemon(str(uid))
        if not chenil_data:
            print(f"[CHENIL] {uid} aurait pu gagner {xp_amount} XP mais n'a pas de Pokémon dans le chenil.")
            continue

        # ── Œuf ──────────────────────────────────────────────────────────────
        if chenil_data["is_egg"]:
            ready = add_egg_xp(str(uid), xp_amount)

            # Relit les valeurs fraîches
            cur.execute(
                "SELECT egg_xp, egg_xp_evo FROM chenil WHERE user_id = %s",
                (str(uid),)
            )
            row = cur.fetchone()
            current_xp, xp_evo = row if row else (0, 400)

            await channel.send(
                f"🥚 **+{xp_amount} XP** pour l'œuf de <@{uid}> ! "
                f"(`{current_xp}/{xp_evo}`)"
            )

            if ready:
                remove_chenil_pokemon(str(uid))
                pokemon_name = get_random_egg_pokemon()

                if not pokemon_name:
                    await channel.send(
                        f"🥚 L'œuf de <@{uid}> a éclos... mais rien n'en est sorti. "
                        f"(Erreur oeuf.json)"
                    )
                    continue

                # Ajout via save_new_capture avec IVs et stats depuis oeuf.json
                from new_db import save_new_capture
                import random as _random

                oeuf_json_path = os.path.join(script_dir, "json", "marche_noir", "oeuf.json")
                try:
                    with open(oeuf_json_path, "r", encoding="utf-8") as _f:
                        oeuf_pool = json.load(_f)
                    chosen_data = next(
                        (p for p in oeuf_pool if p.get("name") == pokemon_name),
                        None
                    )
                except Exception as _e:
                    chosen_data = None
                    print(f"[CHENIL] Erreur lecture oeuf.json pour éclosion : {_e}")

                if chosen_data:
                    base_stats = chosen_data.get("stats", {})
                    ivs = {stat: _random.randint(0, 31) for stat in base_stats}
                    final_stats = {stat: base_stats[stat] + ivs[stat] for stat in base_stats}
                    save_new_capture(str(uid), pokemon_name, ivs, final_stats, chosen_data)
                else:
                    # Fallback minimal si données introuvables
                    ivs = {"hp": 15, "attack": 15, "defense": 15,
                           "special_attack": 15, "special_defense": 15, "speed": 15}
                    final_stats = ivs.copy()
                    save_new_capture(str(uid), pokemon_name, ivs, final_stats, {})

                await channel.send(
                    f"🎉 L'œuf de <@{uid}> a éclos ! "
                    f"Un **{pokemon_name}** en est sorti !"
                )

            continue  # ne pas tomber dans le bloc Pokémon normal

        # ── Pokémon normal ────────────────────────────────────────────────────
        pokemon_name = chenil_data["name"]
        captures = get_new_captures(str(uid))
        pokemon  = next(
            (p for p in captures if p["name"].lower() == pokemon_name.lower()),
            None
        )

        if not pokemon:
            print(f"[CHENIL] Pokémon '{pokemon_name}' de {uid} introuvable dans new_captures.")
            continue

        can_evolve = add_xp(str(uid), pokemon["name"], xp_amount)
        print(f"[CHENIL] +{xp_amount} XP pour {pokemon['name']} de {uid}.")
        await channel.send(
            f"🏠 **+{xp_amount} XP** pour **{pokemon['name']}** de <@{uid}> grâce au chenil !"
        )

        if can_evolve:
            result = evolve_pokemon(str(uid), pokemon)
            if result["success"]:
                print(f"[CHENIL] {pokemon['name']} de {uid} a évolué en {result['evo_name']} !")
                set_chenil_pokemon(str(uid), result["evo_name"])
                await channel.send(
                    f"🎉 **{pokemon['name']}** de <@{uid}> a évolué en "
                    f"**{result['evo_name']}** grâce au chenil !"
                )
            else:
                print(f"[CHENIL] Évolution impossible : {result['reason']}")


# ──────────────────────────────────────────────
# COMMANDES DISCORD
# ──────────────────────────────────────────────

def setup_chenil(bot, channel_id):
    global _bot, _text_channel_id
    _bot             = bot
    _text_channel_id = channel_id

    @bot.command(name="chenil")
    async def chenil_cmd(ctx, pokemon_name: str):
        """!chenil <nom> — Place un Pokémon ou un œuf dans le chenil."""
        uid = str(ctx.author.id)

        # Vérifie qu'il n'y a rien déjà dans le chenil
        current = get_chenil_pokemon(uid)
        if current:
            await ctx.send(
                f"⚠️ Tu as déjà **{current['name']}** dans le chenil. "
                f"Utilise `!retirer_chenil` avant d'en mettre un autre."
            )
            return

        # Cherche d'abord un œuf dans l'inventaire
        from inventory_db import get_inventory
        inventory = get_inventory(uid)
        egg_item  = next(
            (i for i in inventory
             if i["name"].lower() == pokemon_name.lower()
             and i.get("extra") == "oeuf"),
            None
        )

        if egg_item:
            xp_evo = egg_item.get("xp_evo", 400)
            set_chenil_pokemon(uid, egg_item["name"], is_egg=True, egg_xp_evo=xp_evo)
            await ctx.send(
                f"🥚 **{egg_item['name']}** a été placé dans le chenil ! "
                f"Il accumulera de l'XP tant que tu seras dans le vocal. "
                f"(`0/{xp_evo}` XP pour éclore)"
            )
            return

        # Sinon cherche dans les captures Pokémon normales
        captures = get_new_captures(uid)
        pokemon  = next(
            (p for p in captures if p["name"].lower() == pokemon_name.lower()),
            None
        )

        if not pokemon:
            await ctx.send(
                f"❌ **{pokemon_name}** introuvable dans ta collection ou ton inventaire."
            )
            return

        set_chenil_pokemon(uid, pokemon["name"])
        await ctx.send(
            f"🏠 **{pokemon['name']}** a été placé dans le chenil ! "
            f"Il gagnera de l'XP tant que tu seras dans le salon vocal."
        )

    @bot.command(name="retirer_chenil")
    async def retirer_chenil_cmd(ctx):
        """!retirer_chenil — Retire votre Pokémon ou œuf du chenil."""
        uid     = str(ctx.author.id)
        current = get_chenil_pokemon(uid)

        if not current:
            await ctx.send("❌ Tu n'as pas de Pokémon dans le chenil.")
            return

        remove_chenil_pokemon(uid)
        nom = current["name"]
        if current["is_egg"]:
            await ctx.send(
                f"✅ **{nom}** a été retiré du chenil. "
                f"(XP perdu : {current['egg_xp']}/{current['egg_xp_evo']})"
            )
        else:
            await ctx.send(f"✅ **{nom}** a été retiré du chenil.")

    @bot.command(name="add_chenil_xp")
    @commands.has_permissions(administrator=True)
    async def add_chenil_xp_cmd(ctx, member: discord.Member, xp: int):
        """!add_chenil_xp @utilisateur <xp> — (Admin) Ajoute manuellement de l'XP au chenil."""
        uid         = str(member.id)
        chenil_data = get_chenil_pokemon(uid)

        if not chenil_data:
            await ctx.send(f"❌ {member.mention} n'a pas de Pokémon dans le chenil.")
            return

        # ── Œuf ──────────────────────────────────────────────────────────────
        if chenil_data["is_egg"]:
            ready = add_egg_xp(uid, xp)
            cur.execute(
                "SELECT egg_xp, egg_xp_evo FROM chenil WHERE user_id = %s", (uid,)
            )
            row = cur.fetchone()
            current_xp, xp_evo = row if row else (0, 400)

            if not ready:
                await ctx.send(
                    f"🥚 **+{xp} XP** ajouté à l'œuf de {member.mention} !\n"
                    f"📊 XP actuel : `{current_xp} / {xp_evo}`"
                )
                return

            # Éclosion forcée
            remove_chenil_pokemon(uid)
            pokemon_name = get_random_egg_pokemon()
            if not pokemon_name:
                await ctx.send(f"🥚 L'œuf de {member.mention} a éclos mais oeuf.json est vide/introuvable.")
                return

            from new_db import save_new_capture
            oeuf_json_path = os.path.join(script_dir, "json", "marche_noir", "oeuf.json")
            try:
                with open(oeuf_json_path, "r", encoding="utf-8") as _f:
                    oeuf_pool = json.load(_f)
                chosen_data = next(
                    (p for p in oeuf_pool if p.get("name") == pokemon_name),
                    None
                )
            except Exception:
                chosen_data = None

            if chosen_data:
                import random as _random
                base_stats  = chosen_data.get("stats", {})
                ivs         = {stat: _random.randint(0, 31) for stat in base_stats}
                final_stats = {stat: base_stats[stat] + ivs[stat] for stat in base_stats}
                save_new_capture(uid, pokemon_name, ivs, final_stats, chosen_data)
            else:
                ivs = {"hp": 15, "attack": 15, "defense": 15,
                       "special_attack": 15, "special_defense": 15, "speed": 15}
                save_new_capture(uid, pokemon_name, ivs, ivs.copy(), {})

            await ctx.send(
                f"🎉 L'œuf de {member.mention} a éclos ! "
                f"Un **{pokemon_name}** en est sorti !"
            )
            return

        # ── Pokémon normal ────────────────────────────────────────────────────
        pokemon_name = chenil_data["name"]
        captures = get_new_captures(uid)
        pokemon  = next(
            (p for p in captures if p["name"].lower() == pokemon_name.lower()),
            None
        )

        if not pokemon:
            await ctx.send(f"❌ Pokémon **{pokemon_name}** introuvable dans new_captures.")
            return

        can_evolve = add_xp(uid, pokemon["name"], xp)

        if not can_evolve:
            updated    = next(
                (p for p in get_new_captures(uid) if p["name"] == pokemon["name"]),
                None
            )
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
                f"🎉 **{pokemon['name']}** de {member.mention} a évolué en "
                f"**{result['evo_name']}** !\n"
                f"✨ IV hérités **+4** sur toutes les stats."
            )
        else:
            await ctx.send(
                f"✅ **+{xp} XP** ajouté à **{pokemon['name']}** de {member.mention}.\n"
                f"⚠️ Évolution impossible : {result['reason']}"
            )