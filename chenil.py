import asyncio
import os
import json
import random
import psycopg2
from dotenv import load_dotenv
from discord.ext import commands
import discord

from new_db import get_new_captures, add_xp, evolve_pokemon

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

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
    egg_xp_evo   INTEGER DEFAULT 400,
    egg_is_shiny BOOLEAN DEFAULT FALSE
);
""")

for col, definition in [
    ("is_egg", "BOOLEAN DEFAULT FALSE"),
    ("egg_xp", "INTEGER DEFAULT 0"),
    ("egg_xp_evo", "INTEGER DEFAULT 400"),
    ("egg_is_shiny", "BOOLEAN DEFAULT FALSE"),
]:
    try:
        cur.execute(f"ALTER TABLE chenil ADD COLUMN IF NOT EXISTS {col} {definition};")
        conn.commit()
    except Exception:
        conn.rollback()


# ──────────────────────────────────────────────
# CORE
# ──────────────────────────────────────────────

def get_chenil_pokemon(user_id: str) -> dict | None:
    cur.execute("""
        SELECT pokemon_name, is_egg, egg_xp, egg_xp_evo, egg_is_shiny
        FROM chenil WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()

    if not row:
        return None

    return {
        "name": row[0],
        "is_egg": row[1],
        "egg_xp": row[2],
        "egg_xp_evo": row[3],
        "egg_is_shiny": row[4],
    }


def set_chenil_pokemon(user_id: str, pokemon_name: str,
                        is_egg: bool = False,
                        egg_xp_evo: int = 400,
                        egg_is_shiny: bool = False):

    cur.execute("""
        INSERT INTO chenil (user_id, pokemon_name, is_egg, egg_xp, egg_xp_evo, egg_is_shiny)
        VALUES (%s, %s, %s, 0, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            pokemon_name = EXCLUDED.pokemon_name,
            is_egg       = EXCLUDED.is_egg,
            egg_xp       = 0,
            egg_xp_evo   = EXCLUDED.egg_xp_evo,
            egg_is_shiny = EXCLUDED.egg_is_shiny
    """, (user_id, pokemon_name, is_egg, egg_xp_evo, egg_is_shiny))

    conn.commit()


def remove_chenil_pokemon(user_id: str):
    cur.execute("DELETE FROM chenil WHERE user_id = %s", (user_id,))
    conn.commit()


def add_egg_xp(user_id: str, amount: int) -> bool:
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


# ──────────────────────────────────────────────
# RANDOM EGG
# ──────────────────────────────────────────────

def get_random_egg_pokemon():
    json_path = os.path.join(script_dir, "json", "marche_noir", "oeuf.json")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            pool = json.load(f)

        if not pool:
            return None, None

        chosen = random.choice(pool)
        name = chosen.get("name") or chosen.get("pokemon_name")

        return name, chosen

    except Exception as e:
        print(f"[CHENIL] erreur lecture oeuf.json : {e}")
        return None, None


# ──────────────────────────────────────────────
# GLOBALS
# ──────────────────────────────────────────────

_bot = None
_text_channel_id = None


# ──────────────────────────────────────────────
# LOOP
# ──────────────────────────────────────────────
#combien on gagne et en combien de temps, de base 5 xp toutes les 30min
async def tick_chenil_xp(members_in_vc, xp_counters,
                         xp_amount=400, threshold=1):

    channel = _bot.get_channel(_text_channel_id)
    ids = {m.id for m in members_in_vc}

    for uid in list(xp_counters.keys()):
        if uid not in ids:
            del xp_counters[uid]

    for m in members_in_vc:
        xp_counters[m.id] = xp_counters.get(m.id, 0) + 1

    for uid, checks in list(xp_counters.items()):
        if checks < threshold:
            continue

        xp_counters[uid] = 0
        data = get_chenil_pokemon(str(uid))

        if not data:
            continue

        # ───────── ŒUF ─────────
        if data["is_egg"]:
            ready = add_egg_xp(str(uid), xp_amount)

            cur.execute(
                "SELECT egg_xp, egg_xp_evo FROM chenil WHERE user_id = %s",
                (str(uid),)
            )
            egg_xp, egg_xp_evo = cur.fetchone()

            await channel.send(
                f"🥚 +{xp_amount} XP pour l'œuf de <@{uid}> ({egg_xp}/{egg_xp_evo})"
            )

            if ready:
                is_shiny = data["egg_is_shiny"]

                remove_chenil_pokemon(str(uid))
                name, chosen = get_random_egg_pokemon()

                if not name:
                    await channel.send("🥚 Éclosion échouée.")
                    continue

                from new_db import save_new_capture

                if chosen:
                    base = chosen.get("stats", {})
                    ivs = {k: random.randint(0, 31) for k in base}
                    final = {k: base[k] + ivs[k] for k in base}
                    save_new_capture(str(uid), name, ivs, final, chosen)
                else:
                    ivs = {
                        "hp": 15,
                        "attack": 15,
                        "defense": 15,
                        "special_attack": 15,
                        "special_defense": 15,
                        "speed": 15
                    }
                    save_new_capture(str(uid), name, ivs, ivs.copy(), {})

                shiny_txt = " ✨ SHINY" if is_shiny else ""
                await channel.send(
                    f"🎉 Éclosion : **{name}**{shiny_txt} pour <@{uid}> !"
                )

            continue

        # ───────── POKÉMON ─────────
        pokemon_name = data["name"]

        captures = get_new_captures(str(uid))
        pokemon = next((p for p in captures
                        if p["name"].lower() == pokemon_name.lower()), None)

        if not pokemon:
            continue

        can_evolve = add_xp(str(uid), pokemon["name"], xp_amount)

        await channel.send(
            f"🏠 +{xp_amount} XP pour {pokemon['name']} (<@{uid}>)"
        )

        if can_evolve:
            result = evolve_pokemon(str(uid), pokemon)
            if result["success"]:
                set_chenil_pokemon(str(uid), result["evo_name"])
                await channel.send(
                    f"🎉 Évolution : {pokemon['name']} → {result['evo_name']}"
                )


# ──────────────────────────────────────────────
# COMMANDES
# ──────────────────────────────────────────────

def setup_chenil(bot, channel_id):
    global _bot, _text_channel_id
    _bot = bot
    _text_channel_id = channel_id

    @bot.command(name="chenil")
    async def chenil_cmd(ctx, name: str = None):
        uid = str(ctx.author.id)

        if name is None:
            data = get_chenil_pokemon(uid)
            return await ctx.send(str(data) if data else "Chenil vide.")

        if get_chenil_pokemon(uid):
            return await ctx.send("Déjà un Pokémon dans le chenil.")

        from inventory_db import get_inventory
        inv = get_inventory(uid)

        egg = next((i for i in inv
                    if i["name"].lower() == name.lower()
                    and i.get("extra") == "oeuf"), None)

        if egg:
            # 🎯 PROBA SHINY DÉFINIE DANS LE JSON
            shiny_rate = egg.get("shiny", 0)
            is_shiny = shiny_rate > 0 and random.randint(1, shiny_rate) == 1

            set_chenil_pokemon(
                uid,
                egg["name"],
                is_egg=True,
                egg_xp_evo=egg.get("xp_evo", 400),
                egg_is_shiny=is_shiny
            )

            return await ctx.send("🥚 Œuf placé dans le chenil.")

        captures = get_new_captures(uid)
        pokemon = next((p for p in captures
                        if p["name"].lower() == name.lower()), None)

        if not pokemon:
            return await ctx.send("Introuvable.")

        set_chenil_pokemon(uid, pokemon["name"])
        await ctx.send("🏠 Pokémon placé.")

    @bot.command(name="retirer_chenil")
    async def remove_cmd(ctx):
        uid = str(ctx.author.id)
        remove_chenil_pokemon(uid)
        await ctx.send("Retiré.")