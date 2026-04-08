"""
NinjaTrader Python API - Base class for Python strategies.

Mirrors the NinjaTrader C# Strategy API with Python snake_case conventions.
All properties and methods proxy to the live C# Strategy instance via self._api.

Usage:
    from nt_api import NtStrategy

    class MyStrategy(NtStrategy):
        PARAMETERS = {
            'fast_period': {'type': 'int', 'default': 10, 'display': 'Fast Period'},
        }

        def on_bar_update(self):
            if self.current_bar < self.fast_period:
                return
            if self.close[0] > self.sma(self.fast_period)[0]:
                self.enter_long()
"""


class _BarDataAccessor:
    """Lightweight accessor for bar data pushed from C# as dict.
    Supports [0] indexing for current bar only."""
    def __init__(self, data, key):
        self._data = data
        self._key = key

    def __getitem__(self, index):
        if index == 0:
            return self._data.get(self._key, 0.0)
        return 0.0  # historical bars not available without _api


class NtStrategy:
    """Base class for NinjaTrader Python strategies.

    Override the lifecycle methods below. Access price data, indicators,
    and order methods through self.* properties.
    """

    # Marker so C# bridge can find NtStrategy subclasses
    _is_nt_strategy = True

    # Override in subclass: {'param_name': {'type': 'int', 'default': 10, ...}}
    PARAMETERS = {}

    def __init__(self):
        # Set by C# bridge — reference to the PythonStrategy C# instance
        self._api = None
        # Bar data pushed from C# each tick (fallback when _api not injected)
        self._bar_data = {}
        # Collected orders to send back to C#
        self._pending_orders = []
        # Collected prints to send back to C#
        self._pending_prints = []
        # Apply default parameter values
        for name, spec in self.PARAMETERS.items():
            if not hasattr(self, name):
                setattr(self, name, spec.get('default'))

    # ──────────────────────────────────────────────
    # Lifecycle methods (override these in subclass)
    # ──────────────────────────────────────────────

    def on_configure(self):
        """Called during State.Configure. Add data series here."""
        pass

    def on_data_loaded(self):
        """Called during State.DataLoaded. Initialize indicators here."""
        pass

    def on_historical(self):
        """Called when strategy enters historical processing mode."""
        pass

    def on_realtime(self):
        """Called when strategy switches to realtime mode."""
        pass

    def on_bar_update(self):
        """Called on each bar update. Main strategy logic goes here."""
        pass

    def on_market_data(self):
        """Called on each market data tick."""
        pass

    def on_execution_update(self, price, quantity, market_position, order_id, time):
        """Called when an execution occurs."""
        pass

    def on_order_update(self, limit_price, stop_price, order_state, quantity, avg_fill_price):
        """Called when an order state changes."""
        pass

    def on_position_update(self, avg_price, quantity, market_position):
        """Called when the position changes."""
        pass

    def on_stop(self):
        """Called when strategy is terminated. Cleanup here."""
        pass

    # ──────────────────────────────────────────────
    # Price Data (proxied to C# ISeries<double>)
    # ──────────────────────────────────────────────

    @property
    def close(self):
        """Close prices. close[0] = current bar."""
        if self._api:
            return self._api.Close
        return _BarDataAccessor(self._bar_data, 'close')

    @property
    def open(self):
        """Open prices."""
        if self._api:
            return self._api.Open
        return _BarDataAccessor(self._bar_data, 'open')

    @property
    def high(self):
        """High prices."""
        if self._api:
            return self._api.High
        return _BarDataAccessor(self._bar_data, 'high')

    @property
    def low(self):
        """Low prices."""
        if self._api:
            return self._api.Low
        return _BarDataAccessor(self._bar_data, 'low')

    @property
    def volume(self):
        """Volume data."""
        if self._api:
            return self._api.Volume
        return _BarDataAccessor(self._bar_data, 'volume')

    @property
    def time(self):
        """Bar timestamps."""
        if self._api:
            return self._api.Time
        return None

    # ──────────────────────────────────────────────
    # Strategy State Properties
    # ──────────────────────────────────────────────

    @property
    def current_bar(self):
        """Index of the current bar (0-based from oldest)."""
        if self._api:
            return int(self._api.CurrentBar)
        return self._bar_data.get('current_bar', 0)

    @property
    def bars_in_progress(self):
        """Which data series is currently updating (0 = primary)."""
        if self._api:
            return int(self._api.BarsInProgress)
        return 0

    @property
    def state(self):
        """Current strategy state."""
        return str(self._api.State)

    @property
    def position(self):
        """Current position object."""
        return self._api.Position

    @property
    def account(self):
        """Account information."""
        return self._api.Account

    @property
    def instrument(self):
        """Current trading instrument."""
        return self._api.Instrument

    # ──────────────────────────────────────────────
    # Order Methods
    # ──────────────────────────────────────────────

    def enter_long(self, quantity=1, signal_name="PythonLong"):
        """Submit a market order to go long."""
        if self._api:
            return self._api.EnterLong(quantity, signal_name)
        self._pending_orders.append(('enter_long', quantity, signal_name))

    def enter_short(self, quantity=1, signal_name="PythonShort"):
        """Submit a market order to go short."""
        if self._api:
            return self._api.EnterShort(quantity, signal_name)
        self._pending_orders.append(('enter_short', quantity, signal_name))

    def enter_long_limit(self, quantity, limit_price, signal_name="PythonLongLimit"):
        """Submit a limit order to go long."""
        return self._api.EnterLongLimit(0, True, quantity, limit_price, signal_name)

    def enter_short_limit(self, quantity, limit_price, signal_name="PythonShortLimit"):
        """Submit a limit order to go short."""
        return self._api.EnterShortLimit(0, True, quantity, limit_price, signal_name)

    def exit_long(self, signal_name="PythonExitLong", from_entry_signal=""):
        """Exit a long position at market."""
        if self._api:
            return self._api.ExitLong(signal_name, from_entry_signal)
        self._pending_orders.append(('exit_long', 0, signal_name))

    def exit_short(self, signal_name="PythonExitShort", from_entry_signal=""):
        """Exit a short position at market."""
        if self._api:
            return self._api.ExitShort(signal_name, from_entry_signal)
        self._pending_orders.append(('exit_short', 0, signal_name))

    def set_stop_loss(self, signal_name, mode, value):
        """Set stop loss. mode: 'Ticks', 'Price', or CalculationMode enum."""
        calc_mode = self._resolve_calc_mode(mode)
        self._api.SetStopLoss(signal_name, calc_mode, value, False)

    def set_profit_target(self, signal_name, mode, value):
        """Set profit target."""
        calc_mode = self._resolve_calc_mode(mode)
        self._api.SetProfitTarget(signal_name, calc_mode, value)

    def set_trail_stop(self, signal_name, mode, value):
        """Set trailing stop."""
        calc_mode = self._resolve_calc_mode(mode)
        self._api.SetTrailStop(signal_name, calc_mode, value, False)

    # ──────────────────────────────────────────────
    # Indicator Access
    # ──────────────────────────────────────────────

    def sma(self, period, input_series=None):
        """Simple Moving Average."""
        if input_series is None:
            return self._api.SMA(period)
        return self._api.SMA(input_series, period)

    def ema(self, period, input_series=None):
        """Exponential Moving Average."""
        if input_series is None:
            return self._api.EMA(period)
        return self._api.EMA(input_series, period)

    def rsi(self, period, smooth=3, input_series=None):
        """Relative Strength Index."""
        if input_series is None:
            return self._api.RSI(period, smooth)
        return self._api.RSI(input_series, period, smooth)

    def atr(self, period):
        """Average True Range."""
        return self._api.ATR(period)

    def bollinger(self, period, std_dev=2):
        """Bollinger Bands."""
        return self._api.Bollinger(std_dev, period)

    def macd(self, fast=12, slow=26, smooth=9):
        """MACD indicator."""
        return self._api.MACD(fast, slow, smooth)

    def stochastics(self, period_d=7, period_k=14, smooth=3):
        """Stochastics."""
        return self._api.Stochastics(period_d, period_k, smooth)

    # ──────────────────────────────────────────────
    # Data Series
    # ──────────────────────────────────────────────

    def add_data_series(self, period_type, value, instrument_name=None):
        """Add a secondary data series. Call in on_configure().

        period_type: 'Minute', 'Hour', 'Day', 'Tick', etc.
        value: period value (e.g. 5 for 5-minute)
        """
        bars_period = self._resolve_bars_period(period_type)
        if instrument_name:
            self._api.AddDataSeries(instrument_name, bars_period, value)
        else:
            self._api.AddDataSeries(bars_period, value)

    # ──────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────

    def print(self, message):
        """Print to NinjaTrader Output window."""
        if self._api:
            self._api.Print(str(message))
        else:
            self._pending_prints.append(str(message))

    def get_current_bid(self, bars_ago=0):
        """Get current bid price."""
        return float(self._api.GetCurrentBid(bars_ago))

    def get_current_ask(self, bars_ago=0):
        """Get current ask price."""
        return float(self._api.GetCurrentAsk(bars_ago))

    @property
    def bars_required_to_trade(self):
        return int(self._api.BarsRequiredToTrade)

    @bars_required_to_trade.setter
    def bars_required_to_trade(self, value):
        self._api.BarsRequiredToTrade = value

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    def _resolve_calc_mode(self, mode):
        """Convert string to CalculationMode enum."""
        if isinstance(mode, str):
            import clr
            from NinjaTrader.NinjaScript import CalculationMode
            return getattr(CalculationMode, mode)
        return mode

    def _resolve_bars_period(self, period_type):
        """Convert string to BarsPeriodType enum."""
        if isinstance(mode, str):
            import clr
            from NinjaTrader.Data import BarsPeriodType
            return getattr(BarsPeriodType, period_type)
        return period_type
