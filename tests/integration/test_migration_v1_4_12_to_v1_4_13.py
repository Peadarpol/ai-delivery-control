"""
Unit tests for migration v1.4.12 -> v1.4.13 (Phase 5 / Scenario 6 & 8).
Verifies literal extraction from target project files into .agent/config.yaml under schema_hardening.
"""

from pathlib import Path
import pytest
import sys
from bootstrap.migrations.v1_4_12_to_v1_4_13 import (
    MigrationV1_4_12_to_V1_4_13,
    extract_set_literal,
)


def test_extract_set_literal_ast_and_regex(tmp_path: Path):
    py_file = tmp_path / "sample.py"
    py_file.write_text(
        'WHITELIST = {\n    "src/schemas/a.py",\n    "src/schemas/b.py",\n}\n',
        encoding="utf-8",
    )

    extracted = extract_set_literal(py_file, "WHITELIST")
    assert extracted == {"src/schemas/a.py", "src/schemas/b.py"}


def test_migration_v1_4_12_to_v1_4_13_migrate_and_downgrade(tmp_path: Path, capsys):
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    config_file = agent_dir / "config.yaml"
    config_file.write_text('version: "1.4.12"\n', encoding="utf-8")

    scripts_dir = agent_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    enforce_file = scripts_dir / "enforce_hardened_schemas.py"
    enforce_file.write_text(
        'WHITELIST = {"src/schemas/legacy_schema.py"}\n', encoding="utf-8"
    )

    db_scripts = agent_dir / "skills" / "universal" / "database-design" / "scripts"
    db_scripts.mkdir(parents=True)
    analyze_file = db_scripts / "analyze_schema.py"
    analyze_file.write_text(
        'exempt_tables = {"gym_businesses", "custom_table"}\n', encoding="utf-8"
    )

    migration = MigrationV1_4_12_to_V1_4_13()
    migration.migrate(config_file)

    content = config_file.read_text(encoding="utf-8")
    assert 'version: "1.4.13"' in content
    assert "schema_hardening:" in content
    assert '"src/schemas/legacy_schema.py"' in content
    assert '"gym_businesses"' in content
    assert '"custom_table"' in content
    assert '"alembic_version"' in content

    captured = capsys.readouterr().out
    assert "SCHEMA HARDENING AUTO-MIGRATION" in captured
    assert "Extracted Whitelisted Schemas" in captured

    migration.downgrade(config_file)
    content_downgraded = config_file.read_text(encoding="utf-8")
    assert 'version: "1.4.12"' in content_downgraded


def test_schema_hardening_config_readers(tmp_path: Path):
    """Scenario 6: Verify enforce_hardened_schemas and analyze_schema read config-driven exemptions."""
    from unittest.mock import patch
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    config_file = agent_dir / "config.yaml"
    config_file.write_text(
        'version: "1.4.13"\n'
        'schema_hardening:\n'
        '  whitelist:\n'
        '    - "src/domain/schemas/custom.py"\n'
        '  exempt_tables:\n'
        '    - "my_custom_table"\n',
        encoding="utf-8",
    )

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "scripts"))
    from harness_utils import _reset_config_cache
    _reset_config_cache()

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".agent" / "scripts"))
    import enforce_hardened_schemas

    whitelist = enforce_hardened_schemas.load_whitelist(tmp_path)
    assert "src/domain/schemas/custom.py" in whitelist

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".agent" / "skills" / "universal" / "database-design" / "scripts"))
    import analyze_schema

    exempt = analyze_schema.load_exempt_tables(tmp_path)
    assert "my_custom_table" in exempt
    assert "alembic_version" in exempt

