# inventory_view.py
import discord
from discord.ui import View, Button
from PIL import Image, ImageDraw, ImageFont
import requests, io, os
from io import BytesIO

from inventory_db import get_inventory


script_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = os.path.join(script_dir, "images")


class InventoryView(View):
    def __init__(self, items):
        super().__init__(timeout=180)
        self.items = items
        self.page = 0
        self.max_per_page = 10
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start = self.page * self.max_per_page
        end = start + self.max_per_page

        for item in self.items[start:end]:
            self.add_item(InventoryItemButton(item))

        if self.page > 0:
            self.add_item(InventoryPrevButton(self))
        if end < len(self.items):
            self.add_item(InventoryNextButton(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class InventoryPrevButton(Button):
    def __init__(self, view_ref):
        super().__init__(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
        self.view_ref = view_ref

    async def callback(self, interaction):
        self.view_ref.page -= 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(view=self.view_ref)


class InventoryNextButton(Button):
    def __init__(self, view_ref):
        super().__init__(label="Suivant ➡️", style=discord.ButtonStyle.secondary)
        self.view_ref = view_ref

    async def callback(self, interaction):
        self.view_ref.page += 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(view=self.view_ref)


class InventoryItemButton(Button):
    def __init__(self, item):
        super().__init__(label=f"{item['name']} ×{item['quantity']}", style=discord.ButtonStyle.primary)
        self.item = item

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        name = self.item["name"]
        quantity = self.item["quantity"]
        rarity = self.item["rarity"]
        description = self.item["description"]
        image_url = self.item["image"]

        card = Image.new("RGBA", (600, 400), (245, 245, 245, 255))
        draw = ImageDraw.Draw(card)

        font_path = os.path.join(script_dir, "fonts", "DejaVuSans-Bold.ttf")
        try:
            font = ImageFont.truetype(font_path, 22)
            font_small = ImageFont.truetype(font_path, 18)
        except:
            font = ImageFont.load_default()
            font_small = font

        draw.text((30, 30), f"{name} ({rarity})", fill="black", font=font)
        draw.text((30, 80), f"Quantité : {quantity}", fill="black", font=font_small)
        draw.text((30, 130), description or "Aucune description.", fill="black", font=font_small)

        # Image de l'objet
        if image_url and image_url.startswith("http"):
            try:
                resp = requests.get(image_url)
                item_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                item_img = item_img.resize((200, 200))
                card.paste(item_img, (350, 100), item_img)
            except:
                pass

        with BytesIO() as buffer:
            card.save(buffer, "PNG")
            buffer.seek(0)
            file = discord.File(buffer, filename="item.png")

        embed = discord.Embed(title=name)
        embed.set_image(url="attachment://item.png")
        await interaction.followup.send(file=file, embed=embed, ephemeral=True)


# Commande à ajouter dans ton bot
def setup_inventory(bot):
    @bot.command(name="inventaire")
    async def inventaire(ctx):
        items = get_inventory(ctx.author.id)
        if not items:
            await ctx.send("🎒 Votre inventaire est vide.")
            return

        view = InventoryView(items)
        await ctx.send("🎒 **Votre inventaire :**", view=view)
