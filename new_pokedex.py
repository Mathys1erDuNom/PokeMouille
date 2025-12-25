# new_pokedex.py
import discord
from discord.ui import View, Button
from PIL import Image, ImageDraw, ImageFont
import requests, io, os
from io import BytesIO
import json
from new_db import get_new_captures

from combat.utils import normalize_text



script_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = os.path.join(script_dir, "images")

# --- CACHE POKEDEX DYNAMIQUE ---
NEW_POKEDEX_CACHE = {}   # { user_id: { "pokemons": [...], "mosaic": bytes } }


def invalidate_new_pokedex_cache(user_id):
    """Invalide le cache du pokédex pour un utilisateur donné"""
    user_id = str(user_id)
    if user_id in NEW_POKEDEX_CACHE:
        del NEW_POKEDEX_CACHE[user_id]
        print(f"[CACHE] Cache invalidé pour l'utilisateur {user_id}")


async def create_mosaic(pokemon_names, full_pokemon_data, full_pokemon_shiny_data):
    images = []
    nb_total = len(pokemon_names)
    nb_ignores = 0

    for name in pokemon_names:
        clean_name = normalize_text(name)
        # 🔥 CORRECTION : Extraire le nom de base sans le numéro final
        # Enlève les chiffres à la fin (pikachu_shiny2 → pikachu_shiny)
        clean_base = clean_name.rstrip('0123456789')
        
        # Cherche d'abord avec le nom exact
        p_data = next((p for p in full_pokemon_data + full_pokemon_shiny_data 
                      if normalize_text(p["name"]) == clean_name), None)
        
        # 🔥 CORRECTION : Si pas trouvé, chercher avec le nom sans le numéro final
        if not p_data:
            p_data = next((p for p in full_pokemon_data + full_pokemon_shiny_data 
                          if normalize_text(p["name"]) == clean_base), None)

        if not p_data:
            print(f"[IGNORÉ] {name} (base: {clean_base}) non trouvé dans le JSON. Utilisation de l'image par défaut.")
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

        # Vérifie si c'est un shiny
        is_shiny = any(normalize_text(p.get("name", "")) == normalize_text(self.pokemon_name) for p in self.shiny_data)
        display_name = self.pokemon_name + "(Shiny)" if is_shiny else self.pokemon_name

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
            image = Image.open(os.path.join(images_dir, "fond_pokedex_3.png")).convert("RGBA")
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"[ERREUR] Impossible de charger le fond : {e}")
            image = Image.new("RGBA", (width, height), (245, 245, 245, 255))

        draw = ImageDraw.Draw(image)
        try:
            font_path_bold = os.path.join(script_dir, "fonts", "DejaVuSans-Bold.ttf")
            font = ImageFont.truetype(font_path_bold, 15)
            font_bold = ImageFont.truetype(font_path_bold, 20) 
        except:
            font = ImageFont.load_default()
            font_bold = font

        pos_nom_type = (90, 150)
        pos_ivs = (90, 285)
        pos_stats = (90, 380)
        pos_sprite = (550, 165)
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
            f"PV : {ivs.get('hp', '?')} Atk : {ivs.get('attack', '?')}   AtkSpé : {ivs.get('special_attack', '?')}",
            f"Def : {ivs.get('defense', '?')}   DefSpé : {ivs.get('special_defense', '?')}   Vit : {ivs.get('speed', '?')}",
        ]:
            draw.text((x, y), line, font=font, fill="black")
            y += 25

        # --- Stats ---
        x, y = pos_stats
        draw.text((x, y), "Stats :", font=font_bold, fill="black")
        y += 30
        for line in [
            f"PV : {stats.get('hp', '?')}  Atk : {stats.get('attack', '?')}   AtkSpé : {stats.get('special_attack', '?')}",
            f"Def : {stats.get('defense', '?')}   DefSpé : {stats.get('special_defense', '?')}   Vit : {stats.get('speed', '?')}",
        ]:
            draw.text((x, y), line, font=font, fill="black")
            y += 25

        # --- Sprite et Attaques ---
        poke_img_url = p_data.get("image", "")
        if poke_img_url.startswith("http"):
            try:
                response = requests.get(poke_img_url)
                poke_img = Image.open(io.BytesIO(response.content)).convert("RGBA")
                poke_img = self.resize_keep_aspect(poke_img, 150)
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


def setup_new_pokedex(bot, full_pokemon_shiny_data, full_pokemon_data, type_sprites, attack_type_map, json_dir):
    @bot.command()
    async def pokedex(ctx):
        user_id = str(ctx.author.id)
        captures = get_new_captures(user_id)

        if not captures:
            await ctx.send("Tu n'as encore rien capturé dans la nouvelle table.")
            return

        pokemons = [entry["name"] for entry in captures]

        # ----- 🔥 Vérification du cache -----
        cache = NEW_POKEDEX_CACHE.get(user_id)

        if cache and cache["pokemons"] == pokemons:
            print("[CACHE] Nouveau Pokédex envoyé depuis le cache !")

            mosaic_image = io.BytesIO(cache["mosaic"])
            mosaic_image.seek(0)

            file = discord.File(mosaic_image, filename="pokedex_mosaic.png")

            embed = discord.Embed(
                title=f"📘 Nouveau Pokédex de {ctx.author.display_name}",
                description=f"(Cache) Voici ton Pokédex avec {len(pokemons)} Pokémon !",
                color=0x3498db
            )
            embed.set_image(url="attachment://pokedex_mosaic.png")

            view = PokedexView(
                pokemons,
                full_pokemon_shiny_data,
                full_pokemon_data,
                type_sprites,
                attack_type_map,
                captures
            )

            await ctx.send(embed=embed, file=file, view=view)
            return

        # ----- 🛠 PAS DE CACHE → Génération normale -----
        mosaic_image, displayed_count = await create_mosaic(pokemons, full_pokemon_data, full_pokemon_shiny_data)
        
        if mosaic_image is None:
            await ctx.send("Erreur lors de la création de la mosaïque.")
            return

        # ----- 💾 Mise en cache -----
        NEW_POKEDEX_CACHE[user_id] = {
            "pokemons": pokemons,
            "mosaic": mosaic_image.getvalue()
        }

        file = discord.File(mosaic_image, filename="pokedex_mosaic.png")

        embed = discord.Embed(
            title=f"📘 Nouveau Pokédex de {ctx.author.display_name}",
            description=f"Voici la mosaïque de tes {displayed_count} Pokémon !",
            color=0x3498db
        )
        embed.set_image(url="attachment://pokedex_mosaic.png")

        view = PokedexView(
            pokemons,
            full_pokemon_shiny_data,
            full_pokemon_data,
            type_sprites,
            attack_type_map,
            captures
        )

        await ctx.send(embed=embed, file=file, view=view)