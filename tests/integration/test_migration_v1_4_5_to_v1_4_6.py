"""Integration tests for migration v1.4.5 -> v1.4.6."""
from pathlib import Path
from bootstrap.migrations.v1_4_5_to_v1_4_6 import MigrationV1_4_5_to_V1_4_6
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_4_5_to_v1_4_6(tmp_path: Path):
    migration = MigrationV1_4_5_to_V1_4_6()
    run_standard_migration_suite(migration, "1.4.5", "1.4.6", tmp_path)
