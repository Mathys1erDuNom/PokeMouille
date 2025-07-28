import discord
from discord.ui import View, Select, Button
from math import ceil

class PokemonSelectMenu(Select):
    def __init__(self, options, menu_index, parent_view):
        super().__init__(
            placeholder=f"Sélection {menu_index + 1}",
            min_values=0,
            max_values=6,
            options=options,
            custom_id=f"select_{menu_index}"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Enregistre les valeurs sélectionnées dans le View
        self.parent_view.selections[self.custom_id] = self.values
        await interaction.response.defer()  # pas de message, juste une MAJ des données

class SelectionView(View):
    def __init__(self, pokemons):
        super().__init__(timeout=300)
        self.selections = {}

        chunk_size = 25
        chunks = [pokemons[i:i+chunk_size] for i in range(0, len(pokemons), chunk_size)]

        for idx, chunk in enumerate(chunks):
            options = [
                discord.SelectOption(label=name, value=name)
                for name in chunk
            ]
            select = PokemonSelectMenu(options, idx, self)
            self.add_item(select)

        self.add_item(ValidateButton(self))

class ValidateButton(Button):
    def __init__(self, view: SelectionView):
        super().__init__(label="✅ Valider", style=discord.ButtonStyle.green)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        # Fusionne toutes les sélections
        all_selected = []
        for selected in self.parent_view.selections.values():
            all_selected.extend(selected)

        if len(all_selected) == 0:
            await interaction.response.send_message("❌ Tu dois sélectionner au moins un Pokémon.", ephemeral=True)
            return

        if len(all_selected) > 6:
            await interaction.response.send_message("❌ Tu ne peux sélectionner que 6 Pokémon maximum.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Tu as choisi : {', '.join(all_selected)}", ephemeral=True
        )
