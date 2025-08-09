# croco_event.py
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
    interval_seconds: int = DEFAULT_INTERVAL
):
    if not hasattr(bot, "_croco_event_state"):
        bot._croco_event_state = {"task_started": False}
    state = bot._croco_event_state
    state.update({
        "voice_channel_id": voice_channel_id,
        "text_channel_id": text_channel_id,
        "target_user_id": target_user_id,
        "spawn_func": spawn_func,
        "role_id": role_id,
        "interval_seconds": int(max(1, interval_seconds))
    })

    async def get_channels():
        vc = bot.get_channel(state["voice_channel_id"])
        tx = bot.get_channel(state["text_channel_id"])
        return vc, tx

    def is_croco_only():
        async def predicate(ctx: commands.Context):
            return ctx.author.id == state["target_user_id"]
        return commands.check(predicate)

    @tasks.loop(seconds=DEFAULT_INTERVAL)  # valeur par défaut, ajustée juste avant start
    async def croco_minutely_event():
        vc, channel = await get_channels()
        if not vc or not hasattr(vc, "members"):
            return
        if not channel or not hasattr(channel, "send"):
            return

        croco_in_vc = any(m.id == state["target_user_id"] for m in vc.members)
        if not croco_in_vc:
            return

        croco_member = vc.guild.get_member(state["target_user_id"])
        if not croco_member:
            return

        try:
            await channel.send(f"💎 {croco_member.mention} est le plus beau ! 😍")
        except Exception:
            pass

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

    if not state["task_started"]:
        async def _start_when_ready():
            await bot.wait_until_ready()
            try:
                croco_minutely_event.change_interval(seconds=state["interval_seconds"])
            except Exception:
                # au cas où, on garde l’interval défaut
                pass
            croco_minutely_event.start()
            state["task_started"] = True

        bot.loop.create_task(_start_when_ready())

    @bot.command(name="croco_now")
    @is_croco_only()
    async def croco_now(ctx: commands.Context):
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

    @bot.command(name="croco_status")
    @is_croco_only()
    async def croco_status(ctx: commands.Context):
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
        await ctx.reply("\n".join(parts))
