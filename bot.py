
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
from croco_event import setup_croco_event


import unicodedata

from quiz_spawn import setup_quiz_commands
from devine_poke import setup_guess_pokemon_command

from combat.utils import normalize_text

from pokedex import setup_pokedex
from new_pokedex import setup_new_pokedex



from io import BytesIO

from db import save_capture, get_captures
from new_db import save_new_capture, get_new_captures


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


item_file_path = os.path.join(json_dir, "item.json")

with open(item_file_path, "r", encoding="utf-8") as f:
    items_data = json.load(f)

pokeball_url = next((item["image"] for item in items_data if item["name"].lower() == "pokéball"), None)

##############################################################
##############################################################
##############################################################

#####################################
# --- 🔥 AJOUT DES FICHIERS GEN 1 ---
#####################################
pokemon_file_path = os.path.join(json_dir, "pokemon_gen1_normal.json")

with open(os.path.join(json_dir, "pokemon_gen1_shiny.json"), "r", encoding="utf-8") as f:
    full_pokemon_shiny_data = json.load(f)

with open(pokemon_file_path, "r", encoding="utf-8") as f:
    full_pokemon_data = json.load(f)

#####################################
# --- 🔥 AJOUT DES FICHIERS GEN 2 ---
#####################################

gen2_normal_path = os.path.join(json_dir, "pokemon_gen2_normal.json")
if os.path.exists(gen2_normal_path):
    with open(gen2_normal_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        full_pokemon_data.extend(data)
        
gen2_shiny_path = os.path.join(json_dir, "pokemon_gen2_shiny.json")
if os.path.exists(gen2_shiny_path):
    with open(gen2_shiny_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        full_pokemon_shiny_data.extend(data)
        

#####################################
# --- 🔥 AJOUT DES FICHIERS GEN 3 ---
#####################################

gen3_normal_path = os.path.join(json_dir, "pokemon_gen3_normal.json")
if os.path.exists(gen3_normal_path):
    with open(gen3_normal_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        full_pokemon_data.extend(data)
        
gen3_shiny_path = os.path.join(json_dir, "pokemon_gen3_shiny.json")
if os.path.exists(gen3_shiny_path):
    with open(gen3_shiny_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        full_pokemon_shiny_data.extend(data)
        

##############################################################
##############################################################
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

def is_croco():
    def predicate(ctx):
        return ctx.author.id == TARGET_USER_ID_CROCO
    return commands.check(predicate)


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




async def spawn_pokemon(channel, force=False, author=None, target_user: discord.Member = None, pokemon_name: str = None, shiny_rate=64):
    guild_id = channel.guild.id

    # Gestion des spawns manuel vs auto
    if force:
        spawn_origin_manual[guild_id] = True
    else:
        spawn_origin_manual[guild_id] = False
        if current_auto_pokemon.get(guild_id):
            print(f"[INFO] Un Pokémon auto est déjà présent sur le serveur {guild_id}, on ne remplace pas.")
            return

    # Choix du Pokémon
    if pokemon_name:
        pokemon = next((p for p in full_pokemon_data if p["name"].lower() == pokemon_name.lower()), None)
        if not pokemon:
            await channel.send(f"❌ Le Pokémon {pokemon_name} est introuvable.")
            return

        is_shiny = (random.randint(1, shiny_rate) == 1)
        if is_shiny:
            shiny_match = next((p for p in full_pokemon_shiny_data if p["name"].lower().replace("_shiny", "") == pokemon_name.lower()), None)
            if shiny_match:
                pokemon = shiny_match

        print(f"[DEBUG] shiny_rate={shiny_rate}, is_shiny={is_shiny}, pokemon={pokemon['name']}".encode('utf-8', errors='replace').decode('utf-8'))
    else:
        is_shiny = (random.randint(1, shiny_rate) == 1)
        pokemon = random.choice(full_pokemon_shiny_data if is_shiny else full_pokemon_data)
        print(f"[DEBUG] shiny_rate={shiny_rate}, is_shiny={is_shiny}, pokemon={pokemon['name']}".encode('utf-8', errors='replace').decode('utf-8'))

    # Nom du Pokémon affiché
    if is_shiny and not pokemon["name"].endswith("_shiny"):
        pokemon_name_spawned = pokemon["name"] + "_shiny"
    else:
        pokemon_name_spawned = pokemon["name"]

    if force:
        current_pokemon[guild_id] = pokemon_name_spawned
    else:
        current_auto_pokemon[guild_id] = pokemon_name_spawned
        current_pokemon[guild_id] = pokemon_name_spawned

    # 🎯 Ajout des IV et stats finales
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

    # 📢 Préparation de l'embed de spawn
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

    # 📷 Création de l'image spawn
    try:
        background = get_background_image_for_pokemon(pokemon)  # <= fond selon type(s)

        poke_url = pokemon.get("image", "")
        if poke_url.startswith("http"):
            response = requests.get(poke_url, timeout=15)
            pokemon_img = Image.open(BytesIO(response.content)).convert("RGBA").resize((392, 392))

            composed = background.copy()
            x = (background.width - pokemon_img.width) // 2
            y = (background.height - pokemon_img.height) // 2
            composed.paste(pokemon_img, (x, y), pokemon_img)

            output = BytesIO()
            composed.save(output, format="PNG")
            output.seek(0)

            file = discord.File(fp=output, filename="spawn.png")
            content = f"<@&{ROLE_ID}>"
            embed.set_image(url="attachment://spawn.png")

            await channel.send(content=content, embed=embed, file=file)
        else:
            await channel.send("Erreur : image du Pokémon invalide.")
    except Exception as e:
        await channel.send("❌ Erreur lors de la création de l'image.")
        print(f"[ERREUR IMAGE SPAWN] {e}")





    if force:
        global DEFAULT_SHINY_RATE
        DEFAULT_SHINY_RATE = 64



@tasks.loop(seconds=120)
async def check_voice_channel():
    bot.last_check_voice_time = time.time()
    # Exemple simple pour un serveur avec ID et channels fixes
    vc = bot.get_channel(VOICE_CHANNEL_ID)
    channel = bot.get_channel(TEXT_CHANNEL_ID)

    if channel is None or vc is None:
        return

    guild_id = channel.guild.id

    if len(vc.members) > 0:
        if guild_id not in spawn_task or spawn_task[guild_id] is None:
            if current_auto_pokemon.get(guild_id) is None:
                wait_time = random.randint(600,1200)  # 10 à 20 minutes
                minutes, seconds = divmod(wait_time, 60)  # ✅ calcule minutes et secondes
                print(f"[INFO] Spawn automatique prévu dans {minutes} min {seconds} sec.")
                spawn_task[guild_id] = asyncio.create_task(wait_and_spawn(wait_time, channel))
    else:
        if guild_id in spawn_task and spawn_task[guild_id] is not None and not spawn_task[guild_id].done():
            spawn_task[guild_id].cancel()
            
            spawn_task[guild_id] = None


async def wait_and_spawn(wait_time, channel):
    guild_id = channel.guild.id
    try:
        for remaining in range(wait_time, 0, -1):
            spawn_remaining_time[guild_id] = remaining
            await asyncio.sleep(1)
        spawn_remaining_time[guild_id] = 0
        await spawn_pokemon(channel)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass
    finally:
        spawn_task[guild_id] = None



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
        save_capture(ctx.author.id, pokemon_name, ivs, stats_with_iv, pokemon_data)
        

        # Envoi du message de capture
        embed_captured = discord.Embed(
            description=f"🎉 **{ctx.author.display_name} a capturé {pokemon_name} !\nVise bien l'aveugle**",
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
    guild_id = ctx.guild.id
    if guild_id not in spawn_task or spawn_task[guild_id] is None:
        await ctx.author.send("⏱ Aucun spawn automatique en cours.")
        return

    remaining = spawn_remaining_time.get(guild_id)
    if remaining is None:
        await ctx.author.send("⏱ Le temps de spawn n'est pas encore initialisé.")
        return

    minutes, seconds = divmod(remaining, 60)
    await ctx.author.send(f"⏱ Prochain spawn automatique dans {minutes} min {seconds:02d} sec.")




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

setup_guess_pokemon_command(
    bot,
    spawn_pokemon=spawn_pokemon,
    role_id=ROLE_ID,
    authorized_user_id=TARGET_USER_ID_CROCO,
    is_under_ban_func=is_under_ban
)

bot.is_under_ban = is_under_ban
setup_pokedex(bot, full_pokemon_shiny_data, full_pokemon_data, type_sprites, attack_type_map, json_dir)
setup_new_pokedex(bot, full_pokemon_shiny_data, full_pokemon_data, type_sprites, attack_type_map, json_dir)

print("[DEBUG] Ready to run bot...")


@bot.command()
async def battle(ctx):
    user_id = str(ctx.author.id)
    captures = get_captures(user_id)

    if not captures:
        await ctx.send("Tu n'as aucun Pokémon à utiliser en combat.")
        return

    pokemons = [entry["name"] for entry in captures]
    view = SelectionView(pokemons, full_pokemon_data)
    await ctx.send("Choisis jusqu’à 6 Pokémon pour ton équipe de combat :", view=view)


setup_croco_event(
    bot,
    VOICE_CHANNEL_ID,
    TEXT_CHANNEL_ID,
    TARGET_USER_ID_CROCO,
    spawn_func=spawn_pokemon,
    role_id=ROLE_ID,
    interval_seconds=60  # ajuste librement
)


bot.run(TOKEN)