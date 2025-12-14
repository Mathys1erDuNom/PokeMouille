# inventory_view.py
import discord
from discord.ui import View, Button
from PIL import Image, ImageDraw, ImageFont
import requests, io, os
from io import BytesIO
from utils import is_croco

from inventory_db import add_item
from inventory_db import get_inventory
from inventory_db import delete_inventory
import json
from inventory_db import use_item
from utils import spawn_pokemon_for_user
script_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = os.path.join(script_dir, "images")


# Chargement du fichier item.json

item_json_path = os.path.join(script_dir, "json", "item.json")

with open(item_json_path, "r", encoding="utf-8") as f:
    ITEM_LIST = json.load(f)

class InventoryView(View):
    def __init__(self, items, spawn_func=None):
        super().__init__(timeout=180)
        self.items = items
        self.spawn_func = spawn_func
        self.page = 0
        self.max_per_page = 10
    
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start = self.page * self.max_per_page
        end = start + self.max_per_page

        for item in self.items[start:end]:
           self.add_item(InventoryItemButton(item, self))


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



class UseItemButton(Button):
    def __init__(self, item, user_id, spawn_func=None):
        super().__init__(label="🛠 Utiliser", style=discord.ButtonStyle.success)
        self.item = item
        self.user_id = user_id
        self.spawn_func = spawn_func

    async def callback(self, interaction: discord.Interaction):
        new_qty, extra = use_item(self.user_id, self.item["name"])
        

        if new_qty is None:
            await interaction.response.send_message(
                "❌ Cet item n'existe plus dans votre inventaire.", ephemeral=True
            )
            return

        # Défère l'interaction immédiatement
        await interaction.response.defer(ephemeral=True)

        msg = f"✅ Vous avez utilisé **{self.item['name']}**."
        if new_qty == 0:
            msg += " C'était le dernier, il a été supprimé ahhhhaaaaaaaaaaa."
        else:
            msg += f" Il vous en reste {new_qty}."

        # Effets spécifiques
        if extra == "spawn_pokemon":
            if self.spawn_func is not None:
                pokemon_name, is_shiny = await self.spawn_func(interaction.user)
                if pokemon_name:
                    shiny_text = "✨ " if is_shiny else ""
                    await interaction.followup.send(
                        f"🎉 Vous avez gagné un Pokémon {shiny_text}**{pokemon_name}** !",
                        ephemeral=True
                        )
                else:
                    await interaction.followup.send(
                        "❌ Impossible de spawn le Pokémon.", ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    "❌ La fonction de spawn n'est pas définie.", ephemeral=True
                )
        elif extra == "soin":
            await interaction.followup.send("💖 Votre Pokémon a été soigné !", ephemeral=True)
        elif extra == "boost":
            await interaction.followup.send("⚡ Vous avez reçu un boost !", ephemeral=True)

        # Envoie maintenant le message générique
        await interaction.followup.send(msg, ephemeral=True)
    

class InventoryItemButton(Button):
    def __init__(self, item, parent_view):
        super().__init__(
            label=f"{item.get('name','Inconnu')} ×{item.get('quantity', 1)}",
            style=discord.ButtonStyle.primary
        )
        self.item = item
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Création de la carte visuelle de l'item
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
                resp.raise_for_status()
                item_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                item_img = item_img.resize((200, 200), Image.Resampling.LANCZOS)
                card.paste(item_img, (350, 100), item_img if item_img.mode == "RGBA" else None)
            except Exception as e:
                print(f"Erreur lors du chargement de l'image : {e}")

        with BytesIO() as buffer:
            card.save(buffer, "PNG")
            buffer.seek(0)
            file = discord.File(buffer, filename="item.png")

        embed = discord.Embed(title=name)
        embed.set_image(url="attachment://item.png")

        # InventoryItemButton.callback
        view = View()
        view.add_item(
            UseItemButton(
                self.item,
                interaction.user.id,
                spawn_func=self.parent_view.spawn_func
            )
        )

        await interaction.followup.send(
            file=file,
            embed=embed,
            view=view,
            ephemeral=True
        )
    


def setup_inventory(bot, spawn_func=None):

    @bot.command(name="inventaire")
    async def inventaire(ctx):
        items = get_inventory(ctx.author.id)
        if not items:
            await ctx.send("🎒 Votre inventaire est vide.")
            return

        view = InventoryView(items, spawn_func=spawn_pokemon_for_user)
        await ctx.send("🎒 **Votre inventaire :**", view=view)


    # 👉 Nouvelle commande GIVE
    @is_croco()
    @bot.command(name="give")
    async def give(ctx, user: discord.User, *, item_name: str):
        """Donne un item à un utilisateur."""

        # Recherche de l'item dans item.json
        found_item = next(
            (i for i in ITEM_LIST if i["item_name"].lower() == item_name.lower()),
            None
        )

        if not found_item:
            await ctx.send(f"❌ Grand Maître suprême des Crocodiles, l’item `{item_name}` n’existe pas.")
            return

        # Ajout de l’item dans la DB
        add_item(
            user_id=user.id,
            name=found_item["item_name"],
            quantity=1,
            rarity=found_item.get("rarity", "common"),
            description=found_item.get("description", ""),
            image=found_item.get("image", ""),
            extra=found_item.get("extra")
        )
        

        await ctx.send(
            f"🎁 Grand Maître suprême des Crocodiles, l’item **{found_item['item_name']}** "
            f"a été ajouté à l’inventaire de **{user.mention}**."
        )

    @bot.command(name="inventaire_vide")
    async def inventaire_vide(ctx, user: discord.User):
        """Supprime tous les items de l'inventaire d'un utilisateur."""
    
        delete_inventory(user.id)
        await ctx.send(f"🗑️ Grand Maître suprême des Crocodiles, l'inventaire de {user.mention} a été vidé !")
    
