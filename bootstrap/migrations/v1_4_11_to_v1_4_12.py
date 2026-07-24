"""
AI Delivery Control — Configuration Migration (v1.4.11 ➔ v1.4.12)
Upgrade to v1.4.12 version-of-record.
Adds enforcement posture configuration block (strict, ratchet, observe), human-only baseline CLI (.agent/scripts/baseline.py), AST region hashing grandfathering, invariant floor registry pinning, and GateContext v1.1 schema.
"""

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol


class MigrationV1_4_11_to_V1_4_12(MigrationProtocol):
    from_version = "1.4.11"
    to_version = "1.4.12"

    def _validate_config(self, content: str):
        from bootstrap.migration_base import validate_yaml_config
        validate_yaml_config(content)

    def migrate(self, config_path: Path) -> None:
        """Upgrade configuration version from v1.4.11 to v1.4.12 with enforcement block."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        # Check if enforcement block is already present
        has_enforcement = False
        for line in lines:
            if line.strip().startswith("enforcement:"):
                has_enforcement = True
                break

        if not has_enforcement:
            # Inject enforcement block structure cleanly before 'skip_paths:' or 'architecture:' section if possible, else append
            inject_idx = len(lines)
            for idx, line in enumerate(lines):
                if line.strip().startswith("skip_paths:") or line.strip().startswith("architecture:"):
                    inject_idx = idx
                    break

            enforcement_block = [
                "",
                "# Gate Enforcement Postures (T1-G-18)",
                "enforcement:",
                "  posture: strict",
                "  observe_expires: null        # ISO date, mandatory when posture: observe",
                "  rule_overrides: {}           # e.g. HIGH_COUPLING: warn   (pinned rules reject overrides)",
            ]

            lines = lines[:inject_idx] + enforcement_block + lines[inject_idx:]

        # Update Framework Version
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
        """Revert configuration version from v1.4.12 back to v1.4.11 removing enforcement block."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        # Remove enforcement section block cleanly
        new_lines = []
        skip_mode = False
        for line in lines:
            stripped = line.strip()
            if stripped == "enforcement:":
                skip_mode = True
                if new_lines and new_lines[-1].strip() == "# Gate Enforcement Postures (T1-G-18)":
                    new_lines.pop()
                if new_lines and new_lines[-1].strip() == "":
                    new_lines.pop()
                continue

            if skip_mode:
                if line.startswith("  ") or not stripped:
                    continue
                else:
                    skip_mode = False

            new_lines.append(line)

        # Revert Framework Version
        replaced = False
        for idx, line in enumerate(new_lines):
            if line.strip().startswith("#"):
                continue
            match = re.match(r'^(\s*)(version)(\s*:\s*)"([^"]+)"(.*)', line)
            if match:
                new_lines[idx] = f'{match.group(1)}{match.group(2)}{match.group(3)}"{self.from_version}"{match.group(5)}'
                replaced = True
                break

        if not replaced:
            raise ValueError(f"Version key not found in configuration file at {config_path}")

        config_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


# Chain-discovery constants used by _assert_chain_contiguous().
FROM_VERSION = "1.4.11"
TO_VERSION = "1.4.12"
MIGRATION_TYPE = "minor"

# Expose direct attributes for upgrade CLI scanning
v1_4_11_to_v1_4_12_migration = MigrationV1_4_11_to_V1_4_12()
from_version = MigrationV1_4_11_to_V1_4_12.from_version
to_version = MigrationV1_4_11_to_V1_4_12.to_version
migrate = v1_4_11_to_v1_4_12_migration.migrate
downgrade = v1_4_11_to_v1_4_12_migration.downgrade
