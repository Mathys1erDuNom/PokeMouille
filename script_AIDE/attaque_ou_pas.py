import json

# Fichiers à charger
pokemon_file = "pokemon_gen3_normal.json"
attack_file = "attack_data.json"

# Charger les fichiers JSON
with open(pokemon_file, "r", encoding="utf-8") as f:
    pokemon_data = json.load(f)

with open(attack_file, "r", encoding="utf-8") as f:
    attack_data = json.load(f)

# Récupérer la liste des attaques dans attack_data.json
attacks_in_data = {atk["name"] for atk in attack_data if "name" in atk}

# Récupérer toutes les attaques utilisées par les Pokémon
attacks_in_pokemon = set()
for p in pokemon_data:
    for atk in p.get("attacks", []):
        attacks_in_pokemon.add(atk)

# Trouver les attaques manquantes
missing_attacks = sorted(attacks_in_pokemon - attacks_in_data)

# Résultat
if missing_attacks:
    print("⚠️ Attaques présentes dans pokemon_gen3_normal.json mais absentes de attack_data.json :")
    for atk in missing_attacks:
        print(f" - {atk}")
else:
    print("Toutes les attaques des Pokémon sont présentes dans attack_data.json.")
