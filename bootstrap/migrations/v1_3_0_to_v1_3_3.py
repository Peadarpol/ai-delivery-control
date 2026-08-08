"""
AI Delivery Control — Configuration Migration (v1.3.0 ➔ v1.3.3)
Patch release; no config.yaml schema changes.
Updates the framework version field in config.yaml only.
"""

from pathlib import Path

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


class MigrationV1_3_0_to_V1_3_3(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.3.0"
    to_version = "1.3.3"

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.3.0 to v1.3.3 in config.yaml."""
        self._rewrite_version(config_path, self.from_version, self.to_version)

    def downgrade(self, config_path: Path) -> None:
        """Revert framework version from v1.3.3 back to v1.3.0 in config.yaml."""
        self._rewrite_version(config_path, self.to_version, self.from_version)


FROM_VERSION = "1.3.0"
TO_VERSION = "1.3.3"
MIGRATION_TYPE = "patch"

v1_3_0_to_v1_3_3_migration = MigrationV1_3_0_to_V1_3_3()
from_version = MigrationV1_3_0_to_V1_3_3.from_version
to_version = MigrationV1_3_0_to_V1_3_3.to_version
migrate = v1_3_0_to_v1_3_3_migration.migrate
downgrade = v1_3_0_to_v1_3_3_migration.downgrade
