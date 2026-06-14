#!/usr/bin/env python3
"""
Incident-to-Eval Extractor.
Interactive script to create a new golden_dataset.yaml entry from an incident.

Usage: python .agent/evals/incident_to_eval.py
"""

import datetime
import sys
from pathlib import Path

import yaml

# Fix: Ensure UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    import io
    try:
        if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass

DATASET_PATH = Path(__file__).parent / "golden_dataset.yaml"


def main():
    print("\n📋 Golden Dataset — New Entry Wizard\n")

    if not DATASET_PATH.exists():
        data = {"entries": []}
    else:
        with open(DATASET_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {"entries": []}

    entries = data.get("entries", [])
    next_num = len(entries) + 1
    entry_id = f"GD-{next_num:03d}"

    print(f"  New entry ID: {entry_id}")
    source = input(
        "  Incident source (e.g., 'incident-2026-04-17-description'): "
    ).strip()
    description = input("  What went wrong? (one sentence): ").strip()
    trigger = input(
        "  What triggers the failure? (e.g., 'POST /endpoint with X'): "
    ).strip()
    expected = input("  What SHOULD happen? (e.g., '403 Forbidden'): ").strip()
    test_ref = input("  Test reference (file::function): ").strip()
    severity = input("  Severity (HIGH/MEDIUM/LOW): ").strip().upper()

    new_entry = {
        "id": entry_id,
        "source": source,
        "description": description,
        "trigger": trigger,
        "expected_outcome": expected,
        "test_reference": test_ref,
        "severity": severity,
        "date_added": datetime.date.today().isoformat(),
        "added_by": "post-mortem",
    }

    entries.append(new_entry)
    data["entries"] = entries

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )

    print(f"\n  ✅ Entry {entry_id} added to golden_dataset.yaml")
    print(f"  Next: Ensure the test at '{test_ref}' exists and covers this scenario.\n")


if __name__ == "__main__":
    main()
