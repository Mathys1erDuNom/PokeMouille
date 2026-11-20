
import requests
import json
import os
import time

# Identifiants PokeAPI des formes d'Alola
ALOLA_IDS = [
    10091, 10092,  # Rattata, Rattatac
    10100,         # Raichu
    10101, 10102,  # Sabelette, Sablaireau
    10103, 10104,  # Goupix, Feunard
    10105, 10106,  # Taupiqueur, Triopikeur
    10107, 10108,  # Miaouss, Persian
    10109, 10110, 10111,  # Racaillou, Gravalanch, Grolem
    10112, 10113,  # Tadmorv, Grotadmorv
    10114,         # Noadkoko
    10115          # Ossatueur
]

TYPE_TRANSLATION = {
    "normal": "normal",
    "fighting": "combat",
    "flying": "vol",
    "poison": "poison",
    "ground": "sol",
    "rock": "roche",
    "bug": "insecte",
    "ghost": "spectre",
    "steel": "acier",
    "fire": "feu",
    "water": "eau",
    "grass": "plante",
    "electric": "electrique",
    "psychic": "psy",
    "ice": "glace",
    "dragon": "dragon",
    "dark": "tenebres",
    "fairy": "fee"
}

session = requests.Session()
move_cache = {}

def get_french_name(species_url):
    response = session.get(species_url, timeout=15)
    response.raise_for_status()
    species_data = response.json()

    for entry in species_data["names"]:
        if entry["language"]["name"] == "fr":
            return entry["name"] + " d'Alola"

    return species_data["name"].capitalize() + " d'Alola"


def get_french_move(move_url):
    if move_url in move_cache:
        return move_cache[move_url]

    response = session.get(move_url, timeout=15)
    response.raise_for_status()
    move_data = response.json()

    french_name = None

    for entry in move_data["names"]:
        if entry["language"]["name"] == "fr":
            french_name = entry["name"]
            break

    move_cache[move_url] = french_name
    return french_name


def get_pokemon_data(pokemon_id):
    try:
        # Récupération des données du Pokémon
        url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
        response = session.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Nom français
        french_name = get_french_name(data["species"]["url"])

        # Types
        types = []
        for entry in data["types"]:
            type_name = entry["type"]["name"]
            types.append(TYPE_TRANSLATION.get(type_name, type_name))

        # Statistiques
        stats = {}

        for stat in data["stats"]:
            stat_name = stat["stat"]["name"]

            if stat_name == "hp":
                stats["hp"] = stat["base_stat"]
            elif stat_name == "attack":
                stats["attack"] = stat["base_stat"]
            elif stat_name == "defense":
                stats["defense"] = stat["base_stat"]
            elif stat_name == "special-attack":
                stats["special_attack"] = stat["base_stat"]
            elif stat_name == "special-defense":
                stats["special_defense"] = stat["base_stat"]
            elif stat_name == "speed":
                stats["speed"] = stat["base_stat"]

        # Attaques en français
        attacks = []

        for move_entry in data["moves"]:
            if len(attacks) >= 3:
                break

            move_url = move_entry["move"]["url"]
            french_move = get_french_move(move_url)

            if french_move and french_move not in attacks:
                attacks.append(french_move)

        # Ajouter Charge si nécessaire
        while len(attacks) < 2:
            attacks.append("Charge")

        # Sprite normal (PNG), comme les autres JSON
        image = (
            "https://raw.githubusercontent.com/PokeAPI/sprites/"
            f"master/sprites/pokemon/{pokemon_id}.png"
        )

        pokemon_data = {
            "name": french_name,
            "type": types,
            "image": image,
            "attacks": attacks,
            "stats": stats
        }

        print(f"OK {french_name} (#{pokemon_id})")
        return pokemon_data

    except Exception as e:
        print(f"ERREUR Pokémon #{pokemon_id}: {e}")
        return None


def generate_alola_json():
    pokemon_list = []

    print("Récupération des formes d'Alola...")
    print("-" * 50)

    for pokemon_id in ALOLA_IDS:
        pokemon_data = get_pokemon_data(pokemon_id)

        if pokemon_data:
            pokemon_list.append(pokemon_data)

        time.sleep(0.1)

    # Création du dossier json s'il n'existe pas
    os.makedirs("json", exist_ok=True)

    # Sauvegarde
    output_file = "json/alola.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(pokemon_list, f, ensure_ascii=False, indent=4)

    print("-" * 50)
    print(f"Fichier généré : {output_file}")
    print(f"{len(pokemon_list)}/{len(ALOLA_IDS)} Pokémon enregistrés")


if __name__ == "__main__":
    generate_alola_json()
