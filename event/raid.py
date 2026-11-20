import asyncio
import json
import os
import random
import unicodedata

import discord
from discord.ext import commands
from discord.ui import Button, Select, View

from new_db import get_new_captures, save_new_capture
from utils import apply_ivs, generate_ivs, is_croco
from combat.utils import TYPE_CHART


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAID_DATA_DIR = os.path.join(PROJECT_ROOT, "json", "raid")
RAID_BOSS_PATH = os.path.join(RAID_DATA_DIR, "raid_boss.json")
RECOMPENSES_PATH = os.path.join(RAID_DATA_DIR, "raid_recompenses.json")
RECOMPENSES_SHINY_PATH = os.path.join(RAID_DATA_DIR, "raid_recompenses_shiny.json")
RAID_DURATION_SECONDS = 60 * 60 * 4 # duré du raid 4h
RAID_SHINY_RATE = 1/16 # 1 chance sur 16 par joueur ayant gagné le raid


def _load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"[RAID] Impossible de charger {path}: {error}")
        return fallback


def _normalize(value):
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower().strip()


def _get_stat(pokemon, stat_name, default=1):
    try:
        return max(1, int(pokemon.get("stats", {}).get(stat_name, default)))
    except (TypeError, ValueError):
        return default


def _type_effectiveness(attack_type, defender_types):
    chart = TYPE_CHART.get(_normalize(attack_type), {"x2": [], "x0.5": [], "x0": []})
    multiplier = 1.0
    if isinstance(defender_types, str):
        defender_types = [defender_types]
    for defender_type in defender_types or []:
        normalized_type = _normalize(defender_type)
        if normalized_type in chart["x0"]:
            return 0.0
        if normalized_type in chart["x2"]:
            multiplier *= 2.0
        elif normalized_type in chart["x0.5"]:
            multiplier *= 0.5
    return multiplier


def _find_reward(source, boss_name):
    return source.get(_normalize(boss_name)) or source.get(boss_name)


def calculate_raid_damage(attacker, defender):
    """Calcule une contribution déterministe à partir des statistiques et des types."""
    attacker_types = attacker.get("type") or ["normal"]
    if isinstance(attacker_types, str):
        attacker_types = [attacker_types]

    best_damage = 0
    best_effectiveness = 0.0
    best_attack_type = "normal"
    for attack_type in attacker_types:
        effectiveness = _type_effectiveness(attack_type, defender.get("type", []))
        if effectiveness == 0:
            continue

        physical_ratio = _get_stat(attacker, "attack") / _get_stat(defender, "defense")
        special_ratio = _get_stat(attacker, "special_attack") / _get_stat(defender, "special_defense")
        if physical_ratio >= special_ratio:
            offense = _get_stat(attacker, "attack")
            defense = _get_stat(defender, "defense")
        else:
            offense = _get_stat(attacker, "special_attack")
            defense = _get_stat(defender, "special_defense")

        stab = 1.5 if _normalize(attack_type) in {_normalize(item) for item in attacker_types} else 1.0
        base_damage = ((22 * 80 * (offense / defense)) / 50) + 2
        damage = max(1, int(base_damage * stab * effectiveness))
        if damage > best_damage:
            best_damage = damage
            best_effectiveness = effectiveness
            best_attack_type = _normalize(attack_type)

    return best_damage, best_effectiveness, best_attack_type


class RaidPokemonSelect(Select):
    def __init__(self, raid, captures):
        self.raid = raid
        self.captures_by_name = {}
        for pokemon in captures:
            name = pokemon.get("name")
            if name:
                self.captures_by_name.setdefault(name, pokemon)

        names = list(self.captures_by_name)[:25]
        options = [discord.SelectOption(label=name[:100], value=name) for name in names]
        super().__init__(placeholder="Choisis un Pokémon pour le raid", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if self.raid["closed"]:
            await interaction.response.send_message("Le raid est terminé.", ephemeral=True)
            return
        if user_id in self.raid["participants"]:
            await interaction.response.send_message("Tu as déjà choisi ton Pokémon pour ce raid.", ephemeral=True)
            return

        pokemon = self.captures_by_name[self.values[0]]
        damage, effectiveness, attack_type = calculate_raid_damage(pokemon, self.raid["boss"])
        self.raid["participants"][user_id] = {
            "name": pokemon["name"],
            "damage": damage,
            "effectiveness": effectiveness,
            "attack_type": attack_type,
        }
        await interaction.response.send_message(
            f"✅ **{pokemon['name']}** est engagé et infligera **{damage} dégâts** (type {attack_type}).",
            ephemeral=True,
        )


class RaidChoiceView(View):
    def __init__(self, raid, captures):
        super().__init__(timeout=120)
        self.add_item(RaidPokemonSelect(raid, captures))


class RaidView(View):
    def __init__(self, raid):
        super().__init__(timeout=RAID_DURATION_SECONDS)
        self.raid = raid

    @discord.ui.button(label="Choisir mon Pokémon", style=discord.ButtonStyle.primary, emoji="⚔️")
    async def choose_pokemon(self, interaction: discord.Interaction, button: Button):
        user_id = interaction.user.id
        if self.raid["closed"]:
            await interaction.response.send_message("Le raid est terminé.", ephemeral=True)
            return
        if user_id in self.raid["participants"]:
            await interaction.response.send_message("Tu as déjà choisi ton Pokémon pour ce raid.", ephemeral=True)
            return

        captures = get_new_captures(str(user_id))
        if not captures:
            await interaction.response.send_message("Tu n'as aucun Pokémon capturé à engager.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Sélectionne ton Pokémon (un seul choix pour tout le raid) :",
            view=RaidChoiceView(self.raid, captures),
            ephemeral=True,
        )


def setup_raid(bot):
    raid_boss = _load_json(RAID_BOSS_PATH, [])
    recompenses = _load_json(RECOMPENSES_PATH, {})
    recompenses_shiny = _load_json(RECOMPENSES_SHINY_PATH, {})
    channel_id_raw = os.getenv("CHANNEL_ID_RAID")
    try:
        raid_channel_id = int(channel_id_raw) if channel_id_raw else None
    except ValueError:
        raid_channel_id = None

    if isinstance(raid_boss, dict):
        raid_entries = raid_boss.values()
    elif isinstance(raid_boss, list):
        raid_entries = raid_boss
    else:
        raid_entries = []
    valid_raids = [
        pokemon for pokemon in raid_entries
        if isinstance(pokemon, dict)
        and pokemon.get("name")
        and pokemon.get("stats")
        and pokemon.get("type")
    ]
    bot.raid_enabled = bool(raid_channel_id and valid_raids and isinstance(recompenses, dict))
    active_raid = False

    async def run_raid():
        nonlocal active_raid
        if active_raid:
            print("[RAID] Un raid est déjà en cours.")
            return
        if not bot.raid_enabled:
            print("[RAID] Raid désactivé: vérifie CHANNEL_ID_RAID et les fichiers JSON.")
            return

        channel = bot.get_channel(raid_channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(raid_channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as error:
                print(f"[RAID] Salon introuvable ou inaccessible: {error}")
                return

        boss = random.choice(valid_raids)
        reward = _find_reward(recompenses, boss["name"])
        reward_shiny = _find_reward(recompenses_shiny, boss["name"])
        if not reward or not reward.get("name") or not reward.get("stats"):
            await channel.send(f"❌ Aucune récompense valide n'est liée au raid **{boss['name']}** dans `raid_recompenses.json`.")
            return

        active_raid = True
        raid = {"boss": boss, "participants": {}, "closed": False}
        view = RaidView(raid)
        boss_hp = _get_stat(boss, "hp")
        embed = discord.Embed(
            title=f"⚔️ Raid Pokémon : {boss['name']}",
            description=(
                f"Un **{boss['name']}** apparaît !\n"
                f"PV du raid : **{boss_hp}**\n"
                f"Chaque joueur peut engager un seul Pokémon. Le raid se termine dans 3 minutes."
            ),
            color=0xD94F4F,
        )
        if boss.get("image"):
            embed.set_image(url=boss["image"])

        try:
            message = await channel.send(embed=embed, view=view)
            await asyncio.sleep(RAID_DURATION_SECONDS)
            raid["closed"] = True
            view.stop()
            for child in view.children:
                child.disabled = True
            await message.edit(view=view)

            participants = raid["participants"]
            total_damage = sum(entry["damage"] for entry in participants.values())
            if total_damage < boss_hp:
                await channel.send(
                    f"💥 Le raid échoue : **{total_damage}/{boss_hp} dégâts**. "
                    f"{len(participants)} joueur(s) ont participé, mais personne ne reçoit de récompense."
                )
                return

            shiny_winners = []
            for user_id in participants:
                # tirage shiny indépendant pour chaque joueur
                is_shiny = bool(reward_shiny) and random.randint(1, RAID_SHINY_RATE) == 1
                base = reward_shiny if is_shiny else reward
                reward_ivs = generate_ivs()
                reward_stats = apply_ivs(base["stats"], reward_ivs)
                reward_pokemon = dict(base)
                reward_pokemon["ivs"] = reward_ivs
                reward_pokemon["stats_iv"] = reward_stats
                save_new_capture(
                    user_id,
                    base["name"],
                    reward_ivs,
                    reward_stats,
                    reward_pokemon,
                )
                if is_shiny:
                    shiny_winners.append(f"<@{user_id}>")
            mentions = ", ".join(f"<@{user_id}>" for user_id in participants)
            await channel.send(
                f"🏆 **Raid remporté !** Les joueurs {mentions} reçoivent chacun **{reward['name']}**. "
                f"Dégâts cumulés : **{total_damage}/{boss_hp}**."
            )
            if shiny_winners:
                await channel.send(
                    f"✨ **Shiny !** {', '.join(shiny_winners)} obtiennent **{reward['name']} ✨** !"
                )
        finally:
            raid["closed"] = True
            active_raid = False

    @bot.command(name="raid")
    @is_croco()
    async def raid_command(ctx):
        if not bot.raid_enabled:
            await ctx.send("❌ Raid indisponible : vérifie `CHANNEL_ID_RAID` et les deux fichiers JSON dans `json/raid/`.")
            return
        await run_raid()

    bot.run_raid = run_raid