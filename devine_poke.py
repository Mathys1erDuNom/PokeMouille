import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import random
import json
import os
import aiohttp
import io

script_dir = os.path.dirname(os.path.abspath(__file__))
json_dir = os.path.join(script_dir, "json")

answered_users = set()
quiz_winner = None


def load_pokemon_data():
    normal_files = [
        "pokemon_gen1_normal.json",
        "pokemon_gen2_normal.json",
        "pokemon_gen3_normal.json",
        "pokemon_gen4_normal.json",
    ]
    all_pokemon = []
    for fname in normal_files:
        file_path = os.path.join(json_dir, fname)
        if not os.path.exists(file_path):
            print(f"[AVERTISSEMENT] Fichier introuvable : {file_path}")
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_pokemon.extend(data)
    return all_pokemon


def load_shiny_data():
    file_path = os.path.join(json_dir, "pokemon_shiny_data.json")
    if not os.path.exists(file_path):
        print(f"[ERREUR] Fichier shiny introuvable : {file_path}")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def setup_guess_pokemon_command(bot, spawn_pokemon=None, role_id=None, authorized_user_id=None, is_under_ban_func=None):
    base_data = load_pokemon_data()
    all_pokemon = base_data

    class GuessButton(Button):
        def __init__(self, label, correct_answer):
            super().__init__(label=label, style=discord.ButtonStyle.primary)
            self.correct_answer = correct_answer

        async def callback(self, interaction: discord.Interaction):
            global answered_users, quiz_winner

            guild_id = interaction.guild.id
            user_id = interaction.user.id

            if is_under_ban_func and is_under_ban_func(guild_id, user_id):
                await interaction.response.send_message("⏳ Tu es sous ban. Attends encore un peu avant de répondre.", ephemeral=True)
                return

            if user_id in answered_users:
                await interaction.response.send_message("Tu as déjà répondu !", ephemeral=True)
                return

            answered_users.add(user_id)

            if self.label == self.correct_answer:
                if quiz_winner is None:
                    quiz_winner = user_id
                    await interaction.response.send_message(
                        f"✅ Bonne réponse {interaction.user.mention} ! C'était **{self.correct_answer}**.")
                    if spawn_pokemon:
                        await spawn_pokemon(interaction.channel, force=True, author=interaction.user, target_user=interaction.user)
                else:
                    await interaction.response.send_message("Quelqu'un a déjà deviné correctement !", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Mauvaise réponse !", ephemeral=True)

    class GuessView(View):
        def __init__(self, correct_name, options):
            super().__init__(timeout=10)
            self.message = None
            for opt in options:
                self.add_item(GuessButton(label=opt, correct_answer=correct_name))

        async def on_timeout(self):
            for child in self.children:
                child.disabled = True
            if self.message:
                try:
                    await self.message.edit(view=self)
                except Exception as e:
                    print(f"[ERREUR] Impossible d'éditer le message après timeout : {e}")

    # ─── Fonction standalone appelable sans contexte ───────────────────────────
    async def run_devine(channel):
        """Lance un devine-pokémon directement dans un salon Discord donné."""
        global answered_users, quiz_winner
        answered_users = set()
        quiz_winner = None

        if not all_pokemon or len(all_pokemon) < 4:
            await channel.send("Pas assez de Pokémon pour générer un quiz.")
            return

        chosen = random.choice(all_pokemon)
        correct_name = chosen["name"]
        image_url = chosen["image"]

        if correct_name.endswith("_shiny"):
            correct_name = correct_name.replace("_shiny", "")

        other_options = random.sample(
            [p["name"].replace("_shiny", "") for p in all_pokemon if p["name"].replace("_shiny", "") != correct_name],
            3
        )

        options = other_options + [correct_name]
        random.shuffle(options)

        if role_id:
            await channel.send(f"<@&{role_id}>")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        await channel.send("❌ Impossible de charger l'image du Pokémon.")
                        return
                    data = await resp.read()
                    file = discord.File(fp=io.BytesIO(data), filename="pokemon.png")
                    await channel.send(file=file)
        except Exception as e:
            await channel.send("❌ Erreur lors de la récupération de l'image.")
            print(f"[ERREUR IMAGE] : {e}")
            return

        await channel.send("🔍 Devine quel est ce Pokémon ! Réponses dans 5 secondes...")
        await asyncio.sleep(5)

        view = GuessView(correct_name, options)
        view.message = await channel.send("🧐 Qui est-ce Pokémon ?", view=view)

    # ─── Commande manuelle (usage admin) ───────────────────────────────────────
    @bot.command()
    async def devine(ctx):
        if authorized_user_id is not None and ctx.author.id != authorized_user_id:
            await ctx.send("⛔ Tu n'as pas la permission d'utiliser cette commande.")
            return
        await run_devine(ctx.channel)

    # Expose run_devine pour pouvoir l'appeler depuis le main
    bot.run_devine = run_devine