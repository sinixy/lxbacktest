from pytz import timezone
from datetime import datetime
import pandas as pd


def split_into_symbol_batches(symbols: list[dict], batch_size: int = 2000):
    batches = [symbols[i : i + batch_size] for i in range(0, len(symbols), batch_size)]
    return [[record['symbol'] for record in batch] for batch in batches]

def localize_ts(ts: int, tz: str):
    '''
    ts: int - UNIX timestamp (seconds)
    tz: str - e.g. "America/New_York"
    '''
    return timezone(tz).localize(datetime.fromtimestamp(ts))

def load_by_stats(stats: dict, dirpath: str, pars: list[str] = ['day_net_change', 'rvol', 'pullback']) -> pd.DataFrame:
    filename = 'trades-' + '-'.join([f'{p}={stats[p]}' for p in pars]) + '.csv'
    df = pd.read_csv(dirpath + '\\' + filename)
    df['EntryTime'] = pd.to_datetime(df['EntryTime'])
    df['ExitTime'] = pd.to_datetime(df['ExitTime'])
    df = df.sort_values('ExitTime')
    return df
