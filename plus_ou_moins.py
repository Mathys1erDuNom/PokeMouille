# dice_game.py
import discord
from discord.ui import View, Button
import random
from money_db import get_balance, add_money, remove_money

# Mise et gains
BET_AMOUNT = 10
EXACT_MULTIPLIER = 10   # x10 pour total exact → gain 100💰
HIGHLOW_MULTIPLIER = 2  # x2 pour haut/bas → gain 20 💰

# Représentation visuelle des dés
DICE_FACES = {
    1: "⚀", 2: "⚁", 3: "⚂",
    4: "⚃", 5: "⚄", 6: "⚅"
}


class DiceGame(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.phase = "choose_mode"  # "choose_mode" → "choose_bet" → "done"

        # Boutons de sélection du mode
        self.add_item(ExactButton(self))
        self.add_item(HighLowButton(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    # ------------------------------------------------------------------ #
    #  PHASE 1 – L'utilisateur choisit le mode de jeu                     #
    # ------------------------------------------------------------------ #
    async def show_exact_choice(self, interaction: discord.Interaction):
        """Affiche les boutons pour choisir un total exact (2-12)."""
        self.clear_items()
        # Ligne 1 : 2 → 7
        for total in range(2, 8):
            self.add_item(ExactTotalButton(self, total))
        # Ligne 2 : 8 → 12
        for total in range(8, 13):
            self.add_item(ExactTotalButton(self, total))

        embed = discord.Embed(
            title="🎲 Jeu de Dés — Total exact",
            description="**Choisissez le total des deux dés (2 à 12)**\n\n"
                        f"Mise : **{BET_AMOUNT} 💰🐊**\n"
                        f"Gain si correct : **{BET_AMOUNT * EXACT_MULTIPLIER} 💰🐊** (x{EXACT_MULTIPLIER})\n\n"
                        "_Plus le total est rare, plus c'est risqué !_",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Sélectionnez votre total...")
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_highlow_choice(self, interaction: discord.Interaction):
        """Affiche les boutons Haut / Bas / Égal."""
        self.clear_items()
        self.add_item(HighButton(self))
        self.add_item(LowButton(self))
        self.add_item(EqualButton(self))

        embed = discord.Embed(
            title="🎲 Jeu de Dés — Haut / Bas",
            description="**Le total des deux dés sera-t-il :**\n\n"
                        "📈 **Haut** → Total **8 à 12**\n"
                        "📉 **Bas** → Total **2 à 6**\n"
                        "⚖️ **Égal** → Total **exactement 7**\n\n"
                        f"Mise : **{BET_AMOUNT} 💰🐊**\n"
                        f"Gain si correct : **{BET_AMOUNT * HIGHLOW_MULTIPLIER} 💰🐊** (x{HIGHLOW_MULTIPLIER})\n"
                        f"_(Égal rapporte x{EXACT_MULTIPLIER} car plus rare !)_",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Sélectionnez Haut, Bas ou Égal...")
        await interaction.response.edit_message(embed=embed, view=self)

    # ------------------------------------------------------------------ #
    #  PHASE 2 – Résolution du pari                                       #
    # ------------------------------------------------------------------ #
    async def resolve_bet(self, interaction: discord.Interaction, bet_type: str, bet_value):
        """Vérifie le solde, retire la mise, lance les dés, calcule le résultat."""

        # Vérification du solde
        balance = get_balance(self.user_id)
        if balance < BET_AMOUNT:
            embed = discord.Embed(
                title="❌ Solde insuffisant",
                description=f"Vous avez besoin de **{BET_AMOUNT} 💰🐊** pour jouer.\n"
                            f"Votre solde actuel : **{balance} 💰🐊**",
                color=discord.Color.red()
            )
            self.clear_items()
            await interaction.response.edit_message(embed=embed, view=self)
            return

        # Retire la mise
        remove_money(self.user_id, BET_AMOUNT)

        # Lance les dés
        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        total = die1 + die2
        dice_display = f"{DICE_FACES[die1]}  {DICE_FACES[die2]}"

        # Détermine victoire et gain
        won = False
        gain = 0
        result_label = ""

        if bet_type == "exact":
            won = (total == bet_value)
            gain = BET_AMOUNT * EXACT_MULTIPLIER
            result_label = f"Total exact **{bet_value}**"

        elif bet_type == "high":
            won = (total >= 8)
            gain = BET_AMOUNT * HIGHLOW_MULTIPLIER
            result_label = "**Haut** (8-12)"

        elif bet_type == "low":
            won = (total <= 6)
            gain = BET_AMOUNT * HIGHLOW_MULTIPLIER
            result_label = "**Bas** (2-6)"

        elif bet_type == "equal":
            won = (total == 7)
            gain = BET_AMOUNT * EXACT_MULTIPLIER  # bonus car rare
            result_label = "**Égal** (7)"

        # Mise à jour du solde
        if won:
            add_money(self.user_id, gain)

        new_balance = get_balance(self.user_id)

        # Construction de l'embed résultat
        if won:
            embed = discord.Embed(
                title="🎉 Vous avez gagné !",
                description=f"## {dice_display}\n"
                            f"**Total : {total}**\n\n"
                            f"Votre pari : {result_label}\n"
                            f"✅ **Correct !**\n\n"
                            f"**Gain :** +{gain} 💰🐊\n"
                            f"**Nouveau solde :** {new_balance} 💰🐊",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="💔 Perdu !",
                description=f"## {dice_display}\n"
                            f"**Total : {total}**\n\n"
                            f"Votre pari : {result_label}\n"
                            f"❌ **Raté !**\n\n"
                            f"**Perte :** -{BET_AMOUNT} 💰🐊\n"
                            f"**Nouveau solde :** {new_balance} 💰🐊",
                color=discord.Color.red()
            )

        embed.set_footer(text="Bonne chance ! 🎲")
        self.clear_items()
        self.add_item(ReplayButton(self.user_id))
        await interaction.response.edit_message(embed=embed, view=self)


# ------------------------------------------------------------------ #
#  Boutons — Sélection du mode                                        #
# ------------------------------------------------------------------ #

class ExactButton(Button):
    def __init__(self, game_view: DiceGame):
        super().__init__(
            label="Total exact",
            style=discord.ButtonStyle.primary,
            emoji="🎯"
        )
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        await self.game_view.show_exact_choice(interaction)


class HighLowButton(Button):
    def __init__(self, game_view: DiceGame):
        super().__init__(
            label="Haut / Bas / Égal",
            style=discord.ButtonStyle.secondary,
            emoji="📊"
        )
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        await self.game_view.show_highlow_choice(interaction)


# ------------------------------------------------------------------ #
#  Boutons — Sélection du total exact                                 #
# ------------------------------------------------------------------ #

class ExactTotalButton(Button):
    def __init__(self, game_view: DiceGame, total: int):
        # Indique visuellement les totaux rares
        if total in (2, 12):
            style = discord.ButtonStyle.danger
        elif total in (3, 11):
            style = discord.ButtonStyle.primary
        else:
            style = discord.ButtonStyle.secondary

        super().__init__(
            label=str(total),
            style=style,
            row=0 if total <= 7 else 1
        )
        self.game_view = game_view
        self.total = total

    async def callback(self, interaction: discord.Interaction):
        await self.game_view.resolve_bet(interaction, "exact", self.total)


# ------------------------------------------------------------------ #
#  Boutons — Haut / Bas / Égal                                        #
# ------------------------------------------------------------------ #

class HighButton(Button):
    def __init__(self, game_view: DiceGame):
        super().__init__(
            label="Haut  (8-12)",
            style=discord.ButtonStyle.success,
            emoji="📈"
        )
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        await self.game_view.resolve_bet(interaction, "high", None)


class LowButton(Button):
    def __init__(self, game_view: DiceGame):
        super().__init__(
            label="Bas  (2-6)",
            style=discord.ButtonStyle.danger,
            emoji="📉"
        )
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        await self.game_view.resolve_bet(interaction, "low", None)


class EqualButton(Button):
    def __init__(self, game_view: DiceGame):
        super().__init__(
            label="Égal  (7)",
            style=discord.ButtonStyle.primary,
            emoji="⚖️"
        )
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        await self.game_view.resolve_bet(interaction, "equal", None)


# ------------------------------------------------------------------ #
#  Bouton — Rejouer                                                   #
# ------------------------------------------------------------------ #

class ReplayButton(Button):
    def __init__(self, user_id: int):
        super().__init__(
            label="Rejouer",
            style=discord.ButtonStyle.success,
            emoji="🔄"
        )
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        new_game = DiceGame(user_id=self.user_id)
        balance = get_balance(self.user_id)

        embed = discord.Embed(
            title="🎲 Jeu de Dés",
            description="**Choisissez votre mode de pari :**\n\n"
                        "🎯 **Total exact** → Devinez le total précis (2-12)\n"
                        f"   Gain : **{BET_AMOUNT * EXACT_MULTIPLIER} 💰🐊** (x{EXACT_MULTIPLIER})\n\n"
                        "📊 **Haut / Bas / Égal** → Estimez la zone du total\n"
                        f"   Gain : **{BET_AMOUNT * HIGHLOW_MULTIPLIER} 💰🐊** (x{HIGHLOW_MULTIPLIER})\n\n"
                        f"**Mise :** {BET_AMOUNT} 💰🐊\n"
                        f"**Votre solde :** {balance} 💰🐊",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Bonne chance ! 🍀")
        await interaction.response.edit_message(embed=embed, view=new_game)