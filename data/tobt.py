from tqdm import tqdm
import pandas as pd
import sqlite3
import os
import multiprocessing as mp
from utils import localize_ts

def init_db(db_path):
    global con
    con = sqlite3.connect(db_path)

def process_symbol(args):
    scheme, symbol = args
    df = pd.read_sql(f'SELECT * FROM "{scheme}" WHERE symbol = "{symbol}"', con)
    df['timestamp'] = df['timestamp'].apply(lambda ts: localize_ts(ts, 'America/New_York').strftime('%Y-%m-%d %H:%M:%S'))
    df.rename(columns={'timestamp': 'datetime'}).to_csv(f'data/{scheme}/backtrader/{symbol}.csv', index=False)

def main():
    db_path = 'data/data.db'
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    for scheme in ['ohlcv-1d', 'ohlcv-1h']:
        symbols = [s[0] for s in cur.execute(f'SELECT DISTINCT symbol FROM "{scheme}"')]
        dir_path = f'data/{scheme}/backtrader'
        os.makedirs(dir_path, exist_ok=True)
        
        with mp.Pool(mp.cpu_count(), initializer=init_db, initargs=(db_path,)) as pool:
            list(tqdm(pool.imap(process_symbol, [(scheme, symbol) for symbol in symbols]), total=len(symbols), desc=scheme))

    con.close()

if __name__ == "__main__":
    main()