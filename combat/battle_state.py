class BattleState:
    def __init__(self, player_team, bot_team):
        self.player_team = player_team
        self.bot_team = bot_team

        self.active_player_index = 0
        self.active_bot_index = 0

        # Initialise les PV de chaque Pokémon individuellement
        self.player_hp_pool = [p["stats"]["hp"] for p in player_team]
        self.bot_hp_pool = [p["stats"]["hp"] for p in bot_team]

    @property
    def active_player(self):
        return self.player_team[self.active_player_index]

    @property
    def active_bot(self):
        return self.bot_team[self.active_bot_index]

    def is_player_ko(self):
        return self.get_hp("player") <= 0

    def is_bot_ko(self):
        return self.get_hp("bot") <= 0

    def switch_player(self):
        while self.active_player_index + 1 < len(self.player_team):
            self.active_player_index += 1
            if self.player_hp_pool[self.active_player_index] > 0:
                return True
        return False


    def switch_bot(self):
        while self.active_bot_index + 1 < len(self.bot_team):
            self.active_bot_index += 1
            if self.bot_hp_pool[self.active_bot_index] > 0:
                return True
        return False



    def take_damage(self, target: str, damage: int):
        if target == "player":
            self.player_hp_pool[self.active_player_index] = max(0, self.player_hp_pool[self.active_player_index] - damage)
        elif target == "bot":
            self.bot_hp_pool[self.active_bot_index] = max(0, self.bot_hp_pool[self.active_bot_index] - damage)

    def get_hp(self, target: str):
        if target == "player":
            return self.player_hp_pool[self.active_player_index]
        elif target == "bot":
            return self.bot_hp_pool[self.active_bot_index]
