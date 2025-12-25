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



import json
import discord
from io import BytesIO
import requests

async def get_pokemon_image_embed(pokemon_name: str, json_file: str, is_shiny: bool = False) -> (discord.Embed, discord.File):
    """
    Renvoie un embed Discord et un fichier avec l'image du Pokémon.

    :param pokemon_name: Nom du Pokémon à afficher
    :param json_file: Chemin du fichier JSON contenant les données des Pokémon
    :param is_shiny: Indique si le Pokémon est shiny (pour le préfixe ✨)
    """
    # Chargement du JSON
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Recherche du Pokémon
    pokemon_data = next((p for p in data if p["name"].lower() == pokemon_name.lower()), None)
    if not pokemon_data:
        return None, None

    # Préparation de l'image
    image_url = pokemon_data.get("image")
    if image_url.startswith("http"):
        resp = requests.get(image_url)
        resp.raise_for_status()
        buffer = BytesIO(resp.content)
        file = discord.File(buffer, filename=f"{pokemon_name}.png")
    else:
        file = None

    # Préparation de l'embed
    shiny_text = "✨ " if is_shiny else ""
    embed = discord.Embed(title=f"{shiny_text}{pokemon_data['name']}")
    if file:
        embed.set_image(url=f"attachment://{pokemon_name}.png")

    return embed, file


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

                pokemon_name, is_shiny = await self.spawn_func(
                    interaction.user,
                    json_file="pokemon_all_pokeball_normal.json",  # 📦 JSON choisi ici
                    shiny_rate=64  # ✨ shiny boosté
                )

                if pokemon_name:
                    json_file_to_use = "json/pokemon_all_pokeball_shiny.json" if is_shiny else "json/pokemon_all_pokeball_normal.json"

                    embed, file = await get_pokemon_image_embed(
                        pokemon_name, 
                        json_file= json_file_to_use ,
                        is_shiny=is_shiny
                    )
                    if embed and file:
                        await interaction.followup.send(
                            content="🎉 Vous avez gagné un Pokémon !",
                            embed=embed,
                            file=file,
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            "❌ Impossible de trouver l'image du Pokémon.",
                            ephemeral=True
                        )    
                else:
                    await interaction.followup.send(
                    "❌ Impossible de spawn le Pokémon.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                "❌ La fonction de spawn n'est pas définie.",
                ephemeral=True
                )

        

        if extra == "spawn_pokemon_legendary":
            if self.spawn_func is not None:

                pokemon_name, is_shiny = await self.spawn_func(
                    interaction.user,
                    json_file="pokemon_legendaire_normal.json",  # 📦 JSON choisi ici
                    shiny_rate=64   # ✨ shiny boosté
                )

                if pokemon_name:
                    json_file_to_use = "json/pokemon_legendaire_shiny.json" if is_shiny else "json/pokemon_legendaire_normal.json"
                    embed, file = await get_pokemon_image_embed(
                        pokemon_name, 
                        json_file=json_file_to_use,
                        is_shiny=is_shiny
                    )
                    if embed and file:
                        await interaction.followup.send(
                            content="🎉 Vous avez gagné un Pokémon !",
                            embed=embed,
                            file=file,
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            "❌ Impossible de trouver l'image du Pokémon.",
                            ephemeral=True
                        )    
                else:
                    await interaction.followup.send(
                    "❌ Impossible de spawn le Pokémon.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                "❌ La fonction de spawn n'est pas définie.",
                ephemeral=True
                )


        elif extra == "boost":
            await interaction.followup.send("⚡ Vous avez reçu un boost !", ephemeral=True)

        # Envoie maintenant le message générique
        await interaction.followup.send(msg, ephemeral=True)

def draw_multiline_text(draw, text, position, font, max_width, fill=(0,0,0)):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = font.getbbox(test_line)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    x, y = position
    line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 4
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height



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

        # 🔥 Chargement de l'image de fond
        width, height = 600, 400
        try:
            card = Image.open(os.path.join(images_dir, "image_item.png")).convert("RGBA")
            card = card.resize((width, height), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"[ERREUR] Impossible de charger le fond image_item.png : {e}")
            # Fallback : fond uni si l'image n'existe pas
            card = Image.new("RGBA", (width, height), (245, 245, 245, 255))

        draw = ImageDraw.Draw(card)
        font_path = os.path.join(script_dir, "fonts", "DejaVuSans-Bold.ttf")
        try:
            font = ImageFont.truetype(font_path, 22)
            font_small = ImageFont.truetype(font_path, 18)
        except:
            font = ImageFont.load_default()
            font_small = font

        # Texte sur le fond
        draw.text((30, 30), f"{name} ({rarity})", fill="black", font=font)
        draw.text((30, 80), f"Quantité : {quantity}", fill="black", font=font_small)
        draw_multiline_text(draw, description or "Aucune description.", (30, 130), font_small, max_width=300)

        # Image de l'objet
        if image_url and image_url.startswith("http"):
            try:
                resp = requests.get(image_url)
                resp.raise_for_status()
                item_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                item_img = item_img.resize((150, 150), Image.Resampling.LANCZOS)
                card.paste(item_img, (350, 80), item_img if item_img.mode == "RGBA" else None)
            except Exception as e:
                print(f"Erreur lors du chargement de l'image : {e}")

        with BytesIO() as buffer:
            card.save(buffer, "PNG")
            buffer.seek(0)
            file = discord.File(buffer, filename="item.png")

        embed = discord.Embed(title=name)
        embed.set_image(url="attachment://item.png")

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
            await ctx.send(f"❌ Grand Maître suprême des Crocodiles, l'item `{item_name}` n'existe pas.")
            return

        # Ajout de l'item dans la DB
        add_item(
            user_id=user.id,
            name=found_item["item_name"],
            quantity=1,
            rarity=found_item.get("rarity", "common"),
            description=found_item.get("description", ""),
            image=found_item.get("image", ""),
            extra=found_item.get("extra"),
            price = found_item.get("price")
        )
        

        await ctx.send(
            f"🎁 Grand Maître suprême des Crocodiles, l'item **{found_item['item_name']}** "
            f"a été ajouté à l'inventaire de **{user.mention}**."
        )

    @bot.command(name="inventaire_vide")
    async def inventaire_vide(ctx, user: discord.User):
        """Supprime tous les items de l'inventaire d'un utilisateur."""
    
        delete_inventory(user.id)
        await ctx.send(f"🗑️ Grand Maître suprême des Crocodiles, l'inventaire de {user.mention} a été vidé !")