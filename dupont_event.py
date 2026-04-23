import discord
from discord.ui import View, Button
import aiohttp
import asyncio
import random
import io

# ─── Tableaux de personnages ───────────────────────────────────────────────────

tableau_riche = [
    {
        "id": 0,
        "name": "Jean Dupont",
        "premier_texte": [
            "Bonjour, je suis Jean Dupont, un riche entrepreneur. J'ai plus d'argent qu'il ne m'en faut...",
            "La vie m'a bien souri. Peut-être un peu trop, d'ailleurs."
        ],
        "somme_prendre": 500,
        "texte_fin": [
            "Merci de m'avoir délésté de quelques billets, c'est pour la bonne cause !",
            "L'argent ne fait pas le bonheur... mais ça aide !"
        ],
        "adresse_image": "https://exemple.com/jean_riche.png"
    },
    {
        "id": 1,
        "name": "Marie Dupont",
        "premier_texte": [
            "Je suis Marie Dupont, héritière d'une grande fortune familiale.",
            "Mon coffre-fort déborde, autant en profiter !"
        ],
        "somme_prendre": 750,
        "texte_fin": [
            "Bien joué ! Cet argent sera mieux utilisé ailleurs.",
            "Je ne manquerai pas ces quelques billets, croyez-moi."
        ],
        "adresse_image": "https://exemple.com/marie_riche.png"
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
        "adresse_image": "https://exemple.com/pierre_pauvre.png"
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
        "adresse_image": "https://exemple.com/lucie_pauvre.png"
    }
]


# ─── Fonction principale ───────────────────────────────────────────────────────

async def run_interaction_personnage(channel: discord.TextChannel, riche_or_not: bool):
    """
    Lance une interaction avec un personnage aléatoire.

    :param channel:      Le salon Discord où envoyer les messages.
    :param riche_or_not: True  → personnage riche (on lui prend de l'argent)
                         False → personnage pauvre (on lui donne de l'argent)
    """

    tableau = tableau_riche if riche_or_not else tableau_pauvre

    # Choix aléatoire du personnage (id 0 à 3) et du texte (index 0 à 3 limité à la taille)
    personnage = tableau[random.randint(0, len(tableau) - 1)]
    index_premier_texte = random.randint(0, len(personnage["premier_texte"]) - 1)
    index_texte_fin     = random.randint(0, len(personnage["texte_fin"]) - 1)

    premier_texte = personnage["premier_texte"][index_premier_texte]
    texte_fin     = personnage["texte_fin"][index_texte_fin]
    image_url     = personnage["adresse_image"]

    if riche_or_not:
        somme   = personnage["somme_prendre"]
        label_bouton = f"💰 Prendre {somme} pièces"
    else:
        somme   = personnage["somme_don"]
        label_bouton = f"🤝 Donner {somme} pièces"

    # ── Envoi de l'image ──────────────────────────────────────────────────────
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    file = discord.File(fp=io.BytesIO(data), filename="personnage.png")
                    await channel.send(file=file)
                else:
                    await channel.send(f"*(image indisponible pour {personnage['name']})*")
    except Exception as e:
        print(f"[ERREUR IMAGE] {e}")
        await channel.send(f"*(image indisponible pour {personnage['name']})*")

    # ── Envoi du premier texte ────────────────────────────────────────────────
    await channel.send(f"**{personnage['name']}** : {premier_texte}")

    # ── Bouton d'interaction ──────────────────────────────────────────────────
    interaction_done = asyncio.Event()

    class ActionButton(Button):
        def __init__(self):
            super().__init__(label=label_bouton, style=discord.ButtonStyle.success)

        async def callback(self, interaction: discord.Interaction):
            # Désactive tous les boutons immédiatement
            for child in self.view.children:
                child.disabled = True
            await interaction.response.edit_message(view=self.view)

            # Affiche le texte de fin
            await channel.send(f"**{personnage['name']}** : {texte_fin}")
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
    view.message = await channel.send("Que faites-vous ?", view=view)

    # Attend que quelqu'un clique (ou que le timeout expire)
    await interaction_done.wait()