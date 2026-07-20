"""
Unit tests for bootstrap.migrations.v1_4_9_to_v1_4_10 configuration migration.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bootstrap.migrations.v1_4_9_to_v1_4_10 import MigrationV1_4_9_to_V1_4_10


def test_migration_v1_4_9_to_v1_4_10_migrate_and_downgrade(tmp_path):
    """Verify migrate() bumps 1.4.9 -> 1.4.10 and downgrade() reverts 1.4.10 -> 1.4.9."""
    config_file = tmp_path / "config.yaml"
    initial_content = 'version: "1.4.9"\nouter_loop:\n  mode: "strict"\n'
    config_file.write_text(initial_content, encoding="utf-8")

    migration = MigrationV1_4_9_to_V1_4_10()

    # Step 1: Migrate
    migration.migrate(config_file)
    migrated_content = config_file.read_text(encoding="utf-8")
    assert 'version: "1.4.10"' in migrated_content

    # Step 2: Downgrade
    migration.downgrade(config_file)
    downgraded_content = config_file.read_text(encoding="utf-8")
    assert 'version: "1.4.9"' in downgraded_content


def test_migration_v1_4_9_to_v1_4_10_missing_file(tmp_path):
    """Verify migrate() and downgrade() raise FileNotFoundError for nonexistent config."""
    config_file = tmp_path / "nonexistent.yaml"
    migration = MigrationV1_4_9_to_V1_4_10()

    with pytest.raises(FileNotFoundError):
        migration.migrate(config_file)

    with pytest.raises(FileNotFoundError):
        migration.downgrade(config_file)


def test_migration_v1_4_9_to_v1_4_10_missing_version_key(tmp_path):
    """Verify migrate() and downgrade() raise ValueError when version key is absent."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text('outer_loop:\n  mode: "strict"\n', encoding="utf-8")

    migration = MigrationV1_4_9_to_V1_4_10()

    with pytest.raises(ValueError, match="Version key not found"):
        migration.migrate(config_file)

    with pytest.raises(ValueError, match="Version key not found"):
        migration.downgrade(config_file)
