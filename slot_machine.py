# slot_machine.py
import discord
from discord.ui import View, Button
import random
from money_db import get_balance, add_money, remove_money

class SlotMachine(View):
    def __init__(self, user_id, bet_amount=50):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bet_amount = bet_amount
        
        # Symboles avec leurs poids (total = 100 pour des pourcentages directs)
        self.symbols = {
            "🍒": {"weight": 35, "name": "Cerise"},      # 35%
            "🍋": {"weight": 30, "name": "Citron"},      # 30%
            "🍊": {"weight": 20, "name": "Orange"},      # 20%
            "⭐": {"weight": 5, "name": "Étoile"},      # 5%
            "💎": {"weight": 1, "name": "Diamant"}       # 1%
        }
        
        # Gains selon le nombre de symboles identiques
        self.payouts = {
            "🍒": {"3": 100},
            "🍋": {"3": 200},
            "🍊": {"3": 500},
            "⭐": {"2": 1000, "3": 7000},
            "💎": {"2": 5000, "3": 10000}
        }
        
        self.add_item(SpinButton(self))
    
    def spin_reels(self):
        """Fait tourner les 3 rouleaux et retourne les symboles."""
        symbols_list = []
        weights_list = []
        
        for symbol, data in self.symbols.items():
            symbols_list.append(symbol)
            weights_list.append(data["weight"])
        
        # Tire 3 symboles aléatoires avec pondération
        results = random.choices(symbols_list, weights=weights_list, k=3)
        return results
    
    def calculate_win(self, results):
        """Calcule les gains en fonction des résultats."""
        # Compte les symboles identiques
        symbol_counts = {}
        for symbol in results:
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        # Trouve le symbole avec le plus d'occurrences
        max_count = max(symbol_counts.values())
        winning_symbol = None
        
        for symbol, count in symbol_counts.items():
            if count == max_count:
                winning_symbol = symbol
                break
        
        # Calcule le gain
        if max_count >= 2:
            payout = self.payouts[winning_symbol].get(str(max_count), 0)
            return payout, max_count, winning_symbol
        
        return 0, 0, None
    
    async def play(self, interaction: discord.Interaction):
        """Lance la machine à sous."""
        # Vérifie le solde
        current_balance = get_balance(self.user_id)
        
        if current_balance < self.bet_amount:
            embed = discord.Embed(
                title="❌ Solde insuffisant",
                description=f"Vous avez besoin de **{self.bet_amount} 💰🐊** pour jouer.\n"
                           f"Votre solde actuel : **{current_balance} 💰🐊**",
                color=discord.Color.red()
            )
            
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        # Retire la mise
        remove_money(self.user_id, self.bet_amount)
        
        # Fait tourner les rouleaux
        results = self.spin_reels()
        
        # Calcule les gains
        win_amount, matching_count, winning_symbol = self.calculate_win(results)
        
        # Crée l'affichage des rouleaux
        reel_display = f"┃ {results[0]} ┃ {results[1]} ┃ {results[2]} ┃"
        
        # Détermine le résultat
        if win_amount > 0:
            add_money(self.user_id, win_amount)
            new_balance = get_balance(self.user_id)
            net_gain = win_amount - self.bet_amount
            
            # Message selon le gain
            if winning_symbol == "💎" and matching_count == 3:
                title = "💎💎 JACKPOT DIAMANT ! 💎💎"
                color = discord.Color.purple()
            elif matching_count == 3:
                title = "🎉 TROIS IDENTIQUES ! 🎉"
                color = discord.Color.gold()
            else:
                title = "✅ Vous avez gagné !"
                color = discord.Color.green()
            
            description = f"**╔═══════════╗**\n" \
                         f"**{reel_display}**\n" \
                         f"**╚═══════════╝**\n\n" \
                         f"{'🎊 ' if matching_count == 3 else ''}**{matching_count} {winning_symbol} {self.symbols[winning_symbol]['name']}** !\n\n" \
                         f"**Gain :** +{win_amount} 💰🐊\n" \
                         f"**Profit net :** {'+' if net_gain >= 0 else ''}{net_gain} 💰🐊\n" \
                         f"**Nouveau solde :** {new_balance} 💰🐊"
            
            embed = discord.Embed(title=title, description=description, color=color)
        else:
            new_balance = get_balance(self.user_id)
            
            embed = discord.Embed(
                title="😢 Perdu !",
                description=f"**╔═══════════╗**\n"
                           f"**{reel_display}**\n"
                           f"**╚═══════════╝**\n\n"
                           f"Aucune combinaison gagnante...\n\n"
                           f"**Perte :** -{self.bet_amount} 💰🐊\n"
                           f"**Nouveau solde :** {new_balance} 💰🐊",
                color=discord.Color.red()
            )
        
        # Désactive le bouton
        for item in self.children:
            item.disabled = True
        
        # Ajoute un bouton pour rejouer
        self.add_item(PlayAgainButton(self.user_id, self.bet_amount))
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class SpinButton(Button):
    def __init__(self, slot_machine):
        super().__init__(
            label="🎰 SPIN !",
            style=discord.ButtonStyle.success,
            emoji="🎲"
        )
        self.slot_machine = slot_machine
    
    async def callback(self, interaction: discord.Interaction):
        await self.slot_machine.play(interaction)


class PlayAgainButton(Button):
    def __init__(self, user_id, bet_amount):
        super().__init__(
            label="🔄 Rejouer",
            style=discord.ButtonStyle.primary
        )
        self.user_id = user_id
        self.bet_amount = bet_amount
    
    async def callback(self, interaction: discord.Interaction):
        # Crée une nouvelle machine à sous
        new_slot = SlotMachine(self.user_id, self.bet_amount)
        
        balance = get_balance(self.user_id)
        
        embed = discord.Embed(
            title="🎰 Machine à Sous",
            description="**Alignez les symboles pour gagner !**\n\n"
                       "**Gains :**\n"
                       "💎💎💎 → 10 000 💰🐊 | 💎💎 → 5000 💰🐊\n"
                       "⭐⭐⭐ → 7000 💰🐊 | ⭐⭐ → 1000 💰🐊\n"
                       "🍊🍊🍊 → 500 💰🐊\n"
                       "🍋🍋🍋 → 200 💰🐊\n"
                       "🍒🍒🍒 → 100 💰🐊\n\n"
                       f"**Mise :** 50 💰🐊\n"
                       f"**Votre solde :** {balance} 💰🐊",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Cliquez sur SPIN pour lancer ! 🎰")
        
        await interaction.response.edit_message(embed=embed, view=new_slot)