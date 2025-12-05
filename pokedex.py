# pokedex.py
import discord
from discord.ui import View, Button
from PIL import Image, ImageDraw, ImageFont
import requests, io, os
from io import BytesIO
import json


from db import get_captures_old, get_captures_new

script_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = os.path.join(script_dir, "images")


# 👉 Les fonctions utilitaires
def normalize_text(text):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')

async def create_mosaic(pokemon_names, full_pokemon_data, full_pokemon_shiny_data):
    images = []
    nb_total = len(pokemon_names)
    nb_ignores = 0

    for name in pokemon_names:
        clean_name = normalize_text(name)
        clean_base = ''.join(filter(str.isalpha, clean_name))
        p_data = next((p for p in full_pokemon_data + full_pokemon_shiny_data if normalize_text(p["name"]) == clean_name), None)
        if not p_data:
            p_data = next((p for p in full_pokemon_data + full_pokemon_shiny_data if normalize_text(p["name"]) == clean_base), None)

        if not p_data:
            print(f"[IGNORÉ] {name} non trouvé dans le JSON. Utilisation de l'image par défaut.")
            try:
                fallback = Image.open(os.path.join(images_dir, "default.png")).convert("RGBA").resize((64, 64))
                images.append(fallback)
                continue
            except Exception as e:
                print(f"[ERREUR] Image par défaut manquante ou corrompue : {e}")
                nb_ignores += 1
                continue

        try:
            response = requests.get(p_data["image"])
            img = Image.open(BytesIO(response.content)).convert("RGBA").resize((64, 64))
            images.append(img)
        except Exception as e:
            print(f"[ERREUR] Image introuvable pour {p_data['name']}, fallback utilisé. → {e}")
            try:
                fallback = Image.open(os.path.join(images_dir, "default.png")).convert("RGBA").resize((64, 64))
                images.append(fallback)
            except Exception as e:
                print(f"[ERREUR] Image par défaut manquante ou corrompue : {e}")
                nb_ignores += 1

    if not images:
        return None, 0

    cols = 5
    rows = (len(images) + cols - 1) // cols
    mosaic = Image.new("RGBA", (cols * 64, rows * 64))
    for i, img in enumerate(images):
        x = (i % cols) * 64
        y = (i // cols) * 64
        mosaic.paste(img, (x, y))

    output = BytesIO()
    mosaic.save(output, format="PNG")
    output.seek(0)
    return output, len(images) 


# 👉 Les Views et Buttons du Pokédex
class PokedexView(View):
    def __init__(self, pokemons, shiny_data, full_pokemon_data, type_sprites, attack_type_map, capture_data):
        super().__init__(timeout=180)
        self.pokemons = pokemons
        self.shiny_data = shiny_data
        self.full_pokemon_data = full_pokemon_data
        self.type_sprites = type_sprites
        self.attack_type_map = attack_type_map
        self.capture_data = capture_data
        self.page = 0
        self.max_per_page = 23
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start = self.page * self.max_per_page
        end = start + self.max_per_page
        page_pokemons = self.pokemons[start:end]
        for pkmn in page_pokemons:
            self.add_item(PokemonButton(pkmn, self.shiny_data, self.full_pokemon_data, self.type_sprites, self.attack_type_map, self.capture_data))
        if self.page > 0:
            self.add_item(PokedexPrevButton(self))
        if end < len(self.pokemons):
            self.add_item(PokedexNextButton(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class PokedexPrevButton(Button):
    def __init__(self, view_ref):
        super().__init__(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
        self.view_ref = view_ref

    async def callback(self, interaction):
        self.view_ref.page -= 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(view=self.view_ref)

class PokedexNextButton(Button):
    def __init__(self, view_ref):
        super().__init__(label="Suivant ➡️", style=discord.ButtonStyle.secondary)
        self.view_ref = view_ref

    async def callback(self, interaction):
        self.view_ref.page += 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(view=self.view_ref)

class PokemonButton(Button):
    def __init__(self, pokemon_name, shiny_data, full_pokemon_data, type_sprites, attack_type_map, capture_data):
        super().__init__(label=pokemon_name, style=discord.ButtonStyle.primary)
        self.pokemon_name = pokemon_name
        self.shiny_data = shiny_data
        self.full_pokemon_data = full_pokemon_data
        self.type_sprites = type_sprites
        self.attack_type_map = attack_type_map
        self.capture_data = capture_data

    def resize_keep_aspect(self, img, max_size):
        w, h = img.size
        ratio = min(max_size / w, max_size / h)
        return img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Vérifie si c’est un shiny
        is_shiny = any(normalize_text(p.get("name", "")) == normalize_text(self.pokemon_name) for p in self.shiny_data)
        display_name = self.pokemon_name + " ✨" if is_shiny else self.pokemon_name

        # Cherche les données de ce Pokémon
        p_data = next((p for p in self.capture_data if normalize_text(p["name"]) == normalize_text(self.pokemon_name)), None)
        if not p_data:
            p_data = next((p for p in self.full_pokemon_data + self.shiny_data if normalize_text(p["name"]) == normalize_text(self.pokemon_name)), None)
        if not p_data:
            await interaction.followup.send("❌ Pokémon introuvable.", ephemeral=True)
            return

        type_ = p_data.get("type", [])
        if isinstance(type_, str):
            type_ = [type_]

        stats = p_data.get("stats_iv", p_data.get("stats", {}))
        ivs = p_data.get("ivs", {})
        attacks = p_data.get("attacks", [])

        width, height = 850, 600
        try:
            image = Image.open(os.path.join(images_dir, "fond_pokedex.png")).convert("RGBA")
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"[ERREUR] Impossible de charger le fond : {e}")
            image = Image.new("RGBA", (width, height), (245, 245, 245, 255))

        draw = ImageDraw.Draw(image)
        try:
            font_path_bold = os.path.join(script_dir, "fonts", "DejaVuSans-Bold.ttf")
            font = ImageFont.truetype(font_path_bold, 15)       # texte normal ou gras selon ton besoin
            font_bold = ImageFont.truetype(font_path_bold, 20) 
        except:
            font = ImageFont.load_default()
            font_bold = font

        pos_nom_type = (90, 70)
        pos_ivs = (90, 270)
        pos_stats = (90, 420)
        pos_sprite = (520, 40)
        pos_attaques = (535, 340)

        # --- Nom + Types ---
        x, y = pos_nom_type
        draw.text((x, y), display_name, font=font_bold, fill="black")
        y += 30
        for t in type_:
            url = self.type_sprites.get(t.lower())
            if url:
                try:
                    response = requests.get(url)
                    icon = Image.open(io.BytesIO(response.content)).convert("RGBA")
                    icon = self.resize_keep_aspect(icon, 70)
                    image.paste(icon, (x, y), icon)
                    draw.text((x + icon.width + 5, y), t.capitalize(), font=font_bold, fill="black")
                    y += icon.height + 5
                except:
                    draw.text((x, y), t.capitalize(), font=font, fill="black")
                    y += 20
            else:
                draw.text((x, y), t.capitalize(), font=font, fill="black")
                y += 20

        # --- IVs ---
        x, y = pos_ivs
        draw.text((x, y), "IVs :", font=font_bold, fill="black")
        y += 25
        for line in [
            f"PV : {ivs.get('hp', '?')}",
            f"Atk : {ivs.get('attack', '?')} | AtkSpé : {ivs.get('special_attack', '?')}",
            f"Def : {ivs.get('defense', '?')} | DefSpé : {ivs.get('special_defense', '?')} | Vit : {ivs.get('speed', '?')}",
        ]:
            draw.text((x, y), line, font=font, fill="black")
            y += 25

        # --- Stats ---
        x, y = pos_stats
        draw.text((x, y), "Stats :", font=font_bold, fill="black")
        y += 30
        for line in [
            f"PV : {stats.get('hp', '?')}",
            f"Atk : {stats.get('attack', '?')} | AtkSpé : {stats.get('special_attack', '?')}",
            f"Def : {stats.get('defense', '?')} | DefSpé : {stats.get('special_defense', '?')}",
            f"Vit : {stats.get('speed', '?')}"
        ]:
            draw.text((x, y), line, font=font, fill="black")
            y += 25

        # --- Sprite et Attaques ---
        poke_img_url = p_data.get("image", "")
        if poke_img_url.startswith("http"):
            try:
                response = requests.get(poke_img_url)
                poke_img = Image.open(io.BytesIO(response.content)).convert("RGBA")
                poke_img = self.resize_keep_aspect(poke_img, 250)
                image.paste(poke_img, pos_sprite, poke_img)
            except:
                pass

        # Attaques
        x, y = pos_attaques
        draw.text((x, y), "Attaques :", font=font_bold, fill="black")
        y += 40
        for atk_name in attacks:
            atk_type = self.attack_type_map.get(normalize_text(atk_name))
            atk_sprite_url = self.type_sprites.get(atk_type.lower()) if atk_type else None
            if atk_sprite_url:
                try:
                    response = requests.get(atk_sprite_url)
                    icon = Image.open(io.BytesIO(response.content)).convert("RGBA")
                    icon = self.resize_keep_aspect(icon, 80)
                    image.paste(icon, (x, y), icon)
                    draw.text((x + icon.width + 8, y), atk_name, font=font, fill="black")
                except:
                    draw.text((x, y), atk_name, font=font, fill="black")
            else:
                draw.text((x, y), atk_name, font=font, fill="black")
            y += 40

        # --- Envoi du résultat ---
        with io.BytesIO() as img_binary:
            image.save(img_binary, "PNG")
            img_binary.seek(0)
            file = discord.File(img_binary, filename=f"{self.pokemon_name}.png")

        embed = discord.Embed(title=display_name)
        embed.set_image(url=f"attachment://{self.pokemon_name}.png")
        await interaction.followup.send(file=file, embed=embed, ephemeral=True)



def setup_pokedex(bot, full_pokemon_shiny_data, full_pokemon_data, type_sprites, attack_type_map, json_dir):

    # --- Commande pour la nouvelle base ---
    @bot.command()
    async def pokedex(ctx):
        user_id = str(ctx.author.id)
        captures = get_captures_new(user_id)  # <-- new database
        if not captures:
            await ctx.send("Tu n'as encore rien capturé.")
            return
        await send_pokedex_view(ctx, captures, full_pokemon_data, full_pokemon_shiny_data)


    # --- Commande pour l'ancienne base ---
    @bot.command(name="ex_pokedex")
    async def ex_pokedex(ctx):
        user_id = str(ctx.author.id)
        captures = get_captures_old(user_id)  # <-- old database

        if not captures:
            await ctx.send("Tu n'as capturé aucun Pokémon !")
            return
    
        view = ExPokedexSelect(captures)
        await ctx.send(
            "Choisis un Pokémon à afficher dans le Pokédex :", 
            view=view
        )




# --- Fonction réutilisable pour envoyer l'embed + view ---
async def send_pokedex_view(ctx, captures, full_pokemon_data, full_pokemon_shiny_data):
    pokemons = [entry["name"] for entry in captures]
    mosaic_image, displayed_count = await create_mosaic(
        pokemons, full_pokemon_data, full_pokemon_shiny_data
    )

    if mosaic_image is None:
        await ctx.send("Erreur lors de la création de la mosaïque.")
        return

    file = discord.File(mosaic_image, filename="pokedex_mosaic.png")
    embed = discord.Embed(
        title=f"📘 Pokédex de {ctx.author.display_name}",
        description=f"Voici la mosaïque de tes {displayed_count} Pokémon visibles (sur {len(pokemons)} capturés) !",
        color=0x3498db
    )
    embed.set_image(url="attachment://pokedex_mosaic.png")
    await ctx.send(embed=embed, file=file)



from discord.ui import View, Select


class ExPokedexSelect(discord.ui.Select):
    def __init__(self, user_captures):
        options = []

        # user_captures EST UNE LISTE
        for entry in user_captures:
            poke_name = entry.get("name")
            if poke_name:
                options.append(discord.SelectOption(label=poke_name, value=str(poke_name)))

        super().__init__(
            placeholder="Choisis un Pokémon",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        chosen_name = self.values[0]

        # Récupérer les données complètes du Pokémon capturé
        for entry in self.view.user_captures:
            if entry["name"] == chosen_name:
                selected = entry
                break

        # Afficher le Pokémon
        await interaction.response.send_message(
            f"Tu as choisi **{selected['name']}** !",
            ephemeral=True
        )


class ExPokedexSelect(View):
    def __init__(self, user_captures):
        super().__init__(timeout=180)

        options = []
        for data in user_captures:
            options.append(discord.SelectOption(
                label=data["name"],
                description=f"Afficher {data['name']}"
            ))

        self.add_item(Select(
            placeholder="Choisis un Pokémon",
            options=options
        ))
