import discord
from discord.ui import View, Select, Button
from math import ceil
from db import get_captures
from combat.logic_battle import start_battle_turn_based


# ---- Menus ----
class PokemonSelectMenu(Select):
    def __init__(self, options, menu_index, parent_view):
        # Un Select = max 25 options
        super().__init__(
            placeholder=f"Sélection {menu_index + 1}",
            min_values=0,                               # aucun choix obligatoire par menu
            max_values=min(6, len(options)),            # limite locale; la vraie limite (6 au total) est revalidée à la fin
            options=options,
            custom_id=f"select_{menu_index}",
            row=menu_index % 4                          # 4 lignes pour les selects (0..3)
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Mémorise les sélections de ce menu
        self.parent_view.selections[self.custom_id] = self.values
        # Pas de validation ici : l'utilisateur peut continuer à changer de page et choisir ailleurs
        await interaction.response.defer()


# ---- Boutons de navigation ----
class PageButton(Button):
    def __init__(self, label, direction, parent_view, disabled=False):
        # Boutons sur la ligne 5 (row=4)
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=4, disabled=disabled)
        self.direction = direction
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        new_page = self.parent_view.page + self.direction
        if 0 <= new_page < self.parent_view.total_pages:
            self.parent_view.page = new_page
            self.parent_view.rebuild()
            await interaction.response.edit_message(view=self.parent_view)
        else:
            await interaction.response.defer()

from pathlib import Path

class ValidateButton(Button):
    def __init__(self, view: "SelectionView"):
        super().__init__(label="✅ Valider", style=discord.ButtonStyle.success, row=4)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        # Concatène & dédoublonne
        all_selected = []
        for selected in self.parent_view.selections.values():
            all_selected.extend(selected)
        seen = set()
        unique_selected = []
        for name in all_selected:
            if name not in seen:
                seen.add(name)
                unique_selected.append(name)

        if len(unique_selected) == 0:
            await interaction.response.send_message("❌ Tu dois sélectionner au moins un Pokémon.", ephemeral=True)
            return
        if len(unique_selected) > 6:
            await interaction.response.send_message("❌ Tu ne peux sélectionner que 6 Pokémon maximum (tous menus/pages confondus).", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Tu as choisi : {', '.join(unique_selected)}.\nPréparation du combat...", ephemeral=True
        )

        user_id = str(interaction.user.id)
        all_captures = get_captures(user_id)

        # 🔒 Match exact par nom (pense à harmoniser la casse côté données)
        selected_pokemons = [p for p in all_captures if p.get("name") in unique_selected]
        if not selected_pokemons:
            await interaction.followup.send("❌ Aucun des Pokémon sélectionnés n'a été trouvé dans tes captures.", ephemeral=True)
            return

        # Équipe bot d'exemple (à adapter)
        bot_team = [poke for poke in self.parent_view.full_pokemon_data if poke.get("name") in ["Mew", "Roucool", "Rattata"]]

        # ✅ Résolution d'un chemin ABSOLU pour l'image locale
        #   -> part de ce fichier, remonte au dossier racine de ton projet si besoin
        base_dir = Path(__file__).resolve().parent  # ex: .../combat/
        # ajuste le nombre de .parent selon ta structure
        bg_path = (base_dir.parent / "images" / "arena.png").as_posix()

        # Option: si tu héberges l'image en HTTP, mets directement l’URL ici
        # bg_path = "https://ton-cdn.exemple.com/images/arena.png"

        await start_battle_turn_based(interaction, selected_pokemons, bot_team, bg_image=bg_path)
