import discord
from discord.ui import View, Select, Button
from math import ceil
import random
from db import get_captures
from combat.logic_battle import start_battle_turn_based


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
        self.parent_view.selections[self.custom_id] = self.values
        await interaction.response.defer()


class SelectionView(View):
    def __init__(self, pokemons, full_pokemon_data):
        super().__init__(timeout=300)
        self.selections = {}
        self.full_pokemon_data = full_pokemon_data

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

        user_id = str(interaction.user.id)
        all_captures = get_captures(user_id)
        selected_pokemons = [p for p in all_captures if p["name"] in all_selected]

        bot_team = [poke for poke in self.parent_view.full_pokemon_data if poke["name"] in ["Mew", "Roucool", "Rattata"]]



        await start_battle_turn_based(interaction, selected_pokemons, bot_team)
# combat/menu_combat.py
import discord
from discord.ui import View, Select, Button
from discord import SelectOption, ButtonStyle, Interaction
from typing import List
from db import get_captures
from combat.logic_battle import start_battle_turn_based
import random

MAX_TEAM = 6
PAGE_SIZE = 25  # Discord: max 25 options par Select

class SelectionView(View):
    def __init__(self, pokemons: List[str], full_pokemon_data: List[dict]):
        super().__init__(timeout=300)
        self.all_names = pokemons[:]              # tous les noms capturés par l’utilisateur
        self.full_pokemon_data = full_pokemon_data
        self.page = 0
        self.selected = set()                     # noms choisis (persistés entre pages)

        self._rebuild()

    # -------- helpers de pagination --------
    def _page_names(self) -> List[str]:
        start = self.page * PAGE_SIZE
        return self.all_names[start:start + PAGE_SIZE]

    def _last_page_index(self) -> int:
        if not self.all_names:
            return 0
        return (len(self.all_names) - 1) // PAGE_SIZE

    # -------- reconstruction de la View --------
    def _rebuild(self):
        self.clear_items()

        page_names = self._page_names()
        options = [
            SelectOption(label=name, value=name, default=(name in self.selected))
            for name in page_names
        ]

        # calcule combien l’utilisateur peut encore cocher au total
        remaining = MAX_TEAM - len(self.selected)
        max_values_here = min(len(page_names), max(0, remaining))

        select = Select(
            placeholder=f"Sélection (≤ {MAX_TEAM}) — page {self.page + 1}/{self._last_page_index() + 1}",
            min_values=0,
            max_values=max_values_here if max_values_here > 0 else 0,
            options=options,
            row=0
        )

        @select.callback
        async def on_select(inter: Interaction):
            # met à jour les sélections pour CETTE page sans perdre les autres
            current_set = set(page_names)
            # retire ce qui appartenait à cette page
            self.selected -= (self.selected & current_set)
            # ajoute ce que l’utilisateur vient de choisir
            self.selected |= set(select.values)

            # recalcule le max selectable local (au cas où)
            remaining_now = MAX_TEAM - len(self.selected)
            select.max_values = min(len(page_names), max(0, remaining_now))
            await inter.response.edit_message(view=self)

        prev_btn = Button(label="◀️ Précédent", style=ButtonStyle.secondary, row=1)
        next_btn = Button(label="Suivant ▶️", style=ButtonStyle.secondary, row=1)
        validate_btn = Button(label="✅ Valider", style=ButtonStyle.success, row=1)

        @prev_btn.callback
        async def on_prev(inter: Interaction):
            if self.page > 0:
                self.page -= 1
                self._rebuild()
                await inter.response.edit_message(view=self)
            else:
                await inter.response.defer()

        @next_btn.callback
        async def on_next(inter: Interaction):
            if self.page < self._last_page_index():
                self.page += 1
                self._rebuild()
                await inter.response.edit_message(view=self)
            else:
                await inter.response.defer()

        @validate_btn.callback
        async def on_validate(inter: Interaction):
            if not self.selected:
                await inter.response.send_message("❌ Sélectionne au moins un Pokémon.", ephemeral=True)
                return
            if len(self.selected) > MAX_TEAM:
                await inter.response.send_message(f"❌ Maximum {MAX_TEAM} Pokémon.", ephemeral=True)
                return

            user_id = str(inter.user.id)
            all_captures = get_captures(user_id) or []

            # Construit l’équipe joueur à partir des captures, pour conserver IV/stats sauvegardés
            caps_by_name = {}
            for c in all_captures:
                name = c.get("name")
                if name and name not in caps_by_name:
                    caps_by_name[name] = c

            player_team = []
            for name in list(self.selected)[:MAX_TEAM]:
                entry = caps_by_name.get(name)
                if entry:
                    player_team.append(entry)
                else:
                    # repli si pas trouvé dans captures: cherche dans full_pokemon_data
                    for p in self.full_pokemon_data:
                        if p.get("name","").lower() == name.lower():
                            player_team.append(p)
                            break

            if not player_team:
                await inter.response.send_message("❌ Impossible de construire ton équipe.", ephemeral=True)
                return

            # Petite équipe bot: ajuste selon ton besoin
            candidates = [p for p in self.full_pokemon_data if p.get("name") in ["Mew", "Roucool", "Rattata"]]
            bot_team = candidates or random.sample(self.full_pokemon_data, k=min(3, len(self.full_pokemon_data)))

            await inter.response.edit_message(
                content=f"Équipe sélectionnée : {', '.join([p.get('name') for p in player_team])}",
                view=None
            )
            await start_battle_turn_based(inter, player_team, bot_team)

        prev_btn.disabled = (self.page == 0)
        next_btn.disabled = (self.page >= self._last_page_index())

        self.add_item(select)
        self.add_item(prev_btn)
        self.add_item(next_btn)
        self.add_item(validate_btn)
