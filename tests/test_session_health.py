"""
Unit Tests for session_health.py
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_ROOT / ".agent" / "scripts"))

# Safely import the module under test
import importlib.util
spec = importlib.util.spec_from_file_location("session_health", WORKSPACE_ROOT / ".agent" / "scripts" / "session_health.py")
session_health = importlib.util.module_from_spec(spec)
sys.modules["session_health"] = session_health
spec.loader.exec_module(session_health)


@pytest.fixture
def mock_session_env(tmp_path):
    """Create a temporary session environment with mocked files."""
    session_file = tmp_path / "session.json"
    events_file = tmp_path / "harness_events.jsonl"
    config_file = tmp_path / "config.yaml"
    review_log_file = tmp_path / "ai-review-log.jsonl"
    halt_file = tmp_path / "HALT"

    session_data = {
        "session_id": "test_session_123456789",
        "start_time": "2026-06-12T10:00:00Z",
        "agent": "Antigravity",
        "token_usage": {
            "input_tokens": 1000,
            "output_tokens": 500
        }
    }
    session_file.write_text(json.dumps(session_data), encoding="utf-8")

    return {
        "session_file": session_file,
        "events_file": events_file,
        "config_file": config_file,
        "review_log_file": review_log_file,
        "halt_file": halt_file,
    }


def test_session_health_exit_0(mock_session_env):
    """Verify session_health.main() completes with no errors when files exist."""
    env = mock_session_env
    with patch("session_health.Path", side_effect=lambda val: env["session_file"] if "session.json" in val else Path(env["session_file"].parent / val.split("/")[-1])), \
         patch("sys.exit") as mock_exit:
        session_health.main()
        mock_exit.assert_not_called()


def test_session_health_headers(mock_session_env, capsys):
    """Verify session_health.main() prints the correct headers and details."""
    env = mock_session_env
    # Add dummy config to test ceiling loading
    env["config_file"].write_text("session_token_budget: 10000\n", encoding="utf-8")
    
    with patch("session_health.Path", side_effect=lambda val: {
        ".agent/state/session.json": env["session_file"],
        ".agent/state/harness_events.jsonl": env["events_file"],
        ".agent/config.yaml": env["config_file"],
        ".ai-review-log.jsonl": env["review_log_file"],
        ".agent/state/HALT": env["halt_file"],
    }.get(val, Path(env["session_file"].parent / val.split("/")[-1]))):
        session_health.main()

    captured = capsys.readouterr()
    assert "Session Health Report" in captured.out
    assert "Session ID   : test_ses…" in captured.out
    assert "Events       : 0 recorded in harness_events.jsonl" in captured.out
    assert "Token usage  : 1,000 in / 500 out" in captured.out
    assert "HALT file    : not detected" in captured.out


def test_session_health_warnings(mock_session_env, capsys):
    """Verify session_health.main() detects same file read 3+ times and repeated errors."""
    env = mock_session_env
    
    # Write event logs with repeated reads and error exceptions
    events = [
        # File reads
        {"session_id": "test_session_123456789", "event_type": "file_read", "payload": {"path": "governance.md"}},
        {"session_id": "test_session_123456789", "event_type": "file_read", "payload": {"path": "governance.md"}},
        {"session_id": "test_session_123456789", "event_type": "file_read", "payload": {"path": "governance.md"}},
        # Repeated errors
        {"session_id": "test_session_123456789", "event_type": "tool_call", "payload": {"error": "FileNotFoundError"}},
        {"session_id": "test_session_123456789", "event_type": "tool_call", "payload": {"error": "FileNotFoundError"}},
    ]
    env["events_file"].write_text("\n".join(json.dumps(evt) for evt in events) + "\n", encoding="utf-8")

    with patch("session_health.Path", side_effect=lambda val: {
        ".agent/state/session.json": env["session_file"],
        ".agent/state/harness_events.jsonl": env["events_file"],
        ".agent/config.yaml": env["config_file"],
        ".ai-review-log.jsonl": env["review_log_file"],
        ".agent/state/HALT": env["halt_file"],
    }.get(val, Path(env["session_file"].parent / val.split("/")[-1]))):
        session_health.main()

    captured = capsys.readouterr()
    assert "Same file read 3+ times: governance.md (3x)" in captured.out
    assert "Repeated error: \"FileNotFoundError\" appeared 2x" in captured.out


def test_session_health_missing_events_file(mock_session_env, capsys):
    """Verify session_health.main() handles missing events file gracefully."""
    env = mock_session_env
    # We do not write/create events_file, and exists() returns False for it
    with patch("session_health.Path", side_effect=lambda val: {
        ".agent/state/session.json": env["session_file"],
        ".agent/state/harness_events.jsonl": Path("non-existent-events-file.jsonl"),
        ".agent/config.yaml": env["config_file"],
        ".ai-review-log.jsonl": env["review_log_file"],
        ".agent/state/HALT": env["halt_file"],
    }.get(val, Path(env["session_file"].parent / val.split("/")[-1]))):
        session_health.main()

    captured = capsys.readouterr()
    assert "Events       : 0 recorded in harness_events.jsonl" in captured.out


def test_session_health_missing_review_log(mock_session_env, capsys):
    """Verify session_health.main() handles missing review log file gracefully."""
    env = mock_session_env
    with patch("session_health.Path", side_effect=lambda val: {
        ".agent/state/session.json": env["session_file"],
        ".agent/state/harness_events.jsonl": env["events_file"],
        ".agent/config.yaml": env["config_file"],
        ".ai-review-log.jsonl": Path("non-existent-review-log.jsonl"),
        ".agent/state/HALT": env["halt_file"],
    }.get(val, Path(env["session_file"].parent / val.split("/")[-1]))):
        session_health.main()

    captured = capsys.readouterr()
    assert "Gate verdicts this session: 0 PASS, 0 FAIL" in captured.out

