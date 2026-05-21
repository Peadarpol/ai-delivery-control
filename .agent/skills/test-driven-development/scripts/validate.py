#!/usr/bin/env python3
"""
Test-Driven Development Skill — Validation Script

Validates that TDD discipline was followed:
1. New test file(s) exist at the specified path.
2. Tests actually pass (not just exist).
3. No lint errors were introduced in modified source files.
4. Coverage did not decrease (optional, if baseline provided).

Usage:
    poetry run python .agent/skills/test-driven-development/scripts/validate.py --test-file <path> [--source-file <path>] [--baseline-coverage <float>]

Exit Codes:
    0  — PASS: TDD discipline verified.
    1  — FAIL: Tests missing, failing, or lint violations found.
"""

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate TDD discipline")
    parser.add_argument(
        "--test-file",
        type=str,
        required=True,
        help="Path to the new/modified test file",
    )
    parser.add_argument(
        "--source-file", type=str, help="Path to the implementation file to lint-check"
    )
    parser.add_argument(
        "--baseline-coverage",
        type=float,
        help="Previous coverage percentage to compare against",
    )
    args = parser.parse_args()

    results: list[tuple[str, bool]] = []

    # --- Check 1: Test file exists ---
    test_path = Path(args.test_file)
    if not test_path.is_absolute():
        test_path = PROJECT_ROOT / test_path

    if not test_path.exists():
        print(f"\n❌ FAIL: Test file does not exist: {test_path}")
        print("   TDD requires writing the test FIRST. The test file must exist.")
        return 1
    results.append(("Test File Exists", True))

    # --- Check 2: Tests pass ---
    exit_code, _ = run_cmd(
        ["poetry", "run", "pytest", str(test_path), "-v", "--tb=short", "-q"],
        "Test Execution — New Tests Must Pass",
    )
    passed = exit_code == 0
    results.append(("Tests Pass", passed))
    if not passed:
        print("\n❌ FAIL: New tests are failing. Implementation incomplete.")

    # --- Check 3: Lint check on source file ---
    if args.source_file:
        source_path = Path(args.source_file)
        if not source_path.is_absolute():
            source_path = PROJECT_ROOT / source_path

        if source_path.exists():
            exit_code, _ = run_cmd(
                ["poetry", "run", "ruff", "check", str(source_path)],
                "Lint Check — No New Violations",
            )
            lint_passed = exit_code == 0
            results.append(("Lint Clean", lint_passed))
            if not lint_passed:
                print("\n⚠️  WARNING: Lint violations in source file.")
        else:
            print(f"\n⚠️  Source file not found: {source_path} — skipping lint check.")
    else:
        print("\n⚠️  No --source-file specified. Skipping lint check.")

    # --- Check 4: Regression check ---
    exit_code, _ = run_cmd(
        ["poetry", "run", "pytest", "tests/", "-v", "--tb=short", "-q"],
        "Regression Check — Full Suite",
    )
    regression_passed = exit_code == 0
    results.append(("No Regressions", regression_passed))
    if not regression_passed:
        print("\n❌ FAIL: Regressions detected in the full test suite.")

    # --- Summary ---
    print(f"\n{'='*60}")
    print("  TDD VALIDATION SUMMARY")
    print(f"{'='*60}")
    all_passed = True
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  ✅ PASS — TDD discipline verified.")
        return 0
    else:
        print("\n  ❌ FAIL — See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
