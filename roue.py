# roue.py
import discord
from discord.ui import View, Button
import random
from inventory_db import get_items, use_item
from money_db import get_balance, add_money

# Nom de l'objet jeton dans l'inventaire
JETON_NAME = "Jeton"

# Segments de la roue : (label, gain en golds, probabilité)
WHEEL_SEGMENTS = [
    ("50 💰🐊",  50,  0.30),
    ("🎰 Jeton",   0,  0.20),  # gain spécial : 1 jeton
    ("100 💰🐊", 100,  0.20),
    ("150 💰🐊", 150,  0.15),
    ("300 💰🐊", 300,  0.10),
    ("500 💰🐊", 500,  0.05),
]

# Emojis de couleurs pour l'animation de la roue
WHEEL_DISPLAY = [
    "🟥", "🟧", "🟨", "🟩", "🟦", "🟪"
]


def spin_wheel() -> tuple[str, int, bool]:
    """
    Lance la roue et retourne (label, gain_golds, est_jeton).
    Si est_jeton=True, le joueur gagne 1 jeton au lieu de golds.
    """
    labels  = [s[0] for s in WHEEL_SEGMENTS]
    weights = [s[2] for s in WHEEL_SEGMENTS]
    index = random.choices(range(len(WHEEL_SEGMENTS)), weights=weights, k=1)[0]
    label, gain, _ = WHEEL_SEGMENTS[index]
    is_token = (index == 1)
    return label, gain, is_token


def build_wheel_visual(winning_index: int) -> str:
    """Construit une représentation visuelle de la roue avec le résultat mis en évidence."""
    lines = []
    for i, (seg, color) in enumerate(zip(WHEEL_SEGMENTS, WHEEL_DISPLAY)):
        label, _, _ = seg
        if i == winning_index:
            lines.append(f"▶ **{color} {label}** ◀")
        else:
            lines.append(f"　 {color} {label}")
    return "\n".join(lines)


def get_winning_index(label: str) -> int:
    for i, (l, _, _) in enumerate(WHEEL_SEGMENTS):
        if l == label:
            return i
    return 0


class RoueView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(SpinButton(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    async def do_spin(self, interaction: discord.Interaction):
        """Vérifie le jeton, consomme-le et résout la roue."""

        # Vérifie que le joueur a un jeton
        item = get_items(self.user_id, JETON_NAME)
        if item is None or item["quantity"] < 1:
            embed = discord.Embed(
                title="❌ Pas de jeton !",
                description=f"Vous n'avez pas de **{JETON_NAME}** dans votre inventaire.\n\n"
                            f"Obtenez-en en jouant ou en achetant au marché !",
                color=discord.Color.red()
            )
            self.clear_items()
            await interaction.response.edit_message(embed=embed, view=self)
            return

        # Consomme 1 jeton
        use_item(self.user_id, JETON_NAME, quantity=1)

        # Lance la roue
        label, gain, is_token = spin_wheel()
        winning_index = get_winning_index(label)
        wheel_visual = build_wheel_visual(winning_index)

        # Applique le gain
        if is_token:
            # Redonne 1 jeton au joueur
            from inventory_db import add_item
            add_item(
                self.user_id,
                JETON_NAME,
                quantity=1,
                rarity="rare",
                description="Permet de tourner la Roue de la Fortune au casino.",
                price=0
            )
            result_line = "🎰 **Vous regagnez 1 Jeton de roue !**"
        else:
            add_money(self.user_id, gain)
            result_line = f"💰 **+{gain} 💰🐊** ajoutés à votre solde !"

        balance = get_balance(self.user_id)
        jetons_restants = get_items(self.user_id, JETON_NAME)
        jetons_qty = jetons_restants["quantity"] if jetons_restants else 0

        embed = discord.Embed(
            title="🎡 La Roue tourne… et s'arrête sur :",
            description=f"## {label}\n\n"
                        f"{wheel_visual}\n\n"
                        f"{result_line}\n\n"
                        f"**Solde :** {balance} 💰🐊\n"
                        f"**Jetons restants :** {jetons_qty} 🎰",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Bonne chance ! 🍀")

        self.clear_items()
        if jetons_qty > 0:
            self.add_item(SpinAgainButton(self.user_id))

        await interaction.response.edit_message(embed=embed, view=self)


class SpinButton(Button):
    def __init__(self, game_view: "RoueView"):
        super().__init__(
            label="🎡 Lancer la roue",
            style=discord.ButtonStyle.primary,
            emoji="🎰"
        )
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        await self.game_view.do_spin(interaction)


class SpinAgainButton(Button):
    def __init__(self, user_id: int):
        super().__init__(
            label="🔄 Rejouer",
            style=discord.ButtonStyle.success,
            emoji="🎡"
        )
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        new_view = RoueView(user_id=self.user_id)
        item = get_items(self.user_id, JETON_NAME)
        qty = item["quantity"] if item else 0
        balance = get_balance(self.user_id)

        embed = discord.Embed(
            title="🎡 Roue de la Fortune",
            description="**Dépensez 1 Jeton pour faire tourner la roue !**\n\n"
                        + _build_odds_table()
                        + f"\n\n**Votre solde :** {balance} 💰🐊\n"
                        f"**Jetons disponibles :** {qty} 🎰",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Bonne chance ! 🍀")
        await interaction.response.edit_message(embed=embed, view=new_view)


def _build_odds_table() -> str:
    lines = ["**Gains possibles :**"]
    for label, gain, prob in WHEEL_SEGMENTS:
        pct = int(prob * 100)
        lines.append(f"• {label} — {pct}%")
    return "\n".join(lines)


# ------------------------------------------------------------------ #
#  Bouton pour le menu casino                                         #
# ------------------------------------------------------------------ #

class WheelButton(Button):
    """Bouton à ajouter dans CasinoView."""
    def __init__(self):
        super().__init__(
            label="🎡 Roue de la Fortune",
            style=discord.ButtonStyle.primary,
            emoji="🎡"
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        item = get_items(user_id, JETON_NAME)
        qty = item["quantity"] if item else 0
        balance = get_balance(user_id)

        view = RoueView(user_id=user_id)
        embed = discord.Embed(
            title="🎡 Roue de la Fortune",
            description="**Dépensez 1 Jeton pour faire tourner la roue !**\n\n"
                        + _build_odds_table()
                        + f"\n\n**Votre solde :** {balance} 💰🐊\n"
                        f"**Jetons disponibles :** {qty} 🎰",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Bonne chance ! 🍀")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)