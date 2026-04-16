import pandas as pd
from data_loader import DataLoader
from indicators import add_all_indicators
from strategy import FVGStrategy

def run_backtest(symbol="XAUUSD", interval="1h", period="300d", position_size=0.01):
    """
    Run the full backtest.
    Returns:
        - df: The dataframe with all indicators.
        - trades: A list of executed trades.
    """
    loader = DataLoader()
    
    # 1. Fetch Data
    df = loader.fetch_data(symbol, interval, period)
    
    # 2. Compute Indicators
    df = add_all_indicators(df)
    
    # 3. Simulate Strategy
    strategy = FVGStrategy(position_size=position_size)
    all_trades = []
    
    # Loop over bars
    for idx, row in df.iterrows():
        # Iterate handles timezone and index naturally
        closed_trades = strategy.evaluate_bar(row)
        if closed_trades:
            all_trades.extend(closed_trades)
            
    # Finalize FVG endpoints for the ones still open
    end_index = df.index[-1]
    for fvg in strategy.all_fvg_log:
        if fvg['end_time'] is None:
            fvg['end_time'] = end_index
            
    # Compile Trade History
    trades_df = pd.DataFrame(all_trades)
    
    return df, trades_df, strategy.all_fvg_log

if __name__ == '__main__':
    df, trades, fvg_log = run_backtest()
    print(f"Backtest complete. Number of trades: {len(trades)}")
    if not trades.empty:
        print(trades.head())
        print(f"Total PnL: {trades['pnl'].sum()}")
