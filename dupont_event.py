import discord
from discord.ui import View, Button
import aiohttp
import asyncio
import random
import io
from inventory_db import get_inventory, use_item
from money_db import add_money, remove_money, get_balance

from discord.ui import View, Button, Select

import os
script_dir = os.path.dirname(os.path.abspath(__file__))

# ─── Tableaux de personnages ───────────────────────────────────────────────────

'''
Père -> Jean Dupon
Mère Bienvellante -> Marie Dupont

Enfant A (n'aime pas les actions de son père = colère) -> Sophie Dupont

Enfant B (ne sait rien du trafic = ignorance) -> Serge Dupont

Enfant C (complice car son père le terrifie = peur) -> Anne Dupont

Enfant D (l'ainé, héritier de l'empire de son père, -> Bernard Dupong
qui est lui aussi complice mais lui l'a choisi, car son père manipulateur lui a fait miroiter un avenir prospère grâce au trafic = naiveté)
'''


#Sophie
#  "Je n'en reviens toujours pas de ce qu'il fait, il est tellement corrompu... J'aimerais avoir l'influence nécessaire pour faire cesser tout cela, mais seul je n'irais pas bien loin... Peut-être avec la police ? (!police) Tiens, prends cet argent, il est sale et je n'en veux pas.",

#Anne
 #   "Il l'a fait disparaître, c'est sûr, on n'a plus de nouvelles de lui... En même temps, quelle idée d'essayer de lui mettre des bâtons dans les roues. J'ai entendu dire qu'il avait fui vers Sinnoh, qu'il se cachait quelque part dans une grotte (!grotte) froide et sombre. Il aurait laissé quelque chose derrière lui là-bas... Mince, je pensais être seule, tiens prends cet argent et ne répète rien à personne."
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
    
            "Oh tiens, bonjour. As-tu besoin d'argent ? Tiens, tu peux prendre un peu du mien. De toutes façons, je n'en veux pas, cela ne m'intéresse pas, je ne suis pas comme eux. Je veux simplement faire éclater la vérité et sauver ces pauvres créatures du sort qui les attend...",
            "Je suis sûr que c'est sa faute si Joseph a disparu, je ne peux pas encore le prouver mais j'en suis sûr. Ah tiens, je croyais être seul, je réfléchissais à voix haute, tant que tu es là, tu veux de l'argent ? Je n'en veux pas.",
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
            "Bonjour ! Mais qui es-tu ? As-tu besoin d'un coup de main ? Ma famille est riche grâce à mon père, qui mène un noble commerce avec le casino ! Mon frère aîné travaille avec lui, mais mon autre soeur a toujours été distant, et je n'ai jamais su pourquoi. Sûrement une petite querelle de famille ! Tu me parais sympathique, tiens, cadeau !",
            "Oh bonjour ! J'aime bien ta tête, tu as l'air d'une personne honnête et respectable. Des gens disent que mon père est un criminel, sans coeur. Je ne comprends pas pourquoi ces bruits courent. Père dit que ce sont des journalistes, et qu'il ne faut pas les écouter ! Tiens, prends cet argent, je n'en manque pas",
            "Bonjour, j'ai une question. C'est normal les engueulades dans une famille ?  Désolée, je suis un peu préoccupée, car ma soeur et père se disputent encore à propos de ces animaux. Je ne sais pas trop de quoi ils parlent, à vrai dire. Ils vont sûrement se réconcilier bientôt ! Merci de m'avoir écouté, tiens !",
            "Bonjour, tu n'aurais pas vu un Ramoloss ? Je ne trouve plus mon Ramoloss et ça me fait peur. Père dit qu'il s'est enfui lors d'une balade... mais je veux le retrouver ! On m'a dit qu'il y avait un parc dans la région de Kanto où on pouvait retrouver des Pokémon perdus... Si tu y vas un jour, tu pourrais peut-être demander aux gardes du parc (!parc) s'ils n'ont rien trouvé ? Tu en as vu un ? Non... Tant pis merci quand même, tiens prends cet argent !"
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
        
             "Oui monsieur je sais que vous avez beaucoup perdu au casino, mais vous savez c'est le jeu et ça peut arriver dans tous les casinos, nous respectons toutes les règles. Ouf c'était moins une, il faut que je le contacte pour qu'il règle cette histoire. Mince je ne t'avais pas vu, tu sais quoi, prends cet argent et ne dis rien à personne de ce que tu as entendu."
        

        ],
        "somme_prendre": 30,
        "texte_fin": [
            "",
            ""
        ],
        "adresse_image": "images/famille/anne.png"
    },
    {
        "id": 5,
        "name": "Bernard Dupont",
        "premier_texte": [
           "Il s'est chargé de lui, une bonne chose de faite, de nos jours les gens fouinent dans les affaires des autres, quel irrespect. Heureusement que personne ne sait pour l'entrepôt (!entrepot) d'Unys... Oh excuse-moi, je ne t'avais pas vu, tiens prends cet argent, et oublie ce que tu viens d'entendre."
            "Oh, bonjour ! Prends donc un peu d'argent. J'ai de plus en plus de responsabilités dans l'entreprise de Père, mon avenir prospère s'approche à grands pas ! Tout se passe exactement comme nous l'avons prévu, avec Père.",
            "Bonjour. Ah, oui, tiens, prends ton argent. Au fait, as-tu vu ma soeur ? Père était dans une fureur monstrueuse après leur discussion. Cette petite écervelée n'a pas intérêt à mettre le nez dans nos affaires, à Père et moi. Et toi non plus, d'ailleurs.",
            "Prendre le Pokémon du petit n'était peut-être pas la meilleure des idées, mais sa queue rapporte tellement. Hein quoi, qu'est-ce que tu fais là ? Tu m'espionnais ? Ok on va faire quelque chose, prends ça et ne dis rien à personne"

         
        ],
        "somme_prendre": 20,
        "texte_fin": [
            "",
            ""
        ],
        "adresse_image": "images/famille/bernard.png"
    }
]

tableau_pauvre = [
    {
        "id": 1,
        "name": "Marie Dupont",
        "premier_texte": [

            "Bonjour, excusez-moi de vous déranger, après l'arrestation de mon mari et de notre fils, nous avons tout perdu, nous n'avons plus rien et je dois nourrir mes enfants, pourriez-vous me donner un peu d'argent ou de la nourriture si vous en avez ?",
            "Bonjour, non ça ne va pas du tout. J'étais au courant qu'il y avait des choses louches dans ce que faisaient mon mari, j'aurais sûrement dû agir ou lui parler... J'étais aveuglé par la sécurité que cela apportait à notre famille. Nos enfants ne manquaient de rien. Aujourd'hui je n'arrive plus à les nourrir... Auriez-vous de la nourriture ou un peu d'argent ?",
            "Je sais que ce que faisait mon mari était mal... Mais pourquoi nos enfants devraient souffrir de ces actions ?? Cela m'attriste d'autant plus qu'un de mes fils soit lui aussi en prison. Je sais bien que leur commerce était illégal, mais je ne peux m'empêcher de ressentir de la haine contre la personne qui les a dénoncés, même si malheureusement je ne sais pas qui est cette personne."
         
        ],
        "somme_don": 50,
        "texte_fin": [
            "",
            ""
        ],
        "adresse_image": "images/famille/pauvre/marie.png"
    },

    {
        "id": 2,
        "name": "Sophie Dupont",
        "premier_texte": [

            "Tous les crimes de mon père ont été découverts... Même si c'était ce que je voulais, je ne m'attendais pas à ce que mon frère finisse aussi sous les barreaux... Il était sous l'influence de notre père, c'est injuste... Je sais que je ne voulais pas de l'argent sale de mon père, mais c'est vraiment dur de voir ma mère, elle est si triste. À vrai dire, nous n'avons plus rien et nous avons du mal à trouver à manger... Aurait-tu par hasard de la nourriture ou un peu d'argent ?",
            "Hahahaha, je meurs de faim. Sans l'argent sale de mon père, ma famille et moi n'avons plus rien... Je n'avais pas réalisé que nous étions si dépendants de lui... Tu aurais quelque chose qui pourrait aider ma famille ?"

        ],
        "somme_don": 100,
        "texte_fin": [
             "",
            ""
        ],
        "adresse_image": "images/famille/pauvre/sophie.png"
    },
       {
        "id": 3,
        "name": "Anne Dupont",
        "premier_texte": [
            "Ma famille et moi n'avons plus rien, par pitié aidez-nous !",
            "Je ne sais pas où nous allons dormir ce soir. Nous mourrons de faim avec ma famille. Après l'arrestation de mon père et de mon frère, nous avons tous perdu. S'il te plaît, aurais-tu quelque chose qui pourrait aider ma famille ?"

        
        ],
        "somme_don": 60,
        "texte_fin": [
            "",
            ""
        ],
        "adresse_image": "images/famille/pauvre/anne.png"
    },

       {
        "id": 4,
        "name": "Serge Dupont",
        "premier_texte": [
             "C'est une injustice, mon père et mon frère sont en prison ! Ils sont accusés de choses qu'ils n'ont pas commises, c'est une honte. Maintenant, nous sommes devenus pauvres avec ma famille, nous n'avons plus à manger, tu aurais quelque chose qui pourrait nous aider ?",
             "Je suis tellement énervé, j'aimerais retrouver celui qui a pu mentir à la police ! Comment mon père et mon frère pourraient-ils être coupables de cela ! Ils travaillaient dur au casino. Père gagnait sa vie honnêtement et maintenant nous avons tout perdu, qui a osé nous faire ça ???? Ma famille et moi n'avons rien à manger, pourrais-tu nous aider ?"
         

        
        ],
        "somme_don": 30,
        "texte_fin": [
             "",
            ""
           
        ],
        "adresse_image": "images/famille/pauvre/serge.png"
    }
  
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

    somme        = personnage["somme_prendre"] if riche_or_not else personnage["somme_don"]
    label_bouton = f"💰 Prendre {somme} pièces" if riche_or_not else f"🤝 Donner {somme} pièces"

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

    # ── Vue ───────────────────────────────────────────────────────────────────
    interaction_done = asyncio.Event()

    # ════════════════════════════════════════════════════════════════════════
    # CAS RICHE : un seul bouton
    # ════════════════════════════════════════════════════════════════════════
    if riche_or_not:

        class RicheButton(Button):
            def __init__(self):
                super().__init__(label=label_bouton, style=discord.ButtonStyle.success)

            async def callback(self, interaction: discord.Interaction):
                for child in self.view.children:
                    child.disabled = True
                await interaction.response.edit_message(view=self.view)

                add_money(interaction.user.id, somme)
                new_balance = get_balance(interaction.user.id)
                await channel.send(f"**{personnage['name']}** : {texte_fin}")
                await channel.send(
                    f"💰 {interaction.user.mention} a pris **{somme:,}** Croco dollars à {personnage['name']} !\n"
                    f"🐊 Nouveau solde : **{new_balance:,}** Croco dollars."
                )
                interaction_done.set()

        class RicheView(View):
            def __init__(self):
                super().__init__(timeout=600)
                self.add_item(RicheButton())

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                if self.message:
                    try:
                        await self.message.edit(view=self)
                    except Exception:
                        pass

        view = RicheView()
        view.message = await channel.send("", view=view)

    # ════════════════════════════════════════════════════════════════════════
    # CAS PAUVRE : deux boutons → argent ou baie
    # ════════════════════════════════════════════════════════════════════════
    else:

        class ItemSelectView(View):
            def __init__(self, baies: list, original_interaction: discord.Interaction):
                super().__init__(timeout=120)
                self.original_interaction = original_interaction

                options = [
                    discord.SelectOption(
                        label=item["name"][:100],
                        description=f"Quantité : {item['quantity']}  •  {item['rarity']}",
                        value=item["name"],
                    )
                    for item in baies[:25]
                ]

                select = Select(
                    placeholder="Choisis une baie à donner…",
                    options=options,
                    min_values=1,
                    max_values=1,
                )
                select.callback = self.select_callback
                self.add_item(select)

            async def select_callback(self, interaction: discord.Interaction):
                if interaction.user.id != self.original_interaction.user.id:
                    await interaction.response.send_message(
                        "❌ Ce n'est pas ton interaction !", ephemeral=True
                    )
                    return

                chosen_item = interaction.data["values"][0]
                new_qty, _ = use_item(interaction.user.id, chosen_item, quantity=1)

                if new_qty is None:
                    await interaction.response.send_message(
                        f"❌ Tu ne possèdes pas **{chosen_item}** dans ton inventaire.",
                        ephemeral=True,
                    )
                    return

                for child in self.children:
                    child.disabled = True
                await interaction.response.edit_message(view=self)

                await channel.send(f"**{personnage['name']}** : {texte_fin}")
                await channel.send(
                    f"🫐 {interaction.user.mention} a donné **{chosen_item}** à {personnage['name']} !\n"
                    f"📦 Quantité restante : **{new_qty}**."
                )
                interaction_done.set()

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True

        class PauvreView(View):
            def __init__(self):
                super().__init__(timeout=600)

                btn_argent = Button(
                    label=label_bouton,
                    style=discord.ButtonStyle.success,
                    custom_id="btn_argent",
                )
                btn_argent.callback = self.argent_callback
                self.add_item(btn_argent)

                btn_item = Button(
                    label="🫐 Donner une baie",
                    style=discord.ButtonStyle.primary,
                    custom_id="btn_item",
                )
                btn_item.callback = self.item_callback
                self.add_item(btn_item)

            def _disable_all(self):
                for child in self.children:
                    child.disabled = True

            async def argent_callback(self, interaction: discord.Interaction):
                self._disable_all()
                await interaction.response.edit_message(view=self)

                success = remove_money(interaction.user.id, somme)
                if not success:
                    balance = get_balance(interaction.user.id)
                    await channel.send(
                        f"❌ {interaction.user.mention} tu n'as pas assez de Croco dollars !\n"
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

            async def item_callback(self, interaction: discord.Interaction):
                # Filtre uniquement les items dont le nom commence par "Baie"
                all_items = get_inventory(interaction.user.id)
                baies = [item for item in all_items if item["name"].startswith("Baie")]

                if not baies:
                    await interaction.response.send_message(
                        "❌ Tu n'as aucune baie à donner… Mais tu peux toujours faire un don en Croco dollars ! 🐊",
                        ephemeral=True,
                    )
                    return  # Les boutons restent actifs

                self._disable_all()
                await interaction.response.edit_message(view=self)

                item_view = ItemSelectView(baies, interaction)
                await channel.send(
                    f"🫐 {interaction.user.mention}, choisis la baie que tu veux donner à **{personnage['name']}** :",
                    view=item_view,
                )

                await item_view.wait()
                if not interaction_done.is_set():
                    await channel.send(f"⏰ Temps écoulé, {interaction.user.mention} n'a rien donné.")
                    interaction_done.set()

            async def on_timeout(self):
                self._disable_all()
                if self.message:
                    try:
                        await self.message.edit(view=self)
                    except Exception:
                        pass

        view = PauvreView()
        view.message = await channel.send("", view=view)

    await interaction_done.wait()


# ─── Setup de la commande ──────────────────────────────────────────────────────

def setup_dupont_command(bot, authorized_user_id=None):

    @bot.command(name="event_dupont")
    async def event_dupont(ctx, type_event: str = None):
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
            await ctx.send("❌ Argument invalide. Utilise `riche`, `pauvre`, ou laisse vide.")
            return

        await run_interaction_personnage(ctx.channel, riche_or_not)

    bot.run_interaction_personnage = run_interaction_personnage