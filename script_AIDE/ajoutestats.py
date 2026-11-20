import json
from pathlib import Path

# Chemin basé sur l'emplacement du script (indépendant du dossier depuis lequel tu lances python)
SCRIPT_DIR = Path(__file__).resolve().parent
CHEMIN_FICHIER = SCRIPT_DIR.parent / "json" / "adversaire_rocket.json"
BONUS = 51

STATS_A_MODIFIER = [
    "hp",
    "attack",
    "defense",
    "special_attack",
    "special_defense",
    "speed",
]

def modifier_stats_pokemon(pokemon):
    """Ajoute le bonus à toutes les stats connues d'un pokémon."""
    stats = pokemon.get("stats", {})
    for cle in STATS_A_MODIFIER:
        if cle in stats:
            stats[cle] += BONUS

def main():
    with open(CHEMIN_FICHIER, "r", encoding="utf-8") as f:
        data = json.load(f)

    for adversaire in data:
        pokemons = adversaire.get("pokemons", [])
        for pokemon in pokemons:
            modifier_stats_pokemon(pokemon)

    with open(CHEMIN_FICHIER, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Stats mises à jour (+{BONUS}) pour tous les Pokémon dans {CHEMIN_FICHIER}")

if __name__ == "__main__":
    main()