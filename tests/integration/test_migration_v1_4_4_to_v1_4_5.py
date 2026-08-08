"""Integration tests for migration v1.4.4 -> v1.4.5."""
from pathlib import Path
from bootstrap.migrations.v1_4_4_to_v1_4_5 import MigrationV1_4_4_to_V1_4_5
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_4_4_to_v1_4_5(tmp_path: Path):
    migration = MigrationV1_4_4_to_V1_4_5()
    run_standard_migration_suite(migration, "1.4.4", "1.4.5", tmp_path)
