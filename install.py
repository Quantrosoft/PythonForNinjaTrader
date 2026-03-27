#!/usr/bin/env python3
"""
One-click installer for Python for NinjaTrader 8.

Copies the Python/ directory to NinjaTrader's Custom/Strategies/Python/
and runs generate_strategy.py to create C# wrappers + NT templates.

Usage:
    python install.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def check_python_version():
    """Ensure Python 3.8+ is running."""
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 8):
        print(f"ERROR: Python 3.8+ required, found {v.major}.{v.minor}.{v.micro}")
        return False
    print(f"[OK] Python {v.major}.{v.minor}.{v.micro} ({sys.executable})")
    return True


def check_pythonnet():
    """Check that pythonnet is installed."""
    try:
        import importlib
        spec = importlib.util.find_spec("clr")
        if spec is None:
            raise ImportError
        print("[OK] pythonnet installed")
        return True
    except ImportError:
        print("ERROR: pythonnet not found. Install it with:")
        print("    pip install pythonnet")
        return False


def find_nt8_path():
    """Auto-detect NinjaTrader 8 Custom directory."""
    docs = Path.home() / "Documents"
    nt_custom = docs / "NinjaTrader 8" / "bin" / "Custom"
    if nt_custom.is_dir():
        print(f"[OK] NinjaTrader 8 found: {nt_custom}")
        return nt_custom

    # Fallback: check common alternative locations
    for alt in [Path("C:/Users") / os.getlogin() / "Documents" / "NinjaTrader 8" / "bin" / "Custom"]:
        if alt.is_dir():
            print(f"[OK] NinjaTrader 8 found: {alt}")
            return alt

    print("ERROR: NinjaTrader 8 not found at ~/Documents/NinjaTrader 8/bin/Custom/")
    print("       Make sure NinjaTrader 8 is installed and has been run at least once.")
    return None


def copy_python_dir(source_dir, dest_dir):
    """Copy Python/ directory to NT8, excluding .git, __pycache__, .pyc files."""

    def ignore_patterns(directory, files):
        ignored = set()
        for f in files:
            if f in ('.git', '__pycache__', '.gitignore'):
                ignored.add(f)
            elif f.endswith('.pyc'):
                ignored.add(f)
        return ignored

    print(f"\nCopying files to {dest_dir}")
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True, ignore=ignore_patterns)

    # Count copied files
    count = sum(1 for _ in dest_dir.rglob('*') if _.is_file())
    print(f"[OK] {count} files copied to {dest_dir}")


def run_generate_strategy(python_dest_dir):
    """Run generate_strategy.py --all from the Python destination directory."""
    gen_script = python_dest_dir / "generate_strategy.py"
    if not gen_script.exists():
        print(f"ERROR: {gen_script} not found after copy")
        return False

    print("\nGenerating C# wrappers and NT templates...")
    result = subprocess.run(
        [sys.executable, str(gen_script), "--all"],
        cwd=str(python_dest_dir),
        capture_output=True,
        text=True,
    )

    if result.stdout:
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
    if result.stderr:
        for line in result.stderr.strip().splitlines():
            print(f"  [stderr] {line}")

    if result.returncode != 0:
        print(f"ERROR: generate_strategy.py exited with code {result.returncode}")
        return False

    print("[OK] C# wrappers generated")
    return True


def main():
    print("=" * 60)
    print("  Python for NinjaTrader 8 - Installer")
    print("=" * 60)
    print()

    # Verify we're running from the repo root
    repo_root = Path(__file__).parent
    source_python_dir = repo_root / "Python"
    if not source_python_dir.is_dir():
        print(f"ERROR: Python/ directory not found at {source_python_dir}")
        print("       Run this script from the repository root.")
        sys.exit(1)

    # Check prerequisites
    print("Checking prerequisites...\n")

    if not check_python_version():
        sys.exit(1)

    if not check_pythonnet():
        sys.exit(1)

    nt_custom = find_nt8_path()
    if nt_custom is None:
        sys.exit(1)

    # Copy files
    dest_dir = nt_custom / "Strategies" / "Python"
    copy_python_dir(source_python_dir, dest_dir)

    # Generate C# wrappers
    if not run_generate_strategy(dest_dir):
        sys.exit(1)

    # Done
    print()
    print("=" * 60)
    print("  Installation complete!")
    print()
    print("  Next steps:")
    print("  1. Open NinjaTrader 8")
    print("  2. Go to Strategies tab")
    print("  3. Your Python strategies should appear after compilation")
    print("  4. Configure Python Home and Python DLL paths in strategy settings")
    print("=" * 60)


if __name__ == "__main__":
    main()
