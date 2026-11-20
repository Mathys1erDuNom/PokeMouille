# Graph Report - Test-PokeMouille  (2026-11-11)

## Corpus Check
- 228 files · ~229,455 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 6, .ttf 1)

## Summary
- 816 nodes · 1873 edges · 46 communities (35 shown, 11 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 59 edges (avg confidence: 0.86)
- Token cost: 39,147 input · 0 output

## Community Hubs (Navigation)
- Chenil & Egg Hatching
- Inventory View & Spawns
- Guess-the-Pokemon & Raids
- Battle State Engine
- Money Database
- Fishing & Inventory Reads
- News (Actu) Event
- Dice Game (Plus ou Moins)
- Croco Event
- Badges & Battle Limits DB
- Badge View
- Bot Admin & Climate Commands
- Pokedex & Captures
- Shop View
- Investigation (Enquete) Event
- Inventory DB & Dupont Event
- Wheel Game (Roue)
- Opponents & Pokemon Display
- Battle Menu Selection
- Casino Lobby View
- Slot Machine
- Bot Core Helpers
- Black Market Shop
- Spawning & IVs
- Region Selection
- Climate Event Loop
- Casino Modules
- Bot Event Loop & Black Market Hours
- Opponent Select by Region
- Damage & Type Effectiveness
- Shiny & Name Check Scripts
- Card Game Buttons
- Python Dependencies
- Quiz Spawn Event
- XP Evolution Script
- Card Colour Game
- Gen 5 PokeAPI Import
- Pokemon File Adapter Script
- Fence (Receleur) Selling
- Legacy DB (avant modif)
- Type Accent Normaliser
- README Redeploy Trigger

## God Nodes (most connected - your core abstractions)
1. `get_balance()` - 45 edges
2. `add_money()` - 24 edges
3. `save_new_capture()` - 23 edges
4. `is_croco()` - 22 edges
5. `remove_money()` - 21 edges
6. `run_interaction_personnage()` - 21 edges
7. `add_item()` - 19 edges
8. `start_battle_turn_based()` - 19 edges
9. `get_new_captures()` - 19 edges
10. `get_inventory()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `callback()` --calls--> `spawn_pokemon()`  [INFERRED]
  event/quiz_spawn.py → bot.py
- `inventaire()` --indirect_call--> `spawn_pokemon_for_user()`  [INFERRED]
  BDD/inventory_view.py → utils.py
- `callback()` --calls--> `spawn_pokemon()`  [INFERRED]
  event/devine_poke.py → bot.py
- `battle()` --uses--> `SelectionView`  [INFERRED]
  bot.py → combat/menu_combat.py
- `setup_badges()` --calls--> `is_croco()`  [EXTRACTED]
  BDD/badge_view.py → utils.py

## Import Cycles
- None detected.

## Communities (46 total, 11 thin omitted)

### Community 0 - "Chenil & Egg Hatching"
Cohesion: 0.07
Nodes (30): add_egg_xp(), get_chenil_pokemon(), get_random_egg_pokemon(), hatch_egg_with_shiny_check(), remove_chenil_pokemon(), set_chenil_pokemon(), setup_chenil(), add_chenil_xp_cmd() (+22 more)

### Community 1 - "Inventory View & Spawns"
Cohesion: 0.06
Nodes (17): delete_inventory(), draw_multiline_text(), get_pokemon_image_embed(), _handle_spawn(), InventoryItemButton, InventoryNextButton, InventoryPrevButton, InventoryView (+9 more)

### Community 2 - "Guess-the-Pokemon & Raids"
Cohesion: 0.08
Nodes (26): load_pokemon_data(), setup_guess_pokemon_command(), devine(), __init__(), run_devine(), calculate_raid_damage(), _get_stat(), _load_json() (+18 more)

### Community 3 - "Battle State Engine"
Cohesion: 0.08
Nodes (10): BattleState, build_turn_embed(), _format_damage_line(), prompt_player_action(), start_battle_turn_based(), AttackButton, AttackOrSwitchView, SwitchButton (+2 more)

### Community 4 - "Money Database"
Cohesion: 0.11
Nodes (18): add_money(), get_balance(), remove_money(), set_money(), transfer_money(), setup_money(), addmoney(), money() (+10 more)

### Community 5 - "Fishing & Inventory Reads"
Cohesion: 0.08
Nodes (16): get_inventory(), ask_rod_choice(), __init__(), get_available_rods(), get_user_region_with_cursor(), load_fishing_items(), load_rod_data(), save_fish_capture() (+8 more)

### Community 6 - "News (Actu) Event"
Cohesion: 0.09
Nodes (18): add_item_to_inventory(), get_user_item_names(), get_user_region(), is_croco(), item_embed(), load_actu_messages(), load_lieu_objets(), load_lieu_pokemon() (+10 more)

### Community 7 - "Dice Game (Plus ou Moins)"
Cohesion: 0.11
Nodes (8): DiceGame, EqualButton, ExactButton, ExactTotalButton, HighButton, HighLowButton, LowButton, ReplayButton

### Community 8 - "Croco Event"
Cohesion: 0.13
Nodes (12): setup_croco_event(), croco_minutely_event(), croco_now(), croco_status(), get_channels(), is_croco_only(), _send_dm_or_fallback(), get_french_move_name() (+4 more)

### Community 9 - "Badges & Battle Limits DB"
Cohesion: 0.13
Nodes (8): can_battle(), _get_connection(), get_daily_attempts(), increment_daily_attempts(), increment_daily_victories(), _init_table(), reset_daily_battles(), delete_capture()

### Community 10 - "Badge View"
Cohesion: 0.14
Nodes (15): get_user_badges(), give_badge(), remove_user_badge(), BadgeInfoButton, create_badge_mosaic(), setup_badges(), badge(), givebadge() (+7 more)

### Community 11 - "Bot Admin & Climate Commands"
Cohesion: 0.12
Nodes (15): ban(), battle(), capture(), climat_force(), climat_list(), climat_off(), climat_on(), climat_status() (+7 more)

### Community 12 - "Pokedex & Captures"
Cohesion: 0.13
Nodes (9): normalize_text(), get_captures(), create_mosaic(), PokedexNextButton, PokedexPrevButton, PokedexView, PokemonButton, setup_pokedex() (+1 more)

### Community 13 - "Shop View"
Cohesion: 0.11
Nodes (8): BuyItemButton, setup_shop(), boutique(), shop(), ShopItemButton, ShopNextButton, ShopPrevButton, ShopView

### Community 14 - "Investigation (Enquete) Event"
Cohesion: 0.21
Nodes (13): load_item(), make_command(), _command(), PreuvesView, setup_enquete(), preuves(), supprimer_preuves(), add_preuve() (+5 more)

### Community 15 - "Inventory DB & Dupont Event"
Cohesion: 0.18
Nodes (12): add_item(), use_item(), donner_recompense(), run_interaction_personnage(), argent_callback(), _disable_all(), __init__(), item_callback() (+4 more)

### Community 16 - "Wheel Game (Roue)"
Cohesion: 0.14
Nodes (7): get_items(), _build_odds_table(), build_wheel_visual(), get_winning_index(), RoueView, SpinAgainButton, SpinButton

### Community 17 - "Opponents & Pokemon Display"
Cohesion: 0.14
Nodes (7): get_adversaire_by_name(), get_all_adversaires(), create_pokemon_embed(), generate_gen5_json(), get_pokemon_data(), main(), modifier_stats_pokemon()

### Community 18 - "Battle Menu Selection"
Cohesion: 0.14
Nodes (6): NextButton, SelectionView, SelectionView2, SlotSelect, ValidateButton, get_new_captures()

### Community 19 - "Casino Lobby View"
Cohesion: 0.14
Nodes (5): CardGameButton, CasinoView, DiceGameButton, SlotMachineButton, WheelButton

### Community 20 - "Slot Machine"
Cohesion: 0.15
Nodes (3): PlayAgainButton, SlotMachine, SpinButton

### Community 21 - "Bot Core Helpers"
Cohesion: 0.14
Nodes (8): before_check_voice(), catch(), catch_error(), get_background_image_for_pokemon(), is_under_ban(), _norm(), reset_spawn(), save_capture()

### Community 22 - "Black Market Shop"
Cohesion: 0.17
Nodes (4): AcheterMarcheNoirButton, MarcheNoirIntroView, MarcheNoirItemButton, MarcheNoirView

### Community 23 - "Spawning & IVs"
Cohesion: 0.17
Nodes (9): apply_ivs(), check_voice_channel(), generate_ivs(), spawn_pokemon(), wait_and_spawn_dm(), callback(), filter_pools_by_types(), get_allowed_types_for_current_state() (+1 more)

### Community 24 - "Region Selection"
Cohesion: 0.22
Nodes (6): get_connection(), get_user_region(), RegionSelect, RegionView, set_user_region(), setup_regions()

### Community 25 - "Climate Event Loop"
Cohesion: 0.26
Nodes (5): _climate_loop(), _normalize_type(), _pokemon_has_type(), setup_event_climatique(), _start_task_on_ready()

### Community 27 - "Bot Event Loop & Black Market Hours"
Cohesion: 0.20
Nodes (7): auto_event_loop(), is_marche_noir_available(), on_message(), on_ready(), run_marche_noir(), setup_marche_noir(), marche_noir()

### Community 28 - "Opponent Select by Region"
Cohesion: 0.24
Nodes (5): AdversaireSelect, get_adversaire_by_name(), get_adversaires_by_region(), setup_region(), region()

### Community 29 - "Damage & Type Effectiveness"
Cohesion: 0.31
Nodes (6): calculate_damage(), describe_effectiveness(), get_attack_info(), _norm(), _type_effectiveness(), clean_text()

### Community 30 - "Shiny & Name Check Scripts"
Cohesion: 0.31
Nodes (5): compare(), load_names(), main(), main(), make_shiny()

### Community 32 - "Python Dependencies"
Cohesion: 0.31
Nodes (9): requirements.txt (Python dependencies), aiohttp, datetime, discord.py, Pillow, psycopg2-binary, python-dotenv, pytz (+1 more)

### Community 33 - "Quiz Spawn Event"
Cohesion: 0.32
Nodes (6): load_questions(), setup_quiz_commands(), callback(), __init__(), quiz(), run_quiz()

### Community 34 - "XP Evolution Script"
Cohesion: 0.39
Nodes (4): main(), process_file(), sum_stats(), update_xp_evo()

### Community 36 - "Gen 5 PokeAPI Import"
Cohesion: 0.38
Nodes (3): create_mosaic(), generate_gen5_json(), get_pokemon_data()

### Community 37 - "Pokemon File Adapter Script"
Cohesion: 0.43
Nodes (4): adapt(), get_next_evo(), main(), sum_stats()

## Knowledge Gaps
- **4 isolated node(s):** `README (trigger redeploy)`, `python-dotenv`, `Pillow`, `psycopg2-binary`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 242 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_balance()` connect `Money Database` to `Card Colour Game`, `Fishing & Inventory Reads`, `Fence (Receleur) Selling`, `Dice Game (Plus ou Moins)`, `Shop View`, `Inventory DB & Dupont Event`, `Wheel Game (Roue)`, `Casino Lobby View`, `Slot Machine`, `Black Market Shop`, `Casino Modules`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `get_balance()` (e.g. with `.callback()` and `.entrer()`) actually correct?**
  _`get_balance()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `README (trigger redeploy)`, `python-dotenv`, `Pillow` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Chenil & Egg Hatching` be split into smaller, more focused modules?**
  _Cohesion score 0.06836158192090395 - nodes in this community are weakly interconnected._
- **Why does `add_money()` connect `Money Database` to `Card Colour Game`, `Battle State Engine`, `Fence (Receleur) Selling`, `Badge View`, `Inventory DB & Dupont Event`, `Wheel Game (Roue)`, `Slot Machine`, `Bot Core Helpers`, `Casino Modules`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Should `Inventory View & Spawns` be split into smaller, more focused modules?**
  _Cohesion score 0.061170212765957445 - nodes in this community are weakly interconnected._
- **Why does `DiceGame` connect `Dice Game (Plus ou Moins)` to `Casino Modules`, `Casino Lobby View`, `Money Database`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._