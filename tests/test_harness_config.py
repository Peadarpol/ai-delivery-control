"""
tests/test_harness_config.py — T1-B-10 verification

Pins the four harness architectural boundaries declared in .agent/config.yaml
against the _load_layer_paths_from_config() loader, and verifies the
startswith-prefix matching logic used by the co-change reconciler.

Acceptance criteria (SPEC §6):
  AC-1  Loader reads all four boundaries with correct names and paths.
  AC-2  A known cross-boundary file pair (review_engine vs governance_scripts)
        resolves to DIFFERENT boundaries — the canonical "interesting" co-change case.
  AC-3  A within-boundary pair both resolve to the SAME boundary — the reconciler
        should NOT flag this as a boundary crossing.
  AC-4  A file under no declared boundary resolves to None — unmatched files are
        not misattributed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest


# ---------------------------------------------------------------------------
# Helper: reproduce the same prefix-match logic the reconciler's consumers use
# (route_decision.py line 398: f.startswith(lp.rstrip("/") + "/"))
# ---------------------------------------------------------------------------

def _find_boundary(file_path: str, layers: dict) -> Optional[str]:
    """Return the layer name whose path-prefix matches *file_path*, or None."""
    for name, prefix in layers.items():
        if file_path.startswith(prefix.rstrip("/") + "/"):
            return name
    return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def harness_config_path() -> Path:
    """Absolute path to the harness .agent/config.yaml."""
    # Walk up from this test file to the repo root (the directory containing .git).
    candidate = Path(__file__).resolve().parent.parent
    for _ in range(5):
        if (candidate / ".git").exists():
            return candidate / ".agent" / "config.yaml"
        candidate = candidate.parent
    pytest.fail("Could not locate harness repo root from test file path.")


@pytest.fixture(scope="module")
def loaded_layers(harness_config_path: Path) -> dict:
    """
    Call _load_layer_paths_from_config() pointed at the harness repo root.

    Import route_decision directly and temporarily patch its PROJECT_ROOT so
    the loader reads the harness's own config.yaml rather than a consumer
    project's config.
    """
    import importlib
    import sys

    # Ensure route_decision is importable from the harness src/scripts directory.
    src_scripts = harness_config_path.parent.parent / "src" / "scripts"
    if str(src_scripts) not in sys.path:
        sys.path.insert(0, str(src_scripts))

    import route_decision  # noqa: PLC0415

    # Patch PROJECT_ROOT to the harness repo root so the loader finds the
    # config.yaml we just created.
    harness_root = harness_config_path.parent.parent
    original_root = route_decision.PROJECT_ROOT
    route_decision.PROJECT_ROOT = harness_root
    try:
        result = route_decision._load_layer_paths_from_config()
    finally:
        route_decision.PROJECT_ROOT = original_root

    return result


# ---------------------------------------------------------------------------
# AC-1: Loader reads all four boundaries
# ---------------------------------------------------------------------------

class TestLoaderReadsFourBoundaries:
    """AC-1: _load_layer_paths_from_config() returns exactly the four declared layers."""

    def test_returns_all_four_boundary_names(self, loaded_layers: dict):
        """All four boundary names are present as keys."""
        assert set(loaded_layers.keys()) == {
            "review_engine",
            "governance_scripts",
            "bootstrap",
            "skills",
        }, f"Unexpected layer keys: {set(loaded_layers.keys())}"

    def test_review_engine_path(self, loaded_layers: dict):
        assert loaded_layers["review_engine"] == "src/scripts"

    def test_governance_scripts_path(self, loaded_layers: dict):
        """Leading-dot path (.agent/scripts) must be parsed without stripping."""
        assert loaded_layers["governance_scripts"] == ".agent/scripts"

    def test_bootstrap_path(self, loaded_layers: dict):
        assert loaded_layers["bootstrap"] == "bootstrap"

    def test_skills_path(self, loaded_layers: dict):
        assert loaded_layers["skills"] == ".agent/skills"

    def test_exact_dict_equality(self, loaded_layers: dict):
        """Full dict match — no extra or missing entries."""
        expected = {
            "review_engine": "src/scripts",
            "governance_scripts": ".agent/scripts",
            "bootstrap": "bootstrap",
            "skills": ".agent/skills",
        }
        assert loaded_layers == expected, (
            f"Loader returned:\n  {loaded_layers}\nExpected:\n  {expected}"
        )


# ---------------------------------------------------------------------------
# AC-2: Known cross-boundary pair resolves to DIFFERENT boundaries
# ---------------------------------------------------------------------------

class TestCrossBoundaryResolution:
    """
    AC-2: The T1-G-17 canonical cross-tree pair — one file from review_engine,
    one from governance_scripts — must resolve to different boundary names.
    """

    def test_harness_utils_is_in_review_engine(self, loaded_layers: dict):
        boundary = _find_boundary("src/scripts/harness_utils.py", loaded_layers)
        assert boundary == "review_engine", (
            f"Expected 'review_engine', got {boundary!r}"
        )

    def test_co_change_check_is_in_governance_scripts(self, loaded_layers: dict):
        boundary = _find_boundary(".agent/scripts/co_change_check.py", loaded_layers)
        assert boundary == "governance_scripts", (
            f"Expected 'governance_scripts', got {boundary!r}"
        )

    def test_canonical_pair_is_cross_boundary(self, loaded_layers: dict):
        """
        src/scripts/harness_utils.py (review_engine) and
        .agent/scripts/co_change_check.py (governance_scripts)
        are the canonical cross-boundary case from T1-G-17.
        """
        b1 = _find_boundary("src/scripts/harness_utils.py", loaded_layers)
        b2 = _find_boundary(".agent/scripts/co_change_check.py", loaded_layers)
        assert b1 != b2, (
            f"Expected different boundaries; both resolved to {b1!r}"
        )

    def test_review_engine_vs_bootstrap_is_cross_boundary(self, loaded_layers: dict):
        """A review_engine file and a bootstrap file are also cross-boundary."""
        b1 = _find_boundary("src/scripts/ai_review.py", loaded_layers)
        b2 = _find_boundary("bootstrap/install.py", loaded_layers)
        assert b1 != b2, (
            f"Expected different boundaries; both resolved to {b1!r}"
        )


# ---------------------------------------------------------------------------
# AC-3: Within-boundary pairs resolve to the SAME boundary
# ---------------------------------------------------------------------------

class TestWithinBoundaryResolution:
    """
    AC-3: Two files under the same boundary prefix are within-boundary co-change.
    The reconciler must NOT flag these as boundary crossings.
    """

    def test_governance_scripts_within_boundary(self, loaded_layers: dict):
        """co_change_check.py and co_change_core.py are both in governance_scripts."""
        b1 = _find_boundary(".agent/scripts/co_change_check.py", loaded_layers)
        b2 = _find_boundary(".agent/scripts/co_change_core.py", loaded_layers)
        assert b1 == b2 == "governance_scripts"

    def test_review_engine_within_boundary(self, loaded_layers: dict):
        """Two src/scripts files are within the review_engine boundary."""
        b1 = _find_boundary("src/scripts/ai_review.py", loaded_layers)
        b2 = _find_boundary("src/scripts/route_decision.py", loaded_layers)
        assert b1 == b2 == "review_engine"

    def test_skills_within_boundary(self, loaded_layers: dict):
        """Two skills files are within the skills boundary."""
        b1 = _find_boundary(".agent/skills/meta/SKILL.md", loaded_layers)
        b2 = _find_boundary(".agent/skills/branch-isolation/SKILL.md", loaded_layers)
        assert b1 == b2 == "skills"


# ---------------------------------------------------------------------------
# AC-4: File under no declared boundary resolves to None
# ---------------------------------------------------------------------------

class TestUnmatchedFileResolution:
    """
    AC-4: Files outside all declared boundary prefixes must resolve to None,
    not be misattributed to any boundary.
    """

    def test_docs_file_is_unmatched(self, loaded_layers: dict):
        assert _find_boundary("docs/x.md", loaded_layers) is None

    def test_root_readme_is_unmatched(self, loaded_layers: dict):
        assert _find_boundary("README.md", loaded_layers) is None

    def test_tests_dir_is_unmatched(self, loaded_layers: dict):
        """
        tests/ is deliberately NOT a boundary (SPEC §2): tests co-change
        constantly with code; including them as a boundary would flood the
        reconciler with expected-noise crossings.
        """
        assert _find_boundary("tests/test_ai_review.py", loaded_layers) is None

    def test_agent_state_is_unmatched(self, loaded_layers: dict):
        """.agent/state/ is not a declared boundary."""
        assert _find_boundary(".agent/state/active_context.md", loaded_layers) is None

    def test_partial_prefix_does_not_match(self, loaded_layers: dict):
        """
        A path that starts with a boundary name but lacks the '/' separator
        must NOT match. e.g. 'bootstrapper.py' must not match 'bootstrap/'.
        """
        assert _find_boundary("bootstrapper.py", loaded_layers) is None

    def test_src_without_scripts_is_unmatched(self, loaded_layers: dict):
        """src/ alone (without /scripts/) does not match the review_engine boundary."""
        assert _find_boundary("src/conftest.py", loaded_layers) is None
