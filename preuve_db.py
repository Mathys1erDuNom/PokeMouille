import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_preuves_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS preuves (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    region TEXT NOT NULL,
                    description TEXT,
                    image TEXT,
                    obtained_at TIMESTAMP DEFAULT NOW()
                )
            """)
        conn.commit()

def add_preuve(user_id, item_name, region, description="", image=""):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO preuves (user_id, item_name, region, description, image)
                VALUES (%s, %s, %s, %s, %s)
            """, (str(user_id), item_name, region, description, image))
        conn.commit()

def get_preuves(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT item_name, region, description, image, obtained_at
                FROM preuves
                WHERE user_id = %s
                ORDER BY obtained_at ASC
            """, (str(user_id),))
            rows = cur.fetchall()
    return [
        {
            "item_name": row[0],
            "region": row[1],
            "description": row[2],
            "image": row[3],
            "obtained_at": row[4]
        }
        for row in rows
    ]

def delete_preuves(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM preuves WHERE user_id = %s", (str(user_id),))
        conn.commit()

def has_preuve(user_id, item_name):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM preuves
                WHERE user_id = %s AND item_name = %s
            """, (str(user_id), item_name))
            return cur.fetchone() is not None
        

        