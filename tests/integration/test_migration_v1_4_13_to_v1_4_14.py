"""
Unit tests for migration v1.4.13 -> v1.4.14.
Version-bump-only migration: no config.yaml schema changes, so the tests cover the
version-line rewrite itself and its guards (quoting styles, comment skipping,
version-match guard, and the exactly-one-line write verification).

Includes the permanent regression guard for the project.version clobber: before the
fix, migrate() rewrote every matching `version:` line, so a config carrying both
framework.version and project.version had its project version silently overwritten
with the harness version.
"""

from pathlib import Path
import pytest
from bootstrap.migrations.v1_4_13_to_v1_4_14 import MigrationV1_4_13_to_V1_4_14


def test_migration_v1_4_13_to_v1_4_14_migrate_and_downgrade(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'framework:\n  version: "1.4.13"\n  repository: "https://example.invalid/repo.git"\n',
        encoding="utf-8",
    )

    migration = MigrationV1_4_13_to_V1_4_14()
    migration.migrate(config_file)

    content = config_file.read_text(encoding="utf-8")
    assert '  version: "1.4.14"' in content
    assert "1.4.13" not in content
    assert '  repository: "https://example.invalid/repo.git"' in content

    migration.downgrade(config_file)
    content_downgraded = config_file.read_text(encoding="utf-8")
    assert '  version: "1.4.13"' in content_downgraded
    assert "1.4.14" not in content_downgraded


def test_migration_v1_4_13_to_v1_4_14_unquoted_version(tmp_path: Path):
    """An unquoted version value must be updated, not silently skipped."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("framework:\n  version: 1.4.13\n", encoding="utf-8")

    migration = MigrationV1_4_13_to_V1_4_14()
    migration.migrate(config_file)

    assert "  version: 1.4.14\n" in config_file.read_text(encoding="utf-8")

    migration.downgrade(config_file)
    assert "  version: 1.4.13\n" in config_file.read_text(encoding="utf-8")


def test_migration_v1_4_13_to_v1_4_14_single_quoted_version(tmp_path: Path):
    """Single-quoted values are updated and keep their quoting style."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("framework:\n  version: '1.4.13'\n", encoding="utf-8")

    MigrationV1_4_13_to_V1_4_14().migrate(config_file)

    assert "  version: '1.4.14'\n" in config_file.read_text(encoding="utf-8")


def test_migration_v1_4_13_to_v1_4_14_missing_file(tmp_path: Path):
    missing_file = tmp_path / "nonexistent.yaml"
    migration = MigrationV1_4_13_to_V1_4_14()

    with pytest.raises(FileNotFoundError, match="Configuration file not found at"):
        migration.migrate(missing_file)

    with pytest.raises(FileNotFoundError, match="Configuration file not found at"):
        migration.downgrade(missing_file)


def test_migration_v1_4_13_to_v1_4_14_skips_commented_version_line(tmp_path: Path):
    """A commented-out version line is left untouched and does not count as a match."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "framework:\n"
        '  # version: "1.4.13"   <- previous pin, kept for reference\n'
        '  version: "1.4.13"\n',
        encoding="utf-8",
    )

    MigrationV1_4_13_to_V1_4_14().migrate(config_file)

    content = config_file.read_text(encoding="utf-8")
    assert '  # version: "1.4.13"   <- previous pin, kept for reference\n' in content
    assert '  version: "1.4.14"\n' in content


def test_migration_v1_4_13_to_v1_4_14_no_version_line_raises(tmp_path: Path):
    """Zero matching version lines must raise, not report silent success."""
    config_file = tmp_path / "config.yaml"
    original = "architecture:\n  layers:\n    domain: [\"src/domain\"]\n"
    config_file.write_text(original, encoding="utf-8")

    migration = MigrationV1_4_13_to_V1_4_14()

    with pytest.raises(RuntimeError, match="found 0"):
        migration.migrate(config_file)

    with pytest.raises(RuntimeError, match="found 0"):
        migration.downgrade(config_file)

    # The file must be left exactly as it was found.
    assert config_file.read_text(encoding="utf-8") == original


def test_migration_v1_4_13_to_v1_4_14_wrong_version_raises(tmp_path: Path):
    """Version-match guard: a config at another version is not silently rewritten."""
    config_file = tmp_path / "config.yaml"
    original = 'framework:\n  version: "1.3.0"\n'
    config_file.write_text(original, encoding="utf-8")

    migration = MigrationV1_4_13_to_V1_4_14()

    with pytest.raises(ValueError, match="expected version '1.4.13' but found '1.3.0'"):
        migration.migrate(config_file)

    assert config_file.read_text(encoding="utf-8") == original


def test_migration_v1_4_13_to_v1_4_14_leaves_project_version_untouched(tmp_path: Path):
    """Regression guard: project.version at its own value must survive the bump.

    Before the fix the substitution loop had no break, so this config came out with
    project.version rewritten from "0.1.0" to "1.4.14".
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'framework:\n  version: "1.4.13"\n\nproject:\n  name: "demo"\n  version: "0.1.0"\n',
        encoding="utf-8",
    )

    MigrationV1_4_13_to_V1_4_14().migrate(config_file)

    content = config_file.read_text(encoding="utf-8")
    assert 'framework:\n  version: "1.4.14"\n' in content
    assert '  version: "0.1.0"\n' in content


def test_migration_v1_4_13_to_v1_4_14_ambiguous_version_lines_raise(tmp_path: Path):
    """Regression guard: two lines at from_version are ambiguous and must not be rewritten.

    Before the fix this config had BOTH version lines rewritten to "1.4.14" and
    migrate() returned normally. The migration now refuses to guess and leaves the
    file byte-identical.
    """
    config_file = tmp_path / "config.yaml"
    original = (
        'framework:\n  version: "1.4.13"\n\nproject:\n  name: "demo"\n  version: "1.4.13"\n'
    )
    config_file.write_text(original, encoding="utf-8")

    with pytest.raises(RuntimeError, match="found 2"):
        MigrationV1_4_13_to_V1_4_14().migrate(config_file)

    assert config_file.read_text(encoding="utf-8") == original


def test_migration_v1_4_13_to_v1_4_14_preserves_trailing_comment(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        'framework:\n  version: "1.4.13"  # harness version of record\n', encoding="utf-8"
    )

    MigrationV1_4_13_to_V1_4_14().migrate(config_file)

    assert (
        '  version: "1.4.14"  # harness version of record\n'
        in config_file.read_text(encoding="utf-8")
    )
