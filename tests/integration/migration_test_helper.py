"""
Shared test helper for migration module unit/integration testing.
Runs standard test suite verifying version rewriting, quoting preservation,
wrong-version guards, missing-file handling, and project.version clobber prevention.
"""

from pathlib import Path
import pytest


def run_standard_migration_suite(migration_obj, from_version: str, to_version: str, tmp_path: Path):
    """Execute standard 10-test suite against migration_obj."""
    # 1. Quoted version migrate & downgrade
    config = tmp_path / "config_quoted.yaml"
    config.write_text(f'framework:\n  version: "{from_version}"\nproject:\n  version: "0.1.0"\n', encoding="utf-8")
    migration_obj.migrate(config)
    content = config.read_text(encoding="utf-8")
    assert f'version: "{to_version}"' in content
    assert 'version: "0.1.0"' in content

    migration_obj.downgrade(config)
    content = config.read_text(encoding="utf-8")
    assert f'version: "{from_version}"' in content

    # 2. Unquoted version migrate & downgrade
    config_unquoted = tmp_path / "config_unquoted.yaml"
    config_unquoted.write_text(f'framework:\n  version: {from_version}\nproject:\n  version: 0.1.0\n', encoding="utf-8")
    migration_obj.migrate(config_unquoted)
    content = config_unquoted.read_text(encoding="utf-8")
    assert f'version: {to_version}' in content
    assert 'version: 0.1.0' in content

    migration_obj.downgrade(config_unquoted)
    content = config_unquoted.read_text(encoding="utf-8")
    assert f'version: {from_version}' in content

    # 3. Single-quoted version migrate & downgrade
    config_squoted = tmp_path / "config_squoted.yaml"
    config_squoted.write_text(f"framework:\n  version: '{from_version}'\nproject:\n  version: '0.1.0'\n", encoding="utf-8")
    migration_obj.migrate(config_squoted)
    content = config_squoted.read_text(encoding="utf-8")
    assert f"version: '{to_version}'" in content
    assert "version: '0.1.0'" in content

    # 4. Missing file error
    with pytest.raises(FileNotFoundError):
        migration_obj.migrate(tmp_path / "nonexistent.yaml")

    # 5. Commented-out version line error
    config_comment = tmp_path / "config_comment.yaml"
    config_comment.write_text(f'# version: "{from_version}"\n', encoding="utf-8")
    with pytest.raises((ValueError, RuntimeError)):
        migration_obj.migrate(config_comment)

    # 6. Missing version key error
    config_no_version = tmp_path / "config_no_version.yaml"
    config_no_version.write_text('architecture:\n  layers: ["src/domain"]\n', encoding="utf-8")
    with pytest.raises((ValueError, RuntimeError)):
        migration_obj.migrate(config_no_version)

    # 7. Wrong version ValueError
    config_wrong = tmp_path / "config_wrong.yaml"
    config_wrong.write_text('framework:\n  version: "9.9.9"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="expected version"):
        migration_obj.migrate(config_wrong)

    # 8. Clobber prevention (confirm project.version at "0.1.0" is NOT rewritten)
    config_clobber = tmp_path / "config_clobber.yaml"
    config_clobber.write_text(
        f'framework:\n  version: "{from_version}"\n'
        'project:\n'
        '  version: "0.1.0"\n',
        encoding="utf-8"
    )
    migration_obj.migrate(config_clobber)
    content = config_clobber.read_text(encoding="utf-8")
    assert f'version: "{to_version}"' in content
    assert 'version: "0.1.0"' in content  # Must NOT be clobbered!

    # 9. Coincidental matching project.version (project.version == framework.version == from_version)
    config_ambiguous = tmp_path / "config_ambiguous.yaml"
    config_ambiguous.write_text(
        f'framework:\n  version: "{from_version}"\n'
        'project:\n'
        f'  version: "{from_version}"\n',
        encoding="utf-8"
    )
    migration_obj.migrate(config_ambiguous)
    content = config_ambiguous.read_text(encoding="utf-8")
    assert f'framework:\n  version: "{to_version}"' in content
    assert f'  version: "{from_version}"' in content  # project.version untouched

    # 10. Truly ambiguous version lines under framework: header
    config_true_ambiguous = tmp_path / "config_true_ambiguous.yaml"
    config_true_ambiguous.write_text(
        f'framework:\n  version: "{to_version}"\n  version: "{to_version}"\n',
        encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="found 2"):
        migration_obj.downgrade(config_true_ambiguous)

    # 10. Trailing comment preservation
    config_tc = tmp_path / "config_tc.yaml"
    config_tc.write_text(f'framework:\n  version: "{from_version}"  # framework version\n', encoding="utf-8")
    migration_obj.migrate(config_tc)
    content = config_tc.read_text(encoding="utf-8")
    assert f'version: "{to_version}"  # framework version' in content
