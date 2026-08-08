"""
AI Delivery Control — Configuration Migration (v1.1.5 ➔ v1.1.5.1)
Patch release; no config.yaml schema changes.
Updates the framework version field in config.yaml only.
"""

from pathlib import Path

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


class MigrationV1_1_5_to_V1_1_5_1(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.1.5"
    to_version = "1.1.5.1"

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.1.5 to v1.1.5.1 in config.yaml."""
        self._rewrite_version(config_path, self.from_version, self.to_version)

    def downgrade(self, config_path: Path) -> None:
        """Revert framework version from v1.1.5.1 back to v1.1.5 in config.yaml."""
        self._rewrite_version(config_path, self.to_version, self.from_version)


FROM_VERSION = "1.1.5"
TO_VERSION = "1.1.5.1"
MIGRATION_TYPE = "patch"

v1_1_5_to_v1_1_5_1_migration = MigrationV1_1_5_to_V1_1_5_1()
from_version = MigrationV1_1_5_to_V1_1_5_1.from_version
to_version = MigrationV1_1_5_to_V1_1_5_1.to_version
migrate = v1_1_5_to_v1_1_5_1_migration.migrate
downgrade = v1_1_5_to_v1_1_5_1_migration.downgrade
