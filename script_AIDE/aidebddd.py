import json

# fichiers
input_file = "json/pokemon_gen4_normal.json"
output_file = "pokemon_gen4_shiny.json"

# charger les pokemon normaux
with open(input_file, "r", encoding="utf-8") as f:
    pokemons = json.load(f)

shiny_pokemons = []

for pokemon in pokemons:
    shiny_pokemon = pokemon.copy()

    # modifier le nom
    shiny_pokemon["name"] = pokemon["name"] + "_shiny"

    # modifier l'image (ajouter /shiny/)
    shiny_pokemon["image"] = pokemon["image"].replace(
        "/pokemon/", "/pokemon/shiny/"
    )

    shiny_pokemons.append(shiny_pokemon)

# sauvegarder
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(shiny_pokemons, f, indent=4, ensure_ascii=False)

print("Fichier shiny généré :", output_file)