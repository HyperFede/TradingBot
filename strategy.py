from math import floor

class Position:
    def __init__(self, entry_price, entry_time, entry_rsi, direction, tp=None, sl=None):
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.entry_rsi = entry_rsi
        self.direction = direction  # 'LONG' or 'SHORT'
        self.tp = tp
        self.sl = sl

class FVGStrategy:
    def __init__(self, position_size=0.01):
        self.open_bear_fvgs = []  # List of unmitigated Bearish FVGs
        self.open_bull_fvgs = []  # List of unmitigated Bullish FVGs
        self.all_fvg_log = []     # Log of all formed FVGs for plotting
        
        self.position = None
        self.position_size = position_size

    def evaluate_bar(self, row):
        """
        Evaluate a single bar/row for strategy logic.
        Returns newly generated trade(s) if any closed during this bar.
        """
        closed_trades = []
        high = row['High']
        low = row['Low']
        close = row['Close']
        
        # 1. Update Invalidation states for existing FVGs map
        # Bearish: Invalidated if High >= FVG Top
        for f in self.open_bear_fvgs[:]:
            if high >= f['top']:
                f['end_time'] = row.name
                self.open_bear_fvgs.remove(f)
                
        # Bullish: Invalidated if Low <= FVG Bottom
        for f in self.open_bull_fvgs[:]:
            if low <= f['bottom']:
                f['end_time'] = row.name
                self.open_bull_fvgs.remove(f)

        # 2. Add New FVGs to Maps
        if row.get('is_bearish_fvg', False):
            fvg = {
                'type': 'bearish',
                'top': row['bear_fvg_top'],
                'bottom': row['bear_fvg_bottom'],
                'size': row['bear_fvg_size'],
                'start_time': row.name,
                'end_time': None,
                'traded': False
            }
            self.open_bear_fvgs.append(fvg)
            self.all_fvg_log.append(fvg)
            
        if row.get('is_bullish_fvg', False):
            fvg = {
                'type': 'bullish',
                'top': row['bull_fvg_top'],
                'bottom': row['bull_fvg_bottom'],
                'size': row['bull_fvg_size'],
                'start_time': row.name,
                'end_time': None,
                'traded': False
            }
            self.open_bull_fvgs.append(fvg)
            self.all_fvg_log.append(fvg)

        # 3. Manage Active Position
        if self.position is not None:
            trade_closed = False
            exit_price = None
            exit_reason = None
            
            # 3.1 Force close on Friday before market close (e.g. 20:00 / 8 PM)
            friday_close = (row.name.weekday() == 4 and row.name.hour >= 20)
            
            # Check TP/SL Hits
            if self.position.direction == 'SHORT':
                sl_hit = self.position.sl is not None and high >= self.position.sl
                tp_hit = self.position.tp is not None and low <= self.position.tp
                # Determine exits
                if friday_close:
                    exit_price = close
                    exit_reason = 'Friday Close'
                    trade_closed = True
                elif sl_hit and tp_hit:
                    # Worst case assignment
                    exit_price = self.position.sl
                    exit_reason = 'SL'
                    trade_closed = True
                elif sl_hit:
                    exit_price = self.position.sl
                    exit_reason = 'SL'
                    trade_closed = True
                elif tp_hit:
                    exit_price = self.position.tp
                    exit_reason = 'TP'
                    trade_closed = True
                    
            elif self.position.direction == 'LONG':
                sl_hit = self.position.sl is not None and low <= self.position.sl
                tp_hit = self.position.tp is not None and high >= self.position.tp
                # Determine exits
                if friday_close:
                    exit_price = close
                    exit_reason = 'Friday Close'
                    trade_closed = True
                elif sl_hit and tp_hit:
                    exit_price = self.position.sl
                    exit_reason = 'SL'
                    trade_closed = True
                elif sl_hit:
                    exit_price = self.position.sl
                    exit_reason = 'SL'
                    trade_closed = True
                elif tp_hit:
                    exit_price = self.position.tp
                    exit_reason = 'TP'
                    trade_closed = True
                
            # Log Closed Trade
            if trade_closed:
                if self.position.direction == 'SHORT':
                    pnl = (self.position.entry_price - exit_price) * self.position_size
                else:
                    pnl = (exit_price - self.position.entry_price) * self.position_size
                    
                closed_trades.append({
                    'direction': self.position.direction,
                    'entry_time': self.position.entry_time,
                    'entry_price': self.position.entry_price,
                    'exit_time': row.name,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'pnl': pnl
                })
                self.position = None
            else:
                # --- Dynamic SL Management ---
                sma_slopes_down = (row.get('SMA_9_slope', 0) < 0) and (row.get('SMA_20_slope', 0) < 0)
                sma_slopes_up = (row.get('SMA_9_slope', 0) > 0) and (row.get('SMA_20_slope', 0) > 0)
                
                if self.position.direction == 'SHORT':
                    # Has price broken below the active Bearish FVG?
                    # The FVG associated to this short was tracked, but we must use the most recent Unmitigated
                    latest_bear = self.open_bear_fvgs[-1] if self.open_bear_fvgs else None
                    if latest_bear and close < latest_bear['bottom']:
                        if close < self.position.entry_price and row.get('RSI_14', 50) < self.position.entry_rsi and sma_slopes_down:
                            new_sl = latest_bear['bottom'] + (0.35 * latest_bear['size'])
                            if self.position.sl is None or new_sl < self.position.sl:
                                self.position.sl = new_sl
                                
                elif self.position.direction == 'LONG':
                    # Has price broken above the active Bullish FVG?
                    latest_bull = self.open_bull_fvgs[-1] if self.open_bull_fvgs else None
                    if latest_bull and close > latest_bull['top']:
                        if close > self.position.entry_price and row.get('RSI_14', 50) > self.position.entry_rsi and sma_slopes_up:
                            new_sl = latest_bull['top'] - (0.35 * latest_bull['size'])
                            if self.position.sl is None or new_sl > self.position.sl:
                                self.position.sl = new_sl

        # 4. Check for Entries (if not in position)
        if self.position is None:
            # Check Short Entry
            if len(self.open_bear_fvgs) > 0 and len(self.open_bull_fvgs) > 0:
                latest_bear = self.open_bear_fvgs[-1]
                entry_level_short = latest_bear['bottom'] + (0.25 * latest_bear['size'])
                
                if high >= entry_level_short and low <= entry_level_short:
                    # Find highest unmitigated Bullish FVG below entry
                    lower_bulls = [f['top'] for f in self.open_bull_fvgs if f['top'] < entry_level_short]
                    if lower_bulls: # Only trigger if an opposing valid TP exists
                        tp_level = max(lower_bulls)
                        self.position = Position(
                            entry_price=entry_level_short,
                            entry_time=row.name,
                            entry_rsi=row.get('RSI_14', 50),
                            direction='SHORT',
                            tp=tp_level
                        )
                        latest_bear['traded'] = True

            # Check Long Entry
            # We allow multiple entry conditionals per bar, it'll pick the first executed if both crossed
            if self.position is None and len(self.open_bull_fvgs) > 0 and len(self.open_bear_fvgs) > 0:
                latest_bull = self.open_bull_fvgs[-1]
                entry_level_long = latest_bull['top'] - (0.25 * latest_bull['size'])
                
                if low <= entry_level_long and high >= entry_level_long:
                    # Find lowest unmitigated Bearish FVG above entry
                    higher_bears = [f['bottom'] for f in self.open_bear_fvgs if f['bottom'] > entry_level_long]
                    if higher_bears: # Only trigger if an opposing valid TP exists
                        tp_level = min(higher_bears)
                        self.position = Position(
                            entry_price=entry_level_long,
                            entry_time=row.name,
                            entry_rsi=row.get('RSI_14', 50),
                            direction='LONG',
                            tp=tp_level
                        )
                        latest_bull['traded'] = True

        return closed_trades
