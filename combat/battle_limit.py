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
    """Initialise la table des tentatives de combat."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS battle_attempts (
            user_id TEXT NOT NULL,
            attempt_date DATE NOT NULL,
            attempt_count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, attempt_date)
        );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la table: {e}")


# Initialiser la table au démarrage
_init_table()


def get_daily_attempts(user_id: str) -> int:
    """Retourne le nombre de tentatives de combat du jour pour cet utilisateur."""
    user_id = str(user_id)
    today = date.today()
    
    conn = None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT attempt_count FROM battle_attempts
            WHERE user_id = %s AND attempt_date = %s
        """, (user_id, today))
        
        row = cur.fetchone()
        cur.close()
        return row[0] if row else 0
    except Exception as e:
        print(f"Erreur lors de la récupération des tentatives: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def increment_daily_attempts(user_id: str) -> int:
    """Incrémente les tentatives du jour et retourne le nouveau total."""
    user_id = str(user_id)
    today = date.today()
    
    conn = None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO battle_attempts (user_id, attempt_date, attempt_count)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id, attempt_date) DO UPDATE SET
                attempt_count = battle_attempts.attempt_count + 1
            RETURNING battle_attempts.attempt_count
        """, (user_id, today))
        
        
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row[0] if row else 1
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erreur lors de l'incrémentation des tentatives: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def can_battle(user_id: str, max_attempts: int = 3) -> tuple[bool, int]:
    """
    Vérifie si l'utilisateur peut combattre aujourd'hui.
    Limite: 3 tentatives par jour, reset à 00h.
    Retourne (peut_combattre, tentatives_actuelles)
    """
    user_id = str(user_id)
    try:
        attempts = get_daily_attempts(user_id)
        return attempts < max_attempts, attempts
    except Exception as e:
        print(f"Erreur lors de la vérification de bataille: {e}")
        return True, 0


def reset_daily_battles():
    """À appeler une fois par jour pour nettoyer les anciennes entrées (optionnel)."""
    # Cette fonction peut être appelée par une tâche automatique
    # pour ne pas laisser la table trop grande
    pass



def increment_daily_victories(user_id: str) -> int:
    """
    Alias pour incrémenter les victoires du jour.
    Réutilise la même table battle_attempts.
    """
    return increment_daily_attempts(user_id)