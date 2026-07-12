#!/usr/bin/env python3
"""
Context Compaction Validator.
Verifies that context-compaction.md exists and contains the 6 required headings.
"""

import sys
from pathlib import Path

# Fix: Ensure UTF-8 encoding for stdout/stderr on Windows to prevent UnicodeEncodeError with emojis
if sys.platform == "win32" and "pytest" not in sys.modules:
    import io

    if (
        hasattr(sys.stdout, "buffer")
        and getattr(sys.stdout, "encoding", "").lower() != "utf-8"
    ):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if (
        hasattr(sys.stderr, "buffer")
        and getattr(sys.stderr, "encoding", "").lower() != "utf-8"
    ):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

def main() -> int:
    skill_dir = Path(__file__).resolve().parent
    compaction_file = skill_dir / "context-compaction.md"

    if not compaction_file.exists():
        print(f"❌ Error: {compaction_file.name} is missing!")
        return 1

    try:
        content = compaction_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Error reading {compaction_file.name}: {e}")
        return 1

    required_headings = [
        "### 1. Completed Tasks",
        "### 2. Verification Findings (mandatory — ALL severities)",
        "### 3. Architectural Decisions",
        "### 4. Failed Experiments",
        "### 5. Remaining Tasks",
        "### 6. Open Questions"
    ]

    missing = []
    for heading in required_headings:
        if heading not in content:
            missing.append(heading)

    if missing:
        print(f"❌ Verification failed for {compaction_file.name}!")
        print("Missing required headings:")
        for m in missing:
            print(f"  - {m}")
        return 1

    print(f"✅ Verification successful for {compaction_file.name}!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
