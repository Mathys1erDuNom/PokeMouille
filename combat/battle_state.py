# battle_state.py

class BattleState:
    def __init__(self, player_team, bot_team):
        # Assure que les équipes sont toujours des listes
        self.player_team = player_team or []
        self.bot_team = bot_team or []

        self.active_player_index = 0
        self.active_bot_index = 0

        # Pool de PV initialisée ou vide si aucune équipe
        self.player_hp_pool = [p["stats"]["hp"] for p in self.player_team]
        self.bot_hp_pool = [p["stats"]["hp"] for p in self.bot_team]

    # ======================
    # Actifs sécurisés
    # ======================
    @property
    def active_player(self):
        if not self.player_team:
            return None
        if self.active_player_index < 0 or self.active_player_index >= len(self.player_team):
            return None
        return self.player_team[self.active_player_index]

    @property
    def active_bot(self):
        if not self.bot_team:
            return None
        if self.active_bot_index < 0 or self.active_bot_index >= len(self.bot_team):
            return None
        return self.bot_team[self.active_bot_index]

    # ======================
    # États KO
    # ======================
    def is_player_ko(self):
        return self.get_hp("player") <= 0

    def is_bot_ko(self):
        return self.get_hp("bot") <= 0

    # ======================
    # Switch joueur
    # ======================
    def can_switch_player_to(self, new_index: int) -> bool:
        if new_index < 0 or new_index >= len(self.player_team):
            return False
        if new_index == self.active_player_index:
            return False
        return self.player_hp_pool[new_index] > 0

    def switch_player_to(self, new_index: int) -> bool:
        if self.can_switch_player_to(new_index):
            self.active_player_index = new_index
            return True
        return False

    def switch_player(self):
        """
        Switch automatique vers le premier Pokémon vivant.
        Ne modifie PAS l'index si aucun Pokémon valide.
        """
        for i in range(len(self.player_team)):
            if self.player_hp_pool[i] > 0:
                self.active_player_index = i
                return True
        return False

    # ======================
    # Switch bot
    # ======================
    def switch_bot(self):
        """
        Switch automatique du bot vers le premier Pokémon vivant.
        Ne modifie PAS l'index si aucun Pokémon valide.
        """
        for i in range(len(self.bot_team)):
            if self.bot_hp_pool[i] > 0:
                self.active_bot_index = i
                return True
        return False

    # ======================
    # Dégâts / PV
    # ======================
    def take_damage(self, target: str, damage: int):
        damage = max(0, int(damage))  # S'assure que les dégâts sont positifs

        if target == "player":
            if self.active_player_index < len(self.player_hp_pool):
                self.player_hp_pool[self.active_player_index] = max(
                    0,
                    self.player_hp_pool[self.active_player_index] - damage
                )

        elif target == "bot":
            if self.active_bot_index < len(self.bot_hp_pool):
                self.bot_hp_pool[self.active_bot_index] = max(
                    0,
                    self.bot_hp_pool[self.active_bot_index] - damage
                )

    def get_hp(self, target: str):
        if target == "player":
            if self.active_player_index >= len(self.player_hp_pool):
                return 0
            return self.player_hp_pool[self.active_player_index]

        elif target == "bot":
            if self.active_bot_index >= len(self.bot_hp_pool):
                return 0
            return self.bot_hp_pool[self.active_bot_index]

        return 0
