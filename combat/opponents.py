# opponents.py
import random

class Opponent:
    """Représente un adversaire avec son nom et son équipe"""
    def __init__(self, name, team, difficulty="normal", dialogue=None):
        self.name = name
        self.team = team  # Liste de noms de Pokémon
        self.difficulty = difficulty
        self.dialogue = dialogue or {}
    
    def get_intro(self):
        return self.dialogue.get("intro", f"{self.name} te défie en combat !")
    
    def get_victory(self):
        return self.dialogue.get("victory", f"{self.name} : Bien joué, tu es un excellent dresseur !")
    
    def get_defeat(self):
        return self.dialogue.get("defeat", f"{self.name} : J'ai gagné ! Continue à t'entraîner !")


# Base de données d'adversaires
OPPONENTS = {
    "dresseur_debutant": Opponent(
        name="Timmy le Débutant",
        team=["Rattata", "Pikachu", "Aspicot"],
        difficulty="facile",
        dialogue={
            "intro": "Timmy : Hey ! C'est mon premier combat, allons-y !",
            "victory": "Timmy : Waou, tu es trop fort pour moi !",
            "defeat": "Timmy : Yes ! J'ai gagné mon premier combat !"
        }
    ),
    
    "champion_arene": Opponent(
        name="Pierre - Champion d'Arène",
        team=["Onix", "Geodude", "Racaillou", "Steelix"],
        difficulty="moyen",
        dialogue={
            "intro": "Pierre : Je suis le champion de l'arène de type Roche ! Prépare-toi !",
            "victory": "Pierre : Incroyable... Ta détermination a brisé ma défense de roche.",
            "defeat": "Pierre : La roche est indestructible ! Reviens quand tu seras plus fort !"
        }
    ),
    
    "team_rocket": Opponent(
        name="Jessie & James (Team Rocket)",
        team=["Arbok", "Weezing", "Meowth"],
        difficulty="moyen",
        dialogue={
            "intro": "🚀 Pour protéger le monde de la dévastation ! Prépare-toi au combat !",
            "victory": "On se fait encore battre ! La Team Rocket s'envole vers d'autres cieux ! ✨",
            "defeat": "Haha ! La Team Rocket triomphe ! On va voler tous tes Pokémon !"
        }
    ),
    
    "maitre_pokemon": Opponent(
        name="Red - Maître Pokémon",
        team=["Pikachu", "Charizard", "Blastoise", "Venusaur", "Snorlax", "Lapras"],
        difficulty="difficile",
        dialogue={
            "intro": "Red : ...",
            "victory": "Red : ... *hoche la tête avec respect*",
            "defeat": "Red : ... *s'en va silencieusement*"
        }
    ),
    
    "rival": Opponent(
        name="Blue - Ton Rival",
        team=["Alakazam", "Rhydon", "Arcanine", "Exeggutor", "Gyarados"],
        difficulty="difficile",
        dialogue={
            "intro": "Blue : Tiens tiens, tu es toujours là ? Voyons si tu as progressé !",
            "victory": "Blue : Grr... J'ai encore perdu. Mais je reviendrai plus fort !",
            "defeat": "Blue : Je suis toujours meilleur que toi ! L'odeur des perdants !"
        }
    ),
    
    "champion_elite": Opponent(
        name="Cynthia - Championne Régionale",
        team=["Garchomp", "Lucario", "Milotic", "Roserade", "Spiritomb", "Togekiss"],
        difficulty="très_difficile",
        dialogue={
            "intro": "Cynthia : J'ai entendu parler de toi. Montre-moi la puissance de tes liens avec tes Pokémon.",
            "victory": "Cynthia : Magnifique... Tu as vraiment quelque chose de spécial.",
            "defeat": "Cynthia : Continue ton voyage, tu as encore beaucoup à apprendre."
        }
    ),
    
    "legendaire": Opponent(
        name="Giovanni - Boss de la Team Rocket",
        team=["Mewtwo", "Nidoking", "Nidoqueen", "Rhyperior", "Dugtrio", "Rhydon"],
        difficulty="très_difficile",
        dialogue={
            "intro": "Giovanni : Tu as osé me défier ? Je vais te montrer la vraie puissance !",
            "victory": "Giovanni : Impossible... Comment as-tu pu... *disparaît dans l'ombre*",
            "defeat": "Giovanni : Pathétique. La Team Rocket dominera le monde !"
        }
    ),
    
    "dresseur_aleatoire": Opponent(
        name="Dresseur Errant",
        team=["random"],  # Sera remplacé par des Pokémon aléatoires
        difficulty="variable"
    )
}


def get_random_opponent(exclude=None):
    """Récupère un adversaire aléatoire"""
    available = [k for k in OPPONENTS.keys() if k != exclude]
    return OPPONENTS[random.choice(available)]


def get_opponent_by_difficulty(difficulty):
    """Récupère un adversaire selon la difficulté"""
    matching = [opp for opp in OPPONENTS.values() if opp.difficulty == difficulty]
    return random.choice(matching) if matching else get_random_opponent()


def create_random_team(full_pokemon_data, size=3):
    """Crée une équipe aléatoire de Pokémon"""
    available = [p["name"] for p in full_pokemon_data if p.get("name")]
    return random.sample(available, min(size, len(available)))


def get_opponent_team(opponent, full_pokemon_data):
    """Récupère l'équipe complète d'un adversaire avec leurs données"""
    team_names = opponent.team
    
    # Si l'équipe est "random", on en génère une
    if team_names == ["random"]:
        team_names = create_random_team(full_pokemon_data, random.randint(3, 6))
    
    # Récupère les données complètes des Pokémon
    team_data = []
    for name in team_names:
        poke = next((p for p in full_pokemon_data if p.get("name") == name), None)
        if poke:
            team_data.append(poke)
    
    return team_data