import discord
from discord.ext import commands, tasks
import random, asyncio, os, json

TARGET_USER_ID_CROCO = int(os.getenv("TARGET_USER_ID_CROCO"))


import datetime
import pytz

# Heure aléatoire générée une fois par jour
_daily_spawn_time = None
_last_generated_date = None

def get_daily_spawn_window():
    """Génère (ou récupère) l'heure de spawn aléatoire du jour."""
    global _daily_spawn_time, _last_generated_date
    
    today = datetime.date.today()
    if _last_generated_date != today:
        # Nouvelle journée → nouvelle heure aléatoire entre 20h30 et 22h30
        # (22h30 + 1h = 23h30 max)
        minutes_offset = random.randint(0, 120)  # 0 à 120 min après 20h30
        _daily_spawn_time = datetime.time(20, 30) 
        _daily_spawn_time = (
            datetime.datetime.combine(today, datetime.time(20, 30))
            + datetime.timedelta(minutes=minutes_offset)
        ).time()
        _last_generated_date = today
    
    return _daily_spawn_time

def is_in_spawn_window() -> bool:
    """Retourne True si on est dans la fenêtre d'1h du jour."""
    now = datetime.datetime.now()  # adapte avec pytz si tu as un timezone
    today = now.date()
    
    spawn_start = datetime.datetime.combine(today, get_daily_spawn_window())
    spawn_end = spawn_start + datetime.timedelta(hours=1)
    
    return spawn_start <= now <= spawn_end


def is_battle_time():
    def predicate(ctx):
        return is_in_spawn_window()
    return commands.check(predicate)


def is_croco():
    def predicate(ctx):
        return ctx.author.id == TARGET_USER_ID_CROCO
    return commands.check(predicate)



# add_pokemon.py
import discord
from discord.ext import commands
import os, random, json
from utils import is_croco
from new_db import save_new_capture  # ou save_capture selon ton usage

import stat  # pour les stats

script_dir = os.path.dirname(os.path.abspath(__file__))
json_dir = os.path.join(script_dir, "json")



async def spawn_pokemon_for_user(user, json_file="pokemon_gen1_normal.json", shiny_rate=64):
    """
    Génère un Pokémon pour un utilisateur, d'abord en décidant s'il est shiny ou non,
    puis en le tirant dans le JSON correspondant.
    """
    # Roll shiny d'abord
    is_shiny = (random.randint(1, shiny_rate) == 1)

    # Choisir le fichier JSON selon shiny ou normal
    chosen_file = json_file
    if is_shiny:
        chosen_file = json_file.replace("_normal.json", "_shiny.json")

    # Charger le JSON choisi
    data = load_json_file(chosen_file)
    if data is None:
        print(f"❌ Fichier {chosen_file} introuvable.")
        return None, False

    # Tirage du Pokémon dans le JSON choisi
    pokemon = random.choice(data)

    # IV & stats
    ivs = generate_ivs()
    stats_with_iv = apply_ivs(pokemon["stats"], ivs)

    # Sauvegarde
    save_new_capture(user.id, pokemon["name"], ivs, stats_with_iv, pokemon)

    return pokemon["name"], is_shiny



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
    return { stat: base_stats[stat] + ivs[stat] for stat in base_stats }

def load_json_file(filename):
    path = os.path.join(json_dir, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def setup_addpokemon_command(bot):
    
    @bot.command(name="addpokemon")
    @is_croco()
    async def addpokemon(ctx, user: discord.User, json_file: str, shiny_rate: int = 64):
        """
        Donne un Pokémon aléatoire depuis un fichier JSON à un utilisateur.
        !addpokemon @user pokemon_gen1_normal.json 64
        """
        data = load_json_file(json_file)
        if data is None:
            await ctx.send(f"❌ Fichier `{json_file}` introuvable.")
            return

        # Choix aléatoire du Pokémon
        pokemon = random.choice(data)
        is_shiny = (random.randint(1, shiny_rate) == 1)

        if is_shiny and any(p["name"] == pokemon["name"] + "_shiny" for p in data):
            # On remplace par la version shiny si elle existe
            shiny_match = next((p for p in data if p["name"] == pokemon["name"] + "_shiny"), None)
            if shiny_match:
                pokemon = shiny_match

        # Génération IV et stats
        ivs = generate_ivs()
        stats_with_iv = apply_ivs(pokemon["stats"], ivs)

        # Sauvegarde
        save_new_capture(user.id, pokemon["name"], ivs, stats_with_iv, pokemon)

        shiny_text = "✨ " if is_shiny else ""
        await ctx.send(f"🎉 {user.mention} a reçu un Pokémon aléatoire {shiny_text}**{pokemon['name']}** !")
