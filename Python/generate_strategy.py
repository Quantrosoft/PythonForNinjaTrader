"""
Auto-generates NinjaTrader C# strategy wrappers from Python strategy files.

Reads PARAMETERS dict from a Python strategy file and generates:
  1. A C# strategy class with typed NinjaTrader properties (clear names!)
  2. A strategy template XML

Usage:
    python generate_strategy.py strategies/chrystal_ball.py
    python generate_strategy.py --watch     # watch mode: auto-regenerate on changes

The generated .cs file is saved to NinjaTrader's Custom/Strategies/ folder,
which triggers NinjaTrader's auto-recompilation.
"""

import ast
import os
import re
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime

# Paths relative to this script
SCRIPT_DIR = Path(__file__).parent
STRATEGIES_DIR = SCRIPT_DIR / 'strategies'
NT_CUSTOM = SCRIPT_DIR.parent.parent  # bin/Custom
NT_STRATEGIES = NT_CUSTOM / 'Strategies'
NT_ROOT = NT_CUSTOM.parent.parent     # NinjaTrader 8
TEMPLATES_DIR = NT_ROOT / 'templates' / 'Strategy'

# Map Python types to C# types
TYPE_MAP = {
    'int': 'int',
    'float': 'double',
    'double': 'double',
    'string': 'string',
    'bool': 'bool',
}

# Map Python types to C# default literals
DEFAULT_MAP = {
    'int': '0',
    'float': '0.0',
    'double': '0.0',
    'string': '""',
    'bool': 'false',
}


def snake_to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return ''.join(w.capitalize() for w in name.split('_'))


def parse_parameters(py_path: str) -> dict:
    """Parse PARAMETERS dict from a Python strategy file using AST."""
    with open(py_path, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if (isinstance(item, ast.Assign)
                        and len(item.targets) == 1
                        and isinstance(item.targets[0], ast.Name)
                        and item.targets[0].id == 'PARAMETERS'):
                    return _eval_dict(item.value, source)
    return {}


def _eval_dict(node, source: str) -> dict:
    """Safely evaluate a dict literal from AST."""
    try:
        code = ast.get_source_segment(source, node)
        if code:
            return ast.literal_eval(code)
    except (ValueError, SyntaxError):
        pass
    return {}


def find_strategy_class(py_path: str) -> str:
    """Find the NtStrategy subclass name in the Python file."""
    with open(py_path, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = ''
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if base_name == 'NtStrategy':
                    return node.name
    return None


def generate_cs(class_name: str, py_filename: str, parameters: dict) -> str:
    """Generate a NinjaTrader C# strategy wrapper class."""
    cs_class = class_name + 'Strategy'
    rel_script = f'strategies\\\\{py_filename}'

    # Build property declarations
    props = []
    defaults = []
    order = 0

    for param_name, spec in parameters.items():
        ptype = spec.get('type', 'string')
        cs_type = TYPE_MAP.get(ptype, 'string')
        display = spec.get('display', snake_to_pascal(param_name))
        group = spec.get('group', class_name)
        default = spec.get('default')

        # Format default value for C#
        if default is None:
            cs_default = DEFAULT_MAP.get(ptype, '""')
        elif ptype == 'bool':
            cs_default = 'true' if default else 'false'
        elif ptype == 'string':
            cs_default = f'"{default}"'
        elif ptype in ('float', 'double'):
            cs_default = f'{default}'
        else:
            cs_default = str(default)

        defaults.append(f'                    {snake_to_pascal(param_name)} = {cs_default};')

        props.append(f'''
        [Display(Name = "{display}", GroupName = "{group}", Order = {order})]
        public {cs_type} {snake_to_pascal(param_name)} {{ get; set; }}''')
        order += 1

    # Build parameter push code for OnBarUpdate
    param_pushes = []
    for param_name, spec in parameters.items():
        ptype = spec.get('type', 'string')
        pascal = snake_to_pascal(param_name)
        if ptype in ('int', 'float', 'double'):
            param_pushes.append(
                f'                        $"_nt_bridge_instance.{param_name} = '
                f'{{{pascal}.ToString(System.Globalization.CultureInfo.InvariantCulture)}}\\n" +')
        elif ptype == 'bool':
            param_pushes.append(
                f'                        $"_nt_bridge_instance.{param_name} = '
                f'{{{pascal}.ToString().Replace(\\"True\\", \\"True\\").Replace(\\"False\\", \\"False\\")}}\\n" +')
        else:
            param_pushes.append(
                f'                        $"_nt_bridge_instance.{param_name} = '
                f"\\'{{{pascal}}}\\'\\n\" +")

    param_push_code = '\n'.join(param_pushes).rstrip(' +') if param_pushes else '                        "" +'
    # Remove trailing +
    param_push_code = param_push_code.rstrip(' +')

    defaults_code = '\n'.join(defaults)

    cs = f'''// AUTO-GENERATED by generate_strategy.py — DO NOT EDIT MANUALLY
// Source: strategies/{py_filename}
// Generated: {datetime.now():%Y-%m-%d %H:%M:%S}

using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript.Strategies.Python;

namespace NinjaTrader.NinjaScript.Strategies
{{
    public class {cs_class} : Strategy
    {{
        private bool _engineReady;
        private string _pythonBasePath;
        private int _barCallCount;
        private bool _paramsApplied;

        protected override void OnStateChange()
        {{
            switch (State)
            {{
                case State.SetDefaults:
                    Description = "Python strategy: {class_name}";
                    Name = "{cs_class}";
                    Calculate = Calculate.OnEachTick;
                    EntriesPerDirection = 1;
                    EntryHandling = EntryHandling.AllEntries;
                    IsExitOnSessionCloseStrategy = true;
                    ExitOnSessionCloseSeconds = 30;
                    IsFillLimitOnTouch = false;
                    BarsRequiredToTrade = 20;
                    StartBehavior = StartBehavior.WaitUntilFlat;
                    // Python
                    PythonHome = @"C:\\Python311";
                    PythonDll = @"C:\\Python311\\python311.dll";
                    // Parameters
{defaults_code}
                    break;

                case State.Configure:
                    break;

                case State.DataLoaded:
                    try
                    {{
                        _pythonBasePath = System.IO.Path.Combine(
                            NinjaTrader.Core.Globals.UserDataDir, "bin", "Custom", "Strategies", "Python");
                        PythonEngineManager.Initialize(PythonHome, PythonDll, Print);
                        var scriptPath = System.IO.Path.Combine(_pythonBasePath, @"{rel_script}");
                        PythonEngineManager.LoadStrategy(scriptPath, _pythonBasePath, Print);
                        _engineReady = true;
                        Print("[{cs_class}] Python engine ready");
                    }}
                    catch (Exception ex)
                    {{
                        Print($"[{cs_class}] Init failed: {{ex.Message}}");
                        _engineReady = false;
                    }}
                    break;

                case State.Terminated:
                    PythonEngineManager.Shutdown(Print);
                    _engineReady = false;
                    break;
            }}
        }}

        protected override void OnBarUpdate()
        {{
            if (!_engineReady) return;
            try
            {{
                using (var gil = PythonEngineManager.AcquireGIL())
                {{
                    // Apply typed parameters once
                    if (!_paramsApplied)
                    {{
                        PythonEngineManager.RunSimple(
{param_push_code});
                        _paramsApplied = true;
                        Print("[{cs_class}] Parameters applied");
                    }}

                    // Push bar data
                    PythonEngineManager.RunSimple(
                        $"_nt_bridge_instance._bar_data = {{{{'current_bar': {{CurrentBar}}, " +
                        $"'close': {{Close[0].ToString(System.Globalization.CultureInfo.InvariantCulture)}}, " +
                        $"'open': {{Open[0].ToString(System.Globalization.CultureInfo.InvariantCulture)}}, " +
                        $"'high': {{High[0].ToString(System.Globalization.CultureInfo.InvariantCulture)}}, " +
                        $"'low': {{Low[0].ToString(System.Globalization.CultureInfo.InvariantCulture)}}, " +
                        $"'volume': {{Volume[0].ToString(System.Globalization.CultureInfo.InvariantCulture)}}, " +
                        $"'time': '{{Times[0][0]:o}}', " +
                        $"'instrument': '{{Instrument.FullName}}', " +
                        $"'tick_size': {{TickSize.ToString(System.Globalization.CultureInfo.InvariantCulture)}}}}}}");
                    PythonEngineManager.RunSimple("_nt_bridge_instance.on_bar_update()");

                    // Flush prints
                    FlushPrints();
                    // Flush orders
                    FlushOrders();
                }}
            }}
            catch (Exception ex) {{ Print($"[{cs_class}] Error: {{ex.Message}}"); }}
        }}

        private void FlushPrints()
        {{
            try
            {{
                PythonEngineManager.RunSimple("_flush_tmp = '\\\\n'.join(_nt_bridge_instance._pending_prints)");
                PythonEngineManager.RunSimple("_nt_bridge_instance._pending_prints.clear()");
                var result = PythonEngineManager.Eval("_flush_tmp");
                var text = result?.ToString();
                if (!string.IsNullOrEmpty(text))
                    foreach (var line in text.Split('\\n'))
                        Print(line);
            }}
            catch {{ }}
        }}

        private void FlushOrders()
        {{
            try
            {{
                PythonEngineManager.RunSimple("_orders_tmp = '|'.join(f'{{o[0]}},{{o[1]}},{{o[2]}}' for o in _nt_bridge_instance._pending_orders)");
                PythonEngineManager.RunSimple("_nt_bridge_instance._pending_orders.clear()");
                var result = PythonEngineManager.Eval("_orders_tmp");
                var orderStr = result?.ToString();
                if (string.IsNullOrEmpty(orderStr)) return;

                foreach (var order in orderStr.Split('|'))
                {{
                    var parts = order.Split(',');
                    if (parts.Length < 3) continue;
                    var action = parts[0];
                    int qty = int.Parse(parts[1]);
                    var signal = parts[2];
                    switch (action)
                    {{
                        case "enter_long": EnterLong(qty, signal); break;
                        case "enter_short": EnterShort(qty, signal); break;
                        case "exit_long": ExitLong(signal, ""); break;
                        case "exit_short": ExitShort(signal, ""); break;
                    }}
                }}
            }}
            catch {{ }}
        }}

        #region Properties
        [Display(Name = "Python Home", GroupName = "0. Python", Order = 0)]
        public string PythonHome {{ get; set; }}

        [Display(Name = "Python DLL", GroupName = "0. Python", Order = 1)]
        public string PythonDll {{ get; set; }}
{chr(10).join(props)}
        #endregion
    }}
}}
'''
    return cs


def generate_template(cs_class: str, class_name: str, parameters: dict) -> str:
    """Generate NinjaTrader strategy template XML."""
    param_xml = []
    for param_name, spec in parameters.items():
        pascal = snake_to_pascal(param_name)
        default = spec.get('default', '')
        if isinstance(default, bool):
            default = str(default).lower()
        param_xml.append(f'      <{pascal}>{default}</{pascal}>')

    params_str = '\n'.join(param_xml)

    return f'''<?xml version="1.0" encoding="utf-8"?>
<StrategyTemplate>
  <StrategyType>NinjaTrader.NinjaScript.Strategies.{cs_class}</StrategyType>
  <Strategy>
    <{cs_class} xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
      <IsVisible>true</IsVisible>
      <calculate2>OnEachTick</calculate2>
      <AreLinesConfigurable>true</AreLinesConfigurable>
      <ArePlotsConfigurable>true</ArePlotsConfigurable>
      <BarsPeriodSerializable>
        <BarsPeriodTypeSerialize>1</BarsPeriodTypeSerialize>
        <BaseBarsPeriodType>Minute</BaseBarsPeriodType>
        <BaseBarsPeriodValue>1</BaseBarsPeriodValue>
        <VolumetricDeltaType>BidAsk</VolumetricDeltaType>
        <MarketDataType>Last</MarketDataType>
        <PointAndFigurePriceType>Close</PointAndFigurePriceType>
        <ReversalType>Tick</ReversalType>
        <Value>1</Value>
        <Value2>1</Value2>
      </BarsPeriodSerializable>
      <BarsToLoad>0</BarsToLoad>
      <Calculate>OnEachTick</Calculate>
      <Displacement>0</Displacement>
      <DisplayInDataBox>true</DisplayInDataBox>
      <From>2025-11-01T00:00:00</From>
      <IsAutoScale>true</IsAutoScale>
      <Lines />
      <MaximumBarsLookBack>TwoHundredFiftySix</MaximumBarsLookBack>
      <Name>{cs_class}</Name>
      <Panel>-1</Panel>
      <Plots />
      <SessionTemplate>Default</SessionTemplate>
      <To>2025-11-08T00:00:00</To>
      <BarsRequiredToTrade>20</BarsRequiredToTrade>
      <DaysToLoad>20</DaysToLoad>
      <DefaultQuantity>1</DefaultQuantity>
      <EntriesPerDirection>1</EntriesPerDirection>
      <EntryHandling>AllEntries</EntryHandling>
      <ExitOnSessionCloseSeconds>30</ExitOnSessionCloseSeconds>
      <IsFillLimitOnTouch>false</IsFillLimitOnTouch>
      <IsExitOnSessionCloseStrategy>true</IsExitOnSessionCloseStrategy>
      <IsInstantiatedOnEachOptimizationIteration>true</IsInstantiatedOnEachOptimizationIteration>
      <IsUnmanaged>false</IsUnmanaged>
      <OrderFillResolution>Standard</OrderFillResolution>
      <Slippage>0</Slippage>
      <StartBehavior>WaitUntilFlat</StartBehavior>
      <StopTargetHandling>PerEntryExecution</StopTargetHandling>
      <TimeInForce>Gtc</TimeInForce>
      <TraceOrders>false</TraceOrders>
      <RealtimeErrorHandling>StopCancelClose</RealtimeErrorHandling>
      <PythonHome>C:\\Python311</PythonHome>
      <PythonDll>C:\\Python311\\python311.dll</PythonDll>
{params_str}
    </{cs_class}>
  </Strategy>
</StrategyTemplate>
'''


def generate_for_file(py_path: str, quiet=False):
    """Generate C# wrapper + template for a Python strategy file."""
    py_path = Path(py_path)
    if not py_path.exists():
        print(f"ERROR: {py_path} not found")
        return False

    class_name = find_strategy_class(str(py_path))
    if not class_name:
        if not quiet:
            print(f"SKIP: No NtStrategy subclass in {py_path.name}")
        return False

    parameters = parse_parameters(str(py_path))
    cs_class = class_name + 'Strategy'

    # Generate C# wrapper
    cs_code = generate_cs(class_name, py_path.name, parameters)
    cs_path = NT_STRATEGIES / f'{cs_class}.cs'

    # Only write if content changed (avoid unnecessary NT recompilation)
    cs_hash_new = hashlib.md5(cs_code.encode()).hexdigest()
    cs_hash_old = ''
    if cs_path.exists():
        cs_hash_old = hashlib.md5(cs_path.read_bytes()).hexdigest()

    if cs_hash_new != cs_hash_old:
        cs_path.write_text(cs_code, encoding='utf-8')
        print(f"{'UPDATED' if cs_hash_old else 'CREATED'}: {cs_path.name} ({len(parameters)} params)")
    else:
        if not quiet:
            print(f"UNCHANGED: {cs_path.name}")
        return False

    # Generate template
    template_dir = TEMPLATES_DIR / cs_class
    template_dir.mkdir(parents=True, exist_ok=True)
    template_path = template_dir / 'Default.xml'
    template_code = generate_template(cs_class, class_name, parameters)
    template_path.write_text(template_code, encoding='utf-8')

    return True


def watch_mode():
    """Watch strategies/ directory and auto-regenerate on changes."""
    print(f"Watching {STRATEGIES_DIR} for changes...")
    print("Press Ctrl+C to stop.\n")

    # Track file modification times
    mtimes = {}

    # Initial scan
    for py_file in STRATEGIES_DIR.glob('*.py'):
        if py_file.name.startswith('_'):
            continue
        mtimes[py_file] = py_file.stat().st_mtime
        generate_for_file(str(py_file), quiet=True)

    print(f"Watching {len(mtimes)} Python strategy files...\n")

    while True:
        try:
            time.sleep(1)
            for py_file in STRATEGIES_DIR.glob('*.py'):
                if py_file.name.startswith('_'):
                    continue
                mtime = py_file.stat().st_mtime
                if py_file not in mtimes or mtimes[py_file] != mtime:
                    mtimes[py_file] = mtime
                    print(f"\n[{datetime.now():%H:%M:%S}] Changed: {py_file.name}")
                    if generate_for_file(str(py_file)):
                        print("  -> NinjaTrader will auto-recompile")
        except KeyboardInterrupt:
            print("\nStopped.")
            break


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python generate_strategy.py strategies/chrystal_ball.py")
        print("  python generate_strategy.py --watch")
        print("  python generate_strategy.py --all")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--watch':
        watch_mode()
    elif arg == '--all':
        for py_file in sorted(STRATEGIES_DIR.glob('*.py')):
            if py_file.name.startswith('_'):
                continue
            generate_for_file(str(py_file))
    else:
        generate_for_file(arg)
