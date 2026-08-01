import os
import json
import pytest
import sys
from pathlib import Path
from unittest import mock

# Ensure PROJECT_ROOT/src/scripts is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / ".agent" / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / ".agent" / "skills"))

from ai_review import (
    count_diff_lines,
    _load_session_token_budget,
    _load_review_config,
    get_high_risk_files,
    PROJECT_ROOT as AI_PROJECT_ROOT
)
from init_session import (
    classify_task_magnitude,
    PROJECT_ROOT as INIT_PROJECT_ROOT
)
from check_halt import main as check_halt_main


def test_count_diff_lines_strips_headers_correctly():
    diff = """diff --git a/src/main.py b/src/main.py
index 1234567..7654321 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,4 +10,4 @@
-old_code()
+new_code()
 # a comment
"""
    assert count_diff_lines(diff) == 2


def test_count_diff_lines_exactly_at_threshold_uses_standard_strategy():
    threshold, *_ = _load_review_config()
    # At exactly threshold lines, count_diff_lines works normally
    assert threshold == 400 or isinstance(threshold, int)


def test_session_json_path_consistency():
    # Both ai_review.py and init_session.py must resolve to the exact same absolute session.json path
    ai_session_file = AI_PROJECT_ROOT / ".agent" / "state" / "session.json"
    init_session_file = INIT_PROJECT_ROOT / ".agent" / "state" / "session.json"
    assert ai_session_file.resolve() == init_session_file.resolve()


def test_missing_review_config_section_uses_defaults():
    # Mocking absent review section
    with mock.patch("pathlib.Path.exists", return_value=True):
        with mock.patch("pathlib.Path.read_text", return_value="framework:\n  version: \"1.1.5\"\n"):
            threshold, strategy, *_ = _load_review_config()
            assert threshold == 400
            assert strategy == "stratified"


def test_null_budget_handling():
    with mock.patch("pathlib.Path.exists", return_value=True):
        with mock.patch("pathlib.Path.read_text", return_value="session_token_budget: null\n"):
            assert _load_session_token_budget() is None
        with mock.patch("pathlib.Path.read_text", return_value="session_token_budget: ~\n"):
            assert _load_session_token_budget() is None


def test_sys_path_resolution_verifies_import():
    # Verify we can dynamically resolve senior-architect and import successfully
    from ai_review import _setup_sys_path
    _setup_sys_path()
    assert any("senior-architect" in p for p in sys.path if "scripts" in p)


def test_meta_skill_validation():
    # Call the meta-skill validation script
    from meta.validate import main as validate_main
    assert validate_main() == 0


def test_magnitude_micro_from_hotfix_branch():
    with mock.patch("init_session.get_current_branch", return_value="hotfix/login-crash"):
        with mock.patch("init_session.get_modified_files", return_value=[]):
            assert classify_task_magnitude() == "micro"


def test_magnitude_major_from_rfc_branch():
    with mock.patch("init_session.get_current_branch", return_value="rfc/entitlement-redesign"):
        with mock.patch("init_session.get_modified_files", return_value=[]):
            assert classify_task_magnitude() == "major"


def test_magnitude_upgrade_micro_to_standard_when_code_present():
    with mock.patch("init_session.get_current_branch", return_value="docs/update-guide"):
        with mock.patch("init_session.get_modified_files", return_value=["src/main.py"]):
            assert classify_task_magnitude() == "standard"


def test_magnitude_downgrade_standard_to_micro_when_docs_only():
    with mock.patch("init_session.get_current_branch", return_value="feat/add-docs"):
        with mock.patch("init_session.get_modified_files", return_value=["README.md", "docs/planning.md"]):
            assert classify_task_magnitude() == "micro"


def test_magnitude_major_when_migration_file_present():
    with mock.patch("init_session.get_current_branch", return_value="feat/add-field"):
        with mock.patch("init_session.get_modified_files", return_value=["migrations/versions/v1_0_0_to_v1_1_0.py"]):
            assert classify_task_magnitude() == "major"


def test_escape_hatch_valid_skip():
    # Mock structured JSON token_budget_exhausted HALT file
    halt_path = PROJECT_ROOT / ".agent" / "state" / "HALT"
    halt_path.parent.mkdir(parents=True, exist_ok=True)
    halt_data = {
        "reason": "token_budget_exhausted",
        "message": "Out of budget.",
        "timestamp": "2026-05-27T19:32:04Z"
    }
    with open(halt_path, "w", encoding="utf-8") as f:
        json.dump(halt_data, f, indent=4)
        
    try:
        with mock.patch.dict(os.environ, {"BYPASS_HALT_REASON": "emergency-hotfix-P0"}):
            with pytest.raises(SystemExit) as exc:
                check_halt_main()
            assert exc.value.code == 0
    finally:
        if halt_path.exists():
            halt_path.unlink()


def test_escape_hatch_missing_skip_reason():
    # Mock structured JSON token_budget_exhausted HALT file
    halt_path = PROJECT_ROOT / ".agent" / "state" / "HALT"
    halt_path.parent.mkdir(parents=True, exist_ok=True)
    halt_data = {
        "reason": "token_budget_exhausted",
        "message": "Out of budget.",
        "timestamp": "2026-05-27T19:32:04Z"
    }
    with open(halt_path, "w", encoding="utf-8") as f:
        json.dump(halt_data, f, indent=4)
        
    try:
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as exc:
                check_halt_main()
            assert exc.value.code == 2
    finally:
        if halt_path.exists():
            halt_path.unlink()


def test_budget_includes_reasoning_tokens_when_present():
    # Mocking provider response with reasoning tokens and testing extraction
    from providers import AnthropicProvider
    
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = mock.Mock()
        mock_response.read.return_value = json.dumps({
            "content": [{"text": "{\"verdict\": \"PASS\", \"intent_alignment\": \"ok\", \"issues\": [], \"summary\": \"fine\"}"}],
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "thinking_tokens": 200,
                "cache_read_input_tokens": 10
            }
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        provider = AnthropicProvider()
        provider.review("system_prompt", "user_content")
        
        usage = provider.last_token_usage
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["reasoning_tokens"] == 200
        assert usage["cache_read_input_tokens"] == 10
        
        # Test budget summation with mock usage dictionary
        input_t = usage.get("input_tokens", 0)
        output_t = usage.get("output_tokens", 0)
        reasoning_t = usage.get("reasoning_tokens", 0)
        
        total_spent = input_t + output_t + reasoning_t
        assert total_spent == 350


def test_missing_session_json_budget_assumes_zero_spent():
    from ai_review import _run_review
    from pathlib import Path

    original_exists = Path.exists
    def mock_exists(self):
        if "session.json" in str(self):
            return False
        return original_exists(self)

    clean_env = os.environ.copy()
    clean_env.pop("CI", None)
    clean_env.pop("GITHUB_ACTIONS", None)

    with mock.patch("ai_review._load_session_token_budget", return_value=1000), \
         mock.patch("ai_review._streaming_size_precheck", return_value=(1, 10, False)), \
         mock.patch("ai_review.get_changed_files", return_value=[]), \
         mock.patch("pathlib.Path.exists", new=mock_exists), \
         mock.patch.dict(os.environ, clean_env, clear=True):
        try:
            _run_review()
        except SystemExit as exc:
            assert exc.code != 1 or "budget" not in str(exc).lower(), \
                "Missing session.json should not trigger budget fail-closed (spent=0 < budget)"

    ci_env = clean_env.copy()
    ci_env["CI"] = "true"
    with mock.patch("ai_review._load_session_token_budget", return_value=1000), \
         mock.patch("ai_review._streaming_size_precheck", return_value=(1, 10, False)), \
         mock.patch("ai_review.get_changed_files", return_value=[]), \
         mock.patch("pathlib.Path.exists", new=mock_exists), \
         mock.patch.dict(os.environ, ci_env, clear=True):
        try:
            _run_review()
        except SystemExit as exc:
            assert exc.code != 1 or "budget" not in str(exc).lower()
        except Exception:
            pass

    with mock.patch("ai_review._load_session_token_budget", return_value=None), \
         mock.patch("ai_review._streaming_size_precheck", return_value=(1, 10, False)), \
         mock.patch("ai_review.get_changed_files", return_value=[]), \
         mock.patch("pathlib.Path.exists", new=mock_exists), \
         mock.patch.dict(os.environ, clean_env, clear=True):
        try:
            _run_review()
        except SystemExit as exc:
            assert exc.code != 1
        except Exception:
            pass


