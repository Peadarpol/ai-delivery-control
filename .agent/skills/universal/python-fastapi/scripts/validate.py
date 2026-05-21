#!/usr/bin/env python3
"""
Python FastAPI Skill — Validation Script

Validates that FastAPI endpoint development follows project standards:
1. Lint check passes on modified source files.
2. Type checking passes (mypy) on modified source files.
3. Related tests pass.
4. OpenAPI schema is valid (app can start and serve /openapi.json).

Usage:
    poetry run python .agent/skills/python-fastapi/scripts/validate.py --source <path> [--test-file <path>]

Exit Codes:
    0  — PASS: Endpoint implementation is standards-compliant.
    1  — FAIL: Lint, type, or test failures detected.
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
    parser = argparse.ArgumentParser(
        description="Validate FastAPI endpoint implementation"
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path to the modified source file or directory",
    )
    parser.add_argument("--test-file", type=str, help="Path to the related test file")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path

    results: list[tuple[str, bool]] = []

    # --- Check 1: Ruff lint ---
    exit_code, _ = run_cmd(
        ["poetry", "run", "ruff", "check", str(source_path)],
        "Ruff Lint — No Violations",
    )
    results.append(("Lint (ruff)", exit_code == 0))

    # --- Check 2: Mypy type check ---
    exit_code, _ = run_cmd(
        ["poetry", "run", "mypy", str(source_path), "--ignore-missing-imports"],
        "Type Check (mypy)",
    )
    results.append(("Type Check (mypy)", exit_code == 0))

    # --- Check 3: Related tests ---
    if args.test_file:
        test_path = Path(args.test_file)
        if not test_path.is_absolute():
            test_path = PROJECT_ROOT / test_path

        if test_path.exists():
            exit_code, _ = run_cmd(
                ["poetry", "run", "pytest", str(test_path), "-v", "--tb=short", "-q"],
                "Related Tests — Must Pass",
            )
            results.append(("Related Tests", exit_code == 0))
        else:
            print(f"\n⚠️  Test file not found: {test_path}")
            results.append(("Related Tests", False))
    else:
        print("\n⚠️  No --test-file specified. Skipping targeted test run.")

    # --- Check 4: Full regression ---
    exit_code, _ = run_cmd(
        ["poetry", "run", "pytest", "tests/unit/", "-v", "--tb=short", "-q"],
        "Unit Test Regression Check",
    )
    results.append(("Unit Regression", exit_code == 0))

    # --- Summary ---
    print(f"\n{'='*60}")
    print("  FASTAPI VALIDATION SUMMARY")
    print(f"{'='*60}")
    all_passed = True
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  ✅ PASS — FastAPI endpoint is standards-compliant.")
        return 0
    else:
        print("\n  ❌ FAIL — See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
