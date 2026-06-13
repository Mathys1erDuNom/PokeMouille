import asyncio
import discord
from discord.ui import View, Button, Select
from PIL import Image, ImageDraw, ImageFont
import requests
import os
import json
from io import BytesIO
from inventory_db import delete_inventory, get_inventory  # adapte si tes fonctions s'appellent autrement
from money_db import get_balance, add_money
from db_connection import get_connection

script_dir = os.path.dirname(os.path.abspath(__file__))
receleur_json_path = os.path.join(script_dir, "json", "receleur.json")
images_dir = os.path.join(script_dir, "images")
images_json_path = os.path.join(script_dir, "json", "images.json")

# ─── Chargement des prix de rachat ────────────────────────────────────────────
with open(receleur_json_path, "r", encoding="utf-8") as f:
    RECELEUR_PRIX = json.load(f)  # { "item_name": prix_rachat, ... }

# ─── Chargement des images de fond ────────────────────────────────────────────
try:
    with open(images_json_path, "r", encoding="utf-8") as f:
        IMAGES_DATA = json.load(f)
except Exception as e:
    print(f"[RECELEUR] Erreur lors du chargement de images.json : {e}")
    IMAGES_DATA = {}


def get_items_vendables(user_id: str) -> list[dict]:
    """
    Récupère les items de l'inventaire du joueur
    qui figurent dans receleur.json (donc revendables).
    Retourne une liste de dicts avec les infos enrichies du prix de rachat.
    """
    inventory = get_inventory(user_id)  # liste de dicts : item_name, quantity, rarity, description, image, price...
    vendables = []
    for item in inventory:
        name = item.get("item_name") or item.get("name", "")
        if name in RECELEUR_PRIX:
            vendables.append({
                **item,
                "item_name": name,
                "rachat_price": RECELEUR_PRIX[name]
            })
    return vendables


# ─── Vue d'introduction ───────────────────────────────────────────────────────
class ReceleurIntroView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🤫 Parler au receleur", style=discord.ButtonStyle.secondary)
    async def entrer(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        try:
            user_id = str(interaction.user.id)
            balance = await asyncio.to_thread(get_balance, user_id)
            items_vendables = await asyncio.to_thread(get_items_vendables, user_id)

            if not items_vendables:
                await interaction.followup.send(
                    "❌ T'as rien que j'veux... Reviens quand t'as des trucs intéressants.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="🤫 Receleur",
                description=(
                    f"*Il t'examine d'un œil méfiant...*\n\n"
                    f"💰 Votre solde : **{balance:,}** Croco dollars\n"
                    f"🎒 **{len(items_vendables)}** article(s) dans ton sac m'intéressent.\n\n"
                    "Sélectionne un article à me vendre."
                ),
                color=discord.Color.from_rgb(80, 50, 20)
            )

            view = ReceleurSelectView(user_id, items_vendables)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"[RECELEUR] Erreur dans entrer() : {e}")
            import traceback; traceback.print_exc()
            try:
                await interaction.followup.send("❌ Une erreur est survenue.", ephemeral=True)
            except Exception:
                pass


# ─── Vue avec Select menu ─────────────────────────────────────────────────────
class ReceleurSelectView(View):
    def __init__(self, user_id: str, items: list[dict]):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.items = items
        self._build_select()

    def _build_select(self):
        self.clear_items()

        rarity_emoji = {
            "common":    "⚪",
            "uncommon":  "🟢",
            "rare":      "🔵",
            "epic":      "🟣",
            "legendary": "🟡"
        }

        options = []
        for item in self.items[:25]:  # limite Discord
            name     = item["item_name"]
            qty      = item.get("quantity", 1)
            rarity   = item.get("rarity", "common").lower()
            emoji    = rarity_emoji.get(rarity, "⚪")
            prix     = item["rachat_price"]
            label    = f"{name} (x{qty})"[:100]
            desc     = f"Rachat : {prix:,} 💰 — Rareté : {rarity.capitalize()}"[:100]

            options.append(discord.SelectOption(
                label=label,
                value=name,
                description=desc,
                emoji=emoji
            ))

        select = Select(
            placeholder="Choisis un item à vendre...",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        item_name = interaction.data["values"][0]
        item = next((i for i in self.items if i["item_name"] == item_name), None)
        if not item:
            await interaction.followup.send("❌ Item introuvable.", ephemeral=True)
            return

        # Génère la carte de détail
        file, embed, view = await asyncio.to_thread(
            build_item_card, item, self.user_id
        )
        await interaction.followup.send(file=file, embed=embed, view=view, ephemeral=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


# ─── Génération de la carte item ──────────────────────────────────────────────
def build_item_card(item: dict, user_id: str):
    """
    Génère l'image PIL de la fiche item + l'embed + la vue avec le bouton de vente.
    Exécuté dans un thread séparé (asyncio.to_thread).
    """
    name        = item["item_name"]
    rachat      = item["rachat_price"]
    rarity      = item.get("rarity", "common").lower()
    description = item.get("description", "Aucune description.")
    image_url   = item.get("image", "")
    quantity    = item.get("quantity", 1)
    balance     = get_balance(user_id)

    rarity_colors = {
        "common":    (200, 200, 200),
        "uncommon":  (50, 205, 50),
        "rare":      (30, 144, 255),
        "epic":      (138, 43, 226),
        "legendary": (255, 215, 0)
    }
    rarity_color = rarity_colors.get(rarity, (200, 200, 200))

    width, height = 850, 600

    # ── Fond ──────────────────────────────────────────────────────────────────
    background = None
    fond_url = (
        IMAGES_DATA.get("fond_receleur")
        or IMAGES_DATA.get("fond_marche_noir")
        or IMAGES_DATA.get("fond_shop")
    )

    if fond_url and fond_url.startswith("http"):
        try:
            resp = requests.get(fond_url, timeout=5)
            resp.raise_for_status()
            background = Image.open(BytesIO(resp.content)).convert("RGBA")
            background = background.resize((width, height), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"[RECELEUR] Erreur fond URL : {e}")

    if background is None:
        try:
            background = Image.open(
                os.path.join(images_dir, "receleur", "receleur.png")
            ).convert("RGBA")
            background = background.resize((width, height), Image.Resampling.LANCZOS)
        except Exception:
            background = Image.new("RGBA", (width, height), (30, 20, 10, 255))

    draw = ImageDraw.Draw(background)

    # ── Polices ───────────────────────────────────────────────────────────────
    font_path_bold = os.path.join(script_dir, "fonts", "DejaVuSans-Bold.ttf")
    try:
        font_title  = ImageFont.truetype(font_path_bold, 28)
        font_normal = ImageFont.truetype(font_path_bold, 18)
        font_small  = ImageFont.truetype(font_path_bold, 16)
    except Exception:
        font_title = font_normal = font_small = ImageFont.load_default()

    # ── Textes ────────────────────────────────────────────────────────────────
    draw.text((540, 115), name,                                          font=font_title,  fill="white")
    draw.text((450, 320), f"Rareté : {rarity.capitalize()}",            font=font_normal, fill="white")
    draw.text((450, 360), f"Quantité possédée : {quantity}",            font=font_normal, fill="white")
    draw.text((450, 400), f"Rachat : {rachat:,} Croco dollars",         font=font_normal, fill=(255, 215, 0))

    balance_color = (50, 205, 50)
    draw.text((450, 440), f"Votre solde : {balance:,} Croco dollars",  font=font_normal, fill=balance_color)

    # Description multi-lignes
    x, y = 450, 480
    draw.text((x, y), "Description :", font=font_normal, fill="white")
    y += 28
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
    for line in lines[:3]:
        draw.text((x, y), line, font=font_small, fill="white")
        y += 24

    # ── Image de l'item ───────────────────────────────────────────────────────
    if image_url:
        try:
            if image_url.startswith("http"):
                resp = requests.get(image_url, timeout=5)
                resp.raise_for_status()
                item_img = Image.open(BytesIO(resp.content)).convert("RGBA")
            else:
                item_img = Image.open(os.path.join(script_dir, image_url)).convert("RGBA")

            # resize proportionnel
            w, h = item_img.size
            ratio = min(200 / w, 200 / h)
            item_img = item_img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
            img_x = 530 + (200 - item_img.width) // 2
            background.paste(item_img, (img_x, 140), item_img)
        except Exception as e:
            print(f"[RECELEUR] Erreur image item : {e}")

    # ── Fichier Discord ───────────────────────────────────────────────────────
    buffer = BytesIO()
    background.save(buffer, "PNG")
    buffer.seek(0)
    file = discord.File(buffer, filename="receleur_card.png")

    embed = discord.Embed(
        title=f"🤫 {name}",
        color=discord.Color.from_rgb(*rarity_color)
    )
    embed.set_image(url="attachment://receleur_card.png")

    view = View()
    view.add_item(VendreButton(item, user_id))

    return file, embed, view


# ─── Bouton de vente ──────────────────────────────────────────────────────────
class VendreButton(Button):
    def __init__(self, item: dict, user_id: str):
        super().__init__(
            label=f"💸 Vendre — {item['rachat_price']:,} 💰",
            style=discord.ButtonStyle.success
        )
        self.item    = item
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        name     = self.item["item_name"]
        rachat   = self.item["rachat_price"]
        quantity = self.item.get("quantity", 1)

        # Retire 1 exemplaire de l'inventaire
        success_remove = await asyncio.to_thread(delete_inventory, self.user_id, name, 1)
        if not success_remove:
            await interaction.followup.send(
                "❌ Impossible de retirer l'item de ton inventaire. Tu l'as encore ?",
                ephemeral=True
            )
            return

        # Crédite l'argent
        await asyncio.to_thread(add_money, self.user_id, rachat)
        new_balance = await asyncio.to_thread(get_balance, self.user_id)

        await interaction.followup.send(
            f"🤝 Marché conclu dans l'ombre...\n"
            f"📦 Tu as vendu **{name}** pour **{rachat:,}** Croco dollars.\n"
            f"💰 Nouveau solde : **{new_balance:,}** Croco dollars.\n"
            f"*Bonne journée... et t'as rien vu.*",
            ephemeral=True
        )


# ─── Entrée publique ──────────────────────────────────────────────────────────
async def run_receleur(channel, user_id=None):
    """Affiche le message public d'intro du receleur."""
    embed = discord.Embed(
        title="🤫 Receleur",
        description=(
            "*Un homme dans l'ombre te fait signe discrètement...*\n\n"
            "Il rachète ce que tu n'utilises plus. Pas de questions posées.\n"
            "🎒 Montre-lui ce que tu as."
        ),
        color=discord.Color.from_rgb(80, 50, 20)
    )
    view = ReceleurIntroView()
    await channel.send(embed=embed, view=view)


# ─── Setup ────────────────────────────────────────────────────────────────────
def setup_receleur(bot):
    """Enregistre la commande !receleur sur le bot."""

    @bot.command(name="receleur")
    async def receleur(ctx):
        """Ouvre le receleur — vends tes items contre des Croco dollars."""
        await run_receleur(ctx.channel, ctx.author.id)

    bot.run_receleur = run_receleur