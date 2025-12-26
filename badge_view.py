# badge_view.py
import discord
from discord.ext import commands
from discord.ui import View, Button
from PIL import Image
import io, os, requests, json
from badge_db import give_badge, get_user_badges
from utils import is_croco

script_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = os.path.join(script_dir, "json")  # dossier pour fallback si image introuvable

# --- Cache ---
BADGE_CACHE = {}  # { user_id: { "mosaic": bytes, "badge_ids": [] } }

# --- Buttons ---
class BadgeInfoButton(Button):
    def __init__(self, badge):
        super().__init__(label=badge["name"], style=discord.ButtonStyle.primary)
        self.badge = badge

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=self.badge["name"],
            description=self.badge["description"],
            color=0xFFD700
        )
        embed.set_image(url=self.badge["image"])
        await interaction.response.send_message(embed=embed, ephemeral=True)




async def create_badge_mosaic(badges):
    images = []
    for badge in badges:
        try:
            resp = requests.get(badge["image"], stream=True)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGBA").resize((64,64))
            images.append(img)
        except Exception as e:
            print(f"Erreur image {badge['name']}: {e}")
            fallback = Image.new("RGBA", (64,64), (200,200,200,255))
            images.append(fallback)

    if not images:
        return None

    cols = 5
    rows = (len(images) + cols - 1) // cols
    mosaic = Image.new("RGBA", (cols*64, rows*64), (255,255,255,0))  # fond transparent

    for i, img in enumerate(images):
        x = (i % cols) * 64
        y = (i // cols) * 64
        mosaic.paste(img, (x, y), img)  # utiliser le masque pour la transparence

    mosaic = mosaic.convert("RGB")  # Discord préfère RGB

    output = io.BytesIO()
    mosaic.save(output, "PNG")
    output.seek(0)
    return output



# --- Setup du module ---
def setup_badges(bot, full_badge_data):
    @is_croco()
    @bot.command()
    async def givebadge(ctx, badge_id: int, user: discord.Member = None):
        """Attribue un badge à un utilisateur"""
        user = user or ctx.author
        badge = next((b for b in full_badge_data if b["id"] == badge_id), None)
        if not badge:
            await ctx.send("❌ Badge introuvable.")
            return
        if give_badge(user.id, badge_id):
            await ctx.send(f"✅ Badge **{badge['name']}** attribué à {user.display_name}.")
        else:
            await ctx.send("❌ Impossible d'attribuer le badge.")

    @bot.command()
    async def badge(ctx, generation: int = None):
        """Affiche tous les badges de l'utilisateur"""
        user_id = str(ctx.author.id)
        user_badge_ids = get_user_badges(user_id)
        user_badges = [b for b in full_badge_data if b["id"] in user_badge_ids]

        if generation:
            user_badges = [b for b in user_badges if b["generation"] == generation]

        if not user_badges:
            await ctx.send("Tu n'as aucun badge dans cette sélection.")
            return

        # Vérification cache
        cache = BADGE_CACHE.get(user_id)
        badge_ids = [b["id"] for b in user_badges]
        if cache and cache["badge_ids"] == badge_ids:
            mosaic_img = io.BytesIO(cache["mosaic"])
        else:
            mosaic_img = await create_badge_mosaic(user_badges)
            BADGE_CACHE[user_id] = {"badge_ids": badge_ids, "mosaic": mosaic_img.getvalue()}

        file = discord.File(mosaic_img, filename="badge_mosaic.png")
        embed = discord.Embed(title=f"🏅 Badges de {ctx.author.display_name}", color=0xFFD700)
        embed.set_image(url="attachment://badge_mosaic.png")

        view = View()
        for b in user_badges:
            view.add_item(BadgeInfoButton(b))

        await ctx.send(embed=embed, file=file, view=view)
