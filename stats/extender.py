import pandas as pd
import json
import os
from itertools import product
from dataclasses import dataclass


@dataclass
class Filter:
    val: int | float
    op: str

f = Filter

def extend(df: pd.DataFrame, grid: dict[str, Filter], fixed_cols: list[str] = [], trade_on_open: bool = False, trim_pnl: str = ''):
    # fixed_cols - list of columns that were actually backtested
    pars_df = pd.DataFrame(
        data=df['Tag'].apply(lambda x: json.loads(x.replace("'", '"'))).to_list()
    )
    additional_cols = [c for c in pars_df.columns if (c not in fixed_cols) and (c not in grid.keys())]
    fixed_pars = {k: v for k, v in pars_df.iloc[0].items() if k in fixed_cols}
    df = pd.concat([df.drop(columns=['Tag']), pars_df], axis=1)

    # fix trade on open cuz wtf is this library
    if trade_on_open:
        df['ExitPrice'] = df['exit']
        df['PnL'] = df['Size'] * (df['ExitPrice'] - df['EntryPrice'])

    if trim_pnl == 'simple':
        base_risk = fixed_pars['sl_prc'] * 1000 # $1000
        def f(x):
            if x < 0 and x < -base_risk - 50:
                return -base_risk
            if x > 0 and x > base_risk * fixed_pars['reward'] + 50:
                return base_risk * fixed_pars['reward']
            return x
        df['PnL'] = df['PnL'].apply(f)
    elif trim_pnl == 'sl/tp':
        sl_mask = df['exit_reason'] == 'sl'
        df.loc[sl_mask, 'ExitPrice'] = df.loc[sl_mask, 'sl']
        df.loc[sl_mask, 'PnL'] = df.loc[sl_mask, 'Size'] * (df.loc[sl_mask, 'sl'] - df.loc[sl_mask, 'EntryPrice'])
        tp_mask = df['exit_reason'] == 'tp'
        df.loc[tp_mask, 'ExitPrice'] = df.loc[tp_mask, 'tp']
        df.loc[tp_mask, 'PnL'] = df.loc[tp_mask, 'Size'] * (df.loc[tp_mask, 'tp'] - df.loc[tp_mask, 'EntryPrice'])

    k = grid.keys()
    combs: list[dict[str, Filter]] = [dict(zip(k, v)) for v in product(*grid.values())]
    dfs = []
    for comb in combs:
        cdf = df.query(
            ' and '.join([f'{k} {v.op} {v.val}' for k, v in comb.items()])
        )
        dfs.append({
            'pars': {**{k: v.val for k, v in comb.items()}, **fixed_pars},
            'df': cdf[['Symbol', 'Size', 'EntryBar', 'ExitBar', 'EntryPrice', 'ExitPrice', 'SL', 'TP', 'PnL', 'EntryTime', 'ExitTime', 'Duration', *additional_cols]]
        })
    return dfs


tdir = os.path.abspath(os.pardir) + '/data/trades-simplepump-ocprc-1'

def extend_file(filepath):
    trades = pd.read_csv(filepath)
    
    edfs = extend(trades, {
        'day_net_change': [f(0.2, '>='), f(0.3, '>='), f(0.4, '>='), f(0.5, '>='), f(0.75, '>='), f(1, '>=')],
        'rvol': [f(3, '>='), f(4, '>='), f(5, '>='), f(7, '>='), f(10, '>=')],
        'pullback': [f(0.6, '<='), f(0.5, '<='), f(0.4, '<='), f(0.3, '<='), f(0.2, '<='), f(0.1, '<=')],
    }, ['sl_prc', 'reward'], trade_on_open=True, trim_pnl='sl/tp')

    for edf in edfs:
        edf_fpath = tdir + '/extended/' + 'trades-' + '-'.join([k + '=' + str(v) for k, v in edf['pars'].items()]) + '.csv'
        edf_fpath = edf_fpath.replace('sl/tp', 'sltp')  # kosstiliki cuz i zaebavsya
        if os.path.exists(edf_fpath): continue
        edf['df'].to_csv(edf_fpath, index=False)


if __name__ == '__main__':
    from tqdm.contrib.concurrent import process_map
    trades = [tdir + '/raw/' + fname for fname in os.listdir(tdir + '/raw')]
    process_map(extend_file, trades, max_workers=os.cpu_count())
        