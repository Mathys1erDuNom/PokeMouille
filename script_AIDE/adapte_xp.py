"""
update_xp_evo.py
────────────────
Met à jour le champ xp_evo de chaque Pokémon dans tous les fichiers JSON.
La nouvelle valeur = somme de toutes les stats de base (hp + attack + special_attack + speed + defense + special_defense)

Fichiers traités : json/new_pokemons/pokemon_gen*_*.json
"""
import json
import os
import glob

# ── Répertoires ────────────────────────────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir   = os.path.join(script_dir, "..")
JSON_DIR   = os.path.join(root_dir, "json", "new_pokemons")
# ──────────────────────────────────────────────────────────────────────────────

def sum_stats(stats: dict) -> int:
    """Calcule la somme de toutes les stats de base."""
    return sum(stats.values())

def update_xp_evo(pokemon: dict) -> dict:
    p = dict(pokemon)
    stats = p.get("stats", {})
    if stats:
        p["xp_evo"] = sum_stats(stats)
    return p

def process_file(filepath: str) -> None:
    with open(filepath, "r", encoding="utf-8") as f:
        pokemons = json.load(f)

    updated = [update_xp_evo(p) for p in pokemons]

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=4)

    print(f"[OK] {len(updated):>3} Pokémons mis à jour → {os.path.basename(filepath)}")

def main():
    pattern = os.path.join(JSON_DIR, "pokemon_gen5_normal.json")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"❌ Aucun fichier trouvé dans : {JSON_DIR}")
        return

    print(f"📂 {len(files)} fichier(s) trouvé(s) dans {JSON_DIR}\n")
    total = 0
    for filepath in files:
        process_file(filepath)
        total += 1

    print(f"\n✅ {total} fichier(s) traité(s). xp_evo = somme des stats pour tous les Pokémons.")

if __name__ == "__main__":
    main()