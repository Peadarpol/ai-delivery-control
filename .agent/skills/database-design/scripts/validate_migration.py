#!/usr/bin/env python3
"""
Migration Safety Validator

Validates Alembic migrations for safety issues:
- Checks for destructive operations (DROP, DELETE)
- Validates reversibility (downgrade path exists)
- Checks for proper index creation (CONCURRENTLY)
- Warns about NOT NULL additions without defaults

Usage:
    poetry run python .agent/skills/database-design/scripts/validate_migration.py <migration_file>
"""

import re
import sys
from pathlib import Path

# Patterns to check for safety issues
DESTRUCTIVE_PATTERNS = [
    (r"\bDROP\s+TABLE\b", "DROP TABLE - Consider soft delete first"),
    (r"\bDROP\s+COLUMN\b", "DROP COLUMN - Ensure data is backed up"),
    (r"\bDELETE\s+FROM\b", "DELETE FROM - Data will be permanently removed"),
    (r"\bTRUNCATE\b", "TRUNCATE - All data will be removed"),
]

WARNING_PATTERNS = [
    (
        r"ADD\s+COLUMN\s+\w+\s+\w+\s+NOT\s+NULL(?!\s+DEFAULT)",
        "Adding NOT NULL column without DEFAULT - May fail on existing rows",
    ),
    (
        r"CREATE\s+INDEX(?!\s+CONCURRENTLY)",
        "CREATE INDEX without CONCURRENTLY - May lock table",
    ),
    (
        r"ALTER\s+TABLE.*ALTER\s+COLUMN.*TYPE",
        "Column type change - May cause data loss",
    ),
]


def validate_migration(file_path: Path) -> dict:
    """Validate a migration file for safety issues."""
    content = file_path.read_text()

    results = {
        "file": str(file_path),
        "destructive": [],
        "warnings": [],
        "has_downgrade": False,
        "is_reversible": True,
    }

    # Check for downgrade function
    if "def downgrade():" in content:
        results["has_downgrade"] = True

        # Check if downgrade has actual content
        downgrade_match = re.search(
            r"def downgrade\(\):.*?(?=\ndef|\Z)", content, re.DOTALL
        )
        if downgrade_match:
            downgrade_body = downgrade_match.group()
            if "pass" in downgrade_body and downgrade_body.strip().endswith("pass"):
                results["is_reversible"] = False
                results["warnings"].append(
                    "Downgrade function only contains pass - Not reversible"
                )
    else:
        results["is_reversible"] = False
        results["warnings"].append("No downgrade function found")

    # Check for destructive patterns
    for pattern, message in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            results["destructive"].append(message)

    # Check for warning patterns
    for pattern, message in WARNING_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            results["warnings"].append(message)

    return results


def print_results(results: dict):
    """Print validation results."""
    print("=" * 60)
    print("MIGRATION SAFETY VALIDATION")
    print("=" * 60)
    print(f"\nFile: {results['file']}")

    # Reversibility
    if results["is_reversible"]:
        print("\n✅ Migration is reversible")
    else:
        print("\n⚠️  Migration may not be reversible")

    # Destructive operations
    if results["destructive"]:
        print("\n🔴 DESTRUCTIVE OPERATIONS DETECTED:")
        for item in results["destructive"]:
            print(f"    - {item}")

    # Warnings
    if results["warnings"]:
        print("\n🟡 WARNINGS:")
        for item in results["warnings"]:
            print(f"    - {item}")

    # Overall status
    print("\n" + "-" * 40)
    if results["destructive"]:
        print("❌ FAILED - Manual review required before applying")
        return 1
    elif results["warnings"]:
        print("⚠️  PASSED WITH WARNINGS - Review recommended")
        return 0
    else:
        print("✅ PASSED - Migration appears safe")
        return 0


def main():
    if len(sys.argv) < 2:
        # If no file specified, validate all pending migrations
        migrations_dir = Path("alembic/versions")
        if migrations_dir.exists():
            migration_files = sorted(migrations_dir.glob("*.py"))
            if migration_files:
                print(f"Validating {len(migration_files)} migration files...\n")
                all_passed = True
                for f in migration_files:
                    results = validate_migration(f)
                    if results["destructive"] or results["warnings"]:
                        print_results(results)
                        print()
                        if results["destructive"]:
                            all_passed = False
                if all_passed:
                    print("✅ All migrations passed validation")
            else:
                print("No migration files found in alembic/versions/")
        else:
            print("Usage: python validate_migration.py <migration_file>")
            print("   or: python validate_migration.py  (validates all migrations)")
        return

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    results = validate_migration(file_path)
    sys.exit(print_results(results))


if __name__ == "__main__":
    main()
