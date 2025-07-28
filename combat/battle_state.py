



class BattleState:
    def __init__(self, player_team, bot_team):
        self.player_team = player_team
        self.bot_team = bot_team

        self.active_player_index = 0
        self.active_bot_index = 0

        self.player_current_hp = player_team[0]["stats"]["hp"]
        self.bot_current_hp = bot_team[0]["stats"]["hp"]


    @property
    def active_player(self):
        return self.player_team[self.active_player_index]

    @property
    def active_bot(self):
        return self.bot_team[self.active_bot_index]

    def is_player_ko(self):
        return self.player_current_hp <= 0

    def is_bot_ko(self):
        return self.bot_current_hp <= 0

    def switch_player(self):
        if self.active_player_index + 1 < len(self.player_team):
            self.active_player_index += 1
            self.player_current_hp = self.active_player["stats"]["hp"]
            return True
        return False

    def switch_bot(self):
        if self.active_bot_index + 1 < len(self.bot_team):
            self.active_bot_index += 1
            self.bot_current_hp = self.active_bot["stats"]["hp"]
            return True
        return False

    def take_damage(self, target: str, damage: int):
        if target == "player":
            self.player_current_hp = max(0, self.player_current_hp - damage)
        elif target == "bot":
            self.bot_current_hp = max(0, self.bot_current_hp - damage)

    def get_hp(self, target: str):
        return self.player_current_hp if target == "player" else self.bot_current_hp
