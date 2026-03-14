import asyncio
import random
import json
import os
import discord
from discord.ext import commands

# -----------------------
# CONFIGURATION PÊCHE
# -----------------------
FISH_TIMER_MIN = 60
FISH_TIMER_MAX = 300
SHINY_RATE = 1 / 512
NO_CATCH_RATE = 0.35

JSON_DIR = os.path.join(os.path.dirname(__file__), "json")

REGION_FILES = {
    "Kanto":  ("pokemon_gen1_normal.json", "pokemon_gen1_shiny.json"),
    "Johto":  ("pokemon_gen2_normal.json", "pokemon_gen2_shiny.json"),
    "Hoenn":  ("pokemon_gen3_normal.json", "pokemon_gen3_shiny.json"),
    "Sinnoh": ("pokemon_gen4_normal.json", "pokemon_gen4_shiny.json"),
}

fishing_in_progress: set[int] = set()


def load_region_data(region: str):
    if region not in REGION_FILES:
        return [], []
    normal_file, shiny_file = REGION_FILES[region]
    try:
        with open(os.path.join(JSON_DIR, normal_file), "r", encoding="utf-8") as f:
            normal_data = json.load(f)
    except FileNotFoundError:
        normal_data = []
    try:
        with open(os.path.join(JSON_DIR, shiny_file), "r", encoding="utf-8") as f:
            shiny_data = json.load(f)
    except FileNotFoundError:
        shiny_data = []

    normal_water = [p for p in normal_data if "eau" in [t.lower() for t in p.get("type", [])]]
    shiny_water  = [p for p in shiny_data  if "eau" in [t.lower() for t in p.get("type", [])]]
    return normal_water, shiny_water


def get_user_region(cur, user_id: str) -> str | None:
    cur.execute("SELECT region FROM user_regions WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None


def save_fish_capture(user_id: str, pokemon: dict, is_shiny: bool):
    from new_db import save_new_capture
    base_stats = pokemon.get("stats", {})
    ivs = {stat: random.randint(0, 31) for stat in base_stats}
    final_stats = {stat: base_stats[stat] + ivs[stat] for stat in base_stats}
    display_name = ("✨" + pokemon["name"]) if is_shiny else pokemon["name"]
    pokemon_data = {
        "image":   pokemon.get("image", ""),
        "type":    pokemon.get("type", []),
        "attacks": pokemon.get("attacks", []),
    }
    save_new_capture(user_id, display_name, ivs, final_stats, pokemon_data)
    return ivs, final_stats


def setup_fishing(bot: commands.Bot, cur):
    """Enregistre la commande !peche sur le bot."""

    @bot.command()
    async def peche(ctx):
        user_id = ctx.author.id
        user_id_str = str(user_id)

        if user_id in fishing_in_progress:
            await ctx.send(
                f"{ctx.author.mention} 🎣 Tu as déjà une ligne à l'eau !",
                delete_after=5
            )
            return

        region = get_user_region(cur, user_id_str)
        if not region:
            await ctx.send(
                f"{ctx.author.mention} ❌ Pas de région choisie ! Utilise `!region`.",
                delete_after=5
            )
            return

        normal_pool, shiny_pool = load_region_data(region)
        if not normal_pool:
            await ctx.send(
                f"{ctx.author.mention} ❌ Aucun Pokémon aquatique pour **{region}**.",
                delete_after=5
            )
            return

        fishing_in_progress.add(user_id)

        wait_time = random.randint(FISH_TIMER_MIN, FISH_TIMER_MAX)
        minutes = wait_time // 60
        seconds = wait_time % 60

        try:
            dm = await ctx.author.create_dm()
            await dm.send(
                f"🎣 **Tu lances ta ligne dans les eaux de {region} !**\n"
                f"⏳ Attends environ **{minutes}min {seconds}s**... quelque chose va peut-être mordre."
            )
            await ctx.send(f"{ctx.author.mention} 📩 Check tes DMs !", delete_after=5)
        except discord.Forbidden:
            fishing_in_progress.discard(user_id)
            await ctx.send(
                f"{ctx.author.mention} ❌ Active tes DMs et réessaie.",
                delete_after=5
            )
            return

        await asyncio.sleep(wait_time)
        fishing_in_progress.discard(user_id)

        if random.random() < NO_CATCH_RATE:
            await dm.send(
                "💨 **Rien au bout de la ligne...**\n"
                "Aucun Pokémon n'a mordu. Retente ta chance !"
            )
            return

        is_shiny = random.random() < SHINY_RATE
        if is_shiny and shiny_pool:
            pokemon = random.choice(shiny_pool)
        else:
            is_shiny = False
            pokemon = random.choice(normal_pool)

        ivs, final_stats = save_fish_capture(user_id_str, pokemon, is_shiny)

        color = discord.Color.gold() if is_shiny else discord.Color.blue()
        embed = discord.Embed(
            title=f"🎣 Tu as pêché {'✨ un Shiny ' if is_shiny else 'un '}{pokemon['name']} !",
            color=color
        )
        embed.set_thumbnail(url=pokemon.get("image", ""))
        embed.add_field(name="Type", value=" / ".join(t.capitalize() for t in pokemon.get("type", [])), inline=True)
        embed.add_field(name="Attaques", value="\n".join(pokemon.get("attacks", [])) or "Aucune", inline=True)

        avg_iv = round(sum(ivs.values()) / len(ivs), 1) if ivs else 0
        embed.add_field(name="IV moyens", value=f"{avg_iv} / 31", inline=False)

        stats_lines = "\n".join(f"**{k.replace('_', ' ').capitalize()}** : {v}" for k, v in final_stats.items())
        embed.add_field(name="Stats", value=stats_lines, inline=False)
        embed.set_footer(text="✨ Incroyable ! Un Pokémon Shiny !" if is_shiny else f"Région : {region}")

        await dm.send(embed=embed)