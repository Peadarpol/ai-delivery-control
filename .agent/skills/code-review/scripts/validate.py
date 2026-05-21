#!/usr/bin/env python3
"""
Code Review Skill — Validation Script

Validates that a code review did not introduce quality regressions:
1. No new `# type: ignore` markers added to source files.
2. No new `# noqa` suppressions added to source files.
3. No new `@pytest.mark.skip` (without reason) added to test files.
4. Ruff lint exits clean on changed source files.
5. Full test suite still passes (no regressions introduced during review fixes).

Usage:
    poetry run python .agent/skills/code-review/scripts/validate.py

Exit Codes:
    0  — PASS: Code review quality gates satisfied.
    1  — FAIL: New suppressions, lint errors, or regressions detected.
"""

import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def run_cmd(cmd: list[str], label: str) -> tuple[int, str]:
    print(f"\n{'=' * 60}")
    print(f"  VALIDATE: {label}")
    print(f"  Command:  {' '.join(cmd)}")
    print(f"{'=' * 60}\n")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    output = result.stdout + result.stderr
    print(output[-3000:] if len(output) > 3000 else output)
    return result.returncode, output


def check_diff_for_pattern(
    pattern: str, label: str, paths: list[str]
) -> tuple[bool, str]:
    """Check if a pattern appears in additions in the last commit diff."""
    cmd = ["git", "diff", "HEAD~1", "--"] + paths
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    additions = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("+") and pattern in line and not line.startswith("+++")
    ]
    if additions:
        print(f"\n⚠️  New '{pattern}' occurrences detected ({len(additions)}):")
        for a in additions[:10]:
            print(f"   {a}")
        return False, f"{len(additions)} new {label} added"
    return True, f"No new {label}"


def main() -> int:
    results: list[tuple[str, bool]] = []

    # Check 1: No new type: ignore in src/
    ok, msg = check_diff_for_pattern(
        "# type: ignore", "type:ignore suppressions", ["src/"]
    )
    results.append(("No New type:ignore", ok))
    if not ok:
        print(f"  ⚠️  {msg} — each suppression requires documented justification.")

    # Check 2: No new noqa in src/
    ok, msg = check_diff_for_pattern("# noqa", "noqa suppressions", ["src/"])
    results.append(("No New noqa", ok))
    if not ok:
        print(f"  ⚠️  {msg} — prefer fixing the lint issue over suppressing it.")

    # Check 3: No new unannotated skip markers in tests/
    ok, msg = check_diff_for_pattern(
        "mark.skip", "pytest.mark.skip markers", ["tests/"]
    )
    results.append(("No New skip Markers", ok))
    if not ok:
        print(
            f"  ❌  {msg} — skipped tests hide failures. Add reason= or fix the test."
        )

    # Check 4: Ruff lint on src/
    exit_code, _ = run_cmd(
        ["poetry", "run", "ruff", "check", "src/"],
        "Ruff Lint — No Violations in src/",
    )
    results.append(("Ruff Lint Clean", exit_code == 0))
    if exit_code != 0:
        print("\n❌ FAIL: Lint violations remain after review.")

    # Check 5: Full test suite — no regressions
    exit_code, _ = run_cmd(
        ["poetry", "run", "pytest", "tests/", "-q", "--tb=short", "--no-header"],
        "Regression Check — Full Test Suite",
    )
    results.append(("No Regressions", exit_code == 0))
    if exit_code != 0:
        print("\n❌ FAIL: Test regressions detected.")

    # Summary
    print(f"\n{'=' * 60}")
    print("  CODE REVIEW VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    all_passed = True
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  ✅ PASS — Code review quality gates satisfied.")
        return 0
    else:
        print("\n  ❌ FAIL — See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
