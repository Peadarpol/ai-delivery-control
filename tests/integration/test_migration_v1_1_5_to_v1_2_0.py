"""Integration tests for migration v1.1.5.2 -> v1.2.0."""
from pathlib import Path
from bootstrap.migrations.v1_1_5_to_v1_2_0 import MigrationV1_1_5_to_V1_2_0
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_1_5_to_v1_2_0(tmp_path: Path):
    migration = MigrationV1_1_5_to_V1_2_0()
    run_standard_migration_suite(migration, "1.1.5.2", "1.2.0", tmp_path)
