from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd

from stats import get_winrate_ma, get_drawdown, get_used_bp


def get_ec_trace(df: pd.DataFrame, net=True):
    if net:
        ec = (df['PnL'] - df['Size'] * 0.014).cumsum()
    else:
        ec = df['PnL'].cumsum()
    return go.Scatter(x=df['ExitTime'].values, y=ec.values, name='PnL')

def get_winrate_trace(df: pd.DataFrame, window=100):
    return go.Scatter(x=df['ExitTime'].values, y=get_winrate_ma(df, window).values, name='Winrate')

def get_drawdown_trace(df: pd.DataFrame):
    return go.Bar(x=df['ExitTime'].values, y=get_drawdown(df).values, name='Drawdown')

def get_used_bp_trace(df: pd.DataFrame):
    bp_use = get_used_bp(df)
    return go.Scatter(x=bp_use['Time'].values, y=bp_use['Change'].values, name='BP Use')

def plot(df: pd.DataFrame):
    fig = make_subplots(
        rows=5, cols=1,
        specs=[
            [{'rowspan': 3}],
            [None],
            [None],
            [{}],
            [{}]
        ]
    )
    fig.add_trace(get_ec_trace(df), row=1, col=1)
    fig.add_trace(get_drawdown_trace(df), row=4, col=1)
    fig.add_trace(get_winrate_trace(df), row=5, col=1)
   
    return fig