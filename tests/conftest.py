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


def _get_git_v110_file(rel_path: str) -> str:
    """Retrieve file content from git v1.1.0 tag, falling back gracefully."""
    import subprocess
    try:
        # Resolve path correctly
        res = subprocess.run(
            ["git", "show", f"v1.1.0:{rel_path}"],
            capture_output=True,
            encoding="utf-8",
            check=True,
            cwd=str(WORKSPACE_ROOT)
        )
        return res.stdout
    except Exception:
        # Fallback mock contents that match our testing expectations
        if rel_path == ".agent/governance.md":
            return "mock governance content for v1.1.0"
        elif "ai_review.py" in rel_path:
            return "mock ai_review content for v1.1.0"
        return "mock content"


@pytest.fixture
def fresh_v110_project(tmp_path):
    """Create a temporary project directory populated with a minimal valid v1.1.0 layout."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "scripts").mkdir()
    (agent_dir / "workflows").mkdir()
    (agent_dir / "skills").mkdir()
    (agent_dir / "config").mkdir()
    
    # 1. Scaffold config.yaml in v1.1.0 format
    config_content = """# AI Delivery Control - Config v1.1.0
framework:
  version: "1.1.0"
  repo: "https://github.com/Peadarpol/ai-delivery-control"
  installed_at: "2026-05-20"

project:
  name: "MockProject"

model_routing:
  local_provider: "ollama"  # local_provider comment
  local_model: "gemma4"
  local_tasks:
    - wiki_compile
    - knowledge_lint
  cloud_provider: "anthropic"
  cloud_model: "claude-sonnet"

token_tracking:
  some_key: "value"

paths:
  source_root: "src"

domain_constraints:
  - "Tenant Isolation"
"""
    (agent_dir / "config.yaml").write_text(config_content, encoding="utf-8")
    
    # 2. Write skill_ownership.yaml
    (agent_dir / "config" / "skill_ownership.yaml").write_text("skills:\n  - api-design", encoding="utf-8")

    # 3. Pull actual v1.1.0 contents for manifest framework files
    gov_content = _get_git_v110_file(".agent/governance.md")
    (agent_dir / "governance.md").write_text(gov_content, encoding="utf-8")
    
    (agent_dir / "AGENTS.md").write_text(_get_git_v110_file(".agent/AGENTS.md"), encoding="utf-8")
    
    # Decisions Log
    decisions_log = """## 2026-05-26: Componentized Bidirectional Upgrade & Downgrade Manager
- **Decision**: Developed a highly componentized and isolated upgrade/downgrade system consisting of `manifest.py` (file registry), `migration_base.py` (runtime @runtime_checkable MigrationProtocol contract), `checksums.py` (CRLF-normalized digest registry), `upgrade.py` (atomic upgrade CLI tool), `downgrade.py` (reversion CLI tool), and isolated config migration step modules.
- **Context**: Portability and system safety dictate that framework file registry, version registries, and migration steps remain logically detached from CLI runners. Upgrades must be fully atomic to prevent corruptions during failures, and downgrades must cleanly revert custom modifications.
- **Consequence**: Delivers robust dry-runs, colorized ANSI unified diffs, auto-exits, and timestamped backups. An failure mid-upgrade automatically triggers a complete rollback restore of the original system files (including `.gitignore`).

## 2026-05-26: Automated Diagnostic Onboarding Assistant
- **Decision**: Scaffolded a beautiful first-session onboarding workflow `.agent/workflows/onboarding.md` coupled with a zero-dependency diagnostic onboarding runner `.agent/scripts/onboarding.py`.
- **Context**: Helping developers get up to speed with process configurations, gating tests, reachability checks, and git hooks wiring needs to be smooth and wows-at-first-glance.
- **Consequence**: Automates reachability checks across Ollama/localhost vs cloud models, performs local test suite execution, checks git hook status, and automatically outputs a dated `onboarding_baseline_{YYYY-MM-DD}.md` snapshot for future debugging and regression verification.
"""
    (agent_dir / "decisions_log.md").write_text(decisions_log, encoding="utf-8")
    
    # Src scripts scripts/ai_review.py
    src_scripts = tmp_path / "src" / "scripts"
    src_scripts.mkdir(parents=True)
    
    ai_rev_content = _get_git_v110_file("src/scripts/ai_review.py")
    (src_scripts / "ai_review.py").write_text(ai_rev_content, encoding="utf-8")
    
    (src_scripts / "providers.py").write_text(_get_git_v110_file("src/scripts/providers.py"), encoding="utf-8")
    (src_scripts / "review_context_universal.md").write_text(_get_git_v110_file("src/scripts/review_context_universal.md"), encoding="utf-8")

    # 4. Scaffold .gitignore
    (tmp_path / ".gitignore").write_text("/node_modules/\n", encoding="utf-8")
    
    return tmp_path


@pytest.fixture
def modified_v110_project(fresh_v110_project):
    """A fresh v1.1.0 project but with a developer customized governance.md to trigger CONFLICT."""
    gov_file = fresh_v110_project / ".agent" / "governance.md"
    gov_file.write_text(gov_file.read_text(encoding="utf-8") + "\n# Custom developer rule\n", encoding="utf-8")
    return fresh_v110_project


@pytest.fixture
def malformed_config_project(fresh_v110_project):
    """A fresh v1.1.0 project but with an empty/malformed config.yaml."""
    config_file = fresh_v110_project / ".agent" / "config.yaml"
    config_file.write_text("", encoding="utf-8")
    return fresh_v110_project

