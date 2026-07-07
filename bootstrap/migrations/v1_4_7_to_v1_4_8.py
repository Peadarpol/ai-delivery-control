"""
AI Delivery Control — Configuration Migration (v1.4.7 ➔ v1.4.8)
Upgrade to v1.4.8 version-of-record.
Enables co-change reconciler and Coupling Decision Record (CDR) ledger integration.

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

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol


class MigrationV1_4_7_to_V1_4_8(MigrationProtocol):
    from_version = "1.4.7"
    to_version = "1.4.8"

    def _validate_config(self, content: str):
        from bootstrap.migration_base import validate_yaml_config
        validate_yaml_config(content)

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.4.7 to v1.4.8 in config.yaml."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = re.match(r'^(\s*)(version)(\s*:\s*)"([^"]+)"(.*)', line)
            if match:
                lines[idx] = f'{match.group(1)}{match.group(2)}{match.group(3)}"{self.to_version}"{match.group(5)}'

        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def downgrade(self, config_path: Path) -> None:
        """Revert framework version from v1.4.8 back to v1.4.7 in config.yaml."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = re.match(r'^(\s*)(version)(\s*:\s*)"([^"]+)"(.*)', line)
            if match:
                lines[idx] = f'{match.group(1)}{match.group(2)}{match.group(3)}"{self.from_version}"{match.group(5)}'

        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# Chain-discovery constants used by _assert_chain_contiguous().
FROM_VERSION = "1.4.7"
TO_VERSION = "1.4.8"
MIGRATION_TYPE = "patch"

# Expose direct attributes for upgrade CLI scanning
v1_4_7_to_v1_4_8_migration = MigrationV1_4_7_to_V1_4_8()
from_version = MigrationV1_4_7_to_V1_4_8.from_version
to_version = MigrationV1_4_7_to_V1_4_8.to_version
migrate = v1_4_7_to_v1_4_8_migration.migrate
downgrade = v1_4_7_to_v1_4_8_migration.downgrade
