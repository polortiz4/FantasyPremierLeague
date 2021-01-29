import requests
import time
import types
from pathlib import Path
types.GeneratorType

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

from keyPoller import KeyPoller as kp

# This is my encrypted password for the EPL fantasy
encrypted_password = b"\xad\xdb8\xab\xa7\xaeA\r\xf2C\xc1\xb3u\xba?\xa0<\xce\xba\xd0\n6.\x0f\xf1\x08\x04\xd1\x8d\xc1W\xa9\xd2\xd5\xc2\x03\x19\xd5\x96\xa3\tI\xac*\xf7{\xf0\xa1\xb4N9\xa2y^\xe2\x8dr\xdfYEg\xa1\xe0?\x1d\xd8\xc3\x19\xcc\x069\x08=\xe7\xd5\x1d\xefT\xff\xf6L\x81s\xbd\x08s\x86uVK\x1d\xf7\xfc=g\xce#\x85\x1b\xa2\x8bJ\x8f\xea6q3\xee\x93\x8e1\xa1a\x12\xb8q\x8b^\xa0\xed\xa9R\xe2\xffo\xb9r\x14\x18\xab\xf1<h\x1a\xc0}\x9a\x89\xd8V\xadT\x1b\xa4\xfdj\x89\xe3U<2\x8a\x94\xbf\xd8\xbeE\xef\xf2Y\x870 \x17\x16\xc7\xe1\xf8\xd13\x9ab\x1eOz\t\xd9\xc8+J\xb6\xf3\x97Q\x96<\x94\x98E\xeb\xf9\xe3\x83\x0b4\xac\xdf\xb4\x8c8\xdb9\xd1\xa3[}\xe7$\x10\\\x02Xrw\xf9\x88\x82\x9e\xde\xbcF\x9d#n\xc0D\xf2\x90\xb6\x86\x0b\x98\xd9\xbeT{{\x92:aK\xeb\x9c\xd3\x03\xbf\x976G\xe9\xe1\xf4\x7f',1"

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

    return player(name=p_info['second_name'], form=float(p_info['form']), price=float(p_info['now_cost'])/10, position=position, team=p_info['team'], id=p_info['id'], health=p_info['chance_of_playing_next_round']/100)

def add_by_last_name(squad, last_name):
    for p in players:
        if p.name == last_name:
            squad.add_player(p)
            return
    raise RuntimeError(f"Couldn't find player: {last_name}")


class player():
    def __init__(self, name, form, price, position, team, id, health):
        super().__init__()
        self._form = form
        self._health = health
        self.price = price
        self.name = name
        self.position = position
        self.team = team
        self.id = id

        self.metric = self.form * self.health  ## If this line is changed, make sure to change the line where players_json is sorted as well

    def __repr__(self):
        return f"({self.name}, {float(self.form):.2f}, {float(self.price):.2f}, {self.position}, {self.team}, {self.id}, {self.health})"

    def __str__(self):
        return f"({self.name}, form: {float(self.form):.2f}, price: {float(self.price):.2f}, position: {self.position}, team: {self.team}, id: {self.id}, health: {self.health})"

    def __eq__(self, other):
        return self.id == other.id

    @property
    def form(self):
        return self._form
    
    @form.setter
    def form(self, new_form):
        self._form = new_form
        self.metric = self._form * self.health

    @property
    def health(self):
        return self._health
    
    @health.setter
    def health(self, new_health):
        self._health = new_health
        self.metric = self._form * self._health 


class squad():
    def __init__(self, max_cost=100):
        self.max_cost = max_cost
        self._goalkeepers = []
        self._defenders = []
        self._midfielders = []
        self._strikers = []
        self._players = []

    def changes_from(self, other):
        unique_from_self = squad()
        unique_from_other = squad()
        for my_player, other_player in zip(self.players, other.players):
            if my_player not in other.players:
                unique_from_self.add_player(my_player)
            if other_player not in self.players:
                unique_from_other.add_player(other_player)
        for mine, other in zip(unique_from_self.organized_players(), unique_from_other.organized_players()):
            assert(mine.position == other.position)
            print(f"Out: {other} <-----------> In: {mine}")

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
            assert(c == 1 or c == 0)
            if c == 0:
                diff += 1
        return diff

    def remove_player(self, player):
        if self.players.count(player) > 0:
            getattr(self, f"_{player.position}s").remove(player)
            self._players.remove(player)

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
            if len(self._goalkeepers) < 2:
                self._goalkeepers.append(player)
                self._players.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many goalkeepers: {len(self._goalkeepers)}")

        if player.position == "defender":
            if len(self._defenders) < 5:
                self._defenders.append(player)
                self._players.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many defenders: {len(self._defenders)}")

        if player.position == "midfielder":
            if len(self._midfielders) < 5:
                self._midfielders.append(player)
                self._players.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many midfielders: {len(self._midfielders)}")

        if player.position == "striker":
            if len(self._strikers) < 3:
                self._strikers.append(player)
                self._players.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many strikers: {len(self._strikers)}")

    def validate_cost(self):
        if self.total_cost > self.max_cost:
            raise TooExpensiveError(f"Total Cost: {self.total_cost} > max_cost: {self.max_cost}")
    
    @property
    def positions_full(self):
        return len(self._goalkeepers) == 2 and len(self._defenders) == 5 and len(self._midfielders) == 5 and len(self._strikers) == 3

    def starters(self, player_list, n_starters):
        player_list.sort(reverse=True, key=lambda x: x.metric)
        return player_list[:n_starters]

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"Squad with Metric: {self.total_metric:.2f}, cost: {self.total_metric:.2f}"

    @property
    def starting_goalkeeper(self):
        return self.starters(self._goalkeepers, 1)

    @property
    def players(self):
        return self._players

    def organized_players(self):
        self.sort_players()
        return [*self._goalkeepers, *self._defenders, *self._midfielders, *self._strikers]


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
    def total_metric(self, double_captain=True):
        metric = 0
        for player in self.players:
            metric += player.metric
            if double_captain and player == self.captain:
                metric += player.metric
        return metric

    def player_list_metric(self, player_list):
        metric = 0
        for player in player_list:
            metric += player.metric
        return metric

    @property
    def bench(self):
        bench = squad()
        starters = self.best_starter_lineup
        for p in self.players:
            if p not in starters.players:
                bench.add_player(p)
        return bench

    @property
    def best_starter_lineup(self):
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

        best_combination = None
        best_metric = None
        for lineup in possible_lineups:
            gks = self.starters(self._goalkeepers, lineup[0])
            defs = self.starters(self._defenders, lineup[1])
            mids = self.starters(self._midfielders, lineup[2])
            fors = self.starters(self._strikers, lineup[3])

            starting_squad = squad()
            for gk in gks:
                starting_squad.add_player(gk)
            for defender in defs:
                starting_squad.add_player(defender)
            for mid in mids:
                starting_squad.add_player(mid)
            for forward in fors:
                starting_squad.add_player(forward)

            if best_combination is None or starting_squad.total_metric > best_metric:
                best_combination = starting_squad
                best_metric = best_combination.total_metric
        return best_combination

    def copy(self):
        other = squad(max_cost=self.max_cost)
        for p in self.players:
            other.add_player(p)
        return other

    def sort_players(self):
        self._goalkeepers.sort(reverse=True, key=lambda x: x.metric)
        self._defenders.sort(reverse=True, key=lambda x: x.metric)
        self._midfielders.sort(reverse=True, key=lambda x: x.metric)
        self._strikers.sort(reverse=True, key=lambda x: x.metric)
        self._players.sort(reverse=True, key=lambda x: x.metric)

# @profile
def fill_squad(squad, available_players, cheapest_cost=None, squad_max_len=15, current_squad=None, n_free_transfers=None, transfer_cost=4, min_metric=None, max_metric=None, stack_i=1, changes_so_far=None):
    if cheapest_cost is None:
        cheapest_cost = min(available_players, key=lambda x: x.price).price
    if min_metric is None:
        min_metric = min(available_players, key=lambda x: x.metric).metric
    if max_metric is None:
        max_metric = max(available_players, key=lambda x: x.metric).metric
    if n_free_transfers is None:
        n_free_transfers = squad_max_len
    if current_squad is None:
        n_free_transfers = squad_max_len
    if changes_so_far is None:
        changes_so_far = squad.number_of_changes(current_squad)

    no_new_players = current_squad is not None and changes_so_far > n_free_transfers and max_metric - min_metric < transfer_cost
    no_new_players = False

    len_players = len(squad.players)
    if len(available_players) == 0 or len_players + len(available_players) < squad_max_len:
        raise SquadNotFull(f"Not enough Players")

    for i, p in enumerate(available_players):
        assert(p not in squad.players)
        if len_players < squad_max_len - 1 and (squad.max_cost - (squad.total_cost + p.price)) / (squad_max_len - 1 - len_players) <= cheapest_cost:
            continue
        if squad.total_cost + p.price > squad.max_cost:
            continue
        if no_new_players and p not in current_squad.players:
            continue

        try:
            squad.add_player(p)
        except PositionFull:
            continue 
        except TeamSpotsFull:
            continue

        if squad.positions_full:
            yield squad
        elif len(available_players) != i+1:
            # Assumption: available_players is sorted by metric
            nested_gen = fill_squad(squad, available_players[i+1:], cheapest_cost, transfer_cost=transfer_cost, current_squad=current_squad, n_free_transfers=n_free_transfers, min_metric=min_metric, max_metric=available_players[i+1].metric, stack_i=stack_i+1)
            try:
                yield from nested_gen
            except SquadNotFull:
                pass
        squad.remove_player(p)

    raise SquadNotFull(f"Squad not full")
    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--gameweek', help='last week\'s gameweek number')
    parser.add_argument('-p', '--password', action="store_true", help="True if fantasy password is to be provided manually, false if it's to be decoded from hardcoded encrypted password")
    parser.add_argument('-u', '--user-id', default=3521386, help="user-id from fantasy server to evaluate")
    parser.add_argument('-v', '--verbose', action="store_true", help="Print output for every possible squad")
    parser.add_argument('-n', '--top-n-players', default=20, help="Number of players to search in, that is the top n players in terms of metric")
    parser.add_argument('--free-transfers',  default=1, help="number of free transfers available")
    parser.add_argument('--overwrite-pulled-team', action="store_true", help="True if you want to build your current squad manually instead of pulling, team would have to be hardcoded")
    parser.add_argument('--min-player-metric', help="minimum acceptable player metric")
    parser.add_argument('--transfer-cost', default=4, help="cost per transfer")
    parser.add_argument('--bench-point-value', default=5, help="cost of a bench point")

    args = vars(parser.parse_args())

    if args['min_player_metric'] is not None:
        min_acceptable_metric = float(args['min_player_metric'])
        top_n_players = None
        if args['verbose']:
            print(f"Choosing from players with metric > {min_acceptable_metric} instead of using a top_n_players")
    else:
        top_n_players = int(args['top_n_players'])
        if args['verbose']:
            print(f"Choosing from top {top_n_players} players")

    n_free_transfers = int(args['free_transfers'])
    transfer_cost = float(args['transfer_cost'])

    if args['gameweek'] is None:
        current_gameweek = input("What was the last gameweek? ")
    else:
        current_gameweek = args['gameweek']
    user_id = args['user_id']

    player_info_url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    my_team_url = f'https://fantasy.premierleague.com/api/entry/{user_id}/event/{current_gameweek}/picks/'
    login_url = "https://users.premierleague.com/accounts/login/"

    if not args['password']:
        with open(Path.home().joinpath(".ssh/id_rsa_nopassword"), "rb") as key_file:
            private_key = serialization.load_ssh_private_key(key_file.read(), password=None)
            decrypted_password = private_key.decrypt(encrypted_password, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)).decode("utf-8")
    else:
        decrypted_password = input("Password: ")

    payload = {
        'login': "polortiz_4@hotmail.com",
        'password': decrypted_password,
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
    for p in players_json:
        if p['chance_of_playing_next_round'] is None:
            p['chance_of_playing_next_round'] = 100
    players_json.sort(reverse=True, key=lambda x: float(x['form']) * float(x['chance_of_playing_next_round']) / 100)  # if this line is changed, make sure to change the line in the players constructor as well

    players = []
    current_squad = squad(max_cost=1000)
    n_new_players = 0
    for p in players_json:
        pp = player_(p)
        if pp.id in [o['element'] for o in my_team_json['picks']]:
            current_squad.add_player(pp)
            players.append(pp)
        elif top_n_players is not None and n_new_players < top_n_players:
            players.append(pp)
            n_new_players += 1
        elif top_n_players is None and pp.form > min_acceptable_metric:
            players.append(pp)
            n_new_players += 1

    current_squad.max_cost = my_team_json['entry_history']['bank']/10 + current_squad.total_cost

    if args['overwrite_pulled_team']:
        money_in_bank = 11.3
        current_squad = squad(max_cost=1000)
        add_by_last_name(current_squad, "Leno")
        add_by_last_name(current_squad, "Meslier")
        add_by_last_name(current_squad, "Cancelo")
        add_by_last_name(current_squad, "Cresswell")
        add_by_last_name(current_squad, "Stones")
        add_by_last_name(current_squad, "Targett")
        add_by_last_name(current_squad, "Dunk")
        add_by_last_name(current_squad, "Saka")
        add_by_last_name(current_squad, "Tielemans")
        add_by_last_name(current_squad, "Soucek")
        add_by_last_name(current_squad, "Maddison")
        add_by_last_name(current_squad, "Gündogan")
        add_by_last_name(current_squad, "Lacazette")
        add_by_last_name(current_squad, "Antonio")
        add_by_last_name(current_squad, "Maupay")
        current_squad.sort_players()
        current_squad.max_cost = money_in_bank + current_squad.total_cost

    t_0 = time.time()

    changed_squad = current_squad.copy()  # best squad given transfer costs
    current_metric = current_squad.best_starter_lineup.total_metric

    a_squad = squad(max_cost=current_squad.max_cost)
    a_squad_generator = fill_squad(a_squad, players, transfer_cost=transfer_cost, current_squad=current_squad, n_free_transfers=n_free_transfers, max_metric=players[0].metric, min_metric=players[-1].metric)

    n_squads = 1
    erase = '\x1b[1A\x1b[2K'
    if not args['verbose']:
        print('')  # so the erase later doesn't erase the command

    def print_changed_squad():
        print(f"\nChanged Squad Lineup:")
        for player in changed_squad.best_starter_lineup.players:
            print(f"{player}")
        print(f"\nChanged Squad Bench:")
        for player in changed_squad.bench.players:
            print(f"{player}")
        print(f"\nCaptain: {changed_squad.captain}, metric: {changed_squad.captain.metric}")
        print("\nChanges needed for Changed Squad:\n")
        changed_squad.changes_from(current_squad)
        print("\n")

    with kp() as KP:
        top_changed_bench_metric = 0
        while True:
            try:
                b_squad = next(a_squad_generator)
                if args['verbose']:
                    print(f"Found! Current metric: {current_metric:.2f}; Changed metric: {changed_squad.best_starter_lineup.total_metric:.2f}; Iter metric: {b_squad.best_starter_lineup.total_metric:.2f}\n")
                else:
                    print(f'{erase}Valid squads found: {n_squads}, Progress: ', end='')
                    for i, player in enumerate(b_squad.players):
                        print(f"{players[i:].index(player)}/{len(players[i:])}, ", end='')
                    print('')
                    n_squads += 1
                if n_squads % 100 == 0:
                    key = KP.poll()
                    if key == "p":
                        print_changed_squad()
            except StopIteration:
                break
            except SquadNotFull:
                break

            # Adjust for cost of transfers
            b_squad_adjusted = b_squad.best_starter_lineup.total_metric - max(0, b_squad.number_of_changes(current_squad) - n_free_transfers) * transfer_cost
            changed_squad_adjusted = changed_squad.best_starter_lineup.total_metric - max(0, changed_squad.number_of_changes(current_squad) - n_free_transfers) * transfer_cost
            if  b_squad_adjusted > changed_squad_adjusted:
                changed_squad = b_squad.copy()
                print(f"Found a squad that was better for the change! New startup metric: {b_squad.best_starter_lineup.total_metric:.2f}\n")
            elif b_squad_adjusted == changed_squad_adjusted:
                bench_points_required_for_change = (b_squad.total_cost - changed_squad.total_cost) * float(args['bench_point_value'])  # If positive, I prefer changed_squad unless it has a nice bench

                if b_squad.bench.total_metric - changed_squad.bench.total_metric > bench_points_required_for_change:
                    changed_squad = b_squad.copy()
                    print(f"Found a squad was as good but with better value/bench! New startup metric: {b_squad.best_starter_lineup.total_metric:.2f}\n")                    

        t_1 = time.time()
        print(f"Total time: {t_1 - t_0:.2f}s = {(t_1 - t_0) // 60:.0f}:{t_1 - t_0 - 60 * ((t_1 - t_0) // 60):.0f}")

        print_changed_squad()
        pass
