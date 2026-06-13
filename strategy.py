from math import floor

class Position:
    def __init__(self, entry_price, entry_time, entry_rsi, direction, case_reason, tp=None, sl=None):
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.entry_rsi = entry_rsi
        self.direction = direction  # 'LONG' or 'SHORT'
        self.case_reason = case_reason # 'Case 1' or 'Case 2'
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
        """
        closed_trades = []
        high = row['High']
        low = row['Low']
        close = row['Close']
        
        # 1. Update Invalidation states for existing FVGs map
        for f in self.open_bear_fvgs[:]:
            if high >= f['top']:
                f['end_time'] = row.name
                self.open_bear_fvgs.remove(f)
                
        for f in self.open_bull_fvgs[:]:
            if low <= f['bottom']:
                f['end_time'] = row.name
                self.open_bull_fvgs.remove(f)

        # Helper function for overlap rule
        def is_overlap(fvg1, fvg2):
            return max(fvg1['bottom'], fvg2['bottom']) <= min(fvg1['top'], fvg2['top'])

        # 2. Add New FVGs to Maps & Apply Overlap Rule
        if row.get('is_bearish_fvg', False):
            new_fvg = {
                'type': 'bearish',
                'top': row['bear_fvg_top'],
                'bottom': row['bear_fvg_bottom'],
                'size': row['bear_fvg_size'],
                'start_time': row.name,
                'end_time': None,
                'traded': False,
                'trade_case': None
            }
            # Overlap Rule: discard older FVG if it overlaps
            for old_fvg in self.open_bear_fvgs[:]:
                if is_overlap(new_fvg, old_fvg):
                    old_fvg['end_time'] = row.name
                    self.open_bear_fvgs.remove(old_fvg)
            
            self.open_bear_fvgs.append(new_fvg)
            if len(self.open_bear_fvgs) > 21:
                self.open_bear_fvgs.pop(0) # Keep max 21 (1 Current + 20 Historical)
            self.all_fvg_log.append(new_fvg)
            
        if row.get('is_bullish_fvg', False):
            new_fvg = {
                'type': 'bullish',
                'top': row['bull_fvg_top'],
                'bottom': row['bull_fvg_bottom'],
                'size': row['bull_fvg_size'],
                'start_time': row.name,
                'end_time': None,
                'traded': False,
                'trade_case': None
            }
            for old_fvg in self.open_bull_fvgs[:]:
                if is_overlap(new_fvg, old_fvg):
                    old_fvg['end_time'] = row.name
                    self.open_bull_fvgs.remove(old_fvg)
                    
            self.open_bull_fvgs.append(new_fvg)
            if len(self.open_bull_fvgs) > 21:
                self.open_bull_fvgs.pop(0)
            self.all_fvg_log.append(new_fvg)

        # 3. Manage Active Position
        if self.position is not None:
            trade_closed = False
            exit_price = None
            exit_reason = None
            
            friday_close = (row.name.weekday() == 4 and row.name.hour >= 20)
            
            if self.position.direction == 'SHORT':
                sl_hit = high >= self.position.sl
                tp_hit = low <= self.position.tp
                
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
                    
            elif self.position.direction == 'LONG':
                sl_hit = low <= self.position.sl
                tp_hit = high >= self.position.tp
                
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
                
            if trade_closed:
                if self.position.direction == 'SHORT':
                    pnl = (self.position.entry_price - exit_price) * self.position_size
                else:
                    pnl = (exit_price - self.position.entry_price) * self.position_size
                    
                closed_trades.append({
                    'direction': self.position.direction,
                    'case_reason': self.position.case_reason,
                    'entry_time': self.position.entry_time,
                    'entry_price': self.position.entry_price,
                    'exit_time': row.name,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'pnl': pnl
                })
                self.position = None

        # 4. Check for Entries (Strictly One Trade at a Time)
        if self.position is None:
            # Check Short Entries
            # Iterate backwards (most recent first)
            for idx, bear in enumerate(reversed(self.open_bear_fvgs)):
                # idx == 0 is the most recent (Case 1), others are Case 2
                is_case_1 = (idx == 0)
                
                # Condition: Price touches lower band of Bearish FVG
                if high >= bear['bottom']:
                    entry_price = bear['bottom']
                    sl = bear['top'] + 5
                    # Cap SL risk to $50
                    if sl - entry_price > 50:
                        sl = entry_price + 50
                    # TP at 2.0 RR
                    tp = entry_price - 2 * (sl - entry_price)
                    
                    self.position = Position(
                        entry_price=entry_price,
                        entry_time=row.name,
                        entry_rsi=row.get('RSI_14', 50),
                        direction='SHORT',
                        case_reason='Case 1' if is_case_1 else 'Case 2',
                        tp=tp,
                        sl=sl
                    )
                    bear['traded'] = True
                    bear['trade_case'] = self.position.case_reason
                    break # Position filled, stop searching

        if self.position is None:
            # Check Long Entries
            for idx, bull in enumerate(reversed(self.open_bull_fvgs)):
                is_case_1 = (idx == 0)
                
                # Condition: Price touches upper band of Bullish FVG
                if low <= bull['top']:
                    entry_price = bull['top']
                    sl = bull['bottom'] - 5
                    # Cap SL risk to $50
                    if entry_price - sl > 50:
                        sl = entry_price - 50
                    # TP at 2.0 RR
                    tp = entry_price + 2 * (entry_price - sl)
                    
                    self.position = Position(
                        entry_price=entry_price,
                        entry_time=row.name,
                        entry_rsi=row.get('RSI_14', 50),
                        direction='LONG',
                        case_reason='Case 1' if is_case_1 else 'Case 2',
                        tp=tp,
                        sl=sl
                    )
                    bull['traded'] = True
                    bull['trade_case'] = self.position.case_reason
                    break

        return closed_trades
