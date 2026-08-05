import os
from unittest.mock import patch
import pytest
from src.scripts.harness_utils import _safe_git_env

def test_safe_git_env_excludes_api_keys():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-123", "OPENAI_API_KEY": "sk-456", "PATH": "/usr/bin"}, clear=True):
        env = _safe_git_env()
        assert "ANTHROPIC_API_KEY" not in env
        assert "OPENAI_API_KEY" not in env
        assert "PATH" in env

def test_safe_git_env_includes_path():
    with patch.dict(os.environ, {"PATH": "/custom/path"}, clear=True):
        env = _safe_git_env()
        assert env.get("PATH") == "/custom/path"

def test_safe_git_env_passes_git_prefix():
    with patch.dict(os.environ, {"GIT_AUTHOR_NAME": "Test User", "GIT_COMMITTER_EMAIL": "test@example.com", "PATH": "/usr/bin"}, clear=True):
        env = _safe_git_env()
        assert env.get("GIT_AUTHOR_NAME") == "Test User"
        assert env.get("GIT_COMMITTER_EMAIL") == "test@example.com"

def test_safe_git_env_excludes_pythonpath():
    with patch.dict(os.environ, {"PYTHONPATH": "/src/lib", "PATH": "/usr/bin"}, clear=True):
        env = _safe_git_env()
        assert "PYTHONPATH" not in env
        assert "PATH" in env
