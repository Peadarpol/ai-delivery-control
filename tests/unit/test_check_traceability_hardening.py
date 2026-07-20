"""
Unit tests for check_traceability hardening (T1-K-12, T1-K-13, HIB-061, AT-06).
"""

from __future__ import annotations

import sys
import unittest.mock
from pathlib import Path

# Add .agent/scripts and src/scripts to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_SCRIPTS = PROJECT_ROOT / ".agent" / "scripts"
SYS_SCRIPTS = PROJECT_ROOT / "src" / "scripts"

for p in (str(AGENT_SCRIPTS), str(SYS_SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

import check_traceability


def test_is_root_commit_exemption_predicate():
    """Verify is_root_commit returns True when git rev-list --all --count returns 0."""
    with unittest.mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "0\n"
        mock_run.return_value.returncode = 0
        assert check_traceability.is_root_commit() is True

    with unittest.mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "42\n"
        mock_run.return_value.returncode = 0
        assert check_traceability.is_root_commit() is False


def test_get_worktree_root_anchoring():
    """Verify get_worktree_root resolves top-level path from git rev-parse."""
    with unittest.mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "/path/to/repo\n"
        mock_run.return_value.returncode = 0
        res = check_traceability.get_worktree_root()
        assert isinstance(res, Path)


def test_extract_commit_trailers():
    """Verify extract_commit_trailers parses trailer key-values."""
    trailer_output = "Session-Id: test-session-123\nSigned-by: Agent-007\n"
    with unittest.mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = trailer_output
        mock_run.return_value.returncode = 0
        trailers = check_traceability.extract_commit_trailers("HEAD")
        assert trailers.get("Session-Id") == "test-session-123"
        assert trailers.get("Signed-by") == "Agent-007"


def test_check_branch_no_trace_commits_aggregator():
    """Verify check_branch_no_trace_commits behavior with and without --ack-no-trace."""
    # Case 1: Clean branch
    with unittest.mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = ""
        assert check_traceability.check_branch_no_trace_commits("main") is True

    # Case 2: --no-trace commits present without ack
    with unittest.mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "a1b2c3d feat: --no-trace Quick bug fix\n"
        assert check_traceability.check_branch_no_trace_commits("main", ack_reason=None) is False

    # Case 3: --no-trace commits present with ack and reason truncation
    long_reason = "X" * 300
    with unittest.mock.patch("subprocess.run") as mock_run, \
         unittest.mock.patch("harness_utils.log_harness_event") as mock_log:
        mock_run.return_value.stdout = "a1b2c3d feat: --no-trace Quick bug fix\n"
        res = check_traceability.check_branch_no_trace_commits("main", ack_reason=long_reason)
        assert res is True
        mock_log.assert_called_once()
        payload = mock_log.call_args[0][0]["payload"]
        assert len(payload["reason"]) == 250


def test_spec_regex_matches_versioned_spec_id():
    """Verify spec-ID regex captures full versioned spec ID (e.g. SPEC-v1.4.10-governance-hardening)."""
    import re
    msg = "[SPEC-v1.4.10-governance-hardening] fix: test commit"
    matches = re.findall(
        r"\b(SPEC-v[\d.]+(?:-[\w-]+)?|(?:SPEC|HIB|BUG)-\d+|T1-\w+-\d+)\b",
        msg,
        re.IGNORECASE,
    )
    assert matches == ["SPEC-v1.4.10-governance-hardening"]


def test_spec_regex_matches_legacy_numeric_spec_id():
    """Verify spec-ID regex captures legacy numeric spec ID (e.g. SPEC-001)."""
    import re
    msg = "[SPEC-001] fix: legacy spec commit"
    matches = re.findall(
        r"\b(SPEC-v[\d.]+(?:-[\w-]+)?|(?:SPEC|HIB|BUG)-\d+|T1-\w+-\d+)\b",
        msg,
        re.IGNORECASE,
    )
    assert matches == ["SPEC-001"]


def test_spec_regex_resolves_correct_spec_file_path():
    """Verify check_traceability resolves full spec file path for SPEC-v1.4.10-governance-hardening."""
    msg = "[SPEC-v1.4.10-governance-hardening] test commit"
    with unittest.mock.patch("check_traceability.is_root_commit", return_value=False), \
         unittest.mock.patch("check_traceability.get_commit_message", return_value=msg), \
         unittest.mock.patch("check_traceability.is_doc_or_trivial_diff", return_value=False), \
         unittest.mock.patch("check_traceability.get_config_options", return_value=(PROJECT_ROOT / "docs" / "planning" / "specs", "strict")), \
         unittest.mock.patch("sys.argv", ["check_traceability.py"]):

        # Main should exit 0 because docs/planning/specs/SPEC-v1.4.10-governance-hardening.md exists and is APPROVED
        try:
            check_traceability.main()
        except SystemExit as e:
            assert e.code == 0


def test_spec_regex_no_match_on_unrelated_fid_reference():
    """Verify FID-1 or unrelated tags do not match spec_matches regex."""
    import re
    msg = "fix(gate): fix issue (FID-1)"
    matches = re.findall(
        r"\b(SPEC-v[\d.]+(?:-[\w-]+)?|(?:SPEC|HIB|BUG)-\d+|T1-\w+-\d+)\b",
        msg,
        re.IGNORECASE,
    )
    assert matches == []
