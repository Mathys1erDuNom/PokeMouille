import random
import asyncio
import time
import discord
from discord.ext import tasks

# Variables globales pour suivre les tâches
croco_task = None
last_check_time = time.time()
CHECK_INTERVAL = 60  # on vérifie toutes les minutes

def setup_croco_event(bot, voice_channel_id, text_channel_id, target_user_id):
    """
    Active un événement qui, si Croco est en vocal, toutes les 20-30 minutes :
    - Envoie un message disant qu'il est le plus beau
    - Lance la commande !spawn pour lui
    """
    global croco_task

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def croco_checker():
        vc = bot.get_channel(voice_channel_id)
        channel = bot.get_channel(text_channel_id)
        if not vc or not channel:
            return

        # Si Croco est dans le vocal
        member_ids = [m.id for m in vc.members]
        if target_user_id in member_ids:
            # On garde une variable sur le prochain "tirage"
            if not hasattr(bot, "croco_next_event"):
                bot.croco_next_event = time.time() + random.randint(30, 60)  # 20-30 min
                return

            # Si le temps est écoulé
            if time.time() >= bot.croco_next_event:
                croco_user = vc.guild.get_member(target_user_id)
                if croco_user:
                    await channel.send(f"💎 {croco_user.mention} est le plus beau ! 😍")
                    await channel.send(f"!spawn {croco_user.mention}")
                # On redéfinit le prochain tirage
                bot.croco_next_event = time.time() + random.randint(30, 60)

    croco_task = croco_checker
    croco_checker.start()
