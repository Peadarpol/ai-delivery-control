"""Integration tests for migration v1.3.4 -> v1.4.0."""
from pathlib import Path
from bootstrap.migrations.v1_3_4_to_v1_4_0 import MigrationV1_3_4_to_V1_4_0
from tests.integration.migration_test_helper import run_standard_migration_suite


def test_migration_v1_3_4_to_v1_4_0(tmp_path: Path):
    migration = MigrationV1_3_4_to_V1_4_0()
    run_standard_migration_suite(migration, "1.3.4", "1.4.0", tmp_path)
