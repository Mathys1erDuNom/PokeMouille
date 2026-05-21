import asyncio
import random
import json
import os
import discord
from discord.ext import commands

# -----------------------
# CONFIGURATION PÊCHE
# -----------------------
FISH_TIMER_MIN = 300 #5min
FISH_TIMER_MAX = 900 #15 min
SHINY_RATE = 1 / 64

NO_CATCH_RATE = 0.40
ITEM_RATE     = 0.30

JSON_DIR = os.path.join(os.path.dirname(__file__), "json")
FISHING_ITEMS_FILE = os.path.join(JSON_DIR, "fishing_items.json")

RODS = {
    "Canne":       {"emoji": "1️⃣"},
    "Super Canne": {"emoji": "2️⃣"},
    "Méga Canne":  {"emoji": "3️⃣"},
}

# Remplace la constante FISHING_ITEMS_FILE par un dict par canne
ROD_ITEMS_FILES = {
    "Canne":       os.path.join(JSON_DIR, "pêche", "canne.json"),
    "Super Canne": os.path.join(JSON_DIR, "pêche", "super_canne.json"),
    "Méga Canne":  os.path.join(JSON_DIR, "pêche", "mega_canne.json"),
}

REGION_TO_GEN = {
    "Kanto":  "gen1",
    "Johto":  "gen2",
    "Hoenn":  "gen3",
    "Sinnoh": "gen4",
    "Unys":   "gen5",
}




fishing_in_progress: set[int] = set()

def load_rod_data(rod_name: str, region: str):
    gen = REGION_TO_GEN.get(region)
    if not gen:
        print(f"[DEBUG] région='{region}' → gen='{gen}'")
        return [], []

    def _load(filename):
        filepath = os.path.join(JSON_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            eau_types = {"eau", "water"}
            filtered = [
                p for p in data
                if any(t.lower() in eau_types for t in p.get("type", []))
            ]
            print(f"[DEBUG] {filename} → {len(data)} total, {len(filtered)} de type Eau")
            return filtered
        except FileNotFoundError:
            print(f"[DEBUG] Fichier introuvable : {filepath}")
            return []

    normal = _load(f"pokemon_{gen}_normal.json")
    shiny  = _load(f"pokemon_{gen}_shiny.json")
    return normal, shiny

# Modifie load_fishing_items pour prendre la canne en paramètre
def load_fishing_items(rod_name: str) -> list:
    filepath = ROD_ITEMS_FILES.get(rod_name)
    if not filepath:
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def get_user_region(cur, user_id: str) -> str | None:
    cur.execute("SELECT region FROM user_regions WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None


def get_available_rods(user_id: str) -> list[str]:
    """Retourne les cannes que le joueur possède dans son inventaire."""
    from inventory_db import get_inventory
    inventory = get_inventory(user_id)
    owned_items = {item["name"] for item in inventory if item["quantity"] > 0}
    return [rod for rod in RODS if rod in owned_items]


def save_fish_capture(user_id: str, pokemon: dict, is_shiny: bool):
    from new_db  import save_new_capture
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


# -----------------------
# CHOIX DE LA CANNE
# -----------------------
async def ask_rod_choice(ctx, available_rods: list[str]) -> str | None:
    result = asyncio.get_event_loop().create_future()

    class RodSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=rod, emoji=RODS[rod]["emoji"])
                for rod in available_rods
            ]
            super().__init__(placeholder="Choisis ta canne...", options=options)

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ Ce n'est pas ton choix !", ephemeral=True)
                return
            result.set_result(self.values[0])
            await interaction.response.defer()

    class RodView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.add_item(RodSelect())

        async def on_timeout(self):
            if not result.done():
                result.set_result(None)

    view = RodView()
    msg = await ctx.send(
        f"{ctx.author.mention} 🎣 **Quelle canne veux-tu utiliser ?**",
        view=view
    )

    chosen = await result
    await msg.delete()
    return chosen


# -----------------------
# COMMANDE !peche
# -----------------------
def setup_fishing(bot: commands.Bot, cur):

    @bot.command()
    async def peche(ctx):
        user_id = ctx.author.id
        user_id_str = str(user_id)

        # Vérif pêche déjà en cours
        if user_id in fishing_in_progress:
            await ctx.send(
                f"{ctx.author.mention} 🎣 Tu as déjà une ligne à l'eau !",
                delete_after=5
            )
            return

        # Vérif région
        region = get_user_region(cur, user_id_str)
        if not region:
            await ctx.send(
                f"{ctx.author.mention} ❌ Pas de région choisie ! Utilise `!region`.",
                delete_after=5
            )
            return

        # Vérif cannes disponibles
        available_rods = get_available_rods(user_id_str)
        if not available_rods:
            await ctx.send(
                f"{ctx.author.mention} ❌ Tu n'as aucune canne à pêche ! "
                f"Procure-toi une **Canne**, une **Super Canne** ou une **Méga Canne**.",
                delete_after=8
            )
            return
        
    
        # Vérif connexion au vocal
        # Vérif connexion au vocal via le guild
        VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID_COPAING"))
        GUILD_ID = int(os.getenv("GUILD_ID")) 

        print(f"[DEBUG] guild={guild}")
        print(f"[DEBUG] member={member}")
        print(f"[DEBUG] voice={member.voice if member else 'None'}")
        print(f"[DEBUG] channel_id={member.voice.channel.id if member and member.voice and member.voice.channel else 'None'}")
        print(f"[DEBUG] VOICE_CHANNEL_ID={VOICE_CHANNEL_ID}")

        guild = bot.get_guild(GUILD_ID)
        if guild is None:
            await ctx.send("❌ Impossible de trouver le serveur.", delete_after=5)
            return

        member = guild.get_member(user_id)
        if member is None:
            await ctx.send("❌ Impossible de te trouver dans le serveur.", delete_after=5)
            return

        voice_state = member.voice
        in_correct_channel = (
            voice_state is not None
            and voice_state.channel is not None
            and voice_state.channel.id == VOICE_CHANNEL_ID
        )

        if not in_correct_channel:
            await ctx.send(
                f"{ctx.author.mention} 🔇 Tu dois être connecté au salon vocal pour lancer ta ligne !",
                delete_after=8
            )
            return

        # Choix de la canne (auto si une seule)
        if len(available_rods) == 1:
            chosen_rod = available_rods[0]
            await ctx.send(
                f"{ctx.author.mention} 🎣 Tu utilises ta **{chosen_rod}**.",
                delete_after=5
            )
        else:
            chosen_rod = await ask_rod_choice(ctx, available_rods)
            if chosen_rod is None:
                await ctx.send(
                    f"{ctx.author.mention} ⏱️ Temps écoulé, pêche annulée.",
                    delete_after=5
                )
                return

        # Charge les Pokémon de la canne choisie
        normal_pool, shiny_pool = load_rod_data(chosen_rod, region)
        if not normal_pool:
            await ctx.send(
                f"{ctx.author.mention} ❌ Aucun Pokémon disponible pour la **{chosen_rod}** dans **{region}**.",
                delete_after=5
            )
            return

        fishing_in_progress.add(user_id)

        wait_time = random.randint(FISH_TIMER_MIN, FISH_TIMER_MAX)
        minutes = wait_time // 60
        seconds = wait_time % 60

        
        print(f"[PÊCHE] {ctx.author} (ID: {user_id}) | Canne : {chosen_rod} | Région : {region} | Attente : {wait_time}s")

        try:
            dm = await ctx.author.create_dm()
            await dm.send(
                f"🎣 **Tu lances ta {chosen_rod} dans les eaux de {region} !**\n"
                f"⏳ Quelque chose va peut-être mordre... Reste à l'affût !"
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

        roll = random.random()

        # --- CAS 1 : Rien (40%) ---
        if roll < NO_CATCH_RATE:
            await dm.send(
                "💨 **Rien au bout de la ligne...**\n"
                "Aucun Pokémon n'a mordu. Retente ta chance !"
            )
            return

        # --- CAS 2 : Item (30%) ---
        if roll < NO_CATCH_RATE + ITEM_RATE:
            fishing_items = load_fishing_items(chosen_rod)
            if fishing_items:
                found_item = random.choice(fishing_items)
                from inventory_db import add_item
                add_item(
                    user_id=user_id_str,
                    name=found_item["item_name"],
                    quantity=1,
                    rarity=found_item.get("rarity", "commun"),
                    description=found_item.get("description", ""),
                    image=found_item.get("image", ""),
                    extra=found_item.get("extra"),
                    price=found_item.get("price"),
                )
                embed = discord.Embed(
                    title="🎣 Tu as remonté un item !",
                    description=f"**{found_item['item_name']}** a été ajouté à ton inventaire.",
                    color=discord.Color.green()
                )
                if found_item.get("image"):
                    embed.set_thumbnail(url=found_item["image"])
                if found_item.get("description"):
                    embed.add_field(name="Description", value=found_item["description"], inline=False)
                embed.add_field(name="Rareté", value=found_item.get("rarity", "commun").capitalize(), inline=True)
                embed.set_footer(text=f"Région : {region} | Canne : {chosen_rod}")
                await dm.send(embed=embed)
                return

        # --- CAS 3 : Pokémon (30%, ou fallback) ---
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
        embed.set_footer(text="✨ Incroyable ! Un Pokémon Shiny !" if is_shiny else f"Région : {region} | Canne : {chosen_rod}")

        await dm.send(embed=embed)