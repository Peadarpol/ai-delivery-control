"""
Unit/integration tests for the Framework Uninstall Utility (bootstrap/uninstall.py).
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bootstrap import uninstall, manifest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _scaffold_installed_project(tmp_path: Path, version: str = "1.2.0") -> Path:
    """Scaffold a minimal installed framework project for uninstall testing."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    scripts_dir = agent_dir / "scripts"
    scripts_dir.mkdir()
    workflows_dir = agent_dir / "workflows"
    workflows_dir.mkdir()

    # Framework state file (signals active installation)
    state = {"current_version": version, "applied_migrations": [], "last_upgraded": "2026-05-30"}
    (agent_dir / ".framework_migration_state").write_text(json.dumps(state), encoding="utf-8")

    # A few framework-owned files
    (scripts_dir / "check_halt.py").write_text("# check_halt", encoding="utf-8")
    (scripts_dir / "init_session.py").write_text("# init_session", encoding="utf-8")
    (workflows_dir / "feature-implementation.md").write_text("# feature impl", encoding="utf-8")
    (agent_dir / "governance.md").write_text("# governance", encoding="utf-8")
    (agent_dir / "AGENTS.md").write_text("# agents", encoding="utf-8")
    (agent_dir / "config.yaml").write_text("framework:\n  version: '1.2.0'\n", encoding="utf-8")

    src_scripts = tmp_path / "src" / "scripts"
    src_scripts.mkdir(parents=True)
    (src_scripts / "ai_review.py").write_text("# ai_review", encoding="utf-8")
    (src_scripts / "providers.py").write_text("# providers", encoding="utf-8")

    # Pre-commit config with a harness hook
    (tmp_path / ".pre-commit-config.yaml").write_text(
        "repos:\n- repo: local\n  hooks:\n  - id: ai-review-gate\n    name: AI Review Gate\n    entry: python src/scripts/ai_review.py\n    language: python\n",
        encoding="utf-8",
    )

    return tmp_path


# ── Guard: no state file ────────────────────────────────────────────────────────

def test_uninstall_exits_without_state_file(tmp_path, capsys):
    """Uninstaller must exit with code 1 when no .framework_migration_state is found."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=False, force=True)
    with pytest.raises(SystemExit) as excinfo:
        manager.run_uninstall()
    assert excinfo.value.code == 1


# ── Dry-run ─────────────────────────────────────────────────────────────────────

def test_uninstall_dry_run_makes_no_changes(tmp_path, capsys):
    """--dry-run must print removal report without deleting any files."""
    _scaffold_installed_project(tmp_path)
    manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=True, force=False)
    manager.run_uninstall()

    captured = capsys.readouterr()
    assert "[DRY RUN]" in captured.out

    # State file must still exist
    state_file = tmp_path / ".agent" / ".framework_migration_state"
    assert state_file.exists()

    # Framework files must still exist
    assert (tmp_path / ".agent" / "scripts" / "check_halt.py").exists()
    assert (tmp_path / "src" / "scripts" / "ai_review.py").exists()


def test_uninstall_dry_run_suppresses_prompts(tmp_path, capsys):
    """--dry-run must print [DRY RUN] Would prompt for interactive checks, never call input()."""
    _scaffold_installed_project(tmp_path)
    # Add a spec file to trigger developer content detection
    specs_dir = tmp_path / "docs" / "planning" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "SPEC-001.md").write_text("# Spec 001", encoding="utf-8")

    with patch("builtins.input") as mock_input:
        manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=True, force=False)
        manager.run_uninstall()
        mock_input.assert_not_called()

    captured = capsys.readouterr()
    assert "[DRY RUN] Would prompt" in captured.out


# ── Force ───────────────────────────────────────────────────────────────────────

def test_uninstall_force_skips_prompts_and_removes_files(tmp_path):
    """--force must remove files without prompting the user."""
    _scaffold_installed_project(tmp_path)
    with patch("builtins.input") as mock_input:
        manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=False, force=True)
        manager.run_uninstall()
        mock_input.assert_not_called()

    # State file must be gone
    state_file = tmp_path / ".agent" / ".framework_migration_state"
    assert not state_file.exists()


def test_dry_run_takes_precedence_over_force(tmp_path):
    """When both --dry-run and --force are supplied, --dry-run wins — nothing is deleted."""
    _scaffold_installed_project(tmp_path)
    # dry_run=True, force=False (force is suppressed by dry-run in main() before UninstallManager)
    manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=True, force=False)
    manager.run_uninstall()

    state_file = tmp_path / ".agent" / ".framework_migration_state"
    assert state_file.exists()


# ── Safety gating ───────────────────────────────────────────────────────────────

def test_uninstall_prompts_on_developer_content_and_cancels(tmp_path, capsys):
    """Developer spec files must trigger a confirmation prompt; 'n' cancels uninstall."""
    _scaffold_installed_project(tmp_path)
    specs_dir = tmp_path / "docs" / "planning" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "SPEC-001.md").write_text("# Spec 001", encoding="utf-8")

    with patch("builtins.input", return_value="n"):
        with pytest.raises(SystemExit) as excinfo:
            manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=False, force=False)
            manager.run_uninstall()
    assert excinfo.value.code == 0

    # Files must be untouched
    assert (tmp_path / ".agent" / ".framework_migration_state").exists()


def test_uninstall_continues_on_yes_confirmation(tmp_path):
    """Answering 'y' to developer content prompt allows uninstall to proceed."""
    _scaffold_installed_project(tmp_path)
    specs_dir = tmp_path / "docs" / "planning" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "SPEC-001.md").write_text("# Spec 001", encoding="utf-8")

    with patch("builtins.input", return_value="y"):
        manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=False, force=False)
        manager.run_uninstall()

    # State file should be gone
    assert not (tmp_path / ".agent" / ".framework_migration_state").exists()


# ── Manifest dynamic expansion ──────────────────────────────────────────────────

def test_manifest_expand_finds_framework_files(tmp_path):
    """_expand_framework_files must discover files matching FRAMEWORK_OWNED patterns."""
    _scaffold_installed_project(tmp_path)
    framework_path = Path(__file__).resolve().parents[1]
    found = uninstall._expand_framework_files(tmp_path, framework_path)
    rel_paths = {f.relative_to(tmp_path).as_posix() for f in found}

    assert ".agent/scripts/check_halt.py" in rel_paths
    assert "src/scripts/ai_review.py" in rel_paths
    assert ".agent/governance.md" in rel_paths


# ── Clean removal ───────────────────────────────────────────────────────────────

def test_uninstall_removes_framework_files(tmp_path):
    """Full uninstall must remove all discovered framework-owned files."""
    _scaffold_installed_project(tmp_path)
    manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=False, force=True)
    manager.run_uninstall()

    assert not (tmp_path / ".agent" / "scripts" / "check_halt.py").exists()
    assert not (tmp_path / "src" / "scripts" / "ai_review.py").exists()
    assert not (tmp_path / ".agent" / ".framework_migration_state").exists()


def test_uninstall_removes_stale_migration_backup(tmp_path):
    """Stale .yaml.migration_backup must be removed during uninstall."""
    _scaffold_installed_project(tmp_path)
    backup = tmp_path / ".agent" / "config.yaml.migration_backup"
    backup.write_text("backup content", encoding="utf-8")

    manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=False, force=True)
    manager.run_uninstall()

    assert not backup.exists()


def test_uninstall_state_file_removed_last(tmp_path):
    """State file (.framework_migration_state) must be removed as the final step."""
    _scaffold_installed_project(tmp_path)
    removal_order = []

    original_remove = uninstall.UninstallManager._remove

    def tracking_remove(self, path):
        removal_order.append(path.name)
        original_remove(self, path)

    with patch.object(uninstall.UninstallManager, "_remove", tracking_remove):
        manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=False, force=True)
        manager.run_uninstall()

    assert removal_order[-1] == ".framework_migration_state"


def test_uninstall_prunes_harness_hooks_from_precommit(tmp_path):
    """Harness hook entries must be pruned from .pre-commit-config.yaml."""
    _scaffold_installed_project(tmp_path)
    manager = uninstall.UninstallManager(project_path=tmp_path, dry_run=False, force=True)
    manager.run_uninstall()

    precommit = tmp_path / ".pre-commit-config.yaml"
    # Either the file is deleted (empty) or the ai-review-gate entry is gone
    if precommit.exists():
        assert "ai-review-gate" not in precommit.read_text(encoding="utf-8")
