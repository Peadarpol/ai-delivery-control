"""
AI Delivery Control — Configuration Migration (v1.2.0.1 ➔ v1.3.0)
Implements MigrationProtocol for upgrading/downgrading config.yaml key schemas for traceability and acceptance gates.
"""

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


class MigrationV1_2_0_1_to_V1_3_0(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.2.0.1"
    to_version = "1.3.0"

    def _validate_config(self, content: str):
        from bootstrap.migration_base import validate_yaml_config
        validate_yaml_config(content)

    def migrate(self, config_path: Path) -> None:
        """Upgrade configuration version from v1.2.0.1 to v1.3.0 and append traceability and acceptance gate blocks."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
            
        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)

        # Check if already has traceability and acceptance_gate blocks
        has_traceability = "traceability:" in content
        has_acceptance_gate = "acceptance_gate:" in content

        if not has_traceability or not has_acceptance_gate:
            # Resolve specs_path from spec_gate: specs_path if present
            specs_path = "docs/planning/specs/"
            spec_gate_match = re.search(r"^\s*spec_gate:\s*\n\s*specs_path:\s*([^\s\n]+)", content, re.MULTILINE)
            if spec_gate_match:
                specs_path = spec_gate_match.group(1).strip().strip('"').strip("'")

            # Construct new config blocks
            blocks_to_append = []
            if not has_traceability:
                blocks_to_append.append(f"""
# Requirement Traceability Gate (T1-L-04)
traceability:
  specs_path: {specs_path}""")
            if not has_acceptance_gate:
                blocks_to_append.append("""
# Acceptance Gate (T1-L-05)
acceptance_gate:
  base_branch: main
  migration_paths:
    - migrations/versions/
    - alembic/versions/
    - db/migration/
    - migrations/""")

            content = content.rstrip() + "\n" + "\n".join(blocks_to_append) + "\n"

        config_path.write_text(content, encoding="utf-8")
        self._rewrite_version(config_path, self.from_version, self.to_version, section="framework")

    def downgrade(self, config_path: Path) -> None:
        """Revert configuration version from v1.3.0 back to v1.2.0.1 and remove traceability/acceptance gate blocks."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
            
        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)

        # Remove traceability block
        content = re.sub(
            r"\n*# Requirement Traceability Gate \(T1-L-04\)\ntraceability:\n\s*specs_path:\s*[^\n]+",
            "",
            content
        )

        # Remove acceptance_gate block
        content = re.sub(
            r"\n*# Acceptance Gate \(T1-L-05\)\nacceptance_gate:\n\s*base_branch:\s*[^\n]+\n\s*migration_paths:\n(?:\s*-\s*[^\n]+\n?)+",
            "",
            content
        )

        # Let's clean up multiple newlines at end
        content = re.sub(r"\n\n\n+", "\n\n", content)
        config_path.write_text(content, encoding="utf-8")
        self._rewrite_version(config_path, self.to_version, self.from_version, section="framework")


# Chain-discovery constants used by _assert_chain_contiguous().
FROM_VERSION = "1.2.0.1"
TO_VERSION = "1.3.0"
MIGRATION_TYPE = "minor"

# Expose direct attributes for upgrade CLI scanning
v1_2_0_1_to_v1_3_0_migration = MigrationV1_2_0_1_to_V1_3_0()
from_version = MigrationV1_2_0_1_to_V1_3_0.from_version
to_version = MigrationV1_2_0_1_to_V1_3_0.to_version
migrate = v1_2_0_1_to_v1_3_0_migration.migrate
downgrade = v1_2_0_1_to_v1_3_0_migration.downgrade
