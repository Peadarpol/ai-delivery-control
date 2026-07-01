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
    thirty_five_days_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=35)).date()
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
    ninety_five_days_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=95)).date()
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


# --- Capability Calibration Tests ---

def test_capability_calibration_report_missing_file(capsys):
    """Verify default message when file is missing."""
    def mock_path_constructor(val):
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        return mock_path

    with patch("harness_health.Path", side_effect=mock_path_constructor):
        harness_health.report_capability_calibration()
    captured = capsys.readouterr()
    assert "NO CALIBRATION DATA" in captured.out


def test_capability_calibration_report_healthy(tmp_path, capsys):
    """Verify output of healthy capabilities."""
    cal_file = tmp_path / "capability_calibration.json"
    cal_data = {
        "schema_version": "1.0",
        "capabilities": {
            "INTENT_ALIGNMENT": {"tp": 2, "fp": 1, "weight": 1.05}
        }
    }
    import json
    cal_file.write_text(json.dumps(cal_data), encoding="utf-8")

    with patch("harness_health.Path", return_value=cal_file):
        harness_health.report_capability_calibration()
    captured = capsys.readouterr()
    assert "INTENT_ALIGNMENT" in captured.out
    assert "weight=1.05" in captured.out
    assert "precision=0.67" in captured.out
    assert "DEGRADING" not in captured.out
    assert "BOUNDARY" not in captured.out


def test_capability_calibration_report_degrading(tmp_path, capsys):
    """Verify output and [DEGRADING] flag for low precision."""
    cal_file = tmp_path / "capability_calibration.json"
    cal_data = {
        "schema_version": "1.0",
        "capabilities": {
            "INTENT_ALIGNMENT": {"tp": 1, "fp": 9, "weight": 0.55}  # precision = 0.1
        }
    }
    import json
    cal_file.write_text(json.dumps(cal_data), encoding="utf-8")

    with patch("harness_health.Path", return_value=cal_file):
        harness_health.report_capability_calibration()
    captured = capsys.readouterr()
    assert "INTENT_ALIGNMENT" in captured.out
    assert "weight=0.55" in captured.out
    assert "precision=0.10" in captured.out
    assert "DEGRADING" in captured.out


def test_capability_calibration_report_boundary_warning(tmp_path, capsys):
    """Verify output and [AT BOUNDARY] flag when weight is clamped."""
    cal_file = tmp_path / "capability_calibration.json"
    cal_data = {
        "schema_version": "1.0",
        "capabilities": {
            "INTENT_ALIGNMENT": {"tp": 5, "fp": 1, "weight": 1.5}
        }
    }
    import json
    cal_file.write_text(json.dumps(cal_data), encoding="utf-8")

    with patch("harness_health.Path", return_value=cal_file):
        harness_health.report_capability_calibration()
    captured = capsys.readouterr()
    assert "INTENT_ALIGNMENT" in captured.out
    assert "weight=1.50" in captured.out
    assert "precision=0.83" in captured.out
    assert "AT BOUNDARY" in captured.out


# --- Unmerged Stale Branches Tests ---

def test_report_unmerged_branches_healthy_no_branches(capsys):
    """Verify healthy status when git returns no unmerged branches."""
    mock_run = MagicMock()
    # Mocking first subprocess.run (local branch check) to return empty
    mock_run.return_value = MagicMock(returncode=0, stdout="")
    
    with patch("subprocess.run", mock_run), \
         patch("harness_health.load_config", return_value={}):
        harness_health.report_unmerged_branches()
        
    captured = capsys.readouterr()
    assert "HEALTHY (no unmerged branches)" in captured.out


def test_report_unmerged_branches_healthy_recent_branch(capsys):
    """Verify healthy status when unmerged branch exists but last commit is recent."""
    mock_run = MagicMock()
    # First call: git branch --no-merged main
    res1 = MagicMock(returncode=0, stdout="  feat/recent-branch\n")
    # Second call: git log -1 --format=%ct feat/recent-branch
    now_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    res2 = MagicMock(returncode=0, stdout=str(now_ts))
    
    mock_run.side_effect = [res1, res2]
    
    with patch("subprocess.run", mock_run), \
         patch("harness_health.load_config", return_value={}):
        harness_health.report_unmerged_branches()
        
    captured = capsys.readouterr()
    assert "HEALTHY (no stale unmerged branches)" in captured.out


def test_report_unmerged_branches_degrading_stale_branch(capsys):
    """Verify degrading status when unmerged branch exists and last commit is older than threshold."""
    mock_run = MagicMock()
    # First call: git branch --no-merged main
    res1 = MagicMock(returncode=0, stdout="  feat/stale-branch\n")
    # Second call: git log -1 --format=%ct feat/stale-branch (e.g. 20 days ago)
    stale_ts = int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)).timestamp())
    res2 = MagicMock(returncode=0, stdout=str(stale_ts))
    
    mock_run.side_effect = [res1, res2]
    
    with patch("subprocess.run", mock_run), \
         patch("harness_health.load_config", return_value={}):
        harness_health.report_unmerged_branches()
        
    captured = capsys.readouterr()
    assert "DEGRADING" in captured.out
    assert "feat/stale-branch" in captured.out
    assert "last commit was 20 days ago" in captured.out


