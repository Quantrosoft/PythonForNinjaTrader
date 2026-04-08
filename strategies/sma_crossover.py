"""
SMA Crossover Strategy — enters long/short on simple moving average crossover.

Uses self._bar_data for close prices and maintains its own SMA buffers,
so it works both with and without a live C# _api connection.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nt_api import NtStrategy


class SmaCrossover(NtStrategy):
    """Go long when fast SMA crosses above slow SMA, short when it crosses below."""

    PARAMETERS = {
        'fast_period': {'type': 'int', 'default': 10, 'display': 'Fast Period', 'group': 'SmaCrossover'},
        'slow_period': {'type': 'int', 'default': 20, 'display': 'Slow Period', 'group': 'SmaCrossover'},
        'lot_size':    {'type': 'int', 'default': 1,  'display': 'Position Size', 'group': 'SmaCrossover'},
    }

    def __init__(self):
        super().__init__()
        # Rolling buffer of close prices for SMA calculation
        self._closes = []
        # Previous SMA values for cross detection
        self._prev_fast_sma = None
        self._prev_slow_sma = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_sma(values, period):
        """Compute SMA over the last `period` values. Returns None if not enough data."""
        if len(values) < period:
            return None
        return sum(values[-period:]) / period

    # ------------------------------------------------------------------
    # Main logic
    # ------------------------------------------------------------------

    def on_bar_update(self):
        # Append latest close to the rolling buffer
        close = self._bar_data.get('close', 0.0) if not self._api else float(self.close[0])
        self._closes.append(close)

        # Need at least slow_period + 1 bars to detect a crossover
        if len(self._closes) < self.slow_period + 1:
            return

        fast_sma = self._calc_sma(self._closes, self.fast_period)
        slow_sma = self._calc_sma(self._closes, self.slow_period)

        if fast_sma is None or slow_sma is None:
            return

        # Cross detection: compare current relationship to previous
        if self._prev_fast_sma is not None and self._prev_slow_sma is not None:
            prev_above = self._prev_fast_sma > self._prev_slow_sma
            curr_above = fast_sma > slow_sma

            # Fast crossed above slow -> go long
            if curr_above and not prev_above:
                self.enter_long(self.lot_size, "SmaLong")

            # Fast crossed below slow -> go short
            elif not curr_above and prev_above:
                self.enter_short(self.lot_size, "SmaShort")

        # Store for next bar
        self._prev_fast_sma = fast_sma
        self._prev_slow_sma = slow_sma
