"""
Unit tests for migration v1.4.11 -> v1.4.12.
"""

from pathlib import Path
import pytest
from bootstrap.migrations.v1_4_11_to_v1_4_12 import MigrationV1_4_11_to_V1_4_12


def test_migration_v1_4_11_to_v1_4_12_migrate_and_downgrade(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text('version: "1.4.11"\narchitecture:\n  layers:\n    domain: ["src/domain"]\n', encoding="utf-8")

    migration = MigrationV1_4_11_to_V1_4_12()
    migration.migrate(config_file)

    content = config_file.read_text(encoding="utf-8")
    assert 'version: "1.4.12"' in content
    assert 'enforcement:' in content
    assert 'posture: strict' in content
    assert 'observe_expires: null' in content
    assert 'rule_overrides: {}' in content

    migration.downgrade(config_file)
    content_downgraded = config_file.read_text(encoding="utf-8")
    assert 'version: "1.4.11"' in content_downgraded
    assert 'enforcement:' not in content_downgraded


def test_migration_v1_4_11_to_v1_4_12_missing_file(tmp_path: Path):
    missing_file = tmp_path / "nonexistent.yaml"
    migration = MigrationV1_4_11_to_V1_4_12()
    with pytest.raises(FileNotFoundError):
        migration.migrate(missing_file)


def test_migration_v1_4_11_to_v1_4_12_missing_version_key(tmp_path: Path):
    config_file = tmp_path / "invalid_config.yaml"
    config_file.write_text('architecture:\n  layers:\n    domain: ["src/domain"]\n', encoding="utf-8")
    migration = MigrationV1_4_11_to_V1_4_12()
    with pytest.raises((ValueError, RuntimeError)):
        migration.migrate(config_file)
