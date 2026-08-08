"""Integration tests for migration v1.4.8 -> v1.4.9."""
from pathlib import Path
from bootstrap.migrations.v1_4_8_to_v1_4_9 import MigrationV1_4_8_to_V1_4_9
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_4_8_to_v1_4_9(tmp_path: Path):
    migration = MigrationV1_4_8_to_V1_4_9()
    run_standard_migration_suite(migration, "1.4.8", "1.4.9", tmp_path)
