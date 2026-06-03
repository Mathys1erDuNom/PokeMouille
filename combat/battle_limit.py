# battle_limit.py
import os
import psycopg2
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def _get_connection():
    """Crée une nouvelle connexion à la base de données."""
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def _init_table():
    """Initialise la table des victoires."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS battle_victories (
            user_id TEXT NOT NULL,
            victory_date DATE NOT NULL,
            victory_count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, victory_date)
        );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la table: {e}")


# Initialiser la table au démarrage
_init_table()


def get_daily_victories(user_id: str) -> int:
    """Retourne le nombre de victoires du jour pour cet utilisateur."""
    user_id = str(user_id)
    today = date.today()
    
    conn = None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT victory_count FROM battle_victories
            WHERE user_id = %s AND victory_date = %s
        """, (user_id, today))
        
        row = cur.fetchone()
        cur.close()
        return row[0] if row else 0
    except Exception as e:
        print(f"Erreur lors de la récupération des victoires: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def increment_daily_victories(user_id: str) -> int:
    """Incrémente les victoires du jour et retourne le nouveau total."""
    user_id = str(user_id)
    today = date.today()
    
    conn = None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO battle_victories (user_id, victory_date, victory_count)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id, victory_date) DO UPDATE SET
                victory_count = victory_count + 1
            RETURNING victory_count
        """, (user_id, today))
        
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row[0] if row else 1
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erreur lors de l'incrémentation des victoires: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def can_battle(user_id: str, max_victories: int = 2) -> tuple[bool, int]:
    """
    Vérifie si l'utilisateur peut combattre aujourd'hui.
    Retourne (peut_combattre, victoires_actuelles)
    """
    user_id = str(user_id)
    try:
        victories = get_daily_victories(user_id)
        return victories < max_victories, victories
    except Exception as e:
        print(f"Erreur lors de la vérification de bataille: {e}")
        return True, 0


def reset_daily_battles():
    """À appeler une fois par jour pour nettoyer les anciennes entrées (optionnel)."""
    # Cette fonction peut être appelée par une tâche automatique
    # pour ne pas laisser la table trop grande
    pass
