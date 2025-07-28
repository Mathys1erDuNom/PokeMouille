from db import get_captures
from bot import full_pokemon_data  # assure-toi que ce chemin est correct selon ton projet

class ValidateButton(Button):
    def __init__(self, view: SelectionView):
        super().__init__(label="✅ Valider", style=discord.ButtonStyle.green)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
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
            f"Tu as choisi : {', '.join(all_selected)}.\nPréparation du combat...", ephemeral=True
        )

        # Récupération des Pokémon sélectionnés du joueur
        user_id = str(interaction.user.id)
        all_captures = get_captures(user_id)
        selected_pokemons = [p for p in all_captures if p["name"] in all_selected]

        # Générer une équipe bot aléatoire
        import random
        bot_team = random.sample(full_pokemon_data, k=min(6, len(full_pokemon_data)))

        # Lancer le combat
        await start_battle_turn_based(interaction, selected_pokemons, bot_team)
