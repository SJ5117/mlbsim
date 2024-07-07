import pandas as pd
from pybaseball import batting_stats

# Set pandas options to display all columns
pd.set_option('display.max_columns', None)

# Fetching batting stats for the specified player
res = batting_stats(start_season=2024, end_season=2024, split_seasons=True, players="10155", qual=0)

# Print the DataFrame
print(res)
