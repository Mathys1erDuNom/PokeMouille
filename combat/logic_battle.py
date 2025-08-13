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
        # Image plus visible que thumbnail pour bien "afficher le sprite"
        emb.set_image(url=img)
    return emb


async def start_battle_turn_based(interaction, player_team, bot_team):
    state = BattleState(player_team, bot_team)
    tour = 1

    # Annonce + sprites des 2 combattants actifs
    await interaction.channel.send(
        content=f"⚔️ Début du combat entre **{state.active_player['name']}** et **{state.active_bot['name']}** !",
        embeds=[
            sprite_embed(state.active_player, "Côté joueur"),
            sprite_embed(state.active_bot, "Côté bot")
        ]
    )

    while True:
        await asyncio.sleep(1)

        # Déterminer l'ordre d'attaque (affiche aussi le sprite de l'attaquant prioritaire)
        if state.active_player['stats']['speed'] >= state.active_bot['stats']['speed']:
            order = ['player', 'bot']
            first_attacker = state.active_player
            first_label = "Joueur"
        else:
            order = ['bot', 'player']
            first_attacker = state.active_bot
            first_label = "Bot"

        main_embed = discord.Embed(title=f"🔁 Tour {tour}", color=0x00BFFF)
        main_embed.set_thumbnail(url=first_attacker.get("image", None))
        main_embed.add_field(
            name="Initiative",
            value=f"{first_label} ({first_attacker['name']}) agit en premier.",
            inline=False
        )

        # On accumule ici tous les embeds de sprites à montrer ce tour
        sprite_embeds = [sprite_embed(state.active_player, "Actif — Joueur"),
                         sprite_embed(state.active_bot, "Actif — Bot")]

        for actor in order:
            if actor == "player":
                if state.is_player_ko():
                    continue

                # Prompt de choix + sprite du Pokémon du joueur
                view = AttackView(state.active_player["attacks"])
                prompt = await interaction.channel.send(
                    content=f"🧠 Choisis une attaque pour **{state.active_player['name']}** !",
                    view=view,
                    embed=sprite_embed(state.active_player, "Choix d'attaque")
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
                    name=f"Joueur - {state.active_player['name']} utilise {attack_name} !",
                    value=f"{state.active_bot['name']} perd {damage} PV.",
                    inline=False
                )

                # Sprites des deux protagonistes de l'action
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
                        # Fin de combat : récap + sprites finaux
                        main_embed.set_footer(
                            text=f"PV {state.active_player['name']} : {state.get_hp('player')} | "
                                 f"PV {state.active_bot['name']} : 0"
                        )
                        await interaction.channel.send(embeds=[main_embed] + sprite_embeds)
                        await interaction.channel.send(
                            content="🎉 **Victoire du joueur !**",
                            embed=sprite_embed(state.active_player, "Vainqueur")
                        )
                        return
                    else:
                        # Affiche le sprite du nouveau Pokémon du bot
                        sprite_embeds.append(sprite_embed(state.active_bot, "Entre en scène (Bot)"))

            else:  # bot
                if state.is_bot_ko():
                    continue

                attack_name = random.choice(state.active_bot["attacks"])
                damage = calculate_damage(state.active_bot, state.active_player, attack_name)
                state.take_damage("player", damage)

                main_embed.add_field(
                    name=f"Bot - {state.active_bot['name']} utilise {attack_name} !",
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
                        main_embed.set_footer(
                            text=f"PV {state.active_player['name']} : 0 | "
                                 f"PV {state.active_bot['name']} : {state.get_hp('bot')}"
                        )
                        await interaction.channel.send(embeds=[main_embed] + sprite_embeds)
                        await interaction.channel.send(
                            content="🤖 **Le bot a gagné le combat !**",
                            embed=sprite_embed(state.active_bot, "Vainqueur")
                        )
                        return
                    else:
                        # Affiche le sprite du nouveau Pokémon du joueur
                        sprite_embeds.append(sprite_embed(state.active_player, "Entre en scène (Joueur)"))

        main_embed.set_footer(
            text=f"PV {state.active_player['name']} : {state.get_hp('player')} | "
                 f"PV {state.active_bot['name']} : {state.get_hp('bot')}"
        )

        # Envoie le résumé du tour + tous les sprites pertinents
        await interaction.channel.send(embeds=[main_embed] + sprite_embeds)

        tour += 1
        await asyncio.sleep(2)
