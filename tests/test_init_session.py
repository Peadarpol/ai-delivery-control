"""
Unit Tests for init_session.py — session initialization and spec-aware retrospective outcomes.
"""

import os
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_ROOT / ".agent" / "scripts"))

# Safely import the module under test
import importlib.util
spec = importlib.util.spec_from_file_location("init_session", WORKSPACE_ROOT / ".agent" / "scripts" / "init_session.py")
init_session = importlib.util.module_from_spec(spec)
sys.modules["init_session"] = init_session
spec.loader.exec_module(init_session)


@pytest.fixture
def clean_state(tmp_path):
    """Setup a temporary state directory and files."""
    state_dir = tmp_path / ".agent" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    
    session_file = state_dir / "session.json"
    ledger_file = state_dir / "session_ledger.jsonl"
    
    # Pre-populate ACTIVE session
    session_data = {
        "session_id": "test-session-123",
        "start_time": "2026-05-30T00:00:00Z",
        "last_activity": "2026-05-30T00:00:00Z",
        "status": "ACTIVE",
        "agent": "Harness"
    }
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=4)
        
    return tmp_path, session_file, ledger_file


class TestInitSessionSpecAwareness:
    def test_infer_abandoned_when_no_commits_or_specs(self, clean_state):
        """No commits, no spec files -> infers abandoned."""
        tmp_path, session_file, ledger_file = clean_state
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.get_commits_after", return_value=[]), \
             patch("init_session.PROJECT_ROOT", tmp_path):
             
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "abandoned"
            assert "closed with no commits" in note.lower()

    def test_infer_success_on_spec_modified_no_commits(self, clean_state):
        """No commits, but a SPEC file is modified after start_time -> infers success."""
        tmp_path, session_file, ledger_file = clean_state
        
        # Create a spec file modified recently
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        spec_file = specs_dir / "SPEC-001.md"
        spec_file.write_text("Specification content", encoding="utf-8")
        
        # Set file modification time to future relative to session start (2026-05-30 00:00:00)
        future_timestamp = datetime(2026, 5, 30, 1, 0, 0, tzinfo=UTC).timestamp()
        os.utime(spec_file, (future_timestamp, future_timestamp))
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.get_commits_after", return_value=[]), \
             patch("init_session.PROJECT_ROOT", tmp_path):
             
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "success"
            assert "Specification compiled/updated" in note

    def test_explicit_outcome_override_handshake(self, clean_state):
        """If session has outcome_override from BA close handshake -> obeys override."""
        tmp_path, session_file, ledger_file = clean_state
        
        # Append outcome_override to active session
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["outcome_override"] = "success"
        data["outcome_override_source"] = "business_analyst"
        data["outcome_override_note"] = "Explicit override test."
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path):
             
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "success"
            assert note == "Explicit override test."
