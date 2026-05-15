import os
import json
import discord
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
from discord.ext import commands

# Charge les variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Chemin absolu vers le dossier json
script_dir = os.path.dirname(os.path.abspath(__file__))
json_dir   = os.path.join(script_dir, "json")

# Connexion globale à la base
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()



# Crée la table si elle n'existe pas
cur.execute("""
CREATE TABLE IF NOT EXISTS new_captures (
    user_id     TEXT,
    name        TEXT,
    ivs         JSONB,
    stats       JSONB,
    image       TEXT,
    type        JSONB,
    attacks     JSONB,
    current_xp  INT DEFAULT 0,
    xp_evo      INT DEFAULT 0,
    evo         JSONB DEFAULT '{"name": "pas evo", "file": "pas evo"}'::jsonb
);
""")
conn.commit()





# ──────────────────────────────────────────────
# FONCTIONS BASE DE DONNÉES
# ──────────────────────────────────────────────

def save_new_capture(user_id, pokemon_name, ivs, final_stats, pokemon):
    """
    Enregistre une nouvelle capture et invalide le cache du pokédex pour cet utilisateur.

    pokemon peut contenir les clés optionnelles :
        - current_xp (int)
        - xp_evo     (int)
        - evo        (dict {"name": ..., "file": ...} ou "pas evo")
    """
    user_id = str(user_id)

    evo = pokemon.get("evo", {"name": "pas evo", "file": "pas evo"})
    if evo in (None, "pas evo", ""):
        evo = {"name": "pas evo", "file": "pas evo"}

    cur.execute("""
        SELECT COUNT(*) FROM new_captures
        WHERE user_id = %s AND name LIKE %s || '%%'
    """, (user_id, pokemon_name))
    existing_count = cur.fetchone()[0]

    if existing_count == 0:
        cur.execute("""
            INSERT INTO new_captures
                (user_id, name, ivs, stats, image, type, attacks, current_xp, xp_evo, evo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            pokemon_name,
            Json(ivs),
            Json(final_stats),
            pokemon.get("image", ""),
            Json(pokemon.get("type", [])),
            Json(pokemon.get("attacks", [])),
            pokemon.get("current_xp", 0),
            pokemon.get("xp_evo", 0),
            Json(evo),
        ))
        conn.commit()
        print(f"[INFO] Pokémon {pokemon_name} enregistré pour l'utilisateur {user_id}")
    else:
        increase_pokemon_iv(user_id, pokemon_name, 4)
        print(f"[INFO] Pokémon {pokemon_name} a eu ses IVs augmentés de 3 pour {user_id}")

    try:
        from new_pokedex import invalidate_new_pokedex_cache
        invalidate_new_pokedex_cache(user_id)
        print(f"[CACHE] Cache du pokédex invalidé pour {user_id}")
    except ImportError:
        print("[WARNING] Impossible d'importer invalidate_new_pokedex_cache")


def get_new_captures(user_id):
    """Récupère toutes les captures d'un utilisateur."""
    cur.execute("""
        SELECT name, ivs, stats, image, type, attacks, current_xp, xp_evo, evo
        FROM new_captures
        WHERE user_id = %s
    """, (str(user_id),))
    rows = cur.fetchall()

    captures = []
    for row in rows:
        captures.append({
            "name":       row[0],
            "ivs":        row[1],
            "stats":      row[2],
            "image":      row[3],
            "type":       row[4],
            "attacks":    row[5],
            "current_xp": row[6],
            "xp_evo":     row[7],
            "evo":        row[8],
        })

    return captures


def delete_capture(user_id, pokemon_name):
    """Supprime un Pokémon capturé pour un utilisateur et invalide le cache du Pokédex."""
    user_id = str(user_id)

    cur.execute("""
        DELETE FROM new_captures
        WHERE user_id = %s AND name = %s
    """, (user_id, pokemon_name))
    conn.commit()

    print(f"[INFO] Pokémon {pokemon_name} supprimé pour l'utilisateur {user_id}")

    try:
        from new_pokedex import invalidate_new_pokedex_cache
        invalidate_new_pokedex_cache(user_id)
        print(f"[CACHE] Cache du pokédex invalidé pour {user_id}")
    except ImportError:
        print("[WARNING] Impossible d'importer invalidate_new_pokedex_cache")


def increase_pokemon_iv(user_id, pokemon_name, iv_increase, stat_name=None):
    """
    Augmente les IV d'un Pokémon pour un utilisateur.
    Les IV sont plafonnés à 31, et les stats sont mises à jour en conséquence.

    Paramètres :
    - iv_increase : nombre de points à ajouter
    - stat_name   : (optionnel) nom de la stat ciblée (ex: "attack", "speed")
                    Si None, tous les IV sont augmentés.
    """
    user_id = str(user_id)

    cur.execute("""
        SELECT ivs, stats FROM new_captures
        WHERE user_id = %s AND name = %s
    """, (user_id, pokemon_name))
    row = cur.fetchone()

    if not row:
        print(f"[WARNING] Pokémon {pokemon_name} non trouvé pour {user_id}")
        return False

    ivs   = row[0]
    stats = row[1]

    if stat_name is not None:
        if stat_name not in ivs:
            print(f"[WARNING] Stat '{stat_name}' introuvable pour {pokemon_name} "
                  f"(stats disponibles : {list(ivs.keys())})")
            return False
        old_iv = ivs[stat_name]
        ivs[stat_name]   = min(31, ivs[stat_name] + iv_increase)
        stats[stat_name] = stats.get(stat_name, 0) + (ivs[stat_name] - old_iv)
        print(f"[INFO] IV '{stat_name}' du Pokémon {pokemon_name} de {user_id} augmenté de {iv_increase}")
    else:
        for stat in ivs:
            old_iv = ivs[stat]
            ivs[stat]   = min(31, ivs[stat] + iv_increase)
            stats[stat] = stats.get(stat, 0) + (ivs[stat] - old_iv)
        print(f"[INFO] Tous les IV du Pokémon {pokemon_name} de {user_id} augmentés de {iv_increase}")

    cur.execute("""
        UPDATE new_captures
        SET ivs = %s, stats = %s
        WHERE user_id = %s AND name = %s
    """, (Json(ivs), Json(stats), user_id, pokemon_name))
    conn.commit()

    try:
        from new_pokedex import invalidate_new_pokedex_cache
        invalidate_new_pokedex_cache(user_id)
        print(f"[CACHE] Cache du pokédex invalidé pour {user_id}")
    except ImportError:
        print("[WARNING] Impossible d'importer invalidate_new_pokedex_cache")

    return True


def add_xp(user_id, pokemon_name, xp_gained):
    """
    Ajoute de l'XP à un Pokémon.
    Retourne True si le Pokémon peut évoluer (current_xp >= xp_evo), False sinon.
    """
    user_id = str(user_id)

    cur.execute("""
        SELECT current_xp, xp_evo FROM new_captures
        WHERE user_id = %s AND name = %s
    """, (user_id, pokemon_name))
    row = cur.fetchone()

    if not row:
        print(f"[WARNING] Pokémon {pokemon_name} non trouvé pour {user_id}")
        return False

    current_xp, xp_evo = row
    new_xp = current_xp + xp_gained

    cur.execute("""
        UPDATE new_captures
        SET current_xp = %s
        WHERE user_id = %s AND name = %s
    """, (new_xp, user_id, pokemon_name))
    conn.commit()

    print(f"[INFO] {pokemon_name} a maintenant {new_xp} XP (seuil évolution : {xp_evo})")

    can_evolve = xp_evo > 0 and new_xp >= xp_evo
    return can_evolve


# ──────────────────────────────────────────────
# ÉVOLUTION
# ──────────────────────────────────────────────

def evolve_pokemon(user_id, pokemon):
    """
    Fait évoluer un Pokémon vers sa prochaine forme.

    Paramètres :
    - user_id : ID de l'utilisateur (str ou int)
    - pokemon : dict du Pokémon actuel (tel que retourné par get_new_captures)

    Retourne :
    - {"success": True,  "evo_name": str}  si l'évolution a réussi
    - {"success": False, "reason": str}    si l'évolution est impossible
    """
    user_id  = str(user_id)
    evo      = pokemon.get("evo", {})
    evo_name = evo.get("name", "pas evo")
    evo_file = evo.get("file", "pas evo")

    # Vérifie qu'une évolution existe
    if evo_name == "pas evo" or evo_file == "pas evo":
        return {"success": False, "reason": "Ce Pokémon n'a pas d'évolution."}

    # Charge le fichier JSON de l'évolution
    try:
        with open(os.path.join(json_dir, evo_file), "r", encoding="utf-8") as f:
            all_pokemons = json.load(f)
    except FileNotFoundError:
        return {"success": False, "reason": f"Fichier `json/{evo_file}` introuvable."}

    evo_data = next(
        (p for p in all_pokemons if p["name"].lower() == evo_name.lower()),
        None
    )
    if not evo_data:
        return {"success": False, "reason": f"**{evo_name}** introuvable dans `json/{evo_file}`."}

    # Nouveaux IV : IV actuels + 4, plafonnés à 31
    old_ivs  = pokemon.get("ivs", {})
    new_ivs  = {stat: min(31, val + 4) for stat, val in old_ivs.items()}

    # Stats finales = stats de base de l'évolution + nouveaux IV
    base_stats = evo_data.get("stats", {})
    new_stats  = {stat: base_stats.get(stat, 0) + new_ivs.get(stat, 0) for stat in base_stats}

    # Dict du nouveau Pokémon à enregistrer
    new_pokemon = {
        "image":      evo_data.get("image", ""),
        "type":       evo_data.get("type", []),
        "attacks":    evo_data.get("attacks", []),
        "current_xp": 0,
        "xp_evo":     evo_data.get("xp_evo", 0),
        "evo":        evo_data.get("evo", {"name": "pas evo", "file": "pas evo"}),
    }

    # Supprime l'ancienne forme puis enregistre la nouvelle
    delete_capture(user_id, pokemon["name"])
    save_new_capture(user_id, evo_name, new_ivs, new_stats, new_pokemon)

    print(f"[EVO] {pokemon['name']} → {evo_name} pour l'utilisateur {user_id}")
    return {"success": True, "evo_name": evo_name}


# ──────────────────────────────────────────────
# SETUP DISCORD
# ──────────────────────────────────────────────

def setupxp(bot):

    @bot.command(name="addxp")
    @commands.has_permissions(administrator=True)
    async def addxp(ctx, member: discord.Member, pokemon_name: str, xp: int):
        """
        !addxp @utilisateur <nom_pokemon> <xp>
        Ajoute de l'XP à un Pokémon. Déclenche l'évolution si le seuil est atteint.
        """
        user_id = str(member.id)

        # Cherche le Pokémon dans la collection de l'utilisateur
        captures = get_new_captures(user_id)
        pokemon  = next((p for p in captures if p["name"].lower() == pokemon_name.lower()), None)

        if not pokemon:
            await ctx.send(f"❌ **{pokemon_name}** introuvable dans la collection de {member.display_name}.")
            return

        # Ajoute l'XP
        can_evolve = add_xp(user_id, pokemon["name"], xp)

        if not can_evolve:
            updated    = next((p for p in get_new_captures(user_id) if p["name"] == pokemon["name"]), None)
            current_xp = updated["current_xp"] if updated else "?"
            xp_evo     = updated["xp_evo"]     if updated else "?"

            await ctx.send(
                f"✅ **+{xp} XP** ajouté à **{pokemon['name']}** de {member.mention} !\n"
                f"📊 XP actuel : `{current_xp} / {xp_evo}`"
            )
            return

        # Seuil atteint → tente l'évolution
        result = evolve_pokemon(user_id, pokemon)

        if not result["success"]:
            await ctx.send(
                f"✅ **+{xp} XP** ajouté à **{pokemon['name']}** de {member.mention}.\n"
                f"⚠️ Évolution impossible : {result['reason']}"
            )
            return

        await ctx.send(
            f"🎉 **{pokemon['name']}** de {member.mention} a évolué en **{result['evo_name']}** !\n"
            f"✨ IV hérités **+4** sur toutes les stats.\n"
            f"🗑️ **{pokemon['name']}** a été retiré de la collection."
        )