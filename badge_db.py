# badge_db.py
import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
import json

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Création de la table badges
cur.execute("""
CREATE TABLE IF NOT EXISTS badges (
    user_id TEXT,
    badge_id INT,
    UNIQUE(user_id, badge_id)
);
""")
conn.commit()

def give_badge(user_id, badge_id):
    try:
        cur.execute("INSERT INTO badges (user_id, badge_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (str(user_id), badge_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"[ERROR] Impossible d'attribuer le badge : {e}")
        return False

def get_user_badges(user_id):
    cur.execute("SELECT badge_id FROM badges WHERE user_id = %s", (str(user_id),))
    rows = cur.fetchall()
    return [r[0] for r in rows]
