"""Integration tests for migration v1.1.5 -> v1.1.5.1."""
from pathlib import Path
from bootstrap.migrations.v1_1_5_to_v1_1_5_1 import MigrationV1_1_5_to_V1_1_5_1
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_1_5_to_v1_1_5_1(tmp_path: Path):
    migration = MigrationV1_1_5_to_V1_1_5_1()
    run_standard_migration_suite(migration, "1.1.5", "1.1.5.1", tmp_path)
