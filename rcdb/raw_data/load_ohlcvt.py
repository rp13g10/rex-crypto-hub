import pandas as pd
import re
import sqlalchemy as sql
from glob import glob

# Get a list of data files
all_files = glob('Kraken_OHLCVT/*.csv')

# Get a set of all currency pairs
all_pairs = set(re.search(r'(\w+)_\d+\.csv', x).group(1) for x in all_files)

# Generate sqlalchemy engine for target database
rcdb = sql.create_engine('postgresql+psycopg2://rcdb_super:postgres@localhost:5432/rcdb')

# Load one currency pair at a time to limit memory usage
for inx, pair in enumerate(all_pairs):

    # Work out which currencies are being dealt with
    cur_from = pair[:-3]
    cur_to = pair[-3:]

    # Get a list of all files for the current pair
    pair_files = filter(
        lambda x: pair in x,
        all_files
    )

    # Load them all into memory
    file_headers = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'trades']
    pair_dfs = {}
    for pair_file in pair_files:
        file_resolution = re.search(
            r'(\d+)\.csv', pair_file).group(1)
        file_resolution = int(file_resolution)

        pair_df = pd.read_csv(
            pair_file,
            names=file_headers
        )

        # Record the currencies to which the data apply
        pair_df.loc[:, 'cur_from'] = cur_from
        pair_df.loc[:, 'cur_to'] = cur_to
        pair_df = pair_df[['cur_from', 'cur_to']+file_headers]

        # Convert unix timestamps to standard format
        pair_df.loc[:, 'timestamp'] = pd.to_datetime(pair_df['timestamp'], unit='s')

        pair_dfs[file_resolution] = pair_df

    # Load the data into postgres (one table for each resolution for now)
    for res, table in pair_dfs.items():
        table.to_sql(
            con=rcdb,
            schema='kraken',
            name=f'ohlcvt_{res}',
            if_exists='replace' if inx == 0 else 'append',
            method='multi')
