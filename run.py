import pandas as pd
import os
import warnings
import multiprocessing as mp
import sqlite3
from itertools import product
from tqdm import tqdm
from tqdm.contrib.concurrent import process_map
from backtesting import Backtest, Strategy

warnings.filterwarnings('ignore')


def backtest_df(args: dict):
    def func(df: pd.DataFrame, strategy_pars: dict, strategy: Strategy):
        backtest = Backtest(df, strategy, cash=10000, trade_on_close=True)  # trade_on_close !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        stats = backtest.run(**strategy_pars)
        stats._trades.insert(0, 'Symbol', df['symbol'].iloc[0])
        return stats._trades[['Symbol', 'Size', 'EntryBar', 'ExitBar', 'EntryPrice', 'ExitPrice', 'SL', 'TP', 'PnL', 'ReturnPct', 'EntryTime', 'ExitTime', 'Duration', 'Tag']]
    return func(args['df'], args['strategy_pars'], args['strategy'])

def load_df(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    return df

def run_single(symbol: str, strategy: Strategy, timeframe: str):
    data_dir = f'data/ohlcv-{timeframe}/backtrader'
    df = load_df(data_dir + f'/{symbol}.csv')
    backtest = Backtest(df, strategy, cash=10000, trade_on_close=True)
    stats = backtest.run()
    stats._trades.insert(0, 'Symbol', df['symbol'].iloc[0])
    stats._trades.to_csv('trades.csv', index=False)
    return stats

def run_1h(name):
    data_dir = 'data/ohlcv-1h/backtrader'
    symbols = (pd.read_csv('trades/sample.csv')['Symbol'] + '.csv').unique()  # initial backtest with the most loose pars to cut the amount of symbols to test
    dfs = process_map(
        load_df,
        [data_dir + '/' + symbol_fn for symbol_fn in os.listdir(data_dir) if symbol_fn in symbols],
        max_workers=mp.cpu_count(),
        desc='Data'
    )

    grid = {
        'sl_prc': [0.1, 0.2, 0.3, 0.4, 0.5],
        'reward': [1, 2, 3, 4, 5],  # тестнуть більші значення
        'entry_hour': [15, 4, 6, 7, 8],
        'pullback': [0.6],
        'rvol': [3],
        'day_net_change': [0.2],
    }
    keys = grid.keys()
    combs = [dict(zip(keys, pars)) for pars in product(*grid.values())]
    for pars in tqdm(combs, desc='Grid'):
        res = process_map(backtest_df, [{'df': df, 'strategy_pars': pars} for df in dfs], max_workers=mp.cpu_count(), desc='Backtesting')
        
        stats = pd.DataFrame(columns=res[0].columns)
        for df in res:
            stats = pd.concat([stats, df], ignore_index=True)
        stats.to_csv(
            'trades/trades-' + '-'.join([k + '=' + str(v) for k, v in pars.items()]) + '.csv',
            index=False
        )

def run_1d(name, strategy):
    if not os.path.exists(f'data/trades-{name}/raw'): os.makedirs(f'data/trades-{name}/raw')
    data_dir = 'data/ohlcv-1d/backtrader'
    conn = sqlite3.connect('data/data.db')
    symbols = (pd.read_sql('SELECT DISTINCT symbol FROM "ohlcv-1d"', conn)['symbol'] + '.csv').values
    dfs = process_map(
        load_df,
        [data_dir + '/' + symbol_fn for symbol_fn in os.listdir(data_dir) if symbol_fn in symbols],
        max_workers=mp.cpu_count(),
        desc='Data'
    )

    grid = {
        'sl_prc': [0.1, 0.2, 0.3, 0.4, 0.5],
        'reward': [1, 2, 3, 4, 5],  # тестнуть більші значення
        'fibo': [0, 1, 2, 3, 4, 5],
        'pullback': [0.6],
        'rvol': [3],
        'day_net_change': [0.2]
    }
    keys = grid.keys()
    combs = [dict(zip(keys, pars)) for pars in product(*grid.values())]
    for pars in tqdm(combs, desc='Grid'):
        res = process_map(backtest_df, [{'df': df, 'strategy_pars': pars, 'strategy': strategy} for df in dfs], max_workers=mp.cpu_count(), desc='Backtesting')
        
        stats = pd.DataFrame(columns=res[0].columns)
        for df in res:
            stats = pd.concat([stats, df], ignore_index=True)
        stats.to_csv(
            f'data/trades-{name}/raw/trades-' + '-'.join([k + '=' + str(v) for k, v in pars.items()]) + '.csv',
            index=False
        )

if __name__ == '__main__':
    # run_single('RGTI')
    from strategies.momopump import SimplePumpDaily_Fibo
    run_1d('simplepump-fibo-1', SimplePumpDaily_Fibo)
    # run_single('RGTI', SimplePumpDaily_Fibo, '1d')