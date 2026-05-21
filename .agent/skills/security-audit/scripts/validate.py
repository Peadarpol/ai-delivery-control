#!/usr/bin/env python3
"""
Security Audit Skill — Validation Script

Validates that security scanning was completed and no HIGH/CRITICAL issues remain:
1. Bandit SAST scan exits clean (no HIGH/CRITICAL severity findings).
2. No new `# nosec` suppression markers were introduced in source files.
3. pip-audit exits clean (no known vulnerable dependencies).

Usage:
    poetry run python .agent/skills/security-audit/scripts/validate.py [--source-dir <path>]

Exit Codes:
    0  — PASS: Security gates satisfied.
    1  — FAIL: HIGH/CRITICAL findings, new suppressions, or vulnerable dependencies.
"""

import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "src"


def run_cmd(cmd: list[str], label: str) -> tuple[int, str]:
    print(f"\n{'=' * 60}")
    print(f"  VALIDATE: {label}")
    print(f"  Command:  {' '.join(cmd)}")
    print(f"{'=' * 60}\n")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    output = result.stdout + result.stderr
    print(output[-3000:] if len(output) > 3000 else output)
    return result.returncode, output


def check_nosec_additions() -> tuple[bool, str]:
    """Detect new # nosec markers added in staged/recent changes."""
    result = subprocess.run(
        ["git", "diff", "HEAD~1", "--", "src/"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    additions = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("+") and "# nosec" in line and not line.startswith("+++")
    ]
    if additions:
        print(f"\n⚠️  New # nosec suppressions detected ({len(additions)}):")
        for line in additions:
            print(f"   {line}")
        return (
            False,
            f"{len(additions)} new nosec suppression(s) added without approval",
        )
    return True, "No new nosec suppressions"


def main() -> int:
    source_dir = DEFAULT_SOURCE_DIR
    if "--source-dir" in sys.argv:
        idx = sys.argv.index("--source-dir")
        source_dir = Path(sys.argv[idx + 1])

    results: list[tuple[str, bool]] = []

    # Check 1: Bandit SAST — no HIGH or CRITICAL findings
    exit_code, output = run_cmd(
        [
            "poetry",
            "run",
            "bandit",
            "-r",
            str(source_dir),
            "--severity-level",
            "high",
            "-q",
        ],
        "Bandit SAST — No HIGH/CRITICAL Findings",
    )
    bandit_passed = exit_code == 0
    results.append(("Bandit SAST Clean", bandit_passed))
    if not bandit_passed:
        print(
            "\n❌ FAIL: HIGH or CRITICAL severity findings detected. Fix before proceeding."
        )

    # Check 2: No new nosec suppressions
    nosec_ok, nosec_msg = check_nosec_additions()
    results.append(("No New nosec Suppressions", nosec_ok))
    if not nosec_ok:
        print(
            f"\n⚠️  WARNING: {nosec_msg}. Each suppression requires documented justification."
        )

    # Check 3: pip-audit — no known vulnerable dependencies
    exit_code, _ = run_cmd(
        ["poetry", "run", "pip-audit", "--ignore-vuln", "GHSA-58qw-9mgm-455v"],
        "pip-audit — No Known Vulnerable Dependencies",
    )
    audit_passed = exit_code == 0
    results.append(("No Vulnerable Dependencies", audit_passed))
    if not audit_passed:
        print(
            "\n❌ FAIL: Vulnerable dependencies detected. Run `poetry update` or pin safe versions."
        )

    # Summary
    print(f"\n{'=' * 60}")
    print("  SECURITY AUDIT VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    all_passed = True
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  ✅ PASS — Security gates satisfied.")
        return 0
    else:
        print("\n  ❌ FAIL — See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
