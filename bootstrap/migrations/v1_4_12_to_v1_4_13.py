"""
AI Delivery Control — Configuration Migration (v1.4.12 ➔ v1.4.13)
Upgrade to v1.4.13 stabilization release.
Auto-extracts legacy WHITELIST and exempt_tables literals from target project files
before file overwrite, additively merging them into .agent/config.yaml under 'schema_hardening'.
"""

import ast
import re
from pathlib import Path
from typing import Set

from bootstrap.migration_base import MigrationProtocol, VersionRewriteMixin


def extract_set_literal(file_path: Path, variable_name: str) -> Set[str]:
    """Extract set or list literal assigned to variable_name using AST first, regex fallback."""
    if not file_path.exists():
        return set()
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return set()

    # Strategy 1: AST Parsing
    try:
        tree = ast.parse(content, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == variable_name:
                        val = node.value
                        if isinstance(val, (ast.Set, ast.List, ast.Tuple)):
                            extracted = set()
                            for el in val.elts:
                                if isinstance(el, ast.Constant) and isinstance(el.value, str):
                                    extracted.add(el.value)
                            if extracted:
                                return extracted
    except Exception:
        pass

    # Strategy 2: Regex Set/List Fallback
    try:
        pattern = re.compile(rf"{variable_name}\s*=\s*[\{{\[]([^}}\]]+)[\}}\]]", re.DOTALL)
        match = pattern.search(content)
        if match:
            items_raw = match.group(1)
            strings = re.findall(r"[\"']([^\"']+)[\"']", items_raw)
            return set(strings)
    except Exception:
        pass

    return set()


class MigrationV1_4_12_to_V1_4_13(VersionRewriteMixin, MigrationProtocol):
    from_version = "1.4.12"
    to_version = "1.4.13"

    def _validate_config(self, content: str):
        from bootstrap.migration_base import validate_yaml_config
        validate_yaml_config(content)

    def migrate(self, config_path: Path) -> None:
        """Upgrade configuration version from v1.4.12 to v1.4.13 with schema_hardening extraction."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        project_root = config_path.parent.parent

        # Target files for literal extraction
        enforce_path = project_root / ".agent" / "scripts" / "enforce_hardened_schemas.py"
        analyze_path = project_root / ".agent" / "skills" / "universal" / "database-design" / "scripts" / "analyze_schema.py"

        extracted_whitelist = extract_set_literal(enforce_path, "WHITELIST")
        extracted_exempt_tables = extract_set_literal(analyze_path, "exempt_tables")

        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)

        lines = content.splitlines()

        # Check existing schema_hardening block
        has_schema_hardening = any(line.strip() == "schema_hardening:" for line in lines)

        # Parse existing config if possible
        existing_whitelist: Set[str] = set()
        existing_exempt_tables: Set[str] = set()

        try:
            import yaml
            cfg = yaml.safe_load(content) or {}
            sh = cfg.get("schema_hardening", {})
            if isinstance(sh, dict):
                wl = sh.get("whitelist", [])
                if isinstance(wl, (list, tuple, set)):
                    existing_whitelist = {str(x).strip() for x in wl if x and isinstance(x, str)}
                et = sh.get("exempt_tables", [])
                if isinstance(et, (list, tuple, set)):
                    existing_exempt_tables = {str(x).strip() for x in et if x and isinstance(x, str)}
        except Exception:
            pass

        default_tables = {"alembic_version", "schema_migrations", "sqlite_sequence"}
        final_whitelist = sorted(list(existing_whitelist | extracted_whitelist))
        final_exempt_tables = sorted(list(existing_exempt_tables | extracted_exempt_tables | default_tables))

        # Build schema_hardening yaml block
        sh_block = ["", "schema_hardening:", "  whitelist:"]
        if final_whitelist:
            for item in final_whitelist:
                sh_block.append(f"    - \"{item}\"")
        else:
            sh_block[-1] = "  whitelist: []"

        sh_block.append("  exempt_tables:")
        for item in final_exempt_tables:
            sh_block.append(f"    - \"{item}\"")

        if not has_schema_hardening:
            inject_idx = len(lines)
            for idx, line in enumerate(lines):
                if line.strip().startswith("skip_paths:") or line.strip().startswith("architecture:"):
                    inject_idx = idx
                    break
            lines = lines[:inject_idx] + sh_block + lines[inject_idx:]

        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._rewrite_version(config_path, self.from_version, self.to_version, section="framework")

        # Confirmation Banner
        print("=" * 60)
        print("SCHEMA HARDENING AUTO-MIGRATION (v1.4.12 -> v1.4.13)")
        print("=" * 60)
        print(f"  Extracted Whitelisted Schemas : {len(extracted_whitelist)} item(s)")
        print(f"  Extracted Exempt Tables       : {len(extracted_exempt_tables)} item(s)")
        print("  Successfully merged forward into .agent/config.yaml under 'schema_hardening'.")
        print("=" * 60)

    def downgrade(self, config_path: Path) -> None:
        """Revert configuration version from v1.4.13 back to v1.4.12."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        self._rewrite_version(config_path, self.to_version, self.from_version, section="framework")


FROM_VERSION = "1.4.12"
TO_VERSION = "1.4.13"
MIGRATION_TYPE = "minor"

v1_4_12_to_v1_4_13_migration = MigrationV1_4_12_to_V1_4_13()
from_version = MigrationV1_4_12_to_V1_4_13.from_version
to_version = MigrationV1_4_12_to_V1_4_13.to_version
migrate = v1_4_12_to_v1_4_13_migration.migrate
downgrade = v1_4_12_to_v1_4_13_migration.downgrade
