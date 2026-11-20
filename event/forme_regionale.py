"""Event Formes régionales : quand il est actif, 30 % des spawns (spawn, devine, quiz)
viennent de json/alola.json, json/alola_shiny.json, json/galar.json et json/galar_shiny.json."""
import json
import os
import random

from utils import is_croco

FORME_REGIONALE_CHANCE = 0.40 # 40% de chances d'avoir un pokémon d'une forme régionale

_json_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "json")


def load_regional_pool(file_name: str) -> list:
    try:
        with open(os.path.join(_json_dir, file_name), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[FORME_REGIONALE] json/{file_name} illisible : {e}")
        return []


def pick_forme_regionale_pokemon(bot, shiny: bool = False):
    """Retourne un Pokémon Alola/Galar (30 % de chances si l'event est actif), sinon None.
    La région (Alola/Galar) est tirée 50/50, indépendamment du nombre de Pokémon par région."""
    pools = getattr(bot, "forme_regionale_pools", None)
    if not pools or not any(pools.values()) or random.random() >= FORME_REGIONALE_CHANCE:
        return None
    region = random.choice(list(pools.keys()))
    pool = pools[region]
    if shiny:
        shiny_pool = getattr(bot, "forme_regionale_shiny_pools", {}).get(region)
        # sans pool shiny pour cette région, un tirage shiny retombe sur le pool normal
        pool = shiny_pool or pool
    if not pool:
        return None
    return random.choice(pool)


def activate_forme_regionale(bot) -> int:
    """Charge les pools Alola/Galar (normaux et shiny). Renvoie le nombre de Pokémon (0 = échec)."""
    bot.forme_regionale_pools = {
        "alola": load_regional_pool("alola.json"),
        "galar": load_regional_pool("galar.json"),
    }
    bot.forme_regionale_shiny_pools = {
        "alola": load_regional_pool("alola_shiny.json"),
        "galar": load_regional_pool("galar_shiny.json"),
    }
    return sum(len(p) for p in bot.forme_regionale_pools.values())


def deactivate_forme_regionale(bot):
    """Vide les pools : l'event est inactif."""
    bot.forme_regionale_pools = {"alola": [], "galar": []}


def setup_forme_regionale(bot):
    deactivate_forme_regionale(bot)
    bot.forme_regionale_shiny_pools = {"alola": [], "galar": []}

    @bot.command(name="forme_regionale_on")
    @is_croco()
    async def forme_regionale_on(ctx):
        """Active l'event Formes régionales (relit les json Alola et Galar, normaux et shiny)."""
        total = activate_forme_regionale(bot)
        if total == 0:
            await ctx.send("❌ Les json de formes régionales sont introuvables, vides ou invalides : event non activé.")
            return
        await ctx.send(
            f"🌺 Event Formes régionales activé : {int(FORME_REGIONALE_CHANCE * 100)} % de chances de spawn, "
            f"50/50 entre Alola et Galar, parmi {total} Pokémon."
        )

    @bot.command(name="forme_regionale_off")
    @is_croco()
    async def forme_regionale_off(ctx):
        """Désactive l'event Formes régionales."""
        deactivate_forme_regionale(bot)
        await ctx.send("⛔ Event Formes régionales désactivé.")
