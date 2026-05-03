"""
adapt_gen5.py
─────────────
Lit  : json/pokemon_gen5_normal.json
Écrit: json/new_pokemons/pokemon_gen5_normal.json

Pour chaque Pokémon :
  - current_xp = 0
  - xp_evo     = somme des stats de base (0 si pas d'évolution)
  - evo        = {"name": <evo suivante>, "file": "pokemon_gen5_normal.json"}
                 ou {"name": "pas evo", "file": "pas evo"}
"""

import json
import os

# ── Chemins ────────────────────────────────────────────────────────────────────
script_dir      = os.path.dirname(os.path.abspath(__file__))
root_dir        = os.path.join(script_dir, "..")
INPUT_FILE      = os.path.join(root_dir, "json", "pokemon_gen5_normal.json")
OUTPUT_DIR      = os.path.join(root_dir, "json", "new_pokemons")
OUTPUT_FILE     = os.path.join(OUTPUT_DIR, "pokemon_gen5_normal.json")
OUTPUT_FILENAME = "pokemon_gen5_normal.json"
# ──────────────────────────────────────────────────────────────────────────────

# ── Chaînes d'évolution gen 5 / Unys (noms FR) ───────────────────────────────
EVOLUTION_CHAINS = [
    # Starters
    ["Vipélierre", "Lianaja", "Majaspic"],
    ["Gruikui", "Grotichon", "Roitiflam"],
    ["Moustillon", "Mateloutre", "Clamiral"],

    # Premières routes
    ["Ratentif", "Miradar"],
    ["Ponchiot", "Ponchien", "Mastouffe"],

    # Oiseaux
    ["Poichigeon", "Colombeau", "Déflaisan"],

    # Félins / singes
    ["Chacripan", "Léopardus"],
    ["Feuillajou", "Feuiloutan"],
    ["Flamajou", "Flamoutan"],
    ["Flotajou", "Flotoutan"],

    # Normal
    ["Nanméouïe"],

    # Psy / ténèbres
    ["Chovsourir", "Rhinolove"],
    ["Scrutella", "Mesmérella", "Sidérella"],
    ["Nucléos", "Méios", "Symbios"],

    # Insectes
    ["Larveyette", "Couverdure", "Manternel"],
    ["Venipatte", "Scobolide", "Brutapode"],

    # Plantes
    ["Doudouvet", "Farfaduvet"],
    ["Chlorobule", "Fragilady"],

    # Feu / sol
    ["Darumarond", "Darumacho"],

    # Eau
    ["Tritonde", "Batracné", "Crapustule"],
    ["Bargantua"],

    # Électrique
    ["Zébibron", "Zéblitz"],
    ["Statitik", "Mygavolt"],

    # Roche / sol
    ["Nodulithe", "Géolithe", "Gigalithe"],
    ["Rototaupe", "Minotaupe"],
    ["Charpenti", "Ouvrifier", "Bétochef"],

    # Combat
    ["Kungfouine", "Shaofouine"],

    # Acier
    ["Tic", "Clic", "Cliticlic"],

    # Glace
    ["Sorbébé", "Sorboul", "Sorbouboul"],

    # Dragon
    ["Solochi", "Diamat", "Trioxhydre"],
    ["Coupenotte", "Incisache", "Tranchodon"],

    # Sol / spectre
    ["Mascaïman", "Escroco", "Crocorible"],
    ["Tutafeh", "Tutankafer"],

    # Insecte / feu / autres
    ["Pyronille", "Pyrax"],
    ["Anchwatt", "Lampéroie", "Ohmassacre"],

    # Divers
    ["Vivaldaim", "Haydaim"],
    ["Emolga"],
    ["Carabing", "Lançargot"],
    ["Escargaume", "Limaspeed"],

    # Lames / combat
    ["Baggiguane", "Baggaïd"],
    ["Cryptéro"],
    ["Tutankafer"],

    # Pokémon particuliers
    ["Zorua", "Zoroark"],
    ["Lewsor", "Neitram"],
    ["Funécire", "Mélancolux", "Lugulabre"],
    ["Grindur", "Noacier"],
    ["Polarhume", "Polagriffe"],
    ["Hexagel"],

    # Légendaires (pas d'évolution)
    ["Cobaltium"],
    ["Terrakium"],
    ["Viridium"],
    ["Boréas"],
    ["Fulguris"],
    ["Démétéros"],
    ["Reshiram"],
    ["Zekrom"],
    ["Kyurem"],
    ["Keldeo"],
    ["Meloetta"],
    ["Genesect"],
]

# Construit un dict : nom (lowercase) → nom de l'évolution suivante
NEXT_EVO = {}
for chain in EVOLUTION_CHAINS:
    for i, name in enumerate(chain):
        key = name.lower()
        # Ne pas écraser une entrée déjà définie (première occurrence prioritaire)
        if key not in NEXT_EVO:
            if i < len(chain) - 1:
                NEXT_EVO[key] = chain[i + 1]
            else:
                NEXT_EVO[key] = None  # dernière forme


def get_next_evo(name):
    """Retourne le nom de l'évolution suivante, ou None."""
    return NEXT_EVO.get(name.strip().lower(), None)


def sum_stats(stats):
    return sum(stats.values())


def adapt(pokemon):
    name     = pokemon["name"]
    stats    = pokemon.get("stats", {})
    next_evo = get_next_evo(name)

    if next_evo:
        evo    = {"name": next_evo, "file": OUTPUT_FILENAME}
        xp_evo = sum_stats(stats)
    else:
        evo    = {"name": "pas evo", "file": "pas evo"}
        xp_evo = 0

    return {
        **pokemon,
        "current_xp": 0,
        "xp_evo":     xp_evo,
        "evo":        evo,
    }


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        pokemons = json.load(f)

    adapted = [adapt(p) for p in pokemons]

    # Rapport des Pokémons non reconnus
    unknown = [p["name"] for p in pokemons
               if p["name"].strip().lower() not in NEXT_EVO]
    if unknown:
        print(f"[WARNING] Pokémons sans chaîne d'évolution connue ({len(unknown)}) :")
        for n in unknown:
            print(f"  - {n}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(adapted, f, ensure_ascii=False, indent=4)

    print(f"[OK] {len(adapted)} Pokémons adaptés → {OUTPUT_FILE}")
    print(f"[INFO] Pokémons avec évolution : {sum(1 for p in adapted if p['evo']['name'] != 'pas evo')}")
    print(f"[INFO] Pokémons sans évolution : {sum(1 for p in adapted if p['evo']['name'] == 'pas evo')}")


if __name__ == "__main__":
    main()