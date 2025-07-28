import random
import json
import os

# Chargement unique des données d'attaques
script_dir = os.path.dirname(os.path.abspath(__file__))
attack_data_path = os.path.join(script_dir, "..", "json", "attack_data.json")

with open(attack_data_path, encoding="utf-8") as f:
    all_attacks = json.load(f)

def get_attack_info(name):
    for attack in all_attacks:
        if attack["name"].lower() == name.lower():
            return attack
    return None

def calculate_damage(attacker, defender, attack_name):
    attack_info = get_attack_info(attack_name)
    if not attack_info:
        return random.randint(5, 10)  # attaque inconnue, valeur par défaut

    category = attack_info["category"]
    power = attack_info["damage"]
    level = 50  # fixe pour simplification

    # Choix des stats selon catégorie
    if category == "physique":
        atk_stat = attacker["stats"]["attack"]
        def_stat = defender["stats"]["defense"]
    elif category == "speciale":
        atk_stat = attacker["stats"]["special_attack"]
        def_stat = defender["stats"]["special_defense"]
    else:
        atk_stat = 50
        def_stat = 50

    modifier = random.uniform(0.85, 1.0)  # facteur aléatoire
    base = (((2 * level / 5 + 2) * power * atk_stat / def_stat) / 50) + 2
    damage = int(base * modifier)
    return max(1, damage)
