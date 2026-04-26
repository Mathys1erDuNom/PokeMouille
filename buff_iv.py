# buff_iv.py
import discord
from discord.ui import View, Button
from new_db import increase_pokemon_iv

# Mapping extra → clé de stat
EXTRA_TO_STAT = {
    "buff_pv":           "hp",
    "buff_attaque":      "attack",
    "buff_attaque_spe":  "special_attack",
    "buff_defense":      "defense",
    "buff_defense_spe":  "special_defense",
    "buff_vitesse":      "speed",
}

STAT_LABELS = {
    "hp":               "❤️ PV",
    "attack":           "⚔️ Attaque",
    "special_attack":   "✨ Attaque Spéciale",
    "defense":          "🛡️ Défense",
    "special_defense":  "💠 Défense Spéciale",
    "speed":            "💨 Vitesse",
}


class BuffPokemonView(View):
    """Menu de sélection du Pokémon à buffer — la stat est déjà fixée par l'item utilisé."""

    def __init__(self, user_id, pokemons, stat_key, iv_increase=4):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.pokemons = pokemons
        self.stat_key = stat_key
        self.iv_increase = iv_increase
        self.page = 0
        self.max_per_page = 23
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start = self.page * self.max_per_page
        end = start + self.max_per_page

        for name in self.pokemons[start:end]:
            self.add_item(BuffPokemonButton(name, self.user_id, self.stat_key, self.iv_increase))

        if self.page > 0:
            self.add_item(BuffPrevButton(self))
        if end < len(self.pokemons):
            self.add_item(BuffNextButton(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class BuffPokemonButton(Button):
    def __init__(self, pokemon_name, user_id, stat_key, iv_increase):
        super().__init__(label=pokemon_name, style=discord.ButtonStyle.primary)
        self.pokemon_name = pokemon_name
        self.user_id = user_id
        self.stat_key = stat_key
        self.iv_increase = iv_increase

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        success = increase_pokemon_iv(
            self.user_id,
            self.pokemon_name,
            self.iv_increase,
            stat_name=self.stat_key
        )

        stat_label = STAT_LABELS.get(self.stat_key, self.stat_key)

        if success:
            await interaction.followup.send(
                f"✅ **{self.pokemon_name}** a gagné **+{self.iv_increase} IV en {stat_label}** !",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ Impossible de buff **{self.pokemon_name}** en {stat_label} (IV déjà à 31 ?).",
                ephemeral=True
            )


class BuffPrevButton(Button):
    def __init__(self, view_ref):
        super().__init__(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page -= 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(view=self.view_ref)


class BuffNextButton(Button):
    def __init__(self, view_ref):
        super().__init__(label="Suivant ➡️", style=discord.ButtonStyle.secondary)
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page += 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(view=self.view_ref)