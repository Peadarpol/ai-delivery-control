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
        manager.run_upgrade()
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
    manager.run_upgrade()
    
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
    assert state["current_version"] == "1.1.5.2"
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
    manager.run_upgrade()
    
    # governance.md was modified in fixture, so it should keep custom developer rule
    gov_file = modified_v110_project / ".agent" / "governance.md"
    gov_content = gov_file.read_text(encoding="utf-8")
    assert "# Custom developer rule" in gov_content
    
    # A conflict sidecar should be created containing the framework v1.1.5.2 version
    sidecar_file = modified_v110_project / ".agent" / "governance.md.framework-v1.1.5.2"
    assert sidecar_file.exists()
    sidecar_content = sidecar_file.read_text(encoding="utf-8")
    assert "# Custom developer rule" not in sidecar_content

def test_atomic_restore_on_failure(fresh_v110_project):
    """Verify that any exception during upgrade triggers a complete restore of original state."""
    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    
    class FailureMigration:
        from_version = "1.1.0"
        to_version = "1.1.5.2"
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
    """Verify that re-running upgrade on v1.1.5.2 skips writing and enters re-verify mode."""
    # Run first upgrade to reach v1.1.5.2
    manager = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager.run_upgrade()
    capsys.readouterr() # clear buffer
    
    # Run second time
    manager.run_upgrade()
    captured = capsys.readouterr()
    assert "Project is already at version 1.1.5.2" in captured.out

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
    manager.run_upgrade()
    assert gov_file.is_dir()

def test_downgrade_full_success(fresh_v110_project):
    """Verify full downgrade reverts configurations to v1.1.0 keys and version markers."""
    # 1. Run upgrade to v1.1.5.2
    manager_up = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager_up.run_upgrade()
    
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
