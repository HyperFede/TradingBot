from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import GOOG
import MetaTrader5 as mt5
import pandas as pd
import talib

#print(GOOG)

login = 8680460
password = "$nPrV0Nz"
server = "easyMarkets-Live"

def get_real_data(startPoint, numBars, timeframe):
    if not mt5.initialize("C:/Program Files/MetaTrader 5/terminal64.exe", login=login, password=password, server=server):
        print(f"initialization failed, error {mt5.last_error()}")
        mt5.shutdown()
    print("MT5 initialized")
    symbol = "XAUUSD"
    rates = mt5.copy_rates_from_pos(symbol, timeframe, startPoint, numBars) #Start point è la candela di inzio (0 = index corrente)
    #numBars = numero di candele da ottenere
    rates_df = pd.DataFrame(rates)
    rates_df['time'] = pd.to_datetime(rates_df['time'], unit='s')
    rates_df.drop(['spread', 'real_volume'], axis=1, inplace=True)
    rates_df.set_index("time", inplace=True)
    rates_df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "tick_volume": "Volume"}, inplace=True)
    rates_df.drop(rates_df.tail(1).index, inplace=True)
    return rates_df


df4h = get_real_data(0,2190, mt5.TIMEFRAME_H4)
df = get_real_data(0, 10000, mt5.TIMEFRAME_H1)
df1d = get_real_data(0, 365, mt5.TIMEFRAME_D1)
df1mFirst = get_real_data(0, 10000, mt5.TIMEFRAME_M1)
df1mSecond = get_real_data(10000, 10000, mt5.TIMEFRAME_M1)
df1mThird = get_real_data(20000, 10000, mt5.TIMEFRAME_M1)
frames = [df1mFirst, df1mSecond, df1mThird]
df1m = pd.concat(frames)
dfFilter = df.between_time('07:00', '16:00')

#print(df)

class EMATesting(Strategy):
    periodShort = 2
    periodLong = 11

    def init(self):
        self.demaShort = self.I(talib.DEMA, self.data.Close, self.periodShort)
        self.demaLong = self.I(talib.DEMA, self.data.Close, self.periodLong)

    def next(self):
        if crossover(self.demaShort, self.demaLong):
            #COMPRO LONG E VENDO SHORT
            if self.position.is_short or not self.position:
                self.position.close()
            #self.buy(size=1, sl=self.data.Low[-1])
            self.buy(size=1)
        elif crossover(self.demaLong, self.demaShort):
            #COMPRO SHORT E VENDO LONG
            if self.position.is_long or not self.position:
                self.position.close()
            #self.sell(size=1, sl=self.data.High[-1])
            self.sell(size=1)

bt = Backtest(df1mFirst, EMATesting, cash=10_000)
stats = bt.optimize(
    periodShort = range(2, 50),
    periodLong = range(9, 50),
    maximize = 'Equity Final [$]',
    constraint = lambda param: param.periodShort < param.periodLong
)

print(stats)
print(stats['_trades'])

bt.plot()