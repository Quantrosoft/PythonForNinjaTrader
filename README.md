# Python for NinjaTrader 8

Write NinjaTrader strategies in Python.

## Architecture

```
NinjaTrader 8 (C#)
    |
    +-- Generated C# Wrapper (auto-generated per strategy)
            |
            +-- pythonnet (Python.Runtime.dll)
                    |
                    +-- Your Python Strategy (.py)
```

The C# wrapper handles NinjaTrader lifecycle events, pushes bar data into Python on each tick, and executes orders returned by your Python strategy. `generate_strategy.py` reads your Python file and auto-generates both the C# wrapper and a NinjaTrader template XML.

## Prerequisites

- **Python 3.8 - 3.12** (3.11 recommended)
- **NinjaTrader 8** (installed, run at least once)
- **pythonnet**: `pip install pythonnet`

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/youruser/PythonForNinjaTrader.git
cd PythonForNinjaTrader

# 2. Install
python install.py

# 3. Open NinjaTrader, find your strategy in the Strategies tab
```

The installer copies all files to `~/Documents/NinjaTrader 8/bin/Custom/Strategies/Python/`, generates C# wrappers, and NinjaTrader auto-compiles them on next startup.

## Writing Your First Strategy

Create a new `.py` file in `Python/strategies/`:

```python
from nt_api import NtStrategy

class MyStrategy(NtStrategy):
    PARAMETERS = {
        'fast_period': {'type': 'int', 'default': 10, 'display': 'Fast Period', 'group': 'MyStrategy'},
        'slow_period': {'type': 'int', 'default': 20, 'display': 'Slow Period', 'group': 'MyStrategy'},
    }

    def on_bar_update(self):
        bar = self._bar_data
        close = bar.get('close', 0)
        current_bar = bar.get('current_bar', 0)

        if current_bar < self.slow_period:
            return

        # Your logic here
        if close > some_condition:
            self.enter_long(1, "MyEntry")
        elif close < some_condition:
            self.exit_long("MyExit")
```

Then regenerate the C# wrapper:

```bash
cd Python
python generate_strategy.py strategies/my_strategy.py
```

Or use watch mode to auto-regenerate on file changes:

```bash
python generate_strategy.py --watch
```

## PARAMETERS Dict

Each strategy defines a `PARAMETERS` class variable. Each entry maps a snake_case parameter name to a spec dict:

| Key       | Description                          | Example            |
|-----------|--------------------------------------|--------------------|
| `type`    | `int`, `float`, `double`, `string`, `bool` | `'int'`      |
| `default` | Default value                        | `10`               |
| `display` | Display name in NinjaTrader UI       | `'Fast Period'`    |
| `group`   | Property group in NinjaTrader UI     | `'MyStrategy'`     |

Parameters are automatically exposed as NinjaTrader strategy properties in the generated C# wrapper and pushed to the Python instance at runtime.

## Available API

### Order Methods

| Method | Description |
|--------|-------------|
| `self.enter_long(quantity, signal_name)` | Market order to go long |
| `self.enter_short(quantity, signal_name)` | Market order to go short |
| `self.exit_long(signal_name)` | Exit long position at market |
| `self.exit_short(signal_name)` | Exit short position at market |
| `self.print(message)` | Print to NinjaTrader Output window |

### Bar Data (`self._bar_data` dict keys)

| Key | Description |
|-----|-------------|
| `current_bar` | Bar index (0-based from oldest) |
| `close` | Current bar close price |
| `open` | Current bar open price |
| `high` | Current bar high price |
| `low` | Current bar low price |
| `volume` | Current bar volume |
| `time` | Bar timestamp (ISO format string) |
| `instrument` | Instrument name |
| `tick_size` | Minimum price increment |

### Lifecycle Methods (override in subclass)

| Method | When Called |
|--------|------------|
| `on_bar_update()` | Each bar update (main logic) |
| `on_configure()` | State.Configure |
| `on_data_loaded()` | State.DataLoaded |
| `on_stop()` | Strategy terminated |

## How It Works

1. You write a Python class inheriting from `NtStrategy` with a `PARAMETERS` dict
2. `generate_strategy.py` parses your `.py` file via AST and generates:
   - A C# strategy class (`{ClassName}Strategy.cs`) in NinjaTrader's Strategies folder
   - A NinjaTrader template XML in the templates folder
3. NinjaTrader compiles the C# wrapper on startup
4. At runtime, the C# wrapper initializes pythonnet, loads your Python script, pushes bar data as a dict on each tick, and reads back orders/prints

## Limitations

- **No direct NT indicator access**: Python strategies cannot call NinjaTrader's built-in indicators (SMA, EMA, etc.) directly from the bar-data-push mode. Indicator access via `self._api` requires the full pythonnet bridge (C# instance injection).
- **Crystal Ball**: The ChrystalBall example strategy uses future bar data (`GetValueAt`) and only works in Historical/Backtest mode, not live.
- **Single timeframe**: The bar-data-push mode supports the primary data series only. Multi-timeframe requires the full `_api` bridge.
- **No historical lookback**: `self._bar_data` provides current bar only (`[0]`). Historical bar indexing (`close[5]`) requires the full `_api` bridge.

## Project Structure

```
PythonForNinjaTrader/
  install.py              # One-click installer
  Python/
    nt_api.py             # NtStrategy base class
    nt_wrapper.py         # Utility functions (cross_above, highest, etc.)
    PythonEngine.cs       # C# pythonnet bridge (reflection-based)
    PyChrystalBall.cs     # C# wrapper for ChrystalBall (with future data injection)
    Python.Runtime.dll    # pythonnet runtime
    generate_strategy.py  # Auto-generates C# wrappers from Python strategies
    strategies/
      chrystal_ball.py    # Example: Crystal Ball strategy
```

## License

MIT
