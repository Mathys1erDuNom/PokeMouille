import requests
import json
import time

# Pokémon de la génération 5 (Sinnoh) : IDs 494 à 649
GEN4_START = 387
GEN4_END = 493

# Mapping des types anglais -> français
TYPE_TRANSLATION = {
    "normal": "normal",
    "fighting": "combat",
    "flying": "vol",
    "poison": "poison",
    "ground": "sol",
    "rock": "roche",
    "bug": "insecte",
    "ghost": "spectre",
    "steel": "acier",
    "fire": "feu",
    "water": "eau",
    "grass": "plante",
    "electric": "electrique",
    "psychic": "psy",
    "ice": "glace",
    "dragon": "dragon",
    "dark": "tenebres",
    "fairy": "fee"
}

def get_pokemon_data(pokemon_id):
    """Récupère les données d'un Pokémon via PokeAPI"""
    try:
        # Données du Pokémon
        url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
        response = requests.get(url)
        data = response.json()
        
        # Nom en français
        species_url = data['species']['url']
        species_response = requests.get(species_url)
        species_data = species_response.json()
        
        french_name = None
        for name_entry in species_data['names']:
            if name_entry['language']['name'] == 'fr':
                french_name = name_entry['name']
                break
        
        if not french_name:
            french_name = data['name'].capitalize()
        
        # Types en français
        types = []
        for type_entry in data['types']:
            type_name = type_entry['type']['name']
            types.append(TYPE_TRANSLATION.get(type_name, type_name))
        
        # Stats
        stats = {}
        for stat in data['stats']:
            stat_name = stat['stat']['name']
            if stat_name == 'hp':
                stats['hp'] = stat['base_stat']
            elif stat_name == 'attack':
                stats['attack'] = stat['base_stat']
            elif stat_name == 'defense':
                stats['defense'] = stat['base_stat']
            elif stat_name == 'special-attack':
                stats['special_attack'] = stat['base_stat']
            elif stat_name == 'special-defense':
                stats['special_defense'] = stat['base_stat']
            elif stat_name == 'speed':
                stats['speed'] = stat['base_stat']
        
        # Attaques en français (prend les 2-3 premières attaques apprises)
        attacks = []
        move_count = 0
        for move_entry in data['moves']:
            if move_count >= 3:
                break
            
            # Récupère le nom en français
            move_url = move_entry['move']['url']
            move_response = requests.get(move_url)
            move_data = move_response.json()
            
            for name_entry in move_data['names']:
                if name_entry['language']['name'] == 'fr':
                    attacks.append(name_entry['name'])
                    move_count += 1
                    break
        
        # Si pas assez d'attaques, ajouter "Charge" par défaut
        if len(attacks) < 2:
            attacks.append("Charge")
        
        # Image SHINY
        image = data['sprites']['front_shiny']
        
        pokemon_data = {
            "name": french_name + "_shiny",
            "type": types,
            "image": image,
            "attacks": attacks,
            "stats": stats
        }
        
        print(f"✅ {french_name} (#{pokemon_id}) récupéré")
        return pokemon_data
        
    except Exception as e:
        print(f"❌ Erreur pour le Pokémon #{pokemon_id}: {e}")
        return None

def generate_gen5_json():
    """Génère le fichier JSON pour la génération 4 SHINY"""
    pokemon_list = []
    
    print("✨ Récupération des Pokémon SHINY de la 4G (Sinnoh)...")
    print(f"📊 Pokémon {GEN4_START} à {GEN4_END}")
    print("-" * 50)
    
    for pokemon_id in range(GEN4_START, GEN4_END + 1):
        pokemon_data = get_pokemon_data(pokemon_id)
        if pokemon_data:
            pokemon_list.append(pokemon_data)
        

    
    # Sauvegarde dans un fichier JSON
    output_file = "pokemon_gen4_shiny.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pokemon_list, f, ensure_ascii=False, indent=4)
    
    print("-" * 50)
    print(f"✅ Fichier généré : {output_file}")
    print(f"📦 {len(pokemon_list)} Pokémon shiny enregistrés")

if __name__ == "__main__":
    generate_gen5_json()