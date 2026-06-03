"""
Unit tests for acceptance_check.py (T1-L-05).
"""

import sys
import os
from pathlib import Path
import tempfile
import json
import pytest
from unittest.mock import patch, MagicMock

# Ensure imports can find the script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib.util
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("acceptance_check", WORKSPACE_ROOT / ".agent" / "scripts" / "acceptance_check.py")
acceptance_check = importlib.util.module_from_spec(spec)
sys.modules["acceptance_check"] = acceptance_check
spec.loader.exec_module(acceptance_check)

@pytest.fixture
def mock_acceptance_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        
        # config.yaml
        config_path = tmp_path / ".agent"
        config_path.mkdir(parents=True, exist_ok=True)
        (config_path / "config.yaml").write_text("""
spec_gate:
  specs_path: docs/planning/specs/
acceptance_gate:
  base_branch: main
  migration_paths:
    - migrations/versions/
    - db/migration/
""", encoding="utf-8")
        
        cwd = Path.cwd()
        os.chdir(tmp_path)
        yield tmp_path
        os.chdir(cwd)

def test_resolve_spec_id_arg():
    assert acceptance_check.resolve_spec_id("SPEC-001") == "SPEC-001"

def test_resolve_spec_id_env():
    with patch.dict(os.environ, {"SPEC_ID": "SPEC-002"}):
        assert acceptance_check.resolve_spec_id(None) == "SPEC-002"

def test_resolve_spec_id_branch():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "feature/SPEC-003-login\n"
        assert acceptance_check.resolve_spec_id(None) == "SPEC-003"

def test_load_config_values(mock_acceptance_env):
    cfg = acceptance_check.load_config()
    assert cfg["base_branch"] == "main"
    assert "migrations/versions/" in cfg["migration_paths"]
    assert "db/migration/" in cfg["migration_paths"]

def test_static_schema_creep_blocks(mock_acceptance_env):
    spec_id = "SPEC-001"
    spec_file = mock_acceptance_env / "docs" / "planning" / "specs" / f"{spec_id}.md"
    spec_file.write_text("""# Spec
Status: APPROVED
# Acceptance Criteria
Scenario: Modify DB
""", encoding="utf-8")

    diff_output = "diff --git a/migrations/versions/123_migration.py b/migrations/versions/123_migration.py\n"
    
    with patch("subprocess.run") as mock_run, patch("sys.argv", ["acceptance_check.py", "--spec", spec_id]):
        # Mock git diff and git rev-parse for branch check
        mock_run.side_effect = [
            MagicMock(stdout="feature/SPEC-001\n", returncode=0), # branch check
            MagicMock(stdout=diff_output, returncode=0)          # diff check
        ]
        
        with pytest.raises(SystemExit) as excinfo:
            acceptance_check.main()
        assert excinfo.value.code == 1

def test_static_schema_creep_allowed_with_flag(mock_acceptance_env):
    spec_id = "SPEC-001"
    spec_file = mock_acceptance_env / "docs" / "planning" / "specs" / f"{spec_id}.md"
    spec_file.write_text("""# Spec
Status: APPROVED
# Constraints
[HIGH_RISK_SCHEMA_CHANGE]
# Acceptance Criteria
Scenario: Modify DB
""", encoding="utf-8")

    diff_output = "diff --git a/migrations/versions/123_migration.py b/migrations/versions/123_migration.py\n"
    
    # Mock LLM response to avoid network call
    mock_provider = MagicMock()
    mock_provider.is_available.return_value = True
    mock_provider.raw_completion.return_value = json.dumps({
        "verdict": "SATISFIED",
        "satisfied_scenarios": ["Modify DB"],
        "partial_scenarios": [],
        "unimplemented_scenarios": [],
        "scope_creep_findings": [],
        "remediation_steps": [],
        "rationale": "Perfect implementation"
    })
    
    with patch("subprocess.run") as mock_run, \
         patch("sys.argv", ["acceptance_check.py", "--spec", spec_id]), \
         patch("acceptance_check.get_provider", return_value=mock_provider):
        mock_run.side_effect = [
            MagicMock(stdout="feature/SPEC-001\n", returncode=0),
            MagicMock(stdout=diff_output, returncode=0)
        ]
        
        with pytest.raises(SystemExit) as excinfo:
            acceptance_check.main()
        assert excinfo.value.code == 0

def test_offline_fail_open(mock_acceptance_env):
    spec_id = "SPEC-001"
    spec_file = mock_acceptance_env / "docs" / "planning" / "specs" / f"{spec_id}.md"
    spec_file.write_text("# Spec\nStatus: APPROVED\n", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, \
         patch("sys.argv", ["acceptance_check.py", "--spec", spec_id]), \
         patch("acceptance_check.get_provider", side_effect=RuntimeError("Unavailable")):
        mock_run.side_effect = [
            MagicMock(stdout="feature/SPEC-001\n", returncode=0),
            MagicMock(stdout="", returncode=0)
        ]
        
        with pytest.raises(SystemExit) as excinfo:
            acceptance_check.main()
        assert excinfo.value.code == 0

def test_offline_fail_closed(mock_acceptance_env):
    spec_id = "SPEC-001"
    spec_file = mock_acceptance_env / "docs" / "planning" / "specs" / f"{spec_id}.md"
    spec_file.write_text("# Spec\nStatus: APPROVED\n", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, \
         patch("sys.argv", ["acceptance_check.py", "--spec", spec_id, "--fail-closed"]), \
         patch("acceptance_check.get_provider", side_effect=RuntimeError("Unavailable")):
        mock_run.side_effect = [
            MagicMock(stdout="feature/SPEC-001\n", returncode=0),
            MagicMock(stdout="", returncode=0)
        ]
        
        with pytest.raises(SystemExit) as excinfo:
            acceptance_check.main()
        assert excinfo.value.code == 1

def test_strict_mode_rejects_partial(mock_acceptance_env):
    spec_id = "SPEC-001"
    spec_file = mock_acceptance_env / "docs" / "planning" / "specs" / f"{spec_id}.md"
    spec_file.write_text("# Spec\nStatus: APPROVED\n", encoding="utf-8")
    
    mock_provider = MagicMock()
    mock_provider.is_available.return_value = True
    mock_provider.raw_completion.return_value = json.dumps({
        "verdict": "PARTIAL",
        "satisfied_scenarios": ["Login"],
        "partial_scenarios": ["Reset Password"],
        "unimplemented_scenarios": [],
        "scope_creep_findings": [],
        "remediation_steps": [],
        "rationale": "Partial implementation"
    })
    
    with patch("subprocess.run") as mock_run, \
         patch("sys.argv", ["acceptance_check.py", "--spec", spec_id, "--strict"]), \
         patch("acceptance_check.get_provider", return_value=mock_provider):
        mock_run.side_effect = [
            MagicMock(stdout="feature/SPEC-001\n", returncode=0),
            MagicMock(stdout="", returncode=0)
        ]
        
        with pytest.raises(SystemExit) as excinfo:
            acceptance_check.main()
        assert excinfo.value.code == 1
