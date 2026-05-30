"""
Integration tests for the Framework Downgrade Utility (bootstrap/downgrade.py).
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bootstrap import downgrade, upgrade


def test_stale_backup_blocks_downgrade_without_force(fresh_v110_project):
    """A stale .yaml.migration_backup must block downgrade unless --force is supplied."""
    # First upgrade so we have something to downgrade from
    manager_up = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager_up.run_upgrade(skip_preflight=True)

    config_backup = fresh_v110_project / ".agent" / "config.yaml.migration_backup"
    config_backup.write_text("stale content", encoding="utf-8")

    manager_down = downgrade.DowngradeManager(fresh_v110_project, dry_run=False, force=False, to_version="1.1.0")
    with pytest.raises(SystemExit) as excinfo:
        manager_down.run_downgrade()
    assert excinfo.value.code == 1
    assert config_backup.exists()


def test_stale_backup_override_with_force(fresh_v110_project):
    """--force must allow downgrade to proceed past a stale backup."""
    manager_up = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager_up.run_upgrade(skip_preflight=True)

    config_backup = fresh_v110_project / ".agent" / "config.yaml.migration_backup"
    config_backup.write_text("stale content", encoding="utf-8")

    manager_down = downgrade.DowngradeManager(fresh_v110_project, dry_run=False, force=True, to_version="1.1.0")
    manager_down.run_downgrade()

    state_file = fresh_v110_project / ".agent" / ".framework_migration_state"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["current_version"] == "1.1.0"


def test_atomic_rollback_on_downgrade_failure(fresh_v110_project):
    """If downgrade() raises after backup is written, config.yaml must be restored to pre-downgrade state."""
    # Upgrade first
    manager_up = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager_up.run_upgrade(skip_preflight=True)

    pre_downgrade_config = (fresh_v110_project / ".agent" / "config.yaml").read_text(encoding="utf-8")

    class FailingDowngradeMigration:
        from_version = "1.1.0"
        to_version = "1.2.0"
        __name__ = "FailingDowngradeMigration"

        def migrate(self, p):
            pass

        def downgrade(self, p):
            # Partially corrupt config then raise
            p.write_text("PARTIALLY DOWNGRADED", encoding="utf-8")
            raise RuntimeError("Simulated downgrade failure")

    manager_down = downgrade.DowngradeManager(fresh_v110_project, dry_run=False, force=True, to_version="1.1.0")

    with patch.object(
        downgrade.DowngradeManager,
        "build_reverse_chain",
        return_value=[FailingDowngradeMigration()],
    ):
        with pytest.raises(SystemExit) as excinfo:
            manager_down.run_downgrade()
        assert excinfo.value.code == 1

    # config.yaml must be restored to the pre-downgrade state
    restored_config = (fresh_v110_project / ".agent" / "config.yaml").read_text(encoding="utf-8")
    assert restored_config == pre_downgrade_config

    # Backup must be cleaned up after rollback
    backup = fresh_v110_project / ".agent" / "config.yaml.migration_backup"
    assert not backup.exists()


def test_downgrade_dry_run(fresh_v110_project, capsys):
    """--dry-run must print report and make zero writes."""
    manager_up = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager_up.run_upgrade(skip_preflight=True)

    config_before = (fresh_v110_project / ".agent" / "config.yaml").read_text(encoding="utf-8")

    manager_down = downgrade.DowngradeManager(fresh_v110_project, dry_run=True, force=True, to_version="1.1.0")
    with pytest.raises(SystemExit) as excinfo:
        manager_down.run_downgrade()
    assert excinfo.value.code == 0

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out

    config_after = (fresh_v110_project / ".agent" / "config.yaml").read_text(encoding="utf-8")
    assert config_before == config_after


def test_downgrade_cleans_backup_on_success(fresh_v110_project):
    """On successful downgrade, .yaml.migration_backup must not remain."""
    manager_up = upgrade.UpgradeManager(fresh_v110_project, dry_run=False, force=True)
    manager_up.run_upgrade(skip_preflight=True)

    manager_down = downgrade.DowngradeManager(fresh_v110_project, dry_run=False, force=True, to_version="1.1.0")
    manager_down.run_downgrade()

    backup = fresh_v110_project / ".agent" / "config.yaml.migration_backup"
    assert not backup.exists()
