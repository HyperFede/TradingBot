import pandas as pd
import numpy as pd_np
import numpy as np

def calculate_sma(df, period, column='Close'):
    """Calculate Simple Moving Average."""
    return df[column].rolling(window=period).mean()

def calculate_rsi(df, period=14, column='Close'):
    """
    Calculate Relative Strength Index (Wilder's standard).
    """
    delta = df[column].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Calculate standard Wilder's EWMA
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def identify_bearish_fvgs(df):
    """
    Identifies Bearish Fair Value Gaps.
    Occurs when Low of Candle 1 > High of Candle 3.
    """
    # Shift positive goes backwards in time. 
    # df['Low'].shift(2) -> Candle 1 Low (2 periods ago)
    # df['High'] -> Candle 3 High (Current period)
    
    low_1 = df['Low'].shift(2)
    high_3 = df['High']
    
    # Bearish FVG Condition
    is_fvg = low_1 > high_3
    
    # The FVG zone is between High of Candle 3 and Low of Candle 1
    fvg_bottom = high_3
    fvg_top = low_1
    
    # Calculate the gap size
    fvg_size = fvg_top - fvg_bottom
    
    fvg_df = pd.DataFrame({
        'is_bearish_fvg': is_fvg,
        'bear_fvg_top': fvg_top,
        'bear_fvg_bottom': fvg_bottom,
        'bear_fvg_size': fvg_size
    }, index=df.index)
    
    return fvg_df

def identify_bullish_fvgs(df):
    """
    Identifies Bullish Fair Value Gaps.
    Occurs when High of Candle 1 < Low of Candle 3.
    """
    high_1 = df['High'].shift(2)
    low_3 = df['Low']
    
    # Bullish FVG Condition
    is_fvg = high_1 < low_3
    
    # The FVG zone is between High of Candle 1 and Low of Candle 3
    # Top = Low of Candle 3, Bottom = High of Candle 1
    fvg_top = low_3
    fvg_bottom = high_1
    
    fvg_size = fvg_top - fvg_bottom
    
    fvg_df = pd.DataFrame({
        'is_bullish_fvg': is_fvg,
        'bull_fvg_top': fvg_top,
        'bull_fvg_bottom': fvg_bottom,
        'bull_fvg_size': fvg_size
    }, index=df.index)
    
    return fvg_df

def calculate_sma_slope(series, period=5):
    """
    Calculates the slope of a series (e.g., SMA) over a given period.
    Positive slope means moving up, negative means moving down.
    """
    return series.diff(period)

def add_all_indicators(df):
    """
    Master function to add all technical indicators to the DataFrame.
    """
    # Ensure dataframe is sorted by time ascending
    df = df.sort_index()
    
    # 1. SMAs
    df['SMA_9'] = df['Close'].rolling(window=9).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    # Add SMA slopes (over recent 3 periods for stability)
    df['SMA_9_slope'] = calculate_sma_slope(df['SMA_9'], period=3)
    df['SMA_20_slope'] = calculate_sma_slope(df['SMA_20'], period=3)
    
    # 2. RSI (14 period)
    df['RSI_14'] = calculate_rsi(df, period=14)
    
    # 3. FVGs
    bear_fvg_df = identify_bearish_fvgs(df)
    bull_fvg_df = identify_bullish_fvgs(df)
    
    # Concatenate results
    df = pd.concat([df, bear_fvg_df, bull_fvg_df], axis=1)
    
    return df
