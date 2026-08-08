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


import re

# Matches a `version:` key whose value is double-quoted, single-quoted, or unquoted.
# The quoting style is captured so it can be preserved on rewrite. Keys such as
# `language_version:` do not match because only whitespace may precede `version`.
VERSION_LINE_RE = re.compile(
    r'^(?P<indent>\s*)version(?P<sep>\s*:\s*)'
    r'(?:"(?P<dquoted>[^"]*)"|\'(?P<squoted>[^\']*)\'|(?P<bare>[^\s#][^#]*?))'
    r'(?P<rest>\s*(?:#.*)?)$'
)


def _version_value(match: re.Match) -> str:
    """Return the version value from a VERSION_LINE_RE match, ignoring quoting style."""
    for group in ("dquoted", "squoted", "bare"):
        value = match.group(group)
        if value is not None:
            return value
    return ""


def _rewrite_line(match: re.Match, new_version: str) -> str:
    """Rebuild a `version:` line with new_version, preserving indent, spacing, quoting and comments."""
    if match.group("dquoted") is not None:
        value = f'"{new_version}"'
    elif match.group("squoted") is not None:
        value = f"'{new_version}'"
    else:
        value = new_version
    return f'{match.group("indent")}version{match.group("sep")}{value}{match.group("rest")}'


class VersionRewriteMixin:
    """Mixin or base providing hardened version rewriting for configuration migrations."""

    def _validate_config(self, content: str) -> None:
        validate_yaml_config(content)

    def _rewrite_version(
        self,
        config_path: Path,
        expected: str | tuple | list | set,
        new: str,
        section: str = "framework",
    ) -> None:
        r"""Rewrite the single `version:` line under `section:` currently holding expected, replacing it with new.

        Finds the named section header (`^{section}\s*:` at column 0) and only matches
        a `version:` line that is an indented child of that section.

        Raises instead of reporting silent success when the config is not in the
        expected state: ValueError when a version key exists but holds an unexpected
        value, RuntimeError when the number of lines to update is not exactly one.
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        section_pattern = re.compile(rf"^{re.escape(section)}\s*:")

        matches = []
        in_section = False
        section_indent = -1

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())

            if not in_section:
                if section_pattern.match(line):
                    in_section = True
                    section_indent = indent
            else:
                if indent <= section_indent:
                    in_section = False
                    if section_pattern.match(line):
                        in_section = True
                        section_indent = indent
                    continue

                match = VERSION_LINE_RE.match(line)
                if match:
                    matches.append((idx, match))

        expected_set = {expected} if isinstance(expected, str) else set(expected)

        # Version-match guard: never rewrite a config that is not at the expected version.
        targets = [(idx, match) for idx, match in matches if _version_value(match) in expected_set]
        if matches and not targets:
            found = ", ".join(sorted({_version_value(match) for _, match in matches}))
            exp_str = "', '".join(sorted(expected_set))
            raise ValueError(
                f"Cannot rewrite version in {config_path}: expected version "
                f"'{exp_str}' but found '{found}'"
            )

        # Write verification: a rewrite that changed nothing must not return normally.
        count = len(targets)
        if count != 1:
            raise RuntimeError(
                f"Expected to update exactly one 'version:' line in {config_path}, found {count}"
            )

        idx, match = targets[0]
        lines[idx] = _rewrite_line(match, new)

        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


