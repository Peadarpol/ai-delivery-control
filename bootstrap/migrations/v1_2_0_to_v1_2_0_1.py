"""
AI Delivery Control — Configuration Migration (v1.2.0 ➔ v1.2.0.1)
Implements MigrationProtocol for upgrading/downgrading config.yaml key schemas and target .gitignore block.
"""

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


class MigrationV1_2_0_to_V1_2_0_1(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.2.0"
    to_version = "1.2.0.1"

    def _validate_config(self, content: str):
        from bootstrap.migration_base import validate_yaml_config
        validate_yaml_config(content)

    def migrate(self, config_path: Path) -> None:
        """Upgrade configuration version from v1.2.0 to v1.2.0.1 and append gitignore exclusions."""
        self._rewrite_version(config_path, self.from_version, self.to_version, section="framework")

        # Update .gitignore in the target project
        project_root = config_path.parent.parent
        gitignore_path = project_root / ".gitignore"
        required_entries = [
            ".agent/state/session.json",
            ".agent/state/HALT",
            ".agent/state/*.lock",
            ".agent/config.yaml.migration_backup",
            ".agent/wiki/",
        ]
        
        if gitignore_path.exists():
            try:
                g_content = gitignore_path.read_text(encoding="utf-8")
                g_lines = g_content.splitlines()
            except Exception:
                g_lines = []
        else:
            g_lines = []
            
        # Idempotency check: check if `.agent/state/session.json` is already present
        is_already_present = any(".agent/state/session.json" == line.strip() for line in g_lines)
        if not is_already_present:
            header = "# AI Delivery Control — operational state (not project history)"
            if g_lines:
                g_lines.append("")
            g_lines.append(header)
            for entry in required_entries:
                g_lines.append(entry)
                
            try:
                gitignore_path.write_text("\n".join(g_lines) + "\n", encoding="utf-8")
            except Exception:
                pass

    def downgrade(self, config_path: Path) -> None:
        """Revert configuration version from v1.2.0.1 back to v1.2.0 and remove gitignore exclusions."""
        self._rewrite_version(config_path, self.to_version, self.from_version, section="framework")

        # Downgrade gitignore: scan for the exact header, remove from that line through the next blank line
        project_root = config_path.parent.parent
        gitignore_path = project_root / ".gitignore"
        
        if gitignore_path.exists():
            try:
                g_content = gitignore_path.read_text(encoding="utf-8")
                g_lines = g_content.splitlines()
            except Exception:
                return

            header = "# AI Delivery Control — operational state (not project history)"
            try:
                header_idx = -1
                for idx, line in enumerate(g_lines):
                    if line.strip() == header:
                        header_idx = idx
                        break
                
                if header_idx != -1:
                    # Find the next blank line or end of file
                    end_idx = len(g_lines)
                    for idx in range(header_idx + 1, len(g_lines)):
                        if g_lines[idx].strip() == "":
                            end_idx = idx + 1 # Include the trailing blank line
                            break
                    
                    # Remove the block
                    new_g_lines = g_lines[:header_idx] + g_lines[end_idx:]
                    # Also strip preceding blank line if left hanging at end of file
                    if new_g_lines and new_g_lines[-1].strip() == "":
                        new_g_lines.pop()
                        
                    gitignore_path.write_text("\n".join(new_g_lines) + "\n", encoding="utf-8")
            except Exception:
                pass


# Chain-discovery constants used by _assert_chain_contiguous().
FROM_VERSION = "1.2.0"
TO_VERSION = "1.2.0.1"
MIGRATION_TYPE = "patch"

# Expose direct attributes for upgrade CLI scanning
v1_2_0_to_v1_2_0_1_migration = MigrationV1_2_0_to_V1_2_0_1()
from_version = MigrationV1_2_0_to_V1_2_0_1.from_version
to_version = MigrationV1_2_0_to_V1_2_0_1.to_version
migrate = v1_2_0_to_v1_2_0_1_migration.migrate
downgrade = v1_2_0_to_v1_2_0_1_migration.downgrade
