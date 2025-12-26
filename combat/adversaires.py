import json
import os
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADVERSAIRES_FILE = os.path.join(BASE_DIR, "json", "adversaires.json")


def load_adversaires():
    with open(ADVERSAIRES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_random_adversaire():
    adversaires = load_adversaires()
    return random.choice(adversaires)
