import asyncio
import random
import json
import os
import discord
from discord.ext import commands, tasks
from datetime import datetime

# -----------------------
# CONFIGURATION ACTU
# -----------------------

ACTU_CHANNEL_ID   = int(os.getenv("ACTU"))   # ID du salon texte actu
ACTU_HOUR_MIN     = 20             # heure min de publication (20h)
ACTU_HOUR_MAX     = 24              # heure max de publication (00h)
EXPLORE_DURATION_MIN = 15 * 60     # 15 minutes en secondes
EXPLORE_DURATION_MAX = 20 * 60     # 20 minutes en secondes
POKEMON_RATE = 0.3  #POKEMON_RATE = 0.30
ITEM_RATE    = 0.3    #ITEM_RATE    = 0.30
NOTHING_RATE= 0.4 #NOTHING_RATE = 0.40 
SHINY_RATE   = 1 / 64

JSON_DIR  = os.path.join(os.path.dirname(__file__), "json")
ACTU_DIR  = os.path.join(JSON_DIR, "actu")
IMAGES_ACTU_DIR = os.path.join(os.path.dirname(__file__), "images", "actu")
TARGET_USER_ID_CROCO = int(os.getenv("TARGET_USER_ID_CROCO"))
def is_croco():
    def predicate(ctx):
        return ctx.author.id == TARGET_USER_ID_CROCO
    return commands.check(predicate)


# Dictionnaire des lieux : command_name -> config
LIEUX = {
    "vieuxchateau": {
        "name":    "Vieux Chateau de Vestigion",
        "emoji":   "🏚️",
        "command": "vieuxchateau",
        "region":  "Sinnoh",
        "pokemon_normal": os.path.join(ACTU_DIR, "vieuxchateau", "pokemon_vieuxchateau_normal.json"),
        "pokemon_shiny":  os.path.join(ACTU_DIR, "vieuxchateau", "pokemon_vieuxchateau_shinny.json"),
        "objets":         os.path.join(ACTU_DIR, "vieuxchateau", "objet_vieuxchateau.json"),
        "description":    "Des bruits étranges s'en échappent du vieux chateau de Vestigion",
        "messages_ambiance": [
            "🌫️ *Un silence pesant règne dans le vieux chateau…* (encore {time_left})",
            "🕯️ *Un courant d'air froid traverse le vieux chateau…* (encore {time_left})",
            "🦇 *Des chauves-souris s'envolent dans l'obscurité…* (encore {time_left})",
            "👣 *Tu entends des pas… mais personne n'est là.* (encore {time_left})",
        ],
    },
    "foret": {
        "name":    "Forest Vestigion",
        "emoji":   "🌲",
        "command": "foret",
        "region":  "Sinnoh",
        "pokemon_normal": os.path.join(ACTU_DIR, "foret_vestigion", "pokemon_foret_vestigion_normal.json"),
        "pokemon_shiny":  os.path.join(ACTU_DIR, "foret_vestigion", "pokemon_foret_vestigion_shinny.json"),
        "objets":         os.path.join(ACTU_DIR, "foret_vestigion", "objet_foret_vestigion.json"),
        "description":    "La forêt de Vestegion",
        "messages_ambiance": [
            "🍃 *Les feuilles bruissent autour de toi sans qu'aucun vent ne souffle…* (encore {time_left})",
            "🦉 *Un hibou t'observe depuis les hauteurs, immobile.* (encore {time_left})",
            "🌫️ *Un épais brouillard se lève entre les arbres…* (encore {time_left})",
            "🐾 *Des empreintes fraîches dans la boue… mais aucune créature en vue.* (encore {time_left})",
            "🌑 *La canopée bloque toute lumière. Il fait soudainement très sombre.* (encore {time_left})",
        ],
    },
}

# Joueurs actuellement en exploration  { user_id: lieu_key }
exploring: dict[int, str] = {}

# Suivi de l'exploration par jour  { user_id: date_iso }
explored_today: dict[int, str] = {}

# Lieu débloqué par l'actu du jour
actu_lieu_du_jour: str | None = None

# Flag d'activation du système actu (géré par !actu_on / !actu_off)
actu_enabled: bool = True


# -----------------------
# CHARGEMENT JSON
# -----------------------

def load_actu_messages() -> list[dict]:
    filepath = os.path.join(ACTU_DIR, "message.json")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ACTU] Fichier introuvable : {filepath}")
        return []


def load_lieu_pokemon(lieu_key: str, shiny: bool = False) -> list[dict]:
    cfg  = LIEUX.get(lieu_key, {})
    path = cfg.get("pokemon_shiny" if shiny else "pokemon_normal", "")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def load_lieu_objets(lieu_key: str) -> list[dict]:
    cfg  = LIEUX.get(lieu_key, {})
    path = cfg.get("objets", "")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


# -----------------------
# HELPERS
# -----------------------

def get_user_region(cur, user_id: str) -> str | None:
    cur.execute("SELECT region FROM user_regions WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None


def weighted_choice(pool: list[dict]) -> dict | None:
    """Choisit un élément selon le champ 'probabilité' (float 0-1) ou 'weight' (int)."""
    if not pool:
        return None
    weights = [p.get("probabilité", p.get("weight", 1)) for p in pool]
    return random.choices(pool, weights=weights, k=1)[0]

def get_user_item_names(user_id: str) -> set[str]:
    """Retourne l'ensemble des noms d'objets que le joueur possède déjà."""
    from inventory_db import get_inventory
    items = get_inventory(user_id)
    return {item["name"] for item in items}


STAT_LABELS = {
    "hp":              "PV",
    "attack":          "Attaque",
    "special_attack":  "Att. Spé",
    "defense":         "Défense",
    "special_defense": "Déf. Spé",
    "speed":           "Vitesse",
}


def save_pokemon_capture(user_id: str, pokemon: dict, is_shiny: bool):
    from new_db import save_new_capture
    base_stats  = pokemon.get("stats", {})
    ivs         = {stat: random.randint(0, 31) for stat in base_stats}
    final_stats = {stat: base_stats[stat] + ivs[stat] for stat in base_stats}
    display_name = ("✨" + pokemon["name"]) if is_shiny else pokemon["name"]
    pokemon_data = {
        "image":      pokemon.get("image", ""),
        "type":       pokemon.get("type", []),
        "attacks":    pokemon.get("attacks", []),
        "current_xp": pokemon.get("current_xp", 0),
        "xp_evo":     pokemon.get("xp_evo"),
        "evo":        pokemon.get("evo"),
    }
    save_new_capture(user_id, display_name, ivs, final_stats, pokemon_data)
    return ivs, final_stats


def add_item_to_inventory(user_id: str, item: dict):
    from inventory_db import add_item
    add_item(
        user_id=user_id,
        name=item["item_name"],
        quantity=1,
        rarity=item.get("rarity", "commun"),
        description=item.get("description", ""),
        image=item.get("image", ""),
        extra=item.get("extra"),
        price=item.get("price"),
    )


# -----------------------
# EMBED HELPERS
# -----------------------

def pokemon_embed(pokemon: dict, is_shiny: bool, lieu_name: str, ivs: dict, final_stats: dict) -> discord.Embed:
    color = discord.Color.gold() if is_shiny else discord.Color.purple()
    title = f"{'✨ Shiny ! ' if is_shiny else ''}**{pokemon['name']}** apparaît !"
    embed = discord.Embed(title=title, color=color)
    embed.set_thumbnail(url=pokemon.get("image", ""))
    embed.add_field(name="Type",     value=" / ".join(t.capitalize() for t in pokemon.get("type", [])), inline=True)
    embed.add_field(name="Attaques", value="\n".join(pokemon.get("attacks", [])) or "Aucune",           inline=True)
    avg_iv = round(sum(ivs.values()) / len(ivs), 1) if ivs else 0
    embed.add_field(name="IV moyens", value=f"{avg_iv} / 31", inline=False)
    stats_lines = "\n".join(f"**{STAT_LABELS.get(k, k)}** : {v}" for k, v in final_stats.items())
    embed.add_field(name="Stats", value=stats_lines, inline=False)
    evo    = pokemon.get("evo")
    xp_evo = pokemon.get("xp_evo")
    if evo and xp_evo:
        embed.add_field(name="Évolution", value=f"Évolue en **{evo['name']}** à {xp_evo} XP", inline=False)
    embed.set_footer(text=f"Lieu : {lieu_name}" + (" — ✨ Incroyable !" if is_shiny else ""))
    return embed


def item_embed(item: dict, lieu_name: str) -> tuple[discord.Embed, discord.File | None]:
    embed = discord.Embed(
        title=f"🎁 Tu as trouvé **{item['item_name']}** !",
        description=item.get("description", ""),
        color=discord.Color.green(),
    )
    file = None
    image_path = item.get("image", "")
    if image_path and not os.path.isabs(image_path):
        image_path = os.path.join(os.path.dirname(__file__), image_path)

    if image_path and os.path.exists(image_path):
        filename = os.path.basename(image_path)
        file = discord.File(image_path, filename=filename)
        embed.set_image(url=f"attachment://{filename}")

    return embed, file  # ← ligne manquante
    


# -----------------------
# BOUCLE D'EXPLORATION
# -----------------------

async def run_exploration(dm: discord.DMChannel, user_id: str, lieu_key: str, duration: int):
    """
    Tourne minute par minute pendant `duration` secondes.
    30 % pokémon | 30 % objet | 40 % rien.
    """
    cfg       = LIEUX[lieu_key]
    lieu_name = cfg["name"]
    elapsed   = 0
    tick      = 60  # toutes les minutes

    while elapsed < duration:
        await asyncio.sleep(tick)
        elapsed += tick

        remaining = duration - elapsed
        roll      = random.random()

        # --- Pokémon ---
        if roll < POKEMON_RATE:
            is_shiny    = random.random() < SHINY_RATE
            shiny_pool  = load_lieu_pokemon(lieu_key, shiny=True)
            normal_pool = load_lieu_pokemon(lieu_key, shiny=False)

            if is_shiny and shiny_pool:
                pokemon = weighted_choice(shiny_pool)
            else:
                is_shiny = False
                pokemon  = weighted_choice(normal_pool)

            if pokemon:
                ivs, final_stats = save_pokemon_capture(user_id, pokemon, is_shiny)
                embed     = pokemon_embed(pokemon, is_shiny, lieu_name, ivs, final_stats)
                time_left = f"{remaining // 60}min {remaining % 60}s"
                await dm.send(
                    f"👁️ *Quelque chose bouge dans le {lieu_name}…* (encore {time_left})",
                    embed=embed,
                )

        # --- Objet ---
        elif roll < POKEMON_RATE + ITEM_RATE:
            objets = load_lieu_objets(lieu_key)
            owned = get_user_item_names(user_id)
            objets_dispo = [o for o in objets if o["item_name"] not in owned]

            if not objets_dispo:
                time_left = f"{remaining // 60}min {remaining % 60}s"
                # Dans le bloc "Objet" quand objets_dispo est vide, et dans le bloc "Rien"
                msgs = cfg.get("messages_ambiance", [
                    f"🌫️ *Un silence pesant règne dans le {lieu_name}…* (encore {{time_left}})",
                ])
                await dm.send(random.choice(msgs).format(time_left=time_left))
            else:
                item = weighted_choice(objets_dispo)
                if item:
                    add_item_to_inventory(user_id, item)
                    embed, file = item_embed(item, lieu_name)
                    time_left = f"{remaining // 60}min {remaining % 60}s"
                    await dm.send(
                        f"🔦 *Tu fouilles le {lieu_name}…* (encore {time_left})",
                        embed=embed,
                        file=file if file else discord.utils.MISSING,
                    )

        # --- Rien ---
        else:
            time_left = f"{remaining // 60}min {remaining % 60}s"
            msgs = [
                f"🕯️ *Un courant d'air froid traverse le {lieu_name}…* (encore {time_left})",
                f"🦇 *Des chauves-souris s'envolent dans l'obscurité…* (encore {time_left})",
                f"🌫️ *Un silence pesant règne dans le {lieu_name}…* (encore {time_left})",
                f"👣 *Tu entends des pas… mais personne n'est là.* (encore {time_left})",
            ]
            await dm.send(random.choice(msgs))

    # Fin de l'exploration
    exploring.pop(int(user_id), None)
    await dm.send(
        f"🚪 **Tu quittes le {lieu_name}.**\n"
        f"L'exploration est terminée. Reviens quand une nouvelle actu t'y invite !"
    )


# -----------------------
# SETUP : COMMANDES + TÂCHE ACTU
# -----------------------

def setup_actu(bot: commands.Bot, cur):
    global actu_enabled

    # ---- Tâche quotidienne d'actu ----
    @tasks.loop(minutes=1)
    async def check_actu_time():
        global actu_lieu_du_jour
        if not actu_enabled:
            return
        now = datetime.now()
        if ACTU_HOUR_MIN <= now.hour < ACTU_HOUR_MAX:
            if not check_actu_time._published_today:
                check_actu_time._published_today = True
                await send_daily_actu(bot)
        else:
            check_actu_time._published_today = False
            actu_lieu_du_jour = None  # reset à minuit, plus aucun lieu accessible

    check_actu_time._published_today = False

    @bot.listen("on_ready")
    async def start_actu_task():
        if not check_actu_time.is_running():
            check_actu_time.start()
            print("[ACTU] Tâche d'actu démarrée.")

    # ---- Envoi de l'actu (par ID de salon) ----
    async def send_daily_actu(bot: commands.Bot, channel_override: discord.TextChannel = None):
        global actu_lieu_du_jour

        messages = load_actu_messages()
        if not messages:
            return

        actu     = random.choice(messages)
        lieu_key = actu.get("lieu")
        lieu_cfg = LIEUX.get(lieu_key, {})

        actu_lieu_du_jour = lieu_key

        embed = discord.Embed(
            title=f"📰 {actu.get('titre', 'Nouvelle du jour')}",
            description=actu.get("texte", ""),
            color=discord.Color.dark_orange(),
        )

        # Gestion de l'image locale
        file = None
        image_path = actu.get("image", "")
        if image_path:
            if not os.path.isabs(image_path):
                image_path = os.path.join(os.path.dirname(__file__), image_path)
            if os.path.exists(image_path):
                filename = os.path.basename(image_path)
                file = discord.File(image_path, filename=filename)
                embed.set_image(url=f"attachment://{filename}")
            else:
                print(f"[ACTU] Image introuvable : {image_path}")

        channel = channel_override or bot.get_channel(ACTU_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed, file=file if file else discord.utils.MISSING)
        else:
            print(f"[ACTU] Salon introuvable (ID={ACTU_CHANNEL_ID})")

    # -----------------------------------------------
    # COMMANDES D'ADMINISTRATION
    # -----------------------------------------------

    @bot.command(name="actu_on")
    @is_croco()
    async def actu_on(ctx):
        """Active les publications d'actu automatiques."""
        global actu_enabled
        if actu_enabled:
            await ctx.send("✅ Les actus sont déjà **activées**.", delete_after=6)
            return
        actu_enabled = True
        check_actu_time._published_today = False
        await ctx.send("✅ Les actus automatiques sont maintenant **activées**.", delete_after=6)

    @bot.command(name="actu_off")
    @is_croco()
    async def actu_off(ctx):
        """Désactive les publications d'actu automatiques."""
        global actu_enabled
        if not actu_enabled:
            await ctx.send("⛔ Les actus sont déjà **désactivées**.", delete_after=6)
            return
        actu_enabled = False
        await ctx.send("⛔ Les actus automatiques sont maintenant **désactivées**.", delete_after=6)

    @bot.command(name="actu_status")
    @is_croco()
    async def actu_status(ctx):
        """Affiche l'état actuel du système d'actu."""
        etat   = "✅ Activées" if actu_enabled else "⛔ Désactivées"
        publie = "Oui" if check_actu_time._published_today else "Non"
        embed  = discord.Embed(title="📊 Statut du système Actu", color=discord.Color.blurple())
        embed.add_field(name="État",                   value=etat,   inline=True)
        embed.add_field(name="Publiée aujourd'hui ?",  value=publie, inline=True)
        embed.add_field(name="Fenêtre de publication", value=f"{ACTU_HOUR_MIN}h – {ACTU_HOUR_MAX % 24:02d}h", inline=True)
        lieux_list = "\n".join(f"• `!{v['command']}` — {v['name']} ({v.get('region','?')})" for v in LIEUX.values())
        embed.add_field(name="Lieux disponibles", value=lieux_list, inline=False)
        await ctx.send(embed=embed)

    @bot.command(name="actu_test")
    @is_croco()
    async def actu_test(ctx):
        """Force l'envoi immédiat d'une actu dans CE salon (test admin)."""
        await send_daily_actu(bot, channel_override=ctx.channel)
        await ctx.send("📨 Actu de test envoyée !", delete_after=4)

    @actu_on.error
    @actu_off.error
    @actu_status.error
    @actu_test.error
    async def actu_admin_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Tu n'as pas la permission d'utiliser cette commande.", delete_after=5)

    # -----------------------------------------------
    # COMMANDES D'EXPLORATION (générées dynamiquement)
    # -----------------------------------------------

    # IMPORTANT : make_command doit être définie AVANT la boucle qui l'appelle
    def make_command(lk, lcfg):
        @bot.command(name=lcfg["command"])
        async def explore_command(ctx, _lk=lk, _lcfg=lcfg):
            global actu_lieu_du_jour, exploring, explored_today

            user_id     = ctx.author.id
            user_id_str = str(user_id)

            #Vérif fenêtre horaire (20h–00h uniquement)
            now = datetime.now()

            # 4 = vendredi, 5 = samedi, 6 = dimanche
            if now.weekday() not in (4, 5, 6):
                check_actu_time._published_today = False
                actu_lieu_du_jour = None
                return
            if not (ACTU_HOUR_MIN <= now.hour < ACTU_HOUR_MAX):
                await ctx.send(
                     f"{ctx.author.mention} ⏰ Ce lieu n'est accessible qu'entre "
                    f"**{ACTU_HOUR_MIN}h et {ACTU_HOUR_MAX % 24:02d}h**.",
                    delete_after=6,
                )
                return

            # Vérif lieu de l'actu du jour
            if _lk != actu_lieu_du_jour:
                await ctx.send(
                    f"{ctx.author.mention} ❌ Ce lieu n'est pas évoqué dans l'actu d'aujourd'hui.",
                    delete_after=6,
                )
                return

            # Vérif déjà exploré aujourd'hui
            today = now.date().isoformat()
            if explored_today.get(user_id) == today:
                await ctx.send(
                    f"{ctx.author.mention} 📅 Tu as déjà exploré un lieu aujourd'hui. Reviens demain !",
                    delete_after=6,
                )
                return

            # Déjà en exploration active ?
            if user_id in exploring:
                current = LIEUX.get(exploring[user_id], {}).get("name", "un lieu")
                await ctx.send(
                    f"{ctx.author.mention} 🚶 Tu explores déjà **{current}** ! Termine-le d'abord.",
                    delete_after=6,
                )
                return

            # Vérif DM
            try:
                dm = await ctx.author.create_dm()
            except discord.Forbidden:
                await ctx.send(
                    f"{ctx.author.mention} ❌ Active tes DMs pour explorer !",
                    delete_after=5,
                )
                return

            # Vérif région
            region   = get_user_region(cur, user_id_str)
            required = _lcfg.get("region")
            if required and region != required:
                await ctx.send(
                    f"{ctx.author.mention} ❌ Ce lieu est en région **{required}**.\n"
                    f"Ta région actuelle : **{region or 'aucune'}**.",
                    delete_after=8,
                )
                return

            duration = random.randint(EXPLORE_DURATION_MIN, EXPLORE_DURATION_MAX)
            minutes  = duration // 60

            # Enregistrement APRÈS toutes les vérifs
            explored_today[user_id] = today
            exploring[user_id]      = _lk

            await ctx.send(
                f"{ctx.author.mention} 🚪 Tu pénètres dans **{_lcfg['name']}**… 📩 Suis l'aventure en DM !",
                delete_after=6,
            )
            await dm.send(
                f"🏚️ **Tu entres dans le {_lcfg['name']}.**\n"
                f"_{_lcfg.get('description', '')}_\n\n"
                f"⏳ L'exploration durera environ **{minutes} minutes**.\n"
                f"Toutes les minutes, quelque chose pourrait se passer…"
            )

            asyncio.create_task(run_exploration(dm, user_id_str, _lk, duration))

        return explore_command

    # Enregistrement de toutes les commandes de lieu
    for lieu_key, cfg in LIEUX.items():
        make_command(lieu_key, cfg)