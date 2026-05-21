#!/usr/bin/env python3
"""
Test Coverage Analyzer

Analyzes test coverage and identifies gaps.

Usage:
    poetry run python .agent/skills/python-testing/scripts/coverage_analyzer.py
"""

import json
import subprocess
import sys
from pathlib import Path


def run_coverage():
    """Run pytest with coverage and return results."""
    print("=" * 60)
    print("TEST COVERAGE ANALYZER")
    print("=" * 60)

    print("\nRunning tests with coverage...")

    result = subprocess.run(
        [
            "poetry",
            "run",
            "pytest",
            "--cov=src",
            "--cov-report=json",
            "--cov-report=term-missing",
            "-q",
        ],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr and "error" in result.stderr.lower():
        print(result.stderr)

    return result.returncode == 0


def analyze_coverage():
    """Analyze coverage.json and provide insights."""
    coverage_file = Path("coverage.json")

    if not coverage_file.exists():
        print("\n⚠️  coverage.json not found. Run tests first.")
        return

    data = json.loads(coverage_file.read_text())

    print("\n" + "=" * 60)
    print("COVERAGE ANALYSIS")
    print("=" * 60)

    # Overall summary
    totals = data.get("totals", {})
    covered = totals.get("covered_lines", 0)
    total = totals.get("num_statements", 0)
    percent = totals.get("percent_covered", 0)

    print(f"\n📊 Overall Coverage: {percent:.1f}%")
    print(f"   Covered: {covered}/{total} lines")

    # Threshold check
    threshold = 80
    if percent >= threshold:
        print(f"\n✅ Coverage meets {threshold}% threshold")
    else:
        print(
            f"\n⚠️  Coverage below {threshold}% threshold ({threshold - percent:.1f}% gap)"
        )

    # File-by-file analysis
    files = data.get("files", {})

    # Find files with low coverage
    low_coverage = []
    no_coverage = []

    for filepath, file_data in files.items():
        file_percent = file_data.get("summary", {}).get("percent_covered", 100)
        missing = file_data.get("missing_lines", [])

        if file_percent == 0 and missing:
            no_coverage.append((filepath, len(missing)))
        elif file_percent < 50 and file_percent > 0:
            low_coverage.append((filepath, file_percent, len(missing)))

    if no_coverage:
        print(f"\n🔴 Files with NO coverage ({len(no_coverage)}):")
        for filepath, missing_count in sorted(
            no_coverage, key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"    - {filepath} ({missing_count} lines)")

    if low_coverage:
        print(f"\n🟡 Files with LOW coverage (<50%) ({len(low_coverage)}):")
        for filepath, pct, missing in sorted(low_coverage, key=lambda x: x[1])[:10]:
            print(f"    - {filepath}: {pct:.0f}% ({missing} lines missing)")

    # Most impactful files to test
    print("\n" + "-" * 40)
    print("📈 HIGHEST IMPACT FILES TO TEST")
    print("-" * 40)
    print("\nFiles where adding tests would most improve coverage:\n")

    all_files = [
        (fp, fd.get("summary", {}).get("missing_lines", 0))
        for fp, fd in files.items()
        if fd.get("summary", {}).get("missing_lines", 0) > 0
    ]

    for filepath, missing in sorted(all_files, key=lambda x: x[1], reverse=True)[:5]:
        print(f"    {missing} lines: {filepath}")


def find_untested_functions():
    """Find public functions that aren't tested."""
    print("\n" + "=" * 60)
    print("UNTESTED FUNCTION DETECTION")
    print("=" * 60)

    src_path = Path("src")
    tests_path = Path("tests")

    if not src_path.exists():
        print("\n⚠️  src/ directory not found")
        return

    # Find all function definitions in src/
    import re

    functions = []

    for py_file in src_path.rglob("*.py"):
        content = py_file.read_text(errors="ignore")
        # Find public functions (not starting with _)
        for match in re.finditer(r"def ([a-zA-Z][a-zA-Z0-9_]*)\s*\(", content):
            func_name = match.group(1)
            if not func_name.startswith("_"):
                functions.append((str(py_file), func_name))

    # Find all test functions
    tested = set()
    if tests_path.exists():
        for test_file in tests_path.rglob("test_*.py"):
            content = test_file.read_text(errors="ignore")
            tested.update(re.findall(r"\b([a-zA-Z][a-zA-Z0-9_]*)\b", content))

    # Find untested functions
    untested = [(f, fn) for f, fn in functions if fn not in tested]

    if untested:
        print(f"\n💡 Potentially untested functions ({len(untested)}):\n")
        # Show first 10
        for filepath, func_name in untested[:10]:
            print(f"    - {func_name}() in {filepath}")
        if len(untested) > 10:
            print(f"    ... and {len(untested) - 10} more")
    else:
        print("\n✅ All functions appear to be referenced in tests")


def main():
    success = run_coverage()
    analyze_coverage()
    find_untested_functions()

    print("\n" + "=" * 60)
    print("Analysis complete!")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
