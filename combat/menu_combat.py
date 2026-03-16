import discord
from discord.ui import View, Select, Button
from math import ceil
from new_db import get_new_captures
import json
import os
from combat.logic_battle_avec_mega import start_battle_turn_based

script_dir = os.path.dirname(os.path.abspath(__file__))


# Remplace l'import et la fonction existante
from regions import get_user_region  # ton fichier de gestion des régions

ADVERSAIRES_DIR = os.path.join(script_dir, "../json/")

def get_adversaires_by_region(region: str):
    """Charge le fichier d'adversaires correspondant à la région."""
    if not region:
        return []
    filename = os.path.join(ADVERSAIRES_DIR, f"adversaires_{region.lower()}.json")
    print(f"[DEBUG] Fichier cherché : {filename}")
    print(f"[DEBUG] Fichier existe : {os.path.exists(filename)}")
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def get_adversaire_by_name(name: str, region: str):  # ← ajout region
    adversaires = get_adversaires_by_region(region)  # ← on passe la région
    for adv in adversaires:
        if adv["name"].lower() == name.lower():
            return adv
    return None

# ---- Menus ----
class PokemonSelectMenu(Select):
    def __init__(self, options, menu_index, parent_view):
        super().__init__(
            placeholder=f"Sélection {menu_index + 1}",
            min_values=0,
            max_values=min(6, len(options)),
            options=options,
            custom_id=f"select_{menu_index}",
            row=menu_index % 4
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Mémorise les sélections de ce menu avec timestamp
        import time
        current_time = time.time()
        
        # Récupère les anciennes sélections de ce menu
        old_selections = set(self.parent_view.selections.get(self.custom_id, []))
        new_selections = set(self.values)
        
        # Pokémon nouvellement ajoutés
        added = new_selections - old_selections
        # Pokémon retirés
        removed = old_selections - new_selections
        
        # Met à jour l'ordre global
        for pokemon in removed:
            if pokemon in self.parent_view.selection_order:
                del self.parent_view.selection_order[pokemon]
        
        for pokemon in added:
            if pokemon not in self.parent_view.selection_order:
                self.parent_view.selection_order[pokemon] = current_time
                current_time += 0.001  # Évite les collisions
        
        # Met à jour les sélections de ce menu
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
        super().__init__(label="✅ Valider", style=discord.ButtonStyle.success, row=4)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        # Trie les Pokémon selon l'ordre chronologique de sélection
        sorted_pokemon = sorted(
            self.parent_view.selection_order.items(),
            key=lambda x: x[1]  # Trie par timestamp
        )
        unique_selected = [name for name, _ in sorted_pokemon]
        
        if len(unique_selected) == 0:
            await interaction.response.send_message(
                "❌ Tu dois sélectionner au moins un Pokémon.", 
                ephemeral=True
            )
            return
        
        if len(unique_selected) > 6:
            await interaction.response.send_message(
                "❌ Tu ne peux sélectionner que 6 Pokémon maximum (tous menus/pages confondus).", 
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            f"Tu as choisi (dans l'ordre de combat) : {', '.join(unique_selected)}.\nPréparation du combat...",
            ephemeral=True
        )
        
        user_id = str(interaction.user.id)
        all_captures = get_new_captures(user_id)
        
        # Crée la liste ordonnée des Pokémon pour le combat
        selected_pokemons = []
        for name in unique_selected:
            for p in all_captures:
                if p.get("name") == name:
                    selected_pokemons.append(p)
                    break
        
        # 🔒 Sécurité : aucun Pokémon valide trouvé
        if not selected_pokemons:
            await interaction.followup.send(
                "❌ Aucun Pokémon valide trouvé pour le combat.\n"
                "Tes sélections ne correspondent pas aux captures en base.",
                ephemeral=True
            )
            return
        
        # Récupère l'adversaire choisi
        adversaire = getattr(self.parent_view, "chosen_adversaire", None)
        if adversaire:
            bot_team = adversaire["pokemons"]
            bot_name = adversaire["name"]
            bot_repliques = adversaire.get("repliques", {})
        else:
            bot_team = [poke for poke in self.parent_view.full_pokemon_data 
                       if poke.get("name") in ["Mew", "Groudon_shiny", "Elektek"]]
            bot_name = "Bot"
            bot_repliques = {}
        
        await start_battle_turn_based(
            interaction,
            selected_pokemons,
            bot_team,
            adversaire_name=bot_name,
            repliques=bot_repliques
        )

class AdversaireSelect(Select):
    def __init__(self, adversaires, parent_view):
        options = [discord.SelectOption(label=adv["name"], value=adv["name"]) 
                  for adv in adversaires]
        super().__init__(
            placeholder="Choisis ton adversaire",
            min_values=1,
            max_values=1,
            options=options
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        name = self.values[0]
        region = getattr(self.parent_view, "region", None)  # ← récupère la région
        adversaire = get_adversaire_by_name(name, region)
        if adversaire:
            self.parent_view.chosen_adversaire = adversaire
            await self.parent_view.show_pokemon_select(interaction)

# ---- Vue principale avec pagination ----
class SelectionView(View):
    def __init__(self, pokemons, full_pokemon_data, user_id: str):
        super().__init__(timeout=300)
        self.selections = {}
        self.selection_order = {}
        self.full_pokemon_data = full_pokemon_data
        self.chosen_adversaire = None

        region = get_user_region(user_id)  # ← doit être AVANT get_adversaires_by_region
        self.adversaires = get_adversaires_by_region(region)

        if not self.adversaires:
            raise ValueError(f"Aucun adversaire disponible pour la région : {region}")

        self.chunk_size = 25
        self.option_chunks = [
            [discord.SelectOption(label=name, value=name)
             for name in pokemons[i:i + self.chunk_size]]
            for i in range(0, len(pokemons), self.chunk_size)
        ]

        self.menus_per_page = 4
        self.page = 0
        self.total_menus = len(self.option_chunks)
        self.total_pages = max(1, ceil(self.total_menus / self.menus_per_page))

        self.clear_items()
        self.add_item(AdversaireSelect(self.adversaires, self))

    async def show_pokemon_select(self, interaction: discord.Interaction):
        # Reconstruit la vue pour afficher le menu Pokémon
        self.clear_items()
        self.page = 0
        self.rebuild()
        await interaction.response.edit_message(
            content=f"✅ Adversaire choisi : {self.chosen_adversaire['name']}\nChoisis tes Pokémon (l'ordre de sélection = ordre de combat) :",
            view=self
        )

    def _current_count(self) -> int:
        # Compte total des Pokémon sélectionnés
        return len(self.selection_order)

    def rebuild(self):
        # Reconstruit complètement la page courante
        self.clear_items()
        start = self.page * self.menus_per_page
        end = min(start + self.menus_per_page, self.total_menus)
        
        # Ajoute les Selects de la page
        for idx in range(start, end):
            select = PokemonSelectMenu(self.option_chunks[idx], idx, self)
            
            # Restaure les sélections précédentes
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