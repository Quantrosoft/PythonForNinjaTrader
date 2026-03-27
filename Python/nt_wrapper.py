"""
NinjaTrader Python Wrapper - Convenience functions for strategy development.

Provides utility functions that mirror common NinjaTrader helper methods.
"""


def cross_above(series1, series2, lookback=1):
    """Check if series1 crossed above series2.

    Equivalent to NinjaTrader's CrossAbove().
    Works with indicator series (e.g. sma_fast, sma_slow).
    """
    return series1[0] > series2[0] and series1[lookback] <= series2[lookback]


def cross_below(series1, series2, lookback=1):
    """Check if series1 crossed below series2.

    Equivalent to NinjaTrader's CrossBelow().
    """
    return series1[0] < series2[0] and series1[lookback] >= series2[lookback]


def cross_above_value(series, value, lookback=1):
    """Check if series crossed above a fixed value."""
    return series[0] > value and series[lookback] <= value


def cross_below_value(series, value, lookback=1):
    """Check if series crossed below a fixed value."""
    return series[0] < value and series[lookback] >= value


def highest(series, period):
    """Return the highest value in the series over the last N bars.

    Equivalent to NinjaTrader's MAX().
    """
    return max(series[i] for i in range(period))


def lowest(series, period):
    """Return the lowest value in the series over the last N bars.

    Equivalent to NinjaTrader's MIN().
    """
    return min(series[i] for i in range(period))


def highest_bar(series, period):
    """Return the bars ago index of the highest value."""
    max_val = series[0]
    max_idx = 0
    for i in range(1, period):
        if series[i] > max_val:
            max_val = series[i]
            max_idx = i
    return max_idx


def lowest_bar(series, period):
    """Return the bars ago index of the lowest value."""
    min_val = series[0]
    min_idx = 0
    for i in range(1, period):
        if series[i] < min_val:
            min_val = series[i]
            min_idx = i
    return min_idx


def rising(series, period=1):
    """Check if series has been rising for N bars."""
    return all(series[i] > series[i + 1] for i in range(period))


def falling(series, period=1):
    """Check if series has been falling for N bars."""
    return all(series[i] < series[i + 1] for i in range(period))


def slope(series, period=1):
    """Calculate the slope (difference) over N bars."""
    return series[0] - series[period]
