"""
Unit Tests for harness_health.py
"""

import sys
import datetime
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_ROOT / ".agent" / "scripts"))

# Safely import the module under test while bypassing win32 console redirection
import importlib.util
with patch("sys.platform", "linux"):
    spec = importlib.util.spec_from_file_location("harness_health", WORKSPACE_ROOT / ".agent" / "scripts" / "harness_health.py")
    harness_health = importlib.util.module_from_spec(spec)
    sys.modules["harness_health"] = harness_health
    spec.loader.exec_module(harness_health)


@pytest.fixture
def mock_proposals_dir(tmp_path):
    """Create a temporary directory for proposals."""
    proposals_dir = tmp_path / "dream_proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    return proposals_dir


# --- Proposal Staleness Tests (3 tests: clean, warn, critical) ---

def test_staleness_clean(mock_proposals_dir, capsys):
    """Verify clean status when there are no open proposals, or all are recent."""
    # Test with no proposals
    with patch("harness_health.Path", return_value=mock_proposals_dir):
        harness_health.report_dream_proposal_staleness()
    captured = capsys.readouterr()
    assert "CLEAN (no open proposals)" in captured.out

    # Test with recent proposal (e.g. 5 days old)
    recent_prop = mock_proposals_dir / "skill__rule__open.md"
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    recent_prop.write_text(f"Generated: {today_str}\n", encoding="utf-8")

    with patch("harness_health.Path", return_value=mock_proposals_dir):
        harness_health.report_dream_proposal_staleness()
    captured = capsys.readouterr()
    assert "HEALTHY" in captured.out
    assert "WARN" not in captured.out
    assert "CRITICAL" not in captured.out


def test_staleness_warn(mock_proposals_dir, capsys):
    """Verify warning status when a proposal is between 30 and 90 days old."""
    warn_prop = mock_proposals_dir / "skill__rule__open.md"
    thirty_five_days_ago = (datetime.datetime.now() - datetime.timedelta(days=35)).date()
    date_str = thirty_five_days_ago.strftime("%Y-%m-%d")
    warn_prop.write_text(f"Generated: {date_str}\n", encoding="utf-8")

    with patch("harness_health.Path", return_value=mock_proposals_dir):
        harness_health.report_dream_proposal_staleness()
    captured = capsys.readouterr()
    assert "WARN: skill__rule__open.md" in captured.out
    assert "35d old" in captured.out
    assert "CRITICAL" not in captured.out


def test_staleness_critical(mock_proposals_dir, capsys):
    """Verify critical status when a proposal is older than 90 days."""
    critical_prop = mock_proposals_dir / "skill__rule__open.md"
    ninety_five_days_ago = (datetime.datetime.now() - datetime.timedelta(days=95)).date()
    date_str = ninety_five_days_ago.strftime("%Y-%m-%d")
    critical_prop.write_text(f"Generated: {date_str}\n", encoding="utf-8")

    with patch("harness_health.Path", return_value=mock_proposals_dir):
        harness_health.report_dream_proposal_staleness()
    captured = capsys.readouterr()
    assert "CRITICAL: skill__rule__open.md" in captured.out
    assert "95d old" in captured.out
    assert "WARN:" not in captured.out


# --- State File Size Checks (3 tests: healthy, warn, critical) ---

def test_file_sizes_healthy(capsys):
    """Verify status is HEALTHY when all monitored files are under threshold size."""
    def mock_path_constructor(val):
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 10 * 1024  # 10KB
        return mock_path
    
    with patch("harness_health.Path", side_effect=mock_path_constructor):
        harness_health.report_state_file_sizes()
        
    captured = capsys.readouterr()
    assert "HEALTHY" in captured.out
    assert "WARN" not in captured.out
    assert "CRITICAL" not in captured.out


def test_file_sizes_warn(capsys):
    """Verify warning status when at least one file is between warn and critical size."""
    def mock_path_constructor(val):
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        if "repo_graph_cache.json" in str(val).replace("\\", "/"):
            mock_path.stat.return_value.st_size = int(3 * 1024 * 1024)  # 3MB
        else:
            mock_path.stat.return_value.st_size = 10 * 1024  # 10KB
        return mock_path

    with patch("harness_health.Path", side_effect=mock_path_constructor):
        harness_health.report_state_file_sizes()
        
    captured = capsys.readouterr()
    assert "WARN: .agent/state/repo_graph_cache.json" in captured.out
    assert "3.0MB" in captured.out
    assert "CRITICAL" not in captured.out


def test_file_sizes_critical(capsys):
    """Verify critical status when at least one file is above critical size."""
    def mock_path_constructor(val):
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        if "repo_graph_cache.json" in str(val).replace("\\", "/"):
            mock_path.stat.return_value.st_size = int(12 * 1024 * 1024)  # 12MB
        else:
            mock_path.stat.return_value.st_size = 10 * 1024  # 10KB
        return mock_path

    with patch("harness_health.Path", side_effect=mock_path_constructor):
        harness_health.report_state_file_sizes()
        
    captured = capsys.readouterr()
    assert "CRITICAL: .agent/state/repo_graph_cache.json" in captured.out
    assert "12.0MB" in captured.out
    assert "WARN" not in captured.out
