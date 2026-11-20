# money_db.py (migré dans BDD)
from db_connection import get_connection

# Création de la table argent
conn = get_connection()
cur = conn.cursor()

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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT balance FROM argent
        WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    
    if row:
        return row[0]
    else:
        cur.execute("""
            INSERT INTO argent (user_id, balance)
            VALUES (%s, 0)
        """, (user_id,))
        conn.commit()
        return 0


def add_money(user_id, amount):
    """Ajoute de l'argent à un utilisateur."""
    user_id = str(user_id)
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT balance FROM argent
        WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    
    if row:
        new_balance = row[0] + amount
        cur.execute("""
            UPDATE argent SET balance = %s
            WHERE user_id = %s
        """, (new_balance, user_id))
    else:
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
        return False
    
    new_balance = current_balance - amount
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE argent SET balance = %s
        WHERE user_id = %s
    """, (new_balance, user_id))
    conn.commit()
    return True


def set_money(user_id, amount):
    """Définit le solde exact d'un utilisateur."""
    user_id = str(user_id)
    conn = get_connection()
    cur = conn.cursor()
    
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
    
    if not remove_money(from_user_id, amount):
        return False
    add_money(to_user_id, amount)
    return True
