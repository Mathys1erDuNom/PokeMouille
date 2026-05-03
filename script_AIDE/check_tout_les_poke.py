"""
compare_json.py
───────────────
Compare les noms de Pokémons entre deux fichiers JSON et affiche
les Pokémons présents dans l'un mais pas dans l'autre.
"""

import json
import os
import sys

# ── Fichiers à comparer ────────────────────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir   = os.path.join(script_dir, "..")

FILE_A = os.path.join(root_dir, "json", "pokemon_gen4_normal.json")
FILE_B = os.path.join(root_dir, "json", "new_pokemons", "pokemon_gen4_normal.json")
# ──────────────────────────────────────────────────────────────────────────────


def load_names(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {p["name"].strip().lower(): p["name"] for p in data}


def compare(file1, file2):
    print(f"\n📂 Fichier A : {file1}")
    print(f"📂 Fichier B : {file2}\n")

    names1 = load_names(file1)
    names2 = load_names(file2)

    only_in_1 = {k: v for k, v in names1.items() if k not in names2}
    only_in_2 = {k: v for k, v in names2.items() if k not in names1}
    common    = {k for k in names1 if k in names2}

    print(f"✅ Pokémons en commun       : {len(common)}")
    print(f"❌ Manquants dans fichier B : {len(only_in_1)}")
    print(f"❌ Manquants dans fichier A : {len(only_in_2)}")

    if only_in_1:
        print(f"\n── Présents dans A mais pas dans B ──────────────────────────────")
        for name in sorted(only_in_1.values()):
            print(f"  - {name}")

    if only_in_2:
        print(f"\n── Présents dans B mais pas dans A ──────────────────────────────")
        for name in sorted(only_in_2.values()):
            print(f"  - {name}")

    if not only_in_1 and not only_in_2:
        print("\n🎉 Les deux fichiers ont exactement les mêmes Pokémons !")


def main():
    # Vérifie que les fichiers existent
    for path in (FILE_A, FILE_B):
        if not os.path.exists(path):
            print(f"❌ Fichier introuvable : {path}")
            sys.exit(1)

    compare(FILE_A, FILE_B)


if __name__ == "__main__":
    main()