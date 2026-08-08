"""
AI Delivery Control — Configuration Migration (v1.1.5.2 ➔ v1.2.0)
Implements MigrationProtocol for upgrading/downgrading config.yaml key schemas.
"""

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


class MigrationV1_1_5_to_V1_2_0(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.1.5.2"
    to_version = "1.2.0"

    def _validate_config(self, content: str):
        from bootstrap.migration_base import validate_yaml_config
        validate_yaml_config(content)

    def migrate(self, config_path: Path) -> None:
        """Upgrade configuration version from v1.1.5.2 to v1.2.0 with spec_gate block."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
            
        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        # Check if already present
        has_spec_gate = False
        for line in lines:
            if line.strip().startswith("spec_gate:"):
                has_spec_gate = True
                break

        if not has_spec_gate:
            # Inject spec_gate block structure cleanly before 'framework:' section if possible, else append
            inject_idx = len(lines)
            for idx, line in enumerate(lines):
                if line.strip().startswith("framework:"):
                    inject_idx = idx
                    break
                    
            spec_gate_block = [
                "",
                "# Spec Quality Gate Configuration (T1-L-01)",
                "spec_gate:",
                "  specs_path: docs/planning/specs/",
            ]
            
            lines = lines[:inject_idx] + spec_gate_block + lines[inject_idx:]

        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._rewrite_version(config_path, ("1.1.5", "1.1.5.1", "1.1.5.2"), self.to_version)

    def downgrade(self, config_path: Path) -> None:
        """Revert configuration version from v1.2.0 back to v1.1.5.2 removing spec_gate block."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
            
        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        # Remove spec_gate section block cleanly
        new_lines = []
        skip_mode = False
        for line in lines:
            stripped = line.strip()
            # Detect section start
            if stripped == "spec_gate:":
                skip_mode = True
                # Look back in new_lines to remove the preceding comment if present
                if new_lines and new_lines[-1].strip() == "# Spec Quality Gate Configuration (T1-L-01)":
                    new_lines.pop()
                if new_lines and new_lines[-1].strip() == "":
                    new_lines.pop()
                continue
            
            if skip_mode:
                # We skip lines starting with indentation (part of the spec_gate block)
                if line.startswith("  ") or not stripped:
                    continue
                else:
                    skip_mode = False
                    
            new_lines.append(line)

        config_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        self._rewrite_version(config_path, self.to_version, self.from_version)


# Chain-discovery constants used by _assert_chain_contiguous().
# FROM_VERSION = "1.1.5" matches the filename and is the graph-traversal start point.
# The migration class uses from_version = "1.1.5.2" for the actual config schema logic
# (the real prior install when upgrading via this module). These are different values
# serving different purposes: FROM_VERSION navigates the graph, from_version describes
# the actual previous install that the config migration was written for.
FROM_VERSION = "1.1.5"
TO_VERSION = "1.2.0"
MIGRATION_TYPE = "minor"

# Expose direct attributes for upgrade CLI scanning
v1_1_5_to_v1_2_0_migration = MigrationV1_1_5_to_V1_2_0()
from_version = MigrationV1_1_5_to_V1_2_0.from_version
to_version = MigrationV1_1_5_to_V1_2_0.to_version
migrate = v1_1_5_to_v1_2_0_migration.migrate
downgrade = v1_1_5_to_v1_2_0_migration.downgrade
