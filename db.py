import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()

# --- Base "old_database" ---
OLD_DB_URL = os.getenv("OLD_DATABASE_URL")
old_conn = psycopg2.connect(OLD_DB_URL, sslmode="require")
old_cur = old_conn.cursor()

# --- Base "new_database" ---
NEW_DB_URL = os.getenv("NEW_DATABASE_URL")
new_conn = psycopg2.connect(NEW_DB_URL, sslmode="require")
new_cur = new_conn.cursor()

# --- Fonctions pour récupérer les captures ---
def get_captures_old(user_id):
    old_cur.execute("""
        SELECT name, ivs, stats, image, type, attacks FROM captures WHERE user_id = %s
    """, (str(user_id),))
    rows = old_cur.fetchall()
    return [
        {
            "name": row[0],
            "ivs": row[1],
            "stats": row[2],
            "image": row[3],
            "type": row[4],
            "attacks": row[5]
        } for row in rows
    ]

def get_captures_new(user_id):
    new_cur.execute("""
        SELECT name, ivs, stats, image, type, attacks FROM captures WHERE user_id = %s
    """, (str(user_id),))
    rows = new_cur.fetchall()
    return [
        {
            "name": row[0],
            "ivs": row[1],
            "stats": row[2],
            "image": row[3],
            "type": row[4],
            "attacks": row[5]
        } for row in rows
    ]

# --- Fonction pour sauvegarder une capture dans la nouvelle base ---
def save_capture(user_id, name, ivs, stats, image, type_, attacks):
    new_cur.execute("""
        INSERT INTO captures (user_id, name, ivs, stats, image, type, attacks)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (str(user_id), name, Json(ivs), Json(stats), image, Json(type_), Json(attacks)))
    new_conn.commit()

# --- alias pour que le bot continue de fonctionner avec les noms existants ---
get_captures = get_captures_new
