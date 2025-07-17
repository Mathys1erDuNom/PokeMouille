import json
import unicodedata

def clean_text(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

# Chemin vers ton fichier
fichier = "attack_data.json"

# Chargement
with open(fichier, "r", encoding="utf-8") as f:
    data = json.load(f)

# Nettoyage
for attaque in data:
    attaque["name"] = clean_text(attaque["name"])
    attaque["type"] = clean_text(attaque["type"])
    attaque["category"] = clean_text(attaque["category"])
    if "effect" in attaque:
        attaque["effect"] = clean_text(attaque["effect"])

# Sauvegarde
with open(fichier, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("attack_data.json nettoyé avec succès.")
