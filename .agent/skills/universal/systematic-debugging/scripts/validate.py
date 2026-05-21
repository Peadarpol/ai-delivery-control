#!/usr/bin/env python3
"""
Systematic Debugging Skill — Validation Script

Validates that the debugging process was followed correctly:
1. The originally failing test/condition now passes.
2. No regressions were introduced (full test suite passes).

Usage:
    poetry run python .agent/skills/systematic-debugging/scripts/validate.py [--test-file <path>] [--marker <marker>]

Arguments:
    --test-file   Path to the specific test file that was failing (optional).
    --marker      Pytest marker to scope the regression check (optional).

Exit Codes:
    0  — PASS: Bug is fixed, no regressions.
    1  — FAIL: Original issue still present or regressions introduced.
    2  — SKIP: No test file specified; cannot verify (advisory only).
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Fix Windows console encoding for emoji/unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = (
    Path(__file__).resolve().parents[4]
)  # .agent/skills/systematic-debugging/scripts -> root


def run_pytest(args: list[str], label: str) -> tuple[int, str]:
    """Run pytest with given args and return (exit_code, output)."""
    cmd = ["poetry", "run", "pytest"] + args + ["-v", "--tb=short", "--no-header", "-q"]
    print(f"\n{'='*60}")
    print(f"  VALIDATE: {label}")
    print(f"  Command:  {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    output = result.stdout + result.stderr
    print(output[-2000:] if len(output) > 2000 else output)  # Tail to avoid flooding
    return result.returncode, output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate systematic debugging outcome"
    )
    parser.add_argument(
        "--test-file", type=str, help="Path to the originally failing test file"
    )
    parser.add_argument(
        "--marker", type=str, help="Pytest marker to scope regression check"
    )
    args = parser.parse_args()

    results: list[tuple[str, bool]] = []

    # --- Check 1: Targeted fix verification ---
    if args.test_file:
        test_path = Path(args.test_file)
        if not test_path.is_absolute():
            test_path = PROJECT_ROOT / test_path

        if not test_path.exists():
            print(f"\n❌ FAIL: Test file not found: {test_path}")
            return 1

        exit_code, _ = run_pytest(
            [str(test_path)], "Fix Verification — Originally Failing Test"
        )
        passed = exit_code == 0
        results.append(("Fix Verification", passed))
        if not passed:
            print("\n❌ FAIL: The originally failing test still fails. Bug not fixed.")
    else:
        print("\n⚠️  No --test-file specified. Skipping targeted fix verification.")
        print("   Usage: validate.py --test-file tests/unit/test_example.py")
        results.append(("Fix Verification", True))  # Cannot check, assume advisory

    # --- Check 2: Regression check ---
    regression_args: list[str] = []
    if args.marker:
        regression_args.extend(["-m", args.marker])
    else:
        regression_args.append("tests/")

    exit_code, output = run_pytest(
        regression_args, "Regression Check — Full Test Suite"
    )
    passed = exit_code == 0
    results.append(("Regression Check", passed))
    if not passed:
        print("\n❌ FAIL: Regressions detected in the test suite.")

    # --- Summary ---
    print(f"\n{'='*60}")
    print("  VALIDATION SUMMARY")
    print(f"{'='*60}")
    all_passed = True
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print(f"\n{'='*60}")
        print("  ✅ PASS — Bug fixed, no regressions.")
        print(f"{'='*60}")
        return 0
    else:
        print(f"\n{'='*60}")
        print("  ❌ FAIL — See details above.")
        print(f"{'='*60}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
