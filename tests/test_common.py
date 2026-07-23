"""
Tests for bootstrap/common.py — shared helper functions.
"""

from pathlib import Path
import sys

from bootstrap.common import is_harness_repo, resolve_venv_python


def test_is_harness_repo_detects_version_file(tmp_path):
    """is_harness_repo returns True when harness_version.txt exists in target dir."""
    assert is_harness_repo(tmp_path) is False
    (tmp_path / "harness_version.txt").write_text("1.4.11\n", encoding="utf-8")
    assert is_harness_repo(tmp_path) is True


def test_resolve_venv_python_local_venv(tmp_path, monkeypatch):
    """resolve_venv_python finds local .venv folder executable."""
    if sys.platform == "win32":
        venv_bin = tmp_path / ".venv" / "Scripts"
        venv_bin.mkdir(parents=True)
        py_exe = venv_bin / "python.exe"
    else:
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        py_exe = venv_bin / "python"
    
    py_exe.write_text("", encoding="utf-8")
    resolved = resolve_venv_python(tmp_path)
    assert resolved == py_exe


def test_resolve_venv_python_env_var(tmp_path, monkeypatch):
    """resolve_venv_python checks VIRTUAL_ENV when local .venv absent."""
    env_dir = tmp_path / "custom_env"
    if sys.platform == "win32":
        venv_bin = env_dir / "Scripts"
        venv_bin.mkdir(parents=True)
        py_exe = venv_bin / "python.exe"
    else:
        venv_bin = env_dir / "bin"
        venv_bin.mkdir(parents=True)
        py_exe = venv_bin / "python"
        
    py_exe.write_text("", encoding="utf-8")
    monkeypatch.setenv("VIRTUAL_ENV", str(env_dir))
    resolved = resolve_venv_python(tmp_path)
    assert resolved == py_exe
