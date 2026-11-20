import asyncio
import random
from datetime import datetime, timedelta
import pytz
import unicodedata
from typing import Iterable, List, Tuple, Optional

# Module to manage day/night and short climatic events that filter
# the Pokémon pools. Attach state to the `bot` instance via
# setup_event_climatique(bot, base_pools=(full_pokemon_data, full_pokemon_shiny_data)).


DAY_TYPES = {"normal", "plante", "insecte", "vol"}
NIGHT_TYPES = {"tenebres", "spectre", "poison"}

CLIMATIC_EVENTS = {
    "pluie": {"types": {"eau", "electrique"}, "emoji": "🌧️"},
    "eruption": {"types": {"feu", "roche", "sol"}, "emoji": "🌋"},
    "vent_glacial": {"types": {"glace", "eau"}, "emoji": "❄️"},
    "canicule": {"types": {"feu", "sol", "roche"}, "emoji": "☀️"},
    "tempete": {"types": {"vol", "electrique"}, "emoji": "🌪️"},
    "brouillard": {"types": {"spectre", "tenebres", "poison"}, "emoji": "🌫️"},
    "orage": {"types": {"electrique", "eau"}, "emoji": "⚡"},
    "floraison": {"types": {"plante", "insecte", "fee"}, "emoji": "🌱"},
    "tempete_sable": {"types": {"sol", "roche", "acier"}, "emoji": "🏜️"},
    "raz_de_maree": {"types": {"eau", "glace"}, "emoji": "🌊"},
    "brume_forestiere": {"types": {"plante", "insecte", "poison"}, "emoji": "🌲"},
    "arc_en_ciel": {"types": {"fee", "psy", "vol"}, "emoji": "🌈"},
}


def _normalize_type(t: str) -> str:
    if not t:
        return ""
    t = t.lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return t


def _pokemon_has_type(pokemon: dict, allowed: Iterable[str]) -> bool:
    types = pokemon.get("type") or []
    if not isinstance(types, (list, tuple)):
        types = [types]
    allowed_norm = { _normalize_type(a) for a in allowed }
    for t in types:
        if _normalize_type(t) in allowed_norm:
            return True
    return False


def filter_pools_by_types(pokemon_pool: List[dict], shiny_pool: List[dict], allowed_types: Iterable[str]) -> Tuple[List[dict], List[dict]]:
    """Return filtered (normal, shiny) pools keeping only pokemons that match allowed_types.

    If allowed_types is empty -> returns copies of original pools.
    """
    if not allowed_types:
        return list(pokemon_pool), list(shiny_pool)

    filtered = [p for p in pokemon_pool if _pokemon_has_type(p, allowed_types)]
    filtered_shiny = [p for p in shiny_pool if _pokemon_has_type(p, allowed_types) or p.get("name", "").endswith("_shiny")]
    return filtered, filtered_shiny


async def _climate_loop(bot, timezone: pytz.timezone, event_chance_per_2h: float = 0.35):
    """Background loop that updates bot.climate_state and occasionally activates events.

    - Updates day/night state based on hour (Europe/Paris): day 06..19 (inclusive), night otherwise.
    - Every 2 hours (aligned to multiples of 2h), if daytime, there is a probabilistic chance to start a random event
      that lasts 2 hours.
    """
    print("[CLIMAT] climate loop started")
    try:
        while not bot.is_closed():
            now = datetime.now(timezone)
            hour = now.hour
            is_day = 6 <= hour < 20
            # Preserve existing active_event/event_ends_at if already set (e.g. via climat_force)
            existing = getattr(bot, "climate_state", None) or {}
            bot.climate_state = {
                "time_of_day": "day" if is_day else "night",
                "active_event": existing.get("active_event"),
                "event_ends_at": existing.get("event_ends_at"),
            }

            # If daytime, consider starting an event at every 2-hour boundary (e.g. 0:00,2:00,4:00...)
            if is_day:
                # compute minutes since midnight and check alignment to 2h windows
                minutes_since_midnight = hour * 60 + now.minute
                # If within the first minute of a 2-hour window, consider starting
                if minutes_since_midnight % 120 == 0:
                    # Only start a new random event if none currently active
                    if not bot.climate_state.get("active_event") and random.random() < event_chance_per_2h:
                        event_key = random.choice(list(CLIMATIC_EVENTS.keys()))
                        event_info = CLIMATIC_EVENTS[event_key]
                        bot.climate_state["active_event"] = event_key
                        bot.climate_state["event_ends_at"] = now + timedelta(hours=2)
                        print(f"[CLIMAT] Activated event {event_key} ({event_info['emoji']}) until {bot.climate_state['event_ends_at']}")

            # If there is an active event, and it expired, clear it
            if bot.climate_state.get("active_event") and bot.climate_state.get("event_ends_at"):
                try:
                    if now >= bot.climate_state["event_ends_at"]:
                        print(f"[CLIMAT] Event {bot.climate_state.get('active_event')} ended")
                        bot.climate_state["active_event"] = None
                        bot.climate_state["event_ends_at"] = None
                except Exception:
                    # If event_ends_at is not comparable, clear to be safe
                    bot.climate_state["active_event"] = None
                    bot.climate_state["event_ends_at"] = None

            # Sleep a minute between checks
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        print("[CLIMAT] climate loop cancelled")
        raise


def get_allowed_types_for_current_state(bot) -> List[str]:
    """Return the set of allowed types depending on day/night and active climatic event."""
    time_of_day = bot.climate_state.get("time_of_day", "day")
    # If an event is active, prefer event types only (it overrides day/night pools).
    active = bot.climate_state.get("active_event")
    if active:
        evt = CLIMATIC_EVENTS.get(active)
        if evt:
            return list(evt["types"])

    # Otherwise fallback to normal day/night pools
    allowed = set()
    if time_of_day == "day":
        allowed.update(DAY_TYPES)
    else:
        allowed.update(NIGHT_TYPES)

    return list(allowed)


def setup_event_climatique(bot, base_pools: Optional[Tuple[List[dict], List[dict]]] = None, timezone_name: str = "Europe/Paris"):
    """Attach climatic state to `bot` and start background loop.

    Usage in `bot.py`:
    from event.event_climatique import setup_event_climatique
    setup_event_climatique(bot, base_pools=(full_pokemon_data, full_pokemon_shiny_data))

    After setup, call `bot.get_current_pokemon_pools()` to obtain a tuple (normal_pool, shiny_pool)
    filtered according to time of day and active event.
    """
    tz = pytz.timezone(timezone_name)

    # Attach base pools
    if base_pools and isinstance(base_pools, tuple) and len(base_pools) == 2:
        bot._base_full_pokemon_data = list(base_pools[0])
        bot._base_full_pokemon_shiny_data = list(base_pools[1])
    else:
        # Try to read existing attributes on bot
        bot._base_full_pokemon_data = getattr(bot, "full_pokemon_data", [])[:] if hasattr(bot, "full_pokemon_data") else []
        bot._base_full_pokemon_shiny_data = getattr(bot, "full_pokemon_shiny_data", [])[:] if hasattr(bot, "full_pokemon_shiny_data") else []

    # Initialize climate state
    bot.climate_state = {"time_of_day": "day", "active_event": None, "event_ends_at": None}
    bot.climate_enabled = True

    # Helper to get current pools filtered by active climate
    def get_current_pokemon_pools() -> Tuple[List[dict], List[dict]]:
        if not bot.climate_enabled:
            return list(bot._base_full_pokemon_data), list(bot._base_full_pokemon_shiny_data)

        allowed = get_allowed_types_for_current_state(bot)
        normal, shiny = filter_pools_by_types(bot._base_full_pokemon_data, bot._base_full_pokemon_shiny_data, allowed)
        # If filter produced empty lists, fallback to base pools
        if not normal:
            normal = list(bot._base_full_pokemon_data)
        if not shiny:
            shiny = list(bot._base_full_pokemon_shiny_data)
        return normal, shiny

    bot.get_current_pokemon_pools = get_current_pokemon_pools

    # Start background task if not already running.
    # We must not access `bot.loop` in synchronous context (discord.py restriction).
    # Instead, register an `on_ready` listener that will create the asyncio task when the bot is ready.

    async def _start_task_on_ready(*_args, **_kwargs):
        if not hasattr(bot, "_climate_task") or bot._climate_task is None or getattr(bot._climate_task, "done", lambda: False)():
            bot._climate_task = asyncio.create_task(_climate_loop(bot, tz))
            print("[CLIMAT] climate task started and attached to bot (on_ready)")

    # Register the listener (safe to call multiple times, discord will ignore duplicates)
    try:
        bot.add_listener(_start_task_on_ready, "on_ready")
    except Exception:
        # If add_listener fails for any reason, we ignore but still attempt to start below when possible
        pass

    # If the bot is already ready and we're inside the event loop (e.g. called from a command), start immediately
    if getattr(bot, "is_ready", lambda: False)():
        try:
            if not hasattr(bot, "_climate_task") or bot._climate_task is None or getattr(bot._climate_task, "done", lambda: False)():
                bot._climate_task = asyncio.create_task(_climate_loop(bot, tz))
                print("[CLIMAT] climate task started immediately (bot already ready)")
        except RuntimeError:
            # No running loop in this synchronous context — the on_ready listener will start the task later.
            pass

    return bot
