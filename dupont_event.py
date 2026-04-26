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

'''
Père -> Jean Dupon
Mère Bienvellante -> Marie Dupont

Enfant A (n'aime pas les actions de son père = colère) -> Sophie Dupont

Enfant B (ne sait rien du trafic = ignorance) -> Serge Dupont

Enfant C (complice car son père le terrifie = peur) -> Anne Dupont

Enfant D (l'ainé, héritier de l'empire de son père, 
qui est lui aussi complice mais lui l'a choisi, car son père manipulateur lui a fait miroiter un avenir prospère grâce au trafic = naiveté)

'''

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
        "adresse_image": "images/famille/jean.png"
    },
    {
        "id": 1,
        "name": "Marie Dupont",
        "premier_texte": [
            "Oh, bonjour toi. Tu as besoin d'argent ? Tiens, en voilà un peu, que je t'offre avec plaisir. Tu sais, il m'arrive de me sentir seule ici, mon mari est toujours très occupé... Heureusement que j'ai mes enfants !",
            "Oh que tu as l'air charmant ! Voilà une petite somme, garde-la et utilise-la judicieusement. Tu me fais beaucoup penser à mes enfants, tu sais. Je donnerais ma vie pour les protéger...",
            "Oh bonjour, qu'il est bon d'avoir de la compagnie. Je me sens un peu seule en ce moment, ma fille et son père n'arrêtent pas de se disputer, à propos de son activité... Elle n'a jamais pu supporter ce que son père faisait. J'ai trouvé ce qu'il faisait à ces pauvres bêtes terrible au début, mais le bien de mes enfants passe au-dessus de tout le reste. J'ai bien peur que la vérité finisse par éclater au grand jour, et que mes enfants perdent tout ce qu'ils possèdent... Désolé de t'avoir dérangé, tiens, prends cet argent pour m'avoir écouté.",
            "Bonjour, qu'est-ce que vous êtes mignon, j'ai envie de vous faire un cadeau, tenez"
        ],
        "somme_prendre": 100,
        "texte_fin": [
            "",
            ""
        ],
        "adresse_image": "images/famille/marie.png"
    },
    {
        "id": 2,
        "name": "Sophie Dupont",
        "premier_texte": [
            "Je n'en reviens toujours pas de ce qu'il fait, il est tellement corrompu... J'aimerais avoir l'influence nécessaire pour faire cesser tout cela, mais seul je n'irais pas bien loin.... Tiens, prends cet argent, il est sale et je n'en veux pas. Peut-être qu'en échange, tu pourras m'aider, au moment venu...",
            "Oh tiens, bonjour. As-tu besoin d'argent ? Tiens, tu peux prendre un peu du mien. De toutes façons, je n'en veux pas, cela ne m'intéresse pas, je ne suis pas comme eux. Je veux simplement faire éclater la vérité et sauver ces pauvres créatures du sort qui les attend...",
            "Je suis sûr que c'est sa faute si Bernard a disparu, je ne peux pas encore le prouver mais j'en suis sûr. Ah tiens, je croyais être seul, je réfléchissais à voix haute, tant que tu es là, tu veux de l'argent ? Je n'en veux pas.",
            "Hey, j'ai une question, comment tu ferais pour dénoncer des choses dont personne n'est au courant et qui sont problématiques ? Mmmh, euh je me suis emporté, tiens prends cet argent, désolé de t'avoir dérangé"


        ],
        "somme_prendre": 60,
        "texte_fin": [
            "",
            ""
        ],
        "adresse_image": "images/famille/sophie.png"
    },
    {
        "id": 3,
        "name": "Serge Dupont",
        "premier_texte": [
            "Bonjour ! Mais qui es-tu ? As-tu besoin d'un coup de main ? Ma famille est riche grâce à mon père, qui mène un noble commerce avec le casino ! Mes deux frères aînés travaillent avec lui, mais mon autre frère a toujours été distant, et je n'ai jamais su pourquoi. Sûrement une petite querelle de famille ! Tu me parais sympathique, tiens, cadeau !",
            "Oh bonjour ! J'aime bien ta tête, tu as l'air d'une personne honnête et respectable. Des gens disent que mon père est un criminel, sans coeur. Je ne comprends pas pourquoi ces bruits courent. Père dit que ce sont des journalistes, et qu'il ne faut pas les écouter ! Tiens, prends cet argent, je n'en manque pas",
            "Bonjour, j'ai une question. C'est normal les engueulades dans une famille ?  Désolée, je suis un peu préoccupée, car mon frère et père se disputent encore à propos de ces animaux. Je ne sais pas trop de quoi ils parlent, à vrai dire. Ils vont sûrement se réconcilier bientôt ! Merci de m'avoir écouté, tiens !",
            "Bonjour, tu n'aurais pas vu un Ramoloss ? Je ne trouve plus mon Ramoloss et ça me fait peur. Père dit qu'il s'est enfui lors d'une balade et que ça ne servait à rien de le chercher, mais je veux le retrouver! Tu en as vu un ? Non... Tant pis merci quand même, tiens prends cet argent et si tu en vois un, essaye de me retrouver !"
        

        ],
        "somme_prendre": 50,
        "texte_fin": [
            "",
            ""
        ],
        "adresse_image": "images/famille/serge.png"
    },
    {
        "id": 4,
        "name": "Anne Dupont",
        "premier_texte": [
             "Ah, tiens, bonjour. Tu peux prendre cet argent, si tu veux, nous en avons beaucoup. Mais ne dis pas à Père que je te l'ai donné...",
             "Bonjour. Tu veux de l'argent ? C'est d'accord, en voici un peu, mais je ne suis pas d'humeur. J'ai encore entendu leurs cris, ces pauvres animaux... Les hommes de main de Père avaient mal fermé la porte de la pièce. C'était glaçant.... Enfin, oublie cela et ne le répète à personne, j'en ai déjà trop dit.",
             "Il l'a fait disparaître, c'est sûr, on n'a plus de nouvelles de lui, en même temps quelle idée d'essayer de lui mettre des bâtons dans les roues... Mince, je pensais être seul, tiens prends cet argent et ne répète rien à personne.",
             "Oui monsieur je sais que vous avez beaucoup perdu au casino, mais vous savez c'est le jeu et ça peut arriver dans tous les casinos, nous respectons toutes les règles. Ouf c'était moins une, il faut que je le contacte pour qu'il règle cette histoire. Mince je ne t'avais pas vu, tu sais quoi, prends cet argent et ne dis rien à personne de ce que tu as entendu."
        

        ],
        "somme_prendre": 30,
        "texte_fin": [
            "",
            ""
        ],
        "adresse_image": "images/famille/anne.png"
    }
]

tableau_pauvre = [
  
]


# ─── Fonction principale ───────────────────────────────────────────────────────

async def run_interaction_personnage(channel: discord.TextChannel, riche_or_not: bool):
    tableau = tableau_riche if riche_or_not else tableau_pauvre
    if not tableau:
        await channel.send("❌ Aucun personnage disponible pour ce type d'événement.")
        return

    personnage          = random.choice(tableau)
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
    view.message = await channel.send("", view=view)
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
            riche_or_not = True
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