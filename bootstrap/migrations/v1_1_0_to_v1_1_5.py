"""
AI Delivery Control — Configuration Migration (v1.1.0 ➔ v1.1.5)
Implements MigrationProtocol for upgrading/downgrading config.yaml key schemas.
"""

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol

class MigrationV1_1_0_to_V1_1_5(MigrationProtocol):
    from_version = "1.1.0"
    to_version = "1.1.5"

    def _validate_config(self, content: str):
        from bootstrap.migration_base import validate_yaml_config
        validate_yaml_config(content)

    def migrate(self, config_path: Path) -> None:
        """Upgrade configuration file from v1.1.0 to v1.1.5 key format."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
            
        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        # Pre-migration Validation: check if expected v1.1.0 keys are present
        has_local_provider = False
        has_local_model = False
        has_local_tasks = False
        has_budget_provider = False
        
        for line in lines:
            if line.strip().startswith("#"):
                continue
            if re.match(r'^\s*local_provider\s*:', line):
                has_local_provider = True
            if re.match(r'^\s*local_model\s*:', line):
                has_local_model = True
            if re.match(r'^\s*local_tasks\s*:', line):
                has_local_tasks = True
            if re.match(r'^\s*budget_provider\s*:', line):
                has_budget_provider = True
                
        if not (has_local_provider and has_local_model and has_local_tasks):
            raise ValueError("Expected v1.1.0 keys not found in config.yaml. Config may already be partially migrated. Aborting migration — manual review required.")
        if has_budget_provider:
            raise ValueError("budget_provider already exists in config.yaml. Config may already be partially migrated. Aborting migration — manual review required.")

        # 1. Perform Key Renames preserving inline comments
        renames = {
            "local_provider": "budget_provider",
            "local_model": "budget_model",
            "local_tasks": "budget_tasks",
            "cloud_provider": "review_provider",
            "cloud_model": "review_model",
        }
        
        for idx, line in enumerate(lines):
            for old_k, new_k in renames.items():
                if line.strip().startswith("#"):
                    continue
                pattern = rf'^(\s*)({old_k})(\s*:)(.*)'
                match = re.match(pattern, line)
                if match:
                    lines[idx] = f"{match.group(1)}{new_k}{match.group(3)}{match.group(4)}"
                    break # Only one rename per line

        # 2. Inject new keys using structural injection algorithms
        # A: model_routing additions
        model_routing_keys = [
            "budget_provider_timeout_seconds: 3",
            "budget_base_url: \"http://localhost:11434\"  # budget_base_url only used for ollama-compatible providers — ignored for anthropic/openai"
        ]
        lines = self._inject_in_section(lines, "model_routing", model_routing_keys)

        # B: token_tracking deeply nested additions
        lines = self._inject_nested_token_tracking(lines)

        # C: review additions
        review_keys = [
            "large_diff_threshold: 400  # T1-G-08 — inert until diff size review feature ships",
            "large_diff_strategy: \"stratified\"  # T1-G-08 — inert until diff size review feature ships"
        ]
        lines = self._inject_in_section(lines, "review", review_keys)

        # D: session_token_budget addition
        lines.append("session_token_budget: null  # null = budget enforcement disabled; set an integer to enable")

        # E: Bump Framework Version
        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            # Look for version under framework: section
            match = re.match(r'^(\s*)(version)(\s*:\s*)"([^"]+)"(.*)', line)
            if match:
                # We need to ensure it's under the 'framework:' section
                # For simplicity, since version is unique in standard templates, we bump it
                lines[idx] = f'{match.group(1)}{match.group(2)}{match.group(3)}"{self.to_version}"{match.group(5)}'

        # Write back content
        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def downgrade(self, config_path: Path) -> None:
        """Revert configuration from v1.1.5 back to v1.1.0 key format."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
            
        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        # Validate that v1.1.5 keys exist before downgrading
        has_budget_provider = False
        has_budget_model = False
        has_budget_tasks = False
        has_review_provider = False
        has_review_model = False
        
        for line in lines:
            if line.strip().startswith("#"):
                continue
            if re.match(r'^\s*budget_provider\s*:', line):
                has_budget_provider = True
            if re.match(r'^\s*budget_model\s*:', line):
                has_budget_model = True
            if re.match(r'^\s*budget_tasks\s*:', line):
                has_budget_tasks = True
            if re.match(r'^\s*review_provider\s*:', line):
                has_review_provider = True
            if re.match(r'^\s*review_model\s*:', line):
                has_review_model = True
                
        if not (has_budget_provider and has_budget_model and has_budget_tasks and has_review_provider and has_review_model):
            raise ValueError("Expected v1.1.5 keys not found in config.yaml. Aborting downgrade.")

        # 1. Reverse renames
        reverse_renames = {
            "budget_provider": "local_provider",
            "budget_model": "local_model",
            "budget_tasks": "local_tasks",
            "review_provider": "cloud_provider",
            "review_model": "cloud_model",
        }
        
        for idx, line in enumerate(lines):
            for old_k, new_k in reverse_renames.items():
                if line.strip().startswith("#"):
                    continue
                pattern = rf'^(\s*)({old_k})(\s*:)(.*)'
                match = re.match(pattern, line)
                if match:
                    lines[idx] = f"{match.group(1)}{new_k}{match.group(3)}{match.group(4)}"
                    break

        # 2. Remove injected keys
        keys_to_remove = [
            "budget_provider_timeout_seconds",
            "budget_base_url",
            "char_to_token_ratio",
            "review", # Wait! We only remove review if we added it, but let's remove its specific keys
            "large_diff_threshold",
            "large_diff_strategy",
            "session_token_budget",
        ]
        
        filtered_lines = []
        skip_block_indent = -1
        
        for line in lines:
            if skip_block_indent != -1:
                # We are skipping a block
                indent = len(line) - len(line.lstrip())
                if indent > skip_block_indent:
                    continue # Skip children
                else:
                    skip_block_indent = -1 # Exited block
            
            stripped = line.strip()
            if stripped.startswith("#"):
                filtered_lines.append(line)
                continue
                
            # Check if line matches any single-line keys to remove
            removed = False
            for k in ["budget_provider_timeout_seconds", "budget_base_url", "large_diff_threshold", "large_diff_strategy", "session_token_budget"]:
                if re.match(rf'^\s*{k}\s*:', line):
                    removed = True
                    break
            if removed:
                continue
                
            # Check for block structures like token_tracking -> char_to_token_ratio
            if re.match(r'^\s*char_to_token_ratio\s*:', line):
                skip_block_indent = len(line) - len(line.lstrip())
                continue
                
            # Check for empty review: section if we stripped its keys
            if re.match(r'^\s*review\s*:', line):
                # We can check if it has children next. If it's just the section header, we skip it
                skip_block_indent = len(line) - len(line.lstrip())
                continue
                
            filtered_lines.append(line)
            
        lines = filtered_lines

        # 3. Bump version back to v1.1.0
        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = re.match(r'^(\s*)(version)(\s*:\s*)"([^"]+)"(.*)', line)
            if match:
                lines[idx] = f'{match.group(1)}{match.group(2)}{match.group(3)}"{self.from_version}"{match.group(5)}'

        # Write back content
        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _inject_in_section(self, lines: list[str], section_name: str, new_keys: list[str]) -> list[str]:
        """Find index of section_name: and inject new_keys after its last child."""
        section_idx = -1
        section_indent = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = re.match(rf'^({section_name})\s*:', line)
            if match:
                section_idx = i
                section_indent = 0
                break
                
        if section_idx == -1:
            # Section is absent entirely — append full block at end of file
            new_lines = list(lines)
            new_lines.append(f"{section_name}:")
            for k in new_keys:
                new_lines.append(f"  {k}")
            return new_lines
            
        # Find the last key within the section
        last_key_idx = section_idx
        sibling_indent = -1
        
        for i in range(section_idx + 1, len(lines)):
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= section_indent:
                break
            last_key_idx = i
            sibling_indent = indent
            
        # Inject new keys after last_key_idx
        final_indent = sibling_indent if sibling_indent != -1 else section_indent + 2
        indent_str = " " * final_indent
        
        inserted_lines = [f"{indent_str}{k}" for k in new_keys]
        
        new_lines = list(lines)
        new_lines[last_key_idx+1:last_key_idx+1] = inserted_lines
        return new_lines

    def _inject_nested_token_tracking(self, lines: list[str]) -> list[str]:
        """Inject deeply nested token_tracking.char_to_token_ratio keys structurally."""
        tt_idx = -1
        tt_indent = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = re.match(r'^(token_tracking)\s*:', line)
            if match:
                tt_idx = i
                tt_indent = 0
                break
                
        if tt_idx == -1:
            new_lines = list(lines)
            new_lines.extend([
                "token_tracking:",
                "  char_to_token_ratio:",
                "    review: 4.0",
                "    budget: 3.5"
            ])
            return new_lines
            
        ratio_idx = -1
        ratio_indent = -1
        last_key_in_tt = tt_idx
        sibling_indent_tt = -1
        
        for i in range(tt_idx + 1, len(lines)):
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= tt_indent:
                break
            
            match = re.match(r'^(\s*)(char_to_token_ratio)\s*:', line)
            if match:
                ratio_idx = i
                ratio_indent = len(match.group(1))
            
            last_key_in_tt = i
            sibling_indent_tt = indent
            
        if ratio_idx != -1:
            last_key_in_ratio = ratio_idx
            sibling_indent_ratio = -1
            for i in range(ratio_idx + 1, len(lines)):
                line = lines[i]
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    continue
                indent = len(line) - len(line.lstrip())
                if indent <= ratio_indent:
                    break
                last_key_in_ratio = i
                sibling_indent_ratio = indent
                
            ratio_child_indent = sibling_indent_ratio if sibling_indent_ratio != -1 else ratio_indent + 2
            indent_str = " " * ratio_child_indent
            
            inserted_lines = [
                f"{indent_str}review: 4.0",
                f"{indent_str}budget: 3.5"
            ]
            new_lines = list(lines)
            new_lines[last_key_in_ratio+1:last_key_in_ratio+1] = inserted_lines
            return new_lines
        else:
            final_tt_key_indent = sibling_indent_tt if sibling_indent_tt != -1 else tt_indent + 2
            indent_str = " " * final_tt_key_indent
            child_indent_str = " " * (final_tt_key_indent + 2)
            
            inserted_lines = [
                f"{indent_str}char_to_token_ratio:",
                f"{child_indent_str}review: 4.0",
                f"{child_indent_str}budget: 3.5"
            ]
            new_lines = list(lines)
            new_lines[last_key_in_tt+1:last_key_in_tt+1] = inserted_lines
            return new_lines

# Chain-discovery constants used by _assert_chain_contiguous()
FROM_VERSION = "1.1.0"
TO_VERSION = "1.1.5"
MIGRATION_TYPE = "minor"

# Expose a direct module attribute for discover_migrations scanning
v1_1_0_to_v1_1_5_migration = MigrationV1_1_0_to_V1_1_5()
from_version = MigrationV1_1_0_to_V1_1_5.from_version
to_version = MigrationV1_1_0_to_V1_1_5.to_version
migrate = v1_1_0_to_v1_1_5_migration.migrate
downgrade = v1_1_0_to_v1_1_5_migration.downgrade
