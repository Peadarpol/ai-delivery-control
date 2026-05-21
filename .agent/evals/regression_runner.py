#!/usr/bin/env python3
"""
Golden Dataset Regression Runner.
Validates every catalogued failure scenario still has a covering test.

Usage: python .agent/evals/regression_runner.py [--verify-only | --run]
  --verify-only  Check that test files/functions exist (fast, no execution)
  --run          Actually execute the referenced tests (slow, full verification)
"""

import subprocess
import sys
from pathlib import Path

import yaml  # PyYAML — already a project dependency

# Fix: Ensure UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

DATASET_PATH = Path(__file__).parent / "golden_dataset.yaml"


def load_dataset() -> list[dict]:
    if not DATASET_PATH.exists():
        return []
    with open(DATASET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("entries", [])


def verify_test_exists(entry: dict) -> tuple[bool, str]:
    """Check that the referenced test file and function exist."""
    ref = entry.get("test_reference", "")
    if "::" not in ref:
        return (
            False,
            f"[VIOLATION] Invalid test_reference format for {entry['id']}.\n"
            f"[REMEDIATION] Ensure the reference follows the 'file::function' pattern "
            f"(e.g., 'tests/unit/test_service.py::test_create_member').",
        )
    file_part, func_part = ref.split("::", 1)
    path = Path(file_part)
    if not path.exists():
        return (
            False,
            f"[VIOLATION] Test file not found for {entry['id']}: {file_part}\n"
            f"[REMEDIATION] The golden dataset is referencing a file that no longer exists. "
            f"If the test was moved, update golden_dataset.yaml. If it was deleted, "
            f"this is a REGRESSION — restore the covering test immediately.",
        )
    content = path.read_text(encoding="utf-8")
    if f"def {func_part}" not in content:
        return (
            False,
            f"[VIOLATION] Test function '{func_part}' not found in {file_part} for {entry['id']}.\n"
            f"[REMEDIATION] The function may have been renamed or deleted. "
            f"Restore the test function to maintain golden dataset coverage.",
        )
    return True, f"{entry['id']}: ✅ Test exists"


def run_test(entry: dict) -> tuple[bool, str]:
    """Actually execute the referenced test."""
    ref = entry.get("test_reference", "")
    print(f"  Running: {ref}...", end="", flush=True)
    result = subprocess.run(
        ["poetry", "run", "pytest", ref, "-v", "--tb=short", "--no-header"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    passed = result.returncode == 0
    icon = "✅" if passed else "❌"
    print(f"\r  {entry['id']}: {icon} {ref} — {'PASSED' if passed else 'FAILED'}")
    return passed, f"{entry['id']} {ref}"


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--verify-only"
    entries = load_dataset()

    if not entries:
        print(
            "⚠️  Golden dataset is empty or missing. Add entries after incident post-mortems."
        )
        sys.exit(0)

    print(f"\n{'─' * 60}")
    print(f"  GOLDEN DATASET REGRESSION CHECK ({len(entries)} scenarios)")
    print(f"  Mode: {mode}")
    print(f"{'─' * 60}\n")

    failures = []
    for entry in entries:
        if mode == "--run":
            ok, msg = run_test(entry)
        else:
            ok, msg = verify_test_exists(entry)
            print(f"  {msg}")

        if not ok:
            failures.append(msg)

    print(f"\n{'─' * 60}")
    if failures:
        print(f"  ❌ {len(failures)} failure(s) detected!")
        print(f"{'─' * 60}\n")
        sys.exit(1)
    else:
        print(f"  ✅ All {len(entries)} scenarios verified.")
        print(f"{'─' * 60}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
