import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connexion à la base de données
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Crée la table si elle n'existe pas
cur.execute("""
CREATE TABLE IF NOT EXISTS new_captures (
    capture_id SERIAL PRIMARY KEY,
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

from psycopg2.extras import Json

def save_new_capture(conn, user_id, pokemon_name, ivs, final_stats, pokemon):
    user_id = str(user_id)

    cur = conn.cursor()

    # Vérifie combien de Pokémon avec ce nom existe déjà pour l'utilisateur
    cur.execute("""
        SELECT COUNT(*) FROM new_captures
        WHERE user_id = %s AND name LIKE %s || '%%'
    """, (user_id, pokemon_name))
    existing_count = cur.fetchone()[0]

    # Si déjà existant, on ajoute un suffixe pour différencier
    if existing_count == 0:
        final_name = pokemon_name
    else:
        final_name = f"{pokemon_name}{existing_count + 1}"

    # INSERT sans capture_id
    cur.execute("""
        INSERT INTO new_captures (user_id, name, ivs, stats, image, type, attacks)
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
    cur.close()
    print(f"[INFO] Pokémon {final_name} enregistré pour l’utilisateur {user_id}")




def get_new_captures(conn, user_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, name, ivs, stats, image, type, attacks
        FROM new_captures
        WHERE user_id = %s
    """, (str(user_id),))
    results = cur.fetchall()
    cur.close()

    captures = []
    for row in results:
        captures.append({
            "user_id": row[0],
            "name": row[1],
            "ivs": row[2],
            "stats": row[3],
            "image": row[4],
            "type": row[5],
            "attacks": row[6]
        })
    return captures
