import discord
from discord.ext import commands, tasks
import random, asyncio, os, json

TARGET_USER_ID_CROCO = int(os.getenv("TARGET_USER_ID_CROCO"))





def is_croco():
    def predicate(ctx):
        return ctx.author.id == TARGET_USER_ID_CROCO
    return commands.check(predicate)





# json_gift_pokemon.py
import json
import random
import os
import discord
from discord.ext import commands

from new_db import save_new_capture

# ------------------------
# Utils IV
# ------------------------

def generate_ivs():
    return {
        "hp": random.randint(0, 31),
        "attack": random.randint(0, 31),
        "defense": random.randint(0, 31),
        "special_attack": random.randint(0, 31),
        "special_defense": random.randint(0, 31),
        "speed": random.randint(0, 31)
    }

def apply_ivs(base_stats, ivs):
    return {
        stat: base_stats.get(stat, 0) + ivs.get(stat, 0)
        for stat in base_stats
    }

# ------------------------
# Core function
# ------------------------

async def give_random_pokemon_from_json(
    ctx,
    json_path: str,
    target: discord.Member = None,
    shiny_rate: int = 64
):
    if not os.path.exists(json_path):
        await ctx.send("❌ Fichier JSON introuvable.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        pokemon_list = json.load(f)

    if not pokemon_list:
        await ctx.send("❌ Le fichier JSON est vide.")
        return

    # 🎲 Pokémon aléatoire
    is_shiny = random.randint(1, shiny_rate) == 1
    pokemon = random.choice(pokemon_list)

    pokemon_name = pokemon["name"]
    if is_shiny:
        pokemon_name += "_shiny ✨"

    # 🎯 IV & stats
    ivs = generate_ivs()
    stats_with_iv = apply_ivs(pokemon["stats"], ivs)

    pokemon_instance = dict(pokemon)
    pokemon_instance["ivs"] = ivs
    pokemon_instance["stats_iv"] = stats_with_iv

    # 👤 Cible
    user = target or ctx.author

    # 💾 Sauvegarde
    save_new_capture(
        user.id,
        pokemon_name,
        ivs,
        stats_with_iv,
        pokemon_instance
    )

    # 📢 Message
    embed = discord.Embed(
        title="🎁 Pokémon offert !",
        description=(
            f"**{user.display_name}** reçoit un **{pokemon_name}**\n"
            f"🎲 IV aléatoires générés\n"
            f"✨ Taux shiny : 1/{shiny_rate}"
        ),
        color=0xFFD700 if is_shiny else 0x00CC66
    )

    if pokemon.get("image"):
        embed.set_image(url=pokemon["image"])

    await ctx.send(embed=embed)

# ------------------------
# Command setup
# ------------------------

def setup_json_gift_command(bot):

    @bot.command(name="givepokejson")
    async def givepokejson(
        ctx,
        json_file: str,
        shiny_rate: int = 64,
        target: discord.Member = None
    ):
        """
        Usage:
        !givepokejson pokemon.json
        !givepokejson pokemon.json 32
        !givepokejson pokemon.json 16 @User
        """

        # Autorisation (Croco only)
        if not hasattr(bot, "is_under_ban"):
            pass  # optionnel

        json_path = os.path.join(
            os.path.dirname(__file__),
            "json",
            json_file
        )

        await give_random_pokemon_from_json(
            ctx,
            json_path=json_path,
            target=target,
            shiny_rate=shiny_rate
        )
