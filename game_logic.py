import random

SUITS = ["♠️", "♥️", "♦️", "♣️"]
RANKS = ["6", "7", "8", "9", "10", "В", "Д", "К", "Т"]
RANK_VALUES = {rank: i for i, rank in enumerate(RANKS)}


class DurakGame:
    def __init__(self, room_id, player1_id, player1_name):
        self.room_id = room_id
        self.players = {
            player1_id: {"name": player1_name, "hand": [], "msg_id": None}
        }
        self.player_ids = [player1_id]
        self.deck = [(r, s) for s in SUITS for r in RANKS]
        random.shuffle(self.deck)

        self.trump_card = self.deck[0]
        self.trump_suit = self.trump_card[1]

        self.table = []
        self.attacker_idx = 0
        self.is_started = False
        self.winner = None

    def add_player(self, player2_id, player2_name):
        if len(self.players) < 2 and player2_id not in self.players:
            self.players[player2_id] = {"name": player2_name, "hand": [], "msg_id": None}
            self.player_ids.append(player2_id)
            self.is_started = True
            self.deal_cards()
            self._set_first_attacker()
            return True
        return False

    def _set_first_attacker(self):
        min_trump = 99
        for idx, pid in enumerate(self.player_ids):
            for r, s in self.players[pid]["hand"]:
                if s == self.trump_suit and RANK_VALUES[r] < min_trump:
                    min_trump = RANK_VALUES[r]
                    self.attacker_idx = idx

    def deal_cards(self):
        order = [self.player_ids[self.attacker_idx], self.player_ids[1 - self.attacker_idx]]
        for pid in order:
            while len(self.players[pid]["hand"]) < 6 and self.deck:
                self.players[pid]["hand"].append(self.deck.pop())

    @property
    def attacker_id(self):
        return self.player_ids[self.attacker_idx]

    @property
    def defender_id(self):
        return self.player_ids[1 - self.attacker_idx]

    def can_attack(self, card):
        if not self.table:
            return True
        table_ranks = {c[0] for pair in self.table for c in pair if c is not None}
        return card[0] in table_ranks

    def can_beat(self, attack_card, defense_card):
        a_rank, a_suit = attack_card
        d_rank, d_suit = defense_card
        if a_suit == d_suit:
            return RANK_VALUES[d_rank] > RANK_VALUES[a_rank]
        if d_suit == self.trump_suit and a_suit != self.trump_suit:
            return True
        return False

    def make_move(self, player_id, card_idx):
        hand = self.players[player_id]["hand"]
        if card_idx < 0 or card_idx >= len(hand):
            return False, "Невірна карта"

        card = hand[card_idx]

        if player_id == self.attacker_id:
            unbeaten = sum(1 for _, d in self.table if d is None)
            if unbeaten >= len(self.players[self.defender_id]["hand"]):
                return False, "У суперника не вистачить карт відбитись!"
            if len(self.table) >= 6:
                return False, "На столі вже максимум карт (6)"
            if not self.can_attack(card):
                return False, "Цю карту не можна підкинути!"

            hand.pop(card_idx)
            self.table.append((card, None))
            self.check_winner()
            return True, "Хід зроблено"

        elif player_id == self.defender_id:
            for i, (a_card, d_card) in enumerate(self.table):
                if d_card is None:
                    if self.can_beat(a_card, card):
                        hand.pop(card_idx)
                        self.table[i] = (a_card, card)
                        self.check_winner()
                        return True, "Карту побито"
                    else:
                        return False, "Ця карта не б'є атаку!"
            return False, "Зараз нічого бити"

        return False, "Не твій хід"

    def action_bito(self, player_id):
        if player_id != self.attacker_id or not self.table:
            return False, "Зараз не можна сказати Бито"
        if any(d is None for _, d in self.table):
            return False, "Ще не всі карти побиті!"

        self.table.clear()
        self.deal_cards()
        self.attacker_idx = 1 - self.attacker_idx
        self.check_winner()
        return True, "Бито!"

    def action_take(self, player_id):
        if player_id != self.defender_id:
            return False, "Ти зараз не захищаєшся"
        if not any(d is None for _, d in self.table):
            return False, "Всі карти вже побиті"

        for a_card, d_card in self.table:
            self.players[player_id]["hand"].append(a_card)
            if d_card:
                self.players[player_id]["hand"].append(d_card)

        self.table.clear()
        self.deal_cards()
        self.check_winner()
        return True, "Гравець забрав карти"

    def check_winner(self):
        if not self.deck:
            for pid in self.player_ids:
                if len(self.players[pid]["hand"]) == 0:
                    self.winner = self.players[pid]["name"]