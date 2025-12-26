# logic_battle.py

import discord
import asyncio
import random

from combat.battle_state import BattleState
from combat.views_attack import AttackOrSwitchView, SwitchSelectView
from combat.utils import calculate_damage  # <-- on garde

from badge_db import give_badge, get_user_badges

# Dictionnaire qui lie le nom de l'adversaire à l'ID du badge
BADGES_ADVERSAIRES = {
    "Erika": 1,   # ID du badge Roche
    "Le Leader Cascade": 2, # ID du badge Cascade
    # ajouter d'autres si nécessaire
}



# ✨ NEW: petite fonction utilitaire pour afficher les effets
def _format_damage_line(target_label: str, dmg: int, details: dict) -> str:
    """
    target_label: ex. "Pikachu (👤 Joueur)" ou "Roucool (🤖 Bot)"
    """
    tags = []
    eff = details["eff_multiplier"]
    if eff == 0:
        tags.append("⛔ Aucun effet")
    elif eff > 1:
        tags.append("⚡ Super efficace")
    elif eff < 1:
        tags.append("🛡️ Peu efficace")

    if details["crit"]:
        tags.append("💥 Coup critique !")

    if details.get("stab"):
        tags.append("STAB")

    suffix = (" — " + " · ".join(tags)) if tags else ""
    return f"{target_label} perd {dmg} PV.{suffix}"


def build_turn_embed(state, tour, fields, adversaire_name="🤖 Bot"):
    emb = discord.Embed(title=f"🔁 Tour {tour}", color=0x00BFFF)
    for name, value in fields:  # ici, fields doit être liste de tuples
        emb.add_field(name=name, value=value, inline=False)

    if state.active_player.get("image"):
        emb.set_thumbnail(url=state.active_player["image"])
    if state.active_bot.get("image"):
        emb.set_image(url=state.active_bot["image"])

    hp_p = state.get_hp("player")
    hp_b = state.get_hp("bot")
    emb.set_footer(
        text=f"PV {state.active_player['name']} (👤 Joueur): {hp_p} | "
             f"PV {state.active_bot['name']} ({adversaire_name}): {hp_b}"
    )
    return emb



async def prompt_player_action(interaction, state):
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
        sv = SwitchSelectView(state)
        smsg = await interaction.channel.send(
            content="🔄 Qui veux-tu envoyer ? (Pokémon non K.O., différent de l'actuel)",
            view=sv
        )
        await sv.wait()
        await smsg.delete()

        if sv.chosen_index is None:
            await interaction.channel.send("❌ Aucun changement sélectionné. Retour au choix d'action.")
            return await prompt_player_action(interaction, state)

        return {"action": "switch", "index": sv.chosen_index}

    # Timeout / pas de choix → attaque aléatoire
    atk = random.choice(state.active_player["attacks"])
    await interaction.channel.send(f"⏱ Aucun choix effectué. **{atk}** est utilisé par défaut.")
    return {"action": "attack", "attack": atk}




async def start_battle_turn_based(interaction, player_team, bot_team, adversaire_name="Bot", repliques=None):
    repliques = repliques or {}

    if repliques.get("start"):
        await interaction.channel.send(
        f"🧑‍🎤 **{adversaire_name}** : {repliques['start']}"
    )


    state = BattleState(player_team, bot_team)
    tour = 1

    await interaction.channel.send(
        f"⚔️ Début du combat entre **{state.active_player['name']} (👤 Joueur)** "
        f"et **{state.active_bot['name']} (🤖 Bot)** !"
    )

    while True:
        await asyncio.sleep(1)

        order = (
            ['player', 'bot']
            if state.active_player['stats']['speed'] >= state.active_bot['stats']['speed']
            else ['bot', 'player']
        )
        fields = []
        end_turn = False

        # ---- ACTION 1 ----
        if order[0] == "player":
            if not state.is_player_ko():
                choice = await prompt_player_action(interaction, state)
                if choice["action"] == "attack":
                    attack_name = choice["attack"]
                    # 🔁 CHANGED: on récupère les détails
                    det = calculate_damage(state.active_player, state.active_bot, attack_name, return_details=True)
                    dmg = det["damage"]
                    state.take_damage("bot", dmg)
                    fields.append((
                        f"{state.active_player['name']} (👤 Joueur) utilise {attack_name} !",
                        _format_damage_line(f"{state.active_bot['name']} ({adversaire_name})", dmg, det)

                    ))

                    if state.is_bot_ko():
                        if repliques.get("ko"):
                            await interaction.channel.send(
                            f"🧑‍🎤 **{adversaire_name}** : {repliques['ko']}"
                        )

                        
                        fields.append(("💥 K.O.", f"{state.active_bot['name']} ({adversaire_name}) est K.O. !"))

                        if not state.switch_bot():
                            embed = build_turn_embed(state, tour, fields, adversaire_name)
                            await interaction.channel.send(embed=embed)
                             # ---- LOGIQUE BADGE ----
                            badge_id = BADGES_ADVERSAIRES.get(adversaire_name)
                            if badge_id:
                                user_id = str(interaction.user.id)
                                user_badges = get_user_badges(user_id)
                                if badge_id not in user_badges:
                                    give_badge(user_id, badge_id)
                                    await interaction.channel.send(f"🏅 Félicitations ! Tu as obtenu le badge **{badge_id}** pour avoir battu {adversaire_name} !")
                                else:
                                    await interaction.channel.send(f"Tu as déjà ce badge pour {adversaire_name} !")
                            # -----------------------

                            # Message final de victoire
                            if repliques.get("lose"):
                                await interaction.channel.send(f"🧑‍🎤 **{adversaire_name}** : {repliques['lose']}")
                            await interaction.channel.send("🎉 **Victoire du joueur !**")
                            return
                        else:
                                fields.append((
                                
                                f"{state.active_bot['name']} ({adversaire_name}) entre en scène !",

                                f"{state.active_bot['name']} ({adversaire_name}) se tient prêt."
                            ))
                        end_turn = True
                else:
                    if state.switch_player_to(choice["index"]):
                        fields.append((
                            "🔄 Changement !",
                            f"{state.active_player['name']} (👤 Joueur) entre en scène !"
                        ))
                    else:
                        fields.append(("❌ Échec du changement", "Choix invalide."))
        else:
            if not state.is_bot_ko():
                attack_name = random.choice(state.active_bot["attacks"])
                # 🔁 CHANGED: on récupère les détails
                det = calculate_damage(state.active_bot, state.active_player, attack_name, return_details=True)
                dmg = det["damage"]
                state.take_damage("player", dmg)
                fields.append((
                    f"{state.active_bot['name']} (🤖 Bot) utilise {attack_name} !",
                    _format_damage_line(f"{state.active_player['name']} (👤 Joueur)", dmg, det)
                ))

                if state.is_player_ko():
                    fields.append(("💥 K.O.", f"{state.active_player['name']} (👤 Joueur) est K.O. !"))
                    if not state.switch_player():
                        embed = build_turn_embed(state, tour, fields,  adversaire_name)
                        await interaction.channel.send(embed=embed)
                        await interaction.channel.send("🤖 **Le bot a gagné le combat !**")
                        return
                    else:
                        fields.append((
                            f"{state.active_player['name']} (👤 Joueur) entre en scène !",
                            f"{state.active_player['name']} (👤 Joueur) se tient prêt."
                        ))
                    end_turn = True

        if end_turn:
            embed = build_turn_embed(state, tour, fields,  adversaire_name)
            await interaction.channel.send(embed=embed)
            await interaction.channel.send("🛎 Fin du tour (K.O. détecté).")
            tour += 1
            await asyncio.sleep(2)
            continue

        # ---- ACTION 2 ----
        if order[1] == "bot":
            if not state.is_bot_ko():
                attack_name = random.choice(state.active_bot["attacks"])
                det = calculate_damage(state.active_bot, state.active_player, attack_name, return_details=True)
                dmg = det["damage"]
                state.take_damage("player", dmg)
                fields.append((
                    f"{state.active_bot['name']} (🤖 Bot) utilise {attack_name} !",
                    _format_damage_line(f"{state.active_player['name']} (👤 Joueur)", dmg, det)
                ))

                if state.is_player_ko():
                    fields.append(("💥 K.O.", f"{state.active_player['name']} (👤 Joueur) est K.O. !"))
                    if not state.switch_player():
                        embed = build_turn_embed(state, tour, fields,  adversaire_name)
                        await interaction.channel.send(embed=embed)
                        await interaction.channel.send("🤖 **Le bot a gagné le combat !**")
                        return
                    else:
                        fields.append((
                            f"{state.active_player['name']} (👤 Joueur) entre en scène !",
                            f"{state.active_player['name']} (👤 Joueur) se tient prêt."
                        ))
        else:
            if not state.is_player_ko():
                choice = await prompt_player_action(interaction, state)
                if choice["action"] == "attack":
                    attack_name = choice["attack"]
                    det = calculate_damage(state.active_player, state.active_bot, attack_name, return_details=True)
                    dmg = det["damage"]
                    state.take_damage("bot", dmg)
                    fields.append((
                        f"{state.active_player['name']} (👤 Joueur) utilise {attack_name} !",
                        _format_damage_line(f"{state.active_bot['name']} ({adversaire_name})", dmg, det)

                    ))

                    if state.is_bot_ko():
                        if repliques.get("ko"):
                            await interaction.channel.send(
                            f"🧑‍🎤 **{adversaire_name}** : {repliques['ko']}"
                        )

                        
                        fields.append(("💥 K.O.", f"{state.active_bot['name']} ({adversaire_name}) est K.O. !"))

                        if not state.switch_bot():
                            embed = build_turn_embed(state, tour, fields,  adversaire_name)
                            await interaction.channel.send(embed=embed)
                            await interaction.channel.send(f"🧑‍🎤 **{adversaire_name}** : {repliques['lose']}")
                            await interaction.channel.send("🎉 **Victoire du joueur !**")
                            return
                        else:
                            fields.append((
                                f"{state.active_bot['name']} ({adversaire_name}) entre en scène !",

                                f"{state.active_bot['name']} ({adversaire_name}) se tient prêt."
                            ))
                else:
                    if state.switch_player_to(choice["index"]):
                        fields.append((
                            "🔄 Changement !",
                            f"{state.active_player['name']} (👤 Joueur) entre en scène !"
                        ))
                    else:
                        fields.append(("❌ Échec du changement", "Choix invalide."))

        embed = build_turn_embed(state, tour, fields,  adversaire_name)
        await interaction.channel.send(embed=embed)
        tour += 1
        await asyncio.sleep(2)
