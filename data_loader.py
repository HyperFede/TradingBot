import pandas as pd
from tvDatafeed import TvDatafeed, Interval
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DataLoader:
    def __init__(self):
        # Initialize TradingView connection without login
        self.tv = TvDatafeed()

    def fetch_data(self, symbol="XAUUSD", interval="H1", period="700d"):
        """
        Fetches historical OHLCV data from TradingView.
        Returns a DataFrame with columns: Open, High, Low, Close, Volume, and index Datetime.
        """
        print(f"Fetching data from TradingView for {symbol} ({interval}, {period})...")
        
        # Parse period to calculate approximate number of bars needed
        days = int(period.replace('d', ''))
        
        # Interval Mapping
        tv_interval = Interval.in_1_hour
        hours_per_day = 24
        
        if interval.lower() in ["1h", "h1"]:
            tv_interval = Interval.in_1_hour
            hours_per_day = 24
            
        n_bars = days * hours_per_day
        
        # Max limit for anonymous users is often 5000-10000 on TradingView
        # We cap it reasonably in case of limits, but passing higher limits sometimes works.
        try:
            # We explicitly target OANDA as the spot exchange proxy
            exchange = 'OANDA'
            df = self.tv.get_hist(symbol=symbol.replace("=X", "").replace("-USD", ""), exchange=exchange, interval=tv_interval, n_bars=n_bars)
            
            if df is None or df.empty:
                print("TradingView returned empty data. Trying different standard exchange.")
                df = self.tv.get_hist(symbol=symbol, exchange='FX_IDC', interval=tv_interval, n_bars=n_bars)
                
            if df is not None and not df.empty:
                # Rename columns from lower scale to standard format required by backtester
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                
                # Make timezone naive if needed
                if df.index.tzinfo is not None:
                    df.index = df.index.tz_convert(None)
                    
                return df
                
        except Exception as e:
            print(f"Error fetching from TradingView: {e}")
            
        return pd.DataFrame()

if __name__ == "__main__":
    loader = DataLoader()
    df = loader.fetch_data()
    print(df.tail())
