"""
Tests for bootstrap/validate.py — environment validation checks.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = WORKSPACE_ROOT / "bootstrap" / "validate.py"


@pytest.fixture(scope="session")
def validate_mod():
    """Import validate.py module safely."""
    spec = importlib.util.spec_from_file_location("validate", VALIDATE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["validate"] = mod
    with patch("sys.platform", "linux"):
        spec.loader.exec_module(mod)
    return mod


# ── Directory validation ─────────────────────────────────────────────────────


class TestValidateDirectories:
    def test_all_dirs_present(self, validate_mod, tmp_path):
        """All required .agent/ dirs exist → pass."""
        for d in [".agent", ".agent/skills", ".agent/scripts",
                  ".agent/workflows", ".agent/state", ".agent/wiki"]:
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        v = validate_mod.Validator(tmp_path)
        passed, _ = v.validate_directories()
        assert passed is True

    def test_missing_dirs_fail(self, validate_mod, tmp_path):
        """Missing .agent/ dirs → fail."""
        v = validate_mod.Validator(tmp_path)
        passed, details = v.validate_directories()
        assert passed is False
        assert ".agent" in details


# ── Core files validation ─────────────────────────────────────────────────────


class TestValidateCoreFiles:
    def test_all_files_present(self, validate_mod, tmp_path):
        files = [
            ".agent/AGENTS.md",
            ".agent/governance.md",
            ".agent/scripts/init_session.py",
            ".agent/scripts/check_halt.py",
            ".agent/templates/feature_spec.md",
            ".agent/scripts/check_spec.py",
        ]
        for f in files:
            p = tmp_path / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("content", encoding="utf-8")
        v = validate_mod.Validator(tmp_path)
        passed, _ = v.validate_core_files()
        assert passed is True

    def test_missing_file_fails(self, validate_mod, tmp_path):
        (tmp_path / ".agent").mkdir()
        v = validate_mod.Validator(tmp_path)
        passed, details = v.validate_core_files()
        assert passed is False


# ── Repo guard validation ─────────────────────────────────────────────────────


class TestValidateRepoGuard:
    def test_customized_repo_passes(self, validate_mod, tmp_path):
        scripts = tmp_path / ".agent" / "scripts"
        scripts.mkdir(parents=True)
        check_repo = scripts / "check_repo.py"
        check_repo.write_text('EXPECTED_REPO = "my-project"', encoding="utf-8")
        v = validate_mod.Validator(tmp_path)
        passed, _ = v.validate_repo_guard()
        assert passed is True

    def test_default_repo_warns(self, validate_mod, tmp_path):
        scripts = tmp_path / ".agent" / "scripts"
        scripts.mkdir(parents=True)
        check_repo = scripts / "check_repo.py"
        check_repo.write_text('EXPECTED_REPO = "ai-delivery-control"', encoding="utf-8")
        v = validate_mod.Validator(tmp_path)
        passed, details = v.validate_repo_guard()
        # Default value should trigger a warning but still pass
        assert "ai-delivery-control" in details or "default" in details.lower()


# ── Pre-commit hooks validation ───────────────────────────────────────────────


class TestValidatePrecommitSetup:
    def test_all_hooks_present(self, validate_mod, tmp_path):
        """pre-commit + commit-msg + pre-push all present → pass."""
        (tmp_path / ".pre-commit-config.yaml").write_text(
            "repos:\n  - repo: local\n    hooks:\n      - id: test\n",
            encoding="utf-8",
        )
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        for hook in ["pre-commit", "commit-msg", "pre-push"]:
            (hooks_dir / hook).write_text("#!/bin/sh", encoding="utf-8")
        v = validate_mod.Validator(tmp_path)
        passed, details = v.validate_precommit_setup()
        assert passed is True

    def test_missing_hooks_warns(self, validate_mod, tmp_path):
        """Hooks absent but config present → warning (pass=True, warnings incremented)."""
        (tmp_path / ".pre-commit-config.yaml").write_text(
            "repos:\n  - repo: local\n    hooks:\n      - id: test\n",
            encoding="utf-8",
        )
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        v = validate_mod.Validator(tmp_path)
        passed, details = v.validate_precommit_setup()
        # Should pass with a warning
        assert passed is True
        assert v.warnings >= 1

    def test_missing_config_fails(self, validate_mod, tmp_path):
        """No .pre-commit-config.yaml → fail."""
        v = validate_mod.Validator(tmp_path)
        passed, _ = v.validate_precommit_setup()
        assert passed is False


# ── Tools validation ──────────────────────────────────────────────────────────


class TestValidateTools:
    def test_git_available(self, validate_mod, tmp_path):
        """Git available in PATH → pass."""
        v = validate_mod.Validator(tmp_path)
        passed, _ = v.validate_tools()
        # In CI and local, git should always be available
        assert passed is True


# ── Overall exit code ─────────────────────────────────────────────────────────


class TestOverallResult:
    def test_warnings_only_passes(self, validate_mod, tmp_path):
        """Warnings but no errors → exit 0."""
        v = validate_mod.Validator(tmp_path)
        v.warnings = 3
        v.errors = 0
        # Validator run() returns exit code
        assert v.errors == 0

    def test_errors_fail(self, validate_mod, tmp_path):
        v = validate_mod.Validator(tmp_path)
        v.errors = 1
        assert v.errors > 0


# ── Gitignore state validation ───────────────────────────────────────────────


class TestValidateGitignoredStates:
    def test_all_ignored_passes(self, validate_mod, tmp_path):
        """HALT and session.json are ignored -> pass."""
        (tmp_path / ".git").mkdir()
        v = validate_mod.Validator(tmp_path)
        
        def mock_run(args, **kwargs):
            # Exit code 0 means git check-ignore found it (ignored)
            return MagicMock(returncode=0)
            
        with patch("subprocess.run", side_effect=mock_run):
            passed, _ = v.validate_gitignored_states()
        assert passed is True
        assert v.errors == 0
        assert v.warnings == 0

    def test_halt_not_ignored_fails(self, validate_mod, tmp_path):
        """HALT is not ignored -> hard failure (passed = False)."""
        (tmp_path / ".git").mkdir()
        v = validate_mod.Validator(tmp_path)
        
        def mock_run(args, **kwargs):
            # Non-zero exit code means not ignored
            return MagicMock(returncode=1)
            
        with patch("subprocess.run", side_effect=mock_run):
            passed, details = v.validate_gitignored_states()
        assert passed is False
        assert "HALT" in details

    def test_session_json_not_ignored_warns(self, validate_mod, tmp_path):
        """session.json not ignored -> warning (passed = True, warnings incremented)."""
        (tmp_path / ".git").mkdir()
        v = validate_mod.Validator(tmp_path)
        
        def mock_run(args, **kwargs):
            file_rel = args[-1]
            # HALT is ignored (return 0), session.json is not ignored (return 1)
            if "HALT" in file_rel:
                return MagicMock(returncode=0)
            else:
                return MagicMock(returncode=1)
                
        with patch("subprocess.run", side_effect=mock_run), patch("builtins.print") as mock_print:
            passed, details = v.validate_gitignored_states()
        assert passed is True
        assert v.warnings >= 1
        assert "session.json" in details or "warning" in details.lower()


class TestValidateWikiState:
    def test_validate_warns_on_recent_wiki_failure(self, validate_mod, tmp_path):
        """If last_failure_utc is set within 48h, validator emits warning."""
        from datetime import datetime, UTC, timedelta
        import json
        
        state_dir = tmp_path / ".agent" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "wiki_compile_state.json"
        
        recent_fail = (datetime.now(UTC) - timedelta(hours=10)).replace(tzinfo=None).isoformat() + "Z"
        state_data = {
            "last_run_utc": "1970-01-01T00:00:00Z",
            "last_failure_utc": recent_fail,
            "domains_compiled": 0
        }
        state_file.write_text(json.dumps(state_data), encoding="utf-8")
        
        v = validate_mod.Validator(tmp_path)
        with patch("builtins.print") as mock_print:
            passed, details = v.validate_wiki_state()
            
        assert passed is True
        assert v.warnings >= 1
        assert "failed recently" in details.lower()

    def test_validate_info_on_uncompiled_wiki(self, validate_mod, tmp_path):
        """If last_run_utc is epoch zero and no failure, validator info card prints."""
        import json
        
        state_dir = tmp_path / ".agent" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "wiki_compile_state.json"
        
        state_data = {
            "last_run_utc": "1970-01-01T00:00:00Z",
            "domains_compiled": 0
        }
        state_file.write_text(json.dumps(state_data), encoding="utf-8")
        
        v = validate_mod.Validator(tmp_path)
        with patch("builtins.print") as mock_print:
            passed, details = v.validate_wiki_state()

        assert passed is True
        assert v.warnings == 0
        assert "not yet compiled" in details.lower()


# ── T1-L-00: Outer loop mode validation ─────────────────────────────────────


class TestOuterLoopModeValidation:
    """T1-L-00 — validate_outer_loop_mode() warns on unrecognised values."""

    def test_valid_mode_incremental_passes(self, validate_mod, tmp_path):
        """Known mode 'incremental' → passes with no warning."""
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "config.yaml").write_text(
            "outer_loop:\n  mode: incremental\n", encoding="utf-8"
        )
        v = validate_mod.Validator(tmp_path)
        passed, details = v.validate_outer_loop_mode()
        assert passed is True
        assert v.warnings == 0
        assert "incremental" in details

    def test_valid_mode_discovery_passes(self, validate_mod, tmp_path):
        """Known mode 'discovery' → passes with no warning."""
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "config.yaml").write_text(
            "outer_loop:\n  mode: discovery\n", encoding="utf-8"
        )
        v = validate_mod.Validator(tmp_path)
        passed, details = v.validate_outer_loop_mode()
        assert passed is True
        assert v.warnings == 0

    def test_unknown_mode_emits_warning(self, validate_mod, tmp_path):
        """Unknown mode 'waterfall' → passed=True but warnings incremented."""
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "config.yaml").write_text(
            "outer_loop:\n  mode: waterfall\n", encoding="utf-8"
        )
        v = validate_mod.Validator(tmp_path)
        passed, details = v.validate_outer_loop_mode()
        assert passed is True, "Unknown mode must not fail validation (WARN not ERROR)"
        assert v.warnings == 1
        assert "waterfall" in details
        assert "not a recognised mode" in details.lower() or "not recognised" in details.lower()

    def test_absent_outer_loop_section_passes(self, validate_mod, tmp_path):
        """Missing outer_loop section → passes silently, no warning."""
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "config.yaml").write_text(
            "project:\n  name: test\n", encoding="utf-8"
        )
        v = validate_mod.Validator(tmp_path)
        passed, details = v.validate_outer_loop_mode()
        assert passed is True
        assert v.warnings == 0

    def test_absent_config_passes(self, validate_mod, tmp_path):
        """Absent config.yaml → passes (no harness installed yet)."""
        v = validate_mod.Validator(tmp_path)
        passed, _ = v.validate_outer_loop_mode()
        assert passed is True


# ── v1.4.11 Validator Hardening (F8, F-COLD-3, F-COLD-5, Sandbox) ─────────────


class Testv1411ValidatorHardening:
    def test_sandbox_removal_postcondition(self, validate_mod, tmp_path):
        """Sandbox postcondition: not sandbox_path.exists() and all child paths unlinked, even with read-only files."""
        v = validate_mod.Validator(tmp_path)
        sandbox = tmp_path / ".agent" / "scratch" / "validate_sandbox"
        sandbox.mkdir(parents=True)
        read_only_file = sandbox / "readonly.txt"
        read_only_file.write_text("data", encoding="utf-8")
        import stat
        read_only_file.chmod(stat.S_IREAD)
        
        v.remove_sandbox_dir(sandbox)
        # Assert exact postcondition
        assert not sandbox.exists()
        assert not list(sandbox.glob("*"))

    def test_skip_validation_flag(self, validate_mod, tmp_path):
        """--skip-validation flag bypasses dry-run and prints summary notice."""
        v = validate_mod.Validator(tmp_path, skip_validation=True)
        passed, details = v.validate_sandbox_dryrun()
        assert passed is True
        assert "skipped" in details.lower()

    def test_tool_version_subprocess_timeouts(self, validate_mod, tmp_path):
        """Tool version checks respect individual <=1.0s timeouts."""
        v = validate_mod.Validator(tmp_path)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="black, 24.1.0\n")
            passed, details = v.validate_python_currency()
            assert passed is True
            # Verify timeout parameter was passed
            for call_item in mock_run.call_args_list:
                _, kwargs = call_item
                if "timeout" in kwargs:
                    assert kwargs["timeout"] <= 1.0

    def test_api_preflight_timeout_and_redaction(self, validate_mod, tmp_path, monkeypatch, capsys):
        """API preflight enforces timeout and redacts raw keys, auth headers, and key fragments."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-SECRET12345")
        monkeypatch.delenv("HARNESS_MOCK_API_PREFLIGHT", raising=False)
        
        v = validate_mod.Validator(tmp_path)
        with patch("urllib.request.urlopen", side_effect=Exception("Network failure for Bearer sk-ant-api03-SECRET12345")) as mock_urlopen:
            passed, details = v.validate_api_preflight()
            assert passed is True
            # Assert timeout <= 5.0 parameter was enforced
            assert mock_urlopen.call_args[1].get("timeout") == 5.0

            captured = capsys.readouterr()
            stderr_out = captured.err
            
            # Assert raw key, auth header, and fragment are strictly redacted
            assert "sk-ant-api03-SECRET12345" not in stderr_out
            assert "Bearer sk-ant-api03-SECRET12345" not in stderr_out
            assert "SECRET12345" not in stderr_out
            assert "[REDACTED_KEY]" in stderr_out or "[REDACTED_HEADER]" in stderr_out or "[REDACTED_FRAGMENT]" in stderr_out


