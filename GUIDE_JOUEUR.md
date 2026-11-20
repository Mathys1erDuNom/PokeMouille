# Guide du joueur — PokeMouille

Tout ce que tu peux faire avec le bot. Toutes les commandes commencent par `!`.

## Sommaire

1. [Bien démarrer](#1-bien-démarrer)
2. [Capturer des Pokémon](#2-capturer-des-pokémon)
3. [Les événements automatiques](#3-les-événements-automatiques)
4. [Climat, jour et nuit](#4-climat-jour-et-nuit)
5. [Ta collection](#5-ta-collection)
6. [Combats et badges](#6-combats-et-badges)
7. [XP, évolution et chenil](#7-xp-évolution-et-chenil)
8. [La pêche](#8-la-pêche)
9. [Argent, boutique et inventaire](#9-argent-boutique-et-inventaire)
10. [Le casino](#10-le-casino)
11. [Les actus et l'exploration](#11-les-actus-et-lexploration)
12. [L'enquête sur la famille Dupont](#12-lenquête-sur-la-famille-dupont)
13. [Les raids](#13-les-raids)
14. [L'événement Team Rocket](#14-lévénement-team-rocket)
15. [Récapitulatif des commandes](#15-récapitulatif-des-commandes)

---

## 1. Bien démarrer

- **Rejoins le salon vocal du jeu.** Presque tout en dépend : les événements ne se lancent que s'il y a quelqu'un en vocal, et il faut y être pour capturer, pêcher ou faire gagner de l'XP à ton chenil.
- **Ouvre tes messages privés.** Le bot t'écrit en MP pour les apparitions privées, la pêche et l'exploration.
- **Choisis ta région avec `!region`** : Kanto, Johto, Hoenn, Sinnoh, Unys ou Rocket. Tu peux en changer quand tu veux.

Ta région détermine :

| Ce qui change | Effet de la région |
|---|---|
| Apparitions en MP | Les Pokémon viennent de ta région |
| Pêche | Les Pokémon Eau pêchés viennent de ta région |
| Combats | Les adversaires proposés sont ceux de ta région |
| Enquête et exploration | Certains lieux ne sont accessibles que depuis une région précise |

---

## 2. Capturer des Pokémon

### Sur le serveur : `!catch`

Quand un Pokémon apparaît dans le salon du jeu, tape `!catch`.

- Tu dois être dans le salon vocal et écrire dans le salon texte du jeu.
- Le bot lance une Pokéball : **3 chances sur 4** de réussir.
- En cas d'échec, le Pokémon s'échappe de la Ball et tu dois attendre **10 secondes** avant de retenter.
- Si le Pokémon est réservé à un joueur (après un quiz gagné par exemple), lui seul peut le capturer.
- Chance d'obtenir un shiny : 1 sur 64.

### En message privé : `!capture`

Tant que tu restes dans le salon vocal, un Pokémon de ta région apparaît dans tes MP **toutes les 4 à 5 heures**.

- Tape `!capture` dans la conversation privée avec le bot.
- La capture réussit à tous les coups.
- Chance d'obtenir un shiny : 1 sur 32.
- Si tu quittes le vocal, le compteur est annulé.

### Les IV

Chaque Pokémon capturé reçoit des IV aléatoires de 0 à 31 dans chaque statistique (PV, Attaque, Défense, Attaque Spé, Défense Spé, Vitesse). Ils s'ajoutent à ses stats de base : deux Pokémon de la même espèce n'ont donc pas la même force.

### Les autres façons d'obtenir un Pokémon

| Moyen | Détails |
|---|---|
| Balls de la boutique | Chaque Ball utilisée te donne directement un Pokémon ([section 9](#9-argent-boutique-et-inventaire)) |
| Pêche | Pokémon de type Eau ([section 8](#8-la-pêche)) |
| Exploration | Pokémon propres à chaque lieu ([section 11](#11-les-actus-et-lexploration)) |
| Œuf du marché noir | À faire éclore au chenil ([section 7](#7-xp-évolution-et-chenil)) |
| Raid | Un Pokémon spécial pour tous les participants ([section 13](#13-les-raids)) |

---

## 3. Les événements automatiques

Tant qu'il y a au moins une personne dans le salon vocal, le bot lance régulièrement un événement tiré au hasard dans le salon du jeu. S'il n'y a plus personne en vocal, tout est mis en pause.

`!timeevent` t'indique le prochain événement et dans combien de temps il démarre.

### ✨ Apparition d'un Pokémon

Un Pokémon sauvage apparaît dans le salon. Le premier qui réussit son `!catch` le gagne.

### 🧠 Quiz Pokémon

Le bot pose une question, puis affiche les réponses sous forme de boutons 5 secondes plus tard.

- Une seule réponse par joueur.
- Le premier à trouver la bonne réponse fait apparaître un Pokémon **que lui seul peut capturer** avec `!catch`.
- Le quiz reste ouvert 10 minutes.

### 🔍 Devine le Pokémon

Le bot envoie l'image d'un Pokémon, puis propose 4 noms 5 secondes plus tard. Les règles sont les mêmes que pour le quiz : une réponse par joueur, et le premier qui trouve gagne un Pokémon réservé.

### 🌙 Marché noir

Il n'apparaît que **le mardi entre 20h et minuit**. Tu peux aussi l'ouvrir avec `!marchenoir`.

- Clique sur « Entrer dans le marché noir » pour voir le stock.
- **Un seul achat par jour.**
- On y trouve l'**Œuf** (200 Croco dollars), qui contient un Pokémon avec 1 chance sur 16 d'être shiny.

### 🕵️ La famille Dupont

De temps en temps, un membre de la famille Dupont apparaît dans le salon et te parle.

- **Tant que la famille est riche**, un bouton permet de prendre l'argent qu'il te tend (10 à 100 Croco dollars selon le personnage). Lis bien ce qu'ils disent : leurs phrases contiennent les indices de l'[enquête](#12-lenquête-sur-la-famille-dupont).
- **Une fois la famille démasquée**, ils te demandent de l'aide. Tu peux leur donner des Croco dollars (30 à 100) ou une baie. En remerciement, tu reçois un **Jeton** pour la roue du casino.

---

## 4. Climat, jour et nuit

Les Pokémon qui apparaissent dépendent de l'heure et de la météo.

| Moment | Types qui apparaissent |
|---|---|
| Jour (6h – 20h) | Normal, Plante, Insecte, Vol |
| Nuit (20h – 6h) | Ténèbres, Spectre, Poison |

En journée, toutes les 2 heures, un événement climatique a environ 1 chance sur 3 de se déclencher. Il dure 2 heures et remplace les types du jour par les siens :

| Événement | Types |
|---|---|
| 🌧️ Pluie | Eau, Électrique |
| ⚡ Orage | Électrique, Eau |
| 🌋 Éruption | Feu, Roche, Sol |
| ☀️ Canicule | Feu, Sol, Roche |
| ❄️ Vent glacial | Glace, Eau |
| 🌊 Raz-de-marée | Eau, Glace |
| 🌪️ Tempête | Vol, Électrique |
| 🏜️ Tempête de sable | Sol, Roche, Acier |
| 🌫️ Brouillard | Spectre, Ténèbres, Poison |
| 🌱 Floraison | Plante, Insecte, Fée |
| 🌲 Brume forestière | Plante, Insecte, Poison |
| 🌈 Arc-en-ciel | Fée, Psy, Vol |

Le climat s'applique aux apparitions sur le serveur et en MP.

---

## 5. Ta collection

### `!pokedex`

Affiche une mosaïque de tous tes Pokémon. Clique sur le bouton d'un Pokémon pour voir sa fiche : types, IV, stats, attaques et XP avant évolution.

### `!badge`

Affiche les badges que tu as gagnés en combat. Ajoute un numéro de génération pour filtrer, par exemple `!badge 1`.

---

## 6. Combats et badges

Lance un combat avec `!battle`.

1. **Choisis ton adversaire** parmi ceux de ta région (les champions d'arène).
2. **Compose ton équipe** : jusqu'à 6 Pokémon. Le slot 1 entre en premier.
3. **Combats au tour par tour.** Le Pokémon le plus rapide attaque en premier. À chaque tour, choisis une attaque ou change de Pokémon. Tu as 20 secondes : passé ce délai, une attaque est choisie au hasard.

Les types comptent (super efficace, peu efficace, aucun effet), ainsi que les coups critiques.

### Récompenses en cas de victoire

| Situation | Récompense |
|---|---|
| Première victoire contre un champion | Son badge + 500 Croco dollars |
| Victoire contre un champion déjà battu | 10 Croco dollars |
| Dans tous les cas | +20 XP pour chaque Pokémon de ton équipe |

### Adversaires par région

| Région | Adversaires |
|---|---|
| Kanto | Pierre, Ondine, Major Bob, Erika, Koga, Morgane, Auguste, Giovanni |
| Johto | Albert, Hector, Blanche, Mortimer, Chuck, Jasmine, Frédo, Sandra |
| Hoenn | Roxanne, Bastien, Voltère, Adriane, Norman, Alizée, Lévy & Tatia, Juan, Lucas |
| Sinnoh | Pierrick, Flo, Mélina, Lovis, Kiméra, Charles, Gladyce, Tanguy |
| Unys | Rachid / Armando / Noa, Aloé, Artie, Inezia, Bardane, Carolina, Zhu, Iris / Watson |
| Rocket | Jessie, James, Butch, Cassidy, Proton, Ariana, Archer, Giovanni |

---

## 7. XP, évolution et chenil

### Gagner de l'XP

- **En combat** : +20 XP par victoire pour chaque Pokémon de l'équipe.
- **Au chenil** : +5 XP toutes les 30 minutes passées en vocal.

### Évolution

Quand un Pokémon atteint son seuil d'XP (visible sur sa fiche dans `!pokedex`), il évolue automatiquement. Il garde ses IV, **augmentés de 4** dans chaque statistique (maximum 31).

### Le chenil

Le chenil accueille **un seul** Pokémon ou œuf à la fois. Il progresse tant que tu es dans le salon vocal.

| Commande | Effet |
|---|---|
| `!chenil <nom>` | Place un Pokémon ou un œuf au chenil (ex. `!chenil Salamèche`, `!chenil Oeuf`) |
| `!retirer_chenil` | Retire ce qui s'y trouve |

### Faire éclore un œuf

1. Achète un **Œuf** au marché noir.
2. Place-le avec `!chenil Oeuf`.
3. Il gagne **30 XP toutes les 30 minutes** de vocal et éclot à **400 XP**, soit environ 7 heures.
4. À l'éclosion, tu obtiens un Pokémon (1 chance sur 16 qu'il soit shiny), qui reste au chenil.

Attention : si tu retires un œuf du chenil, son XP est perdue.

---

## 8. La pêche

Commande : `!peche`, à taper sur le serveur.

Conditions :
- avoir choisi une région ;
- posséder une canne (achetée à la boutique) ;
- être dans le salon vocal.

Si tu as plusieurs cannes, le bot te demande laquelle utiliser. Ta ligne reste à l'eau **entre 5 et 15 minutes**, puis le résultat arrive en MP. Tu ne peux avoir qu'une ligne à la fois.

| Résultat | Chance |
|---|---|
| Rien | 40 % |
| Un objet | 30 % |
| Un Pokémon de type Eau de ta région (shiny : 1 sur 64) | 30 % |

Les objets dépendent de la canne :

| Canne | Prix | Objets possibles |
|---|---|---|
| Canne | 300 | Baies |
| Super Canne | 500 | Baies ou boosters d'IV |
| Méga Canne | 700 | Boosters d'IV |

Les baies servent à aider la famille Dupont. Les boosters d'IV sont décrits dans la section suivante.

---

## 9. Argent, boutique et inventaire

La monnaie du jeu est le **Croco dollar**.

### Gagner de l'argent

- Battre un champion (500 la première fois, 20 ensuite).
- Accepter l'argent de la famille Dupont.
- Jouer au casino.
- Vendre des objets au receleur.
- Recevoir un don d'un autre joueur.

### Commandes d'argent

| Commande | Effet |
|---|---|
| `!money` | Affiche ton solde |
| `!money @joueur` | Affiche le solde d'un autre joueur |
| `!pay @joueur <montant>` | Envoie de l'argent à un joueur |
| `!richest` | Classement des 10 plus riches (`!richest 25` pour en voir jusqu'à 25) |

### La boutique : `!shop` ou `!boutique`

Clique sur un objet pour voir sa fiche, puis sur « Acheter ».

| Objet | Prix | Effet |
|---|---|---|
| Poké Ball | 200 | Donne un Pokémon |
| Hyper Ball | 500 | Donne un Pokémon très rare |
| Master Ball | 1 000 | Donne un Pokémon légendaire |
| Hyper Ball S | 1 500 | Pokémon très rare, 1 chance sur 2 d'être shiny |
| Master Ball S | 3 000 | Pokémon légendaire, 1 chance sur 2 d'être shiny |
| PV Plus | 500 | +4 IV en PV |
| Protéine | 500 | +4 IV en Attaque |
| Fer | 500 | +4 IV en Défense |
| Calcium | 500 | +4 IV en Attaque Spé |
| Zinc | 500 | +4 IV en Défense Spé |
| Carbone | 500 | +4 IV en Vitesse |
| Canne | 300 | Permet de pêcher |
| Super Canne | 500 | Pêche avec de meilleurs objets |
| Méga Canne | 700 | Pêche avec les meilleurs objets |

Les Poké Ball et Hyper Ball classiques ont 1 chance sur 64 de donner un shiny, tout comme la Master Ball.

### L'inventaire : `!inventaire`

Clique sur un objet pour voir sa fiche, puis sur « Utiliser ».

- **Balls** : tu reçois immédiatement un Pokémon.
- **Boosters d'IV** : tu choisis le Pokémon qui reçoit +4 IV dans la statistique concernée.
- **Cannes, baies, œufs, jetons** : ils ne s'utilisent pas depuis l'inventaire. Ils servent respectivement à `!peche`, à la famille Dupont, à `!chenil` et à la roue du casino.

### Le receleur : `!receleur`

Il rachète certains objets trouvés en exploration. Clique sur « Parler au receleur », choisis l'objet, puis « Vendre ».

| Objet | Prix de rachat |
|---|---|
| Clé Secrète | 300 |
| Plaque Ombre | 100 |
| Plaque Insecte | 100 |
| Antidote | 60 |
| Anti-Para | 60 |
| Vieux Gâteau | 50 |

---

## 10. Le casino

Commande : `!casino`. Choisis ensuite un jeu.

### 🎴 Deviner la couleur — mise : 10

Devine si la prochaine carte est rouge ou noire.

- 3 bonnes réponses d'affilée : tu gagnes **100**.
- Tu te trompes après 2 bonnes réponses : ta mise est remboursée.
- Tu te trompes avant : tu perds ta mise.

### 🎰 Machine à sous — mise : 10

Il faut aligner **3 symboles identiques**.

| Combinaison | Gain |
|---|---|
| 💎💎💎 | 10 000 |
| ⭐⭐⭐ | 7 000 |
| 🍊🍊🍊 | 500 |
| 🍋🍋🍋 | 200 |
| 🍒🍒🍒 | 100 |

### 🎲 Jeu de dés — mise : 10

Deux dés sont lancés. Tu paries sur leur total.

| Pari | Gain |
|---|---|
| Total exact (de 2 à 12) | 100 |
| Égal (exactement 7) | 100 |
| Haut (de 8 à 12) | 20 |
| Bas (de 2 à 6) | 20 |

### 🎡 Roue de la Fortune — coût : 1 Jeton

Les Jetons s'obtiennent en aidant la famille Dupont après son arrestation.

| Gain | Chance |
|---|---|
| 50 | 30 % |
| 1 Jeton (tu rejoues gratuitement) | 20 % |
| 100 | 20 % |
| 150 | 15 % |
| 300 | 10 % |
| 500 | 5 % |

---

## 11. Les actus et l'exploration

**Les vendredis, samedis et dimanches, entre 20h et minuit**, une actu est publiée dans le salon des actus. Elle parle d'un lieu mystérieux que tu peux aller explorer le soir même.

| Lieu | Commande | Région requise |
|---|---|---|
| Vieux Château de Vestigion | `!vieuxchateau` | Sinnoh |
| Forêt de Vestigion | `!foret` | Sinnoh |
| Château Enfoui | `!chateauenfoui` | Unys |

Règles :
- seul le lieu évoqué dans l'actu du jour est accessible ;
- tu dois être dans la bonne région (`!region`) ;
- **une seule exploration par jour** ;
- tes MP doivent être ouverts.

L'exploration dure **15 à 20 minutes** et se déroule en MP. Chaque minute, il se passe quelque chose :

| Événement | Chance |
|---|---|
| Un Pokémon du lieu apparaît et rejoint directement ta collection (shiny : 1 sur 64) | 30 % |
| Tu trouves un objet que tu ne possèdes pas encore | 30 % |
| Rien, juste l'ambiance du lieu | 40 % |

Les objets trouvés (Vieux Gâteau, Plaque Ombre, Plaque Insecte, Antidote, Anti-Para, Clé Secrète) se revendent au receleur. La Forêt de Vestigion peut aussi donner une Hyper Ball.

---

## 12. L'enquête sur la famille Dupont

La famille Dupont cache un trafic. En écoutant ce que disent ses membres quand ils apparaissent, tu découvres trois lieux à fouiller. Chacun contient une preuve.

| Commande | Région requise | Preuve |
|---|---|---|
| `!parc` | Kanto | Corps Ramoloss |
| `!grotte` | Sinnoh | Veste avec une lettre |
| `!entrepot` | Unys | Livre de comptes falsifiés |

Tu dois te trouver dans la bonne région pour fouiller, et chaque lieu ne se fouille qu'une fois.

- `!preuves` : feuillette ton carnet de preuves.
- `!police` : présente ton dossier à la police. Avec moins de 3 preuves, elle t'indique combien il en manque. **Avec les 3 preuves, la famille Dupont est arrêtée.**

Après l'arrestation, les membres restants de la famille n'ont plus rien : ils ne donnent plus d'argent mais en demandent, et te récompensent d'un Jeton de casino si tu les aides.

---

## 13. Les raids

Un raid est un combat collectif contre un Pokémon très puissant. Il est lancé par l'administrateur dans le salon des raids.

1. Un boss apparaît avec ses PV. Le raid dure **3 minutes**.
2. Clique sur « Choisir mon Pokémon » et engage **un seul** Pokémon. Ce choix est définitif.
3. Le bot calcule les dégâts de ton Pokémon d'après ses stats et ses types face au boss. Choisis un Pokémon fort et d'un type efficace.
4. À la fin, si les dégâts cumulés de tous les joueurs atteignent les PV du boss, **chaque participant reçoit le Pokémon récompense**. Sinon, personne ne gagne rien.

Boss actuel : Méga-Florizarre, qui donne un Méga-Florizarre.

---

## 14. L'événement Team Rocket

Événement spécial déclenché par l'administrateur : Giovanni annonce que la Team Rocket a **volé tous les Pokémon de tous les joueurs**.

Pour récupérer les tiens :

1. Capture de nouveaux Pokémon pour te reconstituer une équipe.
2. Rends-toi dans la région **Rocket** avec `!region`.
3. Bats les sbires de la Team Rocket avec `!battle`. Chaque victoire te donne une « machine » (un badge Rocket).
4. Une fois les machines requises obtenues, tape `!restorerocket`.

Tes Pokémon volés te sont rendus. Si tu avais recapturé entre-temps un Pokémon que tu possédais déjà, il gagne **+4 IV** au lieu d'être ajouté en double. Les machines Rocket te sont ensuite retirées.

---

## 15. Récapitulatif des commandes

| Commande | Effet |
|---|---|
| `!region` | Choisir sa région |
| `!catch` | Capturer le Pokémon apparu sur le serveur |
| `!capture` | Capturer le Pokémon apparu en MP |
| `!timeevent` | Voir le prochain événement |
| `!pokedex` | Voir sa collection et les fiches de ses Pokémon |
| `!badge [génération]` | Voir ses badges |
| `!battle` | Lancer un combat contre un champion |
| `!chenil <nom>` | Placer un Pokémon ou un œuf au chenil |
| `!retirer_chenil` | Vider le chenil |
| `!peche` | Pêcher |
| `!money [@joueur]` | Voir un solde |
| `!pay @joueur <montant>` | Donner de l'argent |
| `!richest [nombre]` | Classement des plus riches |
| `!shop` / `!boutique` | Ouvrir la boutique |
| `!inventaire` | Voir et utiliser ses objets |
| `!receleur` | Vendre des objets |
| `!marchenoir` | Ouvrir le marché noir |
| `!casino` | Ouvrir le casino |
| `!vieuxchateau`, `!foret`, `!chateauenfoui` | Explorer le lieu de l'actu du jour |
| `!parc`, `!grotte`, `!entrepot` | Fouiller un lieu de l'enquête |
| `!preuves` | Voir ses preuves |
| `!police` | Dénoncer la famille Dupont |
| `!restorerocket` | Récupérer ses Pokémon après l'événement Team Rocket |
