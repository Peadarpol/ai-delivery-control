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

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol


class MigrationV1_3_4_to_V1_4_0(MigrationProtocol):
    from_version = "1.3.4"
    to_version = "1.4.0"

    def _validate_config(self, content: str):
        if not content.strip():
            raise ValueError("config.yaml is empty")
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" not in line and not stripped.startswith("-"):
                raise ValueError(f"Malformed YAML at line {i}: {line}")

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.3.4 to v1.4.0 in config.yaml."""
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
        """Revert framework version from v1.4.0 back to v1.3.4 in config.yaml."""
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
FROM_VERSION = "1.3.4"
TO_VERSION = "1.4.0"
MIGRATION_TYPE = "minor"

# Expose direct attributes for upgrade CLI scanning
v1_3_4_to_v1_4_0_migration = MigrationV1_3_4_to_V1_4_0()
from_version = MigrationV1_3_4_to_V1_4_0.from_version
to_version = MigrationV1_3_4_to_V1_4_0.to_version
migrate = v1_3_4_to_v1_4_0_migration.migrate
downgrade = v1_3_4_to_v1_4_0_migration.downgrade
