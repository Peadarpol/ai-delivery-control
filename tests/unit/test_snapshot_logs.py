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

        init_session._snapshot_live_logs("test-session-123")

        snapshot_dir = state_dir / "snapshots"
        assert snapshot_dir.exists()
        assert (snapshot_dir / "harness_events_snapshot.jsonl").exists()
        assert (snapshot_dir / "ai_review_log_snapshot.jsonl").exists()
        assert "test_event" in (snapshot_dir / "harness_events_snapshot.jsonl").read_text(encoding="utf-8")
