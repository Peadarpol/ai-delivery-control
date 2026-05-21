#!/usr/bin/env python3
"""
Kill Switch Sentinel.
Checks for the presence of .agent/state/HALT.
If found, prints the reason and exits with code 2.
"""

import sys
from pathlib import Path

HALT_PATH = Path(".agent/state/HALT")


def main():
    if HALT_PATH.exists():
        reason = HALT_PATH.read_text(encoding="utf-8").strip() or "No reason provided."
        print("\n" + "!" * 60)
        print("  !!! EXECUTION HALTED BY SENTINEL !!!")
        print(f"  Reason: {reason}")
        print("!" * 60 + "\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
