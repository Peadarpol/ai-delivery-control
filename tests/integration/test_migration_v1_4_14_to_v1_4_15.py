"""
Unit tests for migration v1.4.14 -> v1.4.15.
Version-bump-only migration: no config.yaml schema changes, so the tests cover the
version-line rewrite itself and its guards (quoting styles, comment skipping,
version-match guard, and the exactly-one-line write verification).
"""

from pathlib import Path
import pytest
from bootstrap.migrations.v1_4_14_to_v1_4_15 import MigrationV1_4_14_to_V1_4_15


def test_migration_v1_4_14_to_v1_4_15_migrate_and_downgrade(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'framework:\n  version: "1.4.14"\n  repository: "https://example.invalid/repo.git"\n',
        encoding="utf-8",
    )

    migration = MigrationV1_4_14_to_V1_4_15()
    migration.migrate(config_file)

    content = config_file.read_text(encoding="utf-8")
    assert '  version: "1.4.15"' in content
    assert "1.4.14" not in content
    assert '  repository: "https://example.invalid/repo.git"' in content

    migration.downgrade(config_file)
    content_downgraded = config_file.read_text(encoding="utf-8")
    assert '  version: "1.4.14"' in content_downgraded
    assert "1.4.15" not in content_downgraded


def test_migration_v1_4_14_to_v1_4_15_unquoted_version(tmp_path: Path):
    """FID-2: an unquoted version value must be updated, not silently skipped."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("framework:\n  version: 1.4.14\n", encoding="utf-8")

    migration = MigrationV1_4_14_to_V1_4_15()
    migration.migrate(config_file)

    assert "  version: 1.4.15\n" in config_file.read_text(encoding="utf-8")

    migration.downgrade(config_file)
    assert "  version: 1.4.14\n" in config_file.read_text(encoding="utf-8")


def test_migration_v1_4_14_to_v1_4_15_single_quoted_version(tmp_path: Path):
    """Single-quoted values are updated and keep their quoting style."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("framework:\n  version: '1.4.14'\n", encoding="utf-8")

    MigrationV1_4_14_to_V1_4_15().migrate(config_file)

    assert "  version: '1.4.15'\n" in config_file.read_text(encoding="utf-8")


def test_migration_v1_4_14_to_v1_4_15_missing_file(tmp_path: Path):
    missing_file = tmp_path / "nonexistent.yaml"
    migration = MigrationV1_4_14_to_V1_4_15()

    with pytest.raises(FileNotFoundError, match="Configuration file not found at"):
        migration.migrate(missing_file)

    with pytest.raises(FileNotFoundError, match="Configuration file not found at"):
        migration.downgrade(missing_file)


def test_migration_v1_4_14_to_v1_4_15_skips_commented_version_line(tmp_path: Path):
    """A commented-out version line is left untouched and does not count as a match."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "framework:\n"
        '  # version: "1.4.14"   <- previous pin, kept for reference\n'
        '  version: "1.4.14"\n',
        encoding="utf-8",
    )

    MigrationV1_4_14_to_V1_4_15().migrate(config_file)

    content = config_file.read_text(encoding="utf-8")
    assert '  # version: "1.4.14"   <- previous pin, kept for reference\n' in content
    assert '  version: "1.4.15"\n' in content


def test_migration_v1_4_14_to_v1_4_15_no_version_line_raises(tmp_path: Path):
    """Zero matching version lines must raise, not report silent success."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "architecture:\n  layers:\n    domain: [\"src/domain\"]\n", encoding="utf-8"
    )

    migration = MigrationV1_4_14_to_V1_4_15()

    with pytest.raises(RuntimeError, match="found 0"):
        migration.migrate(config_file)

    with pytest.raises(RuntimeError, match="found 0"):
        migration.downgrade(config_file)

    # The file must be left exactly as it was found.
    assert config_file.read_text(encoding="utf-8") == (
        "architecture:\n  layers:\n    domain: [\"src/domain\"]\n"
    )


def test_migration_v1_4_14_to_v1_4_15_wrong_version_raises(tmp_path: Path):
    """Version-match guard: a config at another version is not silently rewritten."""
    config_file = tmp_path / "config.yaml"
    original = 'framework:\n  version: "1.3.0"\n'
    config_file.write_text(original, encoding="utf-8")

    migration = MigrationV1_4_14_to_V1_4_15()

    with pytest.raises(ValueError, match="expected version '1.4.14' but found '1.3.0'"):
        migration.migrate(config_file)

    assert config_file.read_text(encoding="utf-8") == original


def test_migration_v1_4_14_to_v1_4_15_leaves_project_version_untouched(tmp_path: Path):
    """Only the framework version at from_version is rewritten; project.version is not."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'framework:\n  version: "1.4.14"\n\nproject:\n  name: "demo"\n  version: "0.1.0"\n',
        encoding="utf-8",
    )

    MigrationV1_4_14_to_V1_4_15().migrate(config_file)

    content = config_file.read_text(encoding="utf-8")
    assert 'framework:\n  version: "1.4.15"\n' in content
    assert '  version: "0.1.0"\n' in content


def test_migration_v1_4_14_to_v1_4_15_ambiguous_version_lines_raise(tmp_path: Path):
    """More than one line at from_version is ambiguous and must raise."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'framework:\n  version: "1.4.14"\n\nproject:\n  version: "1.4.14"\n',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="found 2"):
        MigrationV1_4_14_to_V1_4_15().migrate(config_file)


def test_migration_v1_4_14_to_v1_4_15_preserves_trailing_comment(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'framework:\n  version: "1.4.14"  # harness version of record\n', encoding="utf-8"
    )

    MigrationV1_4_14_to_V1_4_15().migrate(config_file)

    assert (
        '  version: "1.4.15"  # harness version of record\n'
        in config_file.read_text(encoding="utf-8")
    )
