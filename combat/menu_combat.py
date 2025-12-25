import discord
from discord.ui import View, Select, Button
from math import ceil
from db import get_captures
from combat.logic_battle import start_battle_turn_based
from opponents import OPPONENTS, get_opponent_team


# ---- Sélection d'adversaire ----
class OpponentSelectMenu(Select):
    def __init__(self, parent_view):
        options = [
            discord.SelectOption(
                label=opp.name,
                value=key,
                description=f"Difficulté: {opp.difficulty} | {len(opp.team)} Pokémon",
                emoji="⚔️"
            )
            for key, opp in OPPONENTS.items()
        ]
        
        super().__init__(
            placeholder="Choisis ton adversaire",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="opponent_select",
            row=0
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selected_opponent = self.values[0]
        opponent = OPPONENTS[self.values[0]]
        
        await interaction.response.send_message(
            f"🎯 Adversaire sélectionné : **{opponent.name}**\n"
            f"Difficulté : {opponent.difficulty}\n"
            f"{opponent.get_intro()}",
            ephemeral=True
        )


# ---- Menus de sélection Pokémon ----
class PokemonSelectMenu(Select):
    def __init__(self, options, menu_index, parent_view):
        super().__init__(
            placeholder=f"Sélection {menu_index + 1}",
            min_values=0,
            max_values=min(6, len(options)),
            options=options,
            custom_id=f"select_{menu_index}",
            row=(menu_index % 3) + 1  # Lignes 1-3 (ligne 0 pour l'adversaire)
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selections[self.custom_id] = self.values
        await interaction.response.defer()


# ---- Boutons de navigation ----
class PageButton(Button):
    def __init__(self, label, direction, parent_view, disabled=False):
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
        super().__init__(label="✅ Valider et Combattre", style=discord.ButtonStyle.success, row=4)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        # Vérifie qu'un adversaire est sélectionné
        if not self.parent_view.selected_opponent:
            await interaction.response.send_message(
                "❌ Tu dois d'abord choisir un adversaire !",
                ephemeral=True
            )
            return
        
        # Concatène toutes les sélections et dédoublonne
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
            await interaction.response.send_message(
                "❌ Tu dois sélectionner au moins un Pokémon.",
                ephemeral=True
            )
            return
        if len(unique_selected) > 6:
            await interaction.response.send_message(
                "❌ Tu ne peux sélectionner que 6 Pokémon maximum.",
                ephemeral=True
            )
            return

        # Récupère l'adversaire et son équipe
        opponent = OPPONENTS[self.parent_view.selected_opponent]
        bot_team = get_opponent_team(opponent, self.parent_view.full_pokemon_data)

        await interaction.response.send_message(
            f"⚔️ **Combat contre {opponent.name}** ⚔️\n"
            f"Ton équipe : {', '.join(unique_selected)}\n"
            f"Équipe adverse : {', '.join([p['name'] for p in bot_team])}\n\n"
            f"Que le combat commence !",
            ephemeral=True
        )

        user_id = str(interaction.user.id)
        all_captures = get_captures(user_id)
        selected_pokemons = [p for p in all_captures if p.get("name") in unique_selected]

        # Lance le combat avec le nom de l'adversaire
        await start_battle_turn_based(
            interaction,
            selected_pokemons,
            bot_team,
            opponent_name=opponent.name
        )


# ---- Vue principale avec pagination ----
class SelectionView(View):
    def __init__(self, pokemons, full_pokemon_data):
        super().__init__(timeout=300)
        self.selections = {}
        self.selected_opponent = None
        self.full_pokemon_data = full_pokemon_data

        # Découpe en options (25 max par menu)
        self.chunk_size = 25
        self.option_chunks = [
            [discord.SelectOption(label=name, value=name) for name in pokemons[i:i + self.chunk_size]]
            for i in range(0, len(pokemons), self.chunk_size)
        ]

        # Pagination : 3 menus/page (lignes 1-3), ligne 0 pour adversaire, ligne 4 pour boutons
        self.menus_per_page = 3
        self.page = 0
        self.total_menus = len(self.option_chunks)
        self.total_pages = max(1, ceil(self.total_menus / self.menus_per_page))

        self.rebuild()

    def _current_count(self) -> int:
        all_selected = []
        for vals in self.selections.values():
            all_selected.extend(vals)
        return len(dict.fromkeys(all_selected))

    def rebuild(self):
        self.clear_items()

        # Ajoute le menu de sélection d'adversaire (ligne 0)
        self.add_item(OpponentSelectMenu(self))

        # Ajoute les Selects de Pokémon pour la page courante
        start = self.page * self.menus_per_page
        end = min(start + self.menus_per_page, self.total_menus)

        for idx in range(start, end):
            select = PokemonSelectMenu(self.option_chunks[idx], idx, self)
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
        self.add_item(PageButton(
            f"⬅️ Précédent",
            direction=-1,
            parent_view=self,
            disabled=prev_disabled
        ))
        self.add_item(PageButton(
            f"Suivant ➡️ ({count}/6)",
            direction=1,
            parent_view=self,
            disabled=next_disabled
        ))
        self.add_item(ValidateButton(self))