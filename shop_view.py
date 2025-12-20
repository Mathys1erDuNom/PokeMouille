# shop_view.py
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

# Chargement du fichier item.json
with open(item_json_path, "r", encoding="utf-8") as f:
    ITEM_LIST = json.load(f)


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

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Création de la carte visuelle de l'item
        name = self.item["item_name"]
        price = self.item["price"]
        rarity = self.item.get("rarity", "common")
        description = self.item.get("description", "Aucune description.")
        image_url = self.item.get("image", "")

        # Couleurs par rareté
        rarity_colors = {
            "common": (200, 200, 200, 255),
            "uncommon": (50, 205, 50, 255),
            "rare": (30, 144, 255, 255),
            "epic": (138, 43, 226, 255),
            "legendary": (255, 215, 0, 255)
        }
        bg_color = rarity_colors.get(rarity.lower(), (245, 245, 245, 255))

        card = Image.new("RGBA", (600, 400), bg_color)
        draw = ImageDraw.Draw(card)
        
        font_path = os.path.join(script_dir, "fonts", "DejaVuSans-Bold.ttf")
        try:
            font_title = ImageFont.truetype(font_path, 26)
            font_text = ImageFont.truetype(font_path, 18)
        except:
            font_title = ImageFont.load_default()
            font_text = font_title

        # Texte sur la carte
        draw.text((30, 30), name, fill="white", font=font_title)
        draw.text((30, 80), f"Rareté : {rarity}", fill="white", font=font_text)
        draw.text((30, 120), f"Prix : {price:,} 💰", fill="white", font=font_text)
        
        # Description sur plusieurs lignes
        words = description.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if len(test_line) * 10 < 300:  # Approximation de la largeur
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)
        
        y_offset = 170
        for line in lines[:3]:  # Max 3 lignes
            draw.text((30, y_offset), line, fill="white", font=font_text)
            y_offset += 30

        # Image de l'objet
        if image_url and image_url.startswith("http"):
            try:
                resp = requests.get(image_url, timeout=5)
                resp.raise_for_status()
                item_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                item_img = item_img.resize((150, 150), Image.Resampling.LANCZOS)
                card.paste(item_img, (400, 30), item_img)
            except Exception as e:
                print(f"Erreur lors du chargement de l'image : {e}")

        # Conversion en fichier Discord
        with BytesIO() as buffer:
            card.save(buffer, "PNG")
            buffer.seek(0)
            file = discord.File(buffer, filename="shop_item.png")

        # Création de l'embed
        embed = discord.Embed(
            title=f"🛒 {name}",
            description=description,
            color=discord.Color.from_rgb(*bg_color[:3])
        )
        embed.add_field(name="💰 Prix", value=f"{price:,} Croco dollars", inline=True)
        embed.add_field(name="✨ Rareté", value=rarity.capitalize(), inline=True)
        embed.set_image(url="attachment://shop_item.png")

        # Vérifier le solde de l'utilisateur
        balance = get_balance(self.user_id)
        embed.add_field(
            name="💼 Votre solde", 
            value=f"{balance:,} Croco dollars", 
            inline=False
        )

        # Bouton d'achat
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