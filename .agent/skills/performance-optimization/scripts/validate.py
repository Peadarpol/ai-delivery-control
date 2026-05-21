#!/usr/bin/env python3
"""
Performance Optimization Skill — Validation Script

Validates that performance work met its goals without regressions:
1. Full test suite passes (no functional regressions from optimisations).
2. mypy clean on src/ (optimisations didn't break type safety).
3. If a baseline file exists at .agent/artifacts/perf_baseline.json, asserts
   no regression vs the recorded p95 latency target.

Usage:
    poetry run python .agent/skills/performance-optimization/scripts/validate.py [--p95-target <ms>]

Exit Codes:
    0  — PASS: No regressions; perf target met (if baseline provided).
    1  — FAIL: Test failures, type errors, or perf target missed.
"""

import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
BASELINE_PATH = PROJECT_ROOT / ".agent" / "artifacts" / "perf_baseline.json"
DEFAULT_P95_TARGET_MS = 200


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
    p95_target = DEFAULT_P95_TARGET_MS
    if "--p95-target" in sys.argv:
        idx = sys.argv.index("--p95-target")
        p95_target = int(sys.argv[idx + 1])

    results: list[tuple[str, bool]] = []

    # Check 1: Full test suite — no functional regressions
    exit_code, _ = run_cmd(
        ["poetry", "run", "pytest", "tests/", "-q", "--tb=short", "--no-header"],
        "Regression Check — Full Test Suite",
    )
    results.append(("No Test Regressions", exit_code == 0))
    if exit_code != 0:
        print("\n❌ FAIL: Optimisations introduced test failures.")

    # Check 2: mypy — type safety preserved
    exit_code, _ = run_cmd(
        ["poetry", "run", "mypy", "src/"],
        "mypy — Type Safety Preserved",
    )
    results.append(("mypy Clean", exit_code == 0))
    if exit_code != 0:
        print(
            "\n❌ FAIL: Type errors introduced during optimisation. Fix before merging."
        )

    # Check 3: Baseline comparison (if baseline file exists)
    if BASELINE_PATH.exists():
        try:
            with open(BASELINE_PATH) as f:
                baseline = json.load(f)
            recorded_p95 = baseline.get("p95_ms")
            if recorded_p95 is not None:
                target_ok = recorded_p95 <= p95_target
                results.append(
                    (
                        f"p95 Latency ≤{p95_target}ms (actual: {recorded_p95}ms)",
                        target_ok,
                    )
                )
                if not target_ok:
                    print(
                        f"\n❌ FAIL: p95 latency {recorded_p95}ms exceeds target {p95_target}ms."
                    )
                else:
                    print(
                        f"\n  p95 latency: {recorded_p95}ms ≤ {p95_target}ms target ✅"
                    )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"\n⚠️  Could not read baseline file: {e} — skipping baseline check.")
    else:
        print(
            f"\n  ℹ️  No baseline file at {BASELINE_PATH}. Skipping latency regression check."
        )
        print("     Create it after profiling: {'p95_ms': <measured_value>}")

    # Summary
    print(f"\n{'=' * 60}")
    print("  PERFORMANCE OPTIMIZATION VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    all_passed = True
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  ✅ PASS — Performance gates satisfied.")
        return 0
    else:
        print("\n  ❌ FAIL — See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
