import os
import discord
from discord.ext import commands
from utils import is_croco
from BDD.badge_db import get_user_badges
from new_db import copy_new_captures_table, clear_new_captures, restore_from_copie_new_captures
from BDD.badge_db import get_user_badges, remove_user_badge
from BDD.event_status_db import set_event_active, get_event_started_at
from datetime import datetime, timedelta
import pytz

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEZONE = pytz.timezone("Europe/Paris")
ROCKET_DURATION = timedelta(days=30)   # fenêtre de récupération
ROCKET_COOLDOWN = timedelta(days=60)   # délai minimum avant de rappeler Rocket


def rocket_cooldown_remaining():
    """Temps restant avant de pouvoir rappeler Rocket (None = disponible)."""
    started_at = get_event_started_at("rocket")
    if started_at is None:
        return None
    remaining = started_at + ROCKET_COOLDOWN - datetime.now(TIMEZONE)
    return remaining if remaining.total_seconds() > 0 else None


async def open_rocket_event(channel) -> bool:
    """Vide les captures, ouvre la fenêtre de 1 mois et envoie l'annonce.
    Refuse si Rocket a été lancé il y a moins de 2 mois."""
    remaining = rocket_cooldown_remaining()
    if remaining is not None:
        await channel.send(f"❌ Rocket ne peut pas être rappelé avant encore {remaining.days} jour(s).")
        return False

    # 1. Copie de la table
    copy_new_captures_table()

    # 2. Vidage de la table originale
    clear_new_captures()

    # 3. Fenêtre de récupération : 1 mois, puis le flag repasse à inactif tout seul
    set_event_active("rocket", True, ends_at=datetime.now(TIMEZONE) + ROCKET_DURATION)

    # 4. Annonce : image puis texte
    image_path = os.path.join(PROJECT_ROOT, "images", "giovanni.jpg")
    await channel.send(file=discord.File(image_path, filename="giovanni.jpg"))
    await channel.send(
        "Dresseurs, écoutez-moi attentivement.\n\n"
        "Vos Pokémon ont disparu.\n\n"
        "Inutile de les chercher. C’est moi qui les ai pris.\n\n"
        "La Team Rocket s’est emparée de vos précieux compagnons, "
        "et ils sont désormais sous notre contrôle.\n\n"
        "Vous voulez les récupérer ? Alors venez les chercher.\n\n"
        "Mes hommes sont dans la région Rocket.\n\n"
        "Affrontez-les, et prouvez que vous êtes capables de récupérer ce qui vous appartient.\n\n"
        "Mais ne vous méprenez pas… chaque membre de la Team Rocket "
        "que vous vaincrez vous rapprochera de moi.\n\n"
        "Et lorsque vous serez enfin face à moi… nous verrons si vous êtes "
        "réellement capables de récupérer vos Pokémon.\n\n"
        "À bientôt, dresseurs.\n\n"
        "— Giovanni"
    )
    return True


def setup_rocket(bot):

    is_croco()
    @bot.command(name="eventrocket")
    @commands.has_permissions(administrator=True)
    async def resetcaptures(ctx):
        """
        !eventrocket
        Copie new_captures dans copie_new_captures, vide new_captures, ouvre 1 mois de récupération.
        """
        await open_rocket_event(ctx.channel)


    @bot.command(name="restorerocket")
    async def restorecaptures(ctx):
        """
        !restorerocket
        Restaure uniquement les Pokémon du membre qui a exécuté la commande.
        """
        user_id = str(ctx.author.id)
        required_badges = {100}#, 101, 102, 103, 104, 105, 106, 107}
        user_badges = set(get_user_badges(user_id))

        if not required_badges.issubset(user_badges):
            badge_names = {
                "Jessie": 100,
                #"James": 101,
               # "Butch": 102,
               # "Cassidy": 103,
               # "Proton": 104,
               # "Ariana": 105,
               # "Archer": 106,
               # "Giovanni": 107,
            }
            missing_badges = [
                name for name, badge_id in badge_names.items()
                if badge_id not in user_badges
            ]
            await ctx.send(
                f"❌ Tu ne peux pas utiliser `!restorerocket` tant que tu n'as pas les machines "
                f"{', '.join(missing_badges)}."
            )
            return

        result = restore_from_copie_new_captures(user_id)

        # Suppression des badges requis après restauration
        for badge_id in required_badges:
            remove_user_badge(user_id, badge_id)

        await ctx.send(
            f"✅ Restauration terminée pour {ctx.author.mention} !\n"
            f"➕ {result['inserted']} Pokémon ajouté(s)\n"
            f"📈 {result['updated']} Pokémon déjà existants (IV augmentés de +4)\n"
            f"🎖️ Les machines Team Rocket ont été retirées."
        )
