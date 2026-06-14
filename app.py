import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math

from backtester import run_backtest

st.set_page_config(layout="wide", page_title="Algorithmic Trading Dashboard", page_icon="📈")

# -- Dashboard Header --
st.title("📈 Spot Gold Bearish FVG Strategy Dashboard")
st.markdown("Analyzing 1H Timeframe using dynamic Stop Loss management and RSI/SMA filters.")

# Sidebar settings
st.sidebar.header("Settings")
symbol = st.sidebar.text_input("Symbol (TradingView Live Feed)", "XAUUSD")
period = st.sidebar.selectbox("Period", ["100d", "200d", "300d", "400d"], index=2)
# Fixed position size as strictly 0.01 lots
position_size = 0.01
st.sidebar.markdown(f"**Position Size:** {position_size} (Fixed)")
initial_capital = st.sidebar.number_input("Initial Capital ($)", value=1000.0, step=100.0)
run_btn = st.sidebar.button("Run Backtest")

if 'df' not in st.session_state:
    st.session_state.df = None
    st.session_state.trades = None
    st.session_state.fvgs = None

if run_btn or st.session_state.df is None:
    with st.spinner("Fetching Live OANDA:XAUUSD Data from TradingView and running backtester..."):
        try:
            df, trades, fvg_log = run_backtest(symbol=symbol, interval=period, period=period)
            st.session_state.df = df
            st.session_state.trades = trades
            st.session_state.fvgs = fvg_log
        except Exception as e:
            st.error(f"Error establishing feed: {e}")

df = st.session_state.df
trades = st.session_state.trades

if df is not None and trades is not None:
    st.markdown("---")
    
    # -- Calculate Metrics --
    total_trades = len(trades)
    
    if total_trades > 0:
        win_trades = trades[trades['pnl'] > 0]
        win_rate = (len(win_trades) / total_trades) * 100
        
        trades['cum_pnl'] = trades['pnl'].cumsum()
        trades['equity'] = initial_capital + trades['cum_pnl']
        trades['peak_equity'] = trades['equity'].cummax()
        trades['drawdown'] = trades['peak_equity'] - trades['equity']
        max_drawdown = trades['drawdown'].max()
        
        total_pnl = trades['pnl'].sum()
        final_equity = initial_capital + total_pnl
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Trades", total_trades)
        col2.metric("Win Rate", f"{win_rate:.1f}%")
        col3.metric("Total PnL", f"${total_pnl:.2f}")
        col4.metric("Max Drawdown", f"${max_drawdown:.2f}")
        col5.metric("Final Equity", f"${final_equity:.2f}")
        
    else:
        st.warning("No trades were executed during this period with the current strategy parameters.")
    
    st.markdown("---")
    
    # -- Visualization --
    st.subheader("Price Action, Indicators & Executions")
    
    # We will slice data to the last N bars for better visibility if checked, 
    # but Plotly handles zoom natively really well.
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=('OHLCV & Strategy', 'RSI-14'),
                        row_width=[0.3, 0.7])

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price'
    ), row=1, col=1)

    # SMAs
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_9'], line=dict(color='orange', width=1), name='SMA 9'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='blue', width=1), name='SMA 20'), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name='RSI 14', line=dict(color='purple', width=1.5)), row=2, col=1)
    
    # RSI High/Low Lines
    fig.add_hline(y=70, line_dash="dash", line_color="gray", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="gray", row=2, col=1)

    # Plot Trades
    if total_trades > 0:
        # Entry points (Short -> Red triangle down)
        fig.add_trace(go.Scatter(
            x=trades['entry_time'],
            y=trades['entry_price'] + (df['High'].mean() * 0.001), # slightly above
            mode='markers',
            marker=dict(symbol='triangle-down', size=10, color='red'),
            name='Short Entry'
        ), row=1, col=1)
        
        # Exit points
        profits = trades[trades['pnl'] > 0]
        losses = trades[trades['pnl'] <= 0]
        
        # Profitable Exits (Green check or dot)
        if not profits.empty:
            fig.add_trace(go.Scatter(
                x=profits['exit_time'],
                y=profits['exit_price'],
                mode='markers',
                marker=dict(symbol='circle', size=8, color='green', line=dict(color='black', width=1)),
                name='TP / Profit Exit'
            ), row=1, col=1)
            
        # Losing Exits (Red dot)
        if not losses.empty:
            fig.add_trace(go.Scatter(
                x=losses['exit_time'],
                y=losses['exit_price'],
                mode='markers',
                marker=dict(symbol='x', size=8, color='red', line=dict(color='black', width=1)),
                name='SL Exit'
            ), row=1, col=1)

        # Plot ALL FVGs from the log
        if st.session_state.fvgs:
            for fvg in st.session_state.fvgs:
                # Default style for UNUSED (Unmitigated) FVGs
                color = "rgba(0, 255, 0, 0.1)" if fvg['type'] == 'bullish' else "rgba(255, 0, 0, 0.1)"
                line_color = "rgba(0, 255, 0, 0.2)" if fvg['type'] == 'bullish' else "rgba(255, 0, 0, 0.2)"
                dash_style = "dot"
                line_width = 1
                
                # Highlight style for TRADED FVGs
                if fvg.get('traded', False):
                    color = "rgba(0, 255, 0, 0.25)" if fvg['type'] == 'bullish' else "rgba(255, 0, 0, 0.25)"
                    line_color = "rgba(0, 200, 0, 0.8)" if fvg['type'] == 'bullish' else "rgba(200, 0, 0, 0.8)"
                    dash_style = "solid"
                    line_width = 2
                    
                fig.add_shape(
                    type="rect",
                    x0=fvg['start_time'], 
                    y0=fvg['bottom'],
                    x1=fvg['end_time'],
                    y1=fvg['top'],
                    fillcolor=color,
                    line=dict(color=line_color, width=line_width, dash=dash_style),
                    layer="below",
                    row=1, col=1
                )

    fig.update_layout(height=800, margin=dict(l=0, r=0, t=30, b=0), template='plotly_dark')
    fig.update_xaxes(rangeslider_visible=False)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # -- Trade Log --
    st.subheader("Trade Log")
    if total_trades > 0:
        display_cols = ['entry_time', 'exit_time', 'direction', 'entry_price', 'exit_price', 'exit_reason', 'pnl']
        st.dataframe(trades[display_cols].sort_values(by='entry_time', ascending=False), use_container_width=True)
