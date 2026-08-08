"""Integration tests for migration v1.3.3 -> v1.3.4."""
from pathlib import Path
from bootstrap.migrations.v1_3_3_to_v1_3_4 import MigrationV1_3_3_to_V1_3_4
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_3_3_to_v1_3_4(tmp_path: Path):
    migration = MigrationV1_3_3_to_V1_3_4()
    run_standard_migration_suite(migration, "1.3.3", "1.3.4", tmp_path)
