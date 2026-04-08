"""
Empty Strategy Template — minimal skeleton for a new NtStrategy.

Copy this file, rename the class, and fill in your logic.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nt_api import NtStrategy


class EmptyStrategy(NtStrategy):
    """Minimal strategy template. Replace with your own logic."""

    PARAMETERS = {
        'lot_size': {'type': 'int', 'default': 1, 'display': 'Position Size', 'group': 'MyStrategy'},
    }

    def __init__(self):
        super().__init__()
        # Add your instance variables here

    def on_bar_update(self):
        close = self._bar_data.get('close', 0.0) if not self._api else float(self.close[0])
        current_bar = self._bar_data.get('current_bar', 0) if not self._api else self.current_bar

        # Print close price every 100 bars as a heartbeat
        if current_bar % 100 == 0:
            self.print(f"Bar {current_bar}: Close = {close}")

        # --- Add your entry/exit logic below ---
        # Example:
        #   if <your_condition>:
        #       self.enter_long(self.lot_size, "MyLong")
        #   elif <your_exit_condition>:
        #       self.exit_long("MyExitLong")
