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

# Ensure src/scripts is in sys.path for harness_utils
_bootstrap_path = Path(__file__).resolve()
_bootstrap_root = None
for _p in [_bootstrap_path] + list(_bootstrap_path.parents):
    if (_p / ".git").exists() or (_p / ".agent").exists():
        _bootstrap_root = _p
        break
if _bootstrap_root and str(_bootstrap_root / "src" / "scripts") not in sys.path:
    sys.path.insert(0, str(_bootstrap_root / "src" / "scripts"))

try:
    from src.scripts.harness_utils import _find_project_root
except ImportError:
    from harness_utils import _find_project_root


PROJECT_ROOT = _find_project_root()
_src_scripts = PROJECT_ROOT / "src" / "scripts"
if _src_scripts.exists() and str(_src_scripts) not in sys.path:
    sys.path.insert(0, str(_src_scripts))

import harness_utils

EVENTS_LOG_PATH = PROJECT_ROOT / ".agent" / "state" / "harness_events.jsonl"
SESSION_FILE = PROJECT_ROOT / ".agent" / "state" / "session.json"

_SEVERITY_MAP = {"fail": "warn", "error": "critical", "success": "info", "warn": "warn"}


def _get_session_id() -> str:
    if not SESSION_FILE.exists():
        return "pre-session-init"
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("session_id") or "pre-session-init"
    except Exception:
        return "pre-session-init"


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
