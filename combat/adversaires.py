import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
ADVERSAIRES_FILE = os.path.join(script_dir, "../json/adversaires.json")  # ton fichier JSON

def get_all_adversaires():
    with open(ADVERSAIRES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_adversaire_by_name(name: str):
    adversaires = get_all_adversaires()
    for adv in adversaires:
        if adv["name"].lower() == name.lower():
            return adv
    return None
