# pokemon_display.py
import discord, io, os, requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from combat.utils import normalize_text

script_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = os.path.join(script_dir, "images")

async def send_pokemon_card(
    interaction: discord.Interaction,
    pokemon_name: str,
    is_shiny: bool,
    p_data: dict,
    type_sprites: dict,
    attack_type_map: dict,
    ephemeral=True
):
    display_name = pokemon_name + (" ✨" if is_shiny else "")

    type_ = p_data.get("type", [])
    if isinstance(type_, str):
        type_ = [type_]

    stats = p_data.get("stats_iv", p_data.get("stats", {}))
    ivs = p_data.get("ivs", {})
    attacks = p_data.get("attacks", [])

    width, height = 850, 600
    bg_path = os.path.join(images_dir, "fond_pokedex.png")

    image = Image.open(bg_path).convert("RGBA").resize((width, height))
    draw = ImageDraw.Draw(image)

    font_path = os.path.join(script_dir, "fonts", "DejaVuSans-Bold.ttf")
    font = ImageFont.truetype(font_path, 15)
    font_bold = ImageFont.truetype(font_path, 20)

    # --- Positions ---
    pos_nom_type = (90, 70)
    pos_ivs = (90, 270)
    pos_stats = (90, 420)
    pos_sprite = (520, 40)
    pos_attaques = (535, 340)

    # --- Nom ---
    x, y = pos_nom_type
    draw.text((x, y), display_name, font=font_bold, fill="black")
    y += 30

    # --- Types ---
    for t in type_:
        url = type_sprites.get(t.lower())
        if url:
            r = requests.get(url)
            icon = Image.open(BytesIO(r.content)).convert("RGBA").resize((70, 25))
            image.paste(icon, (x, y), icon)
            draw.text((x + 80, y), t.capitalize(), font=font, fill="black")
            y += 30

    # --- IVs ---
    x, y = pos_ivs
    draw.text((x, y), "IVs :", font=font_bold, fill="black")
    y += 25
    for line in [
        f"PV : {ivs.get('hp','?')}",
        f"Atk : {ivs.get('attack','?')} | AtkSpé : {ivs.get('special_attack','?')}",
        f"Def : {ivs.get('defense','?')} | DefSpé : {ivs.get('special_defense','?')} | Vit : {ivs.get('speed','?')}",
    ]:
        draw.text((x, y), line, font=font, fill="black")
        y += 22

    # --- Stats ---
    x, y = pos_stats
    draw.text((x, y), "Stats :", font=font_bold, fill="black")
    y += 25
    for k, v in stats.items():
        draw.text((x, y), f"{k.capitalize()} : {v}", font=font, fill="black")
        y += 20

    # --- Sprite ---
    if p_data.get("image"):
        r = requests.get(p_data["image"])
        sprite = Image.open(BytesIO(r.content)).convert("RGBA").resize((250, 250))
        image.paste(sprite, pos_sprite, sprite)

    # --- Attaques ---
    x, y = pos_attaques
    draw.text((x, y), "Attaques :", font=font_bold, fill="black")
    y += 30
    for atk in attacks:
        draw.text((x, y), atk, font=font, fill="black")
        y += 25

    # --- Envoi ---
    with io.BytesIO() as buffer:
        image.save(buffer, "PNG")
        buffer.seek(0)
        file = discord.File(buffer, filename="pokemon.png")

    embed = discord.Embed(title=display_name)
    embed.set_image(url="attachment://pokemon.png")

    await interaction.followup.send(
        file=file,
        embed=embed,
        ephemeral=ephemeral
    )
