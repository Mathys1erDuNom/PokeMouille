# buff_iv.py
import discord
from discord.ui import View, Button
from new_db import get_new_captures, increase_pokemon_iv


# Toutes les stats disponibles avec leur clé, label et couleur
STAT_OPTIONS = [
    {"key": "hp",               "label": "❤️ PV",               "color": discord.ButtonStyle.danger},
    {"key": "attack",           "label": "⚔️ Attaque",           "color": discord.ButtonStyle.primary},
    {"key": "special_attack",   "label": "✨ Attaque Spéciale",  "color": discord.ButtonStyle.primary},
    {"key": "defense",          "label": "🛡️ Défense",           "color": discord.ButtonStyle.success},
    {"key": "special_defense",  "label": "💠 Défense Spéciale",  "color": discord.ButtonStyle.success},
    {"key": "speed",            "label": "💨 Vitesse",           "color": discord.ButtonStyle.secondary},
]


# ─── Étape 2 : choix de la stat ───────────────────────────────────────────────

class BuffStatView(View):
    """Affiche les boutons de stats après qu'un Pokémon a été sélectionné."""

    def __init__(self, user_id, pokemon_name, iv_increase=4):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.pokemon_name = pokemon_name
        self.iv_increase = iv_increase

        for stat in STAT_OPTIONS:
            self.add_item(BuffStatButton(
                user_id=user_id,
                pokemon_name=pokemon_name,
                stat_key=stat["key"],
                stat_label=stat["label"],
                style=stat["color"],
                iv_increase=iv_increase,
            ))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class BuffStatButton(Button):
    def __init__(self, user_id, pokemon_name, stat_key, stat_label, style, iv_increase):
        super().__init__(label=stat_label, style=style)
        self.user_id = user_id
        self.pokemon_name = pokemon_name
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

        if success:
            stat_info = next(s for s in STAT_OPTIONS if s["key"] == self.stat_key)
            await interaction.followup.send(
                f"✅ **{self.pokemon_name}** a gagné **+{self.iv_increase} IV en {stat_info['label']}** !",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ Impossible de buff **{self.pokemon_name}** sur cette stat (IV déjà à 31 ?).",
                ephemeral=True
            )


# ─── Étape 1 : choix du Pokémon ───────────────────────────────────────────────

class BuffPokemonView(View):
    """Menu de sélection du Pokémon à buffer, paginé comme le Pokédex."""

    def __init__(self, user_id, pokemons, iv_increase=4):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.pokemons = pokemons
        self.iv_increase = iv_increase
        self.page = 0
        self.max_per_page = 23
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start = self.page * self.max_per_page
        end = start + self.max_per_page

        for name in self.pokemons[start:end]:
            self.add_item(BuffPokemonButton(name, self.user_id, self.iv_increase))

        if self.page > 0:
            self.add_item(BuffPrevButton(self))
        if end < len(self.pokemons):
            self.add_item(BuffNextButton(self))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class BuffPokemonButton(Button):
    def __init__(self, pokemon_name, user_id, iv_increase):
        super().__init__(label=pokemon_name, style=discord.ButtonStyle.primary)
        self.pokemon_name = pokemon_name
        self.user_id = user_id
        self.iv_increase = iv_increase

    async def callback(self, interaction: discord.Interaction):
        """Passe à l'étape 2 : choix de la stat."""
        view = BuffStatView(self.user_id, self.pokemon_name, self.iv_increase)
        embed = discord.Embed(
            title=f"💊 Buff IV — {self.pokemon_name}",
            description=f"Quelle stat veux-tu augmenter de **+{self.iv_increase}** ?",
            color=0xf39c12
        )
        await interaction.response.edit_message(embed=embed, view=view)


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