"""
AI Delivery Control — Migration Protocol Contract (Component 1)
Defines the interface contract that all configuration migrations must implement.
"""

from typing import Protocol, runtime_checkable
from pathlib import Path

@runtime_checkable
class MigrationProtocol(Protocol):
    from_version: str   # e.g. "1.1.0"
    to_version: str     # e.g. "1.1.5"

    def migrate(self, config_path: Path) -> None:
        """Apply migration steps to the config file at config_path."""
        ...

    def downgrade(self, config_path: Path) -> None:
        """Roll back migration steps from the config file at config_path."""
        ...


def validate_yaml_config(content: str) -> None:
    """Validate config.yaml structure is not empty and is basic YAML syntax, supporting multi-line block scalars."""
    if not content.strip():
        raise ValueError("config.yaml is empty")
    
    in_block_scalar = False
    block_indent = 0
    
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        
        if in_block_scalar:
            if stripped.startswith("#"):
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent > block_indent:
                continue
            else:
                in_block_scalar = False
        
        if stripped.startswith("#"):
            continue
        
        # Detect start of multi-line block scalar (| or >)
        clean_line = line.split("#")[0].rstrip()
        if ":" in clean_line or clean_line.strip().startswith("-"):
            indicator_line = clean_line
            if indicator_line.endswith(("+", "-")):
                indicator_line = indicator_line[:-1]
            if indicator_line.endswith(("|", ">")):
                in_block_scalar = True
                block_indent = len(line) - len(line.lstrip())
        
        if ":" not in line and not stripped.startswith("-"):
            raise ValueError(f"Malformed YAML at line {i}: {line}")

