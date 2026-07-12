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

    def test_uncommitted_spec_no_commit_is_partial(self, clean_state):
        """No commits, but an uncommitted SPEC file exists -> infers partial (HIB-053b)."""
        tmp_path, session_file, ledger_file = clean_state
        
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.get_commits_after", return_value=[]), \
             patch("init_session._uncommitted_spec_changes", return_value=True), \
             patch("init_session.PROJECT_ROOT", tmp_path):
             
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "partial"
            assert "Downgraded to partial (HIB-053b guard)" in note

    def test_committed_spec_is_success(self, clean_state):
        """A committed spec file change with no open tasks -> infers success."""
        tmp_path, session_file, ledger_file = clean_state
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.get_commits_after", return_value=[{"sha": "123", "date": "2026-05-30", "message": "feat: SPEC-001 updated"}]), \
             patch("init_session._uncommitted_spec_changes", return_value=False), \
             patch("init_session.PROJECT_ROOT", tmp_path):
             
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "success"
            assert "All committed changes completed" in note

    @patch("subprocess.run")
    def test_uncommitted_spec_changes_helper(self, mock_run):
        """Verify that _uncommitted_spec_changes runs git status with the correct arguments."""
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = " M docs/planning/specs/SPEC-001.md"
        mock_run.return_value = mock_res
        
        dummy_path = Path("/dummy/specs")
        result = init_session._uncommitted_spec_changes(dummy_path)
        assert result is True
        mock_run.assert_called_once_with(
            ["git", "status", "--porcelain", "--", str(dummy_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

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

    def test_override_success_downgraded_when_no_commits(self, clean_state):
        """outcome_override claims success but no commits exist -> downgraded to partial."""
        tmp_path, session_file, ledger_file = clean_state
        
        import json
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["outcome_override"] = "success"
        data["outcome_override_source"] = "agent_override"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("init_session.get_commits_after", return_value=[]):
             
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "partial"
            assert "Downgraded to partial" in note
            assert "write-before-verify guard" in note

    def test_override_success_accepted_when_commits_exist(self, clean_state):
        """outcome_override claims success and commits exist -> success accepted."""
        tmp_path, session_file, ledger_file = clean_state
        
        import json
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["outcome_override"] = "success"
        data["outcome_override_source"] = "agent_override"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("init_session.get_commits_after", return_value=[{"sha": "abc", "date": "2026-05-30", "message": "fix"}]):
             
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "success"


class TestInitSessionGitStash:
    @patch("subprocess.run")
    def test_stash_created(self, mock_run, capsys):
        """Verify that subprocess.run is called and stash message is printed on changes."""
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "Saved working directory and index state WIP on main"
        mock_run.return_value = mock_res

        init_session._create_session_checkpoint("session-1234567890123")
        captured = capsys.readouterr()
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "git" in args
        assert "stash" in args
        assert "push" in args
        assert "session-1234" in captured.out

    @patch("subprocess.run")
    def test_silent_on_clean(self, mock_run, capsys):
        """Verify that when git stash push returns 'No local changes', we print nothing."""
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "No local changes to save"
        mock_run.return_value = mock_res

        init_session._create_session_checkpoint("session-123")
        captured = capsys.readouterr()
        assert "Checkpoint created" not in captured.out

    @patch("subprocess.run")
    def test_silent_on_missing_session_id(self, mock_run):
        """Verify that we handle empty session_id without exception."""
        # Non-fatal execution test
        init_session._create_session_checkpoint("")


class TestInitSessionGeminiClose:
    def test_gemini_close_consumed(self, clean_state, capsys):
        """Verify that a matching gemini_session_close.json is consumed and merged."""
        tmp_path, session_file, ledger_file = clean_state
        
        # Write matching gemini close file
        close_file = session_file.parent / "gemini_session_close.json"
        close_data = {
            "session_id": "test-session-123",
            "outcome": "partial",
            "outcome_note": "Closed via gemini close protocol test"
        }
        close_file.write_text(json.dumps(close_data), encoding="utf-8")

        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("init_session.get_commits_after", return_value=[]):
            
            outcome, note = init_session.infer_and_close_previous_session()
            captured = capsys.readouterr()
            
            assert outcome == "partial"
            assert note == "Closed via gemini close protocol test"
            assert "Gemini close file consumed" in captured.out
            assert not close_file.exists()

    def test_gemini_close_success_downgraded_when_no_commits(self, clean_state, capsys):
        """gemini_session_close claims success but no commits exist -> downgraded to partial."""
        tmp_path, session_file, ledger_file = clean_state
        
        import json
        close_file = session_file.parent / "gemini_session_close.json"
        close_data = {
            "session_id": "test-session-123",
            "outcome": "success",
            "outcome_note": "Should be downgraded"
        }
        close_file.write_text(json.dumps(close_data), encoding="utf-8")

        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("init_session.get_commits_after", return_value=[]):
            
            outcome, note = init_session.infer_and_close_previous_session()
            
            assert outcome == "partial"
            assert "Downgraded to partial" in note
            assert "write-before-verify guard" in note

    def test_gemini_close_mismatch(self, clean_state, capsys):
        """Verify that a non-matching session close file is not consumed and issues warning."""
        tmp_path, session_file, ledger_file = clean_state
        
        # Write non-matching gemini close file
        close_file = session_file.parent / "gemini_session_close.json"
        close_data = {
            "session_id": "different-session-id",
            "outcome": "success",
            "outcome_note": "Should not be merged"
        }
        close_file.write_text(json.dumps(close_data), encoding="utf-8")

        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("init_session.get_commits_after", return_value=[]):
            
            outcome, note = init_session.infer_and_close_previous_session()
            captured = capsys.readouterr()
            
            # Outcome should fall back to inferred "abandoned" because ID mismatched
            assert outcome == "abandoned"
            assert "Gemini close session_id mismatch" in captured.out
            assert close_file.exists()

class TestInitSessionModelTiers:
    def test_gpt_4o_mini_is_standard(self, clean_state):
        """Verify gpt-4o-mini matches the 'mini' keyword and maps to standard."""
        tmp_path, session_file, ledger_file = clean_state
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("os.environ.get", side_effect=lambda k, d=None: "gpt-4o-mini-2024-07-18" if k == "AGENT_MODEL" else d):
             
            init_session.initialize_session("Harness")
            
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data.get("cost_tier") == "standard"

    def test_gpt_5_6_luna_is_standard(self, clean_state):
        """Verify gpt-5.6-luna matches the 'luna' keyword and maps to standard."""
        tmp_path, session_file, ledger_file = clean_state
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("os.environ.get", side_effect=lambda k, d=None: "gpt-5.6-luna" if k == "AGENT_MODEL" else d):
             
            init_session.initialize_session("Harness")
            
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data.get("cost_tier") == "standard"

    def test_claude_sonnet_is_frontier(self, clean_state):
        """Verify claude-sonnet-4-6 matches the 'sonnet' keyword and maps to frontier."""
        tmp_path, session_file, ledger_file = clean_state
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("os.environ.get", side_effect=lambda k, d=None: "claude-sonnet-4-6" if k == "AGENT_MODEL" else d):
             
            init_session.initialize_session("Harness")
            
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data.get("cost_tier") == "frontier"

    def test_qwen_is_local(self, clean_state):
        """Verify qwen models match the 'qwen' keyword and map to local."""
        tmp_path, session_file, ledger_file = clean_state
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("os.environ.get", side_effect=lambda k, d=None: "qwen2.5-coder-7b" if k == "AGENT_MODEL" else d):
             
            init_session.initialize_session("Harness")
            
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data.get("cost_tier") == "local"

    def test_overlap_guard_warning(self, clean_state, capsys):
        """Verify that an overlapping keyword triggers a warning."""
        tmp_path, session_file, ledger_file = clean_state
        
        overlapping_tiers = {
            "standard": ["flash", "lite"],
            "frontier": ["lite", "pro"]
        }
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("init_session.get_harness_config", side_effect=lambda k, default=None: overlapping_tiers if k == "model_tiers" else ({} if k == "model_routing" else default)), \
             patch("os.environ.get", side_effect=lambda k, d=None: "flash" if k == "AGENT_MODEL" else d):
             
            init_session.initialize_session("Harness")
            
            captured = capsys.readouterr()
            assert "[WARNING] Model tier keyword overlap detected: 'lite' is mapped to both 'standard' and 'frontier'" in captured.out



class TestInitSessionKind:
    def test_default_to_code(self, clean_state):
        """Default-to-code when session_kind is unset — regression, confirms nothing changes for existing behavior."""
        tmp_path, session_file, ledger_file = clean_state
        
        import json
        from unittest.mock import patch
        import init_session
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("os.environ.get", side_effect=lambda k, d=None: None if k == "AGENT_SESSION_KIND" else d):
             
            init_session.initialize_session("Harness")
            
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data.get("session_kind") == "code"

    def test_analysis_no_commits_no_override(self, clean_state):
        """analysis kind, no commits, no override -> partial, not abandoned."""
        tmp_path, session_file, ledger_file = clean_state
        
        import json
        from unittest.mock import patch
        import init_session
        session_data = {
            "session_id": "test-session-123",
            "status": "ACTIVE",
            "start_time": "2026-07-01T12:00:00Z",
            "session_kind": "analysis"
        }
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps(session_data), encoding="utf-8")
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("init_session.get_commits_after", return_value=[]):
            
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "partial"
            assert "Outcome labeled partial" in note

    def test_analysis_no_commits_override_success(self, clean_state):
        """analysis kind, no commits, outcome_override: success -> accepted, stays success."""
        tmp_path, session_file, ledger_file = clean_state
        
        import json
        from unittest.mock import patch
        import init_session
        session_data = {
            "session_id": "test-session-123",
            "status": "ACTIVE",
            "start_time": "2026-07-01T12:00:00Z",
            "session_kind": "analysis",
            "outcome_override": "success",
            "outcome_override_note": "I did some planning"
        }
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps(session_data), encoding="utf-8")
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("init_session.get_commits_after", return_value=[]):
            
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "success"
            assert note == "I did some planning"

    def test_code_no_commits_override_success(self, clean_state):
        """code kind, no commits, outcome_override: success -> still downgraded to partial."""
        tmp_path, session_file, ledger_file = clean_state
        
        import json
        from unittest.mock import patch
        import init_session
        session_data = {
            "session_id": "test-session-123",
            "status": "ACTIVE",
            "start_time": "2026-07-01T12:00:00Z",
            "session_kind": "code",
            "outcome_override": "success",
            "outcome_override_note": "I wrote code but didn't commit"
        }
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps(session_data), encoding="utf-8")
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("init_session.get_commits_after", return_value=[]):
            
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "partial"
            assert "Downgraded to partial" in note

    def test_gemini_close_analysis_success_accepted_when_no_commits(self, clean_state):
        """gemini_session_close claims success, no commits, but session is analysis -> accepted."""
        tmp_path, session_file, ledger_file = clean_state
        
        import json
        from unittest.mock import patch
        import init_session
        session_data = {
            "session_id": "test-session-123",
            "status": "ACTIVE",
            "start_time": "2026-07-01T12:00:00Z",
            "session_kind": "analysis"
        }
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps(session_data), encoding="utf-8")

        close_file = session_file.parent / "gemini_session_close.json"
        close_data = {
            "session_id": "test-session-123",
            "outcome": "success",
            "outcome_note": "I did some planning with Gemini close"
        }
        close_file.write_text(json.dumps(close_data), encoding="utf-8")
        
        with patch("init_session.SESSION_FILE", session_file), \
             patch("init_session.LEDGER_FILE", ledger_file), \
             patch("init_session.STATE_DIR", session_file.parent), \
             patch("init_session.PROJECT_ROOT", tmp_path), \
             patch("init_session.get_commits_after", return_value=[]):
            
            outcome, note = init_session.infer_and_close_previous_session()
            assert outcome == "success"
            assert note == "I did some planning with Gemini close"
            assert not close_file.exists()
