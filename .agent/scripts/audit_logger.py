#!/usr/bin/env python3
"""
Unified Audit Logger for Agent Operations.
Records per-action traces into harness_events.jsonl.
"""

import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

if sys.platform == "win32":
    import io
    try:
        if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass

EVENTS_LOG_PATH = Path(".agent/state/harness_events.jsonl")
SESSION_FILE = Path(".agent/state/session.json")

_SEVERITY_MAP = {"fail": "warn", "error": "critical", "success": "info", "warn": "warn"}


def _get_session_id() -> Optional[str]:
    if not SESSION_FILE.exists():
        return None
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("session_id")
    except Exception:
        return None


def log_action(
    action_type: str,
    status: str,
    details: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> None:
    """
    Append an action trace to harness_events.jsonl.
    Signature is unchanged from the original audit_logger.py.
    """
    try:
        EVENTS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        payload: dict[str, Any] = {
            "action": action_type,
            "status": status,
            "details": details or {},
        }
        if error:
            payload["error"] = error

        record = {
            "schema_version": "1.0",
            "event_type": "action_trace",
            "timestamp_utc": datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat() + "Z",
            "session_id": _get_session_id(),
            "commit_sha": None,
            "agent": agent_id or os.environ.get("AGENT_ID", "audit_logger"),
            "severity": _SEVERITY_MAP.get(status.lower(), "info"),
            "payload": payload,
        }

        with open(EVENTS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    except Exception:
        # Audit logging must never block the primary process
        pass


if __name__ == "__main__":
    log_action("audit_initialization", "success", {"msg": "Audit logger initialized"})
    print(f"✅ Logged test action to {EVENTS_LOG_PATH}")
