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
from buff_iv import BuffPokemonView
from new_db_avantmodif import get_new_captures

# Chargement du fichier item.json
item_json_path = os.path.join(script_dir, "json", "item.json")
with open(item_json_path, "r", encoding="utf-8") as f:
    ITEM_LIST = json.load(f)


import discord
from io import BytesIO
import requests

async def get_pokemon_image_embed(pokemon_name: str, json_file: str, is_shiny: bool = False) -> (discord.Embed, discord.File):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    pokemon_data = next((p for p in data if p["name"].lower() == pokemon_name.lower()), None)
    if not pokemon_data:
        return None, None

    image_url = pokemon_data.get("image")
    if image_url.startswith("http"):
        resp = requests.get(image_url)
        resp.raise_for_status()
        buffer = BytesIO(resp.content)
        file = discord.File(buffer, filename=f"{pokemon_name}.png")
    else:
        file = None

    shiny_text = "✨ " if is_shiny else ""
    embed = discord.Embed(title=f"{shiny_text}{pokemon_data['name']}")
    if file:
        embed.set_image(url=f"attachment://{pokemon_name}.png")

    return embed, file


# ─── Helper spawn ─────────────────────────────────────────────────────────────

async def _handle_spawn(interaction, spawn_func, json_normal, json_shiny, shiny_rate):
    if spawn_func is None:
        await interaction.followup.send("❌ La fonction de spawn n'est pas définie.", ephemeral=True)
        return

    pokemon_name, is_shiny = await spawn_func(
        interaction.user,
        json_file=json_normal,   # spawn_pokemon_for_user gère lui-même le chemin et le shiny
        shiny_rate=shiny_rate
    )

    if not pokemon_name:
        await interaction.followup.send("❌ Impossible de spawn le Pokémon.", ephemeral=True)
        return

    # Le fichier à utiliser pour l'embed image uniquement
    json_file_to_use = json_normal.replace("_normal.json", "_shiny.json") if is_shiny else json_normal
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json", json_file_to_use)

    embed, file = await get_pokemon_image_embed(pokemon_name, json_file=json_path, is_shiny=is_shiny)

    if embed and file:
        await interaction.followup.send(
            content="🎉 Vous avez gagné un Pokémon !",
            embed=embed,
            file=file,
            ephemeral=True
        )
    else:
        await interaction.followup.send("❌ Impossible de trouver l'image du Pokémon.", ephemeral=True)
# ─── Views inventaire ─────────────────────────────────────────────────────────

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
        # ✅ Vérifier si c'est un item à ne pas consommer
        if self.item.get("extra") in ("nothing", "pêche", "pêche_super", "pêche_mega", "baie", "oeuf"):
            await interaction.response.defer(ephemeral=True)
            msg = f"✅ Vous avez utilisé **{self.item['name']}**."
            await interaction.followup.send(msg, ephemeral=True)
            await interaction.followup.send("⏳ Chaque chose en son temps…", ephemeral=True)
            return

        new_qty, extra = use_item(self.user_id, self.item["name"])

        if new_qty is None:
            await interaction.response.send_message(
                "❌ Cet item n'existe plus dans votre inventaire.", ephemeral=True
            )
            return

        # ✅ Un seul defer, tout de suite
        await interaction.response.defer(ephemeral=True)

        msg = f"✅ Vous avez utilisé **{self.item['name']}**."
        if new_qty == 0:
            msg += " C'était le dernier, il a été supprimé ahhhhaaaaaaaaaaa."
        else:
            msg += f" Il vous en reste {new_qty}."

        # ─── Effets spécifiques ───────────────────────────────────────────────

        if extra == "spawn_pokemon":
            await interaction.followup.send(msg, ephemeral=True)
            await _handle_spawn(
                interaction, self.spawn_func,
                json_normal="pokemon_all_pokeball_normal.json",
                json_shiny="json/pokemon_all_pokeball_shiny.json",
                shiny_rate=64
            )

        elif extra == "spawn_pokemon_rare":
            await interaction.followup.send(msg, ephemeral=True)
            await _handle_spawn(
                interaction, self.spawn_func,
                json_normal="pokemon_rare_pokeball_normal.json",
                json_shiny="json/pokemon_rare_pokeball_shiny.json",
                shiny_rate=64
            )

        elif extra == "spawn_pokemon_rare_maybe_shiny":
            await interaction.followup.send(msg, ephemeral=True)
            await _handle_spawn(
                interaction, self.spawn_func,
                json_normal="pokemon_rare_pokeball_normal.json",
                json_shiny="json/pokemon_rare_pokeball_shiny.json",
                shiny_rate=2
            )

        elif extra == "spawn_pokemon_legendaire_maybe_shiny":
            await interaction.followup.send(msg, ephemeral=True)
            await _handle_spawn(
                interaction, self.spawn_func,
                json_normal="pokemon_legendaire_normal.json",
                json_shiny="json/pokemon_legendaire_shiny.json",
                shiny_rate=2
            )

        elif extra == "spawn_pokemon_legendary":
            await interaction.followup.send(msg, ephemeral=True)
            await _handle_spawn(
                interaction, self.spawn_func,
                json_normal="pokemon_legendaire_normal.json",
                json_shiny="json/pokemon_legendaire_shiny.json",
                shiny_rate=64
            )

        elif extra in ("buff_pv", "buff_attaque", "buff_attaque_spe", "buff_defense", "buff_defense_spe", "buff_vitesse"):
            from buff_iv import EXTRA_TO_STAT, STAT_LABELS
            stat_key = EXTRA_TO_STAT[extra]
            stat_label = STAT_LABELS[stat_key]

            captures = get_new_captures(str(interaction.user.id))
            pokemons = [entry["name"] for entry in captures]

            if not pokemons:
                await interaction.followup.send(msg, ephemeral=True)
                await interaction.followup.send("❌ Tu n'as aucun Pokémon capturé.", ephemeral=True)
                return

            view = BuffPokemonView(str(interaction.user.id), pokemons, stat_key=stat_key, iv_increase=4)
            embed = discord.Embed(
                title=f"💊 Buff {stat_label}",
                description=f"Choisis le Pokémon qui recevra **+4 IV en {stat_label}** :",
                color=0xf39c12
            )
            await interaction.followup.send(msg, ephemeral=True)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

############## Pour les items pas utiles desuite ou pas ici

        #elif extra in ("nothing", "pêche", "pêche_super", "pêche_mega", "baie"):
         #   await interaction.followup.send("⏳ Chaque chose en son temps…", ephemeral=True)     

        else:
            # Aucun effet spécial → on envoie juste le message de confirmation
            await interaction.followup.send(msg, ephemeral=True)





# ─── Utilitaire texte ─────────────────────────────────────────────────────────

def draw_multiline_text(draw, text, position, font, max_width, fill=(0, 0, 0)):
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
    line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 10
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height


# ─── Bouton item inventaire ───────────────────────────────────────────────────

class InventoryItemButton(Button):
    def __init__(self, item, parent_view):
        super().__init__(
            label=f"{item.get('name', 'Inconnu')} ×{item.get('quantity', 1)}",
            style=discord.ButtonStyle.primary
        )
        self.item = item
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        name = self.item["name"]
        quantity = self.item["quantity"]
        description = self.item["description"]
        image_url = self.item["image"]

        width, height = 600, 400
        try:
            card = Image.open(os.path.join(images_dir, "image_item.png")).convert("RGBA")
            card = card.resize((width, height), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"[ERREUR] Impossible de charger le fond image_item.png : {e}")
            card = Image.new("RGBA", (width, height), (245, 245, 245, 255))

        draw = ImageDraw.Draw(card)
        font_path = os.path.join(script_dir, "fonts", "DejaVuSans-Bold.ttf")
        try:
            font = ImageFont.truetype(font_path, 22)
            font_small = ImageFont.truetype(font_path, 18)
        except:
            font = ImageFont.load_default()
            font_small = font

        draw.text((70, 130), f"{name}", fill="black", font=font)
        draw.text((70, 180), f"Quantité : {quantity}", fill="black", font=font_small)
        draw_multiline_text(draw, description or "Aucune description.", (70, 230), font_small, max_width=240)

        # APRÈS
        if image_url:
            try:
                if image_url.startswith("http"):
                    resp = requests.get(image_url)
                    resp.raise_for_status()
                    item_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                else:
                    local_path = os.path.join(script_dir, image_url)
                    item_img = Image.open(local_path).convert("RGBA")

                item_img = item_img.resize((100, 100), Image.Resampling.LANCZOS)
                card.paste(item_img, (385, 120), item_img if item_img.mode == "RGBA" else None)
            except Exception as e:
                print(f"Erreur lors du chargement de l'image : {e}")

        with BytesIO() as buffer:
            card.save(buffer, "PNG")
            buffer.seek(0)
            file = discord.File(buffer, filename="item.png")

        embed = discord.Embed(title=name)
        embed.set_image(url="attachment://item.png")

        view = View()
        view.add_item(UseItemButton(
            self.item,
            interaction.user.id,
            spawn_func=self.parent_view.spawn_func
        ))

        await interaction.followup.send(file=file, embed=embed, view=view, ephemeral=True)


# ─── Setup commandes ──────────────────────────────────────────────────────────

def setup_inventory(bot, spawn_func=None):

    @bot.command(name="inventaire")
    async def inventaire(ctx):
        items = get_inventory(ctx.author.id)
        if not items:
            await ctx.send("🎒 Votre inventaire est vide.")
            return

        view = InventoryView(items, spawn_func=spawn_pokemon_for_user)
        await ctx.send("🎒 **Votre inventaire :**", view=view)

    @is_croco()
    @bot.command(name="give")
    async def give(ctx, user: discord.User, *, item_name: str):
        found_item = next(
            (i for i in ITEM_LIST if i["item_name"].lower() == item_name.lower()),
            None
        )
        if not found_item:
            await ctx.send(f"❌ Grand Maître suprême des Crocodiles, l'item `{item_name}` n'existe pas.")
            return

        add_item(
            user_id=user.id,
            name=found_item["item_name"],
            quantity=1,
            rarity=found_item.get("rarity", "common"),
            description=found_item.get("description", ""),
            image=found_item.get("image", ""),
            extra=found_item.get("extra"),
            price=found_item.get("price")
        )

        await ctx.send(
            f"🎁 Grand Maître suprême des Crocodiles, l'item **{found_item['item_name']}** "
            f"a été ajouté à l'inventaire de **{user.mention}**."
        )

    @is_croco()
    @bot.command(name="inventaire_vide")
    async def inventaire_vide(ctx, user: discord.User):
        delete_inventory(user.id)
        await ctx.send(f"🗑️ Grand Maître suprême des Crocodiles, l'inventaire de {user.mention} a été vidé !")