"""
tests/unit/test_acceptance_hook.py

Unit tests for src/scripts/acceptance_hook.py (T1-L-05a).

Key behaviours tested:
  - Non-feature branches exit with code 2 (skip).
  - No spec refs in branch commits → exit 0 (nothing to check).
  - All specs ACCEPTED → exit 0.
  - Any spec not ACCEPTED → exit 1 with the failing spec listed.
  - Spec files with missing status field are treated as UNKNOWN (→ fail).
  - Exit codes are correct for each scenario.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.scripts.acceptance_hook import (
    _get_current_branch,
    _is_feature_branch,
    _resolve_specs_dir,
    _load_spec_status,
    _get_branch_spec_refs,
    main,
)


# ---------------------------------------------------------------------------
# _is_feature_branch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("branch,expected", [
    ("feat/framework-v1.4.0-release", True),
    ("feature/my-thing", True),
    ("release/v2.0.0", True),
    ("main", False),
    ("hotfix/typo", False),
    ("fix/ci-description", False),
    ("", False),
])
def test_is_feature_branch(branch, expected):
    assert _is_feature_branch(branch) == expected


# ---------------------------------------------------------------------------
# _load_spec_status
# ---------------------------------------------------------------------------


def test_load_spec_status_reads_accepted(tmp_path):
    """Reads status: ACCEPTED from a spec file."""
    spec = tmp_path / "SPEC-001.md"
    spec.write_text(
        "# SPEC-001 Title\n\nstatus: ACCEPTED\n\nSome content.\n",
        encoding="utf-8",
    )

    statuses = _load_spec_status(tmp_path)
    assert statuses.get("SPEC-001") == "ACCEPTED"


def test_load_spec_status_reads_draft(tmp_path):
    spec = tmp_path / "SPEC-042.md"
    spec.write_text("status: DRAFT\n", encoding="utf-8")
    statuses = _load_spec_status(tmp_path)
    assert statuses.get("SPEC-042") == "DRAFT"


def test_load_spec_status_missing_status_is_unknown(tmp_path):
    spec = tmp_path / "SPEC-099.md"
    spec.write_text("# No status field here.\n", encoding="utf-8")
    statuses = _load_spec_status(tmp_path)
    assert statuses.get("SPEC-099") == "UNKNOWN"


def test_load_spec_status_nonexistent_dir(tmp_path):
    statuses = _load_spec_status(tmp_path / "nonexistent")
    assert statuses == {}


def test_load_spec_status_multiple_specs(tmp_path):
    (tmp_path / "SPEC-001.md").write_text("status: ACCEPTED\n", encoding="utf-8")
    (tmp_path / "SPEC-002.md").write_text("status: IN_REVIEW\n", encoding="utf-8")
    (tmp_path / "SPEC-003.md").write_text("status: ACCEPTED\n", encoding="utf-8")
    # Non-spec file should be ignored
    (tmp_path / "README.md").write_text("status: something\n", encoding="utf-8")

    statuses = _load_spec_status(tmp_path)
    assert statuses == {
        "SPEC-001": "ACCEPTED",
        "SPEC-002": "IN_REVIEW",
        "SPEC-003": "ACCEPTED",
    }


# ---------------------------------------------------------------------------
# _get_branch_spec_refs
# ---------------------------------------------------------------------------


def test_get_branch_spec_refs_extracts_ids(tmp_path):
    """Parses SPEC-NNN references from mock git log output."""
    mock_output = (
        "feat(v1.4.0): implement SPEC-101 and SPEC-102\n"
        "fix: typo\n"
        "docs: update SPEC-101 notes\n"
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
        refs = _get_branch_spec_refs("feat/test", tmp_path)

    # SPEC-101 mentioned twice but should appear once
    assert refs == ["SPEC-101", "SPEC-102"]


def test_get_branch_spec_refs_empty_log(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        refs = _get_branch_spec_refs("feat/test", tmp_path)
    assert refs == []


def test_get_branch_spec_refs_git_failure(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        refs = _get_branch_spec_refs("feat/test", tmp_path)
    assert refs == []


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------


def _make_spec(specs_dir: Path, spec_id: str, status: str) -> None:
    num = spec_id.replace("SPEC-", "")
    (specs_dir / f"{spec_id}.md").write_text(f"status: {status}\n", encoding="utf-8")


def test_main_skips_non_feature_branch(tmp_path):
    """Non-feature branches exit 2."""
    with patch("src.scripts.acceptance_hook._get_current_branch", return_value="main"):
        result = main()
    assert result == 2


def test_main_exits_0_when_no_spec_refs(tmp_path):
    """No SPEC references in commits → exit 0."""
    with (
        patch("src.scripts.acceptance_hook._get_current_branch", return_value="feat/abc"),
        patch("src.scripts.acceptance_hook._resolve_specs_dir", return_value=tmp_path),
        patch("src.scripts.acceptance_hook._get_branch_spec_refs", return_value=[]),
    ):
        result = main()
    assert result == 0


def test_main_exits_0_when_all_accepted(tmp_path):
    """All referenced specs ACCEPTED → exit 0."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    _make_spec(specs_dir, "SPEC-001", "ACCEPTED")
    _make_spec(specs_dir, "SPEC-002", "ACCEPTED")

    with (
        patch("src.scripts.acceptance_hook._get_current_branch", return_value="feat/test"),
        patch("src.scripts.acceptance_hook._resolve_specs_dir", return_value=specs_dir),
        patch("src.scripts.acceptance_hook._get_branch_spec_refs", return_value=["SPEC-001", "SPEC-002"]),
        patch("src.scripts.acceptance_hook._sync_accepted_to_db"),
    ):
        result = main()
    assert result == 0


def test_main_exits_1_when_spec_not_accepted(tmp_path):
    """A spec in DRAFT status causes exit 1."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    _make_spec(specs_dir, "SPEC-001", "ACCEPTED")
    _make_spec(specs_dir, "SPEC-002", "DRAFT")

    with (
        patch("src.scripts.acceptance_hook._get_current_branch", return_value="feat/test"),
        patch("src.scripts.acceptance_hook._resolve_specs_dir", return_value=specs_dir),
        patch("src.scripts.acceptance_hook._get_branch_spec_refs", return_value=["SPEC-001", "SPEC-002"]),
        patch("src.scripts.acceptance_hook._sync_accepted_to_db"),
    ):
        result = main()
    assert result == 1


def test_main_exits_1_when_spec_not_found(tmp_path):
    """A referenced spec with no file status shows as NOT FOUND → exit 1."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    # Only SPEC-001 file exists; SPEC-999 does not

    with (
        patch("src.scripts.acceptance_hook._get_current_branch", return_value="feat/test"),
        patch("src.scripts.acceptance_hook._resolve_specs_dir", return_value=specs_dir),
        patch("src.scripts.acceptance_hook._get_branch_spec_refs", return_value=["SPEC-999"]),
        patch("src.scripts.acceptance_hook._sync_accepted_to_db"),
    ):
        result = main()
    assert result == 1


def test_main_exits_1_when_spec_unknown_status(tmp_path):
    """A spec with no status field in the file is treated as UNKNOWN → exit 1."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "SPEC-010.md").write_text("# No status line here\n", encoding="utf-8")

    with (
        patch("src.scripts.acceptance_hook._get_current_branch", return_value="feat/test"),
        patch("src.scripts.acceptance_hook._resolve_specs_dir", return_value=specs_dir),
        patch("src.scripts.acceptance_hook._get_branch_spec_refs", return_value=["SPEC-010"]),
        patch("src.scripts.acceptance_hook._sync_accepted_to_db"),
    ):
        result = main()
    assert result == 1
