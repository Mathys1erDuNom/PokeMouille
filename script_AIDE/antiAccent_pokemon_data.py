import json

def normalize_type(type_name: str) -> str:
    """Met en minuscule et remplace 'électrik'/'electrik' par 'electrique'."""
    t = type_name.lower()
    if t in ["électrik", "electrik"]:
        return "electrique"
    return t

# Nom du fichier à modifier
file_path = "pokemon_gen3_shiny.json"

# Charger le JSON
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Modifier les types
for pokemon in data:
    if "type" in pokemon and isinstance(pokemon["type"], list):
        pokemon["type"] = [normalize_type(t) for t in pokemon["type"]]

# Réécrire directement le même fichier
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"Types corrigés directement dans '{file_path}'")
