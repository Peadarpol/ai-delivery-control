"""
AI Delivery Control — Configuration Migration (v1.1.5.1 ➔ v1.1.5.2)
Implements MigrationProtocol for upgrading/downgrading config.yaml key schemas.
No-op migration as there are no schema changes between v1.1.5.1 and v1.1.5.2,
only framework script bug fixes.
"""

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol

class MigrationV1_1_5_1_to_V1_1_5_2(MigrationProtocol):
    from_version = "1.1.5.1"
    to_version = "1.1.5.2"

    def _validate_config(self, content: str):
        """Validate config.yaml structure is not empty and is basic YAML syntax."""
        if not content.strip():
            raise ValueError("config.yaml is empty")
            
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" not in line and not stripped.startswith("-"):
                raise ValueError(f"Malformed YAML at line {i}: {line}")

    def migrate(self, config_path: Path) -> None:
        """Upgrade configuration version from v1.1.5.1 to v1.1.5.2."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
            
        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        # Update Framework Version
        modified = False
        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = re.match(r'^(\s*)(version)(\s*:\s*)"([^"]+)"(.*)', line)
            if match:
                lines[idx] = f'{match.group(1)}{match.group(2)}{match.group(3)}"{self.to_version}"{match.group(5)}'
                modified = True

        if modified:
            config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def downgrade(self, config_path: Path) -> None:
        """Revert configuration version from v1.1.5.2 back to v1.1.5.1."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
            
        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        # Revert Framework Version
        modified = False
        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = re.match(r'^(\s*)(version)(\s*:\s*)"([^"]+)"(.*)', line)
            if match:
                lines[idx] = f'{match.group(1)}{match.group(2)}{match.group(3)}"{self.from_version}"{match.group(5)}'
                modified = True

        if modified:
            config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

# Chain-discovery constants used by _assert_chain_contiguous()
FROM_VERSION = "1.1.5.1"
TO_VERSION = "1.1.5.2"
MIGRATION_TYPE = "patch"

# Expose direct attributes for upgrade CLI scanning
v1_1_5_1_to_v1_1_5_2_migration = MigrationV1_1_5_1_to_V1_1_5_2()
from_version = MigrationV1_1_5_1_to_V1_1_5_2.from_version
to_version = MigrationV1_1_5_1_to_V1_1_5_2.to_version
migrate = v1_1_5_1_to_v1_1_5_2_migration.migrate
downgrade = v1_1_5_1_to_v1_1_5_2_migration.downgrade
