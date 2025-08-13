# view_attack.py
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

class AttackView(View):
    """
    Garde le même nom qu'avant pour éviter de changer tes imports,
    mais ajoute un bouton 'Changer de Pokémon'.
    Sortie :
      - selected_action in {"attack","switch",None}
      - selected_attack (si action=attack)
    """
    def __init__(self, attack_names, timeout: float = 20):
        super().__init__(timeout=timeout)
        self.selected_action = None
        self.selected_attack = None

        for name in attack_names:
            self.add_item(AttackButton(name))

        # ➕ le bouton changement
        self.add_item(SwitchButton())


# ------- Sélecteur de Pokémon pour le switch -------
class SwitchSelect(Select):
    def __init__(self, state):
        # Construit les options du joueur
        options = []
        for idx, poke in enumerate(state.player_team):
            name = poke.get("name", f"Pokémon {idx+1}")
            hp = state.player_hp_pool[idx]
            label = f"{name} ({hp} PV)"
            options.append(discord.SelectOption(label=label, value=str(idx)))
        super().__init__(placeholder="Choisis le Pokémon à envoyer", min_values=1, max_values=1, options=options)
        self._state_obj = state

    async def callback(self, interaction: discord.Interaction):
        chosen = int(self.values[0])
        # Refuse l'actuel ou un K.O.
        if chosen == self._state_obj.active_player_index or self._state_obj.player_hp_pool[chosen] <= 0:
            await interaction.response.send_message("❌ Ce Pokémon ne peut pas être envoyé (actuel ou K.O.).", ephemeral=True)
            return
        self.view.chosen_index = chosen
        self.view.stop()
        await interaction.response.defer()

class SwitchSelectView(View):
    def __init__(self, state, timeout: float = 20):
        super().__init__(timeout=timeout)
        self.chosen_index = None
        self.add_item(SwitchSelect(state))
