import asyncio
import discord
from discord.ui import View, Button
from PIL import Image, ImageDraw, ImageFont
import requests
import os
import json
import random
from io import BytesIO
from inventory_db import add_item
from money_db import get_balance, remove_money
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur  = conn.cursor()

script_dir = os.path.dirname(os.path.abspath(__file__))
marche_noir_json_path = os.path.join(script_dir, "json","marche_noir", "marche_noir.json")
images_dir = os.path.join(script_dir, "images")
images_json_path = os.path.join(script_dir, "json", "images.json")

# ─── Table pour tracer les achats du marché noir ───────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS marche_noir_purchases (
    user_id TEXT,
    purchase_date DATE,
    item_name TEXT,
    PRIMARY KEY (user_id, purchase_date)
);
""")
conn.commit()

# ─── Chargement des items du marché noir ───────────────────────────────────────
with open(marche_noir_json_path, "r", encoding="utf-8") as f:
    MARCHE_NOIR_ITEMS = json.load(f)

# ─── Chargement des images de fond ────────────────────────────────────────────
try:
    with open(images_json_path, "r", encoding="utf-8") as f:
        IMAGES_DATA = json.load(f)
except Exception as e:
    print(f"[MARCHE NOIR] Erreur lors du chargement de images.json : {e}")
    IMAGES_DATA = {}

# ─── Stock disponible pour cette session ──────────────────────────────────────
# Le marché noir tire aléatoirement N items à chaque ouverture
NB_ITEMS_AFFICHES = 4  # Nombre d'items affichés au marché noir


def has_bought_today(user_id: str) -> bool:
    """Vérifie si l'utilisateur a déjà acheté quelque chose aujourd'hui."""
    user_id = str(user_id)
    today = datetime.now().date()
    cur.execute("""
        SELECT 1 FROM marche_noir_purchases
        WHERE user_id = %s AND purchase_date = %s
        LIMIT 1
    """, (user_id, today))
    return cur.fetchone() is not None


def record_purchase(user_id: str, item_name: str) -> bool:
    """Enregistre un achat pour l'utilisateur aujourd'hui."""
    user_id = str(user_id)
    today = datetime.now().date()
    try:
        cur.execute("""
            INSERT INTO marche_noir_purchases (user_id, purchase_date, item_name)
            VALUES (%s, %s, %s)
        """, (user_id, today, item_name))
        conn.commit()
        return True
    except Exception as e:
        print(f"[MARCHE NOIR] Erreur lors de l'enregistrement de l'achat : {e}")
        conn.rollback()
        return False


# ─── Stock disponible pour cette session ──────────────────────────────────────
# Le marché noir tire aléatoirement N items à chaque ouverture
NB_ITEMS_AFFICHES = 4  # Nombre d'items affichés au marché noir


def get_stock_du_jour():
    """Tire aléatoirement des items parmi ceux du marché noir."""
    nb = min(NB_ITEMS_AFFICHES, len(MARCHE_NOIR_ITEMS))
    return random.sample(MARCHE_NOIR_ITEMS, nb)


# ─── Vue principale du marché noir ────────────────────────────────────────────
class MarcheNoirView(View):
    def __init__(self, user_id, stock):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.stock = stock
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        for item in self.stock:
            self.add_item(MarcheNoirItemButton(item, self.user_id))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ─── Bouton par item ───────────────────────────────────────────────────────────
class MarcheNoirItemButton(Button):
    def __init__(self, item, user_id):
        rarity_emoji = {
            "common":    "⚪",
            "uncommon":  "🟢",
            "rare":      "🔵",
            "epic":      "🟣",
            "legendary": "🟡"
        }
        emoji = rarity_emoji.get(item.get("rarity", "common").lower(), "⚪")

        super().__init__(
            label=f"{emoji} {item.get('item_name', 'Inconnu')} — {item.get('price', 0):,}💰",
            style=discord.ButtonStyle.danger  # Rouge pour l'ambiance underground
        )
        self.item = item
        self.user_id = user_id

    def resize_keep_aspect(self, img, max_size):
        w, h = img.size
        ratio = min(max_size / w, max_size / h)
        return img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        name        = self.item["item_name"]
        price       = self.item["price"]
        rarity      = self.item.get("rarity", "common")
        description = self.item.get("description", "Aucune description.")
        image_url   = self.item.get("image", "")
        balance     = await asyncio.to_thread(get_balance, self.user_id)

        # Couleurs par rareté
        rarity_colors = {
            "common":    (200, 200, 200),
            "uncommon":  (50, 205, 50),
            "rare":      (30, 144, 255),
            "epic":      (138, 43, 226),
            "legendary": (255, 215, 0)
        }
        rarity_color = rarity_colors.get(rarity.lower(), (200, 200, 200))

        width, height = 850, 600

        # ── Fond ────────────────────────────────────────────────────────────────
        background = None
        fond_url = (
            IMAGES_DATA.get("fond_marche_noir")
            or IMAGES_DATA.get("fond_shop")
            or IMAGES_DATA.get("background")
        )

        if fond_url and fond_url.startswith("http"):
            try:
                resp = requests.get(fond_url, timeout=5)
                resp.raise_for_status()
                background = Image.open(BytesIO(resp.content)).convert("RGBA")
                background = background.resize((width, height), Image.Resampling.LANCZOS)
            except Exception as e:
                print(f"[MARCHE NOIR] Erreur fond URL : {e}")

        if background is None:
            try:
                background = Image.open(
                    os.path.join(images_dir, "marche_noir", "marche_noir.png")
                ).convert("RGBA")
                background = background.resize((width, height), Image.Resampling.LANCZOS)
            except Exception:
                # Fond sombre par défaut, ambiance underground
                background = Image.new("RGBA", (width, height), (20, 20, 20, 255))

        draw = ImageDraw.Draw(background)

        # ── Polices ─────────────────────────────────────────────────────────────
        font_path_bold = os.path.join(script_dir, "fonts", "DejaVuSans-Bold.ttf")
        try:
            font_title  = ImageFont.truetype(font_path_bold, 28)
            font_normal = ImageFont.truetype(font_path_bold, 18)
            font_small  = ImageFont.truetype(font_path_bold, 16)
        except Exception:
            font_title = font_normal = font_small = ImageFont.load_default()

        # ── Textes ──────────────────────────────────────────────────────────────
        draw.text((540, 115), name,                                     font=font_title,  fill="white")
        draw.text((450, 340), f"Rareté : {rarity.capitalize()}",        font=font_normal, fill="white")
        draw.text((450, 380), f"Prix : {price:,} Croco dollars",        font=font_normal, fill="white")

        balance_color = (50, 205, 50) if balance >= price else (255, 69, 0)
        draw.text((450, 420), f"Votre solde : {balance:,} Croco dollars", font=font_normal, fill=balance_color)

        # Description multi-lignes
        x, y = 450, 460
        draw.text((x, y), "Description :", font=font_normal, fill="white")
        y += 30

        words, lines, current_line = description.split(), [], ""
        for word in words:
            test = current_line + word + " "
            if len(test) * 10 < 350:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())

        for line in lines[:4]:
            draw.text((x, y), line, font=font_small, fill="white")
            y += 25

        # ── Image de l'item ─────────────────────────────────────────────────────
        if image_url:
            try:
                if image_url.startswith("http"):
                    # URL distante
                    resp = requests.get(image_url, timeout=5)
                    resp.raise_for_status()
                    item_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                else:
                    # Chemin local relatif au dossier du script
                    local_path = os.path.join(script_dir, image_url)
                    item_img = Image.open(local_path).convert("RGBA")

                item_img = self.resize_keep_aspect(item_img, 200)
                img_x = 530 + (200 - item_img.width) // 2
                background.paste(item_img, (img_x, 140), item_img)
            except Exception as e:
                print(f"[MARCHE NOIR] Erreur image item : {e}")

        # ── Envoi ────────────────────────────────────────────────────────────────
        with BytesIO() as buffer:
            background.save(buffer, "PNG")
            buffer.seek(0)
            file = discord.File(buffer, filename="marche_noir_card.png")

        embed = discord.Embed(
            title=f"🖤 {name}",
            color=discord.Color.from_rgb(*rarity_color)
        )
        embed.set_image(url="attachment://marche_noir_card.png")

        view = View()
        view.add_item(AcheterMarcheNoirButton(self.item, self.user_id))

        await interaction.followup.send(file=file, embed=embed, view=view, ephemeral=True)


# ─── Bouton d'achat ───────────────────────────────────────────────────────────
class AcheterMarcheNoirButton(Button):
    def __init__(self, item, user_id):
        super().__init__(label="🖤 Acheter (marché noir)", style=discord.ButtonStyle.danger)
        self.item    = item
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Vérifie si l'utilisateur a déjà acheté aujourd'hui
        if await asyncio.to_thread(has_bought_today, self.user_id):
            await interaction.followup.send(
                f"❌ Tu as déjà acheté quelque chose au marché noir aujourd'hui.\n"
                f"🔄 Reviens demain pour continuer tes achats secrets !",
                ephemeral=True
            )
            return

        price   = self.item.get("price", 0)
        name    = self.item["item_name"]
        balance = await asyncio.to_thread(get_balance, self.user_id)

        if balance < price:
            await interaction.followup.send(
                f"❌ Pas assez de fonds ! Il te faut **{price:,}** Croco dollars "
                f"mais tu n'as que **{balance:,}**.\n"
                f"💸 Manquant : **{price - balance:,}** Croco dollars.",
                ephemeral=True
            )
            return

        success = await asyncio.to_thread(remove_money, self.user_id, price)
        if not success:
            await interaction.followup.send("❌ Erreur lors de la transaction.", ephemeral=True)
            return

        await asyncio.to_thread(
            add_item,
            self.user_id,
            self.item["item_name"],
            1,
            self.item.get("rarity", "common"),
            self.item.get("description", ""),
            self.item.get("image", ""),
            self.item.get("extra"),
            self.item.get("price", 0)
        )

        # Enregistre l'achat pour aujourd'hui
        await asyncio.to_thread(record_purchase, self.user_id, name)

        new_balance = await asyncio.to_thread(get_balance, self.user_id)
        await interaction.followup.send(
            f"🖤 Transaction secrète effectuée...\n"
            f"🎁 Vous avez obtenu **{name}** pour **{price:,}** Croco dollars.\n"
            f"💰 Solde restant : **{new_balance:,}** Croco dollars.\n"
            f"*Pas un mot à personne.*",
            ephemeral=True
        )


# ─── Fonction standalone appelable sans contexte ───────────────────────────
async def run_marche_noir(channel, user_id=None):
    """Lance le marché noir directement dans un salon Discord donné."""
    if user_id is None:
        user_id = channel.guild.owner_id
    
    balance = await asyncio.to_thread(get_balance, user_id)
    stock   = get_stock_du_jour()

    embed = discord.Embed(
        title="🖤 Marché Noir",
        description=(
            f"*Chut... t'as pas vu ça ici.*\n\n"
            f"💰 Votre solde : **{balance:,}** Croco dollars\n"
            f"🎲 Stock limité — **{len(stock)} article(s)** disponible(s) aujourd'hui.\n\n"
            "Cliquez sur un article pour voir les détails."
        ),
        color=discord.Color.dark_gray()
    )

    view = MarcheNoirView(user_id, stock)
    await channel.send(embed=embed, view=view)


# ─── Setup ────────────────────────────────────────────────────────────────────
def setup_marche_noir(bot):
    """Enregistre la commande !marchenoir sur le bot."""

    @bot.command(name="marchenoir")
    async def marche_noir(ctx):
        """Ouvre le marché noir — stock limité et aléatoire."""
        await run_marche_noir(ctx.channel, ctx.author.id)

    # Expose run_marche_noir pour pouvoir l'importer / l'appeler depuis le main
    bot.run_marche_noir = run_marche_noir