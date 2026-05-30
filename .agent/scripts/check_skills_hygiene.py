#!/usr/bin/env python3
import sys
from pathlib import Path

SKILLS_DIR = Path(".agent/skills")

ALWAYS_LOADED_LINE_CEILING = 300

ALWAYS_LOADED_DOCS = [
    Path(".agent/AGENTS.md"),
    Path(".agent/governance.md"),
    Path("src/scripts/review_context_universal.md"),
]


def run_hygiene_check() -> int:
    """Scans .agent/skills/ for temporary execution scripts and banned test files."""
    if not SKILLS_DIR.exists():
        print(f"[INFO] Skills directory {SKILLS_DIR} does not exist. Skipping.")
        return 0

    print("=== Agent Skills Hygiene Scan ===")

    # 1. Proactive cleanup of playwright-skill temporary execution files (Row 12)
    playwright_temp_pattern = ".temp-execution-*.js"
    temp_files = list(SKILLS_DIR.glob(f"playwright-skill/{playwright_temp_pattern}"))
    for tf in temp_files:
        try:
            tf.unlink()
            print(f"[CLEANUP] Deleted temporary execution file: {tf.name}")
        except Exception as e:
            print(f"[WARNING] Failed to delete {tf}: {e}")

    # 2. Scanning for banned execution/test files (Row 14)
    violations = []

    # Exclude directories
    exclude_dirs = {"node_modules", ".git", "__pycache__"}

    # Banned file patterns (row 14 backlog requirements)
    banned_patterns = {"*.test.js", "*.spec.js", "conftest.py", "test_*.py"}

    # Custom recursive walk to safely ignore excluded folders (like node_modules)
    for path in SKILLS_DIR.rglob("*"):
        if not path.is_file():
            continue

        # Check if the file is within an excluded directory
        parts = path.parts
        if any(d in parts for d in exclude_dirs):
            continue

        # Check against banned patterns
        for pattern in banned_patterns:
            if path.match(pattern):
                violations.append(path)
                break

    if violations:
        print("\n[CRITICAL] Security / Supply Chain Violation detected!")
        print("Found banned test/execution files inside the agent skills directory.")
        print("These files pose a supply chain risk and must be removed or renamed.")
        print("-" * 60)
        for v in violations:
            print(f"  [BANNED] {v}")
        print("-" * 60)
        print("Remediation:")
        print(
            "  - If these are examples, rename them so they do not start/end with banned patterns (e.g. use prefix 'example_' instead of 'test_')"
        )
        print("  - If they are orphaned debug/temp execution scripts, delete them.")
        return 1

    # 3. Always-loaded document line ceiling check
    ceiling_warnings = []
    for doc_path in ALWAYS_LOADED_DOCS:
        if not doc_path.exists():
            continue
        line_count = len(doc_path.read_text(encoding="utf-8", errors="replace").splitlines())
        if line_count > ALWAYS_LOADED_LINE_CEILING:
            ceiling_warnings.append((doc_path, line_count))

    if ceiling_warnings:
        print(f"\n[WARNING] Always-loaded documents exceed {ALWAYS_LOADED_LINE_CEILING}-line ceiling:")
        for doc_path, line_count in ceiling_warnings:
            print(
                f"  [CEILING] {doc_path} — {line_count} lines "
                f"(ceiling: {ALWAYS_LOADED_LINE_CEILING}). "
                "Prune or archive content to keep agent attention focused."
            )

    print("Skills hygiene check complete. No violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(run_hygiene_check())
