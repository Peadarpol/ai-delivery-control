"""
Unit tests for check_traceability.py commit traceability hook (T1-L-04).
"""

import sys
import os
from pathlib import Path
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Ensure imports can find the script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib.util
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_traceability", WORKSPACE_ROOT / ".agent" / "scripts" / "check_traceability.py")
check_traceability = importlib.util.module_from_spec(spec)
sys.modules["check_traceability"] = check_traceability
spec.loader.exec_module(check_traceability)

@pytest.fixture
def mock_trace_env():
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
traceability:
  specs_path: docs/planning/specs/
""", encoding="utf-8")
        
        # Git folder mock
        git_dir = tmp_path / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)
        
        cwd = Path.cwd()
        os.chdir(tmp_path)
        yield tmp_path
        os.chdir(cwd)

def test_resolve_git_dir(mock_trace_env):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = f"{mock_trace_env}/.git\n"
        git_dir = check_traceability.get_git_dir()
        assert git_dir.name == ".git"

def test_merge_commit_bypass(mock_trace_env):
    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text("Merge branch 'main' of github.com/test", encoding="utf-8")
    
    with patch("sys.argv", ["check_traceability.py", str(msg_file)]):
        with pytest.raises(SystemExit) as excinfo:
            check_traceability.main()
        assert excinfo.value.code == 0

def test_docs_only_bypass(mock_trace_env):
    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text("docs: update README", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, patch("sys.argv", ["check_traceability.py", str(msg_file)]):
        mock_run.return_value.stdout = "README.md\ndocs/architecture.md\n"
        with pytest.raises(SystemExit) as excinfo:
            check_traceability.main()
        assert excinfo.value.code == 0

def test_no_trace_bypass_valid(mock_trace_env):
    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text("--no-trace Trivial typo fix in README documentation", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, patch("sys.argv", ["check_traceability.py", str(msg_file)]):
        mock_run.return_value.stdout = "src/main.py\n" # non-trivial
        with pytest.raises(SystemExit) as excinfo:
            check_traceability.main()
        assert excinfo.value.code == 0

def test_no_trace_bypass_invalid_short(mock_trace_env):
    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text("--no-trace short", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, patch("sys.argv", ["check_traceability.py", str(msg_file)]):
        mock_run.return_value.stdout = "src/main.py\n"
        with pytest.raises(SystemExit) as excinfo:
            check_traceability.main()
        assert excinfo.value.code == 1

def test_happy_path_approved_spec(mock_trace_env):
    spec_id = "SPEC-001"
    spec_file = mock_trace_env / "docs" / "planning" / "specs" / f"{spec_id}.md"
    spec_file.write_text("""# Spec 001
Status: APPROVED
""", encoding="utf-8")
    
    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text(f"[{spec_id}] implement feature X", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, patch("sys.argv", ["check_traceability.py", str(msg_file)]):
        mock_run.return_value.stdout = "src/main.py\n"
        with pytest.raises(SystemExit) as excinfo:
            check_traceability.main()
        assert excinfo.value.code == 0

def test_draft_spec_fails_in_ci(mock_trace_env):
    spec_id = "SPEC-002"
    spec_file = mock_trace_env / "docs" / "planning" / "specs" / f"{spec_id}.md"
    spec_file.write_text("""# Spec 002
Status: DRAFT
""", encoding="utf-8")
    
    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text(f"[{spec_id}] working on feature", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, \
         patch("sys.argv", ["check_traceability.py", str(msg_file)]), \
         patch.dict(os.environ, {"CI": "true"}):
        mock_run.return_value.stdout = "src/main.py\n"
        with pytest.raises(SystemExit) as excinfo:
            check_traceability.main()
        assert excinfo.value.code == 1

def test_req_prefix_does_not_match(mock_trace_env):
    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text("[REQ-001] implement feature X", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, patch("sys.argv", ["check_traceability.py", str(msg_file)]):
        mock_run.return_value.stdout = "src/main.py\n"
        with pytest.raises(SystemExit) as excinfo:
            check_traceability.main()
        assert excinfo.value.code == 1

def test_contractual_mode_blocks_no_trace(mock_trace_env):
    # Set mode to contractual
    (mock_trace_env / ".agent" / "config.yaml").write_text("""
outer_loop:
  mode: contractual
""", encoding="utf-8")

    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text("--no-trace Trivial typo fix in README documentation", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, patch("sys.argv", ["check_traceability.py", str(msg_file)]), patch("check_traceability.get_config_options") as mock_get_config:
        mock_get_config.return_value = (mock_trace_env / "docs" / "planning" / "specs", "contractual")
        mock_run.return_value.stdout = "src/main.py\n"
        with pytest.raises(SystemExit) as excinfo:
            check_traceability.main()
        assert excinfo.value.code == 1


def test_multiple_ids_scanned_once(mock_trace_env):
    docs_dir = mock_trace_env / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    backlog_file = docs_dir / "backlog.md"
    backlog_file.write_text("- [ ] HIB-001\n- [ ] BUG-002\n- [ ] T1-A-01\n", encoding="utf-8")
    
    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text("Fixes [HIB-001], [BUG-002], and [T1-A-01]", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, patch("sys.argv", ["check_traceability.py", str(msg_file)]):
        mock_run.return_value.stdout = "src/main.py\n"
        
        real_read_text = Path.read_text
        def mock_read_text_impl(self, *args, **kwargs):
            return real_read_text(self, *args, **kwargs)
            
        with patch.object(Path, 'read_text', autospec=True, side_effect=mock_read_text_impl) as mock_read_text:
            with pytest.raises(SystemExit) as excinfo:
                check_traceability.main()
            assert excinfo.value.code == 0
            calls = [call for call in mock_read_text.call_args_list if call[0][0].name == 'backlog.md']
            assert len(calls) == 1

def test_missing_docs_dir(mock_trace_env, capsys):
    import shutil
    shutil.rmtree(mock_trace_env / "docs")
    
    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text("Fixes [HIB-001]", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, patch("sys.argv", ["check_traceability.py", str(msg_file)]):
        mock_run.return_value.stdout = "src/main.py\n"
        with pytest.raises(SystemExit) as excinfo:
            check_traceability.main()
        assert excinfo.value.code == 1
        
        captured = capsys.readouterr()
        assert "docs/ directory not found" in captured.err

def test_huge_file_skipped(mock_trace_env, capsys):
    docs_dir = mock_trace_env / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    huge_file = docs_dir / "huge.md"
    huge_file.write_bytes(b"0" * (6 * 1024 * 1024))
    
    msg_file = mock_trace_env / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text("Fixes [HIB-001]", encoding="utf-8")
    
    with patch("subprocess.run") as mock_run, patch("sys.argv", ["check_traceability.py", str(msg_file)]):
        mock_run.return_value.stdout = "src/main.py\n"
        with pytest.raises(SystemExit) as excinfo:
            check_traceability.main()
        assert excinfo.value.code == 1
        
        captured = capsys.readouterr()
        assert "Skipping" in captured.out
        assert "huge.md" in captured.out
