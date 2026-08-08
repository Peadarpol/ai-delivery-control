"""Integration tests for migration v1.4.1 -> v1.4.2."""
from pathlib import Path
from bootstrap.migrations.v1_4_1_to_v1_4_2 import MigrationV1_4_1_to_V1_4_2
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_4_1_to_v1_4_2(tmp_path: Path):
    migration = MigrationV1_4_1_to_V1_4_2()
    run_standard_migration_suite(migration, "1.4.1", "1.4.2", tmp_path)
