import discord
from discord.ui import View, Select, Button
from discord import SelectOption, ButtonStyle, Interaction
from typing import List, Dict
import random

from db import get_captures
from combat.logic_battle import start_battle_turn_based

MAX_TEAM = 6
PAGE_SIZE = 25  # Discord: 25 options max par Select

class SelectionView(View):
    def __init__(self, pokemons: List[str], full_pokemon_data: List[Dict]):
        super().__init__(timeout=300)
        self.all_names = pokemons[:]            # tous les noms capturés
        self.full_pokemon_data = full_pokemon_data
        self.page = 0
        self.selected = set()                   # noms choisis (persistés entre pages)
        self._build_view()

    # --------- pagination helpers ----------
    def _page_names(self) -> List[str]:
        start = self.page * PAGE_SIZE
        return self.all_names[start:start + PAGE_SIZE]

    def _last_page_idx(self) -> int:
        if not self.all_names:
            return 0
        return (len(self.all_names) - 1) // PAGE_SIZE

    # --------- (re)construction ----------
    def _build_view(self):
        self.clear_items()

        page_names = self._page_names()
        options = [
            SelectOption(label=name, value=name, default=(name in self.selected))
            for name in page_names
        ]

        remaining = MAX_TEAM - len(self.selected)

        select = Select(
            placeholder=self._placeholder_text(),
            min_values=0,
            max_values=min(len(page_names), max(1, remaining)) if len(page_names) > 0 else 1,
            options=options,
            row=0
        )
        # Désactive complètement le Select si l'équipe est déjà pleine
        if remaining <= 0:
            select.disabled = True

        @select.callback
        async def on_select(inter: Interaction):
            # Met à jour les sélections de CETTE page
            current_page_set = set(page_names)
            self.selected -= (self.selected & current_page_set)     # retire anciens choix de cette page
            proposed = set(select.values)

            # Applique le plafond global MAX_TEAM
            room = MAX_TEAM - len(self.selected)
            if room <= 0:
                # équipe déjà pleine => on remet la vue telle quelle
                await inter.response.send_message("❗ Ton équipe est déjà complète (6).", ephemeral=True)
                self._build_view()
                await inter.edit_original_response(view=self)
                return

            # Si l'utilisateur a coché plus que la place restante, tronque proprement
            if len(proposed) > room:
                proposed = set(list(proposed)[:room])
                await inter.response.send_message(
                    f"❗ Maximum {MAX_TEAM} Pokémon. Seuls {room} choix supplémentaires pris en compte.",
                    ephemeral=True
                )

            # Ajoute les nouveaux choix
            self.selected |= proposed

            # Reconstruit la vue (peut désactiver le Select si plein)
            self._build_view()
            await inter.response.edit_message(view=self)

        prev_btn = Button(label="◀️ Précédent", style=ButtonStyle.secondary, row=1)
        next_btn = Button(label="Suivant ▶️", style=ButtonStyle.secondary, row=1)
        validate_btn = Button(label="✅ Valider", style=ButtonStyle.success, row=1)

        @prev_btn.callback
        async def on_prev(inter: Interaction):
            if self.page > 0:
                self.page -= 1
                self._build_view()
                await inter.response.edit_message(view=self)
            else:
                await inter.response.defer()

        @next_btn.callback
        async def on_next(inter: Interaction):
            if self.page < self._last_page_idx():
                self.page += 1
                self._build_view()
                await inter.response.edit_message(view=self)
            else:
                await inter.response.defer()

        @validate_btn.callback
        async def on_validate(inter: Interaction):
            if not self.selected:
                await inter.response.send_message("❌ Sélectionne au moins un Pokémon.", ephemeral=True)
                return

            # Récup captures joueur pour conserver IV/stats
            user_id = str(inter.user.id)
            captures = get_captures(user_id) or []
            caps_by_name = {c.get("name"): c for c in captures if c.get("name")}

            chosen_names = list(self.selected)[:MAX_TEAM]
            player_team = []
            for name in chosen_names:
                # priorité aux captures (avec IV/stats)
                if name in caps_by_name:
                    player_team.append(caps_by_name[name])
                else:
                    # repli sur le catalogue global
                    for p in self.full_pokemon_data:
                        if p.get("name","").lower() == name.lower():
                            player_team.append(p)
                            break

            if not player_team:
                await inter.response.send_message("❌ Impossible de construire ton équipe.", ephemeral=True)
                return

            # Équipe bot de base (modifie selon tes besoins)
            fixed = [p for p in self.full_pokemon_data if p.get("name") in ["Mew", "Roucool", "Rattata"]]
            bot_team = fixed if fixed else random.sample(self.full_pokemon_data, k=min(3, len(self.full_pokemon_data)))

            await inter.response.edit_message(
                content=f"Équipe sélectionnée : {', '.join(chosen_names)}",
                view=None
            )
            await start_battle_turn_based(inter, player_team, bot_team)

        # états des boutons
        prev_btn.disabled = (self.page == 0)
        next_btn.disabled = (self.page >= self._last_page_idx())

        # Ajout (≤ 4 composants)
        self.add_item(select)
        self.add_item(prev_btn)
        self.add_item(next_btn)
        self.add_item(validate_btn)

    def _placeholder_text(self) -> str:
        total = len(self.all_names)
        page = self.page + 1
        pages = self._last_page_idx() + 1
        left = max(0, MAX_TEAM - len(self.selected))
        return f"Sélection ({MAX_TEAM - left}/{MAX_TEAM}) — page {page}/{pages}"
