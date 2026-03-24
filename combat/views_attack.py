# /app/combat/views_attack.py
import discord
from discord.ui import View, Button, Select

class AttackButton(Button):
    def __init__(self, attack_name: str):
        super().__init__(label=attack_name, style=discord.ButtonStyle.primary)
        self.attack_name = attack_name

    async def callback(self, interaction: discord.Interaction):
        # Le joueur a choisi une attaque
        self.view.selected_action = "attack"
        self.view.selected_attack = self.attack_name
        self.view.stop()
        await interaction.response.defer()

class SwitchButton(Button):
    def __init__(self):
        super().__init__(label="Changer de Pokémon", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        # Le joueur veut changer
        self.view.selected_action = "switch"
        self.view.stop()
        await interaction.response.defer()

class AttackOrSwitchView(View):
    """
    Montre les boutons d'attaque + un bouton "Changer de Pokémon".
    Attributs renseignés à la fin:
      - selected_action ∈ {"attack", "switch", None}
      - selected_attack : str | None
    """
    def __init__(self, attack_names, timeout: float = 20):
        super().__init__(timeout=timeout)
        self.selected_action = None
        self.selected_attack = None

        # 4 attaques max en général, on les ajoute comme boutons
        for name in attack_names:
            self.add_item(AttackButton(str(name)))

        # + le bouton pour changer
        self.add_item(SwitchButton())

class SwitchSelect(Select):
    """
    Select listant les Pokémon du joueur avec leurs PV restants.
    On ne peut pas désactiver une option individuellement côté Discord,
    donc on valide côté callback (pas l'actuel, pas K.O.).
    """
    def __init__(self, state):
        options = []
        for idx, poke in enumerate(state.player_team):
            name = poke.get("name", f"Pokemon {idx+1}")
            hp = state.player_hp_pool[idx]
            label = f"{name} ({hp} PV)"
            options.append(discord.SelectOption(label=label, value=str(idx)))

        super().__init__(
            placeholder="Choisis le Pokémon à envoyer",
            min_values=1,
            max_values=1,
            options=options
        )
        self._state_obj = state

    async def callback(self, interaction: discord.Interaction):
        chosen = int(self.values[0])
        # Refuse l'actuel ou un K.O.
        if chosen == self._state_obj.active_player_index or self._state_obj.player_hp_pool[chosen] <= 0:
            await interaction.response.send_message(
                "❌ Ce Pokémon ne peut pas être envoyé (actuel ou K.O.).",
                ephemeral=True
            )
            return
        # OK
        self.view.chosen_index = chosen
        self.view.stop()
        await interaction.response.defer()

class SwitchSelectView(View):
    """
    Affiche le select de switch.
    Attributs renseignés à la fin:
      - chosen_index : int | None
    """
    def __init__(self, state, timeout: float = 20):
        super().__init__(timeout=timeout)
        self.chosen_index = None
        self.add_item(SwitchSelect(state))
