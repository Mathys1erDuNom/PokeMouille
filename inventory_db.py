# inventory_db.py
import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# Charge les variables d’environnement
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Connexion globale à la base
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Création de la table inventaire
cur.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    user_id TEXT,
    item_name TEXT,
    quantity INTEGER,
    rarity TEXT,
    description TEXT,
    image TEXT,
    extra JSONB
);
""")
conn.commit()


def add_item(user_id, name, quantity=1, rarity="commun", description="", image="", extra=None):
    """Ajoute un item à l’inventaire ou augmente sa quantité."""
    user_id = str(user_id)

    # Vérifie si l’item existe déjà
    cur.execute("""
        SELECT quantity FROM inventory
        WHERE user_id = %s AND item_name = %s
    """, (user_id, name))
    row = cur.fetchone()

    if row:  # Mise à jour
        new_qty = row[0] + quantity
        cur.execute("""
            UPDATE inventory SET quantity = %s
            WHERE user_id = %s AND item_name = %s
        """, (new_qty, user_id, name))
    else:  # Insertion
        cur.execute("""
            INSERT INTO inventory (user_id, item_name, quantity, rarity, description, image, extra)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, name, quantity, rarity, description, image, Json(extra or {})
        ))

    conn.commit()


def get_inventory(user_id):
    """Retourne tout l’inventaire du joueur."""
    cur.execute("""
        SELECT item_name, quantity, rarity, description, image, extra
        FROM inventory
        WHERE user_id = %s
        ORDER BY item_name ASC
    """, (str(user_id),))

    rows = cur.fetchall()
    items = []

    for row in rows:
        items.append({
            "name": row[0],
            "quantity": row[1],
            "rarity": row[2],
            "description": row[3],
            "image": row[4],
            "extra": row[5],
        })

    return items

def delete_inventory(user_id):
    """Supprime tous les items d'un utilisateur."""
    cur.execute("""
        DELETE FROM inventory
        WHERE user_id = %s
    """, (str(user_id),))
    conn.commit()



def use_item(user_id, name, amount=1):
    """Diminue la quantité d'un item. Supprime l'item si quantité ≤ 0."""
    user_id = str(user_id)
    cur.execute("""
        SELECT quantity FROM inventory
        WHERE user_id = %s AND item_name = %s
    """, (user_id, name))
    row = cur.fetchone()

    if not row:
        return False  # L'item n'existe pas

    new_qty = row[0] - amount
    if new_qty > 0:
        cur.execute("""
            UPDATE inventory SET quantity = %s
            WHERE user_id = %s AND item_name = %s
        """, (new_qty, user_id, name))
    else:
        cur.execute("""
            DELETE FROM inventory
            WHERE user_id = %s AND item_name = %s
        """, (user_id, name))

    conn.commit()
    return True
