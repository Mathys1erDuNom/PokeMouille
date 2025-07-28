import discord
import asyncio
import random

from combat.battle_state import BattleState
from combat.views_attack import AttackView
from combat.utils import calculate_damage

async def start_battle_turn_based(interaction, player_team, bot_team):
    state = BattleState(player_team, bot_team)
    tour = 1

    await interaction.channel.send(f"⚔️ Début du combat entre **{state.active_player['name']}** et **{state.active_bot['name']}** !")

    while True:
        await asyncio.sleep(1)

        # Déterminer l'ordre d'attaque
        if state.active_player['stats']['speed'] >= state.active_bot['stats']['speed']:
            order = ['player', 'bot']
            sprite_url = state.active_player["image"]
        else:
            order = ['bot', 'player']
            sprite_url = state.active_bot["image"]

        embed = discord.Embed(title=f"🔁 Tour {tour}", color=0x00BFFF)
        embed.set_thumbnail(url=sprite_url)  # Affiche le sprite de l'attaquant principal

        for actor in order:
            if actor == "player":
                if state.is_player_ko():
                    continue
                
                view = AttackView(state.active_player["attacks"])
                msg = await interaction.channel.send(
                    f"🧠 Choisis une attaque pour **{state.active_player['name']}** !",
                    view=view
                )
                await view.wait()

                attack_name = view.selected_attack
                if not attack_name:
                    attack_name = random.choice(state.active_player["attacks"])
                    await interaction.channel.send("⏱ Aucun choix effectué. Une attaque aléatoire est utilisée.")
                await msg.delete()

                damage = calculate_damage(state.active_player, state.active_bot, attack_name)
                state.take_damage("bot", damage)

                embed.add_field(
                    name=f"Joueur - {state.active_player['name']} utilise {attack_name} !",
                    value=f"{state.active_bot['name']} perd {damage} PV.",
                    inline=False
                )

                if state.is_bot_ko():
                    embed.add_field(name="💥 K.O.", value=f"{state.active_bot['name']} est K.O. !", inline=False)
                    if not state.switch_bot():
                        await interaction.channel.send(embed=embed)
                        await interaction.channel.send("🎉 **Victoire du joueur !**")
                        return
            
            else:  # bot
                if state.is_bot_ko():
                    continue

                attack_name = random.choice(state.active_bot["attacks"])
                damage = calculate_damage(state.active_bot, state.active_player, attack_name)
                state.take_damage("player", damage)

                embed.add_field(
                    name=f"Bot - {state.active_bot['name']} utilise {attack_name} !",
                    value=f"{state.active_player['name']} perd {damage} PV.",
                    inline=False
                )

                if state.is_player_ko():
                    embed.add_field(name="💥 K.O.", value=f"{state.active_player['name']} est K.O. !", inline=False)
                    if not state.switch_player():
                        await interaction.channel.send(embed=embed)
                        await interaction.channel.send("🤖 **Le bot a gagné le combat !**")
                        return

        embed.set_footer(
            text=f"PV {state.active_player['name']} : {state.get_hp('player')} | PV {state.active_bot['name']} : {state.get_hp('bot')}"
        )
        await interaction.channel.send(embed=embed)
        tour += 1
        await asyncio.sleep(2)
