
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
import random, asyncio, os, json
from dotenv import load_dotenv
import time
from PIL import Image, ImageDraw, ImageFont

from combat.menu_combat import SelectionView

import stat

import requests
import io
import uuid
from event.croco_event import setup_croco_event
from event.raid import setup_raid
from BDD.money_view import setup_money

from event.event_climatique import setup_event_climatique, CLIMATIC_EVENTS, filter_pools_by_types, get_allowed_types_for_current_state

from utils import is_in_spawn_window

from utils import  get_daily_spawn_window

from casino.casino_view import setup_casino

import unicodedata

from event.forme_regionale import setup_forme_regionale, pick_forme_regionale_pokemon, load_regional_pool
from event.quiz_spawn import setup_quiz_commands
from event.devine_poke import setup_guess_pokemon_command

from event.dupont_event import run_interaction_personnage


from event.dupont_event import setup_dupont_command

from combat.utils import normalize_text

from pokedex import setup_pokedex, setup_new_pokedex



from io import BytesIO

from db import save_capture, get_captures
from new_db import save_new_capture, get_new_captures, setupxp

from BDD.inventory_view import setup_inventory
from utils import is_croco

from BDD.money_db import add_money
from shop.shop_view import setup_shop

from BDD.badge_view import setup_badges
from regions import setup_regions, setup_region # region_command

import os
import psycopg2
import discord
from discord.ui import Select, View
from dotenv import load_dotenv

from regions import setup_fishing

#tets
# ──────────────────────────────────────────────────────────────────────────────
# CHENIL — Configuration
# ──────────────────────────────────────────────────────────────────────────────
SECONDES_PAR_TRANCHE = 120   # Secondes de vocal pour gagner de l'XP
TICK_MINUTES         = 1     # Fréquence du tick chenil (en minutes)

# Tracking vocal en mémoire : user_id (int) → timestamp d'entrée
_vocal_start: dict[int, float] = {}

# Timestamp du dernier tick chenil
_last_chenil_tick: float = 0.0


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()
#

# Ici, déclare la constante globale :
CHECK_VOICE_CHANNEL_INTERVAL = 120  # secondes

allowed_user = {}  # dictionnaire global : guild_id -> user_id autorisé à capturer

# Chargement du .env
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID_COPAING"))
TEXT_CHANNEL_ID = int(os.getenv("CHANNEL_ID_COPAING"))
TARGET_USER_ID_CROCO = int(os.getenv("TARGET_USER_ID_CROCO"))
ROLE_ID = int(os.getenv("ROLE_ID"))  # ID du rôle à mentionner

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True




DEFAULT_SHINY_RATE = 64


bot = commands.Bot(command_prefix="!", intents=intents)

dm_spawn_tasks = {}  # { member_id: asyncio.Task }
dm_spawn_tasks = {}           # { member_id: asyncio.Task }
dm_spawn_remaining_time = {}  # { member_id: int (secondes restantes) }


# Chargement des données Pokémon (chemin absolu du script)
script_dir = os.path.dirname(os.path.abspath(__file__))
json_dir = os.path.join(script_dir, "json")

#image
images_dir = os.path.join(script_dir, "images")



# --- Fonds par type (fichiers à mettre dans /images)
TYPE_BACKGROUNDS = {
    "feu": "bg_feu.png",
    "eau": "bg_eau.png",
    "plante": "bg_plante.png",
    "electrique": "bg_electrique.png",  # (clé sans accent pour simplifier)
    "roche": "bg_roche.png",
    "sol": "bg_sol.png",
    "glace": "bg_glace.png",
    "psy": "bg_psy.png",
    "spectre": "bg_spectre.png",
    "dragon": "bg_dragon.png",

    "acier": "bg_acier.png",
    "fee": "bg_fee.png",
    "poison": "bg_poison.png",
    "combat": "bg_combat.png",
    "insecte": "bg_insecte.png",
    "vol": "bg_vol.png",
    
    "tenebres": "bg_tenebres.png",
    "normal": "bg_normal.png",
}
DEFAULT_BACKGROUND = "arriere_plan_herbe.png"

def _norm(s: str) -> str:
    # normalise pour matcher les clés ci-dessus (sans accents)
    return (s or "").lower()\
        .replace("é","e").replace("è","e").replace("ê","e")\
        .replace("à","a").replace("ù","u").replace("ï","i").replace("ô","o")

from PIL import Image  # déjà importé plus haut, OK

def get_background_image_for_pokemon(pokemon) -> Image.Image:
    """
    Retourne une Image PIL en fonction du premier type uniquement.
    Repli sur DEFAULT_BACKGROUND si fichier manquant ou aucun type.
    """
    types = pokemon.get("type") or []
    if not isinstance(types, list):
        types = [types]

    # On ne garde que le premier type s'il existe
    first_type = _norm(types[0]) if types else None

    # Résolution du fichier de fond
    if first_type:
        filename = TYPE_BACKGROUNDS.get(first_type, DEFAULT_BACKGROUND)
    else:
        filename = DEFAULT_BACKGROUND

    path = os.path.join(images_dir, filename)
    if not os.path.exists(path):
        path = os.path.join(images_dir, DEFAULT_BACKGROUND)

    return Image.open(path).convert("RGBA")






with open(os.path.join(json_dir, "attack_data.json"), "r", encoding="utf-8") as f:
    full_attack_data = json.load(f)




# Charger les données des sprites de types
type_sprite_path = os.path.join(json_dir, "pokemon_type_sprites.json")

with open(type_sprite_path, "r", encoding="utf-8") as f:
    type_sprite_data = json.load(f)

# Dictionnaire de type → sprite
type_sprites = {entry["type"].lower(): entry["image"] for entry in type_sprite_data}


item_file_path = os.path.join(json_dir, "item_capture.json")

with open(item_file_path, "r", encoding="utf-8") as f:
    items_data = json.load(f)

pokeball_url = next((item["image"] for item in items_data if item["name"].lower() == "pokéball"), None)

##############################################################
##############################################################
##############################################################



#####################################
# --- 🔥 GEN 1 — KANTO ---
#####################################
pokemon_file_path = os.path.join(json_dir, "pokemon_gen1_normal.json")
with open(pokemon_file_path, "r", encoding="utf-8") as f:
    kanto_pokemon_data = json.load(f)

with open(os.path.join(json_dir, "pokemon_gen1_shiny.json"), "r", encoding="utf-8") as f:
    kanto_shiny_data = json.load(f)

#####################################
# --- 🔥 GEN 2 — JOHTO ---
#####################################
johto_pokemon_data = []
johto_shiny_data = []

gen2_normal_path = os.path.join(json_dir, "pokemon_gen2_normal.json")
if os.path.exists(gen2_normal_path):
    with open(gen2_normal_path, "r", encoding="utf-8") as f:
        johto_pokemon_data = json.load(f)

gen2_shiny_path = os.path.join(json_dir, "pokemon_gen2_shiny.json")
if os.path.exists(gen2_shiny_path):
    with open(gen2_shiny_path, "r", encoding="utf-8") as f:
        johto_shiny_data = json.load(f)

#####################################
# --- 🔥 GEN 3 — HOENN ---
#####################################
hoenn_pokemon_data = []
hoenn_shiny_data = []

gen3_normal_path = os.path.join(json_dir, "pokemon_gen3_normal.json")
if os.path.exists(gen3_normal_path):
    with open(gen3_normal_path, "r", encoding="utf-8") as f:
        hoenn_pokemon_data = json.load(f)

gen3_shiny_path = os.path.join(json_dir, "pokemon_gen3_shiny.json")
if os.path.exists(gen3_shiny_path):
    with open(gen3_shiny_path, "r", encoding="utf-8") as f:
        hoenn_shiny_data = json.load(f)

#####################################
# --- 🔥 GEN 4 — SINNOH ---
#####################################
sinnoh_pokemon_data = []
sinnoh_shiny_data = []

gen4_normal_path = os.path.join(json_dir, "pokemon_gen4_normal.json")
if os.path.exists(gen4_normal_path):
    with open(gen4_normal_path, "r", encoding="utf-8") as f:
        sinnoh_pokemon_data = json.load(f)

gen4_shiny_path = os.path.join(json_dir, "pokemon_gen4_shiny.json")
if os.path.exists(gen4_shiny_path):
    with open(gen4_shiny_path, "r", encoding="utf-8") as f:
        sinnoh_shiny_data = json.load(f)

#####################################
# --- 🔥 GEN 5 — UNYS ---
#####################################
unys_pokemon_data = []
unys_shiny_data = []

gen5_normal_path = os.path.join(json_dir, "pokemon_gen5_normal.json")
if os.path.exists(gen5_normal_path):
    with open(gen5_normal_path, "r", encoding="utf-8") as f:
        unys_pokemon_data = json.load(f)

gen5_shiny_path = os.path.join(json_dir, "pokemon_gen5_shiny.json")
if os.path.exists(gen5_shiny_path):
    with open(gen5_shiny_path, "r", encoding="utf-8") as f:
        unys_shiny_data = json.load(f)


#####################################
# --- 🔥 QG Team Rocket 
#####################################
rocket_pokemon_data = []
rocket_shiny_data = []

rocket_normal_path = os.path.join(json_dir, "pokemon_rocket_normal.json")
if os.path.exists(rocket_normal_path):
    with open(rocket_normal_path, "r", encoding="utf-8") as f:
        rocket_pokemon_data = json.load(f)

rocket_shiny_path = os.path.join(json_dir, "pokemon_rocket_shiny.json")
if os.path.exists(rocket_shiny_path):
    with open(rocket_shiny_path, "r", encoding="utf-8") as f:
        rocket_shiny_data = json.load(f)




#####################################
# --- 🔥 POOLS GLOBAUX (toutes régions) ---
#####################################
full_pokemon_data = (
    kanto_pokemon_data +
   johto_pokemon_data +
    hoenn_pokemon_data +
    sinnoh_pokemon_data +
    unys_pokemon_data
)

full_pokemon_shiny_data = (
    kanto_shiny_data +
    johto_shiny_data +
    hoenn_shiny_data +
    sinnoh_shiny_data +
    unys_shiny_data
)

#####################################
# --- 🔥 MAPPING RÉGION → VARIABLES ---
#####################################
REGION_DATA_MAP = {
    "Kanto": (kanto_pokemon_data, kanto_shiny_data),
    "Johto": (johto_pokemon_data, johto_shiny_data),
    "Hoenn": (hoenn_pokemon_data, hoenn_shiny_data),
    "Sinnoh": (sinnoh_pokemon_data, sinnoh_shiny_data),
    "Unys": (unys_pokemon_data, unys_shiny_data),
    "Rocket" :(rocket_pokemon_data, rocket_shiny_data),
    
    

}
        
full_pokedex = full_pokemon_data.copy() 
        #####################################
# --- MEGA ---
#####################################

mega_path = os.path.join(json_dir, "mega.json")
if os.path.exists(mega_path):
    with open(mega_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        full_pokedex.extend(data)

# Shiny des méga (et des récompenses de raid, mêmes noms) : pokédex uniquement,
# pas ajoutés aux pools de spawn
pokedex_shiny_data = list(full_pokemon_shiny_data)
mega_shiny_path = os.path.join(json_dir, "mega_shiny.json")
if os.path.exists(mega_shiny_path):
    with open(mega_shiny_path, "r", encoding="utf-8") as f:
        pokedex_shiny_data.extend(json.load(f))

# Formes régionales (Alola, Galar) : visibles dans le pokédex même si l'event est inactif
full_pokedex.extend(load_regional_pool("alola.json"))
full_pokedex.extend(load_regional_pool("galar.json"))
##############################################################
##############################################################

# Dictionnaires par serveur
current_pokemon = {}         # guild_id -> nom Pokémon
current_pokemon_data = {}    # guild_id -> données Pokémon
pokemon_caught = {}          # guild_id -> bool
spawn_task = {}              # guild_id -> asyncio.Task
current_auto_pokemon = {}   # guild_id -> nom Pokémon spawn auto

spawn_remaining_time = {}  # guild_id -> secondes restantes

spawn_origin_manual = {}  # guild_id -> True si spawn manuel, False sinon

ban_users = {}  # guild_id -> {user_id: timestamp_du_ban}
catch_in_progress = set()  # guild_id en cours de capture


catch_lock = asyncio.Lock()  # Verrou global catch (tu peux faire un dict par guild si besoin)



def reset_spawn(guild_id):
    current_pokemon[guild_id] = None
    current_pokemon_data[guild_id] = None
    current_auto_pokemon[guild_id] = None
    allowed_user.pop(guild_id, None)
    pokemon_caught[guild_id] = True
    spawn_origin_manual[guild_id] = False

def clean_text(text):
    return ''.join(c for c in text if c.isascii())


attack_type_map = {normalize_text(attack["name"]): attack["type"].lower() for attack in full_attack_data}


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
        stat: base_stats[stat] + ivs[stat]
        for stat in base_stats
    }

####################################################################################################################
####################################################################################################################
####################################################################################################################

async def spawn_pokemon(channel, force=False, author=None, target_user: discord.Member = None, pokemon_name: str = None, shiny_rate=64, dm_user: discord.Member = None, ignore_climate=False):
    guild_id = channel.guild.id

    # Gestion des spawns manuel vs auto
    if force:
        spawn_origin_manual[guild_id] = True
    else:
        spawn_origin_manual[guild_id] = False
        if not dm_user and current_auto_pokemon.get(guild_id):
            # Le Pokémon auto précédent n'a pas été capturé : il s'enfuit, on passe au suivant
            print(f"[INFO] {current_auto_pokemon[guild_id]} non capturé, il s'enfuit.")
            reset_spawn(guild_id)

    # -----------------------
    # FILTRAGE PAR RÉGION + CLIMAT
    # -----------------------
    # Par défaut, récupère les pools courants (qui tiennent compte du climat) si le bot expose l'API
    if not ignore_climate and hasattr(bot, "get_current_pokemon_pools"):
        try:
            region_pokemon_data, region_shiny_data = bot.get_current_pokemon_pools()
        except Exception:
            region_pokemon_data = full_pokemon_data
            region_shiny_data = full_pokemon_shiny_data
    else:
        region_pokemon_data = full_pokemon_data
        region_shiny_data = full_pokemon_shiny_data

    # Si spawn en DM, on peut utiliser la région de l'utilisateur (puis appliquer le filtre climatique localement)
    if dm_user:
        cur.execute("SELECT region FROM user_regions WHERE user_id = %s", (str(dm_user.id),))
        row = cur.fetchone()
        user_region = row[0] if row else None

        if user_region and user_region in REGION_DATA_MAP:
            region_pokemon_data, region_shiny_data = REGION_DATA_MAP[user_region]

            # Applique le filtrage climatique (si disponible) sur les pools régionaux
            try:
                allowed = get_allowed_types_for_current_state(bot) if getattr(bot, "climate_enabled", False) and hasattr(bot, "climate_state") else []
                if allowed:
                    region_pokemon_data, region_shiny_data = filter_pools_by_types(region_pokemon_data, region_shiny_data, allowed)

                # Sécurité : si la liste est vide, fallback sur le pool global
                if not region_pokemon_data:
                    region_pokemon_data = full_pokemon_data
                    region_shiny_data = full_pokemon_shiny_data
            except Exception:
                # en cas d'erreur dans le filtre, on fallback proprement
                region_pokemon_data = full_pokemon_data
                region_shiny_data = full_pokemon_shiny_data

    # -----------------------
    # CHOIX DU POKÉMON
    # -----------------------
    if pokemon_name:
        pokemon = next((p for p in region_pokemon_data if p["name"].lower() == pokemon_name.lower()), None)
        if not pokemon:
            await channel.send(f"❌ Le Pokémon `{pokemon_name}` est introuvable dans le pool de spawn.")
            return

        is_shiny = (random.randint(1, shiny_rate) == 1)
        if is_shiny:
            shiny_match = next((p for p in region_shiny_data if p["name"].lower().replace("_shiny", "") == pokemon_name.lower()), None)
            if shiny_match:
                pokemon = shiny_match

        print(f"[DEBUG] shiny_rate={shiny_rate}, is_shiny={is_shiny}, pokemon={pokemon['name']}".encode('utf-8', errors='replace').decode('utf-8'))
    else:
        is_shiny = (random.randint(1, shiny_rate) == 1)
        # Debug: log climate state and pool sizes
        try:
            print(f"[CLIMAT DEBUG] climate_state={getattr(bot,'climate_state',None)}")
            allowed = get_allowed_types_for_current_state(bot) if hasattr(bot, 'climate_state') else []
            print(f"[CLIMAT DEBUG] allowed_types={allowed}")
            print(f"[CLIMAT DEBUG] pool_sizes: normal={len(region_pokemon_data)} shiny={len(region_shiny_data)}")
        except Exception as e:
            print(f"[CLIMAT DEBUG] error reading climate state: {e}")

        regional = pick_forme_regionale_pokemon(bot, is_shiny)
        if regional:
            pokemon, is_shiny = regional, regional["name"].endswith("_shiny")
        else:
            pokemon = random.choice(region_shiny_data if is_shiny else region_pokemon_data)
        print(f"[DEBUG] shiny_rate={shiny_rate}, is_shiny={is_shiny}, pokemon={pokemon['name']}".encode('utf-8', errors='replace').decode('utf-8'))

    # -----------------------
    # NOM AFFICHÉ
    # -----------------------
    if is_shiny and not pokemon["name"].endswith("_shiny"):
        pokemon_name_spawned = pokemon["name"] + "_shiny"
    else:
        pokemon_name_spawned = pokemon["name"]

    if not dm_user:
        if force:
            current_pokemon[guild_id] = pokemon_name_spawned
        else:
            current_auto_pokemon[guild_id] = pokemon_name_spawned
            current_pokemon[guild_id] = pokemon_name_spawned

    # -----------------------
    # IV ET STATS
    # -----------------------
    ivs = generate_ivs()
    stats_with_iv = apply_ivs(pokemon["stats"], ivs)

    pokemon_instance = dict(pokemon)
    pokemon_instance["ivs"] = ivs
    pokemon_instance["stats_iv"] = stats_with_iv

    if dm_user:
        current_pokemon_data[dm_user.id] = pokemon_instance
        pokemon_caught[dm_user.id] = False
    else:
        current_pokemon_data[guild_id] = pokemon_instance
        pokemon_caught[guild_id] = False
        spawn_origin_manual[guild_id] = force

    if target_user:
        allowed_user[guild_id] = target_user.id
    else:
        allowed_user.pop(guild_id, None)

    # -----------------------
    # CONSTRUCTION DE L'EMBED
    # -----------------------
    if is_shiny:
        display_name = pokemon["name"].replace("_shiny", "") + " ✨"
        title = (
            f"✨ **Un {display_name} brillant sauvage apparaît** grâce à {author.display_name} !"
            if author else
            f"✨ **Un {display_name} brillant sauvage est apparu !**"
        )
        description = "C'est un Pokémon BRILLANT ! Tape vite `!catch` ou '!capture' pour le capturer"
        color = 0xFFD700
    else:
        display_name = pokemon["name"]
        title = (
            f"⚡ Un **{display_name}** sauvage apparaît grâce à {author.display_name} !"
            if author else
            f"Un **{display_name}** sauvage est apparu !"
        )
        description = "C'est un Pokémon BRILLANT ! Tape vite `!catch` ou '!capture' pour le capturer"
        color = 0x00FF00

    if target_user:
        title += f"\n🎯 Seul **{target_user.display_name}** peut le capturer !"

    # -----------------------
    # CRÉATION DE L'IMAGE
    # -----------------------
    composed_file_bytes = None

    try:
        background = get_background_image_for_pokemon(pokemon)
        poke_url = pokemon.get("image", "")

        if not poke_url.startswith("http"):
            await channel.send("❌ Erreur : image du Pokémon invalide.")
            return

        response = requests.get(poke_url, timeout=15)
        pokemon_img = Image.open(BytesIO(response.content)).convert("RGBA").resize((392, 392))

        composed = background.copy()
        x = (background.width - pokemon_img.width) // 2
        y = (background.height - pokemon_img.height) // 2
        composed.paste(pokemon_img, (x, y), pokemon_img)

        output = BytesIO()
        composed.save(output, format="PNG")
        composed_file_bytes = output.getvalue()

    except Exception as e:
        await channel.send("❌ Erreur lors de la création de l'image.")
        print(f"[ERREUR IMAGE SPAWN] {e}")
        return

    # -----------------------
    # ENVOI SUR LE CHANNEL
    # -----------------------
    if not dm_user:
        try:
            channel_embed = discord.Embed(title=title, description=description, color=color)
            channel_embed.set_image(url="attachment://spawn.png")

            file_channel = discord.File(fp=BytesIO(composed_file_bytes), filename="spawn.png")
            content = f"<@&{ROLE_ID}>"
            await channel.send(content=content, embed=channel_embed, file=file_channel)

        except Exception as e:
            print(f"[ERREUR ENVOI CHANNEL] {e}")

    # -----------------------
    # ENVOI EN DM
    # -----------------------
    if dm_user:
        try:
            dm_embed = discord.Embed(title=title, description=description, color=color)
            dm_embed.set_image(url="attachment://spawn.png")

            if target_user:
                dm_embed.add_field(
                    name="🎯 Restriction",
                    value=f"Seul **{target_user.display_name}** peut capturer ce Pokémon.",
                    inline=False
                )

            file_dm = discord.File(fp=BytesIO(composed_file_bytes), filename="spawn.png")
            await dm_user.send(embed=dm_embed, file=file_dm)

        except discord.Forbidden:
            await channel.send(f"⚠️ Impossible d'envoyer un DM à **{dm_user.display_name}** (DMs désactivés).")
        except Exception as e:
            print(f"[ERREUR ENVOI DM] {e}")

    # -----------------------
    # RESET SHINY RATE
    # -----------------------
    if force:
        global DEFAULT_SHINY_RATE
        DEFAULT_SHINY_RATE = 64

####################################################################################################################
####################################################################################################################
####################################################################################################################        


## Intervalle spawn MP
MIN_SPAWN = 15*60*60 # // ici c'est un test 15H /  vrai valeur ->#14400 #4h
MAX_SPAWN = 16*60*60# // ici c'est un test 15H /  vrai valeur ->18000 #5h

@tasks.loop(seconds=120)
async def check_voice_channel():
    # print(f"[DEBUG] check_voice_channel exécutée")  # ← à ajouter temporairement
    bot.last_check_voice_time = time.time()
    vc = bot.get_channel(VOICE_CHANNEL_ID)
    channel = bot.get_channel(TEXT_CHANNEL_ID)
    if channel is None or vc is None:
        return

    guild_id = channel.guild.id
    members_in_vc = [m for m in vc.members if not m.bot]

    if len(members_in_vc) > 0:
        # Lance une tâche individuelle pour chaque membre qui n'en a pas encore
        for member in members_in_vc:
            if member.id not in dm_spawn_tasks or dm_spawn_tasks[member.id] is None or dm_spawn_tasks[member.id].done():
                wait_time = random.randint(MIN_SPAWN, MAX_SPAWN) #### Premier spawn
                minutes, seconds = divmod(wait_time, 60)
                ###

                hours, remainder = divmod(wait_time, 3600)
                minutes, seconds = divmod(remainder, 60)

                if hours > 0:
                    print(f"[INFO] Spawn DM prévu pour {member.display_name} dans {hours}h {minutes} min {seconds} sec.")
                else:
                    print(f"[INFO] Spawn DM prévu pour {member.display_name} dans {minutes} min {seconds} sec.")

                ##
                dm_spawn_tasks[member.id] = asyncio.create_task(
                    wait_and_spawn_dm(wait_time, channel, member)
                )
    else:
        # Plus personne en vocal : on annule toutes les tâches DM en cours
        for member_id, task in list(dm_spawn_tasks.items()):
            if task is not None and not task.done():
                task.cancel()
                print(f"[INFO] Tâche DM annulée pour le membre {member_id} (vocal vide).")
            dm_spawn_tasks[member_id] = None
    # ← AJOUTE ICI
    @check_voice_channel.before_loop
    async def before_check_voice():
        await bot.wait_until_ready()

      
async def wait_and_spawn_dm(wait_time, channel, member: discord.Member):
    try:
        dm_spawn_remaining_time[member.id] = wait_time

        for remaining in range(wait_time, 0, -1):
            await asyncio.sleep(1)
            dm_spawn_remaining_time[member.id] = remaining - 1

            # Print toutes les 60 secondes
            if remaining % 60 == 0 and remaining > 0:
                hours, remainder = divmod(remaining, 3600)
                minutes, seconds = divmod(remainder, 60)
                if hours > 0:
                    print(f"[DM SPAWN] {member.display_name} — spawn dans {hours}h {minutes} min {seconds} sec.")
                else:
                    print(f"[DM SPAWN] {member.display_name} — spawn dans {minutes} min {seconds} sec.")

            # Si le membre a quitté le vocal entre-temps, on arrête
            vc = bot.get_channel(VOICE_CHANNEL_ID)
            if vc is None or member not in vc.members:
                print(f"[INFO] {member.display_name} a quitté le vocal, spawn DM annulé.")
                return

        # Spawn dans les DM du membre, shiny rate = 1/32
        await spawn_pokemon(channel=channel, dm_user=member, shiny_rate=32)
        print(f"[INFO] Pokémon spawné en DM pour {member.display_name}.")

        # Relance automatiquement un nouveau compteur
        vc = bot.get_channel(VOICE_CHANNEL_ID)
        if vc and member in vc.members:
            new_wait = random.randint(MIN_SPAWN, MAX_SPAWN)
            hours, remainder = divmod(new_wait, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                print(f"[INFO] Prochain spawn DM pour {member.display_name} dans {hours}h {minutes} min {seconds} sec.")
            else:
                print(f"[INFO] Prochain spawn DM pour {member.display_name} dans {minutes} min {seconds} sec.")
            dm_spawn_tasks[member.id] = asyncio.create_task(
                wait_and_spawn_dm(new_wait, channel, member)
            )
        else:
            dm_spawn_tasks[member.id] = None

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[ERREUR wait_and_spawn_dm] {e}")
    finally:
        dm_spawn_remaining_time.pop(member.id, None)




@bot.command(name="shutdown")
@is_croco()
async def shutdown(ctx):
    await ctx.send("⏹️ Bot en cours d'arrêt...")
    await bot.close()


@bot.command(name="ban")
@is_croco()
async def ban(ctx, member: discord.Member, duration: int = 10):
    guild_id = ctx.guild.id
    if guild_id not in ban_users:
        ban_users[guild_id] = {}

    ban_users[guild_id][member.id] = time.time() + duration
    await ctx.send(f"⏱ {member.mention} est sous ban pendant {duration} secondes. [LIGNE UNIQUE]")


@bot.command()
@is_croco()
async def unban(ctx, member: discord.Member):
    guild_id = ctx.guild.id
    user_id = member.id

    if guild_id in ban_users and user_id in ban_users[guild_id]:
        del ban_users[guild_id][user_id]
        await ctx.send(f"✅ {member.mention} est libéré du ban par la volonté de Croco 🐊.")
    else:
        await ctx.send(f"ℹ️ {member.mention} n’est pas sous ban.")


def is_under_ban(guild_id, user_id):
    if guild_id in ban_users and user_id in ban_users[guild_id]:
        end_time = ban_users[guild_id][user_id]
        if time.time() < end_time:
            return True
        else:
            del ban_users[guild_id][user_id]
    return False


'''
######################################################################################
######################################################################################
######################################################################################

@bot.command()
async def catch(ctx):
    if ctx.channel.id != TEXT_CHANNEL_ID:
        await ctx.send(f"❌ Cette commande est uniquement disponible dans <#{TEXT_CHANNEL_ID}>.")
        return

    guild_id = ctx.guild.id
    lookup_id = guild_id
    trace_id = str(uuid.uuid4())[:8]

    # 🔒 Empêche les captures simultanées
    if lookup_id in catch_in_progress:
        return
    catch_in_progress.add(lookup_id)

    try:
        # Vérifie le ban
        if is_under_ban(guild_id, ctx.author.id):
            print(f"[TRACE {trace_id}] [LOG] Joueur sous ban, refus.")
            await ctx.send("⏳ Tu es sous ban. Attends encore un peu avant de répondre.")
            return

        # Vérifie la présence dans le salon vocal
        vc = bot.get_channel(VOICE_CHANNEL_ID)
        if vc is None:
            print(f"[TRACE {trace_id}] [LOG] Salon vocal introuvable")
            await ctx.send("❌ Salon vocal introuvable.")
            return
        if ctx.author.id != TARGET_USER_ID_CROCO and ctx.author not in vc.members:
            print(f"[TRACE {trace_id}] [LOG] Auteur pas dans le salon vocal.")
            await ctx.send("❌ Tu dois être dans le salon vocal pour capturer un Pokémon.")
            return

        # Vérifie qu'un Pokémon est présent
        current = current_pokemon.get(guild_id)
        if current is None:
            if pokemon_caught.get(guild_id, False):
                print(f"[TRACE {trace_id}] [LOG] Aucun Pokémon mais déjà capturé, on ne dit rien.")
                return
            await ctx.send(f"❌ Aucun Pokémon à capturer. [TRACE {trace_id}]")
            return

        # Vérifie la restriction d'utilisateur
        if guild_id in allowed_user:
            if ctx.author.id != allowed_user[guild_id]:
                allowed_name = ctx.guild.get_member(allowed_user[guild_id]).display_name
                print(f"[TRACE {trace_id}] [LOG] Pokémon réservé à {allowed_name}")
                await ctx.send(f"❌ Seul {allowed_name} peut capturer ce Pokémon.")
                return

        pokemon_name = current
        pokemon_data = current_pokemon_data[guild_id]

        # Envoi du message Pokéball
        embed_pokeball = discord.Embed(
            description=f"**{ctx.author.display_name} lance une Pokéball !**",
            color=0xFF0000
        )
        if pokeball_url:
            embed_pokeball.set_thumbnail(url=pokeball_url)
        await ctx.send(embed=embed_pokeball)

        # Sauvegarde
        ivs = pokemon_data.get("ivs", {})
        stats_with_iv = pokemon_data.get("stats_iv", pokemon_data["stats"])
        save_new_capture(ctx.author.id, pokemon_name, ivs, stats_with_iv, pokemon_data)

        # 💰 Récompense
        reward_amount = 20
        new_balance = add_money(ctx.author.id, reward_amount)

        embed_captured = discord.Embed(
            description=(
                f"🎉 **{ctx.author.display_name} a capturé {pokemon_name} !\n"
                f"Vise bien l'aveugle**\n\n"
                f"💰 Récompense : **+{reward_amount:,}** Croco dollars\n"
                f"💰🐊 Nouveau solde : **{new_balance:,}** Croco dollars"
            ),
            color=0x00CC66
        )
        if pokemon_data.get("image", ""):
            embed_captured.set_image(url=pokemon_data["image"])
        await ctx.send(embed=embed_captured)

        # Reset du spawn
        reset_spawn(guild_id)

    finally:
        catch_in_progress.discard(lookup_id)

'''
######################################################################################
######################################################################################
######################################################################################

# On définit un cooldown de 1 utilisation toutes les 10 secondes par utilisateur
@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def catch(ctx):
    if ctx.channel.id != TEXT_CHANNEL_ID:
        await ctx.send(f"❌ Cette commande est uniquement disponible dans <#{TEXT_CHANNEL_ID}>.")
        # On reset le cooldown pour que l'utilisateur n'ait pas à attendre s'il s'est trompé de salon
        ctx.command.reset_cooldown(ctx)
        return

    guild_id = ctx.guild.id
    lookup_id = guild_id
    trace_id = str(uuid.uuid4())[:8]

    if lookup_id in catch_in_progress:
        ctx.command.reset_cooldown(ctx) # Empêche de bloquer le cooldown si la commande est spam
        return
    catch_in_progress.add(lookup_id)

    try:
        if is_under_ban(guild_id, ctx.author.id):
            await ctx.send("⏳ Tu es sous ban. Attends encore un peu avant de répondre.")
            return

        vc = bot.get_channel(VOICE_CHANNEL_ID)
        if vc is None:
            await ctx.send("❌ Salon vocal introuvable.")
            return
        if ctx.author.id != TARGET_USER_ID_CROCO and ctx.author not in vc.members:
            await ctx.send("❌ Tu dois être dans le salon vocal pour capturer un Pokémon.")
            ctx.command.reset_cooldown(ctx) # On reset pour qu'il puisse retenter dès qu'il rejoint le vocal
            return

        current = current_pokemon.get(guild_id)
        if current is None:
            if not pokemon_caught.get(guild_id, False):
                await ctx.send(f"❌ Aucun Pokémon à capturer. [TRACE {trace_id}]")
            ctx.command.reset_cooldown(ctx)
            return

        if guild_id in allowed_user and ctx.author.id != allowed_user[guild_id]:
            allowed_name = ctx.guild.get_member(allowed_user[guild_id]).display_name
            await ctx.send(f"❌ Seul {allowed_name} peut capturer ce Pokémon.")
            ctx.command.reset_cooldown(ctx)
            return

        # --- 🎲 SYSTÈME DE CHANCE (1 chance sur 4) ---
        reussite = random.randint(1, 4) # Génère 1, 4
        
        # On envoie d'abord la Pokéball
        embed_pokeball = discord.Embed(
            description=f"**{ctx.author.display_name} lance une Pokéball !**",
            color=0xFF0000
        )
        if pokeball_url:
            embed_pokeball.set_thumbnail(url=pokeball_url)
        await ctx.send(embed=embed_pokeball)

        if reussite == 1:  # Échec 
            print(f"[TRACE {trace_id}] [LOG] Échec de la capture (Tirage: {reussite})")
            await ctx.send(f"💨 **Oh non ! Le Pokémon s'est échappé de la Ball !** Retente dans 10 secondes.")
            return # On s'arrête ici, le cooldown de 10s s'applique !

        # --- 🎉 SUCCESS (Si reussite != 1 ) ---
        pokemon_name = current
        pokemon_data = current_pokemon_data[guild_id]

        ivs = pokemon_data.get("ivs", {})
        stats_with_iv = pokemon_data.get("stats_iv", pokemon_data["stats"])
        save_new_capture(ctx.author.id, pokemon_name, ivs, stats_with_iv, pokemon_data)

        embed_captured = discord.Embed(
            description=(
                f"🎉 **{ctx.author.display_name} a capturé {pokemon_name} !\n"
                f"Vise bien l'aveugle**"
            ),
            color=0x00CC66
        )
        if pokemon_data.get("image", ""):
            embed_captured.set_image(url=pokemon_data["image"])
        await ctx.send(embed=embed_captured)

        # On libère le cooldown si la capture est réussie pour que le prochain Pokémon puisse être capturé direct
        ctx.command.reset_cooldown(ctx) 
        reset_spawn(guild_id)

    finally:
        catch_in_progress.discard(lookup_id)



@catch.error
async def catch_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Calme-toi ! La Pokéball est encore brûlante. Réessaie dans **{error.retry_after:.1f} secondes**.")
    else:
        raise error # Laisse passer les autres types d'erreurs
    


######################################################################################
######################################################################################
######################################################################################

@bot.command()
async def capture(ctx):
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("❌ Cette commande est uniquement disponible en message privé.")
        return

    lookup_id = ctx.author.id
    trace_id = str(uuid.uuid4())[:8]

    # 🔒 Empêche les captures simultanées
    if lookup_id in catch_in_progress:
        return
    catch_in_progress.add(lookup_id)

    try:
        # Vérifie qu'un Pokémon est présent
        current = current_pokemon_data.get(lookup_id)
        if current is None or pokemon_caught.get(lookup_id, False):
            if pokemon_caught.get(lookup_id, False):
                print(f"[TRACE {trace_id}] [LOG] Pokémon déjà capturé en DM.")
                return
            await ctx.send(f"❌ Aucun Pokémon à capturer. [TRACE {trace_id}]")
            return

        pokemon_data = current
        pokemon_name = pokemon_data["name"]

        # Envoi du message Pokéball
        embed_pokeball = discord.Embed(
            description=f"**{ctx.author.display_name} lance une Pokéball !**",
            color=0xFF0000
        )
        if pokeball_url:
            embed_pokeball.set_thumbnail(url=pokeball_url)
        await ctx.send(embed=embed_pokeball)

        # Sauvegarde
        ivs = pokemon_data.get("ivs", {})
        stats_with_iv = pokemon_data.get("stats_iv", pokemon_data["stats"])
        save_new_capture(ctx.author.id, pokemon_name, ivs, stats_with_iv, pokemon_data)

        embed_captured = discord.Embed(
            description=(
                f"🎉 **{ctx.author.display_name} a capturé {pokemon_name} !\n"
                f"Vise bien l'aveugle**"
            ),
            color=0x00CC66
        )
        if pokemon_data.get("image", ""):
            embed_captured.set_image(url=pokemon_data["image"])
        await ctx.send(embed=embed_captured)

        # Reset du spawn DM
        pokemon_caught[lookup_id] = True
        current_pokemon_data.pop(lookup_id, None)

    finally:
        catch_in_progress.discard(lookup_id)

######################################################################################
######################################################################################
######################################################################################


@bot.command()
@is_croco()
async def spawn(ctx, *args):
    shiny_rate = DEFAULT_SHINY_RATE
    target_user = None
    pokemon_name = None

    if len(args) == 0 and not ctx.message.mentions:
    # Pas d'arguments, spawn un Pokémon aléatoire avec shiny_rate par défaut
        await spawn_pokemon(
            channel=ctx.channel,
            force=True,
            author=ctx.author,
            shiny_rate=DEFAULT_SHINY_RATE,
            ignore_climate=True
        )
        return


    args = list(args)

    # Vérifie si le premier argument est une mention
    if ctx.message.mentions:
        target_user = ctx.message.mentions[0]
        # Supprime la mention du texte brut (car args contient les mots tapés)
        mention_str = f"<@{target_user.id}>"
        if mention_str in args:
            args.remove(mention_str)
        elif f"<@!{target_user.id}>" in args:  # Mention avec '!' parfois présente
            args.remove(f"<@!{target_user.id}>")

    # Analyse des autres arguments
    if len(args) == 1:
        if args[0].isdigit():
            shiny_rate = int(args[0])
        else:
            pokemon_name = args[0]
    elif len(args) >= 2:
        pokemon_name = args[0]
        if args[1].isdigit():
            shiny_rate = int(args[1])

    if shiny_rate < 1:
        await ctx.send("❌ Le taux shiny doit être au moins 1.")
        return

    await spawn_pokemon(
        channel=ctx.channel,
        force=True,
        author=ctx.author,
        target_user=target_user,
        pokemon_name=pokemon_name,
        shiny_rate=shiny_rate,
        ignore_climate=True
    )





@bot.command()
@is_croco()
async def timecheck(ctx):
    """
    Indique dans combien de temps la prochaine exécution de la tâche check_voice_channel aura lieu.
    Usage réservé à l'utilisateur Croco.
    """
    if not hasattr(bot, 'last_check_voice_time'):
        await ctx.send("Aucune donnée de dernière vérification disponible.")
        return

    now = time.time()
    elapsed = now - bot.last_check_voice_time

    remaining = max(0, int(CHECK_VOICE_CHANNEL_INTERVAL - elapsed))
    minutes, seconds = divmod(remaining, 60)

    await ctx.send(f"⏰ Prochaine vérification du canal vocal dans {minutes} min {seconds} sec.")



@bot.command()
@is_croco()
async def tempspawn(ctx):
    vc = bot.get_channel(VOICE_CHANNEL_ID)
    if vc is None:
        await ctx.send("❌ Impossible de trouver le salon vocal.")
        return
    members_in_vc = [m for m in vc.members if not m.bot]
    if not members_in_vc:
        await ctx.send("❌ Aucun membre en vocal actuellement.")
        return

    # ❌ Bloc supprimé — on ne crée plus de tâches ici

    embed = discord.Embed(
        title="⏱️ Prochains spawns DM",
        color=0x00FF00
    )
    for member in members_in_vc:
        task = dm_spawn_tasks.get(member.id)
        if task is None or task.done():
            status = "❌ Aucune tâche en cours"
        else:
            remaining = dm_spawn_remaining_time.get(member.id)
            if remaining is not None and remaining > 0:
                minutes, seconds = divmod(remaining, 60)
                status = f"🕐 **{minutes} min {seconds} sec**"
            else:
                status = "🔄 Démarrage en cours..."
        embed.add_field(name=member.display_name, value=status, inline=False)
    await ctx.send(embed=embed)



@check_voice_channel.before_loop
async def before_check_voice():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f"[BOT] Connecté en tant que {bot.user} ({bot.user.id})")
    asyncio.ensure_future(auto_event_loop())
    asyncio.ensure_future(planner_loop(bot, TEXT_CHANNEL_ID))
    if not check_voice_channel.is_running():
        check_voice_channel.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)


from event.event_rocket import setup_rocket 

setup_rocket(bot)

setup_money(bot)


setup_shop(bot)


badges_file = os.path.join(script_dir, "json", "badges.json")

# Charger les données des badges depuis le JSON
with open(badges_file, "r", encoding="utf-8") as f:
    full_badge_data = json.load(f)

# Setup du module badge
setup_badges(bot, full_badge_data)

from event.actu import setup_actu
setup_actu(bot,cur)


setupxp(bot)

setup_casino(bot)



bot.is_under_ban = is_under_ban
setup_pokedex(bot, pokedex_shiny_data, full_pokemon_data, type_sprites, attack_type_map, json_dir)
setup_new_pokedex(bot, pokedex_shiny_data, full_pokedex, type_sprites, attack_type_map, json_dir)

# Initialise le système climatique qui attache l'état sur l'objet `bot`
setup_event_climatique(bot, base_pools=(full_pokemon_data, full_pokemon_shiny_data))
setup_forme_regionale(bot)

print("[DEBUG] Ready to run bot...")


@bot.command(name="climat_on")
@is_croco()
async def climat_on(ctx):
    """Active manuellement le système climatique (démarre la tâche si nécessaire)."""
    if hasattr(bot, "_climate_task") and bot._climate_task is not None and not bot._climate_task.done():
        await ctx.send("✅ Le système climatique est déjà actif.")
        return
    setup_event_climatique(bot, base_pools=(full_pokemon_data, full_pokemon_shiny_data))
    await ctx.send("✅ Système climatique activé manuellement.")


@bot.command(name="climat_off")
@is_croco()
async def climat_off(ctx):
    """Désactive manuellement le système climatique (arrête la tâche en arrière-plan)."""
    if hasattr(bot, "_climate_task") and bot._climate_task is not None:
        try:
            bot._climate_task.cancel()
        except Exception:
            pass
    bot._climate_task = None
    bot.climate_enabled = False
    bot.climate_state = {"time_of_day": "day", "active_event": None, "event_ends_at": None}
    await ctx.send("⛔ Climat désactivé : les spawns utilisent tous les Pokémon.")


@bot.command(name="climat_status")
@is_croco()
async def climat_status(ctx):
    """Affiche l'état climatique courant attaché au bot."""
    state = getattr(bot, "climate_state", None)
    if not state:
        await ctx.send("ℹ️ Le système climatique n'est pas initialisé.")
        return

    active = state.get("active_event")
    ends = state.get("event_ends_at")
    tod = state.get("time_of_day")

    msg = f"⏱️ Time of day: **{tod}**\n"
    if active:
        evt = CLIMATIC_EVENTS.get(active, {})
        emoji = evt.get("emoji", "")
        ends_str = ends.strftime('%Y-%m-%d %H:%M:%S') if ends else 'inconnu'
        msg += f"🔥 Active event: **{active}** {emoji} (jusqu'à {ends_str})\n"
    else:
        msg += "✅ Aucun événement climatique actif.\n"

    # pool sizes
    try:
        normal_pool, shiny_pool = bot.get_current_pokemon_pools()
        msg += f"🔸 Pokémons disponibles (normal): {len(normal_pool)}\n"
        msg += f"✨ Pokémons disponibles (shiny): {len(shiny_pool)}\n"
    except Exception:
        pass

    await ctx.send(msg)


@bot.command(name="climat_list")
@is_croco()
async def climat_list(ctx):
    """Liste les événements climatiques utilisables."""
    lines = []
    for k, v in CLIMATIC_EVENTS.items():
        lines.append(f"{v.get('emoji','')} **{k}** → types: {', '.join(sorted(v.get('types', [])))}")
    await ctx.send("\n".join(lines))


@bot.command(name="climat_force")
@is_croco()
async def climat_force(ctx, event_key: str, hours: int = 2):
    """Force un événement climatique pour une durée donnée (heures)."""
    key = event_key.strip().lower()
    if key not in CLIMATIC_EVENTS:
        await ctx.send(f"❌ Événement inconnu: {key}. Utilise `!climat_list` pour la liste.")
        return

    # assure la présence du système
    if not hasattr(bot, "get_current_pokemon_pools"):
        setup_event_climatique(bot, base_pools=(full_pokemon_data, full_pokemon_shiny_data))

    tz = pytz.timezone("Europe/Paris")
    bot.climate_state["active_event"] = key
    bot.climate_state["event_ends_at"] = datetime.now(tz) + timedelta(hours=hours)

    await ctx.send(f"✅ Événement forcé: **{key}** pour {hours} heure(s).")


from datetime import datetime, timedelta
import pytz

'''
@bot.command()
@is_croco()
async def battletime(ctx):
    spawn_time = get_daily_spawn_window()
    spawn_end = (datetime.datetime.combine(datetime.date.today(), spawn_time) + datetime.timedelta(hours=1)).time()
    await ctx.author.send(f"⚔️ Les combats sont disponibles aujourd'hui entre **{spawn_time.strftime('%Hh%M')}** et **{spawn_end.strftime('%Hh%M')}** !")
'''
'''
'''




# !battle désactivé : les combats sont gérés par un autre projet (remettre @bot.command() pour réactiver)
async def battle(ctx):
    #if not await is_in_spawn_window(bot):
     #   await ctx.send("❌ Le crocodile n'est pas apparu ! Revenez entre 21h30 et 23h30.")
      #  return
    user_id = str(ctx.author.id)
    '''
    # Vérifier la limite de tentatives quotidiennes (3 par jour, reset à 00h)
    from combat.battle_limit import can_battle, increment_daily_attempts
    can_battle_now, attempts = can_battle(user_id, max_attempts=3)
    
    if not can_battle_now:
        await ctx.send(f"❌ Tu as déjà utilisé tes 3 tentatives de combat pour aujourd'hui ! Reviens demain.")
        return
    
    # Incrémenter le compteur de tentatives
    increment_daily_attempts(user_id)
    '''
    captures = get_new_captures(user_id)

    if not captures:
        await ctx.send("Tu n'as aucun Pokémon à utiliser en combat.")
        return

    pokemons = [entry["name"] for entry in captures]
    try :
        view = SelectionView(pokemons, full_pokemon_data, user_id=str(ctx.author.id))
    except ValueError as e:
        await ctx.send(f"❌ {e}\nUtilise la commande pour choisir ta région d'abord.")
        return

    await ctx.send("Choisis jusqu'à 6 Pokémon pour ton équipe de combat :", view=view)
   

'''
@battle.error
async def battle_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.author.send("⚔️ Les combats ne sont pas disponibles maintenant. Ce sera durant 1h entre 21h30 et 22h30.")


setup_croco_event(
    bot,
    VOICE_CHANNEL_ID,
    TEXT_CHANNEL_ID,
    TARGET_USER_ID_CROCO,
    spawn_func=spawn_pokemon,
    role_id=ROLE_ID,
    interval_seconds=60  # ajuste librement
)
'''

setup_inventory(bot)

from shop.receleur import setup_receleur
setup_receleur(bot)
setup_region(bot)
setup_regions()

setup_fishing(bot, cur)

# Événements Dupont désactivés (!event_dupont) : décommenter pour réactiver
#setup_dupont_command(bot)


from event.enquete import setup_enquete
from BDD.inventory_db import add_item, get_inventory
from regions import get_user_region

#setup_enquete(bot, get_user_region, add_item)
# Enquête Dupont désactivée (!parc, !grotte, !entrepot, !preuves, !supprimer_preuves) : décommenter pour réactiver
#setup_enquete(bot, get_user_region=get_user_region)

# Après tes setup_*() :
setup_guess_pokemon_command(
    bot,
    spawn_pokemon=spawn_pokemon,
    role_id=ROLE_ID,
    authorized_user_id=TARGET_USER_ID_CROCO,
    is_under_ban_func=is_under_ban
)
setup_quiz_commands(
    bot,
    spawn_pokemon,
    ROLE_ID,
    is_under_ban_func=is_under_ban,
    authorized_user_id=TARGET_USER_ID_CROCO
)
 
 #  Durée entre chaque événement (en secondes)
EVENT_INTERVAL = 25 * 60  # 1 minute
# ──────────────────────────────────────────────────────────────────
#  Boucle automatique
# ──────────────────────────────────────────────────────────────────


# Variables globales partagées entre la boucle et la commande
next_event_time = None
next_event_name = None
TIMEZONE = pytz.timezone("Europe/Paris")



from BDD.chenil import tick_chenil_xp

# dict persistant entre les tours de boucle  { user_id (int): nb_checks (int) }
chenil_xp_counters: dict[int, int] = {}

from BDD.chenil import setup_chenil

setup_chenil(bot,TEXT_CHANNEL_ID)
setup_raid(bot)
from event.planner import planner_loop
riche_or_not = True

async def auto_event_loop():
    await bot.wait_until_ready()
    global next_event_time, next_event_name

    text_channel  = bot.get_channel(TEXT_CHANNEL_ID)
    voice_channel = bot.get_channel(VOICE_CHANNEL_ID)

    if text_channel is None:
        print(f"[ERREUR] Salon texte introuvable (id={TEXT_CHANNEL_ID}).")
        return
    if voice_channel is None:
        print(f"[ERREUR] Salon vocal introuvable (id={VOICE_CHANNEL_ID}).")
        return

    while not bot.is_closed():
        EVENT_INTERVAL = random.randint(20, 25) * 60 # 20-25 minutes

        # ── Personne dans le vocal ────────────────────────────────────────
        if len(voice_channel.members) == 0:
            next_event_time = None
            next_event_name = None
            chenil_xp_counters.clear()   # reset des compteurs si vocal vide
            # print(f"[AUTO] Personne dans le vocal, vérification dans 1 min...")
            await asyncio.sleep(60)
            continue

        # ── Tick chenil (1 check par minute) ────────────────────────────
        members_humans = [m for m in voice_channel.members if not m.bot]
        await tick_chenil_xp(members_humans, chenil_xp_counters)

        # ── Planification de l'événement ─────────────────────────────────
        # Ajoute marche_noir aux choix seulement s'il est disponible
        if is_marche_noir_available():
            available_events = ["marche_noir", "spawn", "devine", "quiz"] # EVENT dupont enlevé
        else:
            available_events = ["spawn", "devine", "quiz"] # EVENT dupont enlevé
        #if bot.raid_enabled:
         #   available_events.append("raid")
        chosen = random.choice(available_events)

        if chosen == "quiz":
            next_event_name = "🧠 Quiz Pokémon"

        elif chosen == "devine":
            next_event_name = "🔍 Devine le Pokémon"

        elif chosen == "spawn":
            next_event_name = "✨ Spawn Pokémon"

        elif chosen == "dupont":
            next_event_name = "🕵️ Événement Dupont"

        elif chosen == "marche_noir":
            next_event_name = "🌙 Événement Marché Noir"

        elif chosen == "raid":
            next_event_name = "⚔️ Raid Pokémon"

        next_event_time = datetime.now(TIMEZONE) + timedelta(seconds=EVENT_INTERVAL)

        print(
            f"[AUTO] {len(voice_channel.members)} joueur(s) dans le vocal — "
            f"Prochain événement : {next_event_name} "
            f"— dans {EVENT_INTERVAL // 60} min "
            f"(à {next_event_time.strftime('%H:%M:%S')})"
        )

        # ── Attente minute par minute (chenil tick toutes les 60 s) ──────
        elapsed = 0
        while elapsed < EVENT_INTERVAL:
            await asyncio.sleep(60)
            elapsed += 60

            members_humans = [m for m in voice_channel.members if not m.bot]
            if members_humans:
                await tick_chenil_xp(members_humans, chenil_xp_counters)
            else:
                chenil_xp_counters.clear()

        # ── Vérif finale avant lancement ─────────────────────────────────
        if len(voice_channel.members) == 0:
            next_event_time = None
            next_event_name = None
            print(f"[AUTO] Plus personne dans le vocal, événement annulé.")
            await asyncio.sleep(60)
            continue

        print(f"[AUTO] Lancement de : {next_event_name} ({len(voice_channel.members)} joueur(s) présent(s))")
        if chosen == "quiz":
            await bot.run_quiz(text_channel)
        elif chosen == "devine":
            await bot.run_devine(text_channel)
        elif chosen == "spawn":
            await spawn_pokemon(text_channel)
        elif chosen == "dupont":
            await run_interaction_personnage(text_channel, riche_or_not)
        elif chosen == "marche_noir":
            await run_marche_noir(text_channel)
        elif chosen == "raid":
            await bot.run_raid()



from event.preuve_db import get_preuves
from shop.marche_noir import setup_marche_noir, run_marche_noir

# ── Fonction pour vérifier si marche noir est disponible ────────────────────
def is_marche_noir_available():
    """Vérifie si le marché noir est disponible (mardi 20h-00h)."""
    now = datetime.now(TIMEZONE)
    # weekday() : lundi=0, mardi=1, ...
    is_tuesday = now.weekday() == 1
    is_time_right = 20 <= now.hour < 24  # 20h à 23h59
    return is_tuesday and is_time_right

setup_marche_noir(bot)

# !police désactivé avec l'enquête Dupont (remettre @bot.command() pour réactiver)
async def police(ctx):
    global riche_or_not
    preuves = get_preuves(ctx.author.id)
    nombre_preuves = len(preuves)
    
    if nombre_preuves >= 3:
        riche_or_not = False
        embed = discord.Embed(
            title="🚔 La famille Dupont est démasquée !",
            description=(
                f"Grâce aux **{nombre_preuves} preuves** rassemblées par **{ctx.author.display_name}**, "
                f"la justice a enfin pu agir.\n\n"
                f"🔒 **Jean Dupont** et **Bernard Dupont** ont été **arrêtés** et inculpés pour :\n"
                f"> 🔪 **Meurtre**\n"
                f"> 🐾 **Trafic de Pokémon**\n"
                f"> 📒 **Falsification des comptes du casino**\n\n"
                f"🏛️ L'ensemble des **biens de la famille Dupont** a été **réquisitionné** par les autorités : "
                f"le casino, l'entrepôt d'Unys, et toutes leurs autres propriétés sont désormais sous séquestre.\n\n"
                f"🐾 Les Pokémon victimes de leur trafic vont enfin pouvoir être pris en charge et libérés.\n\n"
                f"*La vérité a éclaté au grand jour. Justice est faite.*"
            ),
            color=0xe74c3c
        )
        embed.set_footer(text="Famille Dupont — Arrêtés & Biens réquisitionnés")
    else:
        embed = discord.Embed(
            title="🚔 Dossier de preuves",
            description=(
                f"**{ctx.author.display_name}** possède **{nombre_preuves} preuve(s)**.\n\n"
                f"⚠️ Il te faut encore **{3 - nombre_preuves} preuve(s)** "
                f"pour confondre la famille Dupont..."
            ),
            color=0x3498db
        )
    
    await ctx.send(embed=embed)


@bot.command()
async def timeevent(ctx):
    global next_event_time, next_event_name

    if next_event_time is None or next_event_name is None:
        await ctx.send("⏸️ Aucun événement prévu — le vocal est vide.")
        return

    remaining = next_event_time - datetime.now()
    total_seconds = int(remaining.total_seconds())

    if total_seconds <= 0:
        await ctx.send("⚡ Un événement est sur le point de se lancer !")
        return

    minutes = total_seconds // 60
    seconds = total_seconds % 60

    await ctx.send(
        f"📅 Prochain événement : **{next_event_name}**\n"
        f"⏱️ Dans **{minutes} min {seconds} sec** "
        f"(à {next_event_time.strftime('%H:%M:%S')})"
    )

bot.run(TOKEN)