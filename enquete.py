import json
import os
import discord
from preuve_db import add_preuve, has_preuve, get_preuves, init_preuves_db

script_dir = os.path.dirname(os.path.abspath(__file__))
ENQUETE_JSON_PATH = os.path.join(script_dir, "json", "enquete.json")
images_dir = os.path.join(script_dir, "images", "enquete")

REGION_COMMANDS = {
    "parc":     {"region": "Kanto",  "item": "Corps Ramoloss"},
    "grotte":   {"region": "Sinnoh", "item": "Veste avec une lettre"},
    "entrepot": {"region": "Unys",   "item": "Livre de comptes falsifiés"},
}

def load_item(item_name):
    if not os.path.exists(ENQUETE_JSON_PATH):
        return None
    with open(ENQUETE_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return next(
        (item for item in data if item["item_name"].lower() == item_name.lower()),
        None
    )

def make_command(bot, command_name, required_region, item_name, get_user_region):
    @bot.command(name=command_name)
    async def _command(ctx):
        user_id = ctx.author.id
        region = get_user_region(user_id)

        if region != required_region:
            await ctx.send(
                f"❌ Cette commande n'est pas disponible dans cette région. "
                f"Tu es actuellement dans : **{region or 'aucune région'}**."
            )
            return

        if has_preuve(user_id, item_name):
            await ctx.send("🔍 Tu as déjà fouillé ici... il n'y a plus rien à trouver.")
            return

        item_data = load_item(item_name)
        if item_data is None:
            await ctx.send(f"⚠️ L'item **{item_name}** est introuvable dans le fichier JSON.")
            return

        add_preuve(
            user_id=user_id,
            item_name=item_data["item_name"],
            region=required_region,
            description=item_data.get("description", ""),
            image=item_data.get("image", ""),
        )

        embed = discord.Embed(
            title=f"🔎 {required_region} — !{command_name}",
            description=f"Tu as trouvé une preuve : **{item_data['item_name']}** !",
            color=discord.Color.green()
        )
        if item_data.get("description"):
            embed.add_field(name="Description", value=item_data["description"], inline=False)
        embed.set_footer(text=f"Trouvé par {ctx.author.display_name}")

        image_filename = item_data.get("image", "")
        if image_filename:
            image_path = os.path.join(images_dir, image_filename)
            if os.path.exists(image_path):
                file = discord.File(image_path, filename=image_filename)
                embed.set_image(url=f"attachment://{image_filename}")
                await ctx.send(embed=embed, file=file)
                return

        await ctx.send(embed=embed)


class PreuvesView(discord.ui.View):
    def __init__(self, author, liste):
        super().__init__(timeout=120)
        self.author = author
        self.liste = liste
        self.index = 0

    def make_embed(self):
        p = self.liste[self.index]
        embed = discord.Embed(
            title=f"🔎 {p['item_name']} — {p['region']}",
            description=p["description"] or "Aucune description.",
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Preuve {self.index + 1}/{len(self.liste)}")

        file = None
        image_filename = p.get("image", "")
        if image_filename:
            image_path = os.path.join(images_dir, image_filename)
            if os.path.exists(image_path):
                file = discord.File(image_path, filename=image_filename)
                embed.set_image(url=f"attachment://{image_filename}")

        return embed, file

    async def update(self, interaction):
        embed, file = self.make_embed()
        if file:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        else:
            await interaction.response.edit_message(embed=embed, attachments=[], view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Ce n'est pas ton carnet.", ephemeral=True)
            return
        self.index = (self.index - 1) % len(self.liste)
        await self.update(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Ce n'est pas ton carnet.", ephemeral=True)
            return
        self.index = (self.index + 1) % len(self.liste)
        await self.update(interaction)


def setup_enquete(bot, get_user_region):
    init_preuves_db()

    for command_name, config in REGION_COMMANDS.items():
        make_command(
            bot=bot,
            command_name=command_name,
            required_region=config["region"],
            item_name=config["item"],
            get_user_region=get_user_region,
        )

    @bot.command(name="preuves")
    async def preuves(ctx):
        liste = get_preuves(ctx.author.id)
        if not liste:
            await ctx.send("🗂️ Tu n'as encore trouvé aucune preuve.")
            return
        view = PreuvesView(ctx.author, liste)
        embed, file = view.make_embed()
        await ctx.send(embed=embed, file=file, view=view)