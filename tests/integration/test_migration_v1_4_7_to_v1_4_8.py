"""Integration tests for migration v1.4.7 -> v1.4.8."""
from pathlib import Path
from bootstrap.migrations.v1_4_7_to_v1_4_8 import MigrationV1_4_7_to_V1_4_8
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_4_7_to_v1_4_8(tmp_path: Path):
    migration = MigrationV1_4_7_to_V1_4_8()
    run_standard_migration_suite(migration, "1.4.7", "1.4.8", tmp_path)
