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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
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
