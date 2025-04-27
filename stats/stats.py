import pandas as pd
import os


def strip_pnl(x, sl_prc, reward, bp=1000):
    if x > 0 and x > sl_prc * bp * reward:
        return sl_prc * bp * reward
    elif x < 0 and x < -sl_prc * bp:
        return -sl_prc * bp
    return x

def get_used_bp(df: pd.DataFrame):
    events = []
    for _, row in df.iterrows():
        position_cost = row['Size'] * row['EntryPrice']
        events.append((row['EntryTime'], position_cost))
        events.append((row['ExitTime'], -position_cost))
    
    events_df = pd.DataFrame(events, columns=['Time', 'Change'])
    events_df = events_df.sort_values(by='Time')
    events_df['Change'] = events_df['Change'].cumsum()
    
    return events_df

def get_drawdown(df: pd.DataFrame):
    if 'EC' in df.columns:
        ec = df['EC']
    else:
        ec = df['PnL'].cumsum()
    return ec.cummax() - ec

def get_winrate_ma(df: pd.DataFrame, window: int = 100):
    wins = df['PnL'].apply(lambda x: 1 if x > 0 else 0)
    return wins.rolling(window).mean()

def get_stats(filepath: str) -> dict:
    filename = os.path.basename(filepath)
    pars = {}
    for p in filename[:-4].split('-')[1:]:
        k, v = p.split('=')
        pars[k] = float(v)
    df = pd.read_csv(filepath)

    stats = {}

    if 'sl_prc' in pars.keys():
        df['PnL'] = df['PnL'].apply(strip_pnl, args=(pars['sl_prc'], pars['reward']))
        df['rmult'] = df['PnL'] / (df['Size'] * df['EntryPrice'] * pars['sl_prc'])
    else:
        df['rmult'] = df['PnL'] / df[df['PnL'] < 0]['PnL'].mean()
    df['EntryTime'] = pd.to_datetime(df['EntryTime'])
    df['ExitTime'] = pd.to_datetime(df['ExitTime'])
    df = df.sort_values('ExitTime')
    df['NetPnL'] = df['PnL'] - df['Size'] * 0.014
    df['EC'] = df['PnL'].cumsum()
    df['NetEC'] = df['NetPnL'].cumsum()
    stats['PnL'] = df['EC'].iloc[-1]
    stats['NetPnL'] = df['NetEC'].iloc[-1]
    stats['winrate'] = df[df['PnL'] > 0].shape[0] / df.shape[0]
    stats['total_trades'] = df.shape[0]
    stats['total_volume'] = df['Size'].sum()

    df['loss'] = df['PnL'].apply(lambda x: 1 if x < 0 else 0)
    df['streak'] = (df['loss'] != df['loss'].shift()).cumsum()  # basically creates an index for each lossing streak
    stats['max_lossing_streak'] = df.groupby('streak')['loss'].sum().max()

    df['drawdown'] = get_drawdown(df)
    stats['max_drawdown'] = df['drawdown'].max()

    stats['max_used_bp'] = get_used_bp(df)['Change'].max()

    stats['sqn'] = df['rmult'].mean() / df['rmult'].std() * (df.shape[0] ** 0.5)
    stats['std_profit'] = df[df['PnL'] > 0]['PnL'].std()
    stats['std_loss'] = df[df['PnL'] < 0]['PnL'].std()
    stats['avg_profit'] = df[df['PnL'] > 0]['PnL'].mean()
    stats['avg_loss'] = df[df['PnL'] < 0]['PnL'].mean()

    df = df.set_index('ExitTime')
    stats['avg_day_profit'] = df.resample('D')['PnL'].sum().mean()
    stats['std_day_profit'] = df.resample('D')['PnL'].sum().std()

    days = (df.index[-1] - df.index[0]).days
    years = days / 365
    growth = df['NetEC'].iloc[-1] / df['NetEC'].iloc[0]
    stats['cagr'] = growth ** (1 / years) - 1 if growth > 0 else 0

    daily_returns = df['NetEC'].resample('D').last().pct_change(fill_method=None).dropna()
    stats['sharpe'] = daily_returns.mean() / daily_returns.std() * (252**0.5)

    drawdowns_pct = (df['NetEC'] / df['NetEC'].cummax() - 1) * 100
    stats['ulcer'] = ((drawdowns_pct ** 2).mean())**0.5

    stats['score'] = stats['cagr'] * stats['sharpe'] / (stats['ulcer'] + 1e-6)

    return {**pars, **stats}

if __name__ == '__main__':
    from tqdm.contrib.concurrent import process_map
    import os
    tdir = os.path.abspath(os.pardir) + '\\data\\trades-simplepump-ocprc-1'
    def load_df(fname: str):
        pars = {}
        for p in fname[:-4].split('-')[1:]:
            k, v = p.split('=')
            pars[k] = float(v)
        df = pd.read_csv(tdir + '\\extended\\' + fname)
        return {'df': df, 'pars': pars}

    stats = process_map(
        get_stats,
        [tdir + '\\extended\\' + fname for fname in os.listdir(tdir + '\\extended')],
        max_workers=os.cpu_count(),
        desc='STATS',
        chunksize=1
    )
    pd.DataFrame(data=stats).to_csv(tdir + '\\stats.csv', index=False)