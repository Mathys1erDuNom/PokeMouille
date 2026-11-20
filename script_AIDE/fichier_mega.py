
import json

# Fichiers
FICHIER_ENTREE = "pokemon_input.json"
FICHIER_SORTIE = "pokemon_output.json"


def convertir_json():
    # Lecture du fichier source
    with open(FICHIER_ENTREE, "r", encoding="utf-8") as fichier:
        donnees = json.load(fichier)

    # Transformation en liste
    pokemon_liste = []

    for pokemon_id, pokemon in donnees.items():
        nouveau_pokemon = pokemon.copy()

        # Réinitialisation de l'expérience d'évolution
        if nouveau_pokemon["name"] == "Mega-Florizarre":
            nouveau_pokemon["xp_evo"] = 0

        pokemon_liste.append(nouveau_pokemon)

    # Écriture du nouveau fichier
    with open(FICHIER_SORTIE, "w", encoding="utf-8") as fichier:
        json.dump(pokemon_liste, fichier, indent=4, ensure_ascii=False)

    print(f"Conversion terminée : {FICHIER_SORTIE}")


if __name__ == "__main__":
    convertir_json()
