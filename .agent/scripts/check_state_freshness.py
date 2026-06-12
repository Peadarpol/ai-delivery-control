#!/usr/bin/env python3
"""Pre-compaction check: verify session state files are recently updated.

Exits 0 always (non-blocking) — prints a warning if state files appear stale,
giving the agent a chance to update them before compaction destroys context.
"""
import sys
import time
from pathlib import Path

STATE_FILES = [
    ".agent/state/active_context.md",
    ".agent/state/last_session_summary.md",
    ".agent/state/decisions_log.md",
]

STALE_THRESHOLD_SECONDS = 3600  # 1 hour


def main():
    now = time.time()
    stale = []
    missing = []

    for f in STATE_FILES:
        p = Path(f)
        if not p.exists():
            missing.append(f)
            continue
        age = now - p.stat().st_mtime
        if age > STALE_THRESHOLD_SECONDS:
            stale.append((f, int(age / 60)))

    if missing:
        print(f"[PRE-COMPACTION WARNING] State files not found: {', '.join(missing)}")
    if stale:
        for f, age_min in stale:
            print(f"[PRE-COMPACTION WARNING] {f} not updated in {age_min} minutes")
    if stale or missing:
        print(
            "[PRE-COMPACTION] Consider updating session state files before "
            "compaction — see AGENTS.md §6 (session close protocol)."
        )

    sys.exit(0)  # never block compaction


if __name__ == "__main__":
    main()
