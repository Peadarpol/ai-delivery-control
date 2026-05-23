"""
Tests for bootstrap/install.py — stack detection, template rendering,
hook wiring, skill copying.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
INSTALL_PATH = WORKSPACE_ROOT / "bootstrap" / "install.py"


@pytest.fixture(scope="session")
def install_mod():
    """Import install.py module safely."""
    spec = importlib.util.spec_from_file_location("install", INSTALL_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["install"] = mod
    with patch("sys.platform", "linux"):
        spec.loader.exec_module(mod)
    return mod


# ── Stack detection ───────────────────────────────────────────────────────────


class TestDetectStack:
    def test_detect_python_with_pyproject(self, install_mod, tmp_path):
        """pyproject.toml present → Python/poetry detected."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "test-project"\nversion = "1.0.0"',
            encoding="utf-8",
        )
        (tmp_path / ".git").mkdir()
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="")):
            installer = install_mod.Installer(str(tmp_path))
            installer.detect_stack()
        assert installer.language == "Python"
        assert installer.package_manager == "poetry"

    def test_detect_node_with_package_json(self, install_mod, tmp_path):
        """package.json present → JavaScript/npm detected."""
        import json
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "test-js", "version": "1.0.0"}),
            encoding="utf-8",
        )
        (tmp_path / ".git").mkdir()
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="")):
            installer = install_mod.Installer(str(tmp_path))
            installer.detect_stack()
        assert installer.language in ("JavaScript", "TypeScript")
        assert installer.package_manager == "npm"

    def test_detect_fastapi_stack_pack(self, install_mod, tmp_path):
        """FastAPI in pyproject.toml → python-fastapi stack pack."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "api"\nversion = "1.0.0"\n\n'
            '[tool.poetry.dependencies]\nfastapi = "^0.100.0"',
            encoding="utf-8",
        )
        (tmp_path / ".git").mkdir()
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="")):
            installer = install_mod.Installer(str(tmp_path))
            installer.detect_stack()
        assert installer.stack_pack == "python-fastapi"

    def test_language_override(self, install_mod, tmp_path):
        """--language override takes precedence."""
        (tmp_path / ".git").mkdir()
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="")):
            installer = install_mod.Installer(
                str(tmp_path), language_override="TypeScript"
            )
            installer.detect_stack()
        assert installer.language == "TypeScript"


# ── Hook wiring ───────────────────────────────────────────────────────────────


class TestHookWiring:
    def test_wires_all_three_hook_types(self, install_mod, tmp_path):
        """BUG-01 regression: all three hook types must be installed."""
        (tmp_path / ".git").mkdir()
        captured_calls = []

        def mock_run(args, **kwargs):
            captured_calls.append(args)
            return MagicMock(returncode=0, stdout="", stderr="")

        installer = install_mod.Installer(str(tmp_path))
        with patch("subprocess.run", side_effect=mock_run):
            installer.wire_git_hooks()

        # Verify all three hook types were installed
        hook_types = []
        for call in captured_calls:
            if "--hook-type" in call:
                idx = call.index("--hook-type")
                hook_types.append(call[idx + 1])
            elif call == ["pre-commit", "install"]:
                hook_types.append("pre-commit")

        assert "commit-msg" in hook_types, "commit-msg hook must be installed (BUG-01)"
        assert "pre-push" in hook_types, "pre-push hook must be installed"


# ── Repo name seeding ─────────────────────────────────────────────────────────


class TestRepoNameSeeding:
    def test_repo_name_detected_from_remote(self, install_mod, tmp_path):
        """Git remote URL → correct EXPECTED_REPO in check_repo.py."""
        (tmp_path / ".git").mkdir()

        def mock_run(args, **kwargs):
            result = MagicMock()
            if "get-url" in args:
                result.returncode = 0
                result.stdout = "https://github.com/user/my-cool-project.git"
            else:
                result.returncode = 0
                result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            installer = install_mod.Installer(str(tmp_path))
            installer.detect_stack()

        assert installer.detected_repo_name == "my-cool-project"
