import json
from discord import Embed

def create_pokemon_embed(pokemon_name: str, json_file: str, is_shiny: bool = False) -> Embed:
    """
    Crée un embed Discord pour un Pokémon donné depuis un fichier JSON spécifique.

    :param pokemon_name: Nom du Pokémon à afficher
    :param json_file: Chemin vers le fichier JSON contenant les Pokémon
    :param is_shiny: Indique si le Pokémon est shiny
    :return: Un objet discord.Embed prêt à envoyer
    """
    shiny_text = "✨ " if is_shiny else ""

    # Charger le JSON
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            pokemons = json.load(f)
    except Exception as e:
        embed = Embed(
            title="❌ Erreur JSON",
            description=f"Impossible de charger le fichier JSON : {e}",
            color=0xff0000
        )
        return embed

    # Chercher le Pokémon
    pokemon_data = next((p for p in pokemons if p["name"] == pokemon_name), None)

    if not pokemon_data:
        embed = Embed(
            title="❌ Pokémon introuvable",
            description=f"Impossible de trouver le Pokémon {pokemon_name}.",
            color=0xff0000
        )
        return embed

    # Créer l'embed
    embed = Embed(
        title=f"{shiny_text}{pokemon_data['name']}",
        description="🎉 Vous avez gagné ce Pokémon !",
        color=0x00ff00
    )

    # Ajouter l'image si disponible
    if "image" in pokemon_data:
        embed.set_image(url=pokemon_data["image"])

    return embed
