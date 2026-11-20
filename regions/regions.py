import os
import psycopg2
import discord
from discord.ui import Select, View
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


# -----------------------
# CONNEXION DATABASE
# -----------------------
def get_connection():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )


# -----------------------
# REGIONS DISPONIBLES
# -----------------------
AVAILABLE_REGIONS = [
    "Kanto",
    "Johto",
    "Hoenn",
    "Sinnoh",
    "Unys",
    "Rocket"
]


# -----------------------
# IMAGES DES REGIONS
# -----------------------
REGION_IMAGES = {
    "Kanto": "images/regions/kanto.png",
    "Johto": "images/regions/johto.png",
    "Hoenn": "images/regions/hoenn.png",
    "Sinnoh": "images/regions/sinnoh.png",
    "Unys": "images/regions/unys.png",
    "Rocket": "images/regions/rocket.png"
}


# -----------------------
# SETUP TABLE
# -----------------------
def setup_regions():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_regions (
                    user_id TEXT PRIMARY KEY,
                    region TEXT
                );
            """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# -----------------------
# SET REGION
# -----------------------
def set_user_region(user_id, region):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_regions (user_id, region)
                VALUES (%s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET region = EXCLUDED.region
            """, (str(user_id), region))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# -----------------------
# GET REGION
# -----------------------
def get_user_region(user_id):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT region
                FROM user_regions
                WHERE user_id = %s
            """, (str(user_id),))

            result = cur.fetchone()

            return result[0] if result else None

    finally:
        conn.close()


# -----------------------
# MENU DÉROULANT
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

        # Enregistrement en DB
        try:
            set_user_region(
                interaction.user.id,
                region
            )

        except Exception as e:
            print(f"[ERROR] Impossible d'enregistrer la région : {e}")

            await interaction.response.send_message(
                "❌ Une erreur est survenue lors de l'enregistrement de ta région.",
                ephemeral=True
            )

            return

        # Réponse éphémère dans le salon
        await interaction.response.send_message(
            f"🌍 Tu es maintenant dans la région **{region}** ! Vérifie tes MPs.",
            ephemeral=True
        )

        # -----------------------
        # ENVOI DU MP
        # -----------------------

        image_path = REGION_IMAGES.get(region)

        try:

            if image_path and os.path.exists(image_path):

                file = discord.File(
                    image_path,
                    filename=f"{region.lower()}.png"
                )

                await interaction.user.send(
                    f"🌍 Bienvenue dans la région **{region}** ! Bonne aventure !",
                    file=file
                )

            else:

                await interaction.user.send(
                    f"🌍 Bienvenue dans la région **{region}** ! Bonne aventure !"
                )

        except discord.Forbidden:

            await interaction.followup.send(
                "⚠️ Je n'ai pas pu t'envoyer un MP. "
                "Vérifie que tes messages privés sont ouverts.",
                ephemeral=True
            )

        except discord.HTTPException as e:

            print(f"[ERROR] Impossible d'envoyer le MP : {e}")


# -----------------------
# VIEW
# -----------------------
class RegionView(View):

    def __init__(self):
        super().__init__(timeout=180)

        self.add_item(
            RegionSelect()
        )


# -----------------------
# COMMANDE
# -----------------------
def setup_region(bot):

    @bot.command()
    async def region(ctx):

        view = RegionView()

        await ctx.send(
            "🌍 Choisis la région où tu veux aller :",
            view=view
        )
