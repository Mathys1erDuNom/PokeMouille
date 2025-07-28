import discord
from discord.ext import commands
from combats.battle_views import create_team_selection_view, BattleView
from db import get_captures
import random

active_battles = {}  # user_id -> battle state

def setup_battle_commands(bot):

    @bot.command()
    async def battle(ctx):
        user_id = str(ctx.author.id)
        captures = get_captures(user_id)

        if not captures:
            await ctx.send("❌ Tu n'as aucun Pokémon pour combattre.")
            return

        await ctx.send(f"🧠 Sélectionne ton équipe pour combattre le bot :")

        view = create_team_selection_view(ctx.author, captures, on_team_selected)
        await ctx.send(view=view)

    async def on_team_selected(user, selected_team):
        state = {
            "player": {
                "user": user,
                "team": selected_team,
                "current": selected_team[0],
                "hp": selected_team[0]["stats_iv"]["hp"],
            },
            "bot": {
                "team": random.sample(selected_team, k=len(selected_team)),
                "current": None,
                "hp": 0
            },
            "turn": "player"
        }
        state["bot"]["current"] = state["bot"]["team"][0]
        state["bot"]["hp"] = state["bot"]["current"]["stats_iv"]["hp"]

        active_battles[user.id] = state

        embed = discord.Embed(
            title="⚔️ Combat contre le bot !",
            description=f"Ton Pokémon actuel : **{state['player']['current']['name']}**",
            color=0x00FF00
        )
        view = BattleView(user, state, on_player_action)
        await user.send(embed=embed, view=view)

    async def on_player_action(user, action_name):
        state = active_battles.get(user.id)
        if not state:
            return

        player_atk = state["player"]["current"]["stats_iv"]["attack"]
        damage = random.randint(player_atk // 4, player_atk // 2)
        state["bot"]["hp"] -= damage

        if state["bot"]["hp"] <= 0:
            await user.send(f"🎉 Ton Pokémon a mis K.O. le bot avec {action_name} !")
            del active_battles[user.id]
            return

        # Bot contre-attaque
        bot_atk = state["bot"]["current"]["stats_iv"]["attack"]
        counter_damage = random.randint(bot_atk // 4, bot_atk // 2)
        state["player"]["hp"] -= counter_damage

        if state["player"]["hp"] <= 0:
            await user.send(f"💀 Ton Pokémon a été mis K.O. par le bot...")
            del active_battles[user.id]
            return

        embed = discord.Embed(
            title="⚔️ Combat en cours",
            description=(
                f"Ton Pokémon : **{state['player']['current']['name']}** - {state['player']['hp']} PV\n"
                f"Bot : **{state['bot']['current']['name']}** - {state['bot']['hp']} PV"
            ),
            color=0xFFA500
        )
        view = BattleView(user, state, on_player_action)
        await user.send(embed=embed, view=view)
