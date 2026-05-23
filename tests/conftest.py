"""
Shared pytest fixtures for the AI Delivery Control framework test suite.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


# ── ai_review safe import ────────────────────────────────────────────────────

_AI_REVIEW_PATH = WORKSPACE_ROOT / "src" / "scripts" / "ai_review.py"
_PROVIDERS_PATH = WORKSPACE_ROOT / "src" / "scripts" / "providers.py"


def _load_module(name: str, path: Path):
    """Import a module from an absolute path, suppressing Windows stdout wrapping."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"Cannot locate {path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    with patch("sys.platform", "linux"):
        spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def ai_review():
    """Import ai_review module safely (patches Windows stdout wrapper)."""
    return _load_module("ai_review", _AI_REVIEW_PATH)


@pytest.fixture(scope="session")
def providers_mod():
    """Import the providers module."""
    return _load_module("providers", _PROVIDERS_PATH)


# ── Temporary project directory ───────────────────────────────────────────────


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with minimal .git/ structure."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir()
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    (agent_dir / "scripts").mkdir()
    (agent_dir / "workflows").mkdir()
    (agent_dir / "skills").mkdir()
    (agent_dir / "config").mkdir()
    (agent_dir / "state").mkdir()
    return tmp_path


# ── Sample diffs ──────────────────────────────────────────────────────────────


@pytest.fixture
def sample_code_diff():
    """A realistic Python code diff for testing."""
    return (
        "diff --git a/src/service.py b/src/service.py\n"
        "index 0000000..1111111 100644\n"
        "--- a/src/service.py\n"
        "+++ b/src/service.py\n"
        "@@ -10,3 +10,5 @@\n"
        " class UserService:\n"
        "+    def create_user(self, name: str) -> User:\n"
        "+        return User(name=name)\n"
    )


@pytest.fixture
def sample_doc_diff():
    """A documentation-only diff for testing."""
    return (
        "diff --git a/README.md b/README.md\n"
        "index 0000000..1111111 100644\n"
        "--- a/README.md\n"
        "+++ b/README.md\n"
        "@@ -1,2 +1,3 @@\n"
        " # Project\n"
        "+Added usage instructions.\n"
    )
