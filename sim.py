import random
import pandas as pd
import sys
from pybaseball import playerid_lookup, batting_stats, pitching_stats

# Cache dictionaries
batter_stats_cache = {}
pitcher_stats_cache = {}

# Average relief pitcher stats
average_reliever_stats = {
    'K%': 0.24,
    'BB%': 0.09,
    'HR/9': 0.012,
    'out_rate': 1 - (0.24 + 0.09 + 0.012)
}

# Mapping of team names to their abbreviations
team_abbreviations = {
    'D-backs': 'ARI',
    'Braves': 'ATL',
    'Orioles': 'BAL',
    'Red Sox': 'BOS',
    'White Sox': 'CWS',
    'Cubs': 'CHC',
    'Reds': 'CIN',
    'Guardians': 'CLE',
    'Rockies': 'COL',
    'Tigers': 'DET',
    'Astros': 'HOU',
    'Royals': 'KC',
    'Angels': 'LAA',
    'Dodgers': 'LAD',
    'Marlins': 'MIA',
    'Brewers': 'MIL',
    'Twins': 'MIN',
    'Yankees': 'NYY',
    'Mets': 'NYM',
    'Athletics': 'OAK',
    'Phillies': 'PHI',
    'Pirates': 'PIT',
    'Padres': 'SD',
    'Giants': 'SF',
    'Mariners': 'SEA',
    'Cardinals': 'STL',
    'Rays': 'TB',
    'Rangers': 'TEX',
    'Blue Jays': 'TOR',
    'Nationals': 'WSH',
}

def extract_name(line):
    return ' '.join(line.split()[:2])

def parse_lineups(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    games = []
    current_game = None
    away_team = None
    home_team = None
    lineup_start = False
    pitcher_lines = 0

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        if "@" in line:
            if current_game:
                games.append(current_game)
            away_team = lines[i - 1].strip()
            home_team = lines[i + 1].strip()

            if away_team not in team_abbreviations or home_team not in team_abbreviations:
                print(f"Error: Team name not found in abbreviations: {away_team} @ {home_team}")
                continue

            current_game = {
                'home_team': team_abbreviations[home_team],
                'away_team': team_abbreviations[away_team],
                'home_pitcher': None,
                'away_pitcher': None,
                'home_lineup': [],
                'away_lineup': []
            }
            pitcher_lines = 0
            lineup_start = False
            continue

        if "Lineup" in line:
            lineup_start = True
            continue

        if lineup_start:
            if len(current_game['away_lineup']) < 9:
                current_game['away_lineup'].append(extract_name(line))
            elif len(current_game['home_lineup']) < 9:
                current_game['home_lineup'].append(extract_name(line))

        if line in ["RHP", "LHP"]:
            pitcher_name = extract_name(lines[i - 1].strip())
            if pitcher_lines == 0:
                current_game['away_pitcher'] = pitcher_name
                pitcher_lines += 1
            else:
                current_game['home_pitcher'] = pitcher_name
                pitcher_lines += 1

    if current_game:
        games.append(current_game)

    return games

def get_player_stats(player_name, stats):
    player_id = playerid_lookup(last=player_name.split()[-1], first=player_name.split()[0])
    if not player_id.empty:
        player_id = player_id.iloc[0]['key_fangraphs']
        player_stats = stats[stats['IDfg'] == player_id]
        if not player_stats.empty:
            return player_stats
    return None

def fetch_all_player_stats(games):
    season = 2024
    all_batter_stats = batting_stats(season, qual=0)
    all_pitcher_stats = pitching_stats(season, qual=0)

    for game in games:
        for player in game['home_lineup'] + game['away_lineup']:
            if player not in batter_stats_cache:
                batter_stats_cache[player] = get_player_stats(player, all_batter_stats)
        for pitcher in [game['home_pitcher'], game['away_pitcher']]:
            if pitcher not in pitcher_stats_cache:
                pitcher_stats_cache[pitcher] = get_player_stats(pitcher, all_pitcher_stats)

def calculate_batting_probabilities(batter_stats):
    if batter_stats is not None and not batter_stats.empty:
        woba = batter_stats['wOBA'].mean()
        iso = batter_stats['ISO'].mean()
        babip = batter_stats['BABIP'].mean()
        bb_rate = batter_stats['BB%'].mean() / 100
        k_rate = batter_stats['K%'].mean() / 100
        single_rate = (batter_stats['1B'].sum() / batter_stats['AB'].sum()) if '1B' in batter_stats.columns else (woba - iso) * babip
        double_rate = (batter_stats['2B'].sum() / batter_stats['AB'].sum()) if '2B' in batter_stats.columns else iso * 0.2
        triple_rate = (batter_stats['3B'].sum() / batter_stats['AB'].sum()) if '3B' in batter_stats.columns else iso * 0.05
        hr_rate = (batter_stats['HR'].sum() / batter_stats['AB'].sum()) if 'HR' in batter_stats.columns else iso * 0.15
    else:
        # Use league average values if no data
        single_rate = 0.15
        double_rate = 0.05
        triple_rate = 0.01
        hr_rate = 0.03
        bb_rate = 0.08
        k_rate = 0.20

    return {
        'strikeout': k_rate,
        'walk': bb_rate,
        'single': single_rate,
        'double': double_rate,
        'triple': triple_rate,
        'home_run': hr_rate,
        'out': 1 - (k_rate + bb_rate + single_rate + double_rate + triple_rate + hr_rate)
    }

def simulate_at_bat(probabilities):
    result = random.random()
    cumulative_probability = 0
    for outcome, probability in probabilities.items():
        cumulative_probability += probability
        if result < cumulative_probability:
            return outcome
    return 'out'

def advance_runners(bases, hit_type):
    score_increment = 0
    if hit_type == 'single':
        if bases[2]:
            score_increment += 1
        if bases[1]:
            bases[2] = bases[1]
        if bases[0]:
            bases[1] = bases[0]
        bases[0] = True
    elif hit_type == 'double':
        if bases[2]:
            score_increment += 1
        if bases[1]:
            score_increment += 1
        if bases[0]:
            bases[2] = True
        bases[1] = True
        bases[0] = False
    elif hit_type == 'triple':
        score_increment += sum(bases)
        bases = [False, False, True]
    elif hit_type == 'home_run':
        score_increment += sum(bases) + 1
        bases = [False, False, False]
    return bases, score_increment

def make_pitching_substitution(inning, runs_allowed, current_score_diff):
    # Define thresholds
    max_innings = 6
    max_runs_allowed = 4
    close_game_diff = 2
    blowout_diff = 5
    
    # Check if the pitcher has exceeded the maximum innings or runs allowed
    if inning >= max_innings or runs_allowed >= max_runs_allowed:
        return True
    
    # Check if the game is close or a blowout
    if abs(current_score_diff) <= close_game_diff:
        return False  # Use the best reliever available
    elif abs(current_score_diff) >= blowout_diff:
        return True  # Use a less effective reliever

    # Otherwise, do not make a substitution
    return False

def simulate_game(home_lineup, away_lineup, starter_stats_home, starter_stats_away):
    innings = 9
    home_score = 0
    away_score = 0
    home_pitcher = starter_stats_home
    away_pitcher = starter_stats_away
    home_pitcher_runs = 0
    away_pitcher_runs = 0

    for inning in range(1, innings + 1):
        for team in ['home', 'away']:
            if team == 'home':
                lineup = home_lineup
                pitcher_stats = home_pitcher
                runs_allowed = home_pitcher_runs
                current_score_diff = home_score - away_score
                if make_pitching_substitution(inning, runs_allowed, current_score_diff):
                    pitcher_stats = average_reliever_stats
                home_pitcher_runs = runs_allowed
            else:
                lineup = away_lineup
                pitcher_stats = away_pitcher
                runs_allowed = away_pitcher_runs
                current_score_diff = away_score - home_score

                if make_pitching_substitution(inning, runs_allowed, current_score_diff):
                    pitcher_stats = average_reliever_stats
                away_pitcher_runs = runs_allowed

            outs = 0
            bases = [False, False, False]

            while outs < 3:
                player = lineup[0]
                batter_stats = batter_stats_cache.get(player, None)
                probabilities = calculate_batting_probabilities(batter_stats)
                outcome = simulate_at_bat(probabilities)

                if outcome == 'strikeout' or outcome == 'out':
                    outs += 1
                elif outcome == 'walk':
                    if bases[0]:
                        if bases[1]:
                            if bases[2]:
                                bases, increment = advance_runners(bases, 'single')
                                if team == 'home':
                                    home_score += increment
                                else:
                                    away_score += increment
                            else:
                                bases[2] = True
                        else:
                            bases[1] = True
                    else:
                        bases[0] = True
                else:
                    bases, increment = advance_runners(bases, outcome)
                    if team == 'home':
                        home_score += increment
                    else:
                        away_score += increment

                lineup.append(lineup.pop(0))

    while home_score == away_score:
        for team in ['home', 'away']:
            if team == 'home':
                lineup = home_lineup
                pitcher_stats = average_reliever_stats
            else:
                lineup = away_lineup
                pitcher_stats = average_reliever_stats

            outs = 0
            bases = [False, False, False]

            while outs < 3:
                player = lineup[0]
                batter_stats = batter_stats_cache.get(player, None)
                probabilities = calculate_batting_probabilities(batter_stats)
                outcome = simulate_at_bat(probabilities)

                if outcome == 'strikeout' or outcome == 'out':
                    outs += 1
                elif outcome == 'walk':
                    if bases[0]:
                        if bases[1]:
                            if bases[2]:
                                bases, increment = advance_runners(bases, 'single')
                                if team == 'home':
                                    home_score += increment
                                else:
                                    away_score += increment
                            else:
                                bases[2] = True
                        else:
                            bases[1] = True
                    else:
                        bases[0] = True
                else:
                    bases, increment = advance_runners(bases, outcome)
                    if team == 'home':
                        home_score += increment
                    else:
                        away_score += increment

                lineup.append(lineup.pop(0))

    return home_score, away_score

def run_simulations(games, num_simulations=1000, run_threshold=10.5):
    results = []
    fetch_all_player_stats(games)
    for game in games:
        over_threshold_count = 0
        home_lineup = game['home_lineup']
        away_lineup = game['away_lineup']
        pitcher_stats_home = pitcher_stats_cache.get(game['home_pitcher'], None)
        pitcher_stats_away = pitcher_stats_cache.get(game['away_pitcher'], None)

        print(f"Starting Simulations for {game['away_team']} @ {game['home_team']}")
        home_wins = 0
        away_wins = 0

        for sim in range(1, num_simulations + 1):
            home_score, away_score = simulate_game(home_lineup, away_lineup, pitcher_stats_home, pitcher_stats_away)
            if home_score > away_score:
                home_wins += 1
            else:
                away_wins += 1

            if home_score + away_score > run_threshold:
                over_threshold_count += 1

            #print(f"\rRunning sim: {sim}/{num_simulations}", end='')

        over_threshold_percentage = (over_threshold_count / num_simulations) * 100

        results.append({
            'home_team': game['home_team'],
            'away_team': game['away_team'],
            'home_wins': home_wins,
            'away_wins': away_wins,
            'home_win_percentage': home_wins / num_simulations,
            'away_win_percentage': away_wins / num_simulations,
            'over_threshold_percentage': over_threshold_percentage
        })
        print()

        conres = f"{game['home_team']} {game['away_team']} {home_wins} {away_wins} {home_wins / num_simulations} {away_wins / num_simulations} {over_threshold_percentage}"
        print(conres)

    return pd.DataFrame(results)

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 sim.py <num_simulations> <run_threshold>")
        return

    num_simulations = int(sys.argv[1])
    run_threshold = float(sys.argv[2])

    file_path = 'lineups.txt'  # Path to the input file containing the lineups
    games = parse_lineups(file_path)

    results = run_simulations(games, num_simulations, run_threshold)
    
    print("Results DataFrame:")
    print(results)
'''
    for game in games:
        print(f"Data found for players in {game['away_team']} @ {game['home_team']}:")
        for player in game['home_lineup'] + game['away_lineup']:
            player_data = batter_stats_cache.get(player, None)
            print(f"{player}: {'Yes' if player_data is not None and not player_data.empty else 'No'}")
        pitcher_data_home = pitcher_stats_cache.get(game['home_pitcher'], None)
        pitcher_data_away = pitcher_stats_cache.get(game['away_pitcher'], None)
        print(f"{game['home_pitcher']}: {'Yes' if pitcher_data_home is not None and not pitcher_data_home.empty else 'No'}")
        print(f"{game['away_pitcher']}: {'Yes' if pitcher_data_away is not None and not pitcher_data_away.empty else 'No'}")
'''
if __name__ == "__main__":
    main()
