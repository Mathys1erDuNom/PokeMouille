import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import random
import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
json_dir = os.path.join(script_dir, "json")

answered_users = set()
quiz_winner = None


def load_questions(file_name):
    file_path = os.path.join(json_dir, file_name)
    if not os.path.exists(file_path):
        print(f"[ERREUR] Fichier questions introuvable : {file_path}")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def setup_quiz_commands(bot, spawn_pokemon, role_id, is_under_ban_func, questions_file="questions.json", authorized_user_id=None):
    questions = load_questions(questions_file)
    if not questions:
        print("[ERREUR] Aucune question chargée, le quiz ne fonctionnera pas.")

    class QuizButton(Button):
        def __init__(self, label, correct_answer):
            super().__init__(label=label, style=discord.ButtonStyle.secondary)
            self.correct_answer = correct_answer

        async def callback(self, interaction: discord.Interaction):
            global answered_users, quiz_winner

            guild_id = interaction.guild.id
            user_id = interaction.user.id

            if is_under_ban_func(guild_id, user_id):
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
                        f"✅ Bonne réponse {interaction.user.mention} ! Un Pokémon va apparaître pour toi.")
                    await spawn_pokemon(interaction.channel, force=True, author=interaction.user, target_user=interaction.user)
                else:
                    await interaction.response.send_message("Quelqu'un a déjà donné la bonne réponse !", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Mauvaise réponse !", ephemeral=True)

    class QuizView(View):
        def __init__(self, question_data):
            super().__init__(timeout=10)
            self.message = None
            for option in question_data["options"]:
                self.add_item(QuizButton(label=option, correct_answer=question_data["answer"]))

        async def on_timeout(self):
            for child in self.children:
                child.disabled = True
            if self.message:
                try:
                    await self.message.edit(view=self)
                except Exception as e:
                    print(f"[ERREUR] Impossible d'éditer le message après timeout : {e}")

    # ─── Fonction standalone appelable sans contexte ───────────────────────────
    async def run_quiz(channel):
        """Lance un quiz directement dans un salon Discord donné."""
        global answered_users, quiz_winner
        answered_users = set()
        quiz_winner = None

        if not questions:
            await channel.send("❌ Le quiz ne peut pas démarrer car aucune question n'a été chargée.")
            return

        await channel.send(f"<@&{role_id}>")

        q = random.choice(questions)
        await channel.send(f"🧠 **Question** : {q['question']}\n⏳ Réponses dans 5 secondes...")
        await asyncio.sleep(5)

        view = QuizView(q)
        view.message = await channel.send("🧐 Choisis ta réponse :", view=view)

    # ─── Commande manuelle (usage admin) ───────────────────────────────────────
    @bot.command()
    async def quiz(ctx):
        if authorized_user_id is not None and ctx.author.id != authorized_user_id:
            await ctx.send("⛔ Tu n'as pas la permission d'utiliser cette commande.")
            return
        await run_quiz(ctx.channel)

    # Expose run_quiz pour pouvoir l'importer / l'appeler depuis le main
    bot.run_quiz = run_quiz