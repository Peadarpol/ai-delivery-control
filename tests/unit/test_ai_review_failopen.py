"""
Unit tests for AI review gate fail-open audit (T1-K-14) and namespace integration safety.
"""

from __future__ import annotations

import pytest
import sys
import unittest.mock
from pathlib import Path

# Add src/scripts to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYS_SCRIPTS = PROJECT_ROOT / "src" / "scripts"

if str(SYS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SYS_SCRIPTS))

import route_decision
import ai_review


def test_ai_review_route_decision_integration_namespace_safety():
    """Verify route_decision get_harness_config is accessible without NameError when ai_review is active."""
    # Ensure get_harness_config is available in route_decision module namespace
    assert hasattr(route_decision, "get_harness_config")
    is_high, patterns = route_decision.classify_commit_risk(["src/scripts/ai_review.py"], [])
    assert isinstance(is_high, bool)


def test_api_unavailable_fail_open_persistence():
    """Verify provider/API unavailability triggers _persist_verdict with fail_open_reason."""
    with unittest.mock.patch.object(ai_review, "_persist_verdict") as mock_persist, \
         unittest.mock.patch.object(ai_review, "_log_gate_skipped") as mock_skip, \
         unittest.mock.patch.object(ai_review, "log_harness_event") as mock_log:

        # Test _handle_api_unavailable
        res = ai_review._handle_api_unavailable("Provider timeout", ["some_file.py"], [])
        assert res == 0
        mock_persist.assert_called_once_with(fail_open_reason="Provider timeout")


def test_large_diff_lines_fail_open_logging():
    """Verify oversized diff exceeding line ceiling logs oversized_diff_blocked event and persists fail_open_reason."""
    config = {"max_diff_lines": 400, "max_diff_chars": 100000, "skip_paths": []}

    with unittest.mock.patch.object(ai_review, "_persist_verdict") as mock_persist, \
         unittest.mock.patch.object(ai_review, "log_harness_event") as mock_log, \
         unittest.mock.patch.object(ai_review, "load_config", return_value=config), \
         unittest.mock.patch.object(ai_review, "get_changed_files", return_value=["foo.py"]), \
         unittest.mock.patch.object(ai_review, "_streaming_size_precheck", return_value=(6000, 100000, True)), \
         unittest.mock.patch.object(ai_review, "get_high_risk_files", return_value=[]), \
         unittest.mock.patch.object(ai_review, "get_pagerank_scores", return_value={}), \
         unittest.mock.patch.object(sys, "argv", ["ai_review.py"]):

        no_preflight = ai_review.PlanOutput(requires_review=True, direct_pass_allowed=False, planner_note="full review")
        with unittest.mock.patch.object(ai_review, "check_preflight_shortcut", return_value=no_preflight):
            with pytest.raises(SystemExit) as exc_info:
                ai_review._run_review()
            assert exc_info.value.code == 1
            mock_persist.assert_called_once()
            assert "OVERSIZED_DIFF_BLOCKED" in mock_persist.call_args[1]["fail_open_reason"]
            assert any(c[0][0].get("event_type") == "oversized_diff_blocked" for c in mock_log.call_args_list)


def test_large_diff_chars_fail_open_logging():
    """Verify oversized diff exceeding char ceiling logs oversized_diff_blocked event and persists fail_open_reason."""
    config = {"max_diff_lines": 1000, "max_diff_chars": 100, "skip_paths": []}

    with unittest.mock.patch.object(ai_review, "_persist_verdict") as mock_persist, \
         unittest.mock.patch.object(ai_review, "log_harness_event") as mock_log, \
         unittest.mock.patch.object(ai_review, "load_config", return_value=config), \
         unittest.mock.patch.object(ai_review, "get_changed_files", return_value=["foo.py"]), \
         unittest.mock.patch.object(ai_review, "_streaming_size_precheck", return_value=(5, 500000, True)), \
         unittest.mock.patch.object(ai_review, "get_high_risk_files", return_value=[]), \
         unittest.mock.patch.object(ai_review, "get_pagerank_scores", return_value={}), \
         unittest.mock.patch.object(sys, "argv", ["ai_review.py"]):

        no_preflight = ai_review.PlanOutput(requires_review=True, direct_pass_allowed=False, planner_note="full review")
        with unittest.mock.patch.object(ai_review, "check_preflight_shortcut", return_value=no_preflight):
            with pytest.raises(SystemExit) as exc_info:
                ai_review._run_review()
            assert exc_info.value.code == 1
            mock_persist.assert_called_once()
            assert "OVERSIZED_DIFF_BLOCKED" in mock_persist.call_args[1]["fail_open_reason"]
            assert any(c[0][0].get("event_type") == "oversized_diff_blocked" for c in mock_log.call_args_list)

