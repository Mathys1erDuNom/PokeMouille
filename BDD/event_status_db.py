import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Une ligne par événement. Ex : ("rocket", TRUE)
cur.execute("""
CREATE TABLE IF NOT EXISTS event_status (
    event_name TEXT PRIMARY KEY,
    active     BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ends_at    TIMESTAMPTZ            -- NULL = pas de fin automatique
);
""")
cur.execute("ALTER TABLE event_status ADD COLUMN IF NOT EXISTS ends_at TIMESTAMPTZ;")
cur.execute("ALTER TABLE event_status ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;")
conn.commit()


def get_event_started_at(event_name: str):
    """Dernière fois que l'event a été activé (None si jamais)."""
    cur.execute("SELECT started_at FROM event_status WHERE event_name = %s", (event_name,))
    row = cur.fetchone()
    return row[0] if row else None


def is_event_active(event_name: str) -> bool:
    cur.execute("""
        SELECT active AND (ends_at IS NULL OR ends_at > now())
        FROM event_status WHERE event_name = %s
    """, (event_name,))
    row = cur.fetchone()
    return bool(row and row[0])


def set_event_active(event_name: str, active: bool, ends_at=None) -> None:
    cur.execute("""
        INSERT INTO event_status (event_name, active, updated_at, ends_at, started_at)
        VALUES (%s, %s, now(), %s, CASE WHEN %s THEN now() END)
        ON CONFLICT (event_name) DO UPDATE
        SET active = EXCLUDED.active,
            updated_at = now(),
            ends_at = EXCLUDED.ends_at,
            started_at = CASE WHEN EXCLUDED.active THEN now() ELSE event_status.started_at END
    """, (event_name, active, ends_at, active))
    conn.commit()
