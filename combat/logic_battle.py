# logic_battle.py

import discord
import asyncio
import random
import os

from combat.battle_state import BattleState
from combat.views_attack import AttackOrSwitchView, SwitchSelectView
from combat.utils import calculate_damage  # doit supporter return_details=True


def build_turn_embed(state, tour, fields, bg_image: str | None = None, use_attachment: bool = False):
    emb = discord.Embed(title=f"🔁 Tour {tour}", color=0x00BFFF)
    for name, value in fields:
        emb.add_field(name=name, value=value, inline=False)

    # — Option fond via embed image —
    if bg_image:
        if use_attachment:
            # On suppose que bg_image est un chemin local déjà attaché comme "attachment://bg.png"
            emb.set_image(url="attachment://bg.png")
        else:
            # URL distante (CDN/Imgur/etc.)
            emb.set_image(url=bg_image)

    # Vignettes Pokémon (on met la miniature côté joueur pour ne pas écraser l'image de fond)
    if state.active_player.get("image"):
        emb.set_thumbnail(url=state.active_player["image"])

    hp_p = state.get_hp("player")
    hp_b = state.get_hp("bot")
    emb.set_footer(
        text=f"PV {state.active_player['name']} (👤 Joueur): {hp_p} | "
             f"PV {state.active_bot['name']} (🤖 Bot): {hp_b}"
    )
    return emb


def format_damage_desc(target_name_with_owner: str, dmg: int, eff_label: str, eff_mult: float, crit: bool) -> str:
    if eff_mult == 0:
        desc_loss = f"{target_name_with_owner} ne subit **aucun dégât**."
    else:
        desc_loss = f"{target_name_with_owner} perd {dmg} PV."
    suffix_parts = []
    if crit:
        suffix_parts.append("🎯 **Coup critique !**")
    if eff_label != "efficacité normale":
        suffix_parts.append(f"({eff_label})")
    return desc_loss + ((" " + " ".join(suffix_parts)) if suffix_parts else "")


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

    atk = random.choice(state.active_player["attacks"])
    await interaction.channel.send(f"⏱ Aucun choix effectué. **{atk}** est utilisé par défaut.")
    return {"action": "attack", "attack": atk}


async def start_battle_turn_based(interaction, player_team, bot_team, bg_image: str | None = None):
    """
    bg_image:
      - URL (ex: 'https://.../fond.png') -> affichée directement
      - chemin local (ex: 'assets/fonds/arena.png') -> sera envoyé comme pièce jointe (attachment://bg.png)
      - None -> pas de fond
    """
    state = BattleState(player_team, bot_team)
    tour = 1

    # Détection: si bg_image est un fichier local, on utilisera un attachment
    use_attachment = bool(bg_image and os.path.isfile(bg_image))

    # Message d’ouverture (on profite déjà du fond)
    open_embed = build_turn_embed(
        state, tour=0,
        fields=[("⚔️ Début du combat", f"**{state.active_player['name']} (👤 Joueur)** vs **{state.active_bot['name']} (🤖 Bot)**")],
        bg_image=bg_image,
        use_attachment=use_attachment
    )
    if use_attachment:
        await interaction.channel.send(embed=open_embed, file=discord.File(bg_image, filename="bg.png"))
    else:
        await interaction.channel.send(embed=open_embed)

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
                    res = calculate_damage(state.active_player, state.active_bot, attack_name, return_details=True)
                    dmg = res["damage"]
                    state.take_damage("bot", dmg)
                    fields.append((
                        f"{state.active_player['name']} (👤 Joueur) utilise {attack_name} !",
                        format_damage_desc(f"{state.active_bot['name']} (🤖 Bot)", dmg, res["eff_label"], res["eff_multiplier"], res["crit"])
                    ))
                    if state.is_bot_ko():
                        fields.append(("💥 K.O.", f"{state.active_bot['name']} (🤖 Bot) est K.O. !"))
                        if not state.switch_bot():
                            embed = build_turn_embed(state, tour, fields, bg_image, use_attachment)
                            if use_attachment:
                                await interaction.channel.send(embed=embed, file=discord.File(bg_image, filename="bg.png"))
                            else:
                                await interaction.channel.send(embed=embed)
                            await interaction.channel.send("🎉 **Victoire du joueur !**")
                            return
                        else:
                            fields.append((f"{state.active_bot['name']} (🤖 Bot) entre en scène !", f"{state.active_bot['name']} (🤖 Bot) se tient prêt."))
                        end_turn = True
                else:
                    if state.switch_player_to(choice["index"]):
                        fields.append(("🔄 Changement !", f"{state.active_player['name']} (👤 Joueur) entre en scène !"))
                    else:
                        fields.append(("❌ Échec du changement", "Choix invalide."))
        else:
            if not state.is_bot_ko():
                attack_name = random.choice(state.active_bot["attacks"])
                res = calculate_damage(state.active_bot, state.active_player, attack_name, return_details=True)
                dmg = res["damage"]
                state.take_damage("player", dmg)
                fields.append((
                    f"{state.active_bot['name']} (🤖 Bot) utilise {attack_name} !",
                    format_damage_desc(f"{state.active_player['name']} (👤 Joueur)", dmg, res["eff_label"], res["eff_multiplier"], res["crit"])
                ))
                if state.is_player_ko():
                    fields.append(("💥 K.O.", f"{state.active_player['name']} (👤 Joueur) est K.O. !"))
                    if not state.switch_player():
                        embed = build_turn_embed(state, tour, fields, bg_image, use_attachment)
                        if use_attachment:
                            await interaction.channel.send(embed=embed, file=discord.File(bg_image, filename="bg.png"))
                        else:
                            await interaction.channel.send(embed=embed)
                        await interaction.channel.send("🤖 **Le bot a gagné le combat !**")
                        return
                    else:
                        fields.append((f"{state.active_player['name']} (👤 Joueur) entre en scène !", f"{state.active_player['name']} (👤 Joueur) se tient prêt."))
                    end_turn = True

        # Fin anticipée du tour après K.O.
        if end_turn:
            embed = build_turn_embed(state, tour, fields, bg_image, use_attachment)
            if use_attachment:
                await interaction.channel.send(embed=embed, file=discord.File(bg_image, filename="bg.png"))
            else:
                await interaction.channel.send(embed=embed)
            await interaction.channel.send("🛎 Fin du tour (K.O. détecté).")
            tour += 1
            await asyncio.sleep(2)
            continue

        # ---- ACTION 2 ----
        if order[1] == "bot":
            if not state.is_bot_ko():
                attack_name = random.choice(state.active_bot["attacks"])
                res = calculate_damage(state.active_bot, state.active_player, attack_name, return_details=True)
                dmg = res["damage"]
                state.take_damage("player", dmg)
                fields.append((
                    f"{state.active_bot['name']} (🤖 Bot) utilise {attack_name} !",
                    format_damage_desc(f"{state.active_player['name']} (👤 Joueur)", dmg, res["eff_label"], res["eff_multiplier"], res["crit"])
                ))
                if state.is_player_ko():
                    fields.append(("💥 K.O.", f"{state.active_player['name']} (👤 Joueur) est K.O. !"))
                    if not state.switch_player():
                        embed = build_turn_embed(state, tour, fields, bg_image, use_attachment)
                        if use_attachment:
                            await interaction.channel.send(embed=embed, file=discord.File(bg_image, filename="bg.png"))
                        else:
                            await interaction.channel.send(embed=embed)
                        await interaction.channel.send("🤖 **Le bot a gagné le combat !**")
                        return
                    else:
                        fields.append((f"{state.active_player['name']} (👤 Joueur) entre en scène !", f"{state.active_player['name']} (👤 Joueur) se tient prêt."))
        else:
            if not state.is_player_ko():
                choice = await prompt_player_action(interaction, state)
                if choice["action"] == "attack":
                    attack_name = choice["attack"]
                    res = calculate_damage(state.active_player, state.active_bot, attack_name, return_details=True)
                    dmg = res["damage"]
                    state.take_damage("bot", dmg)
                    fields.append((
                        f"{state.active_player['name']} (👤 Joueur) utilise {attack_name} !",
                        format_damage_desc(f"{state.active_bot['name']} (🤖 Bot)", dmg, res["eff_label"], res["eff_multiplier"], res["crit"])
                    ))
                    if state.is_bot_ko():
                        fields.append(("💥 K.O.", f"{state.active_bot['name']} (🤖 Bot) est K.O. !"))
                        if not state.switch_bot():
                            embed = build_turn_embed(state, tour, fields, bg_image, use_attachment)
                            if use_attachment:
                                await interaction.channel.send(embed=embed, file=discord.File(bg_image, filename="bg.png"))
                            else:
                                await interaction.channel.send(embed=embed)
                            await interaction.channel.send("🎉 **Victoire du joueur !**")
                            return
                        else:
                            fields.append((f"{state.active_bot['name']} (🤖 Bot) entre en scène !", f"{state.active_bot['name']} (🤖 Bot) se tient prêt."))
                else:
                    if state.switch_player_to(choice["index"]):
                        fields.append(("🔄 Changement !", f"{state.active_player['name']} (👤 Joueur) entre en scène !"))
                    else:
                        fields.append(("❌ Échec du changement", "Choix invalide."))

        embed = build_turn_embed(state, tour, fields, bg_image, use_attachment)
        if use_attachment:
            await interaction.channel.send(embed=embed, file=discord.File(bg_image, filename="bg.png"))
        else:
            await interaction.channel.send(embed=embed)
        tour += 1
        await asyncio.sleep(2)
