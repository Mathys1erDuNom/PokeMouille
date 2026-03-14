
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
import random, asyncio, os, json
from dotenv import load_dotenv
import time
from PIL import Image, ImageDraw, ImageFont

from combat.menu_combat_sans_mega import SelectionView

import stat

import requests
import io
import uuid
from croco_event import setup_croco_event
from money_view import setup_money

from utils import is_in_spawn_window

from utils import  get_daily_spawn_window

from casino_view import setup_casino

import unicodedata

from quiz_spawn import setup_quiz_commands
from devine_poke import setup_guess_pokemon_command

from combat.utils import normalize_text

from pokedex import setup_pokedex
from new_pokedex import setup_new_pokedex



from io import BytesIO

from db import save_capture, get_captures
from new_db import save_new_capture, get_new_captures

from inventory_view import setup_inventory
from utils import is_croco

from money_db import add_money
from shop_view import setup_shop

from badge_view import setup_badges
from regions import setup_regions, region_command

import os
import psycopg2
import discord
from discord.ui import Select, View
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()


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
'''
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
'''
#####################################
# --- 🔥 POOLS GLOBAUX (toutes régions) ---
#####################################
full_pokemon_data = (
    kanto_pokemon_data +
    johto_pokemon_data +
    hoenn_pokemon_data +
    sinnoh_pokemon_data 
)

full_pokemon_shiny_data = (
    kanto_shiny_data +
    johto_shiny_data +
    hoenn_shiny_data +
    sinnoh_shiny_data 
)

#####################################
# --- 🔥 MAPPING RÉGION → VARIABLES ---
#####################################
REGION_DATA_MAP = {
    "Kanto": (kanto_pokemon_data, kanto_shiny_data),
    "Johto": (johto_pokemon_data, johto_shiny_data),
    "Hoenn": (hoenn_pokemon_data, hoenn_shiny_data),
    "Sinnoh": (sinnoh_pokemon_data, sinnoh_shiny_data)

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

async def spawn_pokemon(channel, force=False, author=None, target_user: discord.Member = None, pokemon_name: str = None, shiny_rate=64, dm_user: discord.Member = None):
    guild_id = channel.guild.id

    # Gestion des spawns manuel vs auto
    if force:
        spawn_origin_manual[guild_id] = True
    else:
        spawn_origin_manual[guild_id] = False
        if not dm_user and current_auto_pokemon.get(guild_id):
            print(f"[INFO] Un Pokémon auto est déjà présent sur le serveur {guild_id}, on ne remplace pas.")
            return

    # -----------------------
    # FILTRAGE PAR RÉGION
    # -----------------------
    region_pokemon_data = full_pokemon_data
    region_shiny_data = full_pokemon_shiny_data

    if dm_user:
        cur.execute("SELECT region FROM user_regions WHERE user_id = ?", (str(dm_user.id),))
        row = cur.fetchone()
        user_region = row[0] if row else None

        if user_region and user_region in REGION_DATA_MAP:
            region_pokemon_data, region_shiny_data = REGION_DATA_MAP[user_region]

            # Sécurité : si la liste est vide, fallback sur le pool global
            if not region_pokemon_data:
                region_pokemon_data = full_pokemon_data
                region_shiny_data = full_pokemon_shiny_data

    # -----------------------
    # CHOIX DU POKÉMON
    # -----------------------
    if pokemon_name:
        pokemon = next((p for p in region_pokemon_data if p["name"].lower() == pokemon_name.lower()), None)
        if not pokemon:
            await channel.send(f"❌ Le Pokémon `{pokemon_name}` est introuvable dans cette région.")
            return

        is_shiny = (random.randint(1, shiny_rate) == 1)
        if is_shiny:
            shiny_match = next((p for p in region_shiny_data if p["name"].lower().replace("_shiny", "") == pokemon_name.lower()), None)
            if shiny_match:
                pokemon = shiny_match

        print(f"[DEBUG] shiny_rate={shiny_rate}, is_shiny={is_shiny}, pokemon={pokemon['name']}".encode('utf-8', errors='replace').decode('utf-8'))
    else:
        is_shiny = (random.randint(1, shiny_rate) == 1)
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
        description = "C'est un Pokémon BRILLANT ! Tape vite `!catch` pour le capturer !"
        color = 0xFFD700
    else:
        display_name = pokemon["name"]
        title = (
            f"⚡ Un **{display_name}** sauvage apparaît grâce à {author.display_name} !"
            if author else
            f"Un **{display_name}** sauvage est apparu !"
        )
        description = "Tape `!catch` pour le capturer !"
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
    try:
        channel_embed = discord.Embed(title=title, color=color)

        if dm_user:
            channel_embed.description = f"🔒 Un Pokémon a été envoyé en DM à **{dm_user.display_name}** !"
        else:
            channel_embed.description = description

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



@tasks.loop(seconds=120)
async def check_voice_channel():
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
                wait_time = random.randint(60, 90)  # 1min à 1min30 minutes
                minutes, seconds = divmod(wait_time, 60)
                print(f"[INFO] Spawn DM prévu pour {member.display_name} dans {minutes} min {seconds} sec.")
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


async def wait_and_spawn_dm(wait_time, channel, member: discord.Member):
    try:
        for remaining in range(wait_time, 0, -1):
            await asyncio.sleep(1)

            # Si le membre a quitté le vocal entre-temps, on arrête
            vc = bot.get_channel(VOICE_CHANNEL_ID)
            if vc is None or member not in vc.members:
                print(f"[INFO] {member.display_name} a quitté le vocal, spawn DM annulé.")
                return

        # Spawn dans les DM du membre
        await spawn_pokemon(channel=channel, dm_user=member)
        print(f"[INFO] Pokémon spawné en DM pour {member.display_name}.")

        # Relance automatiquement un nouveau compteur
        vc = bot.get_channel(VOICE_CHANNEL_ID)
        if vc and member in vc.members:
            new_wait = random.randint(1800, 2400)
            minutes, seconds = divmod(new_wait, 60)
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
        pass



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




@bot.command()
async def catch(ctx):
    guild_id = ctx.guild.id
    trace_id = str(uuid.uuid4())[:8]  # identifiant court unique pour ce catch
    
    # 🔒 Empêche les captures simultanées sur ce serveur
    if guild_id in catch_in_progress:
        return
    catch_in_progress.add(guild_id)
    
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
            print(f"[TRACE {trace_id}] [LOG] Aucun Pokémon à capturer -> Envoi du message d'erreur.")
            await ctx.send(f"❌ Aucun Pokémon à capturer. [TRACE {trace_id}]")
            return
        
        # Vérifie la restriction d'utilisateur
        if guild_id in allowed_user:
            if ctx.author.id != allowed_user[guild_id]:
                allowed_name = ctx.guild.get_member(allowed_user[guild_id]).display_name
                print(f"[TRACE {trace_id}] [LOG] Pokémon réservé à un autre joueur ({allowed_user[guild_id]} / {allowed_name})")
                await ctx.send(f"❌ Seul {allowed_name} peut capturer ce Pokémon.")
                return
        
        # On a bien un Pokémon
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
        
        # 💰 Récompense en argent pour la capture
        reward_amount = 20  # Vous pouvez ajuster le montant
        new_balance = add_money(ctx.author.id, reward_amount)
        
        # Envoi du message de capture avec la récompense
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
        catch_in_progress.discard(guild_id)



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
            shiny_rate=DEFAULT_SHINY_RATE
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
        shiny_rate=shiny_rate
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

    embed = discord.Embed(
        title="⏱️ Prochains spawns DM",
        color=0x00FF00
    )

    for member in members_in_vc:
        task = dm_spawn_tasks.get(member.id)

        if task is None or task.done():
            status = "❌ Aucune tâche en cours"
        else:
            # On récupère le temps restant depuis spawn_remaining_time si dispo
            # Sinon on indique juste qu'une tâche tourne
            remaining = dm_spawn_remaining_time.get(member.id)
            if remaining and remaining > 0:
                minutes, seconds = divmod(remaining, 60)
                status = f"🕐 **{minutes} min {seconds} sec**"
            else:
                status = "🔄 En cours (temps non disponible)"

        embed.add_field(
            name=member.display_name,
            value=status,
            inline=False
        )

    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    print(f"Bot prêt en tant que {bot.user}")
    check_voice_channel.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

# ✅ AJOUTE ICI
setup_quiz_commands(bot, spawn_pokemon, ROLE_ID, is_under_ban_func=is_under_ban, authorized_user_id=TARGET_USER_ID_CROCO)

setup_money(bot)


setup_shop(bot)


badges_file = os.path.join(script_dir, "json", "badges.json")

# Charger les données des badges depuis le JSON
with open(badges_file, "r", encoding="utf-8") as f:
    full_badge_data = json.load(f)

# Setup du module badge
setup_badges(bot, full_badge_data)



setup_casino(bot)

setup_guess_pokemon_command(
    bot,
    spawn_pokemon=spawn_pokemon,
    role_id=ROLE_ID,
    authorized_user_id=TARGET_USER_ID_CROCO,
    is_under_ban_func=is_under_ban
)

bot.is_under_ban = is_under_ban
setup_pokedex(bot, full_pokemon_shiny_data, full_pokemon_data, type_sprites, attack_type_map, json_dir)
setup_new_pokedex(bot, full_pokemon_shiny_data, full_pokedex, type_sprites, attack_type_map, json_dir)

print("[DEBUG] Ready to run bot...")


import datetime
import pytz


@bot.command()
@is_croco()
async def battletime(ctx):
    spawn_time = get_daily_spawn_window()
    spawn_end = (datetime.datetime.combine(datetime.date.today(), spawn_time) + datetime.timedelta(hours=1)).time()
    await ctx.author.send(f"⚔️ Les combats sont disponibles aujourd'hui entre **{spawn_time.strftime('%Hh%M')}** et **{spawn_end.strftime('%Hh%M')}** !")
    

@bot.command()
async def battle(ctx):
    if not await is_in_spawn_window(bot):
        await ctx.send("❌ Le crocodile n'est pas apparu ! Revenez entre 21h30 et 23h30.")
        return
    user_id = str(ctx.author.id)
    captures = get_new_captures(user_id)

    if not captures:
        await ctx.send("Tu n'as aucun Pokémon à utiliser en combat.")
        return

    pokemons = [entry["name"] for entry in captures]
    view = SelectionView(pokemons, full_pokemon_data)
    await ctx.send("Choisis jusqu’à 6 Pokémon pour ton équipe de combat :", view=view)


@battle.error
async def battle_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.author.send("⚔️ Les combats ne sont pas disponibles maintenant. Ce sera durant 1h entre 21h30 et 22h30.")

'''
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


setup_regions()

@bot.command()
async def region(ctx):
    await region_command(ctx)


bot.run(TOKEN)