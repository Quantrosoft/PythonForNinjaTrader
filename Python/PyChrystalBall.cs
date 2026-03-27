using System;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Custom.Python;

namespace NinjaTrader.NinjaScript.Strategies
{
    public class PyChrystalBall : Strategy
    {
        private bool _engineReady;
        private string _pythonBasePath;
        private bool _paramsApplied;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "PyChrystalBall";
                Calculate = Calculate.OnBarClose;
                BarsRequiredToTrade = 20;
                PythonHome = @"C:\Python311";
                PythonDll = @"C:\Python311\python311.dll";
                TfSeconds = 3600;
                LotSize = 1;
                MinProfitTicks = 4;
                TfExact = false;
                TargetPct = 100;
            }
            else if (State == State.DataLoaded)
            {
                ClearOutputWindow();
                try
                {
                    _pythonBasePath = System.IO.Path.Combine(
                        NinjaTrader.Core.Globals.UserDataDir, "bin", "Custom", "Strategies", "Python");
                    PythonEngineManager.Initialize(PythonHome, PythonDll, Print);
                    var scriptPath = System.IO.Path.Combine(_pythonBasePath, @"strategies\chrystal_ball.py");
                    PythonEngineManager.LoadStrategy(scriptPath, _pythonBasePath, Print);
                    _engineReady = true;
                    _paramsApplied = false;
                    Print("[PyChrystalBall] Python engine ready");
                }
                catch (Exception ex)
                {
                    var inner = ex;
                    while (inner.InnerException != null) inner = inner.InnerException;
                    Print($"[PyChrystalBall] Init failed: {inner.GetType().Name}: {inner.Message}");
                    _engineReady = false;
                }
            }
            else if (State == State.Terminated)
            {
                _engineReady = false;
            }
        }

        /// <summary>
        /// Look ahead using GetValueAt() — finds max and min Open prices
        /// in the next TfSeconds/60 bars. Only works in Historical mode
        /// where all bars are already loaded.
        /// </summary>
        private void GetFutureExtrema(
            out double maxOpen, out int maxOpenBarIdx,
            out double minOpen, out int minOpenBarIdx)
        {
            int barsAhead = TfSeconds / 60; // 1-minute bars
            int totalBars = Close.Count;

            maxOpen = double.MinValue;
            maxOpenBarIdx = CurrentBar;
            minOpen = double.MaxValue;
            minOpenBarIdx = CurrentBar;

            // Start from CurrentBar+1 (next bar's open = fill price)
            for (int i = CurrentBar + 1; i <= CurrentBar + barsAhead && i < totalBars; i++)
            {
                double futureOpen = Open.GetValueAt(i);
                if (futureOpen > maxOpen)
                {
                    maxOpen = futureOpen;
                    maxOpenBarIdx = i;
                }
                if (futureOpen < minOpen)
                {
                    minOpen = futureOpen;
                    minOpenBarIdx = i;
                }
            }
        }

        protected override void OnBarUpdate()
        {
            if (!_engineReady) return;
            try
            {
                using (var gil = PythonEngineManager.AcquireGIL())
                {
                    if (!_paramsApplied)
                    {
                        PythonEngineManager.RunSimple(
                            $"_nt_bridge_instance.tf_seconds = {TfSeconds.ToString(System.Globalization.CultureInfo.InvariantCulture)}\n" +
                            $"_nt_bridge_instance.lot_size = {LotSize.ToString(System.Globalization.CultureInfo.InvariantCulture)}\n" +
                            $"_nt_bridge_instance.min_profit_ticks = {MinProfitTicks.ToString(System.Globalization.CultureInfo.InvariantCulture)}\n" +
                            $"_nt_bridge_instance.tf_exact = {(TfExact ? "True" : "False")}\n" +
                            $"_nt_bridge_instance.target_pct = {TargetPct.ToString(System.Globalization.CultureInfo.InvariantCulture)}\n"
                        );
                        _paramsApplied = true;
                    }

                    // Crystal Ball: look into the future using GetValueAt()
                    GetFutureExtrema(out double maxOpen, out int maxIdx,
                                     out double minOpen, out int minIdx);

                    // Current bar's open = the fill price if we enter now
                    double currentOpen = Open[0];

                    PythonEngineManager.RunSimple(
                        $"_nt_bridge_instance._bar_data = {{'current_bar': {CurrentBar}, " +
                        $"'close': {Close[0].ToString(System.Globalization.CultureInfo.InvariantCulture)}, " +
                        $"'open': {currentOpen.ToString(System.Globalization.CultureInfo.InvariantCulture)}, " +
                        $"'high': {High[0].ToString(System.Globalization.CultureInfo.InvariantCulture)}, " +
                        $"'low': {Low[0].ToString(System.Globalization.CultureInfo.InvariantCulture)}, " +
                        $"'volume': {Volume[0].ToString(System.Globalization.CultureInfo.InvariantCulture)}, " +
                        $"'instrument': '{Instrument.FullName}', " +
                        $"'tick_size': {TickSize.ToString(System.Globalization.CultureInfo.InvariantCulture)}, " +
                        $"'max_future_open': {maxOpen.ToString(System.Globalization.CultureInfo.InvariantCulture)}, " +
                        $"'max_future_bar': {maxIdx}, " +
                        $"'min_future_open': {minOpen.ToString(System.Globalization.CultureInfo.InvariantCulture)}, " +
                        $"'min_future_bar': {minIdx}, " +
                        $"'total_bars': {Close.Count}}}");
                    PythonEngineManager.RunSimple("_nt_bridge_instance.on_bar_update()");

                    FlushPrints();
                    FlushOrders();
                }
            }
            catch (Exception ex)
            {
                var inner = ex;
                while (inner.InnerException != null) inner = inner.InnerException;
                Print($"[PyChrystalBall] Error: {inner.GetType().Name}: {inner.Message}");
            }
        }

        private void FlushPrints()
        {
            try
            {
                PythonEngineManager.RunSimple("_flush_tmp = '\\n'.join(_nt_bridge_instance._pending_prints)");
                PythonEngineManager.RunSimple("_nt_bridge_instance._pending_prints.clear()");
                var result = PythonEngineManager.Eval("_flush_tmp");
                var text = result?.ToString();
                if (!string.IsNullOrEmpty(text))
                    foreach (var line in text.Split('\n'))
                        Print(line);
            }
            catch { }
        }

        private void FlushOrders()
        {
            try
            {
                PythonEngineManager.RunSimple("_orders_tmp = '|'.join(f'{o[0]},{o[1]},{o[2]}' for o in _nt_bridge_instance._pending_orders)");
                PythonEngineManager.RunSimple("_nt_bridge_instance._pending_orders.clear()");
                var result = PythonEngineManager.Eval("_orders_tmp");
                var orderStr = result?.ToString();
                if (string.IsNullOrEmpty(orderStr)) return;
                foreach (var order in orderStr.Split('|'))
                {
                    var parts = order.Split(',');
                    if (parts.Length < 3) continue;
                    int qty = int.Parse(parts[1]);
                    var signal = parts[2];
                    switch (parts[0])
                    {
                        case "enter_long": EnterLong(qty, signal); break;
                        case "enter_short": EnterShort(qty, signal); break;
                        case "exit_long": ExitLong(signal, ""); break;
                        case "exit_short": ExitShort(signal, ""); break;
                    }
                }
            }
            catch { }
        }

        #region Properties
        [Display(Name = "Python Home", GroupName = "0. Python", Order = 0)]
        public string PythonHome { get; set; }

        [Display(Name = "Python DLL", GroupName = "0. Python", Order = 1)]
        public string PythonDll { get; set; }

        [Display(Name = "Time Window (sec)", GroupName = "CrystalBall", Order = 0)]
        public int TfSeconds { get; set; }

        [Display(Name = "Position Size", GroupName = "CrystalBall", Order = 1)]
        public int LotSize { get; set; }

        [Display(Name = "Min Profit (Ticks)", GroupName = "CrystalBall", Order = 2)]
        public int MinProfitTicks { get; set; }

        [Display(Name = "Exact Exit Time", GroupName = "CrystalBall", Order = 3)]
        public bool TfExact { get; set; }

        [Display(Name = "Target % of Extrema", GroupName = "CrystalBall", Order = 4)]
        public int TargetPct { get; set; }
        #endregion
    }
}
