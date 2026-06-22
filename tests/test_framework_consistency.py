"""
tests/test_framework_consistency.py — T1-K-09
Consistency gate: assert that cross-references between governance surfaces are valid
and that workflow slugs in AGENTS.md §2 resolve to real files in .agent/workflows/.

These tests are intentionally simple and stdlib-only so they run without any
heavyweight fixtures.  The goal is to catch the class of drift that was found during
the 2026-06-22 prohibition restructure audit (dead /perf and /qa references, stale
blocked_commands.md header) in CI rather than in a human review.

Add a new test whenever you add a new governance cross-reference that could drift
independently (new workflow slug in a table, new §-reference in a companion document,
new "see also" pointer in a skill file).
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = REPO_ROOT / ".agent" / "AGENTS.md"
BLOCKED_COMMANDS_MD = REPO_ROOT / ".agent" / "blocked_commands.md"
GOVERNANCE_MD = REPO_ROOT / ".agent" / "governance.md"
WORKFLOWS_DIR = REPO_ROOT / ".agent" / "workflows"


# ---------------------------------------------------------------------------
# Helper: extract workflow slugs from AGENTS.md §2 table
# ---------------------------------------------------------------------------

def _extract_workflow_slugs_from_agents_md() -> list[str]:
    """
    Parse the workflow routing table in §2 of AGENTS.md.
    Returns a list of slug strings like 'feature-implementation', 'bug-fix', etc.
    The table rows look like:
        | New feature or requirement | `/feature-implementation` |
    """
    text = AGENTS_MD.read_text(encoding="utf-8")
    # Match backtick-quoted slash-command slugs in Markdown table rows
    pattern = re.compile(r"`/([a-z][a-z0-9\-]*)`")
    # Scope to the §2 section only: between "## 2." and the next "## "
    section_match = re.search(
        r"## 2\. Workflow-First.*?(?=\n## \d+\.|\Z)",
        text,
        re.DOTALL,
    )
    if not section_match:
        return []
    section_text = section_match.group(0)
    return pattern.findall(section_text)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_workflows_dir_exists():
    """Sanity check: .agent/workflows/ must exist before any slug tests run."""
    assert WORKFLOWS_DIR.is_dir(), (
        f".agent/workflows/ directory not found at {WORKFLOWS_DIR}. "
        "Cannot validate workflow slug references."
    )


def test_agents_md_workflow_table_slugs_resolve_to_real_files():
    """
    T1-K-09: every `/slug` in the AGENTS.md §2 workflow routing table must
    correspond to a real file at .agent/workflows/<slug>.md.

    Adding a new workflow to AGENTS.md without creating the file, or removing
    the file without updating the table, will cause this test to fail.
    """
    slugs = _extract_workflow_slugs_from_agents_md()
    assert slugs, (
        "No workflow slugs found in AGENTS.md §2 table — "
        "either the section heading changed or the table format drifted."
    )

    missing = []
    for slug in slugs:
        workflow_file = WORKFLOWS_DIR / f"{slug}.md"
        if not workflow_file.exists():
            missing.append(f"  /{ slug } → {workflow_file} (NOT FOUND)")

    assert not missing, (
        "AGENTS.md §2 workflow table references slugs with no matching file in "
        f".agent/workflows/:\n" + "\n".join(missing)
    )


def test_blocked_commands_header_references_current_section_label():
    """
    T1-K-09: blocked_commands.md must reference the current §4 section label
    (H/S/C/G series) rather than the old P-series label.

    The header line is:  Reference: AGENTS.md §4 Absolute Prohibitions (H/S/C/G series).
    If someone updates AGENTS.md §4 and forgets to update blocked_commands.md, this test fails.
    """
    assert BLOCKED_COMMANDS_MD.exists(), (
        f"blocked_commands.md not found at {BLOCKED_COMMANDS_MD}"
    )
    text = BLOCKED_COMMANDS_MD.read_text(encoding="utf-8")

    # Must NOT contain stale P-series reference in the header
    stale_pattern = re.compile(r"P-\d+.*?P-\d+", re.IGNORECASE)  # e.g. P-01–P-17
    stale_match = stale_pattern.search(text[:300])  # only check first 300 chars (header area)
    assert not stale_match, (
        f"blocked_commands.md header still contains a stale P-series reference: "
        f"'{stale_match.group(0)}'. Update it to match the current H/S/C/G series labelling."
    )

    # Must contain the current label
    assert "H/S/C/G" in text[:300] or "AGENTS.md §4" in text[:300], (
        "blocked_commands.md header does not reference 'AGENTS.md §4' or 'H/S/C/G'. "
        "Ensure the file header cross-references the current prohibition section correctly."
    )


def test_agents_md_no_dead_slash_perf_reference():
    """
    Regression guard (T1-K-09): AGENTS.md §2 must not contain '/perf' — the dead
    slug that existed before the 2026-06-22 fix.  The correct slug is '/performance'.
    """
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "`/perf`" not in text, (
        "AGENTS.md §2 contains the dead workflow slug '/perf'. "
        "The correct slug is '/performance' (maps to .agent/workflows/performance.md)."
    )


def test_agents_md_no_dead_slash_qa_reference():
    """
    Regression guard (T1-K-09): AGENTS.md §2 must not contain '/qa' — the dead
    slug that existed before the 2026-06-22 fix.  The correct slug is '/test-engineer'.
    """
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "`/qa`" not in text, (
        "AGENTS.md §2 contains the dead workflow slug '/qa'. "
        "The correct slug is '/test-engineer' (maps to .agent/workflows/test-engineer.md)."
    )


def test_agents_md_section_2_exists():
    """
    Structural guard: AGENTS.md must contain a '## 2.' section heading so that
    other consistency tests can scope their searches correctly.
    """
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert re.search(r"^## 2\.", text, re.MULTILINE), (
        "AGENTS.md does not contain a '## 2.' section heading. "
        "The workflow routing table is expected inside §2."
    )


def test_agents_md_section_4_uses_hscg_labels():
    """
    T1-K-09: AGENTS.md §4 must use the H/S/C/G series labels, not the old P-series.
    Checks for at least one table row with the new label pattern (e.g. '| H-01 |').
    """
    text = AGENTS_MD.read_text(encoding="utf-8")
    # Match rows like "| H-01 |" or "| C-04 |"
    hscg_pattern = re.compile(r"\|\s*[HSCG]-\d{2}\s*\|")
    assert hscg_pattern.search(text), (
        "AGENTS.md §4 does not appear to contain H/S/C/G series prohibition labels. "
        "Expected rows like '| H-01 |', '| C-04 |' in the prohibition tables."
    )
