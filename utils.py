import discord
from discord.ext import commands, tasks
import random, asyncio, os, json

TARGET_USER_ID_CROCO = int(os.getenv("TARGET_USER_ID_CROCO"))





import discord
import random
import asyncio
import requests
from io import BytesIO
from PIL import Image
import os

from bot import images_dir, _norm, DEFAULT_BACKGROUND, TYPE_BACKGROUNDS

async def spawn_custom_pokemon(
    channel: discord.TextChannel,
    author: discord.Member = None,
    target_user: discord.Member = None,
    pokemon_name: str = None,
    shiny_rate: int = 64,
    pokemon_data_list: list = None,
    shiny_data_list: list = None,
    role_id: int = None
):
    """
    Spawn un Pokémon avec possibilité de choisir un joueur qui pourra le capturer
    et un fichier JSON de Pokémon custom (normal et shiny).
    """

    guild_id = channel.guild.id

    # Choix du Pokémon
    if pokemon_name:
        pokemon = next((p for p in pokemon_data_list if p["name"].lower() == pokemon_name.lower()), None)
        if not pokemon:
            await channel.send(f"❌ Le Pokémon {pokemon_name} est introuvable dans la liste fournie.")
            return

        is_shiny = (random.randint(1, shiny_rate) == 1)
        if is_shiny:
            shiny_match = next((p for p in shiny_data_list if p["name"].lower().replace("_shiny","") == pokemon_name.lower()), None)
            if shiny_match:
                pokemon = shiny_match
    else:
        is_shiny = (random.randint(1, shiny_rate) == 1)
        pokemon = random.choice(shiny_data_list if is_shiny else pokemon_data_list)

    # Nom du Pokémon
    if is_shiny and not pokemon["name"].endswith("_shiny"):
        pokemon_name_spawned = pokemon["name"] + "_shiny"
    else:
        pokemon_name_spawned = pokemon["name"]

    # Embed
    if is_shiny:
        display_name = pokemon["name"].replace("_shiny", "") + " ✨"
        title = f"✨ **Un {display_name} brillant sauvage apparaît** grâce à {author.display_name} !" if author else f"✨ **Un {display_name} brillant sauvage est apparu !**"
        description = "C'est un Pokémon BRILLANT ! Tape vite ! !catch pour le capturer !"
        color = 0xFFD700
    else:
        display_name = pokemon["name"]
        title = f"⚡ Un {display_name} sauvage apparaît grâce à {author.display_name} !" if author else f"Un {display_name} sauvage est apparu !"
        description = "Tape !catch pour le capturer !"
        color = 0x00FF00

    if target_user:
        title += f"\n🎯 Seul {target_user.display_name} peut le capturer !"

    embed = discord.Embed(title=title, description=description, color=color)

    # Image
    try:
        types = pokemon.get("type") or []
        first_type = _norm(types[0]) if types else None
        filename = TYPE_BACKGROUNDS.get(first_type, DEFAULT_BACKGROUND) if first_type else DEFAULT_BACKGROUND
        path = os.path.join(images_dir, filename)
        if not os.path.exists(path):
            path = os.path.join(images_dir, DEFAULT_BACKGROUND)

        background = Image.open(path).convert("RGBA")

        poke_url = pokemon.get("image", "")
        if poke_url.startswith("http"):
            response = requests.get(poke_url, timeout=15)
            pokemon_img = Image.open(BytesIO(response.content)).convert("RGBA").resize((392,392))
            composed = background.copy()
            x = (background.width - pokemon_img.width) // 2
            y = (background.height - pokemon_img.height) // 2
            composed.paste(pokemon_img, (x,y), pokemon_img)

            output = BytesIO()
            composed.save(output, format="PNG")
            output.seek(0)
            file = discord.File(fp=output, filename="spawn.png")
            if role_id:
                content = f"<@&{role_id}>"
            else:
                content = None
            embed.set_image(url="attachment://spawn.png")
            await channel.send(content=content, embed=embed, file=file)
        else:
            await channel.send("Erreur : image du Pokémon invalide.")
    except Exception as e:
        await channel.send("❌ Erreur lors de la création de l'image.")
        print(f"[ERREUR IMAGE SPAWN] {e}")

    return pokemon_name_spawned  # utile si tu veux garder trace du spawn










def is_croco():
    def predicate(ctx):
        return ctx.author.id == TARGET_USER_ID_CROCO
    return commands.check(predicate)