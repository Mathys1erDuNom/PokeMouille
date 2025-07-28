import discord
from discord.ui import View, Select
from math import ceil

class PokemonSelectMenu(Select):
    def __init__(self, options, menu_index):
        super().__init__(
            placeholder=f"Sélection {menu_index + 1}",
            min_values=0,
            max_values=min(6, len(options)),  # Tu peux en choisir jusqu’à 6 en tout
            options=options,
            custom_id=f"select_{menu_index}"
        )

    async def callback(self, interaction: discord.Interaction):
        # Réponse silencieuse temporaire (à adapter selon ta logique de combat)
        await interaction.response.send_message(
            f"Tu as choisi : {', '.join(self.values)}", ephemeral=True
        )

class SelectionView(View):
    def __init__(self, pokemons):
        super().__init__(timeout=120)

        # Diviser la liste de Pokémon en groupes de 25
        chunk_size = 25
        pokemon_chunks = [
            pokemons[i:i + chunk_size] for i in range(0, len(pokemons), chunk_size)
        ]

        for index, chunk in enumerate(pokemon_chunks):
            options = [
                discord.SelectOption(label=name, value=name)
                for name in chunk
            ]
            select = PokemonSelectMenu(options, index)
            self.add_item(select)
