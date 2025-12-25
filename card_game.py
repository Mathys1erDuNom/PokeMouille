# card_game.py
import discord
from discord.ui import View, Button
import random
from money_db import get_balance, add_money, remove_money

class CardColorGame(View):
    def __init__(self, user_id, bet_amount=10, win_amount=20):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.win_amount = win_amount
        
        # Cartes avec leurs couleurs
        self.cards = {
            "♥️ As de Cœur": "red", "♥️ 2 de Cœur": "red", "♥️ 3 de Cœur": "red",
            "♥️ 4 de Cœur": "red", "♥️ 5 de Cœur": "red", "♥️ 6 de Cœur": "red",
            "♥️ 7 de Cœur": "red", "♥️ 8 de Cœur": "red", "♥️ 9 de Cœur": "red",
            "♥️ 10 de Cœur": "red", "♥️ Valet de Cœur": "red", "♥️ Dame de Cœur": "red",
            "♥️ Roi de Cœur": "red",
            
            "♦️ As de Carreau": "red", "♦️ 2 de Carreau": "red", "♦️ 3 de Carreau": "red",
            "♦️ 4 de Carreau": "red", "♦️ 5 de Carreau": "red", "♦️ 6 de Carreau": "red",
            "♦️ 7 de Carreau": "red", "♦️ 8 de Carreau": "red", "♦️ 9 de Carreau": "red",
            "♦️ 10 de Carreau": "red", "♦️ Valet de Carreau": "red", "♦️ Dame de Carreau": "red",
            "♦️ Roi de Carreau": "red",
            
            "♠️ As de Pique": "black", "♠️ 2 de Pique": "black", "♠️ 3 de Pique": "black",
            "♠️ 4 de Pique": "black", "♠️ 5 de Pique": "black", "♠️ 6 de Pique": "black",
            "♠️ 7 de Pique": "black", "♠️ 8 de Pique": "black", "♠️ 9 de Pique": "black",
            "♠️ 10 de Pique": "black", "♠️ Valet de Pique": "black", "♠️ Dame de Pique": "black",
            "♠️ Roi de Pique": "black",
            
            "♣️ As de Trèfle": "black", "♣️ 2 de Trèfle": "black", "♣️ 3 de Trèfle": "black",
            "♣️ 4 de Trèfle": "black", "♣️ 5 de Trèfle": "black", "♣️ 6 de Trèfle": "black",
            "♣️ 7 de Trèfle": "black", "♣️ 8 de Trèfle": "black", "♣️ 9 de Trèfle": "black",
            "♣️ 10 de Trèfle": "black", "♣️ Valet de Trèfle": "black", "♣️ Dame de Trèfle": "black",
            "♣️ Roi de Trèfle": "black",
        }
        
        self.add_item(RedButton(self))
        self.add_item(BlackButton(self))
    
    async def play_game(self, interaction: discord.Interaction, player_choice: str):
        """Joue une partie du jeu de devinette de couleur."""
        
        # Vérifie que le joueur a assez d'argent
        current_balance = get_balance(self.user_id)
        
        if current_balance < self.bet_amount:
            embed = discord.Embed(
                title="❌ Solde insuffisant",
                description=f"Vous avez besoin de **{self.bet_amount} 💰** pour jouer.\n"
                           f"Votre solde actuel : **{current_balance} 💰**",
                color=discord.Color.red()
            )
            
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        # Retire la mise
        remove_money(self.user_id, self.bet_amount)
        
        # Tire une carte au hasard
        card_name = random.choice(list(self.cards.keys()))
        card_color = self.cards[card_name]
        
        # Détermine si le joueur a gagné
        won = (player_choice == card_color)
        
        # Crée l'embed de résultat
        if won:
            add_money(self.user_id, self.win_amount)
            new_balance = get_balance(self.user_id)
            
            embed = discord.Embed(
                title="🎉 Victoire !",
                description=f"**Carte tirée :** {card_name}\n\n"
                           f"Vous aviez choisi : **{'🔴 Rouge' if player_choice == 'red' else '⚫ Noir'}**\n"
                           f"✅ Bonne réponse !\n\n"
                           f"**Gain :** +{self.win_amount} 💰\n"
                           f"**Nouveau solde :** {new_balance} 💰",
                color=discord.Color.green()
            )
        else:
            new_balance = get_balance(self.user_id)
            
            embed = discord.Embed(
                title="😢 Perdu !",
                description=f"**Carte tirée :** {card_name}\n\n"
                           f"Vous aviez choisi : **{'🔴 Rouge' if player_choice == 'red' else '⚫ Noir'}**\n"
                           f"❌ Mauvaise réponse !\n\n"
                           f"**Perte :** -{self.bet_amount} 💰\n"
                           f"**Nouveau solde :** {new_balance} 💰",
                color=discord.Color.red()
            )
        
        # Désactive les boutons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class RedButton(Button):
    def __init__(self, game_view):
        super().__init__(
            label="Rouge",
            style=discord.ButtonStyle.danger,
            emoji="🔴"
        )
        self.game_view = game_view
    
    async def callback(self, interaction: discord.Interaction):
        await self.game_view.play_game(interaction, "red")


class BlackButton(Button):
    def __init__(self, game_view):
        super().__init__(
            label="Noir",
            style=discord.ButtonStyle.secondary,
            emoji="⚫"
        )
        self.game_view = game_view
    
    async def callback(self, interaction: discord.Interaction):
        await self.game_view.play_game(interaction, "black")