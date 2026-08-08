"""
AI Delivery Control — Configuration Migration (v1.4.13 ➔ v1.4.14)
Script and documentation-only release; no config.yaml schema changes.
Updates the framework version field in config.yaml only.
"""

import re
from pathlib import Path

from bootstrap.migration_base import MigrationProtocol

# Matches a `version:` key whose value is double-quoted, single-quoted, or unquoted.
# The quoting style is captured so it can be preserved on rewrite. Keys such as
# `language_version:` do not match because only whitespace may precede `version`.
VERSION_LINE_RE = re.compile(
    r'^(?P<indent>\s*)version(?P<sep>\s*:\s*)'
    r'(?:"(?P<dquoted>[^"]*)"|\'(?P<squoted>[^\']*)\'|(?P<bare>[^\s#][^#]*?))'
    r'(?P<rest>\s*(?:#.*)?)$'
)


def _version_value(match: "re.Match") -> str:
    """Return the version value from a VERSION_LINE_RE match, ignoring quoting style."""
    for group in ("dquoted", "squoted", "bare"):
        value = match.group(group)
        if value is not None:
            return value
    return ""


def _rewrite_line(match: "re.Match", new_version: str) -> str:
    """Rebuild a `version:` line with new_version, preserving indent, spacing, quoting and comments."""
    if match.group("dquoted") is not None:
        value = f'"{new_version}"'
    elif match.group("squoted") is not None:
        value = f"'{new_version}'"
    else:
        value = new_version
    return f'{match.group("indent")}version{match.group("sep")}{value}{match.group("rest")}'


class MigrationV1_4_13_to_V1_4_14(MigrationProtocol):
    from_version = "1.4.13"
    to_version = "1.4.14"

    def _validate_config(self, content: str):
        from bootstrap.migration_base import validate_yaml_config
        validate_yaml_config(content)

    def _rewrite_version(self, config_path: Path, expected: str, new: str) -> None:
        """Rewrite the single `version:` line currently holding expected, replacing it with new.

        Raises instead of reporting silent success when the config is not in the
        expected state: ValueError when a version key exists but holds an unexpected
        value, RuntimeError when the number of lines to update is not exactly one.
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        content = config_path.read_text(encoding="utf-8")
        self._validate_config(content)
        lines = content.splitlines()

        matches = []
        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            match = VERSION_LINE_RE.match(line)
            if match:
                matches.append((idx, match))

        # Version-match guard: never rewrite a config that is not at the expected version.
        targets = [(idx, match) for idx, match in matches if _version_value(match) == expected]
        if matches and not targets:
            found = ", ".join(sorted({_version_value(match) for _, match in matches}))
            raise ValueError(
                f"Cannot rewrite version in {config_path}: expected version "
                f"'{expected}' but found '{found}'"
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

    def migrate(self, config_path: Path) -> None:
        """Bump framework version from v1.4.13 to v1.4.14 in config.yaml."""
        self._rewrite_version(config_path, self.from_version, self.to_version)

    def downgrade(self, config_path: Path) -> None:
        """Revert framework version from v1.4.14 back to v1.4.13 in config.yaml."""
        self._rewrite_version(config_path, self.to_version, self.from_version)


# Chain-discovery constants used by _assert_chain_contiguous().
FROM_VERSION = "1.4.13"
TO_VERSION = "1.4.14"
MIGRATION_TYPE = "patch"

# Expose direct attributes for upgrade CLI scanning
v1_4_13_to_v1_4_14_migration = MigrationV1_4_13_to_V1_4_14()
from_version = MigrationV1_4_13_to_V1_4_14.from_version
to_version = MigrationV1_4_13_to_V1_4_14.to_version
migrate = v1_4_13_to_v1_4_14_migration.migrate
downgrade = v1_4_13_to_v1_4_14_migration.downgrade
