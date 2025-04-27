import sqlite3
import csv
import os
from tqdm import tqdm


con = sqlite3.connect('C:\\MyData\\trade\\code\\backtest\\data\\data.db')
cur = con.cursor()
data_scheme = 'ohlcv-1d'


for filepath in [f'{data_scheme}/raw/' + fn for fn in os.listdir(f'{data_scheme}/raw')]:
    if not filepath.endswith('csv'): continue
    with open(filepath, newline='') as file:
        reader = csv.reader(file)
        header = next(reader)
        for row in tqdm(reader, total=reader.line_num):
            cur.execute(f'INSERT INTO "{data_scheme}" VALUES (?, ?, ?, ?, ?, ?, ?)', (row[9], int(row[0])//1000000000, row[4], row[5], row[6], row[7], row[8]))
        con.commit()
