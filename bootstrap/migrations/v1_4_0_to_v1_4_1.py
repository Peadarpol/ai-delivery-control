"""
AI Delivery Control — Configuration Migration (v1.4.0 ➔ v1.4.1)
Patch release; no config.yaml schema changes.
Updates the framework version field in config.yaml only.
"""

from pathlib import Path

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


class MigrationV1_4_0_to_V1_4_1(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.4.0"
    to_version = "1.4.1"

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.4.0 to v1.4.1 in config.yaml."""
        self._rewrite_version(config_path, self.from_version, self.to_version, section="framework")

    def downgrade(self, config_path: Path) -> None:
        """Revert framework version from v1.4.1 back to v1.4.0 in config.yaml."""
        self._rewrite_version(config_path, self.to_version, self.from_version, section="framework")


FROM_VERSION = "1.4.0"
TO_VERSION = "1.4.1"
MIGRATION_TYPE = "patch"

v1_4_0_to_v1_4_1_migration = MigrationV1_4_0_to_V1_4_1()
from_version = MigrationV1_4_0_to_V1_4_1.from_version
to_version = MigrationV1_4_0_to_V1_4_1.to_version
migrate = v1_4_0_to_v1_4_1_migration.migrate
downgrade = v1_4_0_to_v1_4_1_migration.downgrade
