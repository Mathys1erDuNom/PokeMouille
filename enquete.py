# enquete.py
import json
import os
import discord

ENQUETE_JSON_PATH = "json/enquete.json"

REGION_COMMANDS = {
    "park":   {"region": "Kanto", "item": "Corps Ramoloss"},
    "grotte": {"region": "Johto", "item": "nom_item_johto"},
    "marche": {"region": "Hoenn", "item": "nom_item_hoenn"},
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

def make_command(bot, command_name, required_region, item_name, get_user_region, add_item):
    @bot.command(name=command_name)
    async def _command(ctx):
        user_id = ctx.author.id
        region = get_user_region(user_id)

        if region != required_region:
            await ctx.send(
                f"❌ Cette commande n'est disponible que dans la région **{required_region}**. "
                f"Tu es actuellement dans : **{region or 'aucune région'}**."
            )
            return

        item_data = load_item(item_name)

        if item_data is None:
            await ctx.send(f"⚠️ L'item **{item_name}** est introuvable dans le fichier JSON.")
            return

        add_item(
            user_id=user_id,
            name=item_data["item_name"],
            quantity=1,
            rarity=item_data.get("rarity", "commun"),
            description=item_data.get("description", ""),
            image=item_data.get("image", ""),
            extra=item_data.get("extra", None),
            price=item_data.get("price", 0),
        )

        embed = discord.Embed(
            title=f"📦 {required_region} — !{command_name}",
            description=f"Tu as obtenu un **{item_data['item_name']}** !",
            color=discord.Color.green()
        )
        if item_data.get("description"):
            embed.add_field(name="Description", value=item_data["description"], inline=False)
        if item_data.get("image"):
            embed.set_image(url=item_data["image"])
        embed.set_footer(text=f"Trouvé par {ctx.author.display_name}")

        await ctx.send(embed=embed)

def setup_enquete(bot, get_user_region, add_item):
    for command_name, config in REGION_COMMANDS.items():
        make_command(
            bot=bot,
            command_name=command_name,
            required_region=config["region"],
            item_name=config["item"],
            get_user_region=get_user_region,
            add_item=add_item,
        )