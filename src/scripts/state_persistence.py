"""
state_persistence.py — SQLite State Persistence (T1-D-01 / T1-D-02)

Mirrors harness flat-file state to a SQLite index at ~/.aisdlc/harness.db.
Flat files in .agent/state/ remain the canonical source of truth; SQLite is a
derived, rebuildable index used for cross-project querying and analytics only.

Locking notes (addresses T1-N-02 concurrency concern):
  - WAL journal mode is enabled so readers never block writers and vice-versa.
  - busy_timeout=10 000 ms (10 s) is passed at connect time so concurrent writes
    from parallel sessions queue rather than raising OperationalError immediately.
  - All writes are wrapped in a try/except so a locked or missing DB never raises
    an exception in the caller — it logs a warning and returns gracefully.
  - SQLite's own WAL locking is sufficient for the single-writer-per-row access
    pattern here; no external _lock_file wrapper is needed (contrast with JSONL
    files which require _lock_file because Python's file append is not atomic on
    Windows without a lock).

Dependency disclosure:
  - No new pip dependencies: uses Python stdlib sqlite3 only.
  - Writes to ~/.aisdlc/harness.db (shared across all harness-managed projects
    on this machine). Falls back to .agent/state/harness.db in the project root
    if the home-directory path is inaccessible.
  - Flat files in .agent/state/ are always the authoritative source; the SQLite
    DB can be deleted and rebuilt from flat files at any time.
  - Not suitable for ephemeral CI environments or containers without a persistent
    $HOME. In those environments the fallback project-local path is used instead.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_GLOBAL_DB_PATH = Path.home() / ".aisdlc" / "harness.db"
_LOCAL_DB_PATH = Path(".agent") / "state" / "harness.db"

_SCHEMA_VERSION = 1
_CONNECT_TIMEOUT_SECS = 10.0  # WAL busy-wait ceiling before giving up


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_db_path() -> Path:
    """Return the DB path: global home path when writable, project-local fallback."""
    try:
        _GLOBAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Quick write-access probe without creating the DB file itself
        probe = _GLOBAL_DB_PATH.parent / ".write_probe"
        probe.touch()
        probe.unlink()
        return _GLOBAL_DB_PATH
    except Exception:
        return _LOCAL_DB_PATH


def _open_connection(db_path: Path) -> sqlite3.Connection:
    """Open a WAL-mode connection with busy timeout.

    WAL mode ensures concurrent readers and a single writer can coexist without
    blocking.  busy_timeout queues writers for up to _CONNECT_TIMEOUT_SECS before
    raising OperationalError — callers catch that and degrade gracefully.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=_CONNECT_TIMEOUT_SECS)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create schema tables if they do not exist (lazy initialization)."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version  INTEGER NOT NULL,
            applied  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            session_id      TEXT    PRIMARY KEY,
            project_root    TEXT    NOT NULL,
            agent           TEXT,
            start_time      TEXT,
            end_time        TEXT,
            outcome         TEXT,
            outcome_source  TEXT,
            outcome_note    TEXT,
            task_magnitude  TEXT,
            harness_version TEXT,
            created_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS review_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT,
            project_root    TEXT    NOT NULL,
            timestamp_utc   TEXT,
            verdict         TEXT,
            diff_hash       TEXT,
            input_tokens    INTEGER DEFAULT 0,
            output_tokens   INTEGER DEFAULT 0,
            call_count      INTEGER DEFAULT 0,
            created_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS spec_acceptance (
            spec_id         TEXT    NOT NULL,
            project_root    TEXT    NOT NULL,
            status          TEXT    NOT NULL,
            recorded_at     TEXT    DEFAULT (datetime('now')),
            PRIMARY KEY (spec_id, project_root)
        );
        """
    )

    # Inspect all tables for schema drift (HIB-059 & HIB-077)
    table_schemas = {
        "sessions": {
            "session_id": "TEXT",
            "project_root": "TEXT",
            "agent": "TEXT",
            "start_time": "TEXT",
            "end_time": "TEXT",
            "outcome": "TEXT",
            "outcome_source": "TEXT",
            "outcome_note": "TEXT",
            "task_magnitude": "TEXT",
            "harness_version": "TEXT",
        },
        "review_events": {
            "session_id": "TEXT",
            "project_root": "TEXT",
            "timestamp_utc": "TEXT",
            "verdict": "TEXT",
            "diff_hash": "TEXT",
            "input_tokens": "INTEGER DEFAULT 0",
            "output_tokens": "INTEGER DEFAULT 0",
            "call_count": "INTEGER DEFAULT 0",
        },
        "spec_acceptance": {
            "spec_id": "TEXT",
            "project_root": "TEXT",
            "status": "TEXT",
        },
    }

    for table_name, req_cols in table_schemas.items():
        try:
            cursor = conn.execute(f"PRAGMA table_info({table_name});")
            existing_cols = {row[1] for row in cursor.fetchall()}
            for col_name, col_type in req_cols.items():
                if col_name not in existing_cols:
                    try:
                        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};")
                    except sqlite3.OperationalError:
                        pass
        except Exception:
            pass

    # Insert schema version row if missing
    row = conn.execute("SELECT version FROM schema_version LIMIT 1;").fetchone()
    if row is None:
        from datetime import UTC, datetime

        conn.execute(
            "INSERT INTO schema_version (version, applied) VALUES (?, ?);",
            (_SCHEMA_VERSION, datetime.now(UTC).isoformat()),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Project root detection
# ---------------------------------------------------------------------------


def _get_project_root() -> str:
    """Return the project root as a string, best-effort."""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return str(Path.cwd())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sync_session_to_db(session_data: dict[str, Any], db_path: Path | None = None) -> bool:
    """Upsert a session record into the SQLite index.

    Parameters
    ----------
    session_data:
        The session dict from session.json (must contain ``session_id``).
    db_path:
        Override the DB path — used in tests. If None, auto-resolved.

    Returns
    -------
    bool
        True if the write succeeded, False if it was skipped due to an error.
    """
    if not session_data.get("session_id"):
        return False

    db_path = db_path or _resolve_db_path()
    project_root = _get_project_root()

    try:
        with _open_connection(db_path) as conn:
            _ensure_schema(conn)
            token_usage = session_data.get("token_usage", {})
            conn.execute(
                """
                INSERT INTO sessions
                    (session_id, project_root, agent, start_time, end_time,
                     outcome, outcome_source, outcome_note, task_magnitude,
                     harness_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    end_time        = excluded.end_time,
                    outcome         = excluded.outcome,
                    outcome_source  = excluded.outcome_source,
                    outcome_note    = excluded.outcome_note,
                    task_magnitude  = excluded.task_magnitude,
                    harness_version = excluded.harness_version;
                """,
                (
                    session_data["session_id"],
                    project_root,
                    session_data.get("agent"),
                    session_data.get("start_time"),
                    session_data.get("end_time"),
                    session_data.get("outcome"),
                    session_data.get("outcome_source"),
                    session_data.get("outcome_note"),
                    session_data.get("task_magnitude"),
                    session_data.get("harness_version"),
                ),
            )
            conn.commit()
        return True
    except sqlite3.OperationalError as exc:
        # Busy timeout or DB locked — log and degrade gracefully
        logger.warning("[STATE_PERSISTENCE] SQLite write skipped (busy/locked): %s", exc)
        return False
    except Exception as exc:
        logger.warning("[STATE_PERSISTENCE] SQLite write failed: %s", exc)
        return False


def sync_review_event_to_db(event_data: dict[str, Any], db_path: Path | None = None) -> bool:
    """Insert a review event record into the SQLite index.

    Returns True on success, False on any error (never raises).
    """
    db_path = db_path or _resolve_db_path()
    project_root = _get_project_root()

    try:
        with _open_connection(db_path) as conn:
            _ensure_schema(conn)
            token_usage = event_data.get("token_usage", {})
            conn.execute(
                """
                INSERT INTO review_events
                    (session_id, project_root, timestamp_utc, verdict,
                     diff_hash, input_tokens, output_tokens, call_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event_data.get("session_id"),
                    project_root,
                    event_data.get("timestamp"),
                    event_data.get("verdict"),
                    event_data.get("diff_hash"),
                    token_usage.get("input_tokens", 0),
                    token_usage.get("output_tokens", 0),
                    token_usage.get("call_count", 0),
                ),
            )
            conn.commit()
        return True
    except sqlite3.OperationalError as exc:
        logger.warning("[STATE_PERSISTENCE] SQLite review event skipped (busy/locked): %s", exc)
        return False
    except Exception as exc:
        logger.warning("[STATE_PERSISTENCE] SQLite review event failed: %s", exc)
        return False


def sync_spec_acceptance_to_db(
    spec_id: str, status: str, db_path: Path | None = None
) -> bool:
    """Upsert a spec acceptance status into the SQLite index.

    Returns True on success, False on any error (never raises).
    """
    db_path = db_path or _resolve_db_path()
    project_root = _get_project_root()

    try:
        with _open_connection(db_path) as conn:
            _ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO spec_acceptance (spec_id, project_root, status)
                VALUES (?, ?, ?)
                ON CONFLICT(spec_id, project_root) DO UPDATE SET
                    status      = excluded.status,
                    recorded_at = datetime('now');
                """,
                (spec_id, project_root, status),
            )
            conn.commit()
        return True
    except sqlite3.OperationalError as exc:
        logger.warning("[STATE_PERSISTENCE] SQLite spec acceptance skipped (busy/locked): %s", exc)
        return False
    except Exception as exc:
        logger.warning("[STATE_PERSISTENCE] SQLite spec acceptance failed: %s", exc)
        return False


def rebuild_from_flat_files(
    state_dir: Path = Path(".agent/state"), db_path: Path | None = None
) -> int:
    """Rebuild the SQLite index from flat-file sources of truth.

    Reads session_ledger.jsonl to repopulate the sessions table.
    Returns the number of rows inserted/updated.
    """
    db_path = db_path or _resolve_db_path()
    project_root = _get_project_root()
    ledger_path = state_dir / "session_ledger.jsonl"
    if not ledger_path.exists():
        return 0

    count = 0
    try:
        with _open_connection(db_path) as conn:
            _ensure_schema(conn)
            lines = ledger_path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    conn.execute(
                        """
                        INSERT INTO sessions
                            (session_id, project_root, agent, start_time,
                             outcome, outcome_source, outcome_note,
                             task_magnitude, harness_version)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(session_id) DO NOTHING;
                        """,
                        (
                            entry.get("session_id", ""),
                            project_root,
                            entry.get("agent"),
                            entry.get("date"),
                            entry.get("outcome"),
                            entry.get("outcome_source"),
                            entry.get("outcome_note"),
                            entry.get("task_magnitude"),
                            entry.get("harness_version"),
                        ),
                    )
                    count += 1
                except Exception:
                    continue
            conn.commit()
    except Exception as exc:
        logger.warning("[STATE_PERSISTENCE] Rebuild from flat files failed: %s", exc)

    return count


def cleanup_project_rows(project_root: str | None = None, db_path: Path | None = None) -> int:
    """Delete all rows for the given project_root from the SQLite index.

    Used by uninstall.py for selective row-level cleanup.
    Returns the number of rows deleted.
    """
    db_path = db_path or _resolve_db_path()
    project_root = project_root or _get_project_root()

    deleted = 0
    try:
        with _open_connection(db_path) as conn:
            _ensure_schema(conn)
            for table in ("sessions", "review_events", "spec_acceptance"):
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE project_root = ?;", (project_root,)
                )
                deleted += cur.rowcount
            conn.commit()
    except Exception as exc:
        logger.warning("[STATE_PERSISTENCE] Cleanup failed: %s", exc)

    return deleted
