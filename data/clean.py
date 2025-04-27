import csv
import os
import sqlite3


connection = sqlite3.connect('data.db')
cursor = connection.cursor()


daily_dir = 'ohlcv-1d/backtrader'
hourly_dir = 'ohlcv-1h/backtrader'

files = os.listdir(daily_dir)
for i, symbol_fn in enumerate(files, start=1):
    symbol = symbol_fn.split('.')[0]
    with open(f'{daily_dir}/{symbol_fn}', newline='') as file:
        reader = csv.reader(file)
        header = next(reader)
        days = sum(1 for _ in reader)
    if days < 60:
        print(f'{i}/{len(files)} {symbol_fn} {days}')
        os.remove(f'{daily_dir}/{symbol_fn}')
        os.remove(f'{hourly_dir}/{symbol_fn}')
        cursor.execute(f'DELETE FROM "ohlcv-1d" WHERE symbol = "{symbol}"')
        cursor.execute(f'DELETE FROM "ohlcv-1h" WHERE symbol = "{symbol}"')
        connection.commit()