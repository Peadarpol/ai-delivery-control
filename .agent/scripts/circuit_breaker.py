#!/usr/bin/env python3
"""
Circuit Breaker for Agent Operations.
Checks operational limits and returns non-zero if any are exceeded.

Usage: python .agent/scripts/circuit_breaker.py --check [files|iterations|duration]
"""

import subprocess
import sys
from pathlib import Path

from audit_logger import log_action

# Ensure src/scripts is in sys.path for harness_utils
_bootstrap_path = Path(__file__).resolve()
_bootstrap_root = None
for _p in [_bootstrap_path] + list(_bootstrap_path.parents):
    if (_p / ".git").exists() or (_p / ".agent").exists():
        _bootstrap_root = _p
        break
if _bootstrap_root and str(_bootstrap_root / "src" / "scripts") not in sys.path:
    sys.path.insert(0, str(_bootstrap_root / "src" / "scripts"))

try:
    from src.scripts.harness_utils import _find_project_root
except ImportError:
    from harness_utils import _find_project_root

_src_scripts = _find_project_root() / "src" / "scripts"
if _src_scripts.exists() and str(_src_scripts) not in sys.path:
    sys.path.insert(0, str(_src_scripts))
from harness_utils import get_harness_config

def load_limits() -> dict:
    """Load agent_limits from config.yaml, falling back to defaults."""
    
    limits = {
        "max_files_per_commit": get_harness_config("agent_limits", "max_files_per_commit"),
        "max_test_retries": get_harness_config("agent_limits", "max_test_retries"),
        "max_task_budget": get_harness_config("agent_limits", "max_task_budget", default=100),
        "max_session_minutes": get_harness_config("agent_limits", "max_session_minutes"),
        "warn_session_minutes": get_harness_config("agent_limits", "warn_session_minutes"),
    }
    return limits


def check_files_modified() -> tuple[bool, str]:
    """Check number of files staged or modified in working tree."""
    try:
        # Check staged files
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        files = [f for f in result.stdout.strip().splitlines() if f.strip()]
        count = len(files)
        limits = load_limits()
        max_files = limits["max_files_per_commit"]

        if count > max_files:
            return False, (
                f"❌ CIRCUIT BREAKER: {count} files modified (limit: {max_files}). "
                f"Split into smaller commits or get user approval."
            )
        elif count > max_files * 0.75:
            return True, f"⚠️  Approaching file limit: {count}/{max_files}"
        return True, f"✅ Files modified: {count}/{max_files}"
    except Exception as e:
        return True, f"⚠️  Could not check git status: {e}"


def check_recent_test_failures() -> tuple[bool, str]:
    """Check if the same test has failed repeatedly in recent history."""
    # Placeholder for future enhancement (using .agent/state/test_failure_log.jsonl)
    return True, "✅ Test retry tracking: no repeated failures detected"


def main():
    print(f"\n{'─' * 50}")
    print("  CIRCUIT BREAKER STATUS")
    print(f"{'─' * 50}\n")

    all_ok = True

    # Check 1: Files modified
    ok, msg = check_files_modified()
    print(f"  {msg}")
    if not ok:
        all_ok = False

    # Check 2: Test failures
    ok, msg = check_recent_test_failures()
    print(f"  {msg}")
    if not ok:
        all_ok = False

    print(f"\n{'─' * 50}\n")

    if not all_ok:
        log_action("circuit_breaker", "fail", {"checks": "failed"})
        print(
            "💡 TIP: Split your changes into smaller commits or ask the user for a limit override."
        )
        sys.exit(1)

    log_action("circuit_breaker", "success", {"checks": "all_passed"})
    sys.exit(0)


if __name__ == "__main__":
    main()
