# croco_event.py
# ============================================================
# Déclenche un événement toutes les 60s si "Croco" est en vocal :
# - envoie un message "le plus beau"
# - lance un spawn pour Croco (via fonction directe si fournie,
#   sinon en postant la commande texte !spawn @Croco)
#
# Intégration dans main.py (avant bot.run) :
#
#   from croco_event import setup_croco_event
#   setup_croco_event(
#       bot,
#       VOICE_CHANNEL_ID,
#       TEXT_CHANNEL_ID,
#       TARGET_USER_ID_CROCO,
#       spawn_func=spawn_pokemon,        # optionnel : appelle directement ta fonction
#       role_id=ROLE_ID                  # optionnel : juste passé à spawn_func si besoin
#   )
#
# Commandes disponibles (réservées à Croco) :
#   - !croco_now       : déclenche l'événement immédiatement
#   - !croco_status    : affiche l’état (en vocal ? actif ?)
# ============================================================

import discord
from discord.ext import tasks, commands
from typing import Optional, Callable

CHECK_INTERVAL = 60  # secondes (événement toutes les minutes)

def setup_croco_event(
    bot: commands.Bot,
    voice_channel_id: int,
    text_channel_id: int,
    target_user_id: int,
    spawn_func: Optional[Callable] = None,   # signature attendue: async def spawn_pokemon(channel, force=False, author=None, target_user=None, pokemon_name=None, shiny_rate=64)
    role_id: Optional[int] = None
):
    """
    Active un loop qui, chaque minute si Croco est en vocal :
      - envoie un message "Croco est le plus beau"
      - déclenche un spawn pour Croco (fonction directe si fournie, sinon message !spawn @Croco)
    """

    # Espace de stockage sur le bot pour éviter doublons
    if not hasattr(bot, "_croco_event_state"):
        bot._croco_event_state = {
            "task_started": False
        }
    state = bot._croco_event_state
    state.update({
        "voice_channel_id": voice_channel_id,
        "text_channel_id": text_channel_id,
        "target_user_id": target_user_id,
        "spawn_func": spawn_func,
        "role_id": role_id
    })

    # --------- Utils ---------
    async def get_channels():
        vc = bot.get_channel(state["voice_channel_id"])
        tx = bot.get_channel(state["text_channel_id"])
        return vc, tx

    def is_croco_only():
        async def predicate(ctx: commands.Context):
            return ctx.author.id == state["target_user_id"]
        return commands.check(predicate)

    # --------- Tâche principale ---------
    @tasks.loop(seconds=CHECK_INTERVAL)
    async def croco_minutely_event():
        vc, channel = await get_channels()
        if not vc or not isinstance(vc, (discord.VoiceChannel, discord.StageChannel)):
            return
        if not channel or not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return

        # Croco est-il dans le vocal ?
        croco_in_vc = any(m.id == state["target_user_id"] for m in vc.members)
        if not croco_in_vc:
            return

        # Récupération de l'objet Membre pour mention + author
        croco_member = vc.guild.get_member(state["target_user_id"])
        if not croco_member:
            return

        # 1) Message flatteur
        try:
            await channel.send(f"💎 {croco_member.mention} est le plus beau ! 😍")
        except Exception:
            # On n'arrête pas la loop pour un simple échec d'envoi
            pass

        # 2) Déclenchement du spawn
        try:
            if callable(state["spawn_func"]):
                # Appel direct à la fonction fournie par ton main.py
                await state["spawn_func"](
                    channel=channel,
                    force=True,
                    author=croco_member,          # l'auteur affiché dans le titre
                    target_user=croco_member,     # seul Croco peut le capturer si ta fonction gère cette restriction
                    shiny_rate=64                  # ou autre, à ta guise
                )
            else:
                # Fallback: message de commande texte (sera capté par on_message / commandes)
                await channel.send(f"!spawn {croco_member.mention}")
        except Exception:
            # On ignore les exceptions ponctuelles pour ne pas stopper la tâche
            pass

    # Démarrage unique
    if not state["task_started"]:
        croco_minutely_event.start()
        state["task_started"] = True

    # --------- Commandes utilitaires ---------
    @bot.command(name="croco_now")
    @is_croco_only()
    async def croco_now(ctx: commands.Context):
        """Déclenche l’événement immédiatement (test manuel)."""
        vc, channel = await get_channels()
        if not channel:
            await ctx.reply("❌ Canal texte introuvable.")
            return

        # Message flatteur
        await channel.send(f"💎 {ctx.author.mention} est le plus beau ! 😍")

        # Spawn
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
        """Affiche l’état de l’événement minutely."""
        vc, channel = await get_channels()
        parts = []
        parts.append(f"🔁 Tâche active : {'oui' if state.get('task_started') else 'non'}")
        parts.append(f"🗣️ Vocal configuré : {'oui' if isinstance(vc, (discord.VoiceChannel, discord.StageChannel)) else 'non'}")
        parts.append(f"💬 Texte configuré : {'oui' if isinstance(channel, (discord.TextChannel, discord.Thread)) else 'non'}")

        in_vc = False
        if vc and isinstance(vc, (discord.VoiceChannel, discord.StageChannel)):
            in_vc = any(m.id == state['target_user_id'] for m in vc.members)
        parts.append(f"✅ Croco en vocal : {'oui' if in_vc else 'non'}")

        direct_call = callable(state["spawn_func"])
        parts.append(f"🎯 Mode spawn : {'appel direct à spawn_pokemon' if direct_call else 'commande texte !spawn'}")

        await ctx.reply("\n".join(parts))
