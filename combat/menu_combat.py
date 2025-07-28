# combat/menu_combat.py
import discord
from discord.ui import View, Button
from db import get_captures

class SelectionView(View):
    def __init__(self, pokemons, max_select=6):
        super().__init__(timeout=60)
        self.selected = []
        self.max_select = max_select

        for name in pokemons:
            self.add_item(PokemonSelectButton(name, self))

class PokemonSelectButton(Button):
    def __init__(self, name, view_ref):
        super().__init__(label=name, style=discord.ButtonStyle.primary)
        self.pokemon_name = name
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        if self.pokemon_name in self.view_ref.selected:
            await interaction.response.send_message("Déjà sélectionné !", ephemeral=True)
            return

        if len(self.view_ref.selected) >= self.view_ref.max_select:
            await interaction.response.send_message("Tu as déjà choisi 6 Pokémon !", ephemeral=True)
            return

        self.view_ref.selected.append(self.pokemon_name)
        await interaction.response.send_message(f"{self.pokemon_name} ajouté à l'équipe ! ({len(self.view_ref.selected)}/6)", ephemeral=True)

