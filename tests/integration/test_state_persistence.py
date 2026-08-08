"""
tests/unit/test_state_persistence.py

Unit tests for src/scripts/state_persistence.py (T1-D-01 / T1-D-02).

Key design principles tested:
  - Lazy schema creation: DB and tables created on first write, not at import.
  - WAL mode is set on every connection.
  - Write failures (busy timeout, permission error) return False and never raise.
  - cleanup_project_rows deletes only rows matching the given project_root.
  - rebuild_from_flat_files reads session_ledger.jsonl and inserts rows.
  - Global DB path falls back to project-local when home dir is not writable.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from src.scripts.state_persistence import (
    _LOCAL_DB_PATH,
    _open_connection,
    _ensure_schema,
    _resolve_db_path,
    sync_session_to_db,
    sync_review_event_to_db,
    sync_spec_acceptance_to_db,
    rebuild_from_flat_files,
    cleanup_project_rows,
)


# ---------------------------------------------------------------------------
# _resolve_db_path
# ---------------------------------------------------------------------------


def test_resolve_db_path_uses_home_when_writable(tmp_path):
    """When the home dir is writable, _resolve_db_path returns the global path."""
    fake_db = tmp_path / ".aisdlc" / "harness.db"

    # _GLOBAL_DB_PATH is evaluated at import time, so patch the constant directly
    with patch("src.scripts.state_persistence._GLOBAL_DB_PATH", fake_db):
        result = _resolve_db_path()

    assert result == fake_db


def test_resolve_db_path_falls_back_to_local_when_home_not_writable(tmp_path, monkeypatch):
    """When the home dir is not writable, falls back to project-local path."""
    def raising_mkdir(self, *args, **kwargs):
        if ".aisdlc" in str(self):
            raise PermissionError("no write access")
        # Allow other paths (e.g. conftest tmp dirs)
        original_mkdir(self, *args, **kwargs)

    original_mkdir = Path.mkdir
    monkeypatch.setattr(Path, "mkdir", raising_mkdir)

    result = _resolve_db_path()
    assert result == _LOCAL_DB_PATH


# ---------------------------------------------------------------------------
# _open_connection / _ensure_schema
# ---------------------------------------------------------------------------


def test_schema_created_on_first_write(tmp_path):
    """_ensure_schema creates all tables in an empty DB."""
    db = tmp_path / "test.db"
    with _open_connection(db) as conn:
        _ensure_schema(conn)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }

    assert "sessions" in tables
    assert "review_events" in tables
    assert "spec_acceptance" in tables
    assert "schema_version" in tables


def test_wal_mode_enabled(tmp_path):
    """Every connection uses WAL journal mode."""
    db = tmp_path / "wal_test.db"
    with _open_connection(db) as conn:
        mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]

    assert mode == "wal"


def test_schema_idempotent(tmp_path):
    """Calling _ensure_schema twice does not raise or duplicate version rows."""
    db = tmp_path / "test.db"
    with _open_connection(db) as conn:
        _ensure_schema(conn)
        _ensure_schema(conn)
        count = conn.execute("SELECT COUNT(*) FROM schema_version;").fetchone()[0]
    assert count == 1


# ---------------------------------------------------------------------------
# sync_session_to_db
# ---------------------------------------------------------------------------


def test_sync_session_to_db_inserts_row(tmp_path):
    """A session dict is written to the sessions table."""
    db = tmp_path / "harness.db"
    session = {
        "session_id": "test-session-001",
        "agent": "TestAgent",
        "start_time": "2026-01-01T00:00:00Z",
        "task_magnitude": "standard",
    }

    result = sync_session_to_db(session, db_path=db)

    assert result is True
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT session_id, agent FROM sessions WHERE session_id = ?;",
            ("test-session-001",),
        ).fetchone()
    assert row is not None
    assert row[0] == "test-session-001"
    assert row[1] == "TestAgent"


def test_sync_session_to_db_upserts(tmp_path):
    """A second write with the same session_id updates the existing row."""
    db = tmp_path / "harness.db"
    session = {"session_id": "upsert-test", "agent": "AgentA", "outcome": None}
    sync_session_to_db(session, db_path=db)

    session["outcome"] = "success"
    session["agent"] = "AgentB"
    sync_session_to_db(session, db_path=db)

    with sqlite3.connect(str(db)) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE session_id = 'upsert-test';"
        ).fetchone()[0]
        outcome = conn.execute(
            "SELECT outcome FROM sessions WHERE session_id = 'upsert-test';"
        ).fetchone()[0]

    assert count == 1, "Should have exactly one row after upsert"
    assert outcome == "success"


def test_sync_session_to_db_returns_false_on_locked_db(tmp_path):
    """A locked/unavailable DB returns False instead of raising."""
    session = {"session_id": "error-test"}

    def bad_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    with patch("sqlite3.connect", side_effect=bad_connect):
        result = sync_session_to_db(session, db_path=tmp_path / "x.db")

    assert result is False


def test_sync_session_to_db_missing_session_id_returns_false(tmp_path):
    """A session dict without session_id is rejected without touching the DB."""
    result = sync_session_to_db({}, db_path=tmp_path / "x.db")
    assert result is False


# ---------------------------------------------------------------------------
# sync_review_event_to_db
# ---------------------------------------------------------------------------


def test_sync_review_event_to_db_inserts_row(tmp_path):
    """A review event dict is appended to the review_events table."""
    db = tmp_path / "harness.db"
    event = {
        "session_id": "s1",
        "timestamp": "2026-01-01T12:00:00",
        "verdict": "PASS",
        "diff_hash": "abc123",
        "token_usage": {"input_tokens": 100, "output_tokens": 50, "call_count": 1},
    }

    result = sync_review_event_to_db(event, db_path=db)
    assert result is True

    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT verdict, input_tokens FROM review_events WHERE session_id = 's1';"
        ).fetchone()
    assert row is not None
    assert row[0] == "PASS"
    assert row[1] == 100


def test_sync_review_event_to_db_returns_false_on_error(tmp_path):
    """Returns False gracefully on DB errors."""
    event = {"session_id": "s2", "verdict": "FAIL"}

    def bad_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    with patch("sqlite3.connect", side_effect=bad_connect):
        result = sync_review_event_to_db(event, db_path=tmp_path / "x.db")

    assert result is False


# ---------------------------------------------------------------------------
# sync_spec_acceptance_to_db
# ---------------------------------------------------------------------------


def test_sync_spec_acceptance_upserts(tmp_path):
    """spec_acceptance upserts correctly — two writes produce one row with latest status."""
    db = tmp_path / "harness.db"

    sync_spec_acceptance_to_db("SPEC-001", "DRAFT", db_path=db)
    sync_spec_acceptance_to_db("SPEC-001", "ACCEPTED", db_path=db)

    with sqlite3.connect(str(db)) as conn:
        rows = conn.execute(
            "SELECT status FROM spec_acceptance WHERE spec_id = 'SPEC-001';"
        ).fetchall()

    assert len(rows) == 1
    assert rows[0][0] == "ACCEPTED"


def test_sync_spec_acceptance_returns_false_on_error(tmp_path):
    """Returns False gracefully on DB errors."""
    def bad_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    with patch("sqlite3.connect", side_effect=bad_connect):
        result = sync_spec_acceptance_to_db("SPEC-999", "ACCEPTED", db_path=tmp_path / "x.db")

    assert result is False


# ---------------------------------------------------------------------------
# rebuild_from_flat_files
# ---------------------------------------------------------------------------


def test_rebuild_from_flat_files(tmp_path):
    """Reads session_ledger.jsonl and inserts rows into sessions table."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    ledger = state_dir / "session_ledger.jsonl"
    ledger.write_text(
        json.dumps({"session_id": "rebuild-001", "agent": "A", "outcome": "success"}) + "\n"
        + json.dumps({"session_id": "rebuild-002", "agent": "B", "outcome": "partial"}) + "\n",
        encoding="utf-8",
    )

    db = tmp_path / "harness.db"
    count = rebuild_from_flat_files(state_dir=state_dir, db_path=db)

    assert count == 2
    with sqlite3.connect(str(db)) as conn:
        ids = {r[0] for r in conn.execute("SELECT session_id FROM sessions;").fetchall()}
    assert ids == {"rebuild-001", "rebuild-002"}


def test_rebuild_from_flat_files_missing_ledger(tmp_path):
    """Returns 0 gracefully when the ledger file does not exist."""
    count = rebuild_from_flat_files(state_dir=tmp_path / "nonexistent", db_path=tmp_path / "x.db")
    assert count == 0


def test_rebuild_from_flat_files_idempotent(tmp_path):
    """Running rebuild twice does not duplicate rows (ON CONFLICT DO NOTHING)."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "session_ledger.jsonl").write_text(
        json.dumps({"session_id": "idem-001", "agent": "A"}) + "\n",
        encoding="utf-8",
    )
    db = tmp_path / "harness.db"
    rebuild_from_flat_files(state_dir=state_dir, db_path=db)
    rebuild_from_flat_files(state_dir=state_dir, db_path=db)

    with sqlite3.connect(str(db)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM sessions;").fetchone()[0]
    assert count == 1


# ---------------------------------------------------------------------------
# cleanup_project_rows
# ---------------------------------------------------------------------------


def test_cleanup_project_rows_only_removes_target_project(tmp_path):
    """cleanup_project_rows deletes only rows for the specified project_root."""
    db = tmp_path / "harness.db"
    project_a = "/projects/alpha"
    project_b = "/projects/beta"

    # Set up schema first
    with _open_connection(db) as conn:
        _ensure_schema(conn)
        conn.execute(
            "INSERT INTO sessions (session_id, project_root, agent) VALUES (?, ?, ?);",
            ("alpha-1", project_a, "A"),
        )
        conn.execute(
            "INSERT INTO sessions (session_id, project_root, agent) VALUES (?, ?, ?);",
            ("beta-1", project_b, "B"),
        )
        conn.commit()

    deleted = cleanup_project_rows(project_root=project_a, db_path=db)

    assert deleted >= 1
    with sqlite3.connect(str(db)) as conn:
        remaining = {r[0] for r in conn.execute("SELECT session_id FROM sessions;").fetchall()}
    assert "alpha-1" not in remaining, "Alpha rows must be deleted"
    assert "beta-1" in remaining, "Beta rows must not be deleted"


def test_cleanup_project_rows_returns_zero_for_missing_db(tmp_path):
    """Returns 0 gracefully when DB doesn't exist."""
    result = cleanup_project_rows(project_root="/some/path", db_path=tmp_path / "nonexistent.db")
    # nonexistent.db gets created with empty tables, so 0 rows deleted is correct
    assert result == 0
