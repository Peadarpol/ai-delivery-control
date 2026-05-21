#!/usr/bin/env python3
"""
Safe Refactoring Skill — Validation Script

Validates that a refactoring operation was safe:
1. Baseline test count matches or improves (no tests lost).
2. All previously passing tests still pass.
3. No new lint violations introduced.

Usage:
    poetry run python .agent/skills/refactoring/scripts/validate.py --baseline <int> [--scope <path>]

Arguments:
    --baseline   Number of passing tests BEFORE the refactor started.
    --scope      Path to scope the test run (default: tests/).

Exit Codes:
    0  — PASS: Refactor is safe, behavior unchanged.
    1  — FAIL: Tests regressed or were lost.
    2  — WARN: Baseline not provided, advisory only.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Fix Windows console encoding for emoji/unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def run_cmd(cmd: list[str], label: str) -> tuple[int, str]:
    """Run a command and return (exit_code, combined output)."""
    print(f"\n{'='*60}")
    print(f"  VALIDATE: {label}")
    print(f"  Command:  {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    output = result.stdout + result.stderr
    print(output[-2000:] if len(output) > 2000 else output)
    return result.returncode, output


def extract_test_count(output: str) -> int | None:
    """Extract the number of passed tests from pytest output."""
    # Matches patterns like "42 passed" or "42 passed, 2 warnings"
    match = re.search(r"(\d+) passed", output)
    if match:
        return int(match.group(1))
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate safe refactoring outcome")
    parser.add_argument(
        "--baseline", type=int, help="Number of passing tests before refactor"
    )
    parser.add_argument("--scope", type=str, default="tests/", help="Test scope path")
    args = parser.parse_args()

    results: list[tuple[str, bool]] = []

    # --- Check 1: Run test suite ---
    exit_code, output = run_cmd(
        ["poetry", "run", "pytest", args.scope, "-v", "--tb=short", "-q"],
        "Post-Refactor Test Suite",
    )
    tests_pass = exit_code == 0
    results.append(("All Tests Pass", tests_pass))

    if not tests_pass:
        print("\n❌ FAIL: Tests are failing after refactor.")
        print("   STOP: Revert the last change and report the failure.")

    # --- Check 2: Test count comparison ---
    current_count = extract_test_count(output)
    if args.baseline is not None and current_count is not None:
        count_ok = current_count >= args.baseline
        results.append(
            (f"Test Count ({current_count} >= {args.baseline} baseline)", count_ok)
        )
        if not count_ok:
            print(
                f"\n❌ FAIL: Test count dropped from {args.baseline} to {current_count}."
            )
            print(
                "   Tests may have been accidentally deleted or broken during refactor."
            )
    elif args.baseline is not None:
        print("\n⚠️  Could not extract test count from pytest output.")
        results.append(("Test Count Check", False))
    else:
        print("\n⚠️  No --baseline provided. Cannot verify test count stability.")
        print("   Usage: validate.py --baseline 142")

    # --- Check 3: Lint check ---
    exit_code, _ = run_cmd(
        ["poetry", "run", "ruff", "check", "src/"], "Lint Check — No New Violations"
    )
    lint_ok = exit_code == 0
    results.append(("Lint Clean", lint_ok))
    if not lint_ok:
        print("\n⚠️  WARNING: Lint violations found after refactor.")

    # --- Summary ---
    print(f"\n{'='*60}")
    print("  REFACTORING VALIDATION SUMMARY")
    print(f"{'='*60}")
    all_passed = True
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  ✅ PASS — Refactor is safe. Behavior unchanged.")
        return 0
    else:
        print("\n  ❌ FAIL — Refactor introduced problems. See above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
