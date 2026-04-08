"""
ChrystalBall Strategy — uses GetValueAt() future data from C# wrapper.
No NCD files needed — C# reads future Open prices directly from NT's bar series.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nt_api import NtStrategy


class ChrystalBall(NtStrategy):
    """Crystal Ball strategy — C# delivers future extrema, Python decides."""

    PARAMETERS = {
        'tf_seconds': {'type': 'int', 'default': 3600, 'display': 'Time Window (sec)', 'group': 'ChrystalBall'},
        'lot_size': {'type': 'int', 'default': 1, 'display': 'Position Size', 'group': 'ChrystalBall'},
        'min_profit_ticks': {'type': 'int', 'default': 4, 'display': 'Min Profit (Ticks)', 'group': 'ChrystalBall'},
        'tf_exact': {'type': 'bool', 'default': False, 'display': 'Exact Exit Time', 'group': 'ChrystalBall'},
        'target_pct': {'type': 'int', 'default': 100, 'display': 'Target % of Extrema', 'group': 'ChrystalBall'},
    }

    def __init__(self):
        super().__init__()
        self._state = 0
        self._is_long = False
        self._target_price = 0.0
        self._target_bar = 0
        self._entry_price = 0.0
        self._signal_name = ""
        self._trade_count = 0
        self._total_profit = 0.0

    def on_bar_update(self):
        bar = self._bar_data
        tick_size = bar.get('tick_size', 0.25)
        close = bar.get('close', 0)
        current_bar = bar.get('current_bar', 0)

        # Future extrema from C# GetValueAt()
        max_open = bar.get('max_future_open', 0)
        max_bar = bar.get('max_future_bar', 0)
        min_open = bar.get('min_future_open', 0)
        min_bar = bar.get('min_future_bar', 0)

        # Fill price = next bar's open (OnBarClose mode)
        # C# scans Open[CurrentBar+1..CurrentBar+N]
        # Entry fill will be at Open of next bar after signal

        pct = self.target_pct / 100.0
        min_profit = self.min_profit_ticks * tick_size

        if self._state == 0:
            # IDLE — decide based on future extrema
            long_profit = max_open - close
            short_profit = close - min_open

            if long_profit >= min_profit and long_profit >= short_profit:
                self._is_long = True
                self._target_price = close + long_profit * pct
                self._target_bar = max_bar
                self._entry_price = close
                self._trade_count += 1
                self._signal_name = f"CB_{self._trade_count}"
                self.enter_long(self.lot_size, self._signal_name)
                self._state = 1
            elif short_profit >= min_profit:
                self._is_long = False
                self._target_price = close - short_profit * pct
                self._target_bar = min_bar
                self._entry_price = close
                self._trade_count += 1
                self._signal_name = f"CB_{self._trade_count}"
                self.enter_short(self.lot_size, self._signal_name)
                self._state = 1

        elif self._state == 1:
            reached = (close >= self._target_price) if self._is_long else (close <= self._target_price)

            # TfExact=False: check if price goes further
            if not self.tf_exact and reached and current_bar < self._target_bar:
                if self._is_long and max_open > self._target_price + min_profit:
                    self._target_price = close + (max_open - close) * pct
                    self._target_bar = max_bar
                    return
                elif not self._is_long and min_open < self._target_price - min_profit:
                    self._target_price = close - (close - min_open) * pct
                    self._target_bar = min_bar
                    return

            time_expired = current_bar >= self._target_bar

            if reached or time_expired:
                point_value = 20.0
                if self._is_long:
                    pnl_pts = close - self._entry_price
                    self.exit_long(self._signal_name)
                else:
                    pnl_pts = self._entry_price - close
                    self.exit_short(self._signal_name)

                pnl_usd = pnl_pts * point_value * self.lot_size
                self._total_profit += pnl_usd
                direction = "L" if self._is_long else "S"
                self.print(f"[CB] #{self._trade_count} {direction} "
                           f"${pnl_usd:+,.0f} total=${self._total_profit:+,.0f}")
                self._state = 0
