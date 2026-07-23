"""
AI Delivery Control — Configuration Migration (v1.4.10 ➔ v1.4.11)
Upgrade to v1.4.11 version-of-record.
Enables installer & validator hardening: target repository guard (F-COLD-1), --skip-validation CLI flag, pre-commit template exclude regex-escaping (F7), ephemeral git-sandbox dry-run validator with read-only teardown and interrupt safety, Python currency/tooling checks with bounded timeouts, and live API credential preflight with Anthropic/OpenAI probe endpoints.
"""

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol


class MigrationV1_4_10_to_V1_4_11(MigrationProtocol):
    from_version = "1.4.10"
    to_version = "1.4.11"

    def _validate_config(self, content: str):
        from bootstrap.migration_base import validate_yaml_config
        validate_yaml_config(content)

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.4.10 to v1.4.11 in config.yaml."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        replaced = False
        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = re.match(r'^(\s*)(version)(\s*:\s*)"([^"]+)"(.*)', line)
            if match:
                lines[idx] = f'{match.group(1)}{match.group(2)}{match.group(3)}"{self.to_version}"{match.group(5)}'
                replaced = True
                break

        if not replaced:
            raise ValueError(f"Version key not found in configuration file at {config_path}")

        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def downgrade(self, config_path: Path) -> None:
        """Revert framework version from v1.4.11 back to v1.4.10 in config.yaml."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        replaced = False
        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = re.match(r'^(\s*)(version)(\s*:\s*)"([^"]+)"(.*)', line)
            if match:
                lines[idx] = f'{match.group(1)}{match.group(2)}{match.group(3)}"{self.from_version}"{match.group(5)}'
                replaced = True
                break

        if not replaced:
            raise ValueError(f"Version key not found in configuration file at {config_path}")

        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
