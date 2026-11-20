"""Génère json/galar.json : toutes les formes de Galar, au même format que alola.json
(current_xp, xp_evo = somme des stats, evo chaînée, noms avec "_" à la place des espaces).

Lancer depuis la racine du projet : python script_AIDE/creation_galar_json.py
"""

import requests
import json
import os
import time

# Formes régionales de Galar (PokeAPI id -> besoin du suffixe " de Galar").
# IDs vérifiés sur PokeAPI (suffixe "-galar").
GALAR_FORM_IDS = [
    10161,  # Miaouss (Meowth)
    10162,  # Ponyta
    10163,  # Galopa (Rapidash)
    10164,  # Ramoloss (Slowpoke)
    10165,  # Flagadoss (Slowbro)
    10166,  # Canarticho (Farfetch'd)
    10167,  # Smogogo (Weezing)
    10168,  # M. Mime
    10169,  # Artikodin (Articuno)
    10170,  # Électhor (Zapdos)
    10171,  # Sulfura (Moltres)
    10172,  # Roigada (Slowking)
    10173,  # Corayon (Corsola)
    10174,  # Zigzaton
    10175,  # Linéon (Zigzaton évolué)
    10176,  # Darumarond (Darumaka)
    10177,  # Darumacho, forme standard (Darmanitan)
    10179,  # Tutafeh (Yamask)
    10180,  # Limonde (Stunfisk)
]

# Évolutions propres à la région de Galar : nouvelles espèces, pas de suffixe.
GALAR_EVOLUTION_IDS = [862, 863, 864, 865, 866, 867]  # Ixon, Berserkatt, Corayôme, Palarticho, M. Glaquette, Tutétékri

# Ordre d'affichage : chaque forme suivie de son évolution directe.
ORDERED_IDS = [
    10161, 863,
    10162, 10163,
    10164, 10165,
    10172,
    10166, 865,
    10167,
    10168, 866,
    10169,
    10170,
    10171,
    10173, 864,
    10174, 10175, 862,
    10176, 10177,
    10179, 867,
    10180,
]

# base_id -> id de l'évolution directe (dans ce fichier). Absent = pas d'évolution.
# shortcut: Slowpoke de Galar a deux évolutions possibles (Slowbro ou Slowking de
# Galar selon l'objet utilisé) ; un seul "evo" est modélisable ici, on garde Slowbro.
EVOLUTIONS = {
    10161: 863,
    10162: 10163,
    10164: 10165,
    10166: 865,
    10168: 866,
    10173: 864,
    10174: 10175,
    10175: 862,
    10176: 10177,
    10179: 867,
}

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
    "fairy": "fee",
}

session = requests.Session()
move_cache = {}


def get_french_name(species_url, suffix=""):
    response = session.get(species_url, timeout=15)
    response.raise_for_status()
    species_data = response.json()

    for entry in species_data["names"]:
        if entry["language"]["name"] == "fr":
            name = entry["name"]
            break
    else:
        name = species_data["name"].capitalize()

    return (name + suffix).replace(" ", "_")


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


def get_pokemon_data(pokemon_id, is_form):
    try:
        url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
        response = session.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        suffix = " de Galar" if is_form else ""
        french_name = get_french_name(data["species"]["url"], suffix)

        types = [
            TYPE_TRANSLATION.get(entry["type"]["name"], entry["type"]["name"])
            for entry in data["types"]
        ]

        raw_stats = {
            stat["stat"]["name"].replace("-", "_"): stat["base_stat"]
            for stat in data["stats"]
        }
        # Même ordre de clés que les autres fichiers (alola.json, pokemon_gen1_normal.json, ...)
        stats = {k: raw_stats[k] for k in ("hp", "attack", "special_attack", "speed", "defense", "special_defense")}

        attacks = []
        for move_entry in data["moves"]:
            if len(attacks) >= 3:
                break
            french_move = get_french_move(move_entry["move"]["url"])
            if french_move and french_move not in attacks:
                attacks.append(french_move)
        while len(attacks) < 2:
            attacks.append("Charge")

        image = (
            "https://raw.githubusercontent.com/PokeAPI/sprites/"
            f"master/sprites/pokemon/{pokemon_id}.png"
        )

        print(f"OK {french_name} (#{pokemon_id})")
        return {
            "name": french_name,
            "type": types,
            "image": image,
            "attacks": attacks,
            "stats": stats,
        }

    except Exception as e:
        print(f"ERREUR Pokémon #{pokemon_id}: {e}")
        return None


def generate_galar_json():
    by_id = {}

    print("Récupération des formes de Galar...")
    print("-" * 50)

    for pokemon_id in ORDERED_IDS:
        data = get_pokemon_data(pokemon_id, is_form=pokemon_id in GALAR_FORM_IDS)
        if data:
            by_id[pokemon_id] = data
        time.sleep(0.1)

    pokemon_list = []
    for pokemon_id in ORDERED_IDS:
        data = by_id.get(pokemon_id)
        if not data:
            continue

        evo_id = EVOLUTIONS.get(pokemon_id)
        evo_data = by_id.get(evo_id) if evo_id else None
        evo = (
            {"name": evo_data["name"], "file": "galar.json"}
            if evo_data
            else {"name": "pas evo", "file": "pas evo"}
        )

        pokemon_list.append({
            **data,
            "current_xp": 0,
            "xp_evo": sum(data["stats"].values()),
            "evo": evo,
        })

    os.makedirs("json", exist_ok=True)
    output_file = "json/galar.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(pokemon_list, f, ensure_ascii=False, indent=4)

    print("-" * 50)
    print(f"Fichier généré : {output_file}")
    print(f"{len(pokemon_list)}/{len(ORDERED_IDS)} Pokémon enregistrés")


if __name__ == "__main__":
    generate_galar_json()
