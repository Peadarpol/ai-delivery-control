"""
Integration tests for the Framework Upgrade Script and Downgrade chains.
"""

import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure we can import from the bootstrap package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bootstrap import manifest, checksums, upgrade, downgrade, generate_checksums

def test_upgrade_dry_run(fresh_v110_project, capsys):
    """Verify --dry-run prints report, performs zero writes, and does not create backup."""
    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=True, force=True)
    with pytest.raises(SystemExit) as excinfo:
        manager.run_upgrade(skip_preflight=True)
    assert excinfo.value.code == 0
    
    # Check stdout/stderr
    captured = capsys.readouterr()
    assert "DRY RUN MODE" in captured.out
    assert "MIGRATION CHAIN TO APPLY" in captured.out
    assert "FILES TO OVERWRITE" in captured.out
    
    # Verify no backup directory was created
    backup_dir = fresh_v110_project / ".agent_backup_upgrade"
    assert not backup_dir.exists()
    
    # Verify files were not modified
    config_yaml = fresh_v110_project / ".agent" / "config.yaml"
    content = config_yaml.read_text(encoding="utf-8")
    assert "local_provider: \"ollama\"" in content
    assert "framework.version" not in content # v1.1.0 template doesn't have framework: block nested
    
    # State file should not be written
    state_file = fresh_v110_project / ".agent" / ".framework_migration_state"
    assert not state_file.exists()

def test_upgrade_full_success(fresh_v110_project):
    """Verify full interactive/force upgrade successfully migrates configurations and framework files."""
    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager.run_upgrade(skip_preflight=True)
    
    # Check framework files overwritten correctly
    gov_file = fresh_v110_project / ".agent" / "governance.md"
    assert gov_file.exists()
    
    # Check config.yaml was cleanly migrated
    config_yaml = fresh_v110_project / ".agent" / "config.yaml"
    config_content = config_yaml.read_text(encoding="utf-8")
    
    assert "budget_provider: \"ollama\"  # local_provider comment" in config_content
    assert "budget_model: \"gemma4\"" in config_content
    assert "review_provider: \"anthropic\"" in config_content
    
    # Assert key injections
    assert "budget_provider_timeout_seconds: 3" in config_content
    assert "budget_base_url" in config_content
    assert "review:" in config_content
    assert "large_diff_threshold: 400" in config_content
    assert "char_to_token_ratio:" in config_content
    assert "review: 4.0" in config_content
    assert "budget: 3.5" in config_content
    assert "session_token_budget: null" in config_content
    
    # State file should be successfully created
    state_file = fresh_v110_project / ".agent" / ".framework_migration_state"
    assert state_file.exists()
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["current_version"] == "1.3.0"
    assert any("v1_1_0_to_v1_1_5" in m for m in state["applied_migrations"])
    
    # Backup directory must be deleted on successful exit
    backup_dir = fresh_v110_project / ".agent_backup_upgrade"
    assert not backup_dir.exists()
    
    # Verify .gitignore entries added
    gitignore = fresh_v110_project / ".gitignore"
    assert gitignore.exists()
    gi_content = gitignore.read_text(encoding="utf-8")
    assert "*.framework-v*" in gi_content
    assert "/.agent_backup_upgrade/" in gi_content

def test_upgrade_conflict_with_sidecar(modified_v110_project):
    """Verify that a modified framework file triggers CONFLICT, preserves developer edit, and writes sidecar."""
    manager = upgrade.UpgradeManager(modified_v110_project, dry_run=False, force=True)
    manager.run_upgrade(skip_preflight=True)
    
    # governance.md was modified in fixture, so it should keep custom developer rule
    gov_file = modified_v110_project / ".agent" / "governance.md"
    gov_content = gov_file.read_text(encoding="utf-8")
    assert "# Custom developer rule" in gov_content
    
    # A conflict sidecar should be created containing the framework v1.2.0.1 version
    sidecar_file = modified_v110_project / ".agent" / "governance.md.framework-v1.3.0"
    assert sidecar_file.exists()
    sidecar_content = sidecar_file.read_text(encoding="utf-8")
    assert "# Custom developer rule" not in sidecar_content

def test_atomic_restore_on_failure(fresh_v110_project):
    """Verify that any exception during upgrade triggers a complete restore of original state."""
    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    
    class FailureMigration:
        from_version = "1.1.0"
        to_version = "1.2.0"
        __name__ = "FailureMigration"
        def migrate(self, config_path):
            raise ValueError("Simulated Error")
        def downgrade(self, config_path):
            pass
            
    # Force an exception by patching load_migration_module
    with patch.object(upgrade.UpgradeManager, "load_migration_module", return_value=FailureMigration()):
        with pytest.raises(SystemExit) as excinfo:
            manager.run_upgrade()
        assert excinfo.value.code == 1
            
    # Verify config.yaml was restored and not left in partially migrated state
    config_yaml = fresh_v110_project / ".agent" / "config.yaml"
    config_content = config_yaml.read_text(encoding="utf-8")
    assert "local_provider: \"ollama\"" in config_content
    assert "budget_provider" not in config_content
    
    # Backup directory should still be deleted/cleaned
    backup_dir = fresh_v110_project / ".agent_backup_upgrade"
    assert not backup_dir.exists()

def test_already_upgraded_re_verify_mode(fresh_v110_project, capsys):
    """Verify that re-running upgrade on v1.2.0 skips writing and enters re-verify mode."""
    # Run first upgrade to reach v1.2.0
    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager.run_upgrade(skip_preflight=True)
    capsys.readouterr() # clear buffer

    # Run second time
    manager.run_upgrade(skip_preflight=True)
    captured = capsys.readouterr()
    assert "Project is already at version 1.3.0" in captured.out

def test_adversarial_empty_config(malformed_config_project):
    """Verify that a malformed/empty config.yaml triggers validation errors and aborts safely."""
    manager = upgrade.UpgradeManager(malformed_config_project, dry_run=False, force=True)
    with pytest.raises(SystemExit):
        manager.run_upgrade()
        
    # State file should not be written
    state_file = malformed_config_project / ".agent" / ".framework_migration_state"
    assert not state_file.exists()

def test_adversarial_directory_conflict(fresh_v110_project):
    """Verify that a target FRAMEWORK_OWNED entry being a directory triggers CONFLICT gracefully."""
    # Replace .agent/governance.md (which is framework owned) with a directory
    gov_file = fresh_v110_project / ".agent" / "governance.md"
    gov_file.unlink()
    gov_file.mkdir()

    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    # Should complete without crash
    manager.run_upgrade(skip_preflight=True)
    assert gov_file.is_dir()

def test_stale_backup_blocks_upgrade_without_force(fresh_v110_project):
    """A stale .yaml.migration_backup must block upgrade unless --force is passed."""
    config_backup = fresh_v110_project / ".agent" / "config.yaml.migration_backup"
    config_backup.write_text("stale backup content", encoding="utf-8")

    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=False)
    with pytest.raises(SystemExit) as excinfo:
        manager.run_upgrade()
    assert excinfo.value.code == 1
    assert config_backup.exists()


def test_stale_backup_override_with_force(fresh_v110_project):
    """--force must allow upgrade to proceed past a stale backup."""
    config_backup = fresh_v110_project / ".agent" / "config.yaml.migration_backup"
    config_backup.write_text("stale backup content", encoding="utf-8")

    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager.run_upgrade(skip_preflight=True)

    state_file = fresh_v110_project / ".agent" / ".framework_migration_state"
    assert state_file.exists()


def test_atomic_config_rollback_on_migration_failure(fresh_v110_project):
    """If a config migration raises an exception, config.yaml must be restored."""
    original_config = (fresh_v110_project / ".agent" / "config.yaml").read_text(encoding="utf-8")

    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)

    class FailingMigration:
        from_version = "1.1.0"
        to_version = "1.2.0"
        FROM_VERSION = "1.1.0"
        TO_VERSION = "1.2.0"
        MIGRATION_TYPE = "minor"
        __name__ = "FailingMigration"

        def migrate(self, config_path):
            config_path.write_text("PARTIALLY WRITTEN", encoding="utf-8")
            raise RuntimeError("Simulated config migration failure")

        def downgrade(self, config_path):
            pass

    with patch.object(upgrade.UpgradeManager, "_assert_chain_contiguous", return_value=[FailingMigration()]):
        with pytest.raises(SystemExit) as excinfo:
            manager.run_upgrade(skip_preflight=True)
        assert excinfo.value.code == 1

    restored = (fresh_v110_project / ".agent" / "config.yaml").read_text(encoding="utf-8")
    assert restored == original_config
    # Backup must be cleaned up after rollback
    backup = fresh_v110_project / ".agent" / "config.yaml.migration_backup"
    assert not backup.exists()


def test_preflight_halts_on_too_many_mismatches(fresh_v110_project):
    """Pre-flight check must exit 1 when >3 files mismatch expected checksums."""
    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    # Corrupt all framework files by overwriting them
    for rel in [
        "src/scripts/ai_review.py",
        "src/scripts/providers.py",
        ".agent/scripts/init_session.py",
        ".agent/AGENTS.md",
    ]:
        target = fresh_v110_project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("CORRUPTED CONTENT", encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        manager._pre_flight_check("1.1.0", skip=False)
    assert excinfo.value.code == 1


def test_preflight_passes_within_threshold(fresh_v110_project):
    """Pre-flight check must not halt when mismatch count is within threshold (≤3).

    We inject a tiny fake registry (4 files) and mock compute_sha256 so that exactly
    1 file mismatches — well within the >3 halt threshold.
    """
    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)

    # Only the two files that EXIST in fresh_v110_project with real content
    fake_registry = {
        "src/scripts/ai_review.py": "EXPECTED_HASH_A",
        "src/scripts/providers.py":  "EXPECTED_HASH_B",
        ".agent/AGENTS.md":          "EXPECTED_HASH_C",
        ".agent/governance.md":      "EXPECTED_HASH_D",
    }

    def mock_sha256(path):
        rel = path.relative_to(fresh_v110_project).as_posix()
        if rel == "src/scripts/ai_review.py":
            return "WRONG_HASH"           # 1 mismatch
        return fake_registry.get(rel, "EXPECTED_HASH_X")  # all others match

    from bootstrap import checksums as _cs, generate_checksums as gc_mod

    with patch.object(_cs, "V1_1_0", fake_registry):
        with patch.object(gc_mod, "compute_sha256", side_effect=mock_sha256):
            # 1 mismatch ≤ threshold of 3 → must not raise SystemExit
            manager._pre_flight_check("1.1.0", skip=False)


def test_preflight_skip_flag_bypasses_check(fresh_v110_project):
    """--skip-preflight must bypass the pre-flight check entirely."""
    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    # Corrupt many files — would normally halt
    for rel in [
        "src/scripts/ai_review.py",
        "src/scripts/providers.py",
        ".agent/scripts/init_session.py",
        ".agent/AGENTS.md",
        ".agent/scripts/check_halt.py",
    ]:
        target = fresh_v110_project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("CORRUPTED", encoding="utf-8")

    # With skip=True, must not raise SystemExit
    manager._pre_flight_check("1.1.0", skip=True)


def test_chain_fork_resolution_picks_correct_branch(tmp_path):
    """When two modules share FROM_VERSION='1.1.5', the minor-branch module is selected for target 1.2.0."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    (agent_dir / "config.yaml").write_text("framework:\n  version: \"1.1.5\"\n", encoding="utf-8")
    (agent_dir / ".framework_migration_state").write_text(
        '{"current_version": "1.1.5"}', encoding="utf-8"
    )

    class PatchMigration:
        from_version = "1.1.5"
        to_version = "1.1.5.1"
        FROM_VERSION = "1.1.5"
        TO_VERSION = "1.1.5.1"
        MIGRATION_TYPE = "patch"
        __name__ = "PatchMigration"
        migrated = False

        def migrate(self, p):
            PatchMigration.migrated = True

        def downgrade(self, p):
            pass

    class MinorMigration:
        from_version = "1.1.5"
        to_version = "1.2.0"
        FROM_VERSION = "1.1.5"
        TO_VERSION = "1.2.0"
        MIGRATION_TYPE = "minor"
        __name__ = "MinorMigration"
        migrated = False

        def migrate(self, p):
            MinorMigration.migrated = True

        def downgrade(self, p):
            pass

    manager = upgrade.UpgradeManager(tmp_path, dry_run=False, force=True, target_version="1.2.0")

    from packaging.version import Version

    raw = [
        (Version("1.1.5"), Version("1.1.5.1"), None),
        (Version("1.1.5"), Version("1.2.0"), None),
    ]

    patch_mod = PatchMigration()
    minor_mod = MinorMigration()

    with patch.object(upgrade.UpgradeManager, "load_migration_module", side_effect=[patch_mod, minor_mod]):
        chain = manager._assert_chain_contiguous(raw, "1.1.5")

    assert len(chain) == 1
    assert chain[0] is minor_mod, "Minor branch must be selected when upgrading to 1.2.0"


def test_downgrade_full_success(fresh_v110_project):
    """Verify full downgrade reverts configurations to v1.1.0 keys and version markers."""
    # 1. Run upgrade to v1.2.0
    manager_up = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager_up.run_upgrade(skip_preflight=True)
    
    # 2. Run downgrade back to v1.1.0
    manager_down = downgrade.DowngradeManager(fresh_v110_project, dry_run=False, force=True, to_version="1.1.0")
    manager_down.run_downgrade()
    
    # Verify config.yaml keys reverted
    config_yaml = fresh_v110_project / ".agent" / "config.yaml"
    config_content = config_yaml.read_text(encoding="utf-8")
    
    assert "local_provider:" in config_content
    assert "local_model:" in config_content
    assert "cloud_provider:" in config_content
    
    # Injected keys removed
    assert "budget_provider_timeout_seconds" not in config_content
    assert "budget_base_url" not in config_content
    assert "large_diff_threshold" not in config_content
    assert "char_to_token_ratio" not in config_content
    assert "session_token_budget" not in config_content
    
    # State file updated to v1.1.0
    state_file = fresh_v110_project / ".agent" / ".framework_migration_state"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["current_version"] == "1.1.0"


# ── Patch Release 1.2.0.1 upgrade/downgrade ───────────────────────────────────


def test_upgrade_and_downgrade_v1_2_0_1(fresh_v110_project):
    """Verify upgrading to v1.2.0.1 appends gitignore and downgrading reverts it."""
    # 1. Upgrade from 1.1.0 to 1.2.0 first
    manager_up = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager_up.target_version = "1.2.0"
    manager_up.run_upgrade(skip_preflight=True)
    
    state_file = fresh_v110_project / ".agent" / ".framework_migration_state"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["current_version"] == "1.2.0"
    
    # Gitignore in target project should not have the v1.2.0.1 specific entries yet
    gitignore = fresh_v110_project / ".gitignore"
    gi_content = gitignore.read_text(encoding="utf-8")
    assert ".agent/state/session.json" not in gi_content
    
    # 2. Upgrade to 1.2.0.1
    manager_up_patch = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager_up_patch.target_version = "1.2.0.1"
    manager_up_patch.run_upgrade(skip_preflight=True)
    
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["current_version"] == "1.2.0.1"
    
    # Verify .gitignore entries appended
    gi_content = gitignore.read_text(encoding="utf-8")
    assert "# AI Delivery Control — operational state (not project history)" in gi_content
    assert ".agent/state/session.json" in gi_content
    assert ".agent/state/HALT" in gi_content
    assert ".agent/wiki/" in gi_content
    
    # Verify idempotency: run upgrade again
    manager_up_patch.run_upgrade(skip_preflight=True)
    gi_content_after = gitignore.read_text(encoding="utf-8")
    assert gi_content_after.count("# AI Delivery Control") == 1  # Not duplicated
    
    # 3. Downgrade back to 1.2.0
    manager_down_patch = downgrade.DowngradeManager(fresh_v110_project, dry_run=False, force=True, to_version="1.2.0")
    manager_down_patch.run_downgrade()
    
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["current_version"] == "1.2.0"
    
    # Verify .gitignore entries were cleanly removed
    gi_content_down = gitignore.read_text(encoding="utf-8")
    assert "# AI Delivery Control" not in gi_content_down
    assert ".agent/state/session.json" not in gi_content_down

