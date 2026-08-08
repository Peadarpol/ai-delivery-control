"""Scenario 6 (SPEC-loop-closure-verification, Phase C): outcome-equivalence regression detection.

Retroactive-plus-forward, the same discipline every other scenario in this spec uses
(Tier 1's diagnosed fixes, D1's contract tests):

  * retroactive — a *buggy* refactor reproducing the founding incident's shape (claims to
    relocate the fixture's schema-hardening exemption values, silently empties them instead)
    must make the outcome-equivalence assertion FAIL, naming the specific dropped values.
  * forward — a *correct* refactor relocating the same values intact must make the identical
    assertion PASS, proving the mechanism discriminates rather than merely failing loudly.

Both run against the hermetic fixture at tests/data/schema_hardening_fixture/, copied into
tmp_path first — the checked-in fixture is never mutated.
"""

from pathlib import Path

import pytest
import yaml

from tests.helpers.outcome_equivalence import (
    OutcomeEquivalenceError,
    ValueLocator,
    assert_refactor_preserves_values,
    load_operational_values,
    materialize_fixture_project,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = PROJECT_ROOT / "tests" / "data" / "schema_hardening_fixture"

# Where the tracked values live before any refactor.
BEFORE_LOCATORS = (
    ValueLocator("schema_whitelist", ".agent/config.yaml", "schema_hardening.whitelist"),
    ValueLocator("exempt_tables", ".agent/config.yaml", "schema_hardening.exempt_tables"),
)

# Where both refactors below *claim* to have moved them.
RELOCATED_ARTIFACT = ".agent/config/schema_hardening.yaml"
AFTER_LOCATORS = tuple(loc.relocated(artifact=RELOCATED_ARTIFACT) for loc in BEFORE_LOCATORS)


@pytest.fixture
def fixture_project(tmp_path: Path) -> Path:
    """A scratch copy of the hermetic fixture project."""
    return materialize_fixture_project(FIXTURE_DIR, tmp_path / "schema_hardening_fixture")


def _strip_inline_section(project_root: Path) -> dict:
    """Remove the schema_hardening section from .agent/config.yaml, returning what it held."""
    config_path = project_root / ".agent" / "config.yaml"
    document = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    removed = document.pop("schema_hardening", {})
    config_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return removed


def _write_relocated_section(project_root: Path, payload: dict) -> None:
    """Write the new config-driven storage location."""
    target = project_root / Path(RELOCATED_ARTIFACT)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump({"schema_hardening": payload}, sort_keys=False), encoding="utf-8")


def buggy_refactor(project_root: Path) -> None:
    """Claims to move the exemption values to config-driven storage. Silently loses them.

    Reproduces the exact shape of the second incident in the spec's §0 Motivation Gate: the
    new storage location is created and the code still runs end to end, but the operational
    values are replaced with empty/generic defaults instead of being carried over.
    """
    _strip_inline_section(project_root)
    _write_relocated_section(
        project_root,
        {
            "whitelist": [],  # emptied
            "exempt_tables": ["alembic_version"],  # replaced with a generic default
        },
    )


def correct_refactor(project_root: Path) -> None:
    """Moves the same values to the same new location, intact."""
    removed = _strip_inline_section(project_root)
    _write_relocated_section(
        project_root,
        {
            "whitelist": list(removed.get("whitelist", [])),
            "exempt_tables": list(removed.get("exempt_tables", [])),
        },
    )


class TestOutcomeEquivalence:
    def test_fixture_carries_the_expected_operational_values(self, fixture_project: Path):
        """Guard: the assertions below are only meaningful if the fixture holds real values."""
        values = load_operational_values(fixture_project, BEFORE_LOCATORS)

        assert values["schema_whitelist"] == [
            "src/domain/schemas/fixture_alpha.py",
            "src/domain/schemas/fixture_beta.py",
        ]
        assert values["exempt_tables"] == [
            "fixture_table_alpha",
            "fixture_table_beta",
            "fixture_table_gamma",
        ]

    def test_buggy_refactor_is_caught(self, fixture_project: Path):
        """Retroactive: a silent data-deletion refactor fails the outcome-equivalence check."""
        with pytest.raises(OutcomeEquivalenceError) as excinfo:
            assert_refactor_preserves_values(
                fixture_project,
                BEFORE_LOCATORS,
                buggy_refactor,
                after_locators=AFTER_LOCATORS,
                context="buggy relocation of schema-hardening exemptions",
            )

        message = str(excinfo.value)

        # Both tracked values are reported, each classified by how it was lost.
        assert set(excinfo.value.failed_names) == {"schema_whitelist", "exempt_tables"}
        assert "schema_whitelist [EMPTIED]" in message
        assert "exempt_tables [CHANGED]" in message

        # The specific dropped members are named — not just "state differs".
        assert "src/domain/schemas/fixture_alpha.py" in message
        assert "src/domain/schemas/fixture_beta.py" in message
        assert "fixture_table_alpha" in message
        assert "fixture_table_beta" in message
        assert "fixture_table_gamma" in message

        # Both storage locations are named, so the failure is actionable without a debugger.
        assert ".agent/config.yaml::schema_hardening.whitelist" in message
        assert f"{RELOCATED_ARTIFACT}::schema_hardening.exempt_tables" in message

    def test_correct_refactor_passes(self, fixture_project: Path):
        """Forward: a genuine relocation of the same values passes the identical check."""
        after = assert_refactor_preserves_values(
            fixture_project,
            BEFORE_LOCATORS,
            correct_refactor,
            after_locators=AFTER_LOCATORS,
            context="correct relocation of schema-hardening exemptions",
        )

        # The values really did move — this is not passing because nothing changed.
        assert not (fixture_project / ".agent" / "config.yaml").read_text(
            encoding="utf-8"
        ).count("schema_hardening")
        assert (fixture_project / Path(RELOCATED_ARTIFACT)).is_file()
        assert after["schema_whitelist"] == [
            "src/domain/schemas/fixture_alpha.py",
            "src/domain/schemas/fixture_beta.py",
        ]
        assert after["exempt_tables"] == [
            "fixture_table_alpha",
            "fixture_table_beta",
            "fixture_table_gamma",
        ]
