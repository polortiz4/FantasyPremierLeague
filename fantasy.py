import numpy as np 
import requests
import time
import types
from pathlib import Path
types.GeneratorType

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

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
            if c != 1 and c != 0:
                raise RuntimeError(f"Invalid number of the same player (should be either 0 or one, got: {c}")
            elif c == 0:
                diff += 1
        return diff

    def remove_player(self, player):
        if self.players.count(player) > 0:
            getattr(self, f"{player.position}s").remove(player)
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
            if len(self.goalkeepers) < 2:
                self.goalkeepers.append(player)
                self._players.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many goalkeepers: {len(self.goalkeepers)}")

        if player.position == "defender":
            if len(self.defenders) < 5:
                self.defenders.append(player)
                self._players.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many defenders: {len(self.defenders)}")

        if player.position == "midfielder":
            if len(self.midfielders) < 5:
                self.midfielders.append(player)
                self._players.append(player)
                return
            else:
                raise PositionFull(f"Cannot add {player}, as there are too many midfielders: {len(self.midfielders)}")

        if player.position == "striker":
            if len(self.strikers) < 3:
                self.strikers.append(player)
                self._players.append(player)
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
        return self._players

    def organized_players(self):
        self.sort_players()
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

        best_combination = None
        for i, lineup in enumerate(possible_lineups):
            gks = self.starters(self.goalkeepers, lineup[0])
            defs = self.starters(self.defenders, lineup[1])
            mids = self.starters(self.midfielders, lineup[2])
            fors = self.starters(self.strikers, lineup[3])
            # starters = [*gks, *defs, *mids, *fors]
            starting_squad = squad()
            for gk in gks:
                starting_squad.add_player(gk)
            for defender in defs:
                starting_squad.add_player(defender)
            for mid in mids:
                starting_squad.add_player(mid)
            for forward in fors:
                starting_squad.add_player(forward)

            # combinations.append((starters, self.player_list_form(starters)))
            if best_combination is None or starting_squad.total_form > best_combination.total_form:
                best_combination = starting_squad
        return best_combination

    def copy(self):
        other = squad(max_cost=self.max_cost)
        for p in self.players:
            other.add_player(p)
        return other

    def sort_players(self):
        self.goalkeepers.sort(reverse=True, key=lambda x: x.form)
        self.defenders.sort(reverse=True, key=lambda x: x.form)
        self.midfielders.sort(reverse=True, key=lambda x: x.form)
        self.strikers.sort(reverse=True, key=lambda x: x.form)

# @profile
def fill_squad(squad, available_players, cheapest_cost=None, squad_max_len=15, current_squad=None, n_free_transfers=None, transfer_cost=4, min_form=None, max_form=None, stack_i=1, changes_so_far=None):
    if cheapest_cost is None:
        cheapest_cost = min(available_players, key=lambda x: x.price).price
    if min_form is None:
        min_form = min(available_players, key=lambda x: x.form).form
    if max_form is None:
        max_form = max(available_players, key=lambda x: x.form).form
    if n_free_transfers is None:
        n_free_transfers = 15
    if current_squad is None:
        n_free_transfers = 15
    if changes_so_far is None:
        changes_so_far = squad.number_of_changes(current_squad)

    no_new_players = current_squad is not None and changes_so_far > n_free_transfers and max_form - min_form < transfer_cost

    len_players = len(squad.players)
    if len(available_players) == 0 or len_players + len(available_players) < squad_max_len:
        raise SquadNotFull(f"Not enough Players")

    for i, p in enumerate(available_players):
        if p in squad.players:
            continue
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
        if not squad.positions_full:  # else statement would be fine.. but generator is being weird here
            if len(available_players) == i+1:
                squad.remove_player(p)
                raise SquadNotFull(f"Squad not full")
            try:
                # Assumption: available_players is sorted by form
                nested_gen = fill_squad(squad, available_players[i+1:], cheapest_cost, current_squad=current_squad, n_free_transfers=n_free_transfers, min_form=min_form, max_form=available_players[i+1].form, stack_i=stack_i+1)
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
    parser.add_argument('-n', '--top-n-players', default=40, help="Number of players to search in, that is the top n players in terms of form")
    parser.add_argument('--free-transfers',  default=1, help="number of free transfers available")
    parser.add_argument('--overwrite-pulled-team', action="store_true", help="True if you want to build your current squad manually instead of pulling, team would have to be hardcoded")
    parser.add_argument('--min-player-form',  help="minimum acceptable player form")

    args = vars(parser.parse_args())

    if args['min_player_form'] is not None:
        min_acceptable_form = float(args['min_player_form'])
        top_n_players = None
        if args['verbose']:
            print(f"Choosing from players with form > {min_acceptable_form} instead of using a top_n_players")
    else:
        top_n_players = int(args['top_n_players'])
        if args['verbose']:
            print(f"Choosing from top {top_n_players} players")

    n_free_transfers = int(args['free_transfers'])
    transfer_cost = 4

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
            decrpyted_password = private_key.decrypt(encrypted_password, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)).decode("utf-8")
    else:
        decrypted_password = input("Password: ")

    payload = {
        'login': "polortiz_4@hotmail.com",
        'password': decrpyted_password,
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
    n_new_players = 0
    for p in players_json:
        pp = player_(p)
        if pp.id in [o['element'] for o in my_team_json['picks']]:
            current_squad.add_player(pp)
            players.append(pp)
        elif top_n_players is not None and n_new_players < top_n_players:
            players.append(pp)
            n_new_players += 1
        elif top_n_players is None and pp.form > min_acceptable_form:
            players.append(pp)
            n_new_players += 1

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
        current_squad.sort_players()
        current_squad.max_cost = money_in_bank + current_squad.total_cost

    t_0 = time.time()

    changed_squad = current_squad.copy()  # best squad given transfer costs
    current_form = current_squad.best_starter_lineup.total_form

    a_squad = squad(max_cost=current_squad.max_cost)
    a_squad_generator = fill_squad(a_squad, players, current_squad=current_squad, n_free_transfers=n_free_transfers, max_form=players[0].form, min_form=players[-1].form)

    n_squads = 1
    erase = '\x1b[1A\x1b[2K'
    if not args['verbose']:
        print('')  # so the erase later doesn't erase the command
    while True:
        try:
            b_squad = next(a_squad_generator)
            if args['verbose']:
                print(f"Found! Current form: {current_form:.2f}; Changed form: {changed_squad.best_starter_lineup.total_form:.2f}; Iter form: {b_squad.best_starter_lineup.total_form:.2f}\n")
            else:
                print(f'{erase}Valid squads found: {n_squads}, Progress: ', end='')
                for i, player in enumerate(b_squad.players):
                    print(f"{players[i:].index(player)}/{len(players[i:])}, ", end='')
                print('')
                n_squads += 1
        except StopIteration:
            break
        except SquadNotFull:
            break

        # Adjust for cost of transfers
        b_squad_adjusted = b_squad.best_starter_lineup.total_form - max(0, b_squad.number_of_changes(current_squad) - n_free_transfers) * transfer_cost
        changed_squad_adjusted = changed_squad.best_starter_lineup.total_form - max(0, changed_squad.number_of_changes(current_squad) - n_free_transfers) * transfer_cost
        if  b_squad_adjusted > changed_squad_adjusted:
            changed_squad = b_squad.copy()
            print(f"Found a squad that was better for the change! New startup form: {b_squad.best_starter_lineup.total_form:.2f}\n")
        elif b_squad_adjusted == changed_squad_adjusted and b_squad.total_cost < changed_squad.total_cost:
            changed_squad = b_squad.copy()
            print(f"Found a squad was as good but cheaper for the change! New startup form: {b_squad.best_starter_lineup.total_form:.2f}\n")
    t_1 = time.time()
    print(f"Total time: {t_1 - t_0:.2f}s = {(t_1 - t_0) // 60:.0f}:{t_1 - t_0 - 60 * ((t_1 - t_0) // 60):.0f}")

    print(f"\nChanged Squad:")
    for player in changed_squad.players:
        print(f"{player}")
    print(f"\nChanged Squad Lineup:")
    for player in changed_squad.best_starter_lineup.players:
        print(f"{player}")
    print(f"\nCaptain: {changed_squad.captain}, Form: {changed_squad.captain.form}")

    print("\nChanges needed for Changed Squad:\n")
    changed_squad.changes_from(current_squad)
    pass
