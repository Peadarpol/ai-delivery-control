#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Paths
SKILL_MAP_PATH = Path(".agent/config/skill_bdd_map.json")
ACTIVE_CONTEXT_PATH = Path(".agent/state/active_context.md")


def select_tags(skills=None):
    if not SKILL_MAP_PATH.exists():
        print("Error: skill_bdd_map.json missing.", file=sys.stderr)
        return []

    with open(SKILL_MAP_PATH, encoding="utf-8") as f:
        config = json.load(f)

    mapping = config.get("skill_mapping", {})
    default_tags = config.get("default_tags", [])

    if not skills:
        # Try to infer from active_context.md or environment
        # For now, we expect skills to be passed or we use defaults
        skills = []

    selected = set()
    reasons = []

    for skill in skills:
        if skill in mapping:
            tags = mapping[skill]
            selected.update(tags)
            reasons.append(f"{skill} -> {', '.join(tags)}")

    if not selected:
        selected.update(default_tags)
        reasons.append(f"defaults -> {', '.join(default_tags)}")

    return sorted(list(selected)), reasons


def update_context(tags, reasons):
    if not ACTIVE_CONTEXT_PATH.exists():
        return

    tag_str = ", ".join(tags)
    reason_str = "; ".join(reasons)
    entry = f"\n## BDD Gate Selection\n- **Tags**: `{tag_str}`\n- **Triggered by**: {reason_str}\n"

    with open(ACTIVE_CONTEXT_PATH, "a", encoding="utf-8") as f:
        f.write(entry)


def main():
    # Usage: python select_bdd_gate.py <skill1> <skill2> ...
    skills = sys.argv[1:]
    tags, reasons = select_tags(skills)

    if tags:
        # Output the pytest -k or -m string
        # We use -m for tags
        tag_expression = " or ".join(t.replace("@", "") for t in tags)
        print(tag_expression)

        # Update context
        update_context(tags, reasons)


if __name__ == "__main__":
    main()
