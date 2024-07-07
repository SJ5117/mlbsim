import random
import pandas as pd
import sys
from pybaseball import playerid_lookup, batting_stats, pitching_stats

# Cache dictionaries
batter_stats_cache = {}
pitcher_stats_cache = {}

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
    away_pitcher = None
    home_pitcher = None
    lineup_start = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        if line == "@":
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
            continue

        if "Lineup" in line:
            lineup_start = True
            continue

        if lineup_start:
            if len(current_game['away_lineup']) < 9:
                current_game['away_lineup'].append(extract_name(line))
            else:
                current_game['home_lineup'].append(extract_name(line))

        if line in ["RHP", "LHP"]:
            pitcher_name = extract_name(lines[i - 1].strip())
            if not current_game['away_pitcher']:
                current_game['away_pitcher'] = pitcher_name
            else:
                current_game['home_pitcher'] = pitcher_name

        if line == "" and current_game:
            games.append(current_game)
            current_game = None
            lineup_start = False

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

def calculate_probabilities(batter_stats, pitcher_stats):
    if batter_stats is not None and not batter_stats.empty:
        avg = batter_stats['AVG'].mean()
        obp = batter_stats['OBP'].mean()
        slg = batter_stats['SLG'].mean()
        single_rate = batter_stats['1B'].sum() / batter_stats['AB'].sum()
        double_rate = batter_stats['2B'].sum() / batter_stats['AB'].sum()
        triple_rate = batter_stats['3B'].sum() / batter_stats['AB'].sum()
        hr_rate = batter_stats['HR'].sum() / batter_stats['AB'].sum()
    else:
        avg = 0.250
        obp = 0.320
        slg = 0.400
        single_rate = avg * 0.6
        double_rate = avg * 0.2
        triple_rate = avg * 0.05
        hr_rate = avg * 0.15

    if pitcher_stats is not None and not pitcher_stats.empty:
        k_rate = pitcher_stats['K%'].mean()
        bb_rate = pitcher_stats['BB%'].mean()
        hr_rate_pitcher = pitcher_stats['HR/9'].mean() / 9
    else:
        k_rate = 0.20
        bb_rate = 0.08
        hr_rate_pitcher = 0.03

    return {
        'strikeout': k_rate,
        'walk': bb_rate,
        'single': single_rate,
        'double': double_rate,
        'triple': triple_rate,
        'home_run': hr_rate,
        'out': 1 - (k_rate + bb_rate + single_rate + double_rate + triple_rate + hr_rate)
    }

def simulate_at_bat(batter_stats, pitcher_stats):
    probabilities = calculate_probabilities(batter_stats, pitcher_stats)
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

def simulate_game(home_lineup, away_lineup, pitcher_stats_home, pitcher_stats_away):
    innings = 9
    home_score = 0
    away_score = 0
    lineup_home = home_lineup[:]
    lineup_away = away_lineup[:]

    for inning in range(1, innings + 1):
        for team in ['away', 'home']:
            lineup = lineup_away if team == 'away' else lineup_home
            pitcher_stats = pitcher_stats_home if team == 'away' else pitcher_stats_away
            outs = 0
            bases = [False, False, False]  # Empty bases

            while outs < 3:
                player = lineup[0]
                batter_stats = batter_stats_cache.get(player, None)
                outcome = simulate_at_bat(batter_stats, pitcher_stats)

                if outcome == 'strikeout' or outcome == 'out':
                    outs += 1
                elif outcome == 'walk':
                    if bases[0]:
                        if bases[1]:
                            if bases[2]:
                                bases, increment = advance_runners(bases, 'single')
                                home_score += increment
                            else:
                                bases[2] = True
                        else:
                            bases[1] = True
                    else:
                        bases[0] = True
                else:
                    bases, increment = advance_runners(bases, outcome)
                    if team == 'away':
                        away_score += increment
                    else:
                        home_score += increment

                lineup.append(lineup.pop(0))  # Rotate lineup

    while home_score == away_score:
        for team in ['away', 'home']:
            lineup = lineup_away if team == 'away' else lineup_home
            pitcher_stats = pitcher_stats_home if team == 'away' else pitcher_stats_away
            outs = 0
            bases = [False, False, False]  # Empty bases

            while outs < 3:
                player = lineup[0]
                batter_stats = batter_stats_cache.get(player, None)
                outcome = simulate_at_bat(batter_stats, pitcher_stats)

                if outcome == 'strikeout' or outcome == 'out':
                    outs += 1
                elif outcome == 'walk':
                    if bases[0]:
                        if bases[1]:
                            if bases[2]:
                                bases, increment = advance_runners(bases, 'single')
                                home_score += increment
                            else:
                                bases[2] = True
                        else:
                            bases[1] = True
                    else:
                        bases[0] = True
                else:
                    bases, increment = advance_runners(bases, outcome)
                    if team == 'away':
                        away_score += increment
                    else:
                        home_score += increment

                lineup.append(lineup.pop(0))  # Rotate lineup

    return home_score, away_score

def run_simulations(games, num_simulations=1000, run_threshold=10.5):
    results = []
    fetch_all_player_stats(games)
    over_threshold_count = 0

    for game in games:
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

            print(f"\rRunning sim: {sim}/{num_simulations}", end='')

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

if __name__ == "__main__":
    main()
