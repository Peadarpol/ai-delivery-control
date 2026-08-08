"""Integration tests for migration v1.2.0.1 -> v1.3.0."""
from pathlib import Path
from bootstrap.migrations.v1_2_0_1_to_v1_3_0 import MigrationV1_2_0_1_to_V1_3_0
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_2_0_1_to_v1_3_0(tmp_path: Path):
    migration = MigrationV1_2_0_1_to_V1_3_0()
    run_standard_migration_suite(migration, "1.2.0.1", "1.3.0", tmp_path)
