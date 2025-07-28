import discord
from discord.ui import View, Button

class AttackButton(Button):
    def __init__(self, attack_name):
        super().__init__(label=attack_name, style=discord.ButtonStyle.primary)
        self.attack_name = attack_name

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_attack = self.attack_name
        self.view.stop()
        await interaction.response.defer()

class AttackView(View):
    def __init__(self, attack_names):
        super().__init__(timeout=20)
        self.selected_attack = None
        for name in attack_names:
            self.add_item(AttackButton(name))
