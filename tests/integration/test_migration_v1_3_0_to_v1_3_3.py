"""Integration tests for migration v1.3.0 -> v1.3.3."""
from pathlib import Path
from bootstrap.migrations.v1_3_0_to_v1_3_3 import MigrationV1_3_0_to_V1_3_3
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_3_0_to_v1_3_3(tmp_path: Path):
    migration = MigrationV1_3_0_to_V1_3_3()
    run_standard_migration_suite(migration, "1.3.0", "1.3.3", tmp_path)
