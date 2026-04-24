import discord
from discord.ui import View, Button
import aiohttp
import asyncio
import random
import io

from money_db import add_money, remove_money, get_balance



import os
script_dir = os.path.dirname(os.path.abspath(__file__))

# ─── Tableaux de personnages ───────────────────────────────────────────────────

tableau_riche = [
    {
        "id": 0,
        "name": "Jean Dupont",
        "premier_texte": [
            "Oh tu as l'air dans le besoin, tu me fais pitié. Moi grâce à mon traf..., mon commerce honorable et fructueux, je suis plein à l'as. Aller prends cette pièce et hors de ma vue.",
            "Mais non je te dis qu'il ne nous dérangera plus, je te le dis, il ne peut pas. Qu'est-ce que tu fais là ? Tu ne serais pas en train de m'espionner ? Prends ça, et ne t'avises pas de mettre ton nez dans mes affaires, ou tu en subiras les conséquences.",
            "Tu as l'air désespéré et pathétique. Prends cet argent, et fiche le camp : je ne voudrais pas que mes clients pensent que je collabore avec des vauriens dans ton genre. Tu me fais penser à ces affreuses bestioles que mes clients collectionnent : pitoyables et sans aucune intelligence.",
            "Eh toi là, oui tu as l'air pauvre, tiens prends cette pièce, et dis bien que c'est moi qui te l'ai donnée, je dois remonter ma popularité. Par contre ne reste pas à côté de moi, tu me fais honte."


        ],
        "somme_prendre": 10,
        "texte_fin": [
            "",
            ""
        ],
        "adresse_image": "images/famille/homme.png"
    },
    {
        "id": 1,
        "name": "Marie Dupont",
        "premier_texte": [
            "Oh, bonjour toi. Tu as besoin d'argent ? Tiens, en voilà un peu, que je t'offre avec plaisir. Tu sais, il m'arrive de me sentir seule ici, mon mari est toujours très occupé... Heureusement que j'ai mes enfants !",
            "Oh que tu as l'air charmant ! Voilà une petite somme, garde-la et utilise-la judicieusement. Tu me fais beaucoup penser à mes enfants, tu sais. Je donnerais ma vie pour les protéger...",
            "Oh bonjour, qu'il est bon d'avoir de la compagnie. Je me sens un peu seule en ce moment, mon fils et son père n'arrêtent pas de se disputer, à propos de son activité... Il n'a jamais pu supporter ce que son père faisait. J'ai trouvé ce qu'il faisait à ces pauvres bêtes terrible au début, mais le bien de mes enfants passe au-dessus de tout le reste. J'ai bien peur que la vérité finisse par éclater au grand jour, et que mes enfants perdent tout ce qu'ils possèdent... Désolé de t'avoir dérangé, tiens, prends cet argent pour m'avoir écouté.",
            "Bonjour, qu'est-ce que vous êtes mignon, j'ai envie de vous faire un cadeau, tenez"
        ],
        "somme_prendre": 100,
        "texte_fin": [
            "",
            ""
        ],
        "adresse_image": "images/famille/femme.png"
    }
]

tableau_pauvre = [
    {
        "id": 0,
        "name": "Pierre Michu",
        "premier_texte": [
            "S'il vous plaît... je n'ai pas mangé depuis deux jours.",
            "Pierre Michu, ancien ouvrier, à la rue depuis six mois."
        ],
        "somme_don": 50,
        "texte_fin": [
            "Que Dieu vous bénisse... je vais pouvoir manger ce soir.",
            "Merci du fond du cœur, vous êtes une bonne personne."
        ],
        "adresse_image": "images/famille/homme.png"
    },
    {
        "id": 1,
        "name": "Lucie Bernard",
        "premier_texte": [
            "Excusez-moi... auriez-vous un peu de monnaie pour un café ?",
            "Je m'appelle Lucie, j'élève seule mes deux enfants."
        ],
        "somme_don": 30,
        "texte_fin": [
            "Mes enfants vont pouvoir avoir un repas chaud ce soir, merci !",
            "Vous ne savez pas à quel point ça compte pour nous."
        ],
        "adresse_image": "images/famille/femme.png"
    }
]


# ─── Fonction principale ───────────────────────────────────────────────────────

async def run_interaction_personnage(channel: discord.TextChannel, riche_or_not: bool):
    tableau = tableau_riche if riche_or_not else tableau_pauvre

    personnage          = tableau[random.randint(0, len(tableau) - 1)]
    index_premier_texte = random.randint(0, len(personnage["premier_texte"]) - 1)
    index_texte_fin     = random.randint(0, len(personnage["texte_fin"]) - 1)

    premier_texte = personnage["premier_texte"][index_premier_texte]
    texte_fin     = personnage["texte_fin"][index_texte_fin]
    image_url     = personnage["adresse_image"]

    if riche_or_not:
        somme        = personnage["somme_prendre"]
        label_bouton = f"💰 Prendre {somme} pièces"
    else:
        somme        = personnage["somme_don"]
        label_bouton = f"🤝 Donner {somme} pièces"

    # ── Image ─────────────────────────────────────────────────────────────────
  
    try:
        image_path = os.path.join(script_dir, personnage["adresse_image"])
        file = discord.File(fp=image_path, filename="personnage.png")
        await channel.send(file=file)
    except Exception as e:
        print(f"[ERREUR IMAGE] {e}")
        await channel.send(f"*(image indisponible pour {personnage['name']})*")

    # ── Premier texte ─────────────────────────────────────────────────────────
    await channel.send(f"**{personnage['name']}** : {premier_texte}")

    # ── Bouton ────────────────────────────────────────────────────────────────
    interaction_done = asyncio.Event()

    class ActionButton(Button):
        def __init__(self):
            super().__init__(label=label_bouton, style=discord.ButtonStyle.success)

  
        async def callback(self, interaction: discord.Interaction):
            for child in self.view.children:
                child.disabled = True
            await interaction.response.edit_message(view=self.view)

            if riche_or_not:
                # On prend l'argent du riche → on ajoute au joueur
                add_money(interaction.user.id, somme)
                new_balance = get_balance(interaction.user.id)
                await channel.send(f"**{personnage['name']}** : {texte_fin}")
                await channel.send(
                    f"💰 {interaction.user.mention} a pris **{somme:,}** Croco dollars à {personnage['name']} !\n"
                    f"🐊 Nouveau solde : **{new_balance:,}** Croco dollars."
                )
            else:
                # On donne au pauvre → on retire au joueur
                success = remove_money(interaction.user.id, somme)
                if not success:
                    balance = get_balance(interaction.user.id)
                    await channel.send(
                        f"❌ {interaction.user.mention} tu n'as pas assez de Croco dollars pour faire ce don !\n"
                        f"🐊 Solde actuel : **{balance:,}** Croco dollars."
                    )
                    interaction_done.set()
                    return
                new_balance = get_balance(interaction.user.id)
                await channel.send(f"**{personnage['name']}** : {texte_fin}")
                await channel.send(
                    f"🤝 {interaction.user.mention} a donné **{somme:,}** Croco dollars à {personnage['name']} !\n"
                    f"🐊 Nouveau solde : **{new_balance:,}** Croco dollars."
                )

            interaction_done.set()    
        











    class ActionView(View):
        def __init__(self):
            super().__init__(timeout=30)
            self.add_item(ActionButton())

        async def on_timeout(self):
            for child in self.children:
                child.disabled = True
            if self.message:
                try:
                    await self.message.edit(view=self)
                except Exception:
                    pass

    view = ActionView()
    #view.message = await channel.send("Que faites-vous ?", view=view)
    await interaction_done.wait()


# ─── Setup de la commande ──────────────────────────────────────────────────────

def setup_dupont_command(bot, authorized_user_id=None):

    @bot.command(name="event_dupont")
    async def event_dupont(ctx, type_event: str = None):
        """
        Lance un event Dupont manuellement.
        Usage : !event_dupont riche   →  personnage riche
                !event_dupont pauvre  →  personnage pauvre
                !event_dupont         →  choix aléatoire
        """
        if authorized_user_id is not None and ctx.author.id != authorized_user_id:
            await ctx.send("⛔ Tu n'as pas la permission d'utiliser cette commande.")
            return

        if type_event is None:
            riche_or_not = random.choice([True, False])
        elif type_event.lower() == "riche":
            riche_or_not = True
        elif type_event.lower() == "pauvre":
            riche_or_not = False
        else:
            await ctx.send("❌ Argument invalide. Utilise `riche`, `pauvre`, ou laisse vide pour un choix aléatoire.")
            return

        await run_interaction_personnage(ctx.channel, riche_or_not)

    # Expose run_interaction_personnage pour l'appeler depuis le main
    bot.run_interaction_personnage = run_interaction_personnage