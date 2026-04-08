using System;
using System.IO;
using System.Reflection;

namespace NinjaTrader.Custom.Python
{
    internal static class PythonEngineManager
    {
        private static Assembly _pythonRuntime;
        private static bool _initialized;
        private static int _refCount;
        private static readonly object _lock = new object();
        private static Type _pyEngineType;
        private static Type _pyType;
        private static Type _runtimeType; // pythonnet 3: Python.Runtime.Runtime

        // pythonnet 3: use PyModule scope instead of raw IntPtr globals
        private static object _mainScope; // PyModule for __main__
        private static object _mainThreadState; // from BeginAllowThreads

        public static void Initialize(string pythonHome, string pythonDll, Action<string> log)
        {
            lock (_lock)
            {
                _refCount++;
                if (_initialized) return;
                try
                {
                    var dllPath = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                        "NinjaTrader 8", "bin", "Custom", "Python.Runtime.dll");
                    if (!File.Exists(dllPath))
                        throw new FileNotFoundException($"Python.Runtime.dll not found at: {dllPath}");

                    _pythonRuntime = Assembly.LoadFrom(dllPath);
                    log?.Invoke($"[PythonEngine] Loaded Python.Runtime.dll from {dllPath}");

                    _pyEngineType = _pythonRuntime.GetType("Python.Runtime.PythonEngine");
                    _pyType = _pythonRuntime.GetType("Python.Runtime.Py");
                    _runtimeType = _pythonRuntime.GetType("Python.Runtime.Runtime");

                    // pythonnet 3 (same approach as cTrader): set PYTHONNET_PYDLL env var
                    if (!string.IsNullOrEmpty(pythonDll))
                    {
                        Environment.SetEnvironmentVariable("PYTHONNET_PYDLL", pythonDll);
                        log?.Invoke($"[PythonEngine] PYTHONNET_PYDLL={pythonDll}");
                    }

                    // Also try setting Runtime.PythonDLL property directly as fallback
                    if (!string.IsNullOrEmpty(pythonDll) && _runtimeType != null)
                    {
                        var pythonDllProp = _runtimeType.GetProperty("PythonDLL", BindingFlags.Public | BindingFlags.Static);
                        if (pythonDllProp != null)
                        {
                            pythonDllProp.SetValue(null, pythonDll);
                            log?.Invoke($"[PythonEngine] Runtime.PythonDLL={pythonDll}");
                        }
                    }

                    // Add pythonHome to PATH so python3xx.dll can be found
                    if (!string.IsNullOrEmpty(pythonHome))
                    {
                        var path = Environment.GetEnvironmentVariable("PATH") ?? "";
                        if (!path.Contains(pythonHome))
                            Environment.SetEnvironmentVariable("PATH", pythonHome + ";" + path);
                        Environment.SetEnvironmentVariable("PYTHONHOME", pythonHome);
                        log?.Invoke($"[PythonEngine] PYTHONHOME={pythonHome}");
                    }

                    // Initialize Python engine — GIL is implicitly held after this
                    _pyEngineType.GetMethod("Initialize", Type.EmptyTypes)?.Invoke(null, null);
                    DiscoverMethods(log);

                    // pythonnet 3: get __main__ module — NO AcquireGIL(), GIL already held by Initialize()
                    var importMethod = _pyType.GetMethod("Import", new[] { typeof(string) });
                    if (importMethod != null)
                    {
                        _mainScope = importMethod.Invoke(null, new object[] { "__main__" });
                        log?.Invoke($"[PythonEngine] Main scope acquired: {_mainScope?.GetType().Name}");
                        DiscoverScopeMethods(log);
                    }

                    // Release GIL so other threads (warm-up, playback) can acquire it via Py.GIL()
                    var beginAllowThreads = _pyEngineType.GetMethod("BeginAllowThreads",
                        BindingFlags.Public | BindingFlags.Static);
                    if (beginAllowThreads != null)
                    {
                        _mainThreadState = beginAllowThreads.Invoke(null, null);
                        log?.Invoke("[PythonEngine] BeginAllowThreads — GIL released for multi-threading");
                    }

                    _initialized = true;
                    log?.Invoke("[PythonEngine] Python runtime initialized (pythonnet 3)");
                }
                catch (Exception ex)
                {
                    _refCount--;
                    var inner = ex;
                    while (inner.InnerException != null) inner = inner.InnerException;
                    throw new Exception($"Python init failed: {inner.GetType().Name}: {inner.Message}", ex);
                }
            }
        }

        public static void LoadStrategy(string scriptPath, string basePath, Action<string> log)
        {
            using (var gil = AcquireGIL())
            {
                var scriptDir = Path.GetDirectoryName(scriptPath) ?? "";
                var module = Path.GetFileNameWithoutExtension(scriptPath);
                log?.Invoke($"[PythonEngine] Importing: {module} from {basePath}");

                RunSimple($"import sys, importlib, traceback\nif r'{basePath}' not in sys.path: sys.path.insert(0, r'{basePath}')\nif r'{scriptDir}' not in sys.path: sys.path.insert(0, r'{scriptDir}')");
                RunSimple(
                    "# Clear cached lib modules so changes are picked up\n" +
                    "for _mk in list(sys.modules.keys()):\n" +
                    "    if _mk.startswith('lib.') or _mk == 'lib' or _mk == 'nt_api':\n" +
                    "        del sys.modules[_mk]\n");
                RunSimple($"try:\n    if '{module}' in sys.modules:\n        del sys.modules['{module}']\n    import {module}\n    _import_ok = True\nexcept Exception as _e:\n    _import_ok = False\n    _import_err = traceback.format_exc()");

                // Check if import succeeded
                var importOk = Eval("_import_ok");
                if (importOk == null || importOk.ToString() != "True")
                {
                    var err = Eval("_import_err");
                    throw new Exception($"Python import failed:\n{err}");
                }

                RunSimple(
                    $"_nt_bridge_cls = None\n" +
                    $"for _n in dir({module}):\n" +
                    $"    _o = getattr({module}, _n)\n" +
                    $"    if isinstance(_o, type) and _n != 'NtStrategy' and hasattr(_o, '_is_nt_strategy'):\n" +
                    $"        _nt_bridge_cls = _o; break\n");

                RunSimple("if _nt_bridge_cls is None:\n    raise Exception('No NtStrategy subclass found')");
                RunSimple("_nt_bridge_instance = _nt_bridge_cls()");
                log?.Invoke($"[PythonEngine] Strategy created from {module}");
            }
        }

        private static MethodInfo _gilMethod;
        private static MethodInfo _evalMethod;   // PythonEngine.Eval (static)
        private static MethodInfo _execMethod;   // PythonEngine.Exec (static)
        private static MethodInfo _runSimpleMethod; // PythonEngine.RunSimpleString fallback
        private static MethodInfo _scopeEvalMethod;  // PyModule.Eval (instance)
        private static MethodInfo _scopeExecMethod;  // PyModule.Exec (instance)

        private static void DiscoverMethods(Action<string> log)
        {
            // GIL method on Py class
            _gilMethod = _pyType.GetMethod("GIL", BindingFlags.Public | BindingFlags.Static);
            if (_gilMethod == null)
                log?.Invoke("[PythonEngine] WARNING: Py.GIL() not found");

            // Scan PythonEngine static methods
            foreach (var m in _pyEngineType.GetMethods(BindingFlags.Public | BindingFlags.Static))
            {
                var parms = m.GetParameters();
                if (m.Name == "Eval" || m.Name == "Exec" || m.Name == "RunSimpleString" || m.Name == "RunString")
                    log?.Invoke($"[PythonEngine] PythonEngine.{m.Name}({string.Join(", ", Array.ConvertAll(parms, p => p.ParameterType.Name + " " + p.Name))}) -> {m.ReturnType.Name}");

                // PythonEngine.RunSimpleString(string) — works in both v2 and v3
                if (m.Name == "RunSimpleString" && parms.Length == 1 && parms[0].ParameterType == typeof(string))
                    _runSimpleMethod = m;

                // PythonEngine.Exec(string) — pythonnet 3 static Exec
                if (m.Name == "Exec" && parms.Length == 1 && parms[0].ParameterType == typeof(string))
                    _execMethod = m;

                // PythonEngine.Eval(string) — pythonnet 3 static Eval
                if (m.Name == "Eval" && parms.Length == 1 && parms[0].ParameterType == typeof(string))
                    _evalMethod = m;
            }

            log?.Invoke($"[PythonEngine] GIL={_gilMethod != null}, Eval={_evalMethod != null}, Exec={_execMethod != null}, RunSimple={_runSimpleMethod != null}");
        }

        private static MethodInfo _scopeGetMethod;   // PyModule.Get(string) -> PyObject

        private static void DiscoverScopeMethods(Action<string> log)
        {
            if (_mainScope == null) return;
            var scopeType = _mainScope.GetType();
            foreach (var m in scopeType.GetMethods(BindingFlags.Public | BindingFlags.Instance))
            {
                var parms = m.GetParameters();
                if (m.Name == "Exec" || m.Name == "Eval" || m.Name == "Get" || m.Name == "Set")
                    log?.Invoke($"[PythonEngine] PyModule.{m.Name}({string.Join(", ", Array.ConvertAll(parms, p => p.ParameterType.FullName + " " + p.Name))}) -> {m.ReturnType.Name}");

                // Match by name + param count only (typeof(string) comparison fails across assemblies)
                if (m.Name == "Eval" && parms.Length == 2 && !m.IsGenericMethod)
                    _scopeEvalMethod = m;
                if (m.Name == "Exec" && parms.Length == 2 && !m.IsGenericMethod)
                    _scopeExecMethod = m;
                if (m.Name == "Get" && parms.Length == 1 && !m.IsGenericMethod)
                    _scopeGetMethod = m;
            }
            log?.Invoke($"[PythonEngine] ScopeEval={_scopeEvalMethod != null}, ScopeExec={_scopeExecMethod != null}, ScopeGet={_scopeGetMethod != null}");
        }

        public static IDisposable AcquireGIL()
        {
            if (_gilMethod == null)
                throw new InvalidOperationException("GIL method not found on Py type");
            System.Threading.Monitor.Enter(_lock);
            try
            {
                var gil = (IDisposable)_gilMethod.Invoke(null, null);
                return new GILGuard(gil);
            }
            catch
            {
                System.Threading.Monitor.Exit(_lock);
                throw;
            }
        }

        private class GILGuard : IDisposable
        {
            private IDisposable _innerGil;
            private bool _disposed;
            public GILGuard(IDisposable innerGil) { _innerGil = innerGil; }
            public void Dispose()
            {
                if (_disposed) return;
                _disposed = true;
                try { _innerGil?.Dispose(); }
                finally { System.Threading.Monitor.Exit(_lock); }
            }
        }

        public static void RunSimple(string code)
        {
            // pythonnet 3: prefer cached scope.Exec(string, PyDict) on __main__ module
            if (_scopeExecMethod != null && _mainScope != null)
            {
                _scopeExecMethod.Invoke(_mainScope, new object[] { code, null });
                return;
            }
            // Fallback: PythonEngine.RunSimpleString (static, always works)
            if (_runSimpleMethod != null)
                _runSimpleMethod.Invoke(null, new object[] { code });
            else if (_execMethod != null)
                _execMethod.Invoke(null, new object[] { code });
            else
                throw new InvalidOperationException("No exec method available");
        }

        public static object Eval(string expr)
        {
            // pythonnet 3: prefer cached scope.Eval(string, PyDict) on __main__ module
            if (_scopeEvalMethod != null && _mainScope != null)
                return _scopeEvalMethod.Invoke(_mainScope, new object[] { expr, null });
            // Fallback: PythonEngine.Eval (static)
            if (_evalMethod != null)
                return _evalMethod.Invoke(null, new object[] { expr });
            // Last resort: RunSimple to assign temp var, then Get from scope
            if (_scopeGetMethod != null && _mainScope != null)
            {
                RunSimple($"_eval_tmp_ = {expr}");
                return _scopeGetMethod.Invoke(_mainScope, new object[] { "_eval_tmp_" });
            }
            throw new InvalidOperationException("Eval method not found");
        }

        public static void Exec(string stmt)
        {
            RunSimple(stmt); // delegate to RunSimple which handles scope
        }

        public static void Shutdown(Action<string> log)
        {
            lock (_lock)
            {
                _refCount--;
                if (_refCount > 0 || !_initialized) return;
                try
                {
                    _mainScope = null;
                    _pyEngineType.GetMethod("Shutdown", Type.EmptyTypes)?.Invoke(null, null);
                    _initialized = false;
                    log?.Invoke("[PythonEngine] Shut down");
                }
                catch (Exception ex) { log?.Invoke($"[PythonEngine] Shutdown error: {ex.Message}"); }
            }
        }

        public static Type GetPyType() => _pyType;
        public static Type GetEngineType() => _pyEngineType;
        public static bool IsInitialized => _initialized;
    }
}
