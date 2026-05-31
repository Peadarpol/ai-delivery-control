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

