#!/usr/bin/env python3
"""
Senior Architect Skill — Validation Script

Validates Clean Architecture boundaries are respected:
1. Runs architecture_checks.py (coupling thresholds, layer boundary violations).
2. Runs mypy type checking on src/.
3. Runs dependency_analyzer.py to detect circular imports.

Usage:
    poetry run python .agent/skills/senior-architect/scripts/validate.py

Exit Codes:
    0  — PASS: Architecture constraints satisfied.
    1  — FAIL: Layer boundary violation, circular import, or type error detected.
"""

import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = Path(__file__).parent


def run_cmd(cmd: list[str], label: str) -> tuple[int, str]:
    print(f"\n{'=' * 60}")
    print(f"  VALIDATE: {label}")
    print(f"  Command:  {' '.join(cmd)}")
    print(f"{'=' * 60}\n")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    output = result.stdout + result.stderr
    print(output[-3000:] if len(output) > 3000 else output)
    return result.returncode, output


def main() -> int:
    results: list[tuple[str, bool]] = []

    # Check 1: Architecture checks (layer boundaries, coupling thresholds)
    arch_script = SCRIPTS_DIR / "architecture_checks.py"
    exit_code, _ = run_cmd(
        ["poetry", "run", "python", str(arch_script)],
        "Architecture Checks — Layer Boundaries & Coupling",
    )
    results.append(("Architecture Checks", exit_code == 0))
    if exit_code != 0:
        print(
            "\n❌ FAIL: Architecture boundary violation or coupling threshold exceeded."
        )

    # Check 2: mypy type checking
    exit_code, _ = run_cmd(
        ["poetry", "run", "mypy", "src/"],
        "mypy — Type Safety",
    )
    results.append(("mypy Type Check", exit_code == 0))
    if exit_code != 0:
        print("\n❌ FAIL: Type errors detected. Fix before proceeding.")

    # Check 3: Circular import detection via dependency_analyzer
    dep_script = SCRIPTS_DIR / "dependency_analyzer.py"
    if dep_script.exists():
        exit_code, _ = run_cmd(
            ["python", str(dep_script)],
            "Dependency Analyzer — No Circular Imports",
        )
        results.append(("No Circular Imports", exit_code == 0))
        if exit_code != 0:
            print("\n❌ FAIL: Circular imports detected. Resolve before merging.")
    else:
        print(f"\n⚠️  {dep_script} not found — skipping circular import check.")

    # Summary
    print(f"\n{'=' * 60}")
    print("  SENIOR ARCHITECT VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    all_passed = True
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  ✅ PASS — Architecture constraints satisfied.")
        return 0
    else:
        print("\n  ❌ FAIL — See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
