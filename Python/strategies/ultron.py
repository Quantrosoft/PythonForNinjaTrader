"""
Ultron Strategy — 1:1 port of the original ForexFactory Ultron EA for GBPUSD H1.

Original thread: https://www.forexfactory.com/thread/840339-my-ultron-ea-for-gbpusd-h1-timeframe
Video tutorial:  https://youtu.be/y1Vs7AiYlpQ

Uses 4 Moving Averages to detect trend continuation setups:
  MA1 = WMA(Open, 9)   — weighted MA on open prices
  MA2 = WMA(Close, 9)  — weighted MA on close prices
  MA3 = SMA(Close, 50) — slow simple MA (trend direction)
  MA4 = SMA(Close, 1)  — essentially the close price (range filter)

Hardcoded thresholds from original:
  ma3ma4 < 0.0048, ma1ma2 between 0.0004 and 0.0013
  TP = 68 pips, SL = 55 pips
  Trading hours: 4:00-21:00 GMT (London + NY session)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nt_api import NtStrategy


class Ultron(NtStrategy):
    """Ultron — original ForexFactory 4-MA strategy, 1:1 port."""

    PARAMETERS = {
        'lot_size':        {'type': 'int',    'default': 1,      'display': 'Position Size',        'group': 'Ultron'},
        'take_profit_pips': {'type': 'double', 'default': 68.0,  'display': 'Take Profit (pips)',    'group': 'Ultron'},
        'stop_loss_pips':  {'type': 'double', 'default': 55.0,   'display': 'Stop Loss (pips)',      'group': 'Ultron'},
        'hour_start':      {'type': 'int',    'default': 4,      'display': 'GMT Start Hour',        'group': 'Ultron'},
        'hour_end':        {'type': 'int',    'default': 21,     'display': 'GMT End Hour',          'group': 'Ultron'},
    }

    # Original hardcoded thresholds — DO NOT CHANGE
    MA3MA4_MAX = 0.0048
    MA1MA2_MIN = 0.0004
    MA1MA2_MAX = 0.0013

    def __init__(self):
        super().__init__()
        self._state = 0  # 0=IDLE, 1=TRADING
        self._is_long = False
        self._entry_price = 0.0
        self._trade_count = 0
        self._total_profit = 0.0
        self._signal_name = ""

        # Price buffers for MA calculation
        self._closes = []
        self._opens = []

    def _wma(self, data, period):
        """Weighted Moving Average — identical to cTrader/MT4 WMA."""
        if len(data) < period:
            return 0.0
        values = data[-period:]
        weight_sum = period * (period + 1) / 2
        return sum(v * (i + 1) for i, v in enumerate(values)) / weight_sum

    def _sma(self, data, period):
        """Simple Moving Average."""
        if len(data) < period:
            return 0.0
        return sum(data[-period:]) / period

    def on_bar_update(self):
        bar = self._bar_data
        close = bar.get('close', 0)
        opn = bar.get('open', 0)
        tick_size = bar.get('tick_size', 0.0001)
        point_value = bar.get('point_value', 1.0)

        # Build price history
        self._closes.append(close)
        self._opens.append(opn)

        # Need enough bars for SMA(50) + 2 lookback bars
        if len(self._closes) < 53:
            return

        # --- Calculate 4 MAs (original periods hardcoded) ---
        ma1 = self._wma(self._opens, 9)    # WMA on Open prices, period 9
        ma2 = self._wma(self._closes, 9)   # WMA on Close prices, period 9
        ma3 = self._sma(self._closes, 50)  # SMA on Close prices, period 50
        ma4 = self._sma(self._closes, 1)   # SMA period 1 = close price

        # --- MA differences (original variable names) ---
        ma1ma2 = ma1 - ma2
        ma2ma1 = ma2 - ma1
        ma3ma4 = ma3 - ma4
        ma4ma3 = ma4 - ma3

        # --- Previous bar values ---
        close1 = self._closes[-2]  # Bars.ClosePrices.Last(1)
        close2 = self._closes[-3]  # Bars.ClosePrices.Last(2)
        open2 = self._opens[-3]    # Bars.OpenPrices.Last(2)

        # --- Trading hours (GMT) ---
        time_str = bar.get('time', '')
        in_hours = True
        if time_str:
            try:
                hour = int(time_str[11:13])
                in_hours = self.hour_start <= hour <= self.hour_end
            except (ValueError, IndexError):
                pass

        # --- TP/SL distances ---
        # Original uses pips (1 pip = 10 ticks for forex, or Symbol.PipSize)
        # For futures like 6B: 1 pip = 0.0001, tick_size = 0.0001
        pip_size = tick_size  # for 6B futures, pip = tick
        tp_distance = self.take_profit_pips * pip_size
        sl_distance = self.stop_loss_pips * pip_size

        if self._state == 0 and in_hours:
            # === SELL (original lines 137-158) ===
            if (ma3ma4 < self.MA3MA4_MAX
                    and ma3 > ma1
                    and ma3 > ma2
                    and close1 < close2
                    and close2 < open2
                    and ma1ma2 < self.MA1MA2_MAX
                    and ma1ma2 > self.MA1MA2_MIN):

                self._trade_count += 1
                self._signal_name = f"UL_{self._trade_count}"
                self._is_long = False
                self._entry_price = close
                self.enter_short(self.lot_size, self._signal_name)
                self._state = 1

            # === BUY (original lines 161-182) ===
            elif (ma4ma3 < self.MA3MA4_MAX
                    and ma3 < ma1
                    and ma3 < ma2
                    and close1 > close2
                    and close2 > open2
                    and ma2ma1 < self.MA1MA2_MAX
                    and ma2ma1 > self.MA1MA2_MIN):

                self._trade_count += 1
                self._signal_name = f"UL_{self._trade_count}"
                self._is_long = True
                self._entry_price = close
                self.enter_long(self.lot_size, self._signal_name)
                self._state = 1

        elif self._state == 1:
            # === EXIT CHECK (TP / SL) ===
            if self._is_long:
                pnl = close - self._entry_price
            else:
                pnl = self._entry_price - close

            hit_tp = pnl >= tp_distance
            hit_sl = pnl <= -sl_distance

            if hit_tp or hit_sl:
                pnl_usd = pnl / tick_size * point_value * self.lot_size
                self._total_profit += pnl_usd

                direction = "L" if self._is_long else "S"
                result = "TP" if hit_tp else "SL"
                self.print(f"[UL] #{self._trade_count} {direction} {result} "
                           f"${pnl_usd:+,.0f} total=${self._total_profit:+,.0f}")

                if self._is_long:
                    self.exit_long(self._signal_name)
                else:
                    self.exit_short(self._signal_name)

                self._state = 0
