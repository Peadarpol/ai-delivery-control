"""
Unit tests for HIB-063 snapshot-on-close live log archiving mechanism.
"""

from __future__ import annotations

import sys
import unittest.mock
from pathlib import Path

# Add .agent/scripts to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_SCRIPTS = PROJECT_ROOT / ".agent" / "scripts"

if str(AGENT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(AGENT_SCRIPTS))

import init_session


def test_snapshot_live_logs_copies_files(tmp_path):
    """Verify _snapshot_live_logs creates snapshots in STATE_DIR/snapshots on clean session close."""
    state_dir = tmp_path / ".agent" / "state"
    state_dir.mkdir(parents=True)
    
    events_file = state_dir / "harness_events.jsonl"
    events_file.write_text('{"event": "test_event"}\n', encoding="utf-8")
    
    review_file = tmp_path / ".ai-review-log.jsonl"
    review_file.write_text('{"verdict": "PASS"}\n', encoding="utf-8")

    with unittest.mock.patch("init_session.STATE_DIR", state_dir), \
         unittest.mock.patch("init_session.PROJECT_ROOT", tmp_path):

        session_id = "test-session-123"
        init_session._snapshot_live_logs(session_id)

        snapshot_dir = state_dir / "snapshots"
        assert snapshot_dir.exists()
        assert (snapshot_dir / f"harness_events_{session_id}.jsonl").exists()
        assert (snapshot_dir / f"ai_review_log_{session_id}.jsonl").exists()
        assert "test_event" in (snapshot_dir / f"harness_events_{session_id}.jsonl").read_text(encoding="utf-8")


def test_snapshot_live_logs_skips_empty_files(tmp_path):
    """Verify _snapshot_live_logs skips zero-byte files."""
    state_dir = tmp_path / ".agent" / "state"
    state_dir.mkdir(parents=True)
    
    events_file = state_dir / "harness_events.jsonl"
    events_file.write_text('', encoding="utf-8")  # 0 bytes

    review_file = tmp_path / ".ai-review-log.jsonl"
    review_file.write_text('', encoding="utf-8")  # 0 bytes

    with unittest.mock.patch("init_session.STATE_DIR", state_dir), \
         unittest.mock.patch("init_session.PROJECT_ROOT", tmp_path):

        session_id = "test-empty-session"
        init_session._snapshot_live_logs(session_id)

        target_events = state_dir / "snapshots" / f"harness_events_{session_id}.jsonl"
        target_review = state_dir / "snapshots" / f"ai_review_log_{session_id}.jsonl"
        assert not target_events.exists()
        assert not target_review.exists()
