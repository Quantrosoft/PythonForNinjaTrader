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

The C# wrapper handles NinjaTrader lifecycle events, pushes bar data into Python on each bar update, and executes orders returned by your Python strategy. `generate_strategy.py` reads your Python file and auto-generates both the C# wrapper and a NinjaTrader template XML.

## Prerequisites

- **Python 3.8 - 3.12** (3.11 recommended)
- **NinjaTrader 8** (installed, run at least once)
- **pythonnet**: `pip install pythonnet`

## Quick Start

```bash
# 1. Clone directly into NinjaTrader's Strategies folder
cd "%USERPROFILE%\Documents\NinjaTrader 8\bin\Custom\Strategies"
git clone https://github.com/Quantrosoft/PythonForNinjaTrader.git Python

# 2. Generate C# wrappers for all example strategies
cd Python
python generate_strategy.py --all

# 3. Start NinjaTrader — strategies appear automatically
```

NinjaTrader auto-compiles all `.cs` files in the `bin/Custom` folder tree on startup. The generated C# wrappers and templates are placed in the correct locations automatically.

## Writing Your First Strategy

Create a new `.py` file in `strategies/`:

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

Then generate the C# wrapper:

```bash
python generate_strategy.py strategies/my_strategy.py
```

Restart NinjaTrader or recompile in the NinjaScript Editor (F5). Your strategy appears as **PyMyStrategy** in the Strategies list.

## PARAMETERS Dict

Each strategy defines a `PARAMETERS` class variable. Each entry maps a snake_case parameter name to a spec dict:

| Key       | Description                          | Example            |
|-----------|--------------------------------------|--------------------|
| `type`    | `int`, `float`, `double`, `string`, `bool` | `'int'`      |
| `default` | Default value                        | `10`               |
| `display` | Display name in NinjaTrader UI       | `'Fast Period'`    |
| `group`   | Property group in NinjaTrader UI     | `'MyStrategy'`     |

Parameters are automatically exposed as NinjaTrader strategy properties and pushed to the Python instance at runtime. Access them as `self.fast_period` (snake_case name from dict).

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
| `on_bar_update()` | Each bar close (main logic) |
| `on_configure()` | State.Configure |
| `on_data_loaded()` | State.DataLoaded |
| `on_stop()` | Strategy terminated |

## How It Works

1. You write a Python class inheriting from `NtStrategy` with a `PARAMETERS` dict
2. `generate_strategy.py` parses your `.py` file via AST and generates:
   - A C# strategy class (`Py{ClassName}.cs`) in the Python folder
   - A NinjaTrader template XML in the templates folder
3. NinjaTrader compiles the C# wrapper on startup
4. At runtime, the C# wrapper initializes pythonnet, loads your Python script, pushes bar data as a dict on each bar, and reads back orders/prints

## Limitations

- **No direct NT indicator access**: Python strategies cannot call NinjaTrader's built-in indicators (SMA, EMA, etc.) directly. Implement indicators in Python or use `nt_wrapper.py` helpers.
- **Crystal Ball**: The ChrystalBall example uses future bar data (`GetValueAt`) and only works in Historical/Backtest mode, not live.
- **Single timeframe**: Supports the primary data series only.
- **Current bar only**: `self._bar_data` provides the current bar. For historical lookback, maintain your own buffer in Python.

## Project Structure

```
NinjaTrader 8/bin/Custom/Strategies/Python/   (this repo)
    PythonEngine.cs       # C# pythonnet bridge
    Python.Runtime.dll    # pythonnet 3 runtime
    nt_api.py             # NtStrategy base class
    nt_wrapper.py         # Utility functions (cross_above, highest, etc.)
    generate_strategy.py  # Auto-generates C# wrappers from Python strategies
    strategies/
      chrystal_ball.py    # Example: Crystal Ball (backtest-only future-reading)
      sma_crossover.py    # Example: SMA crossover
      empty_strategy.py   # Minimal template to copy
```

## License

MIT - Copyright (c) 2026 Quantrosoft
