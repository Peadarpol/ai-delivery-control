"""
AI Delivery Control — Configuration Migration (v1.4.2 ➔ v1.4.3)
Patch release; no config.yaml schema changes.
Updates the framework version field in config.yaml only.
"""

from pathlib import Path

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


class MigrationV1_4_2_to_V1_4_3(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.4.2"
    to_version = "1.4.3"

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.4.2 to v1.4.3 in config.yaml."""
        self._rewrite_version(config_path, self.from_version, self.to_version, section="framework")

    def downgrade(self, config_path: Path) -> None:
        """Revert framework version from v1.4.3 back to v1.4.2 in config.yaml."""
        self._rewrite_version(config_path, self.to_version, self.from_version, section="framework")


FROM_VERSION = "1.4.2"
TO_VERSION = "1.4.3"
MIGRATION_TYPE = "patch"

v1_4_2_to_v1_4_3_migration = MigrationV1_4_2_to_V1_4_3()
from_version = MigrationV1_4_2_to_V1_4_3.from_version
to_version = MigrationV1_4_2_to_V1_4_3.to_version
migrate = v1_4_2_to_v1_4_3_migration.migrate
downgrade = v1_4_2_to_v1_4_3_migration.downgrade
