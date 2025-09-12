# utils.py
import random
import json
import os
import unicodedata

# ------------ Chargement unique des données d'attaques ------------
script_dir = os.path.dirname(os.path.abspath(__file__))
attack_data_path = os.path.join(script_dir, "..", "json", "attack_data.json")

with open(attack_data_path, encoding="utf-8") as f:
    all_attacks = json.load(f)

# ------------ Normalisation (sans accents, minuscule) ------------
def _norm(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return s.lower().strip()

# ------------ Table d’efficacité des types (FR) ------------
# x2 = super efficace ; x0.5 = peu efficace ; x0 = aucun effet (immunité)
TYPE_CHART = {
    "normal":   {"x2": [], "x0.5": ["roche", "acier"], "x0": ["spectre"]},
    "feu":      {"x2": ["plante", "glace", "insecte", "acier"], "x0.5": ["feu", "eau", "roche", "dragon"], "x0": []},
    "eau":      {"x2": ["feu", "sol", "roche"], "x0.5": ["eau", "plante", "dragon"], "x0": []},
    "plante":   {"x2": ["eau", "sol", "roche"], "x0.5": ["feu", "plante", "poison", "vol", "dragon", "acier", "insecte"], "x0": []},
    "electrique":{"x2": ["eau", "vol"], "x0.5": ["electrique", "plante", "dragon"], "x0": ["sol"]},
    "glace":    {"x2": ["plante", "sol", "vol", "dragon"], "x0.5": ["feu", "eau", "glace", "acier"], "x0": []},
    "combat":   {"x2": ["normal", "glace", "roche", "tenebres", "acier"], "x0.5": ["poison", "vol", "psy", "insecte", "fee"], "x0": ["spectre"]},
    "poison":   {"x2": ["plante", "fee"], "x0.5": ["poison", "sol", "roche", "spectre"], "x0": ["acier"]},
    "sol":      {"x2": ["feu", "electrique", "poison", "roche", "acier"], "x0.5": ["plante", "insecte"], "x0": ["vol"]},
    "vol":      {"x2": ["plante", "combat", "insecte"], "x0.5": ["electrique", "roche", "acier"], "x0": []},
    "psy":      {"x2": ["combat", "poison"], "x0.5": ["psy", "acier"], "x0": ["tenebres"]},
    "insecte":  {"x2": ["plante", "psy", "tenebres"], "x0.5": ["feu", "combat", "vol", "poison", "spectre", "acier", "fee"], "x0": []},
    "roche":    {"x2": ["feu", "glace", "vol", "insecte"], "x0.5": ["combat", "sol", "acier"], "x0": []},
    "spectre":  {"x2": ["psy", "spectre"], "x0.5": ["tenebres"], "x0": ["normal"]},
    "dragon":   {"x2": ["dragon"], "x0.5": ["acier"], "x0": ["fee"]},
    "tenebres": {"x2": ["psy", "spectre"], "x0.5": ["combat", "tenebres", "fee"], "x0": []},
    "acier":    {"x2": ["glace", "roche", "fee"], "x0.5": ["feu", "eau", "electrique", "acier"], "x0": []},
    "fee":      {"x2": ["combat", "dragon", "tenebres"], "x0.5": ["feu", "poison", "acier"], "x0": []},
}

# ------------ Utilitaires attaques ------------
def get_attack_info(name):
    for attack in all_attacks:
        if attack.get("name", "").lower() == str(name).lower():
            return attack
    return None

def _type_effectiveness(attack_type: str, defender_types):
    """Renvoie un multiplicateur (0, 0.5, 1, 2, 4) en cumulant sur 1 ou 2 types."""
    atk = _norm(attack_type)
    chart = TYPE_CHART.get(atk, {"x2": [], "x0.5": [], "x0": []})
    mult = 1.0
    for t in defender_types or []:
        dt = _norm(t)
        if dt in chart["x0"]:
            return 0.0
        if dt in chart["x2"]:
            mult *= 2.0
        elif dt in chart["x0.5"]:
            mult *= 0.5
    return mult

# ------------ Calcul des dégâts ------------


def calculate_damage(attacker, defender, attack_name, return_details: bool = False):
    """
    Si return_details=False (par défaut) -> int
    Si return_details=True  -> dict:
        {
          "damage": int,
          "crit": bool,
          "eff_multiplier": float,
          "eff_label": str,     # 'super efficace', 'peu efficace', 'aucun effet', 'efficacité normale'
          "stab": bool,
          "variance": float,    # ~0.85..1.0
          "category": 'physique'|'speciale',
          "power": int,
          "attack_type": str
        }
    """
    attack_info = get_attack_info(attack_name)
    if not attack_info:
        dmg = random.randint(5, 10)
        if not return_details:
            return dmg
        return {
            "damage": dmg, "crit": False, "eff_multiplier": 1.0, "eff_label": "efficacité normale",
            "stab": False, "variance": 1.0, "category": "", "power": 0, "attack_type": "normal"
        }

    raw_cat = (attack_info.get("category") or attack_info.get("categorie") or "").lower()
    category = "physique" if raw_cat == "physique" else ("speciale" if raw_cat in ("speciale", "special") else "")
    try:
        power = int(attack_info.get("damage", 50))
    except (TypeError, ValueError):
        power = 50

    attack_type = _norm(attack_info.get("type", "normal"))

    if category == "physique":
        atk_stat = attacker["stats"].get("attack", 50)
        def_stat = defender["stats"].get("defense", 50)
    elif category == "speciale":
        atk_stat = attacker["stats"].get("special_attack", 50)
        def_stat = defender["stats"].get("special_defense", 50)
    else:
        if power >= 60:
            atk_stat = attacker["stats"].get("attack", 50)
            def_stat = defender["stats"].get("defense", 50)
        else:
            atk_stat = attacker["stats"].get("special_attack", 50)
            def_stat = defender["stats"].get("special_defense", 50)

    attacker_types = [_norm(t) for t in (attacker.get("type") or [])]
    stab_flag = attack_type in attacker_types
    stab = 1.5 if stab_flag else 1.0

    eff = _type_effectiveness(attack_type, defender.get("type") or [])

    crit_flag = (random.randint(1, 16) == 1)
    crit = 1.5 if crit_flag else 1.0
    variance = random.uniform(0.85, 1.00)

    level = 50
    core = (((2 * level / 5 + 2) * power * (atk_stat / max(1, def_stat))) / 50) + 2
    modifier = stab * eff * crit * variance

    # Immunité: dégâts 0, mais on renvoie tout de même le breakdown cohérent
    if eff == 0.0:
        dmg = 0
    else:
        dmg = int(max(1, core * modifier))

    if not return_details:
        return dmg

    return {
        "damage": dmg,
        "crit": bool(crit_flag),
        "eff_multiplier": float(eff),
        "eff_label": describe_effectiveness(eff),
        "stab": stab_flag,
        "variance": float(variance),
        "category": category or ("physique" if power >= 60 else "speciale"),
        "power": power,
        "attack_type": attack_type
    }

# (Optionnel) Utilitaire si tu veux afficher l’info d’efficacité/crit ailleurs
def describe_effectiveness(mult: float) -> str:
    if mult == 0:
        return "aucun effet"
    if mult < 1:
        return "peu efficace"
    if mult > 1:
        return "super efficace"
    return "efficacité normale"
