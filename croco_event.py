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
    **kwargs  # ← accepte interval_seconds sans planter
):
    interval_seconds = int(max(1, kwargs.get("interval_seconds", DEFAULT_INTERVAL)))

    # État partagé (évite doublons de tâche)
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
        "next_fire_ts": None,  # timestamp du prochain déclenchement (None si désarmé)
    })

    async def get_channels():
        vc = bot.get_channel(state["voice_channel_id"])
        tx = bot.get_channel(state["text_channel_id"])
        return vc, tx

    # --- Helper: répondre en MP, sinon fallback public
    async def _send_dm_or_fallback(ctx: commands.Context, content: str):
        try:
            await ctx.author.send(content)
            try:
                await ctx.message.add_reaction("📩")
            except Exception:
                pass
        except discord.Forbidden:
            await ctx.reply("⚠️ Impossible d’envoyer un MP (DM fermés). Réponse ici :\n" + content)
        except Exception:
            await ctx.reply(content)

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

        # Croco en vocal ?
        croco_in_vc = any(m.id == state["target_user_id"] for m in vc.members)

        # Pas en vocal → désarmer le timer
        if not croco_in_vc:
            state["next_fire_ts"] = None
            return

        now = time.time()

        # En vocal mais pas armé → armer
        if state["next_fire_ts"] is None:
            state["next_fire_ts"] = now + state["interval_seconds"]
            return

        # L'heure est arrivée → déclenchement + réarmement
        if now >= state["next_fire_ts"]:
            croco_member = vc.guild.get_member(state["target_user_id"])
            if not croco_member:
                state["next_fire_ts"] = now + state["interval_seconds"]
                return

            # 1) Message flatteur public
            try:
                await channel.send(f"💎 {croco_member.mention} est le plus beau ! 😍")
            except Exception:
                pass

            # 2) Spawn (appel direct si fourni, sinon commande texte)
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

            # Réarmer
            state["next_fire_ts"] = now + state["interval_seconds"]

    # Démarrage via listener (compatible discord.py v2+)
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
        """Déclenche immédiatement (test) avec accusé en MP."""
        vc, channel = await get_channels()
        if not channel:
            await _send_dm_or_fallback(ctx, "❌ Canal texte introuvable.")
            return

        # Public
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

        # Réarmement + DM
        state["next_fire_ts"] = time.time() + state["interval_seconds"]
        await _send_dm_or_fallback(ctx, f"✅ Événement déclenché. Prochain dans ~{state['interval_seconds']} s.")

    @bot.command(name="croco_status")
    @is_croco_only()
    async def croco_status(ctx: commands.Context):
        """État + temps restant (réponse en MP)."""
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
        if not in_vc or state.get("next_fire_ts") is None:
            parts.append("⏳ Prochain événement : — (désarmé : pas en vocal)")
        else:
            remaining = max(0, int(state["next_fire_ts"] - time.time()))
            m, s = divmod(remaining, 60)
            parts.append(f"⏳ Prochain événement : dans {m} min {s:02d} s")

        await _send_dm_or_fallback(ctx, "\n".join(parts))
