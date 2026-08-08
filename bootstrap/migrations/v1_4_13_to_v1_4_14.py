"""
AI Delivery Control — Configuration Migration (v1.4.13 ➔ v1.4.14)
Script and documentation-only release; no config.yaml schema changes.
Updates the framework version field in config.yaml only.
"""

from pathlib import Path

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


class MigrationV1_4_13_to_V1_4_14(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.4.13"
    to_version = "1.4.14"

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.4.13 to v1.4.14 in config.yaml."""
        self._rewrite_version(config_path, self.from_version, self.to_version)

    def downgrade(self, config_path: Path) -> None:
        """Revert framework version from v1.4.14 back to v1.4.13 in config.yaml."""
        self._rewrite_version(config_path, self.to_version, self.from_version)


# Chain-discovery constants used by _assert_chain_contiguous().
FROM_VERSION = "1.4.13"
TO_VERSION = "1.4.14"
MIGRATION_TYPE = "patch"

# Expose direct attributes for upgrade CLI scanning
v1_4_13_to_v1_4_14_migration = MigrationV1_4_13_to_V1_4_14()
from_version = MigrationV1_4_13_to_V1_4_14.from_version
to_version = MigrationV1_4_13_to_V1_4_14.to_version
migrate = v1_4_13_to_v1_4_14_migration.migrate
downgrade = v1_4_13_to_v1_4_14_migration.downgrade
