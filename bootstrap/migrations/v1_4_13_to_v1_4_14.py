"""
AI Delivery Control — Configuration Migration (v1.4.13 ➔ v1.4.14)
Script and documentation-only release; no config.yaml schema changes.
Updates the framework version field in config.yaml only.
"""

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol


class MigrationV1_4_13_to_V1_4_14(MigrationProtocol):
    from_version = "1.4.13"
    to_version = "1.4.14"

    def _validate_config(self, content: str):
        from bootstrap.migration_base import validate_yaml_config
        validate_yaml_config(content)

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.4.13 to v1.4.14 in config.yaml."""
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
        """Revert framework version from v1.4.14 back to v1.4.13 in config.yaml."""
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
FROM_VERSION = "1.4.13"
TO_VERSION = "1.4.14"
MIGRATION_TYPE = "patch"

# Expose direct attributes for upgrade CLI scanning
v1_4_13_to_v1_4_14_migration = MigrationV1_4_13_to_V1_4_14()
from_version = MigrationV1_4_13_to_V1_4_14.from_version
to_version = MigrationV1_4_13_to_V1_4_14.to_version
migrate = v1_4_13_to_v1_4_14_migration.migrate
downgrade = v1_4_13_to_v1_4_14_migration.downgrade
