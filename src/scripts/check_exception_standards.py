#!/usr/bin/env python3
"""
Exception Standards Gate Wrapper (T1-K-15, AT-04)
Evaluates whether exception standards tests are configured in the workspace.
Exits 0 with SKIPPED-precondition advisory when tests are absent.
"""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path

def _find_project_root() -> Path:
    """Find the project root: cwd fast-path, then authoritative git query, then
    walk-up-from-file fallback, then fixed-depth last resort."""
    try:
        cwd = Path.cwd().resolve()
        if (cwd / ".git").exists() or (cwd / ".agent").exists():
            return cwd
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, encoding="utf-8", timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except Exception:
        pass
    try:
        current = Path(__file__).resolve()
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists() or (parent / ".agent").exists():
                return parent
    except Exception:
        pass
    return Path(__file__).resolve().parent.parent.parent

PROJECT_ROOT = _find_project_root()
_src_scripts = Path(__file__).resolve().parent
if _src_scripts.exists() and str(_src_scripts) not in sys.path:
    sys.path.insert(0, str(_src_scripts))

import harness_utils


def check_exception_standards() -> int:
    """Run exception standards test suite if present, or exit 0 with SKIPPED-precondition."""
    target_test_file = PROJECT_ROOT / "tests" / "unit" / "test_exception_standards.py"
    if not target_test_file.exists():
        print("ℹ️  [EXCEPTION-STANDARDS] verdict: SKIPPED-precondition — exception standards tests not configured.")
        return 0

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(target_test_file), "-v"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode
    except Exception as e:
        print(f"❌ [EXCEPTION-STANDARDS] Error running exception standards tests: {e}", file=sys.stderr)
        return 1


def main() -> None:
    sys.exit(check_exception_standards())


if __name__ == "__main__":
    main()
