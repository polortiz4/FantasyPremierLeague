import numpy as np 
import requests
import time
import types
types.GeneratorType

class TooExpensiveError(RuntimeError):
    pass
class PositionFull(RuntimeError):
    pass
class TeamSpotsFull(RuntimeError):
    pass
class SquadNotFull(RuntimeError):
    pass
class DuplicatePlayer(RuntimeError):
    pass


epsilon = 1e-4

def player_(p_info):
    if p_info['element_type'] == 1:
        position = "goalkeeper"

    if p_info['element_type'] == 2:
        position = "defender"

    if p_info['element_type'] == 3:
        position = "midfielder"

    if p_info['element_type'] == 4:
        position = "striker"

    return player(name=p_info['second_name'], form=float(p_info['form']), price=float(p_info['now_cost'])/10, position=position, team=p_info['team'], id=p_info['id'])

def add_by_last_name(squad, last_name):
    for p in players:
        if p.name == last_name:
            squad.add_player(p)
            return
    raise RuntimeError(f"Couldn't find player: {last_name}")


class player():
    def __init__(self, name, form, price, position, team, id):
        super().__init__()
        self.form = form
        self.price = price
        self.name = name
        self.position = position
        self.team = team
        self.id = id

    def __repr__(self):
        return f"({self.name}, {float(self.form):.2f}, {float(self.price):.2f}, {self.position}, {self.team}, {self.id})"

    def __eq__(self, other):
        return self.name == other.name and self.price == other.price and self.form == other.form and self.position == other.position and self.team == other.team and self.id == other.id


class squad():
    def __init__(self, max_cost=100):
        self.max_cost = max_cost
        self.goalkeepers = []
        self.defenders = []
        self.midfielders = []
        self.strikers = []

    def changes_from(self, other):
        unique_from_self = squad()
        unique_from_other = squad()
        for my_player, other_player in zip(self.players, other.players):
            if my_player not in other.players:
                unique_from_self.add_player(my_player)
            if other_player not in self.players:
                unique_from_other.add_player(other_player)
        for mine, other in zip(unique_from_self.players, unique_from_other.players):
            assert(mine.position == other.position)
            print(f"{mine} <-----------> {other}")

    @property
    def max_cost(self):
        return self._max_cost

    @max_cost.setter
    def max_cost(self, max_cost):
        self._max_cost = max_cost + epsilon

    @property
    def captain(self):
        return max(self.players, key= lambda x: x.form)

    def number_of_changes(self, other):
        diff = 0
        for my_player in self.players:
            c = other.players.count(my_player) 
            if c != 1 and c != 0:
                raise RuntimeError(f"Invalid number of the same player (should be either 0 or one, got: {c}")
            elif c == 0:
                diff += 1
        return diff

    def remove_player(self, player):
        if self.players.count(player) > 0:
            getattr(self, f"{player.position}s").remove(player)

    def players_from_team(self, team):
        total = 0
        for p in self.players:
            if p.team == team:
                total += 1
        return total

    def add_player(self, player):
        if self.players_from_team(player.team) >= 3:
            raise TeamSpotsFull(f"Too many players from team: {player.team}. Already have: {self.players_from_team(player.team)}")

        if self.players.count(player) > 0:
            raise DuplicatePlayer(f"Player {player} is already in the squad")

        if player.price + self.total_cost > self.max_cost:
            raise TooExpensiveError(f"Not enough funds to add {player.name} who costs {player.price} and you have {self.max_cost - self.total_cost}")

        if player.position == "goalkeeper":
            if len(self.goalkeepers) < 2:
                self.goalkeepers.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many goalkeepers: {len(self.goalkeepers)}")

        if player.position == "defender":
            if len(self.defenders) < 5:
                self.defenders.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many defenders: {len(self.defenders)}")

        if player.position == "midfielder":
            if len(self.midfielders) < 5:
                self.midfielders.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many midfielders: {len(self.midfielders)}")

        if player.position == "striker":
            if len(self.strikers) < 3:
                self.strikers.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many strikers: {len(self.strikers)}")

    def validate_cost(self):
        if self.total_cost > self.max_cost:
            raise TooExpensiveError(f"Total Cost: {self.total_cost} > max_cost: {self.max_cost}")
    
    @property
    def positions_full(self):
        return len(self.goalkeepers) == 2 and len(self.defenders) == 5 and len(self.midfielders) == 5 and len(self.strikers) == 3

    def starters(self, player_list, n_starters):
        player_list.sort(reverse=True, key=lambda x: x.form)
        return player_list[:n_starters]

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"Squad with Form: {self.total_form:.2f}, cost: {self.total_cost:.2f}"

    @property
    def starting_goalkeeper(self):
        return self.starters(self.goalkeepers, 1)

    @property
    def players(self):
        return [*self.goalkeepers, *self.defenders, *self.midfielders, *self.strikers]

    @property
    def total_cost(self):
        cost = 0
        for player in self.players:
            cost += player.price
        return cost

    @property
    def leftover_money(self):
        return self.max_cost - self.total_cost

    @property
    def total_form(self, double_captain=True):
        form = 0
        for player in self.players:
            form += player.form
            if double_captain and player == self.captain:
                form += player.form
        return form

    def player_list_form(self, player_list):
        form = 0
        for player in player_list:
            form += player.form
        return form

    @property
    def best_starter_lineup(self):
        form = 0
        possible_lineups = [
            [1, 3, 4, 3], 
            [1, 4, 3, 3], 
            [1, 5, 2, 3], 

            [1, 3, 5, 2],
            [1, 4, 4, 2], 
            [1, 5, 3, 2],

            [1, 5, 4, 1],
            [1, 4, 5, 1]
            ]

        combinations = []
        for lineup in possible_lineups:
            gks = self.starters(self.goalkeepers, lineup[0])
            defs = self.starters(self.defenders, lineup[1])
            mids = self.starters(self.midfielders, lineup[2])
            fors = self.starters(self.strikers, lineup[3])
            # starters = [*gks, *defs, *mids, *fors]
            starting_squad = squad()
            for gk in gks:
                starting_squad.goalkeepers.append(gk)
            for defender in defs:
                starting_squad.defenders.append(defender)
            for mid in mids:
                starting_squad.midfielders.append(mid)
            for forward in fors:
                starting_squad.strikers.append(forward)

            # combinations.append((starters, self.player_list_form(starters)))
            combinations.append(starting_squad)
        combinations.sort(reverse=True, key=lambda x: x.total_form)
        return combinations[0]

    def copy(self):
        other = squad(max_cost=self.max_cost)
        for p in self.players:
            other.add_player(p)
        return other

def fill_squad(squad, available_players, cheapest_cost=None, squad_max_len=15, previous_results=None, current_squad=None, n_free_transfers=None, transfer_cost=4, min_form=None, max_form=None, stack_i=1):
    if cheapest_cost is None:
        cheapest_cost = min(available_players, key=lambda x: x.price).price
    if min_form is None:
        min_form = min(available_players, key=lambda x: x.form).form
    if max_form is None:
        max_form = max(available_players, key=lambda x: x.form).form
    if previous_results is None:
        previous_results = []
    if n_free_transfers is None:
        n_free_transfers = 15
    if current_squad is None:
        n_free_transfers = 15

    if current_squad is not None and squad.number_of_changes(current_squad) > n_free_transfers and max_form - min_form < transfer_cost:  # Assumption: minimum form is 4
        raise SquadNotFull(f"Squad not full")

    len_players = len(squad.players)
    if len_players + len(available_players) < squad_max_len:
        raise SquadNotFull(f"Not enough Players")

    for i, p in enumerate(available_players):
        if p in squad.players:
            continue
        if len_players < squad_max_len - 1 and (squad.max_cost - (squad.total_cost + p.price)) / (squad_max_len - 1 - len_players) <= cheapest_cost:
            continue
        if squad.total_cost + p.price > squad.max_cost:
            continue

        try:
            squad.add_player(p)
            if squad.positions_full:
                if previous_results.count(squad) == 0:
                    yield squad
                    previous_results.append(squad.copy())
            else:
                if len(available_players) == i+1:
                    squad.remove_player(p)
                    raise SquadNotFull(f"Squad not full")
                try:
                    # Assumption: available_players is sorted by form
                    nested_gen = fill_squad(squad, available_players[i+1:], cheapest_cost, previous_results=previous_results, current_squad=current_squad, n_free_transfers=n_free_transfers, min_form=min_form, max_form=available_players[i+1].form, stack_i=stack_i+1)
                    yield from nested_gen
                except SquadNotFull:
                    pass
        except PositionFull:
            continue 
        except TeamSpotsFull:
            continue
        squad.remove_player(p)

    raise SquadNotFull(f"Squad not full")
    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--gameweek', help='last week\'s gameweek number', required=True)
    parser.add_argument('--free-transfers',  default=1, help="number of free transfers available")
    parser.add_argument('--min-player-form',  default=4, help="minimum acceptable player form")
    parser.add_argument('--overwrite-pulled-team', action="store_true", help="True if you want to build your current squad manually instead of pulling, team would have to be hardcoded")

    args = vars(parser.parse_args())

    n_free_transfers = args['free_transfers']
    transfer_cost = 4
    min_acceptable_form = args['min_player_form']
    current_gameweek = args['gameweek']
    user_id = 3521386

    player_info_url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    my_team_url = f'https://fantasy.premierleague.com/api/entry/{user_id}/event/{current_gameweek}/picks/'
    login_url = "https://users.premierleague.com/accounts/login/"

    payload = {
        'login': "polortiz_4@hotmail.com",
        'password': "@8j$*qiDew9pKs",
        'redirect_uri': 'https://fantasy.premierleague.com/',
        'app':'plfpl-web'
    }
    s = requests.session()
    s.post(login_url, data=payload)

    r = s.get(my_team_url)
    my_team_json = r.json()

    r = s.get(player_info_url)
    json = r.json()

    players_json = json['elements']
    players_json.sort(reverse=True, key=lambda x: float(x['form']))

    players = []
    current_squad = squad(max_cost=1000)
    for p in players_json:
        pp = player_(p)
        if pp.id in [o['element'] for o in my_team_json['picks']]:
            players.append(pp)
            current_squad.add_player(pp)
        elif pp.form > min_acceptable_form:
            players.append(pp)
    current_squad.max_cost = my_team_json['entry_history']['bank']/10 + current_squad.total_cost

    if args['overwrite_pulled_team']:
        money_in_bank = 0.3
        current_squad(max_cost=1000)
        add_by_last_name(current_squad, "Pope")
        add_by_last_name(current_squad, "Meslier")
        add_by_last_name(current_squad, "Robertson")
        add_by_last_name(current_squad, "Bednarek")
        add_by_last_name(current_squad, "Aurier")
        add_by_last_name(current_squad, "Dier")
        add_by_last_name(current_squad, "Ogbonna")
        add_by_last_name(current_squad, "Groß")
        add_by_last_name(current_squad, "Salah")
        add_by_last_name(current_squad, "De Bruyne")
        add_by_last_name(current_squad, "Soucek")
        add_by_last_name(current_squad, "Lomba Neto")
        add_by_last_name(current_squad, "Calvert-Lewin")
        add_by_last_name(current_squad, "Apolinário de Lira")
        add_by_last_name(current_squad, "Welbeck")
        current_squad.max_cost = money_in_bank + current_squad.total_cost

    t_0 = time.time()
    a_squad = squad(max_cost=current_squad.max_cost)
    a_squad_generator = fill_squad(a_squad, players, current_squad=current_squad, n_free_transfers=n_free_transfers)
    a_squad = next(a_squad_generator)
    print(f"Found! Startup form: {a_squad.best_starter_lineup.total_form:.2f}")
    best_squad = a_squad.copy()
    changed_squad = current_squad.copy()  # best squad given transfer costs
    current_form = current_squad.best_starter_lineup.total_form
    while True:
        try:
            b_squad = next(a_squad_generator)
            print(f"Found! Current form: {current_form:.2f}; Changed form: {changed_squad.best_starter_lineup.total_form:.2f}; Best found: {best_squad.best_starter_lineup.total_form:.2f}; Iter form: {b_squad.best_starter_lineup.total_form:.2f}")
        except StopIteration:
            break
        except SquadNotFull:
            break

        if b_squad.best_starter_lineup.total_form > best_squad.best_starter_lineup.total_form:
            best_squad = b_squad.copy()
            print(f"It was better! New startup form: {b_squad.best_starter_lineup.total_form:.2f}")

        # Adjust for cost of transfers
        b_squad_adjusted = b_squad.best_starter_lineup.total_form - max(0, b_squad.number_of_changes(current_squad) - n_free_transfers) * transfer_cost
        changed_squad_adjusted = changed_squad.best_starter_lineup.total_form - max(0, changed_squad.number_of_changes(current_squad) - n_free_transfers) * transfer_cost
        if  b_squad_adjusted > changed_squad_adjusted:
            changed_squad = b_squad.copy()
            print(f"It was better for the change! New startup form: {b_squad.best_starter_lineup.total_form:.2f}")
        elif b_squad_adjusted == changed_squad_adjusted and b_squad.total_cost < changed_squad.total_cost:
            changed_squad = b_squad.copy()
            print(f"It was as good but cheaper for the change! New startup form: {b_squad.best_starter_lineup.total_form:.2f}")
    t_1 = time.time()
    print(f"Total time: {t_1 - t_0}s")

    print(f"Best Squad: {best_squad.players}")
    print(f"Best Squad Lineup: {best_squad.best_starter_lineup.players}")

    print(f"Changed Squad:{changed_squad.players}")
    print(f"Changed Squad Lineup:{changed_squad.best_starter_lineup.players}")

    changed_squad.changes_from(current_squad)
    print(f"Captain: {changed_squad.captain}, Form: {changed_squad.captain.form}")
    pass