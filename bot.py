import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import numpy as np
import talib

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
    st.write(rates_df)
    return rates_df


df4h = get_real_data(0,25000, mt5.TIMEFRAME_H4)
df = get_real_data(0, 25000, mt5.TIMEFRAME_M15)
df.drop(['real_volume'], axis=1, inplace=True)

def support(df, l, n1, n2):
    for i in range(l-n1+1, l+1):
        if(df.low[i]>df.low[i-1]):
            return 0
    
    for i in range(l+1, l+n2+1):
        if(df.low[i]<df.low[i-1]):
            return 0
    
    return 1

def resistance(df, l, n1, n2):
    for i in range(l-n1+1, l+1):
        if(df.high[i]<df.high[i-1]):
            return 0
    for i in range(l+1, l+n2+1):
        if(df.high[i]>df.high[i-1]):
            return 0
    
    return 1

def FVG(df, l): #l = middle candle
    if df.low[l+1] > df.high[l-1]: #and (df.low[l+1]-df.high[l-1])<0.005: #GREEN
        gap_start = df.high[l-1]
        gap_end = df.low[l+1]
        isFilled = False
        for i in range(l+1, len(df)):
            #if df.high[i] >= gap_end:
            if df.close[i] > gap_end and df.open[i] < gap_start or (gap_end - gap_start)/gap_start < 0.005: # Se il corpo di una candela successiva ha coperto il gap
                isFilled = True
        if isFilled == False:
            return (l, gap_start, gap_end, 1)
    if df.low[l-1] > df.high[l+1]: #and (df.low[l-1]-df.high[l+1])<0.005: #RED
        gap_start = df.low[l-1]
        gap_end = df.high[l+1]
        isFilled = False
        for i in range(l+1, len(df)):
            if df.open[i] > gap_end and df.close[i] < gap_start or (gap_start - gap_end)/gap_start < 0.005:
                isFilled = True
        if isFilled == False:
            return (l, gap_start, gap_end, 2)
    
    return 0

def OrderBlocks(df, l, trigger=0.01):
    if (df.close[l] < df.open[l] and df.close[l+1] > df.open[l+1]) and ((df.close[l] - df.low[l])/df.close[l] < 0.005 and (df.open[l+1] - df.low[l+1])/df.open[l+1] < 0.005): #Rossa + verde
        #priceMovement = (df.open[l+1]-df.close[l+1]) / df.open[l+1]
        priceMovement = (df.close[l] - df.open[l+1]) / df.close[l]
        if abs(priceMovement) <= trigger:
            return 1
    if (df.close[l] > df.open[l] and df.close[l+1] < df.open[l+1]) and ((df.high[l] - df.close[l])/df.high[l] < 0.005 and (df.high[l+1] - df.open[l+1])/df.high[l+1] < 0.005): #Verde + Rossa
        priceMovement = (df.close[l]-df.open[l+1]) / df.close[l]
        if abs(priceMovement) <= trigger:
            return 2
    
    return 0

# def liquidity(df, l, trigger = 0.005):
#     #GREEN
#     if(df.close[l] > df.open[l] and (df.open[l] - df.low[l])/df.open[l] >= trigger):
#         space = 
#         for i in range(l+1, len(df)):
#             if 

def atr(df, n):
    """Calculate the Average True Range (ATR)."""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(n).mean()

def detect_liquidity_zones(df, liq_len, liq_mar, atr_period, mode='Present', vis_liq=3):
    """Detect Buyside and Sellside liquidity zones."""
    df['atr'] = atr(df, atr_period)
    df['atr200'] = atr(df, 200)
    
    max_size = 50
    per = mode == 'Present'
    
    # Initialize variables
    zz_d = [0] * max_size
    zz_x = [0] * max_size
    zz_y = [np.nan] * max_size
    
    b_liq_B = []
    b_liq_S = []
    
    for i in range(liq_len, len(df)):
        if i >= len(df) - 1:
            break
            
        ph = df['high'][i-liq_len:i+1].max()
        pl = df['low'][i-liq_len:i+1].min()
        
        if df['high'][i] == ph:
            dir = zz_d[0]
            x1 = zz_x[0]
            y1 = zz_y[0]
            y2 = df['high'][i]
            
            if dir < 1:
                zz_d.insert(0, 1)
                zz_x.insert(0, i)
                zz_y.insert(0, y2)
                zz_d.pop()
                zz_x.pop()
                zz_y.pop()
            else:
                if dir == 1 and y2 > y1:
                    zz_x[0] = i
                    zz_y[0] = y2
            
            if per:
                count = 0
                st_P = 0.0
                st_B = 0
                minP = 0.0
                maxP = 1e6
                
                for j in range(max_size):
                    if zz_d[j] == 1:
                        if zz_y[j] > ph + (df['atr'][i] / liq_mar):
                            break
                        elif ph - (df['atr'][i] / liq_mar) <= zz_y[j] <= ph + (df['atr'][i] / liq_mar):
                            count += 1
                            st_B = zz_x[j]
                            st_P = zz_y[j]
                            minP = max(minP, zz_y[j])
                            maxP = min(maxP, zz_y[j])
                
                if count > 2:
                    if b_liq_B and st_B == b_liq_B[0]['bx'][0]:
                        b_liq_B[0]['bx'] = [st_B, (minP + maxP) / 2 + (df['atr'][i] / liq_mar), i + 10, (minP + maxP) / 2 - (df['atr'][i] / liq_mar)]
                    else:
                        b_liq_B.insert(0, {
                            'bx': [st_B, (minP + maxP) / 2 + (df['atr'][i] / liq_mar), i + 10, (minP + maxP) / 2 - (df['atr'][i] / liq_mar)],
                            'st_P': st_P,
                            'label': 'Buyside liquidity'
                        })
                    if len(b_liq_B) > vis_liq:
                        b_liq_B.pop()
        
        if df['low'][i] == pl:
            dir = zz_d[0]
            x1 = zz_x[0]
            y1 = zz_y[0]
            y2 = df['low'][i]
            
            if dir > -1:
                zz_d.insert(0, -1)
                zz_x.insert(0, i)
                zz_y.insert(0, y2)
                zz_d.pop()
                zz_x.pop()
                zz_y.pop()
            else:
                if dir == -1 and y2 < y1:
                    zz_x[0] = i
                    zz_y[0] = y2
            
            if per:
                count = 0
                st_P = 0.0
                st_B = 0
                minP = 0.0
                maxP = 1e6
                
                for j in range(max_size):
                    if zz_d[j] == -1:
                        if zz_y[j] < pl - (df['atr'][i] / liq_mar):
                            break
                        elif pl - (df['atr'][i] / liq_mar) <= zz_y[j] <= pl + (df['atr'][i] / liq_mar):
                            count += 1
                            st_B = zz_x[j]
                            st_P = zz_y[j]
                            minP = max(minP, zz_y[j])
                            maxP = min(maxP, zz_y[j])
                
                if count > 2:
                    if b_liq_S and st_B == b_liq_S[0]['bx'][0]:
                        b_liq_S[0]['bx'] = [st_B, (minP + maxP) / 2 + (df['atr'][i] / liq_mar), i + 10, (minP + maxP) / 2 - (df['atr'][i] / liq_mar)]
                    else:
                        b_liq_S.insert(0, {
                            'bx': [st_B, (minP + maxP) / 2 + (df['atr'][i] / liq_mar), i + 10, (minP + maxP) / 2 - (df['atr'][i] / liq_mar)],
                            'st_P': st_P,
                            'label': 'Sellside liquidity'
                        })
                    if len(b_liq_S) > vis_liq:
                        b_liq_S.pop()
    
    return b_liq_B, b_liq_S

def add_liquidity_zones(fig, b_liq_B, b_liq_S):
    for zone in b_liq_B:
        fig.add_shape(type="line",
                      x0=zone['bx'][0], x1=zone['bx'][2], y0=zone['bx'][3], y1=zone['bx'][3],
                      line=dict(color="purple", width=2),
                      fillcolor="purple", opacity=0.5)
    
    for zone in b_liq_S:
        fig.add_shape(type="line",
                      x0=zone['bx'][0], x1=zone['bx'][2], y0=zone['bx'][3], y1=zone['bx'][3],
                      line=dict(color="black", width=2),
                      fillcolor="black", opacity=0.5)

def identify_candlestick_patterns(df, n):
    # Inizializzare una colonna per i pattern
        df['pattern'] = 0
        start_idx = max(0, len(df) - n)

        bullish_patterns = {
            'hammer': talib.CDLHAMMER(df['open'], df['high'], df['low'], df['close']),
            'inverse_hammer': talib.CDLINVERTEDHAMMER(df['open'], df['high'], df['low'], df['close']),
            'bullish_engulfing': talib.CDLENGULFING(df['open'], df['high'], df['low'], df['close']),
            'morning_star': talib.CDLMORNINGSTAR(df['open'], df['high'], df['low'], df['close']),
            'three_white_soldiers': talib.CDL3WHITESOLDIERS(df['open'], df['high'], df['low'], df['close'])
        }

        bearish_patterns = {
            'hanging_man': talib.CDLHANGINGMAN(df['open'], df['high'], df['low'], df['close']),
            'shooting_star': talib.CDLSHOOTINGSTAR(df['open'], df['high'], df['low'], df['close']),
            'bearish_engulfing': talib.CDLENGULFING(df['open'], df['high'], df['low'], df['close']),
            'evening_star': talib.CDLEVENINGSTAR(df['open'], df['high'], df['low'], df['close']),
            'dark_cloud_cover': talib.CDLDARKCLOUDCOVER(df['open'], df['high'], df['low'], df['close']),
            'three_black_crows': talib.CDL3BLACKCROWS(df['open'], df['high'], df['low'], df['close'])
        }

        continuation_patterns = {
            'doji': talib.CDLDOJI(df['open'], df['high'], df['low'], df['close']),
            'spinning_top': talib.CDLSPINNINGTOP(df['open'], df['high'], df['low'], df['close']),
            'rising_three_methods': talib.CDLRISEFALL3METHODS(df['open'], df['high'], df['low'], df['close'])
        }

        for pattern, series in bullish_patterns.items():
            df.loc[start_idx:, 'pattern'] = df.loc[start_idx:, 'pattern'].where(series[start_idx:] == 0, 1)

        for pattern, series in bearish_patterns.items():
            df.loc[start_idx:, 'pattern'] = df.loc[start_idx:, 'pattern'].where(series[start_idx:] == 0, 2)

        for pattern, series in continuation_patterns.items():
            df.loc[start_idx:, 'pattern'] = df.loc[start_idx:, 'pattern'].where(series[start_idx:] == 0, 0)

        return df

def add_pattern_signals_to_chart(fig, df, start, end):
    #CON LINEE
    # for i in range(start, end):
    #     if df['pattern'][i] == 1:
    #         fig.add_shape(type='line',
    #                       x0=i, y0=df['low'][i] - (df['high'][i] - df['low'][i]) * 0.1,
    #                       x1=i, y1=df['low'][i],
    #                       line=dict(color='Green', width=2),
    #                       name='Bullish Signal')
    #     elif df['pattern'][i] == 2:
    #         fig.add_shape(type='line',
    #                       x0=i, y0=df['high'][i] + (df['high'][i] - df['low'][i]) * 0.1,
    #                       x1=i, y1=df['high'][i],
    #                       line=dict(color='Red', width=2),
    #                       name='Bearish Signal')
    #     elif df['pattern'][i] == 0:
    #         fig.add_shape(type='line',
    #                       x0=i, y0=df['close'][i],
    #                       x1=i, y1=df['close'][i],
    #                       line=dict(color='Blue', width=2),
    #                       name='Continuation Signal')

    #CON LINEE VERTICALI
    for i in range(start, end):
        if df['pattern'].iloc[i] == 1:  # Bullish pattern
            fig.add_shape(
                type='line',
                x0=df.index[i], x1=df.index[i],
                y0=df['low'].min(), y1=df['high'].max(),
                line=dict(color="Green", width=2, dash="dash")
            )
        elif df['pattern'].iloc[i] == 2:  # Bearish pattern
            fig.add_shape(
                type='line',
                x0=df.index[i], x1=df.index[i],
                y0=df['low'].min(), y1=df['high'].max(),
                line=dict(color="Red", width=2, dash="dash")
            )
        elif df['pattern'].iloc[i] == 0:  # Continuation pattern
            pass



def plot_data(plotlist1, plotlist2, allFVG, orderBlock, df, b_liq_B, b_liq_S):
    # s = 0
    # e = 200
    # dfpl = df[s : e]
    # fig = go.Figure(data=[go.Candlestick(x=dfpl.index,
    #                                     open=dfpl['open'],
    #                                     high=dfpl['high'],
    #                                     low=dfpl['low'],
    #                                     close=dfpl['close'])])

    # c=0
    # while (1):
    #     if(c>len(sr)-1):#or sr[c][0]>e
    #         break
    #     fig.add_shape(type='line', x0=s, y0=sr[c][1],
    #                 x1=e,
    #                 y1=sr[c][1]
    #                 )#x0=sr[c][0]-5 x1=sr[c][0]+5
    #     c+=1
    
    # st.plotly_chart(fig)
    s = 20000
    e = len(df)-3
    dfpl = df[s : e]

    fig = go.Figure(data=[go.Candlestick(x=dfpl.index,
                                        open=dfpl['open'],
                                        high=dfpl['high'],
                                        low=dfpl['low'],
                                        close=dfpl['close'])])
    


    c=len(plotlist1)-10 #Number show
    while (1):
        if(c>len(plotlist1)-1):#or sr[c][0]>e
            break
        fig.add_shape(type='line', x0=plotlist1[c][0], y0=plotlist1[c][1],
                    x1=e,
                    y1=plotlist1[c][1],
                    line=dict(color="MediumPurple", width=3)
                    )#x0=sr[c][0]-5 x1=sr[c][0]+5
        c+=1
    c=len(plotlist2)-10 #Number show
    while (1):
        if(c>len(plotlist2)-1):#or sr[c][0]>e
            break
        fig.add_shape(type='line', x0=plotlist2[c][0], y0=plotlist2[c][1],
                    x1=e,
                    y1=plotlist2[c][1],
                    line=dict(color="RoyalBlue", width=3)
                    )#x0=sr[c][0]-5 x1=sr[c][0]+5
        c+=1
    
    for i in range(0, len(allFVG)):
        if(allFVG[i][3] == 1): #GREEN
            fig.add_shape(type="rect", 
                        x0=allFVG[i][0] - 1, x1=allFVG[i][0] + 1, y0= allFVG[i][1], y1= allFVG[i][2],
                        line=dict(color="Green", width=2),
                        fillcolor="green")
        if(allFVG[i][3] == 2): #RED
            fig.add_shape(type="rect", 
                        x0=allFVG[i][0] - 1, x1=allFVG[i][0] + 1, y0= allFVG[i][1], y1= allFVG[i][2],
                        line=dict(color="red", width=2),
                        fillcolor="red")
            
    for i in range(len(orderBlock)-20, len(orderBlock)):
        if(orderBlock[i][2] == 1):
            fig.add_shape(type='line', x0=orderBlock[i][0], y0=orderBlock[i][1],
                    x1=e,
                    y1=orderBlock[i][1],
                    line=dict(color="yellow", width=1))
        if(orderBlock[i][2] == 2):
            fig.add_shape(type='line', x0=orderBlock[i][0], y0=orderBlock[i][1],
                    x1=e,
                    y1=orderBlock[i][1],
                    line=dict(color="pink", width=1))
    
    add_liquidity_zones(fig, b_liq_B, b_liq_S)
    ema200(fig, dfpl)
    ema50(fig, dfpl)

# Mostra il grafico
    fig.update_layout(title='Buyside and Sellside Liquidity Zones')

    add_pattern_signals_to_chart(fig, dfpl, 0, len(dfpl))
    st.plotly_chart(fig)

def ema200(fig, df, period=200):
    df['EMA'] = talib.EMA(df['close'], timeperiod=period)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA'], mode='lines', name=f'EMA {period}', line=dict(color='magenta', width=2)))

def ema50(fig, df, period=50):
    df['EMA50'] = talib.EMA(df['close'], timeperiod=50)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], mode='lines', name=f'EMA {period}', line=dict(color='red', width=2)))




def main():
    ss = []
    rr = []
    fvg = []
    ob = []
    n1 = 4 #Candles before same color
    n2 = 3 #Candles after same color

    for row in range(20000+n1, len(df4h)-n2):
        if support(df4h, row, n1, n2):
            if(df4h.close[row] < df4h.open[row]):
                ss.append((row, df4h.open[row], 1))
            else:
                ss.append((row, df4h.close[row], 1))
        if resistance(df4h, row, n1, n2):
            if(df4h.close[row] > df4h.open[row]):
                rr.append((row, df4h.close[row], 2))
            else:
                rr.append((row, df4h.open[row], 2))
    
    for row in range(20000, len(df)-1):
        if not FVG(df, row) == 0:
            fvg.append(FVG(df, row))

    for row in range(20000, len(df)-1):
        if OrderBlocks(df, row) == 1:
            ob.append((row, df.close[row], 1))
        if OrderBlocks(df, row) == 2:
            ob.append((row, df.open[row], 2))
    st.title("Gold Resistance and support lines")
    st.subheader("Graph:")
    st.subheader("Legenda")
    st.write("Resistenze: \n Supporti: \n OrderBlock+: Linea gialla \n OrderBlock-: Linea rosa \n FVG+: Area verde \n FVG-: Area rossa Buyside Liquidity: Area viola \n Sellside Liquidity: Area nera \n Candle Pattern+: Linea verticale verde\n Candle Pattern-: Linea verticale rossa")

    # plotlist1 = [x[1] for x in sr if x[2] == 1] #Support
    # plotlist2 = [x[1] for x in sr if x[2] == 2] #Resistance
    # plotlist1.sort()
    # plotlist2.sort()

    # for i in range(1, len(plotlist1)):
    #     if(i >= len(plotlist1)):
    #         break
    #     if(abs(plotlist1[i]-plotlist1[i-1]) <= 0.005):
    #         plotlist1.pop(i)
    
    # for i in range(1, len(plotlist2)):
    #     if(i >= len(plotlist2)):
    #         break
    #     if(abs(plotlist2[i] - plotlist2[i-1]) <= 0.005):
    #         plotlist2.pop(i)
    
    
    liq_len = 7
    liq_mar = 10 / 6.9
    atr_period = 10
    b_liq_B, b_liq_S = detect_liquidity_zones(df, liq_len, liq_mar, atr_period)

    print(ss, rr)
    print(fvg)
    print(ob)
    dfp = identify_candlestick_patterns(df, 20)
    st.write(df)
    plot_data(rr, ss, fvg, ob, dfp, b_liq_B, b_liq_S)
    

    mt5.shutdown()

if __name__ == "__main__":
    main()