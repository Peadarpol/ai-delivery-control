"""Integration tests for migration v1.4.3 -> v1.4.4."""
from pathlib import Path
from bootstrap.migrations.v1_4_3_to_v1_4_4 import MigrationV1_4_3_to_V1_4_4
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_4_3_to_v1_4_4(tmp_path: Path):
    migration = MigrationV1_4_3_to_V1_4_4()
    run_standard_migration_suite(migration, "1.4.3", "1.4.4", tmp_path)
