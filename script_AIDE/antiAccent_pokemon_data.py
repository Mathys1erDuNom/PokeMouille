import json
import unicodedata
import os

def clean_text(text):
    # Supprime les accents
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

# Chemin du fichier
fichier = "pokemon_shiny_data.json"

# Chargement du fichier
with open(fichier, "r", encoding="utf-8") as f:
    data = json.load(f)

# Nettoyage des noms et attaques
for pokemon in data:
    pokemon["name"] = clean_text(pokemon["name"])
    pokemon["attacks"] = [clean_text(attaque) for attaque in pokemon["attacks"]]

# Sauvegarde
with open(fichier, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("pokemon_data.json nettoyé avec succès.")
