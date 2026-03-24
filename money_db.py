# money_db.py
import os
import psycopg2
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connexion globale à la base
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()



# Création de la table argent
cur.execute("""
CREATE TABLE IF NOT EXISTS argent (
    user_id TEXT PRIMARY KEY,
    balance INTEGER DEFAULT 0
);
""")
conn.commit()


def get_balance(user_id):
    """Retourne le solde d'un utilisateur."""
    user_id = str(user_id)
    cur.execute("""
        SELECT balance FROM argent
        WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    
    if row:
        return row[0]
    else:
        # Si l'utilisateur n'existe pas, on le crée avec 0
        cur.execute("""
            INSERT INTO argent (user_id, balance)
            VALUES (%s, 0)
        """, (user_id,))
        conn.commit()
        return 0


def add_money(user_id, amount):
    """Ajoute de l'argent à un utilisateur."""
    user_id = str(user_id)
    
    # Vérifie si l'utilisateur existe
    cur.execute("""
        SELECT balance FROM argent
        WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    
    if row:
        # Mise à jour
        new_balance = row[0] + amount
        cur.execute("""
            UPDATE argent SET balance = %s
            WHERE user_id = %s
        """, (new_balance, user_id))
    else:
        # Insertion
        cur.execute("""
            INSERT INTO argent (user_id, balance)
            VALUES (%s, %s)
        """, (user_id, amount))
    
    conn.commit()
    return get_balance(user_id)


def remove_money(user_id, amount):
    """Retire de l'argent à un utilisateur. Retourne False si solde insuffisant."""
    user_id = str(user_id)
    current_balance = get_balance(user_id)
    
    if current_balance < amount:
        return False  # Solde insuffisant
    
    new_balance = current_balance - amount
    cur.execute("""
        UPDATE argent SET balance = %s
        WHERE user_id = %s
    """, (new_balance, user_id))
    conn.commit()
    return True


def set_money(user_id, amount):
    """Définit le solde exact d'un utilisateur."""
    user_id = str(user_id)
    
    cur.execute("""
        SELECT balance FROM argent
        WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    
    if row:
        cur.execute("""
            UPDATE argent SET balance = %s
            WHERE user_id = %s
        """, (amount, user_id))
    else:
        cur.execute("""
            INSERT INTO argent (user_id, balance)
            VALUES (%s, %s)
        """, (user_id, amount))
    
    conn.commit()
    return amount


def transfer_money(from_user_id, to_user_id, amount):
    """Transfère de l'argent entre deux utilisateurs."""
    from_user_id = str(from_user_id)
    to_user_id = str(to_user_id)
    
    # Vérifie le solde de l'expéditeur
    if not remove_money(from_user_id, amount):
        return False  # Solde insuffisant
    
    # Ajoute à l'utilisateur destinataire
    add_money(to_user_id, amount)
    return True