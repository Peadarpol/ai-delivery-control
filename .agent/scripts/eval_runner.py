#!/usr/bin/env python3
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

# Fix: Ensure UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

REGRESSION_PATH = Path(".agent/evals/regression_evals.jsonl")


def run_regression():
    print("\n" + "=" * 60)
    print("  RUNNING DETERMINISTIC REGRESSION EVALS")
    print("=" * 60)

    if not REGRESSION_PATH.exists():
        print(f"⚠️  Regression dataset missing at {REGRESSION_PATH}")
        return False

    failures = 0
    total = 0
    with open(REGRESSION_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                case = json.loads(line)
                total += 1
                print(f"  [{case['id']}] {case['description']}...", end="", flush=True)

                # Execute the check command
                cmd = case["command"]
                # Replace placeholders if any (e.g. {{PATH}})
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                expected = case.get("expected_exit_code", 0)
                if result.returncode == expected:
                    print(" ✅ PASS")
                else:
                    print(" ❌ FAIL")
                    print(f"    Expected: {expected}, Got: {result.returncode}")
                    print(f"    Error: {result.stderr or result.stdout}")
                    failures += 1
            except Exception as e:
                print(f" ❌ ERROR: {e}")
                failures += 1

    print("-" * 60)
    if failures == 0:
        print(f"  ✅ All {total} regressions passed.")
        return True
    else:
        print(f"  ❌ {failures}/{total} regressions failed.")
        return False


def run_skill_eval(skill_name):
    print("\n" + "=" * 60)
    print(f"  RUNNING SKILL EVAL: {skill_name}")
    print("=" * 60)

    cases_path = Path(f".agent/skills/{skill_name}/evals/cases.csv")
    rubric_path = Path(f".agent/skills/{skill_name}/evals/rubric.md")

    if not cases_path.exists():
        print(f"⚠️  Skill cases missing at {cases_path}")
        return

    print(f"  Reading cases from {cases_path}")
    # In a real system, this would trigger LLM-as-judge or specific test suites.
    # For this runner, we report on existence and readiness.
    with open(cases_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = sum(1 for _ in reader)
        print(f"  Loaded {count} evaluation cases.")

    if rubric_path.exists():
        print(f"  Rubric found at {rubric_path}")
    else:
        print(f"  ⚠️  No rubric.md found for {skill_name}")

    print("-" * 60)
    print(f"  ✅ Skill evaluation readiness verified for {skill_name}.")


def main():
    parser = argparse.ArgumentParser(description="Harness Evaluation Runner")
    parser.add_argument("--skill", help="Run evaluation for a specific skill")
    parser.add_argument("--all", action="store_true", help="Run all evaluations")
    parser.add_argument(
        "--regression-only", action="store_true", help="Run only regressions"
    )

    args = parser.parse_args()

    success = True
    if args.regression_only or args.all:
        success = run_regression()

    if args.skill:
        run_skill_eval(args.skill)
    elif args.all:
        # Get all skills
        skills_dir = Path(".agent/skills")
        if skills_dir.exists():
            for skill_path in skills_dir.iterdir():
                if skill_path.is_dir():
                    run_skill_eval(skill_path.name)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
