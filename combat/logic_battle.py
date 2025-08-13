import discord
import asyncio
import random

from combat.battle_state import BattleState
from combat.views_attack import AttackView
from combat.utils import calculate_damage


def sprite_embed(pokemon, subtitle=None, color=0x00BFFF):
    """Crée un embed qui affiche le sprite d'un Pokémon."""
    name = pokemon.get("name", "Pokémon")
    img = pokemon.get("image", None)
    emb = discord.Embed(
        title=name if not subtitle else f"{name} — {subtitle}",
        color=color
    )
    if img:
        emb.set_image(url=img)
    return emb


async def start_battle_turn_based(interaction, player_team, bot_team):
    state = BattleState(player_team, bot_team)
    tour = 1

    # Début du combat : affiche juste les sprites des deux combattants initiaux
    await interaction.channel.send(
        content=f"⚔️ Début du combat entre **{state.active_player['name']}** et **{state.active_bot['name']}** !",
        embeds=[
            sprite_embed(state.active_player, "Côté joueur"),
            sprite_embed(state.active_bot, "Côté bot")
        ]
    )

    while True:
        await asyncio.sleep(1)

        # Déterminer l'ordre d'attaque
        if state.active_player['stats']['speed'] >= state.active_bot['stats']['speed']:
            order = ['player', 'bot']
        else:
            order = ['bot', 'player']

        main_embed = discord.Embed(title=f"🔁 Tour {tour}", color=0x00BFFF)

        sprite_embeds = []

        for actor in order:
            if actor == "player":
                if state.is_player_ko():
                    continue

                # Choix d'attaque
                view = AttackView(state.active_player["attacks"])
                prompt = await interaction.channel.send(
                    content=f"🧠 Choisis une attaque pour **{state.active_player['name']}** !",
                    view=view
                )
                await view.wait()

                attack_name = view.selected_attack
                if not attack_name:
                    attack_name = random.choice(state.active_player["attacks"])
                    await interaction.channel.send("⏱ Aucun choix effectué. Une attaque aléatoire est utilisée.")
                await prompt.delete()

                damage = calculate_damage(state.active_player, state.active_bot, attack_name)
                state.take_damage("bot", damage)

                main_embed.add_field(
                    name=f"{state.active_player['name']} utilise {attack_name} !",
                    value=f"{state.active_bot['name']} perd {damage} PV.",
                    inline=False
                )
                sprite_embeds.append(sprite_embed(state.active_player, f"Utilise {attack_name}"))
                sprite_embeds.append(sprite_embed(state.active_bot, f"Subit {damage} dégâts"))

                if state.is_bot_ko():
                    main_embed.add_field(
                        name="💥 K.O.",
                        value=f"{state.active_bot['name']} est K.O. !",
                        inline=False
                    )
                    sprite_embeds.append(sprite_embed(state.active_bot, "K.O."))
                    if not state.switch_bot():
                        await interaction.channel.send(embeds=[main_embed] + sprite_embeds)
                        await interaction.channel.send(
                            content="🎉 **Victoire du joueur !**",
                            embed=sprite_embed(state.active_player, "Vainqueur")
                        )
                        return
                    else:
                        sprite_embeds.append(sprite_embed(state.active_bot, "Nouveau Pokémon du bot"))

            else:  # bot
                if state.is_bot_ko():
                    continue

                attack_name = random.choice(state.active_bot["attacks"])
                damage = calculate_damage(state.active_bot, state.active_player, attack_name)
                state.take_damage("player", damage)

                main_embed.add_field(
                    name=f"{state.active_bot['name']} utilise {attack_name} !",
                    value=f"{state.active_player['name']} perd {damage} PV.",
                    inline=False
                )
                sprite_embeds.append(sprite_embed(state.active_bot, f"Utilise {attack_name}"))
                sprite_embeds.append(sprite_embed(state.active_player, f"Subit {damage} dégâts"))

                if state.is_player_ko():
                    main_embed.add_field(
                        name="💥 K.O.",
                        value=f"{state.active_player['name']} est K.O. !",
                        inline=False
                    )
                    sprite_embeds.append(sprite_embed(state.active_player, "K.O."))
                    if not state.switch_player():
                        await interaction.channel.send(embeds=[main_embed] + sprite_embeds)
                        await interaction.channel.send(
                            content="🤖 **Le bot a gagné le combat !**",
                            embed=sprite_embed(state.active_bot, "Vainqueur")
                        )
                        return
                    else:
                        sprite_embeds.append(sprite_embed(state.active_player, "Nouveau Pokémon du joueur"))

        main_embed.set_footer(
            text=f"PV {state.active_player['name']} : {state.get_hp('player')} | "
                 f"PV {state.active_bot['name']} : {state.get_hp('bot')}"
        )

        await interaction.channel.send(embeds=[main_embed] + sprite_embeds)
        tour += 1
        await asyncio.sleep(2)
