import discord
import asyncio
import random

from combat.battle_state import BattleState
from combat.views_attack import AttackView
from combat.utils import calculate_damage


def build_turn_embed(state, tour, fields):
    """
    Construit l'embed du tour avec :
      - les lignes d'action accumulées (fields)
      - les sprites actuels (thumbnail joueur, image bot)
      - le récap PV calculé *à la fin du tour*
    """
    emb = discord.Embed(title=f"🔁 Tour {tour}", color=0x00BFFF)

    # Actions du tour
    for name, value in fields:
        emb.add_field(name=name, value=value, inline=False)

    # Sprites actuels (après tous les switch/KO de ce tour)
    if state.active_player.get("image"):
        emb.set_thumbnail(url=state.active_player["image"])
    if state.active_bot.get("image"):
        emb.set_image(url=state.active_bot["image"])

    # PV de fin de tour (lecture juste avant l'envoi)
    hp_p = state.get_hp("player")
    hp_b = state.get_hp("bot")
    emb.set_footer(
        text=f"PV {state.active_player['name']} : {hp_p} | PV {state.active_bot['name']} : {hp_b}"
    )
    return emb


async def start_battle_turn_based(interaction, player_team, bot_team):
    state = BattleState(player_team, bot_team)
    tour = 1

    # Annonce initiale
    await interaction.channel.send(
        f"⚔️ Début du combat entre **{state.active_player['name']}** et **{state.active_bot['name']}** !"
    )

    while True:
        await asyncio.sleep(1)

        # Ordre d'attaque
        order = ['player', 'bot'] if state.active_player['stats']['speed'] >= state.active_bot['stats']['speed'] else ['bot', 'player']

        # On accumule les actions du tour ici
        fields = []

        # ---- ACTION 1 ----
        if order[0] == "player":
            if not state.is_player_ko():
                view = AttackView(state.active_player["attacks"])
                prompt = await interaction.channel.send(
                    content=f"🧠 Choisis une attaque pour **{state.active_player['name']}** !",
                    view=view
                )
                await view.wait()
                attack_name = view.selected_attack or random.choice(state.active_player["attacks"])
                if not view.selected_attack:
                    await interaction.channel.send("⏱ Aucun choix effectué. Une attaque aléatoire est utilisée.")
                await prompt.delete()

                dmg = calculate_damage(state.active_player, state.active_bot, attack_name)
                state.take_damage("bot", dmg)
                fields.append((f"{state.active_player['name']} utilise {attack_name} !",
                               f"{state.active_bot['name']} perd {dmg} PV."))

                if state.is_bot_ko():
                    fields.append(("💥 K.O.", f"{state.active_bot['name']} est K.O. !"))
                    # S'il ne reste plus de Pokémon au bot → fin immédiate
                    if not state.switch_bot():
                        embed = build_turn_embed(state, tour, fields)
                        await interaction.channel.send(embed=embed)
                        await interaction.channel.send("🎉 **Victoire du joueur !**")
                        return
                    else:
                        # Nouveau Pokémon bot entre en scène, on continue le tour
                        fields.append((
                            f"{state.active_bot['name']} entre en scène !",
                            f"{state.active_bot['name']} se tient prêt."
                        ))
        else:
            # Bot agit en premier
            if not state.is_bot_ko():
                attack_name = random.choice(state.active_bot["attacks"])
                dmg = calculate_damage(state.active_bot, state.active_player, attack_name)
                state.take_damage("player", dmg)
                fields.append((f"{state.active_bot['name']} utilise {attack_name} !",
                               f"{state.active_player['name']} perd {dmg} PV."))

                if state.is_player_ko():
                    fields.append(("💥 K.O.", f"{state.active_player['name']} est K.O. !"))
                    if not state.switch_player():
                        embed = build_turn_embed(state, tour, fields)
                        await interaction.channel.send(embed=embed)
                        await interaction.channel.send("🤖 **Le bot a gagné le combat !**")
                        return
                    else:
                        fields.append((
                            f"{state.active_player['name']} entre en scène !",
                            f"{state.active_player['name']} se tient prêt."
                        ))

        # ---- ACTION 2 ----
        if order[1] == "bot":
            if not state.is_bot_ko():  # peut être K.O. après action 1
                attack_name = random.choice(state.active_bot["attacks"])
                dmg = calculate_damage(state.active_bot, state.active_player, attack_name)
                state.take_damage("player", dmg)
                fields.append((f"{state.active_bot['name']} utilise {attack_name} !",
                               f"{state.active_player['name']} perd {dmg} PV."))

                if state.is_player_ko():
                    fields.append(("💥 K.O.", f"{state.active_player['name']} est K.O. !"))
                    if not state.switch_player():
                        # Fin de combat en fin de tour : on envoie l'embed avec PV *finaux*
                        embed = build_turn_embed(state, tour, fields)
                        await interaction.channel.send(embed=embed)
                        await interaction.channel.send("🤖 **Le bot a gagné le combat !**")
                        return
                    else:
                        fields.append((
                            f"{state.active_player['name']} entre en scène !",
                            f"{state.active_player['name']} se tient prêt."
                        ))
        else:
            # Joueur agit en second
            if not state.is_player_ko():
                view = AttackView(state.active_player["attacks"])
                prompt = await interaction.channel.send(
                    content=f"🧠 Choisis une attaque pour **{state.active_player['name']}** !",
                    view=view
                )
                await view.wait()
                attack_name = view.selected_attack or random.choice(state.active_player["attacks"])
                if not view.selected_attack:
                    await interaction.channel.send("⏱ Aucun choix effectué. Une attaque aléatoire est utilisée.")
                await prompt.delete()

                dmg = calculate_damage(state.active_player, state.active_bot, attack_name)
                state.take_damage("bot", dmg)
                fields.append((f"{state.active_player['name']} utilise {attack_name} !",
                               f"{state.active_bot['name']} perd {dmg} PV."))

                if state.is_bot_ko():
                    fields.append(("💥 K.O.", f"{state.active_bot['name']} est K.O. !"))
                    if not state.switch_bot():
                        embed = build_turn_embed(state, tour, fields)
                        await interaction.channel.send(embed=embed)
                        await interaction.channel.send("🎉 **Victoire du joueur !**")
                        return
                    else:
                        fields.append((
                            f"{state.active_bot['name']} entre en scène !",
                            f"{state.active_bot['name']} se tient prêt."
                        ))

        # ---- ENVOI FIN DE TOUR (après TOUTES les actions & switch) ----
        embed = build_turn_embed(state, tour, fields)
        await interaction.channel.send(embed=embed)

        tour += 1
        await asyncio.sleep(2)
