import discord
from discord.ui import View, Select, Button
from math import ceil
from new_db import get_new_captures

from combat.logic_battle import start_battle_turn_based
from combat.adversaires import get_random_adversaire



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


class ValidateButton(Button):
    def __init__(self, view: "SelectionView"):
        super().__init__(label="✅ Valider", style=discord.ButtonStyle.success, row=4)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        # Concatène toutes les sélections et dédoublonne (garde l'ordre)
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
        all_captures = get_new_captures(user_id)
        selected_pokemons = [p for p in all_captures if p.get("name") in unique_selected]

        # 🔒 Sécurité : aucun Pokémon valide trouvé
        if not selected_pokemons:
            await interaction.followup.send(
                "❌ Aucun Pokémon valide trouvé pour le combat.\n"
                "Tes sélections ne correspondent pas aux captures en base.",
                ephemeral=True
            )
            return


        # Exemple équipe bot (à adapter)
     
        adversaire = get_random_adversaire()

        bot_team = adversaire["pokemons"]
        bot_name = adversaire["name"]
        bot_repliques = adversaire.get("repliques", {})


        await start_battle_turn_based(
            interaction,
            selected_pokemons,
            bot_team,
            adversaire_name=bot_name,
            repliques=bot_repliques
        )



# ---- Vue principale avec pagination ----
class SelectionView(View):
    def __init__(self, pokemons, full_pokemon_data):
        super().__init__(timeout=300)
        self.selections = {}  # custom_id -> [values]
        self.full_pokemon_data = full_pokemon_data

        # Découpe en options (25 max par menu)
        self.chunk_size = 25
        self.option_chunks = [
            [discord.SelectOption(label=name, value=name) for name in pokemons[i:i + self.chunk_size]]
            for i in range(0, len(pokemons), self.chunk_size)
        ]

        # Pagination : 4 menus/page (lignes 0..3), ligne 4 pour les boutons
        self.menus_per_page = 4
        self.page = 0
        self.total_menus = len(self.option_chunks)
        self.total_pages = max(1, ceil(self.total_menus / self.menus_per_page))

        self.rebuild()

    def _current_count(self) -> int:
        # Compte cumulé (dédoublonné) sur toutes les pages/menus
        all_selected = []
        for vals in self.selections.values():
            all_selected.extend(vals)
        return len(dict.fromkeys(all_selected))  # dédoublonnage en gardant l'ordre

    def rebuild(self):
        # Reconstruit complètement la page courante
        self.clear_items()

        start = self.page * self.menus_per_page
        end = min(start + self.menus_per_page, self.total_menus)

        # Ajoute les Selects de la page
        for idx in range(start, end):
            select = PokemonSelectMenu(self.option_chunks[idx], idx, self)

            # Restaure les sélections précédentes : marquer opt.default = True
            prev_values = set(self.selections.get(select.custom_id, []))
            if prev_values:
                for opt in select.options:
                    if opt.value in prev_values:
                        opt.default = True

            self.add_item(select)

        # Boutons (ligne 4)
        prev_disabled = (self.page == 0)
        next_disabled = (self.page >= self.total_pages - 1)

        count = self._current_count()
        self.add_item(PageButton(f"⬅️ Précédent", direction=-1, parent_view=self, disabled=prev_disabled))
        self.add_item(PageButton(f"Suivant ➡️", direction=1, parent_view=self, disabled=next_disabled))
        # On peut indiquer l'état dans le label du bouton valider (facultatif)
        self.add_item(ValidateButton(self))
