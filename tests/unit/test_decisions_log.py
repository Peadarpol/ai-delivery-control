"""
Unit tests for record_decision helper in harness_utils.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYS_SCRIPTS = PROJECT_ROOT / "src" / "scripts"
if str(SYS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SYS_SCRIPTS))

import pytest
import harness_utils


def test_record_decision_appends_to_end(tmp_path):
    """Verify record_decision appends new entries to the true end of the file."""
    log_path = tmp_path / "decisions_log.md"
    harness_utils.record_decision(
        title="First Entry",
        decision="Did X",
        context="Because Y",
        consequence="Result Z",
        date="2026-01-01",
        log_path=log_path,
    )
    harness_utils.record_decision(
        title="Second Entry",
        decision="Did A",
        context="Because B",
        consequence="Result C",
        date="2026-01-02",
        log_path=log_path,
    )
    content = log_path.read_text(encoding="utf-8")
    # Second entry must appear AFTER the first — never prepended or inserted mid-file.
    assert content.index("First Entry") < content.index("Second Entry")


def test_record_decision_rejects_empty_fields(tmp_path):
    """Verify record_decision raises ValueError when required fields are empty."""
    log_path = tmp_path / "decisions_log.md"

    with pytest.raises(ValueError, match="non-empty title, decision, context, and consequence"):
        harness_utils.record_decision(
            title="X",
            decision="",
            context="Y",
            consequence="Z",
            log_path=log_path,
        )

    with pytest.raises(ValueError, match="non-empty title, decision, context, and consequence"):
        harness_utils.record_decision(
            title="   ",
            decision="D",
            context="C",
            consequence="Cons",
            log_path=log_path,
        )


def test_record_decision_rejects_invalid_date(tmp_path):
    """Verify record_decision raises ValueError when date format is invalid."""
    log_path = tmp_path / "decisions_log.md"

    with pytest.raises(ValueError, match="date must be YYYY-MM-DD format"):
        harness_utils.record_decision(
            title="X",
            decision="D",
            context="C",
            consequence="Cons",
            date="not-a-date",
            log_path=log_path,
        )


def test_record_decision_creates_file_if_missing(tmp_path):
    """Verify record_decision creates decisions_log.md with header if missing."""
    log_path = tmp_path / "decisions_log.md"
    assert not log_path.exists()

    harness_utils.record_decision(
        title="Initial Setup",
        decision="Decision D",
        context="Context C",
        consequence="Consequence C",
        date="2026-01-01",
        log_path=log_path,
    )
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert content.startswith("# Decisions Log\n")
    assert "## 2026-01-01: Initial Setup" in content


def test_record_decision_supports_extra_fields(tmp_path):
    """Verify record_decision appends extra labeled fields cleanly."""
    log_path = tmp_path / "decisions_log.md"

    harness_utils.record_decision(
        title="Release v1.4.10",
        decision="Delivered release",
        context="Governance hardening",
        consequence="All tests pass",
        date="2026-07-20",
        extra_fields={"Gate Coverage Audit": "5 commits fail-opened due to NameError and were manually verified"},
        log_path=log_path,
    )

    content = log_path.read_text(encoding="utf-8")
    assert "- **Gate Coverage Audit**: 5 commits fail-opened due to NameError and were manually verified" in content


def test_record_decision_rejects_backdated_entry(tmp_path):
    """Verify record_decision refuses an entry dated earlier than the last existing entry."""
    log_path = tmp_path / "decisions_log.md"
    harness_utils.record_decision(
        title="Later Entry", decision="D", context="C", consequence="Cons",
        date="2026-06-01", log_path=log_path,
    )
    with pytest.raises(ValueError, match="earlier than"):
        harness_utils.record_decision(
            title="Earlier Entry", decision="D", context="C", consequence="Cons",
            date="2026-05-01", log_path=log_path,
        )


def test_record_decision_allows_same_date_entries(tmp_path):
    """Verify same-day entries are allowed (not considered 'backdated')."""
    log_path = tmp_path / "decisions_log.md"
    harness_utils.record_decision(
        title="First Today", decision="D", context="C", consequence="Cons",
        date="2026-06-01", log_path=log_path,
    )
    harness_utils.record_decision(
        title="Second Today", decision="D", context="C", consequence="Cons",
        date="2026-06-01", log_path=log_path,
    )
    content = log_path.read_text(encoding="utf-8")
    assert content.count("## 2026-06-01:") == 2


def test_archive_old_decisions_noop_under_threshold(tmp_path):
    """Verify archive_old_decisions does nothing when under the line threshold."""
    log_path = tmp_path / "decisions_log.md"
    archive_path = tmp_path / "decisions_log_archive.md"
    harness_utils.record_decision(
        title="Only Entry", decision="D", context="C", consequence="Cons",
        date="2026-06-01", log_path=log_path,
    )
    count = harness_utils.archive_old_decisions(threshold_lines=150, log_path=log_path, archive_path=archive_path)
    assert count == 0
    assert not archive_path.exists()


def test_archive_old_decisions_moves_oldest_entries(tmp_path):
    """Verify archive_old_decisions moves entries from the front, appends to archive."""
    log_path = tmp_path / "decisions_log.md"
    archive_path = tmp_path / "decisions_log_archive.md"
    for i in range(1, 30):
        harness_utils.record_decision(
            title=f"Entry {i}",
            decision="D" * 20, context="C" * 20, consequence="Cons" * 20,
            date=f"2026-01-{i:02d}", log_path=log_path,
        )
    count = harness_utils.archive_old_decisions(threshold_lines=50, log_path=log_path, archive_path=archive_path)
    assert count > 0
    archive_content = archive_path.read_text(encoding="utf-8")
    assert "Entry 1" in archive_content
    remaining_content = log_path.read_text(encoding="utf-8")
    assert "Entry 29" in remaining_content  # newest entry must still be in the main log


def test_archive_old_decisions_refuses_unsorted_log(tmp_path):
    """Verify archive_old_decisions refuses to run against a disordered log."""
    log_path = tmp_path / "decisions_log.md"
    log_path.write_text(
        "# Decisions Log\n"
        "## 2026-06-01: Later\n- **Decision**: D\n- **Context**: C\n- **Consequence**: Cons\n"
        "## 2026-01-01: Earlier\n- **Decision**: D\n- **Context**: C\n- **Consequence**: Cons\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not in ascending chronological order"):
        harness_utils.archive_old_decisions(threshold_lines=1, log_path=log_path)


def test_archive_old_decisions_never_empties_log(tmp_path):
    """Verify at least one entry always remains in the main log."""
    log_path = tmp_path / "decisions_log.md"
    archive_path = tmp_path / "decisions_log_archive.md"
    harness_utils.record_decision(
        title="Sole Entry", decision="D" * 500, context="C" * 500, consequence="Cons" * 500,
        date="2026-01-01", log_path=log_path,
    )
    harness_utils.archive_old_decisions(threshold_lines=1, log_path=log_path, archive_path=archive_path)
    content = log_path.read_text(encoding="utf-8")
    assert "Sole Entry" in content
