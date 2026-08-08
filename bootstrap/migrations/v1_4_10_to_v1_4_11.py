"""
AI Delivery Control — Configuration Migration (v1.4.10 ➔ v1.4.11)
Script and documentation-only release; no config.yaml schema changes.
Updates the framework version field in config.yaml only.

Framework-owned file copy list:
  - src/scripts/ai_review.py
  - src/scripts/providers.py
  - src/scripts/roster_builder.py
  - src/scripts/review_context_universal.md
  - src/scripts/harness_utils.py
  - src/scripts/gate_context.py
  - src/scripts/capability_calibration.py
  - src/scripts/state_persistence.py
  - src/scripts/acceptance_hook.py
  - src/scripts/context_loader.py
  - src/scripts/route_decision.py
  - src/scripts/rebuttal.py
"""

from pathlib import Path

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


class MigrationV1_4_10_to_V1_4_11(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.4.10"
    to_version = "1.4.11"

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.4.10 to v1.4.11 in config.yaml."""
        self._rewrite_version(config_path, self.from_version, self.to_version, section="framework")

    def downgrade(self, config_path: Path) -> None:
        """Revert framework version from v1.4.11 back to v1.4.10 in config.yaml."""
        self._rewrite_version(config_path, self.to_version, self.from_version, section="framework")


# Chain-discovery constants used by _assert_chain_contiguous().
FROM_VERSION = "1.4.10"
TO_VERSION = "1.4.11"
MIGRATION_TYPE = "patch"

# Expose direct attributes for upgrade CLI scanning
v1_4_10_to_v1_4_11_migration = MigrationV1_4_10_to_V1_4_11()
from_version = MigrationV1_4_10_to_V1_4_11.from_version
to_version = MigrationV1_4_10_to_V1_4_11.to_version
migrate = v1_4_10_to_v1_4_11_migration.migrate
downgrade = v1_4_10_to_v1_4_11_migration.downgrade
