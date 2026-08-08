"""Integration tests for migration v1.2.0 -> v1.2.0.1."""
from pathlib import Path
from bootstrap.migrations.v1_2_0_to_v1_2_0_1 import MigrationV1_2_0_to_V1_2_0_1
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_2_0_to_v1_2_0_1(tmp_path: Path):
    migration = MigrationV1_2_0_to_V1_2_0_1()
    run_standard_migration_suite(migration, "1.2.0", "1.2.0.1", tmp_path)
