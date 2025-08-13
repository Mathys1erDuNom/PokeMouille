# views_attack.py

import discord
from discord.ui import View, Button, Select

class AttackButton(Button):
    def __init__(self, attack_name):
        super().__init__(label=attack_name, style=discord.ButtonStyle.primary)
        self.attack_name = attack_name

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_action = "attack"
        self.view.selected_attack = self.attack_name
        self.view.stop()
        await interaction.response.defer()

class SwitchButton(Button):
    def __init__(self):
        super().__init__(label="Changer de Pokémon", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_action = "switch"
        self.view.stop()
        await interaction.response.defer()

class AttackOrSwitchView(View):
    """
    View montrant 1 à N boutons d'attaque + 1 bouton pour changer de Pokémon.
    Résultats:
        - selected_action in {"attack", "switch", None}
        - selected_attack (str ou None)
    """
    def __init__(self, attack_names, timeout: float = 20):
        super().__init__(timeout=timeout)
        self.selected_action = None
        self.selected_attack = None

        # Discord limite à 5 boutons par ligne, 25 composants max
        for name in attack_names:
            self.add_item(AttackButton(name))

        self.add_item(SwitchButton())

class SwitchSelect(Select):
    def __init__(self, state):
        # Construit la liste des choix du joueur
        options = []
        for idx, poke in enumerate(state.player_team):
            name = poke.get("name", f"Pokémon {idx+1}")
            # Désactiver l'actif / les K.O.
            disabled = (idx == state.active_player_index) or (state.player_hp_pool[idx] <= 0)
            label = f"{name} ({state.player_hp_pool[idx]} PV)"
            options.append(discord.SelectOption(label=label, value=str(idx), default=False, description=None))
            # Note: discord.SelectOption n'a pas de 'disabled', on gère côté logique

        super().__init__(
            placeholder="Choisis le Pokémon à envoyer",
            min_values=1,
            max_values=1,
            options=options
        )
        self._state_obj = state  # référence au BattleState

    async def callback(self, interaction: discord.Interaction):
        chosen = int(self.values[0])
        # Vérifie la validité (pas l'actif, pas K.O.)
        if not self._state_obj.can_switch_player_to(chosen):
            await interaction.response.send_message("❌ Ce Pokémon ne peut pas être envoyé (actuel ou K.O.).", ephemeral=True)
            return
        self.view.chosen_index = chosen
        self.view.stop()
        await interaction.response.defer()

class SwitchSelectView(View):
    """
    View pour choisir le nouveau Pokémon du joueur.
    Résultats:
        - chosen_index (int ou None)
    """
    def __init__(self, state, timeout: float = 20):
        super().__init__(timeout=timeout)
        self.chosen_index = None
        self.add_item(SwitchSelect(state))
