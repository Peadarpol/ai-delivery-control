"""Integration tests for migration v1.4.6 -> v1.4.7."""
from pathlib import Path
from bootstrap.migrations.v1_4_6_to_v1_4_7 import MigrationV1_4_6_to_V1_4_7
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_4_6_to_v1_4_7(tmp_path: Path):
    migration = MigrationV1_4_6_to_V1_4_7()
    run_standard_migration_suite(migration, "1.4.6", "1.4.7", tmp_path)
