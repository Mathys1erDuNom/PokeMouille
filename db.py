import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# Charge les variables d’environnement
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Connexion globale à la base
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()





# Crée la table si elle n'existe pas
cur.execute("""
CREATE TABLE IF NOT EXISTS captures (
    user_id TEXT,
    name TEXT,
    ivs JSONB,
    stats JSONB,
    image TEXT,
    type JSONB,
    attacks JSONB
);
""")
conn.commit()



from functools import lru_cache

@lru_cache(maxsize=5000)
def get_captures_cached(user_id):
    return tuple(get_captures(user_id))  # tuple pour être hashable


def save_capture(user_id, pokemon_name, ivs, final_stats, pokemon):
    user_id = str(user_id)
    get_captures_cached.cache_clear()


    # Vérifie combien de fois ce Pokémon a déjà été capturé pour cet utilisateur
    cur.execute("""
        SELECT COUNT(*) FROM captures
        WHERE user_id = %s AND name LIKE %s || '%%'
    """, (user_id, pokemon_name))
    existing_count = cur.fetchone()[0]

    if existing_count == 0:
        final_name = pokemon_name
    else:
        final_name = f"{pokemon_name}{existing_count + 1}"

    # Insère la capture
    cur.execute("""
        INSERT INTO captures (user_id, name, ivs, stats, image, type, attacks)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        user_id,
        final_name,
        Json(ivs),
        Json(final_stats),
        pokemon.get("image", ""),
        Json(pokemon.get("type", [])),
        Json(pokemon.get("attacks", []))
    ))
    conn.commit()
    print(f"[INFO] Pokémon {final_name} enregistré pour l’utilisateur {user_id}")

def get_captures(user_id):
    """Récupère toutes les captures d’un utilisateur."""
    cur.execute("""
        SELECT name, ivs, stats, image, type, attacks FROM captures WHERE user_id = %s
    """, (str(user_id),))
    rows = cur.fetchall()
    captures = []
    for row in rows:
        captures.append({
            "name": row[0],
            "ivs": row[1],
            "stats": row[2],
            "image": row[3],
            "type": row[4],
            "attacks": row[5]
        })
    return captures
