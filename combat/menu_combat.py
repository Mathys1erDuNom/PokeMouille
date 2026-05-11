import discord
from discord.ui import View, Select, Button
from math import ceil
from new_db_avantmodif import get_new_captures
import json
import os
from combat.logic_battle import start_battle_turn_based

script_dir = os.path.dirname(os.path.abspath(__file__))

from regions import get_user_region

ADVERSAIRES_DIR = os.path.join(script_dir, "../json/")

def get_adversaires_by_region(region: str):
    if not region:
        return []
    filename = os.path.join(ADVERSAIRES_DIR, f"adversaires_{region.lower()}.json")
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def get_adversaire_by_name(name: str, region: str):
    adversaires = get_adversaires_by_region(region)
    for adv in adversaires:
        if adv["name"].lower() == name.lower():
            return adv
    return None


# ---- Slot unique par position ----
class SlotSelect(Select):
    def __init__(self, slot_number, pokemon_names, parent_view):
        options = [discord.SelectOption(label="(aucun)", value="aucun")] + [
            discord.SelectOption(label=name, value=name)
            for name in pokemon_names
        ]
        super().__init__(
            placeholder=f"🥊 Slot {slot_number}",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"slot_{slot_number}",
            row=slot_number - 1  # rows 0 à 4 (donc max 5 slots)
        )
        self.slot = slot_number
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.slots[self.slot] = self.values[0]
        await interaction.response.defer()


# ---- Bouton valider ----
class ValidateButton(Button):
    def __init__(self, view: "SelectionView"):
        super().__init__(label="✅ Valider", style=discord.ButtonStyle.success, row=4)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        # Récupère les slots remplis dans l'ordre
        unique_selected = [
            name for slot, name in sorted(self.parent_view.slots.items())
            if name != "aucun"
        ]

        if len(unique_selected) == 0:
            await interaction.response.send_message(
                "❌ Tu dois sélectionner au moins un Pokémon.",
                ephemeral=True
            )
            return

        # Vérifie les doublons
        if len(unique_selected) != len(set(unique_selected)):
            await interaction.response.send_message(
                "❌ Tu as sélectionné le même Pokémon dans plusieurs slots.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Tu as choisi (dans l'ordre de combat) : {', '.join(unique_selected)}.\nPréparation du combat...",
            ephemeral=True
        )

        user_id = str(interaction.user.id)
        all_captures = get_new_captures(user_id)

        captures_by_name = {}
        for p in all_captures:
            name = p.get("name")
            if name and name not in captures_by_name:
                captures_by_name[name] = p

        selected_pokemons = [
            captures_by_name[name]
            for name in unique_selected
            if name in captures_by_name
        ]

        if not selected_pokemons:
            await interaction.followup.send(
                "❌ Aucun Pokémon valide trouvé pour le combat.",
                ephemeral=True
            )
            return

        adversaire = getattr(self.parent_view, "chosen_adversaire", None)
        if adversaire:
            bot_team = adversaire["pokemons"]
            bot_name = adversaire["name"]
            bot_repliques = adversaire.get("repliques", {})
        else:
            bot_team = []
            bot_name = "Bot"
            bot_repliques = {}

        await start_battle_turn_based(
            interaction,
            selected_pokemons,
            bot_team,
            adversaire_name=bot_name,
            repliques=bot_repliques
        )


# ---- Select adversaire ----
class AdversaireSelect(Select):
    def __init__(self, adversaires, parent_view):
        options = [
            discord.SelectOption(
                label=f"{i+1}. {adv['name']}",
                value=adv["name"]
            )
            for i, adv in enumerate(adversaires)
        ]
        super().__init__(
            placeholder="Choisis ton adversaire",
            min_values=1,
            max_values=1,
            options=options
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        name = self.values[0]
        region = getattr(self.parent_view, "region", None)
        adversaire = get_adversaire_by_name(name, region)
        if adversaire:
            self.parent_view.chosen_adversaire = adversaire
            await self.parent_view.show_pokemon_select(interaction)
        else:
            await interaction.response.send_message(
                f"❌ Adversaire '{name}' introuvable pour la région '{region}'.",
                ephemeral=True
            )


# ---- Vue principale ----
class SelectionView(View):
    def __init__(self, pokemons, full_pokemon_data, user_id: str):
        super().__init__(timeout=300)
        self.full_pokemon_data = full_pokemon_data
        self.chosen_adversaire = None
        self.pokemon_names = pokemons
        self.slots = {i: "aucun" for i in range(1, 5)}

        region = get_user_region(user_id)
        self.region = region
        self.adversaires = get_adversaires_by_region(region)

        if not self.adversaires:
            raise ValueError(f"Aucun adversaire disponible pour la région : {region}")

        self.clear_items()
        self.add_item(AdversaireSelect(self.adversaires, self))

    async def show_pokemon_select(self, interaction: discord.Interaction):
        self.clear_items()
        self.rebuild()
        await interaction.response.edit_message(
            content=f"✅ Adversaire : **{self.chosen_adversaire['name']}**\nChoisis tes Pokémon par slot (slot 1 = premier en combat) :",
            view=self
        )

    def rebuild(self):
        self.clear_items()
        for slot in range(1, 5):
            select = SlotSelect(slot, self.pokemon_names, self)
            # Restaure la valeur déjà choisie
            current = self.slots.get(slot, "")
            if current and current != "aucun":
                for opt in select.options:
                    if opt.value == current:
                        opt.default = True
            self.add_item(select)
        self.add_item(ValidateButton(self))  # row=4