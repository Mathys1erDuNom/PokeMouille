# casino_view.py
import discord
from discord.ui import View, Button
from card_game import CardColorGame
from money_db import get_balance

class CasinoView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(CardGameButton())
        
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
            description="**Devinez la couleur de la prochaine carte !**\n\n"
                       "🔴 Rouge (Cœur ♥️ / Carreau ♦️)\n"
                       "⚫ Noir (Pique ♠️ / Trèfle ♣️)\n\n"
                       "**Mise :** 10 💰\n"
                       "**Gain :** 20 💰\n\n"
                       f"**Votre solde :** {balance} 💰",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Choisissez une couleur pour commencer !")
        
        await interaction.response.send_message(
            embed=embed,
            view=game_view,
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
                       "🎴 **Deviner la couleur** - Devinez si la carte sera rouge ou noire\n"
                       f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                       f"💰 **Votre solde :** {balance:,} Croco dollars",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Bonne chance ! 🍀")
        
        view = CasinoView()
        await ctx.send(embed=embed, view=view)