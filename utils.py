import discord
from discord.ext import commands, tasks
import random, asyncio, os, json

TARGET_USER_ID_CROCO = int(os.getenv("TARGET_USER_ID_CROCO"))





def is_croco():
    def predicate(ctx):
        return ctx.author.id == TARGET_USER_ID_CROCO
    return commands.check(predicate)