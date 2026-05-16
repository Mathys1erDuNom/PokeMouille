"""
make_shiny.py
─────────────
Lit  : json/new_pokemons/pokemon_gen1_normal.json
Écrit: json/new_pokemons/pokemon_gen1_shiny.json

Transformations :
  - name         : "Bulbizarre"  → "Bulbizarre_shiny"
  - evo.name     : "Herbizarre"  → "Herbizarre_shiny"
  - evo.file     : "pokemon_gen1_normal.json" → "pokemon_gen1_shiny.json"
"""

import json
import os
import sys

# ── Fichiers ───────────────────────────────────────────────────────────────────
script_dir  = os.path.dirname(os.path.abspath(__file__))
root_dir    = os.path.join(script_dir, "..")

INPUT_FILE  = os.path.join(root_dir, "json",  "pokemon_rare_pokeball_normal.json")
OUTPUT_FILE = os.path.join(root_dir, "json",  "pokemon_rare_pokeball_shiny.json")
# ──────────────────────────────────────────────────────────────────────────────


def make_shiny(pokemon: dict) -> dict:
    p = dict(pokemon)

    # Nom du Pokémon
    p["name"] = p["name"] + "_shiny"

    # Image : /sprites/pokemon/2.png → /sprites/pokemon/shiny/2.png
    image = p.get("image", "")
    if "sprites/pokemon/" in image and "/shiny/" not in image:
        p["image"] = image.replace("sprites/pokemon/", "sprites/pokemon/shiny/")

    # Champ evo
    evo = dict(p.get("evo", {}))
    if evo.get("name") not in (None, "pas evo"):
        evo["name"] = evo["name"] + "_shiny"
    if evo.get("file") not in (None, "pas evo"):
        evo["file"] = evo["file"].replace("normal", "shiny")
    p["evo"] = evo

    return p


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Fichier introuvable : {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        pokemons = json.load(f)

    shiny_pokemons = [make_shiny(p) for p in pokemons]

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(shiny_pokemons, f, ensure_ascii=False, indent=4)

    print(f"[OK] {len(shiny_pokemons)} Pokémons shiny générés → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()