import discord
from discord.ui import View, Button
from PIL import Image, ImageDraw, ImageFont
import requests
import os
import json
from io import BytesIO
from inventory_db import add_item
from money_db import get_balance, remove_money

script_dir = os.path.dirname(os.path.abspath(__file__))
item_json_path = os.path.join(script_dir, "json", "item.json")
images_dir = os.path.join(script_dir, "images")
images_json_path = os.path.join(script_dir, "json", "images.json")

# Chargement du fichier item.json
with open(item_json_path, "r", encoding="utf-8") as f:
    ITEM_LIST = json.load(f)

# Chargement du fichier images.json pour les URLs des images de fond
try:
    with open(images_json_path, "r", encoding="utf-8") as f:
        IMAGES_DATA = json.load(f)
except Exception as e:
    print(f"[SHOP] Erreur lors du chargement de images.json : {e}")
    IMAGES_DATA = {}


class ShopView(View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.page = 0
        self.max_per_page = 10
        
        # Filtrer uniquement les items avec un prix > 0
        self.items = [item for item in ITEM_LIST if item.get("price", 0) > 0]
        
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start = self.page * self.max_per_page
        end = start + self.max_per_page

        for item in self.items[start:end]:
            self.add_item(ShopItemButton(item, self.user_id))

        # Boutons de navigation
        if self.page > 0:
            self.add_item(ShopPrevButton(self))
        if end < len(self.items):
            self.add_item(ShopNextButton(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class ShopPrevButton(Button):
    def __init__(self, view_ref):
        super().__init__(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
        self.view_ref = view_ref

    async def callback(self, interaction):
        self.view_ref.page -= 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(view=self.view_ref)


class ShopNextButton(Button):
    def __init__(self, view_ref):
        super().__init__(label="Suivant ➡️", style=discord.ButtonStyle.secondary)
        self.view_ref = view_ref

    async def callback(self, interaction):
        self.view_ref.page += 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(view=self.view_ref)


class ShopItemButton(Button):
    def __init__(self, item, user_id):
        rarity_emoji = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡"
        }
        emoji = rarity_emoji.get(item.get("rarity", "common").lower(), "⚪")
        
        super().__init__(
            label=f"{emoji} {item.get('item_name', 'Inconnu')} - {item.get('price', 0):,}💰",
            style=discord.ButtonStyle.primary
        )
        self.item = item
        self.user_id = user_id

    def resize_keep_aspect(self, img, max_size):
        """Redimensionne une image en gardant les proportions"""
        w, h = img.size
        ratio = min(max_size / w, max_size / h)
        return img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Récupération des données de l'item
        name = self.item["item_name"]
        price = self.item["price"]
        rarity = self.item.get("rarity", "common")
        description = self.item.get("description", "Aucune description.")
        image_url = self.item.get("image", "")
        balance = get_balance(self.user_id)

        # Couleurs par rareté
        rarity_colors = {
            "common": (200, 200, 200),
            "uncommon": (50, 205, 50),
            "rare": (30, 144, 255),
            "epic": (138, 43, 226),
            "legendary": (255, 215, 0)
        }
        rarity_color = rarity_colors.get(rarity.lower(), (200, 200, 200))

        # Dimensions de la carte
        width, height = 850, 600

        # ----- 🎨 Chargement de l'image de fond depuis le JSON -----
        background = None
        
        # Essaie de charger l'image depuis le JSON
        fond_url = IMAGES_DATA.get("fond_shop") or IMAGES_DATA.get("fond_pokedex") or IMAGES_DATA.get("background")
        
        if fond_url and fond_url.startswith("http"):
            try:
                print(f"[SHOP] Chargement du fond depuis l'URL : {fond_url}")
                resp = requests.get(fond_url, timeout=5)
                resp.raise_for_status()
                background = Image.open(BytesIO(resp.content)).convert("RGBA")
                background = background.resize((width, height), Image.Resampling.LANCZOS)
            except Exception as e:
                print(f"[SHOP] Erreur lors du chargement du fond depuis l'URL : {e}")
        
        # Fallback : fichiers locaux
        if background is None:
            try:
                background = Image.open(os.path.join(images_dir, "shop_item.png")).convert("RGBA")
                background = background.resize((width, height), Image.Resampling.LANCZOS)
            except Exception as e:
                print(f"[SHOP] Fond local 'shop_item.png' introuvable : {e}")
                try:
                    background = Image.open(os.path.join(images_dir, "shop_item.png")).convert("RGBA")
                    background = background.resize((width, height), Image.Resampling.LANCZOS)
                except Exception as e2:
                    print(f"[SHOP] Aucun fond disponible, création d'un fond uni : {e2}")
                    background = Image.new("RGBA", (width, height), (245, 245, 245, 255))

        draw = ImageDraw.Draw(background)

        # ----- 📝 Chargement des polices -----
        font_path_bold = os.path.join(script_dir, "fonts", "DejaVuSans-Bold.ttf")
        try:
            font_title = ImageFont.truetype(font_path_bold, 28)
            font_normal = ImageFont.truetype(font_path_bold, 18)
            font_small = ImageFont.truetype(font_path_bold, 16)
        except:
            font_title = ImageFont.load_default()
            font_normal = font_title
            font_small = font_title

        # ----- 🖼️ Positions des éléments -----
        pos_title = (540, 115)
        pos_item_image = (530, 140)
        pos_rarity = (450, 340)
        pos_price = (450, 380)
        pos_balance = (450, 420)
        pos_description = (450, 460)
        

        # ----- ✍️ Nom de l'item -----
        draw.text(pos_title, name, font=font_title, fill="black")

        # ----- ✨ Rareté avec couleur -----
        draw.text(pos_rarity, f"Rareté : {rarity.capitalize()}", font=font_normal, fill="black")

        # ----- 💰 Prix -----
        draw.text(pos_price, f"Prix : {price:,} Croco dollars", font=font_normal, fill="black")

        # ----- 💼 Solde de l'utilisateur -----
        balance_color = (50, 205, 50) if balance >= price else (255, 69, 0)
        draw.text(pos_balance, f"Votre solde : {balance:,} Croco dollars", font=font_normal, fill=balance_color)

        # ----- 📜 Description (multi-lignes) -----
        x, y = pos_description
        draw.text((x, y), "Description :", font=font_normal, fill="black")
        y += 30

        words = description.split()
        lines = []
        current_line = ""
        max_width = 450  # Largeur max pour le texte
        
        for word in words:
            test_line = current_line + word + " "
            # Estimation de la largeur (approximative)
            if len(test_line) * 10 < max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        
        if current_line:
            lines.append(current_line.strip())
        
        # Affichage des lignes (max 4 lignes)
        for line in lines[:4]:
            draw.text((x, y), line, font=font_small, fill="black")
            y += 25

        # ----- 🖼️ Image de l'objet -----
        if image_url and image_url.startswith("http"):
            try:
                resp = requests.get(image_url, timeout=5)
                resp.raise_for_status()
                item_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                
                # Redimensionnement en gardant les proportions
                item_img = self.resize_keep_aspect(item_img, 200)
                
                # Centrage de l'image
                img_x = pos_item_image[0] + (200 - item_img.width) // 2
                img_y = pos_item_image[1]
                
                background.paste(item_img, (img_x, img_y), item_img)
            except Exception as e:
                print(f"[SHOP] Erreur lors du chargement de l'image de l'item : {e}")
                # Image par défaut si erreur
                try:
                    default_img = Image.open(os.path.join(images_dir, "default.png")).convert("RGBA")
                    default_img = self.resize_keep_aspect(default_img, 150)
                    background.paste(default_img, pos_item_image, default_img)
                except:
                    pass

        # ----- 📤 Conversion en fichier Discord -----
        with BytesIO() as buffer:
            background.save(buffer, "PNG")
            buffer.seek(0)
            file = discord.File(buffer, filename="shop_item_card.png")

        # ----- 📋 Création de l'embed -----
        embed = discord.Embed(
            title=f"🛒 {name}",
            color=discord.Color.from_rgb(*rarity_color)
        )
        embed.set_image(url="attachment://shop_item_card.png")

        # ----- 🔘 Bouton d'achat -----
        view = View()
        view.add_item(BuyItemButton(self.item, self.user_id))

        await interaction.followup.send(
            file=file,
            embed=embed,
            view=view,
            ephemeral=True
        )


class BuyItemButton(Button):
    def __init__(self, item, user_id):
        super().__init__(label="🛒 Acheter", style=discord.ButtonStyle.success)
        self.item = item
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        # ⚠️ IMPORTANT : Défère l'interaction immédiatement
        await interaction.response.defer(ephemeral=True)
        
        price = self.item.get("price", 0)
        name = self.item["item_name"]
        
        # Vérifier le solde
        balance = get_balance(self.user_id)
        
        if balance < price:
            await interaction.followup.send(
                f"❌ Tu es trop pauvre ! Tu as besoin de **{price:,}** Croco dollars "
                f"mais tu n'as que **{balance:,}** Croco dollars.\n"
                f"💸 Il te manque **{price - balance:,}** Croco dollars.",
                ephemeral=True
            )
            return

        # Retirer l'argent
        success = remove_money(self.user_id, price)
        
        if not success:
            await interaction.followup.send(
                "❌ Erreur lors de la transaction.",
                ephemeral=True
            )
            return

        # Ajouter l'item à l'inventaire
        add_item(
            user_id=self.user_id,
            name=self.item["item_name"],
            quantity=1,
            rarity=self.item.get("rarity", "common"),
            description=self.item.get("description", ""),
            image=self.item.get("image", ""),
            extra=self.item.get("extra"),
            price=self.item.get("price", 0)
        )

        new_balance = get_balance(self.user_id)
        
        await interaction.followup.send(
            f"✅ Achat réussi !\n"
            f"🎁 Vous avez acheté **{name}** pour **{price:,}** Croco dollars.\n"
            f"💰 Nouveau solde : **{new_balance:,}** Croco dollars.",
            ephemeral=True
        )


def setup_shop(bot):
    """Configure la commande de boutique."""
    
    @bot.command(name="shop")
    async def shop(ctx):
        """Affiche la boutique."""
        balance = get_balance(ctx.author.id)
        
        embed = discord.Embed(
            title="🛒 Boutique Croco",
            description=f"💰 Votre solde : **{balance:,}** Croco dollars\n\n"
                       "Cliquez sur un item pour voir ses détails et l'acheter !",
            color=discord.Color.gold()
        )
        
        view = ShopView(ctx.author.id)
        await ctx.send(embed=embed, view=view)
    
    
    @bot.command(name="boutique")
    async def boutique(ctx):
        """Alias de la commande shop."""
        await shop(ctx)