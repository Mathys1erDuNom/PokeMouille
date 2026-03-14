import os
import psycopg2
import discord
from discord.ui import Select, View
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()


# -----------------------
# REGIONS DISPONIBLES
# -----------------------

AVAILABLE_REGIONS = [
    "Kanto",
    "Johto",
    "Hoenn",
    "Sinnoh",
    "Unys",
    "Kalos",
    "Alola",
    "Galar",
    "Paldea"
]


# -----------------------
# SETUP TABLE
# -----------------------

def setup_regions():
    """Crée la table si elle n'existe pas"""

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_regions (
        user_id TEXT PRIMARY KEY,
        region TEXT
    );
    """)

    conn.commit()


# -----------------------
# SET REGION
# -----------------------

def set_user_region(user_id, region):

    cur.execute("""
        INSERT INTO user_regions (user_id, region)
        VALUES (%s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET region = EXCLUDED.region
    """, (str(user_id), region))

    conn.commit()


# -----------------------
# GET REGION
# -----------------------

def get_user_region(user_id):

    cur.execute("""
        SELECT region
        FROM user_regions
        WHERE user_id = %s
    """, (str(user_id),))

    result = cur.fetchone()

    if result:
        return result[0]

    return None


# -----------------------
# MENU DEROUlant
# -----------------------

class RegionSelect(Select):

    def __init__(self):

        options = [
            discord.SelectOption(
                label=region,
                description=f"Aller dans {region}"
            )
            for region in AVAILABLE_REGIONS
        ]

        super().__init__(
            placeholder="Choisis ta région",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        region = self.values[0]

        set_user_region(interaction.user.id, region)

        await interaction.response.send_message(
            f"🌍 Tu es maintenant dans la région **{region}**",
            ephemeral=True
        )


class RegionView(View):

    def __init__(self):
        super().__init__()
        self.add_item(RegionSelect())


# -----------------------
# COMMANDE
# -----------------------

async def region_command(ctx):

    view = RegionView()

    await ctx.send(
        "🌍 Choisis la région où tu veux aller :",
        view=view
    )