import asyncio
import random
from datetime import datetime, timedelta

import pytz

from event.event_climatique import _climate_loop
from event.event_rocket import open_rocket_event, rocket_cooldown_remaining
from event.forme_regionale import activate_forme_regionale, deactivate_forme_regionale

TIMEZONE = pytz.timezone("Europe/Paris")
CYCLE = timedelta(days=14) # 14 days    # un tirage toutes les 2 semaines
WEEK = timedelta(days=7)  #7 days     # durée climat / raid / formes régionales
RAID_HOUR = 20
TICK_SECONDS = 30
START_WITH_EVENT = False       # False : aucun event au démarrage, premier tirage dans 14 jours
WEEKLY_POOL = ["climat", "raid", "rocket", "forme_regionale"]

# État en mémoire : volontairement perdu au redémarrage (le tirage ne survit pas).
# Rocket, lui, est stocké en base (event_status) pour garder son cooldown de 2 mois.
state = {"started": False, "next_draw": None, "current": None, "ends_at": None, "raid_day": None}


def _now():
    return datetime.now(TIMEZONE)


def _climate_running(bot):
    task = getattr(bot, "_climate_task", None)
    return task is not None and not task.done()


def _start_climate(bot):
    bot.climate_enabled = True
    if not _climate_running(bot):
        bot._climate_task = asyncio.create_task(_climate_loop(bot, TIMEZONE))


def _stop_climate(bot):
    task = getattr(bot, "_climate_task", None)
    if task is not None:
        task.cancel()
    bot._climate_task = None
    bot.climate_enabled = False
    bot.climate_state = {"time_of_day": "day", "active_event": None, "event_ends_at": None}


def _end_current(bot):
    """Termine la semaine en cours (climat ou raid). Renvoie son nom, ou None."""
    name = state["current"]
    if name == "climat":
        _stop_climate(bot)
    elif name == "forme_regionale":
        deactivate_forme_regionale(bot)
    state["current"] = None
    state["ends_at"] = None
    return name


async def _draw(bot, channel):
    _end_current(bot)
    pool = [e for e in WEEKLY_POOL if e != "rocket" or rocket_cooldown_remaining() is None]
    choice = random.choice(pool)

    if choice == "climat":
        _start_climate(bot)
        state.update(current="climat", ends_at=_now() + WEEK)
        await channel.send("🌦️ **Semaine climat !** Les changements climatiques sont actifs pendant 1 semaine.")
    elif choice == "raid":
        state.update(current="raid", ends_at=_now() + WEEK)
        await channel.send(f"⚔️ **Semaine raid !** Un raid est lancé tous les jours à {RAID_HOUR}h pendant 1 semaine.")
    elif choice == "forme_regionale":
        if activate_forme_regionale(bot):
            state.update(current="forme_regionale", ends_at=_now() + WEEK)
            await channel.send("🌺 **Semaine Formes régionales !** Les Pokémon Alola et Galar apparaissent pendant 1 semaine.")
        else:
            await channel.send("❌ Semaine Formes régionales annulée : les json Alola/Galar sont introuvables ou vides.")
    elif choice == "rocket":
        # Rocket : fenêtre de 1 mois gérée par open_rocket_event (annonce comprise)
        await open_rocket_event(channel)


async def planner_loop(bot, channel_id):
    """Gère le tirage toutes les 2 semaines, la fin des semaines, le climat et le raid de 20h."""
    if state["started"]:
        return
    state["started"] = True

    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if channel is None:
        print(f"[PLANNER] Salon introuvable (id={channel_id}), planning désactivé.")
        return

    # Premier tirage : immédiat si START_WITH_EVENT, sinon après un cycle complet
    state["next_draw"] = _now() if START_WITH_EVENT else _now() + CYCLE

    while not bot.is_closed():
        now = _now()

        if state["current"] and now >= state["ends_at"]:
            name = _end_current(bot)
            await channel.send(f"🏁 Fin de la semaine **{name}**.")

        if now >= state["next_draw"]:
            state["next_draw"] = now + CYCLE
            await _draw(bot, channel)

        # Garde-fou : le climat ne tourne que pendant sa semaine
        if state["current"] != "climat" and _climate_running(bot):
            _stop_climate(bot)

        # Raid à 20h, uniquement pendant la semaine raid (un seul par jour)
        if state["current"] == "raid" and now.hour == RAID_HOUR and state["raid_day"] != now.date():
            state["raid_day"] = now.date()
            asyncio.ensure_future(bot.run_raid())

        await asyncio.sleep(TICK_SECONDS)
