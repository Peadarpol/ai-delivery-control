#!/usr/bin/env python3
"""
.agent/scripts/log_decision.py — Operational CLI for Decision Logging (HIB-082)

CLI wrapper around record_decision() and archive_old_decisions() with standard path bootstrapping.

Usage:
  python .agent/scripts/log_decision.py "Title" "Decision" "Context" "Consequence" [--date YYYY-MM-DD] [--note "Note"]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _find_project_root() -> Path:
    """Locate workspace root containing .git or .agent directory."""
    cwd = Path.cwd().resolve()
    if (cwd / ".agent" / "config.yaml").exists() or (cwd / ".git").exists():
        return cwd
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".agent" / "config.yaml").exists() or (parent / ".git").exists():
            return parent
    return cwd


PROJECT_ROOT = _find_project_root()
_src_scripts = PROJECT_ROOT / "src" / "scripts"
if _src_scripts.exists() and str(_src_scripts) not in sys.path:
    sys.path.insert(0, str(_src_scripts))

try:
    from harness_utils import record_decision, archive_old_decisions
except ImportError:
    print("[LOG_DECISION] Error: Could not import harness_utils.", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append a structured decision to .agent/state/decisions_log.md and run archive maintenance."
    )
    parser.add_argument("title", help="Decision title / summary")
    parser.add_argument("decision", help="What was decided")
    parser.add_argument("context", help="Context / motivation")
    parser.add_argument("consequence", help="Consequence / trade-offs")
    parser.add_argument(
        "--impact",
        required=True,
        choices=["high", "medium", "low"],
        help="Decision impact classification (required)",
    )
    parser.add_argument("--date", help="Optional date in YYYY-MM-DD format", default=None)
    parser.add_argument("--note", help="Optional Note field for extra_fields", default=None)

    args = parser.parse_args()

    extra = {"Note": args.note} if args.note else None

    try:
        record_decision(
            title=args.title,
            decision=args.decision,
            context=args.context,
            consequence=args.consequence,
            date=args.date,
            extra_fields=extra,
            impact=args.impact,
        )
        archive_old_decisions()
        print(f"[OK] Decision logged successfully: '{args.title}'")
        return 0
    except Exception as exc:
        print(f"❌ Error logging decision: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
