"""Integration tests for migration v1.1.0 -> v1.1.5."""
from pathlib import Path
import pytest
from bootstrap.migrations.v1_1_0_to_v1_1_5 import MigrationV1_1_0_to_V1_1_5


def test_migration_v1_1_0_to_v1_1_5(tmp_path: Path):
    migration = MigrationV1_1_0_to_V1_1_5()

    # 1. Standard migrate & downgrade with required v1.1.0 keys
    config = tmp_path / "config.yaml"
    config.write_text(
        'framework:\n  version: "1.1.0"\n'
        'local_provider: "ollama"\n'
        'local_model: "llama3"\n'
        'local_tasks: ["task1"]\n'
        'cloud_provider: "anthropic"\n'
        'cloud_model: "claude-3"\n',
        encoding="utf-8"
    )
    migration.migrate(config)
    content = config.read_text(encoding="utf-8")
    assert 'framework:\n  version: "1.1.5"' in content
    assert 'budget_provider: "ollama"' in content

    migration.downgrade(config)
    content_down = config.read_text(encoding="utf-8")
    assert 'framework:\n  version: "1.1.0"' in content_down
    assert 'local_provider: "ollama"' in content_down

    # 2. Clobber prevention (confirm project.version at "0.1.0" is NOT rewritten)
    config_clobber = tmp_path / "config_clobber.yaml"
    config_clobber.write_text(
        'framework:\n  version: "1.1.0"\n'
        'project:\n  version: "0.1.0"\n'
        'local_provider: "ollama"\n'
        'local_model: "llama3"\n'
        'local_tasks: ["task1"]\n',
        encoding="utf-8"
    )
    migration.migrate(config_clobber)
    content_c = config_clobber.read_text(encoding="utf-8")
    assert 'framework:\n  version: "1.1.5"' in content_c
    assert 'project:\n  version: "0.1.0"' in content_c
