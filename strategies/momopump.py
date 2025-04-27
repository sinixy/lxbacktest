from backtesting import Strategy
import pandas as pd
import backtesting.lib


def SMA(values, n):
    """
    Return simple moving average of `values`, at
    each step taking into account `n` previous values.
    """
    return pd.Series(values).rolling(n).mean()

FIBO = {
    0: 0,
    1: 0.236,
    2: 0.382,
    3: 0.5,
    4: 0.618,
    5: 0.786
}

class SimplePump(Strategy):

    """
    The Base strategy. 1h version of it, actually.

    If on a single day the stock rose by more than day_net_change, with relative volume > rvol,
    and pullbacked from its high to the close of the day < pullback,
    then buy at entry_hour with stop % = sl_prc, and take profit % = sl_prc * reward.
    """

    pullback = 0.5
    rvol = 5
    day_net_change = 0.3
    entry_hour = 6
    sl_prc = 0.3
    reward = 2

    def init(self):
        daily_volume = backtesting.lib.resample_apply('1D', lambda x: x, self.data.Volume, agg='sum')
        self.adv = self.I(SMA, daily_volume, 16*14)

        self.prev_day_close = self.data.Close[0]
        self.day_high = self.data.High[0]
        self.day_low = self.data.Low[0]
        self.day_volume = 0

        self.status = {
            'waiting_for_entry': False,
            'triggered_datetime': None,
            'tag': {}
        }

    def next(self):
        dt, open, high, low, close = self.data.index, self.data.Open, self.data.High, self.data.Low, self.data.Close
        self.day_volume += self.data.Volume[-1]

        if dt[-1].day != dt[-2].day:
            self.day_volume = self.data.Volume[-1]
            self.day_high = high[-1]
            self.day_low = low[-1]
            if self.position:
                trade = self.trades[-1]
                if (dt[-1].date() - trade.entry_time.date()) >= pd.Timedelta(days=5):
                    self.position.close()
        if high[-1] > self.day_high:
            self.day_high = high[-1]
        if low[-1] < self.day_low:
            self.day_low = low[-1]

        if self.status['waiting_for_entry']:
            if dt[-1].date() > self.status['triggered_datetime'].date() and dt[-1].hour >= self.entry_hour:
                self.buy_fixed(close[-1], self.status['tag'])
                self.status['waiting_for_entry'] = False

        if dt[-1].hour != 15: return

        day_net_change = (self.day_high - self.prev_day_close) / self.prev_day_close
        rvol = self.day_volume / self.adv[-1]
        pullback = (self.day_high - close[-1]) / (self.day_high - self.day_low)  # also try day_open instead of day_low
        
        if rvol > self.rvol and day_net_change > self.day_net_change and pullback < self.pullback and not self.position:
            tag = {'pullback': float(pullback), 'rvol': float(rvol), 'day_net_change': float(day_net_change), 'entry_hour': self.entry_hour, 'sl_prc': self.sl_prc, 'reward': self.reward}
            if self.entry_hour == 15:
                self.buy_fixed(close[-1], tag)
            else:
                self.status['waiting_for_entry'] = True
                self.status['triggered_datetime'] = dt[-1]
                self.status['tag'] = tag
        
        self.prev_day_close = close[-1]

    def buy_fixed(self, price, tag, bp=1000):
        self.buy(
            size=round(bp/price),
            tp=round(price * (1 + self.sl_prc*self.reward), 3),
            sl=round(price * (1 - self.sl_prc), 3),
            tag=tag
        )

class SimplePumpDaily_Fibo(Strategy):

    """
    Enter on close with stop at fibo level and exit at tp or close of the next day.
    """

    pullback = 0.6
    rvol = 3
    day_net_change = 0.3
    sl_prc = 0.3
    reward = 2
    fibo = 0 # 0 = 0, 1 = 0.236, 2 = 0.382, 3 = 0.5, 4 = 0.618, 5 = 0.786

    def init(self):
        self.adv = self.I(SMA, self.data.Volume, 14)

        self.status = {
            'waiting_for_entry': False,
            'triggered_datetime': None,
            'tag': {}
        }

    def next(self):
        dt, open, high, low, close = self.data.index, self.data.Open, self.data.High, self.data.Low, self.data.Close
        if self.position:
            exit_reason = 'close'
            self.status['tag']['exit'] = float(close[-1])
            if low[-1] <= self.status['tag']['sl']:
                exit_reason = 'sl'
                self.status['tag']['exit'] = self.status['tag']['sl']
            elif high[-1] >= self.status['tag']['tp']:
                exit_reason = 'tp'
                self.status['tag']['exit'] = self.status['tag']['tp']
            self.status['tag']['exit_reason'] = exit_reason
            self.position.close()
        day_net_change = (high[-1] - close[-2]) / close[-2]
        rvol = self.data.Volume[-1] / self.adv[-1]
        pullback = (high[-1] - close[-1]) / (high[-1] - low[-1])
        if rvol > self.rvol and day_net_change > self.day_net_change and pullback < self.pullback and not self.position:
            tp = round(close[-1] * (1 + self.sl_prc*self.reward), 3)
            sl = round((high[-1] - low[-1]) * FIBO[self.fibo] + low[-1], 3)
            if sl >= close[-1]:
                sl = round((high[-1] - low[-1]) * FIBO[self.fibo-1] + low[-1], 3)
            self.status['tag'] = {
                'pullback': float(pullback),
                'rvol': float(rvol),
                'day_net_change': float(day_net_change),
                'sl_prc': self.sl_prc,
                'reward': self.reward,
                'fibo': self.fibo,
                'tp': tp,
                'sl': sl
            }
            self.buy(size=round(1000/close[-1]), tag=self.status['tag'])  # it's fine to modify self.status['tag'] until you close this position

    @classmethod
    def pars(cls):
        # the order actually matters, cause in this order params are written for the filename
        return ['day_net_change', 'rvol', 'pullback', 'sl_prc', 'reward', 'fibo']


class SimplePumpDaily_CC(Strategy):

    """
    Just enter on close and exit on close of the next day.
    """

    pullback = 0.5
    rvol = 5
    day_net_change = 0.3

    def init(self):
        self.adv = self.I(SMA, self.data.Volume, 14)

        self.status = {
            'waiting_for_entry': False,
            'triggered_datetime': None,
            'tag': {}
        }

    def next(self):
        dt, open, high, low, close = self.data.index, self.data.Open, self.data.High, self.data.Low, self.data.Close
        if self.position:
            self.position.close()
        day_net_change = (high[-1] - close[-2]) / close[-2]
        rvol = self.data.Volume[-1] / self.adv[-1]
        pullback = (high[-1] - close[-1]) / (high[-1] - low[-1])
        if rvol > self.rvol and day_net_change > self.day_net_change and pullback < self.pullback and not self.position:
            self.status['tag'] = {
                'pullback': float(pullback),
                'rvol': float(rvol),
                'day_net_change': float(day_net_change),
            }
            self.buy(size=round(1000/close[-1]), tag=self.status['tag'])

    @classmethod
    def pars(cls):
        # the order actually matters, cause in this order params are written for the filename
        return ['day_net_change', 'rvol', 'pullback']

class SimplePumpDaily_CCPRC(Strategy):

    """
    Just enter on close and exit on close of the next day, or if SL/TP is triggered.
    """

    pullback = 0.5
    rvol = 5
    day_net_change = 0.3
    sl_prc = 0.3
    reward = 2

    def init(self):
        self.adv = self.I(SMA, self.data.Volume, 14)

        self.status = {
            'waiting_for_entry': False,
            'triggered_datetime': None,
            'tag': {}
        }

    def next(self):
        dt, open, high, low, close = self.data.index, self.data.Open, self.data.High, self.data.Low, self.data.Close
        if self.position:
            self.status['tag']['exit_reason'] = 'close'
            self.position.close()
        day_net_change = (high[-1] - close[-2]) / close[-2]
        rvol = self.data.Volume[-1] / self.adv[-1]
        pullback = (high[-1] - close[-1]) / (high[-1] - low[-1])
        if rvol > self.rvol and day_net_change > self.day_net_change and pullback < self.pullback and not self.position:
            tp = round(close[-1] * (1 + self.sl_prc*self.reward), 3)
            sl = round(close[-1] * (1 - self.sl_prc), 3)
            self.status['tag'] = {
                'pullback': float(pullback),
                'rvol': float(rvol),
                'day_net_change': float(day_net_change),
                'sl_prc': self.sl_prc,
                'reward': self.reward,
                'tp': tp,
                'sl': sl,
                'exit_reason': 'sltp'
            }
            self.buy(size=round(1000/close[-1]), tp=tp, sl=sl, tag=self.status['tag'])

    @classmethod
    def pars(cls):
        # the order actually matters, cause in this order params are written for the filename
        return ['day_net_change', 'rvol', 'pullback', 'sl_prc', 'reward']

class SimplePumpDaily_OC(Strategy):
    # !!! trade_on_close = False !!!

    """
    Just enter on open of the next day and exit on close of the next day.
    """

    pullback = 0.5
    rvol = 5
    day_net_change = 0.3

    def init(self):
        self.adv = self.I(SMA, self.data.Volume, 14)

        self.status = {
            'waiting_for_entry': False,
            'triggered_datetime': None,
            'tag': {}
        }

    def next(self):
        dt, open, high, low, close = self.data.index, self.data.Open, self.data.High, self.data.Low, self.data.Close
        if self.position:
            self.status['tag']['exit'] = float(close[-1])
            self.position.close()
        day_net_change = (high[-1] - close[-2]) / close[-2]
        rvol = self.data.Volume[-1] / self.adv[-1]
        pullback = (high[-1] - close[-1]) / (high[-1] - low[-1])
        if rvol > self.rvol and day_net_change > self.day_net_change and pullback < self.pullback and not self.position:
            self.status['tag'] = {
                'pullback': float(pullback),
                'rvol': float(rvol),
                'day_net_change': float(day_net_change)
            }
            self.buy(size=round(1000/close[-1]), tag=self.status['tag'])

    @classmethod
    def pars(cls):
        # the order actually matters, cause in this order params are written for the filename
        return ['day_net_change', 'rvol', 'pullback']

class SimplePumpDaily_OCPRC(Strategy):
    # !!! trade_on_close = False !!!

    """
    Just enter on open of the next day and exit on close of the next day, or if SL/TP is triggered.
    """

    pullback = 0.5
    rvol = 5
    day_net_change = 0.3
    sl_prc = 0.3
    reward = 2

    def init(self):
        self.adv = self.I(SMA, self.data.Volume, 14)

        self.status = {
            'waiting_for_entry': False,
            'triggered_datetime': None,
            'tag': {}
        }

    def next(self):
        dt, open, high, low, close = self.data.index, self.data.Open, self.data.High, self.data.Low, self.data.Close
        if self.position:
            exit_reason = 'close'
            exit_price = float(close[-1])
            if low[-1] <= self.status['tag']['sl']:
                exit_reason = 'sl'
                exit_price = self.status['tag']['sl']
            elif high[-1] >= self.status['tag']['tp']:
                exit_reason = 'tp'
                exit_price = self.status['tag']['tp']
            self.status['tag']['exit_reason'] = exit_reason
            self.status['tag']['exit'] = exit_price
            self.position.close()
        day_net_change = (high[-1] - close[-2]) / close[-2]
        rvol = self.data.Volume[-1] / self.adv[-1]
        pullback = (high[-1] - close[-1]) / (high[-1] - low[-1])
        if rvol > self.rvol and day_net_change > self.day_net_change and pullback < self.pullback and not self.position:
            tp = round(close[-1] * (1 + self.sl_prc*self.reward), 3)
            sl = round(close[-1] * (1 - self.sl_prc), 3)
            self.status['tag'] = {
                'pullback': float(pullback),
                'rvol': float(rvol),
                'day_net_change': float(day_net_change),
                'sl_prc': self.sl_prc,
                'reward': self.reward,
                'tp': tp,
                'sl': sl,
                'exit_reason': 'sltp'
            }
            self.buy(size=round(1000/close[-1]), tag=self.status['tag'])

    @classmethod
    def pars(cls):
        # the order actually matters, cause in this order params are written for the filename
        return ['day_net_change', 'rvol', 'pullback', 'sl_prc', 'reward']