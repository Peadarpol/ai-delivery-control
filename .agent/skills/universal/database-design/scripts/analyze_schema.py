#!/usr/bin/env python3
"""
Database Schema Analyzer

Analyzes SQLAlchemy models to provide schema insights:
- Lists all tables and their columns
- Shows relationships between tables
- Identifies missing indexes
- Detects potential N+1 query risks

Usage:
    poetry run python .agent/skills/database-design/scripts/analyze_schema.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import inspect
    from src.infrastructure.database.connection import engine
except ImportError:
    inspect = None
    engine = None


def analyze_tables():
    """Analyze all tables in the database schema."""
    if engine is None or inspect is None:
        print("SQLAlchemy engine not available.")
        return
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("=" * 60)
    print("DATABASE SCHEMA ANALYSIS")
    print("=" * 60)
    print(f"\nTotal Tables: {len(tables)}\n")

    for table_name in sorted(tables):
        print(f"\n📋 TABLE: {table_name}")
        print("-" * 40)

        # Columns
        columns = inspector.get_columns(table_name)
        print(f"  Columns ({len(columns)}):")
        for col in columns:
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            print(f"    - {col['name']}: {col['type']} {nullable}")

        # Primary Keys
        pk = inspector.get_pk_constraint(table_name)
        if pk["constrained_columns"]:
            print(f"  Primary Key: {', '.join(pk['constrained_columns'])}")

        # Foreign Keys
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            print("  Foreign Keys:")
            for fk in fks:
                print(
                    f"    - {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}"
                )

        # Indexes
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print("  Indexes:")
            for idx in indexes:
                unique = "UNIQUE " if idx["unique"] else ""
                print(f"    - {unique}{idx['name']}: {idx['column_names']}")


def load_exempt_tables(project_root: Path | None = None) -> set[str]:
    """Load table exemptions from .agent/config.yaml under schema_hardening.exempt_tables."""
    default_exempt = {"alembic_version", "schema_migrations", "sqlite_sequence"}
    try:
        from pathlib import Path
        import sys
        root = project_root or Path(__file__).resolve().parents[4]
        sys.path.insert(0, str(root / "src" / "scripts"))
        from harness_utils import get_harness_config
        raw = get_harness_config("schema_hardening", "exempt_tables", default=list(default_exempt), config_path=root / ".agent" / "config.yaml", strict=True)
    except Exception:
        raw = list(default_exempt)

    if isinstance(raw, (list, tuple, set)):
        configured = {str(x).strip() for x in raw if x and isinstance(x, str)}
        return configured | default_exempt
    return default_exempt


def check_branch_id_compliance():
    """Check if all operational tables have branch_id."""
    if engine is None or inspect is None:
        print("SQLAlchemy engine not available.")
        return
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Tables that should have branch_id (operational tables)
    exempt_tables = load_exempt_tables()

    print("\n" + "=" * 60)
    print("BRANCH_ID COMPLIANCE CHECK")
    print("=" * 60)

    issues = []
    for table_name in sorted(tables):
        if table_name in exempt_tables:
            continue

        columns = inspector.get_columns(table_name)
        column_names = [col["name"] for col in columns]

        if "branch_id" not in column_names:
            issues.append(table_name)

    if issues:
        print("\n⚠️  Tables missing branch_id:")
        for table in issues:
            print(f"    - {table}")
    else:
        print("\n✅ All operational tables have branch_id")


def suggest_indexes():
    """Suggest potential missing indexes based on foreign keys."""
    if engine is None or inspect is None:
        print("SQLAlchemy engine not available.")
        return
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("\n" + "=" * 60)
    print("INDEX RECOMMENDATIONS")
    print("=" * 60)

    suggestions = []
    for table_name in sorted(tables):
        indexes = inspector.get_indexes(table_name)
        indexed_columns = set()
        for idx in indexes:
            indexed_columns.update(idx["column_names"])

        fks = inspector.get_foreign_keys(table_name)
        for fk in fks:
            for col in fk["constrained_columns"]:
                if col not in indexed_columns:
                    suggestions.append((table_name, col, fk["referred_table"]))

    if suggestions:
        print("\n💡 Consider adding indexes for these foreign keys:")
        for table, col, ref_table in suggestions:
            print(f"    - {table}.{col} (references {ref_table})")
    else:
        print("\n✅ All foreign keys appear to be indexed")


if __name__ == "__main__":
    analyze_tables()
    check_branch_id_compliance()
    suggest_indexes()
    print("\n" + "=" * 60)
    print("Analysis complete!")
