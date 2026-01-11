# new_db.py
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





# Crée la table si elle n'existe pas
cur.execute("""
CREATE TABLE IF NOT EXISTS new_captures (
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


def save_new_capture(user_id, pokemon_name, ivs, final_stats, pokemon):
    """
    Enregistre une nouvelle capture et invalide le cache du pokédex pour cet utilisateur
    """
    user_id = str(user_id)
    
    # Vérifie combien de fois ce Pokémon a déjà été capturé pour cet utilisateur
    cur.execute("""
        SELECT COUNT(*) FROM new_captures
        WHERE user_id = %s AND name LIKE %s || '%%'
    """, (user_id, pokemon_name))
    existing_count = cur.fetchone()[0]
    
    if existing_count == 0:
        final_name = pokemon_name
    else:
        final_name = f"{pokemon_name}{existing_count + 1}"
    
    # Insère la capture
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
    
    print(f"[INFO] Pokémon {final_name} enregistré pour l'utilisateur {user_id}")
    
    # 🔥 INVALIDER LE CACHE après chaque capture
    try:
        from new_pokedex import invalidate_new_pokedex_cache
        invalidate_new_pokedex_cache(user_id)
        print(f"[CACHE] Cache du pokédex invalidé pour {user_id}")
    except ImportError:
        print("[WARNING] Impossible d'importer invalidate_new_pokedex_cache")


def get_new_captures(user_id):
    """Récupère toutes les captures d'un utilisateur."""
    cur.execute("""
        SELECT name, ivs, stats, image, type, attacks FROM new_captures WHERE user_id = %s
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


def delete_capture(user_id, pokemon_name):
    """
    Supprime un Pokémon capturé pour un utilisateur et invalide le cache du Pokédex.
    """
    user_id = str(user_id)

    # Supprimer la capture
    cur.execute("""
        DELETE FROM new_captures
        WHERE user_id = %s AND name = %s
    """, (user_id, pokemon_name))
    conn.commit()

    print(f"[INFO] Pokémon {pokemon_name} supprimé pour l'utilisateur {user_id}")

    # 🔥 Invalider le cache du Pokédex pour cet utilisateur
    try:
        from new_pokedex import invalidate_new_pokedex_cache
        invalidate_new_pokedex_cache(user_id)
        print(f"[CACHE] Cache du pokédex invalidé pour {user_id}")
    except ImportError:
        print("[WARNING] Impossible d'importer invalidate_new_pokedex_cache")
