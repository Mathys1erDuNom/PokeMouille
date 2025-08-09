# croco_event.py
import time
import discord
from discord.ext import tasks, commands
from typing import Optional, Callable

DEFAULT_INTERVAL = 60  # secours si rien n'est passé

def setup_croco_event(
    bot: commands.Bot,
    voice_channel_id: int,
    text_channel_id: int,
    target_user_id: int,
    spawn_func: Optional[Callable] = None,   # async def spawn_pokemon(channel, force=False, author=None, target_user=None, pokemon_name=None, shiny_rate=64)
    role_id: Optional[int] = None,
    **kwargs   # ← accepte interval_seconds sans planter
):
    interval_seconds = int(max(1, kwargs.get("interval_seconds", DEFAULT_INTERVAL)))

    # État partagé sur le bot (évite doublons)
    if not hasattr(bot, "_croco_event_state"):
        bot._croco_event_state = {"task_started": False}
    state = bot._croco_event_state
    state.update({
        "voice_channel_id": voice_channel_id,
        "text_channel_id": text_channel_id,
        "target_user_id": target_user_id,
        "spawn_func": spawn_func,
        "role_id": role_id,
        "interval_seconds": interval_seconds,
        "next_fire_ts": None,  # ← timestamp du prochain déclenchement (None si désarmé)
    })

    async def get_channels():
        vc = bot.get_channel(state["voice_channel_id"])
        tx = bot.get_channel(state["text_channel_id"])
        return vc, tx

    def is_croco_only():
        async def predicate(ctx: commands.Context):
            return ctx.author.id == state["target_user_id"]
        return commands.check(predicate)

    @tasks.loop(seconds=DEFAULT_INTERVAL)  # ajusté avant start via change_interval(...)
    async def croco_minutely_event():
        vc, channel = await get_channels()
        if not vc or not hasattr(vc, "members"):
            return
        if not channel or not hasattr(channel, "send"):
            return

        # Est-ce que Croco est en vocal ?
        croco_in_vc = any(m.id == state["target_user_id"] for m in vc.members)

        # Si pas en vocal -> on désarme le timer et on sort
        if not croco_in_vc:
            state["next_fire_ts"] = None
            return

        now = time.time()

        # Si en vocal mais pas encore armé -> on arme maintenant + intervalle
        if state["next_fire_ts"] is None:
            state["next_fire_ts"] = now + state["interval_seconds"]
            return

        # Si l'heure est arrivée -> on déclenche puis on réarme
        if now >= state["next_fire_ts"]:
            croco_member = vc.guild.get_member(state["target_user_id"])
            if not croco_member:
                # réarme quand même pour éviter de spammer au tick suivant
                state["next_fire_ts"] = now + state["interval_seconds"]
                return

            # 1) Message flatteur
            try:
                await channel.send(f"💎 {croco_member.mention} est le plus beau ! 😍")
            except Exception:
                pass

            # 2) Spawn
            try:
                if callable(state["spawn_func"]):
                    await state["spawn_func"](
                        channel=channel,
                        force=True,
                        author=croco_member,
                        target_user=croco_member,
                        shiny_rate=64
                    )
                else:
                    await channel.send(f"!spawn {croco_member.mention}")
            except Exception:
                pass

            # Réarmer pour le prochain tour
            state["next_fire_ts"] = now + state["interval_seconds"]

    # Démarrage via listener (compatible discord.py v2+, pas de bot.loop)
    if not state["task_started"]:
        async def _on_ready():
            if not state["task_started"]:
                try:
                    croco_minutely_event.change_interval(seconds=state["interval_seconds"])
                except Exception:
                    pass
                croco_minutely_event.start()
                state["task_started"] = True

        bot.add_listener(_on_ready, "on_ready")

    # ---------- Commandes ----------
    @bot.command(name="croco_now")
    @is_croco_only()
    async def croco_now(ctx: commands.Context):
        """Déclenche immédiatement (test)."""
        vc, channel = await get_channels()
        if not channel:
            await ctx.reply("❌ Canal texte introuvable.")
            return

        await channel.send(f"💎 {ctx.author.mention} est le plus beau ! 😍")

        if callable(state["spawn_func"]):
            await state["spawn_func"](
                channel=channel,
                force=True,
                author=ctx.author,
                target_user=ctx.author,
                shiny_rate=64
            )
        else:
            await channel.send(f"!spawn {ctx.author.mention}")

        # Réarmer un nouveau délai plein
        state["next_fire_ts"] = time.time() + state["interval_seconds"]

    @bot.command(name="croco_status")
    @is_croco_only()
    async def croco_status(ctx: commands.Context):
        """Affiche l’état + le temps restant avant le prochain event."""
        vc, channel = await get_channels()
        parts = []
        parts.append(f"🔁 Tâche active : {'oui' if state.get('task_started') else 'non'}")
        parts.append(f"🗣️ Vocal configuré : {'oui' if vc and hasattr(vc, 'members') else 'non'}")
        parts.append(f"💬 Texte configuré : {'oui' if channel and hasattr(channel, 'send') else 'non'}")

        in_vc = bool(vc and hasattr(vc, 'members') and any(m.id == state['target_user_id'] for m in vc.members))
        parts.append(f"✅ Croco en vocal : {'oui' if in_vc else 'non'}")

        direct_call = callable(state["spawn_func"])
        parts.append(f"🎯 Mode spawn : {'appel direct à spawn_pokemon' if direct_call else 'commande texte !spawn'}")
        parts.append(f"⏱️ Intervalle : {state['interval_seconds']} s")

        # Compte à rebours
        remaining_line = "⏳ Prochain événement : "
        if not in_vc or state.get("next_fire_ts") is None:
            remaining_line += "— (désarmé : pas en vocal)"
        else:
            remaining = max(0, int(state["next_fire_ts"] - time.time()))
            m, s = divmod(remaining, 60)
            remaining_line += f"dans {m} min {s:02d} s"
        parts.append(remaining_line)

        await ctx.reply("\n".join(parts))
