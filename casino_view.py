# casino_view.py
import discord
from discord.ui import View, Button
from card_game import CardColorGame
from slot_machine import SlotMachine
from money_db import get_balance

class CasinoView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(CardGameButton())
        self.add_item(SlotMachineButton())
        
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class CardGameButton(Button):
    def __init__(self):
        super().__init__(
            label="🎴 Deviner la couleur",
            style=discord.ButtonStyle.primary,
            emoji="🎲"
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Vérifie le solde du joueur
        balance = get_balance(interaction.user.id)
        
        # Lance le jeu de cartes
        game_view = CardColorGame(user_id=interaction.user.id)
        embed = discord.Embed(
            title="🎴 Jeu de Couleur de Carte",
            description="**Devinez la couleur de 4 cartes d'affilée !**\n\n"
                       "🔴 Rouge (Cœur ♥️ / Carreau ♦️)\n"
                       "⚫ Noir (Pique ♠️ / Trèfle ♣️)\n\n"
                       "⚠️ **Règles :**\n"
                       "• Devinez correctement 4 fois de suite pour gagner\n"
                       "• Atteignez 3 bonnes réponses → Mise remboursée\n"
                       "• Moins de 3 → Vous perdez votre mise\n\n"
                       "**Mise :** 10 💰🐊\n"
                       "**Gain :** 100 💰🐊 (si 4/4) | Remboursement (si 3/4)\n\n"
                       f"**Votre solde :** {balance} 💰🐊",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Choisissez une couleur pour commencer ! 🍀")
        
        await interaction.response.send_message(
            embed=embed,
            view=game_view,
            ephemeral=True
        )


class SlotMachineButton(Button):
    def __init__(self):
        super().__init__(
            label="🎰 Machine à sous",
            style=discord.ButtonStyle.success,
            emoji="🎲"
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Vérifie le solde du joueur
        balance = get_balance(interaction.user.id)
        
        # Lance la machine à sous
        slot_view = SlotMachine(user_id=interaction.user.id)
        embed = discord.Embed(
            title="🎰 Machine à Sous",
            description="**Alignez les symboles pour gagner !**\n\n"
                       "**Gains :**\n"
                       "💎💎💎 → 10 000 💰🐊\n"
                       "⭐⭐⭐ → 7000 💰🐊 \n"
                       "🍊🍊🍊 → 500 💰🐊\n"
                       "🍋🍋🍋 → 200 💰🐊\n"
                       "🍒🍒🍒 → 100 💰🐊\n"
                       "☠️ → PERDU\n\n"
                       f"**Mise :** 10 💰🐊\n"
                       f"**Votre solde :** {balance} 💰🐊",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Cliquez sur SPIN pour lancer ! 🎰")
        
        await interaction.response.send_message(
            embed=embed,
            view=slot_view,
            ephemeral=True
        )


def setup_casino(bot):
    @bot.command(name="casino")
    async def casino(ctx):
        """Ouvre le menu du casino avec tous les jeux disponibles."""
        balance = get_balance(ctx.author.id)
        
        embed = discord.Embed(
            title="🎰 Bienvenue au Casino ! 🎰",
            description="Choisissez un jeu pour tenter votre chance !\n\n"
                       "🎴 **Deviner la couleur** - Devinez 4 couleurs d'affilée\n"
                       "   Mise : 10 💰🐊 | Gain : 100 💰🐊 | Remboursement si 3/4\n\n"
                       "🎰 **Machine à sous** - Alignez 3 symboles identiques\n"
                       "   Mise : 10 💰🐊 | Gains : 100-10 000 💰🐊\n"
                       f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                       f"💰🐊 **Votre solde :** {balance:,} Croco dollars",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Bonne chance ! 🍀🍀")
        
        view = CasinoView()
        await ctx.send(embed=embed, view=view)