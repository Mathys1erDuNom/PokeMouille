# battle_limit.py
import os
import psycopg2
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Création de la table pour tracker les victoires quotidiennes
cur.execute("""
CREATE TABLE IF NOT EXISTS battle_victories (
    user_id TEXT NOT NULL,
    victory_date DATE NOT NULL,
    victory_count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, victory_date)
);
""")
conn.commit()


def get_daily_victories(user_id: str) -> int:
    """Retourne le nombre de victoires du jour pour cet utilisateur."""
    user_id = str(user_id)
    today = date.today()
    
    cur.execute("""
        SELECT victory_count FROM battle_victories
        WHERE user_id = %s AND victory_date = %s
    """, (user_id, today))
    
    row = cur.fetchone()
    return row[0] if row else 0


def increment_daily_victories(user_id: str) -> int:
    """Incrémente les victoires du jour et retourne le nouveau total."""
    user_id = str(user_id)
    today = date.today()
    
    cur.execute("""
        INSERT INTO battle_victories (user_id, victory_date, victory_count)
        VALUES (%s, %s, 1)
        ON CONFLICT (user_id, victory_date) DO UPDATE SET
            victory_count = victory_count + 1
        RETURNING victory_count
    """, (user_id, today))
    
    conn.commit()
    row = cur.fetchone()
    return row[0] if row else 1


def can_battle(user_id: str, max_victories: int = 2) -> tuple[bool, int]:
    """
    Vérifie si l'utilisateur peut combattre aujourd'hui.
    Retourne (peut_combattre, victoires_actuelles)
    """
    user_id = str(user_id)
    victories = get_daily_victories(user_id)
    return victories < max_victories, victories


def reset_daily_battles():
    """À appeler une fois par jour pour nettoyer les anciennes entrées (optionnel)."""
    # Cette fonction peut être appelée par une tâche automatique
    # pour ne pas laisser la table trop grande
    pass
