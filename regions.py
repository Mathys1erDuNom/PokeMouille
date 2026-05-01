import os
import psycopg2
import discord
from discord.ui import Select, View
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS user_regions;")
conn.commit()

# -----------------------
# REGIONS DISPONIBLES
# -----------------------
AVAILABLE_REGIONS = [
    "Kanto",
    "Johto",
    "Hoenn",
    "Sinnoh",
    "Unys"
]

# Image associée à chaque région
REGION_IMAGES = {
    "Kanto": "images/regions/kanto.png",
    "Johto": "images/regions/johto.png",
    "Hoenn": "images/regions/hoenn.png",
    "Sinnoh": "images/regions/sinnoh.png",
    "Unys":  "images/regions/unys.png",
}

# -----------------------
# SETUP TABLE
# -----------------------
def setup_regions():
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
        SELECT region FROM user_regions WHERE user_id = %s
    """, (str(user_id),))
    result = cur.fetchone()
    return result[0] if result else None

# -----------------------
# MENU DÉROULANT
# -----------------------
class RegionSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=region, description=f"Aller dans {region}")
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

        # Réponse éphémère dans le salon
        await interaction.response.send_message(
            f"🌍 Tu es maintenant dans la région **{region}** ! Vérifie tes MPs.",
            ephemeral=True
        )

        # Envoi du MP avec l'image
        image_path = REGION_IMAGES.get(region)
        try:
            if image_path and os.path.exists(image_path):
                file = discord.File(image_path, filename=f"{region.lower()}.png")
                await interaction.user.send(
                    f"🌍 Bienvenue dans la région **{region}** ! Bonne aventure !",
                    file=file
                )
            else:
                # Pas d'image trouvée, on envoie juste le texte
                await interaction.user.send(
                    f"🌍 Bienvenue dans la région **{region}** ! Bonne aventure !"
                )
        except discord.Forbidden:
            # L'utilisateur a ses MPs fermés
            await interaction.followup.send(
                "⚠️ Je n'ai pas pu t'envoyer un MP. Vérifie que tes messages privés sont ouverts.",
                ephemeral=True
            )

class RegionView(View):
    def __init__(self):
        super().__init__()
        self.add_item(RegionSelect())

# -----------------------
# COMMANDE
# -----------------------
def setup_region(bot):
    @bot.command()
    async def region(ctx):
        view = RegionView()
        await ctx.send("🌍 Choisis la région où tu veux aller :", view=view)