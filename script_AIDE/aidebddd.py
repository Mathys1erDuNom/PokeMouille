import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # Charge le DATABASE_URL depuis ton .env
DATABASE_URL = os.getenv("postgresql://postgres:EilXxALETOCxwXmbAWTzDAmTJLphQOVk@postgres.railway.internal:5432/railway")

try:
    # Connexion à la base
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    print("[INFO] Connexion réussie à la base PostgreSQL.")

    # Étape 1 : Supprimer l'ancienne clé primaire si elle existe
    cur.execute("""
        ALTER TABLE new_captures
        DROP CONSTRAINT IF EXISTS new_captures_pkey;
    """)
    print("[INFO] Ancienne clé primaire supprimée (si elle existait).")

    # Étape 2 : Créer la nouvelle clé primaire composite (user_id + name)
    cur.execute("""
        ALTER TABLE new_captures
        ADD PRIMARY KEY (user_id, name);
    """)
    print("[INFO] Nouvelle clé primaire (user_id, name) créée.")

    # Commit des changements
    conn.commit()

except Exception as e:
    print(f"[ERREUR] {e}")

finally:
    cur.close()
    conn.close()
    print("[INFO] Connexion fermée.")
