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
