"""
Unit tests for pm_scaffold.py (T1-L-03).
"""

import sys
import os
from pathlib import Path
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock

# Ensure we can import from the bootstrap package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib.util
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pm_scaffold", WORKSPACE_ROOT / ".agent" / "scripts" / "pm_scaffold.py")
pm_scaffold = importlib.util.module_from_spec(spec)
sys.modules["pm_scaffold"] = pm_scaffold
spec.loader.exec_module(pm_scaffold)
from src.scripts import providers

@pytest.fixture
def mock_project_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create specs directory
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create config.yaml
        config_path = tmp_path / ".agent"
        config_path.mkdir(parents=True, exist_ok=True)
        (config_path / "config.yaml").write_text("""
spec_gate:
  specs_path: docs/planning/specs/
""", encoding="utf-8")
        
        # Save current working directory
        cwd = Path.cwd()
        os.chdir(tmp_path)
        yield tmp_path
        os.chdir(cwd)

def test_resolve_spec_id_arg():
    assert pm_scaffold.resolve_spec_id("SPEC-123") == "SPEC-123"

def test_resolve_spec_id_env():
    with patch.dict(os.environ, {"SPEC_ID": "SPEC-456"}):
        assert pm_scaffold.resolve_spec_id(None) == "SPEC-456"

def test_resolve_spec_id_branch():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "feature/SPEC-789-description\n"
        assert pm_scaffold.resolve_spec_id(None) == "SPEC-789"

def test_parse_gherkin_scenarios():
    spec_content = """# Feature Spec
## Status: APPROVED

# Acceptance Criteria
Scenario: User logs in successfully
  Given valid credentials
  When they submit the form
  Then they are redirected to home

Scenario 2: User fails to log in
  Given invalid credentials
  When they submit
  Then error is shown

# Assumptions
- None
"""
    scenarios, has_gwt = pm_scaffold.parse_gherkin_scenarios(spec_content)
    assert len(scenarios) == 2
    assert scenarios[0] == "User logs in successfully"
    assert scenarios[1] == "User fails to log in"
    assert has_gwt is True

def test_parse_gherkin_scenarios_prose():
    spec_content = """# Feature Spec
## Status: APPROVED

# Acceptance Criteria
Here are prose criteria with no given when then.
We should do this and that.
"""
    scenarios, has_gwt = pm_scaffold.parse_gherkin_scenarios(spec_content)
    assert len(scenarios) == 0
    assert has_gwt is False

def test_pm_scaffold_offline_success(mock_project_env):
    spec_id = "SPEC-100"
    spec_file = Path("docs/planning/specs") / f"{spec_id}.md"
    spec_file.write_text("""# SPEC-100 Spec
Status: APPROVED

# Acceptance Criteria
Scenario: User modifies schema
  Given a migration file
  When they run migrate
  Then table is updated
""", encoding="utf-8")

    with patch("sys.argv", ["pm_scaffold.py", spec_id, "--offline"]):
        try:
            pm_scaffold.main()
        except SystemExit as exc:
            assert exc.code == 0 or exc.code is None
        
    output_file = Path("docs/planning/tasks") / f"{spec_id}-tasks.md"
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "⚠️ OFFLINE MODE" in content
    assert "Implement scenario: User modifies schema" in content
    assert "DB/Migration" in content

def test_pm_scaffold_backup_and_check(mock_project_env):
    spec_id = "SPEC-100"
    spec_file = Path("docs/planning/specs") / f"{spec_id}.md"
    spec_file.write_text("""# SPEC-100 Spec
Status: APPROVED

# Acceptance Criteria
Scenario: User modifies schema
  Given a migration file
  When they run migrate
  Then table is updated
""", encoding="utf-8")

    output_dir = Path("docs/planning/tasks")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{spec_id}-tasks.md"
    output_file.write_text("- [x] Done task", encoding="utf-8")

    # Mock non-interactive stream to log caution and proceed
    with patch("sys.argv", ["pm_scaffold.py", spec_id, "--offline"]), patch("sys.stdin.isatty", return_value=False):
        pm_scaffold.main()
        
    backup_file = output_dir / f"{spec_id}-tasks.md.bak"
    assert backup_file.exists()
    assert backup_file.read_text(encoding="utf-8") == "- [x] Done task"
