# TL;DR Workflow
```
1. Pick strategy in run.py → run_1d/run_1h → generate raw trades.
2. Run stats/extender.py → filter extended trades.
3. Run stats/stats.py → generate final stats.csv.
```

Main file: **`run.py`**  
- Import the strategy you want from the `strategies/` folder.  
- Use `run_1d` (for daily charts) or `run_1h` (for hourly charts).  
- Adjust backtest parameters (stop loss, reward, etc.) directly inside these functions (`grid` variable).

**⚡ Important:**  
At this stage, only **loose raw trades** are generated to keep the process efficient. Fine-tuning will happen later.

Raw trades are saved in:  
`data/trades-{strategy_name}/raw/trades-{parameter_combo}.csv`  
**The file name encodes the parameters. Pay attention — it matters.**

---

## Step 1: Generate Raw Trades
- In `run.py`, pick your strategy.
- Use `run_1d` or `run_1h` depending on timeframe.
- It will backtest over a *basic parameter grid* and save raw trades.

---

## Step 2: Extend the Grid
Use `stats/extender.py`.  
- Focuses on **pullback**, **rvol**, and **day_net_change** parameters.
- Reads raw trades, **filters** them **without** re-running full backtests (much faster, much cheaper).
- Saves filtered trades to:  
  `data/trades-{strategy_name}/extended/trades-{parameter_combo}.csv`

---

## Step 3: Generate Stats
Use `stats/stats.py`.  
- Aggregates results from extended trades.
- Outputs a `stats.csv` in each strategy's folder (`data/trades-{strategy_name}/stats.csv`).

This is your final summarized performance file, used for deeper analysis.

---

## Bonus
There's a chaotic analysis notebook: **`stats.ipynb`**.  
Use it at your own risk. No promises.

---


