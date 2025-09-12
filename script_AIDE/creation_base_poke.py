import requests
import json
from time import sleep
from typing import Optional, Dict, Any

# --- Session HTTP + User-Agent (bonne pratique) ---
session = requests.Session()
session.headers.update({"User-Agent": "Pokemon-FR-Exporter/1.0 (+https://pokeapi.co)"})

# --- Caches simples pour limiter les appels ---
species_cache: Dict[str, Optional[str]] = {}
type_cache: Dict[str, Optional[str]] = {}
move_cache: Dict[str, Optional[str]] = {}

def get_localized_name(resource_url: str, lang: str = "fr") -> Optional[str]:
    """Retourne le nom localisé (fr) depuis une ressource PokeAPI contenant 'names'."""
    resp = session.get(resource_url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    for entry in data.get("names", []):
        if entry.get("language", {}).get("name") == lang:
            return entry.get("name")
    return None

def get_french_species_name(species_url: str) -> Optional[str]:
    """Nom FR depuis l'endpoint species."""
    if species_url in species_cache:
        return species_cache[species_url]
    name = get_localized_name(species_url, "fr")
    species_cache[species_url] = name
    return name

def get_french_type_name(type_url: str, fallback_en: str) -> str:
    """Nom FR du type via l'endpoint type."""
    if type_url in type_cache:
        return type_cache[type_url] or fallback_en
    fr = get_localized_name(type_url, "fr")
    type_cache[type_url] = fr
    return fr or fallback_en

def get_french_move_name(move_url: str, fallback_en: str) -> str:
    """Nom FR de l'attaque via l'endpoint move."""
    if move_url in move_cache:
        return move_cache[move_url] or fallback_en
    fr = get_localized_name(move_url, "fr")
    move_cache[move_url] = fr
    return fr or fallback_en

def get_pokemon_normal_data(poke_id: int) -> Optional[Dict[str, Any]]:
    url = f"https://pokeapi.co/api/v2/pokemon/{poke_id}"
    response = session.get(url)
    if response.status_code != 200:
        print(f"[ERREUR] Impossible de récupérer les données pour l'ID {poke_id}")
        return None

    data = response.json()

    # --- Nom FR via species ---
    species_url = data["species"]["url"]
    french_name = get_french_species_name(species_url) or data["name"].capitalize()

    # nom normal (pas de suffixe)
    name = french_name
    # image normale (pas shiny)
    image = data["sprites"]["front_default"]

    # --- Types en FR ---
    types_fr = []
    for t in data["types"]:
        t_en = t["type"]["name"].capitalize()
        t_url = t["type"]["url"]
        types_fr.append(get_french_type_name(t_url, t_en))

    # --- Attaques (3 premières) en FR ---
    attacks_fr = []
    for m in data["moves"][:3]:
        m_en = m["move"]["name"].replace("-", " ").capitalize()
        m_url = m["move"]["url"]
        attacks_fr.append(get_french_move_name(m_url, m_en))

    # --- Stats ---
    stats_map = {
        "hp": "hp",
        "attack": "attack",
        "defense": "defense",
        "special-attack": "special_attack",
        "special-defense": "special_defense",
        "speed": "speed",
    }
    stats = {}
    for stat in data["stats"]:
        key = stats_map.get(stat["stat"]["name"])
        if key:
            stats[key] = stat["base_stat"]

    sleep(0.05)  # petite pause pour éviter de surcharger l'API

    return {
        "name": name,
        "type": types_fr,
        "image": image,
        "attacks": attacks_fr,
        "stats": stats
    }

# --- Génération GEN 3 : 252 à 386 inclus (normal) ---
pokemon_normal_list = []
for pid in range(252, 387):
    print(f"[INFO] Récupération de l'ID {pid} (normal)...")
    p_data = get_pokemon_normal_data(pid)
    if p_data:
        pokemon_normal_list.append(p_data)

with open("pokemon_gen3_normal.json", "w", encoding="utf-8") as f:
    json.dump(pokemon_normal_list, f, ensure_ascii=False, indent=4)

print("Fichier 'pokemon_gen3_normal.json' créé avec succès (noms FR, types FR, attaques FR) !")
