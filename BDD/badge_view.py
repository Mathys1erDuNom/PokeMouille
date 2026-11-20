import discord
from discord.ext import commands
from discord.ui import View, Button
from PIL import Image
import io, os, requests, json
from BDD.badge_db import give_badge, get_user_badges
from utils import is_croco

# Base pour chemins : racine du projet (deux niveaux au-dessus de ce fichier)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
images_dir = os.path.join(PROJECT_ROOT, "images")  # dossier images à la racine

# --- Cache ---
BADGE_CACHE = {}  # { user_id: { "mosaic": bytes, "badge_ids": [] } }

# --- Buttons ---
class BadgeInfoButton(Button):
    def __init__(self, badge):
        super().__init__(label=badge["name"], style=discord.ButtonStyle.primary)
        self.badge = badge

    async def callback(self, interaction: discord.Interaction):
        # Ouvre l'image locale (depuis la racine du projet)
        img_path = os.path.join(PROJECT_ROOT, self.badge["image"]) 
        file = discord.File(img_path, filename="badge.png")

        embed = discord.Embed(
            title=self.badge["name"],
            description=self.badge["description"],
            color=0xFFD700
        )
        # On référence l'image jointe
        embed.set_image(url="attachment://badge.png")

        await interaction.response.send_message(embed=embed, file=file, ephemeral=True)


async def create_badge_mosaic(badges):
    images = []
    nb_ignores = 0

    for badge in badges:
        try:
            # Nouveau chemin vers l'image locale (depuis la racine du projet)
            img_path = os.path.join(PROJECT_ROOT, badge["image"])
            img = Image.open(img_path).convert("RGBA").resize((64,64))
            images.append(img)
        except Exception as e:
            print(f"[IGNORÉ] Badge {badge['name']} : {e}")
            try:
                fallback_path = os.path.join(images_dir, "default.png")
                fallback = Image.open(fallback_path).convert("RGBA").resize((64,64))
                images.append(fallback)
            except Exception as e2:
                print(f"[ERREUR] Image par défaut manquante : {e2}")
                nb_ignores += 1

    if not images:
        return None, 0

    cols = 5
    rows = (len(images) + cols - 1) // cols
    mosaic = Image.new("RGBA", (cols*64, rows*64), (255,255,255,0))
    for i, img in enumerate(images):
        x = (i % cols) * 64
        y = (i // cols) * 64
        mosaic.paste(img, (x, y), img)

    output = io.BytesIO()
    mosaic.save(output, "PNG")
    output.seek(0)
    return output, len(images)



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

    # !badge désactivé : géré par un autre projet (remettre @bot.command() pour réactiver)
    async def badge(ctx, generation: int = None):
        user_id = str(ctx.author.id)
        user_badge_ids = get_user_badges(user_id)
        user_badges = [b for b in full_badge_data if b["id"] in user_badge_ids]

        if generation:
            user_badges = [b for b in user_badges if b["generation"] == generation]

        if not user_badges:
            await ctx.send("Tu n'as aucun badge dans cette sélection.")
            return

        # ----- Vérification cache -----
        cache = BADGE_CACHE.get(user_id)
        badge_ids = [b["id"] for b in user_badges]

        if cache and cache["badge_ids"] == badge_ids:
            mosaic_img = io.BytesIO(cache["mosaic"])
            mosaic_img.seek(0)
            print(f"[CACHE] Badge mosaic envoyé depuis le cache pour {ctx.author.display_name}")
        else:
            mosaic_img, displayed_count = await create_badge_mosaic(user_badges)
            if mosaic_img is None:
                await ctx.send("Erreur lors de la création de la mosaïque.")
                return
            BADGE_CACHE[user_id] = {"badge_ids": badge_ids, "mosaic": mosaic_img.getvalue()}

        file = discord.File(mosaic_img, filename="badge_mosaic.png")
        embed = discord.Embed(
            title=f"🏅 Badges de {ctx.author.display_name}",
            description=f"Mosaïque de {len(user_badges)} badges",
            color=0xFFD700
        )
        embed.set_image(url="attachment://badge_mosaic.png")

        view = View()
        for b in user_badges:
            view.add_item(BadgeInfoButton(b))

        await ctx.send(embed=embed, file=file, view=view)
