"""Integration tests for migration v1.4.2 -> v1.4.3."""
from pathlib import Path
from bootstrap.migrations.v1_4_2_to_v1_4_3 import MigrationV1_4_2_to_V1_4_3
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_4_2_to_v1_4_3(tmp_path: Path):
    migration = MigrationV1_4_2_to_V1_4_3()
    run_standard_migration_suite(migration, "1.4.2", "1.4.3", tmp_path)
