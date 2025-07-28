import discord
from discord.ui import View, Button, Select


def create_team_selection_view(user, captures, on_done_callback):
    class TeamSelect(Select):
        def __init__(self, pokemons):
            options = [
                discord.SelectOption(label=p["name"], value=str(i)) for i, p in enumerate(pokemons)
            ]
            super().__init__(placeholder="Choisis 3 Pokémon", min_values=3, max_values=3, options=options)
            self.pokemons = pokemons

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != user:
                await interaction.response.send_message("Ce menu n'est pas pour toi !", ephemeral=True)
                return

            selected = [self.pokemons[int(i)] for i in self.values]
            await on_done_callback(user, selected)
            await interaction.message.delete()

    class TeamView(View):
        def __init__(self, pokemons):
            super().__init__(timeout=60)
            self.add_item(TeamSelect(pokemons))

    return TeamView(captures)


class BattleView(View):
    def __init__(self, user, state, on_attack_callback):
        super().__init__(timeout=30)
        self.user = user
        self.state = state
        self.on_attack_callback = on_attack_callback
        self.add_item(AttackButton("Attaque Rapide", on_attack_callback))
        self.add_item(AttackButton("Charge", on_attack_callback))


class AttackButton(Button):
    def __init__(self, label, callback_fn):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.callback_fn = callback_fn

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view.user:
            await interaction.response.send_message("Tu ne participes pas à ce combat.", ephemeral=True)
            return
        await self.callback_fn(interaction.user, self.label)
