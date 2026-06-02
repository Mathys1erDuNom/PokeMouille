"""Module centralisé pour gérer la connexion à la base de données."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connexion unique et partagée
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

def get_connection():
    """Retourne la connexion centralisée."""
    global conn
    try:
        conn.isolation_level
    except psycopg2.OperationalError:
        # Reconnexion si la connexion a été fermée
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn

def get_cursor():
    """Retourne le curseur centralisé."""
    return get_connection().cursor()
