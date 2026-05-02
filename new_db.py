import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connexion globale à la base
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS new_captures;")

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
# MIGRATION : ajoute les colonnes si elles n'existent pas encore
# (utile si la table existait déjà avant cette mise à jour)
# ──────────────────────────────────────────────
for column, definition in [
    ("current_xp", "INT DEFAULT 0"),
    ("xp_evo",     "INT DEFAULT 0"),
    ("evo",        "JSONB DEFAULT '{\"name\": \"pas evo\", \"file\": \"pas evo\"}'::jsonb"),
]:
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'new_captures' AND column_name = %s
    """, (column,))
    if not cur.fetchone():
        cur.execute(f"ALTER TABLE new_captures ADD COLUMN {column} {definition}")
        print(f"[MIGRATION] Colonne '{column}' ajoutée.")
    else:
        print(f"[MIGRATION] Colonne '{column}' déjà présente, rien à faire.")

conn.commit()


# ──────────────────────────────────────────────
# FONCTIONS
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

    # Normalise le champ evo
    evo = pokemon.get("evo", {"name": "pas evo", "file": "pas evo"})
    if evo in (None, "pas evo", ""):
        evo = {"name": "pas evo", "file": "pas evo"}

    # Vérifie combien de fois ce Pokémon a déjà été capturé pour cet utilisateur
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
        increase_pokemon_iv(user_id, pokemon_name, 3)
        print(f"[INFO] Pokémon {pokemon_name} a eu ses IVs augmentés de 3 pour {user_id}")

    # Invalider le cache après chaque capture
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
    """
    Supprime un Pokémon capturé pour un utilisateur et invalide le cache du Pokédex.
    """
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