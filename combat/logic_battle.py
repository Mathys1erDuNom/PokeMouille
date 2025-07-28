import discord
import random
import asyncio

async def start_battle_turn_based(interaction, player_team, bot_team):
    player_pokemon = dict(player_team[0])  # Premier Pokémon du joueur
    bot_pokemon = dict(bot_team[0])        # Premier Pokémon du bot
    tour = 1

    player_current_hp = player_pokemon["stats"]["hp"]
    bot_current_hp = bot_pokemon["stats"]["hp"]

    await interaction.channel.send(f"⚔️ Début du combat entre **{player_pokemon['name']}** et **{bot_pokemon['name']}** !")

    while player_current_hp > 0 and bot_current_hp > 0:
        await asyncio.sleep(1)
        embed = discord.Embed(title=f"🔁 Tour {tour}", color=0x00BFFF)

        # Qui attaque en premier ?
        if player_pokemon["stats"]["speed"] >= bot_pokemon["stats"]["speed"]:
            order = [("Joueur", player_pokemon, bot_pokemon), ("Bot", bot_pokemon, player_pokemon)]
        else:
            order = [("Bot", bot_pokemon, player_pokemon), ("Joueur", player_pokemon, bot_pokemon)]

        for camp, attacker, defender in order:
            if attacker["name"] == player_pokemon["name"]:
                attacker_hp = player_current_hp
                defender_hp = bot_current_hp
            else:
                attacker_hp = bot_current_hp
                defender_hp = player_current_hp

            if attacker_hp <= 0:
                continue  # KO

            # Choix d'une attaque
            attack_name = random.choice(attacker["attacks"])
            attack_damage = 10 + random.randint(0, 5)  # 💡 à personnaliser selon attaque plus tard
            defender_hp -= attack_damage

            embed.add_field(
                name=f"{camp} - {attacker['name']} utilise {attack_name} !",
                value=f"{defender['name']} perd {attack_damage} PV.",
                inline=False
            )

            # Mise à jour des PV
            if defender["name"] == bot_pokemon["name"]:
                bot_current_hp = max(defender_hp, 0)
            else:
                player_current_hp = max(defender_hp, 0)

            if defender_hp <= 0:
                embed.add_field(name="💥 K.O.", value=f"{defender['name']} est K.O. !", inline=False)
                break

        embed.set_footer(text=f"PV {player_pokemon['name']} : {player_current_hp} | PV {bot_pokemon['name']} : {bot_current_hp}")
        await interaction.channel.send(embed=embed)
        tour += 1
        await asyncio.sleep(2)

    # Fin du combat
    if player_current_hp > 0:
        await interaction.channel.send("🎉 **Victoire du joueur !**")
    else:
        await interaction.channel.send("🤖 **Le bot a gagné le combat !**")
