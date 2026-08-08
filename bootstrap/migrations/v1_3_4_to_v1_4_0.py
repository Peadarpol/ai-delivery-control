"""
AI Delivery Control — Configuration Migration (v1.3.4 ➔ v1.4.0)

v1.4.0 — Intelligent Gate release. Changes to config.yaml:
  - Framework version string bumped to "1.4.0".

No new required keys are added to config.yaml in this release. The new
capabilities (GateContext, capability calibration, SQLite persistence,
acceptance hook) are all self-contained in src/scripts/ and operate without
additional config.yaml keys. Optional config keys for capability_calibration
and session_token_budget are backward-compatible with their defaults.

SQLite note for migration operators:
  The harness will lazily create ~/.aisdlc/harness.db on first use after
  upgrade. No manual DB setup is required. In CI/container environments
  without a persistent $HOME, it falls back to .agent/state/harness.db.
"""

from pathlib import Path

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


class MigrationV1_3_4_to_V1_4_0(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.3.4"
    to_version = "1.4.0"

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.3.4 to v1.4.0 in config.yaml."""
        self._rewrite_version(config_path, self.from_version, self.to_version)

    def downgrade(self, config_path: Path) -> None:
        """Revert framework version from v1.4.0 back to v1.3.4 in config.yaml."""
        self._rewrite_version(config_path, self.to_version, self.from_version)


# Chain-discovery constants used by _assert_chain_contiguous().
FROM_VERSION = "1.3.4"
TO_VERSION = "1.4.0"
MIGRATION_TYPE = "minor"

# Expose direct attributes for upgrade CLI scanning
v1_3_4_to_v1_4_0_migration = MigrationV1_3_4_to_V1_4_0()
from_version = MigrationV1_3_4_to_V1_4_0.from_version
to_version = MigrationV1_3_4_to_V1_4_0.to_version
migrate = v1_3_4_to_v1_4_0_migration.migrate
downgrade = v1_3_4_to_v1_4_0_migration.downgrade
