"""
Unit tests for SQLite schema drift detection and auto-migration (HIB-059).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Add src/scripts to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYS_SCRIPTS = PROJECT_ROOT / "src" / "scripts"

if str(SYS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SYS_SCRIPTS))

import state_persistence


def test_sqlite_schema_drift_auto_migration():
    """Verify legacy sessions table missing columns is auto-migrated via PRAGMA table_info inspection."""
    conn = sqlite3.connect(":memory:")

    # Create legacy sessions table missing session_id and harness_version
    conn.execute(
        """
        CREATE TABLE sessions (
            legacy_id INTEGER PRIMARY KEY,
            project_root TEXT NOT NULL
        );
        """
    )
    conn.commit()

    # Run _ensure_schema on the drifted database
    state_persistence._ensure_schema(conn)

    # Inspect columns
    cursor = conn.execute("PRAGMA table_info(sessions);")
    cols = {row[1] for row in cursor.fetchall()}

    assert "session_id" in cols
    assert "harness_version" in cols
    assert "project_root" in cols


def test_sqlite_schema_drift_idempotency():
    """Verify _ensure_schema is idempotent across repeated calls."""
    conn = sqlite3.connect(":memory:")

    # Run twice
    state_persistence._ensure_schema(conn)
    state_persistence._ensure_schema(conn)

    cursor = conn.execute("PRAGMA table_info(sessions);")
    cols = {row[1] for row in cursor.fetchall()}
    assert "session_id" in cols
