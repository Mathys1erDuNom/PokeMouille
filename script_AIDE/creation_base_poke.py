import requests
import json

def get_french_name(species_url: str) -> str:
    """Récupère le nom français depuis l'URL de species."""
    resp = requests.get(species_url)
    if resp.status_code != 200:
        return None
    species_data = resp.json()
    for name_entry in species_data["names"]:
        if name_entry["language"]["name"] == "fr":
            return name_entry["name"]
    return None

def get_pokemon_shiny_data(poke_id):
    url = f"https://pokeapi.co/api/v2/pokemon/{poke_id}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"[ERREUR] Impossible de récupérer les données pour l'ID {poke_id}")
        return None

    data = response.json()

    # 🔥 Récupération du nom FR via species
    species_url = data["species"]["url"]
    french_name = get_french_name(species_url)
    if not french_name:
        french_name = data["name"].capitalize()  # fallback anglais

    # Ajout du suffixe _shiny
    shiny_name = f"{french_name}_shiny"

    types = [t["type"]["name"] for t in data["types"]]
    image = data["sprites"]["front_shiny"]  # image shiny

    # Récupérer quelques attaques
    attacks = [m["move"]["name"] for m in data["moves"][:3]]

    # Stats
    stats = {}
    for stat in data["stats"]:
        stat_name = stat["stat"]["name"]
        value = stat["base_stat"]
        if stat_name == "hp":
            stats["hp"] = value
        elif stat_name == "attack":
            stats["attack"] = value
        elif stat_name == "defense":
            stats["defense"] = value
        elif stat_name == "special-attack":
            stats["special_attack"] = value
        elif stat_name == "special-defense":
            stats["special_defense"] = value
        elif stat_name == "speed":
            stats["speed"] = value

    return {
        "name": shiny_name,
        "type": types,
        "image": image,
        "attacks": attacks,
        "stats": stats
    }

# IDs de la 2ème génération : 152 à 251 inclus
pokemon_shiny_list = []
for pid in range(152, 252):
    print(f"[INFO] Récupération de l'ID {pid}...")
    p_data = get_pokemon_shiny_data(pid)
    if p_data:
        pokemon_shiny_list.append(p_data)

# Sauvegarde dans un fichier JSON
with open("pokemon_gen2_shiny.json", "w", encoding="utf-8") as f:
    json.dump(pokemon_shiny_list, f, ensure_ascii=False, indent=4)

print(" Fichier 'pokemon_gen2_shiny.json' créé avec succès avec les noms français et le suffixe _shiny !")
