# logic_battle.py

import discord
import asyncio
import random

from combat.battle_state import BattleState
from combat.views_attack import AttackOrSwitchView, SwitchSelectView  # ⬅️ nouveau
from combat.utils import calculate_damage, _type_effectiveness  # eff (optionnel pour messages)

def build_turn_embed(state, tour, fields):
    emb = discord.Embed(title=f"🔁 Tour {tour}", color=0x00BFFF)
    for name, value in fields:
        emb.add_field(name=name, value=value, inline=False)

    if state.active_player.get("image"):
        emb.set_thumbnail(url=state.active_player["image"])
    if state.active_bot.get("image"):
        emb.set_image(url=state.active_bot["image"])

    hp_p = state.get_hp("player")
    hp_b = state.get_hp("bot")
    emb.set_footer(text=f"PV {state.active_player['name']} : {hp_p} | PV {state.active_bot['name']} : {hp_b}")
    return emb

async def prompt_player_action(interaction, state):
    """
    Ouvre la view actions (attaquer / changer).
    Retourne un dict:
      {"action": "attack", "attack": str} ou {"action": "switch", "index": int}
    """
    view = AttackOrSwitchView(state.active_player["attacks"])
    msg = await interaction.channel.send(
        content=f"🧠 Choisis une action pour **{state.active_player['name']}** :",
        view=view
    )
    await view.wait()
    await msg.delete()

    if view.selected_action == "attack":
        return {"action": "attack", "attack": view.selected_attack}

    if view.selected_action == "switch":
        # Ouvre la sélection des Pokémon
        sv = SwitchSelectView(state)
        smsg = await interaction.channel.send(
            content="🔄 Qui veux-tu envoyer ? (Pokémon non K.O., différent de l'actuel)",
            view=sv
        )
        await sv.wait()
        await smsg.delete()

        if sv.chosen_index is None:
            # Aucun choix => annule et redemande l'action
            await interaction.channel.send("❌ Aucun changement sélectionné. Retour au choix d'action.")
            return await prompt_player_action(interaction, state)

        return {"action": "switch", "index": sv.chosen_index}

    # Temps écoulé / pas de choix → attaque aléatoire
    atk = random.choice(state.active_player["attacks"])
    await interaction.channel.send(f"⏱ Aucun choix effectué. **{atk}** est utilisé par défaut.")
    return {"action": "attack", "attack": atk}

async def start_battle_turn_based(interaction, player_team, bot_team):
    state = BattleState(player_team, bot_team)
    tour = 1

    await interaction.channel.send(
        f"⚔️ Début du combat entre **{state.active_player['name']}** et **{state.active_bot['name']}** !"
    )

    while True:
        await asyncio.sleep(1)

        # Ordre d'attaque
        order = ['player', 'bot'] if state.active_player['stats']['speed'] >= state.active_bot['stats']['speed'] else ['bot', 'player']
        fields = []

        # ---- ACTION 1 ----
        if order[0] == "player":
            if not state.is_player_ko():
                choice = await prompt_player_action(interaction, state)
                if choice["action"] == "attack":
                    attack_name = choice["attack"]
                    dmg = calculate_damage(state.active_player, state.active_bot, attack_name)
                    state.take_damage("bot", dmg)
                    fields.append((f"{state.active_player['name']} utilise {attack_name} !",
                                   f"{state.active_bot['name']} perd {dmg} PV."))
                    # (optionnel) retour efficacité
                    eff = _type_effectiveness(
                        next((a.get("type","normal") for a in []), "normal"),  # tu peux brancher ici si tu veux afficher le msg
                        state.active_bot.get("type", [])
                    )

                    if state.is_bot_ko():
                        fields.append(("💥 K.O.", f"{state.active_bot['name']} est K.O. !"))
                        if not state.switch_bot():
                            embed = build_turn_embed(state, tour, fields)
                            await interaction.channel.send(embed=embed)
                            await interaction.channel.send("🎉 **Victoire du joueur !**")
                            return
                        else:
                            fields.append((f"{state.active_bot['name']} entre en scène !", f"{state.active_bot['name']} se tient prêt."))
                else:
                    # SWITCH consomme l'action du joueur
                    if state.switch_player_to(choice["index"]):
                        fields.append(("🔄 Changement !", f"{state.active_player['name']} entre en scène !"))
                    else:
                        fields.append(("❌ Échec du changement", "Choix invalide."))
            # puis l'adversaire agira en ACTION 2
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
                        fields.append((f"{state.active_player['name']} entre en scène !", f"{state.active_player['name']} se tient prêt."))

        # ---- ACTION 2 ----
        if order[1] == "bot":
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
                        fields.append((f"{state.active_player['name']} entre en scène !", f"{state.active_player['name']} se tient prêt."))
        else:
            # Joueur agit en second
            if not state.is_player_ko():
                choice = await prompt_player_action(interaction, state)
                if choice["action"] == "attack":
                    attack_name = choice["attack"]
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
                            fields.append((f"{state.active_bot['name']} entre en scène !", f"{state.active_bot['name']} se tient prêt."))
                else:
                    # SWITCH consomme l'action du joueur
                    if state.switch_player_to(choice["index"]):
                        fields.append(("🔄 Changement !", f"{state.active_player['name']} entre en scène !"))
                    else:
                        fields.append(("❌ Échec du changement", "Choix invalide."))

        # ---- ENVOI FIN DE TOUR ----
        embed = build_turn_embed(state, tour, fields)
        await interaction.channel.send(embed=embed)

        tour += 1
        await asyncio.sleep(2)
