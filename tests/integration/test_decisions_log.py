"""
Unit tests for record_decision and archive_old_decisions helpers in harness_utils.
"""

import datetime
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
        impact="medium",
        log_path=log_path,
    )
    harness_utils.record_decision(
        title="Second Entry",
        decision="Did A",
        context="Because B",
        consequence="Result C",
        date="2026-01-02",
        impact="medium",
        log_path=log_path,
    )
    content = log_path.read_text(encoding="utf-8")
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
            impact="medium",
            log_path=log_path,
        )

    with pytest.raises(ValueError, match="non-empty title, decision, context, and consequence"):
        harness_utils.record_decision(
            title="   ",
            decision="D",
            context="C",
            consequence="Cons",
            impact="medium",
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
            impact="medium",
            log_path=log_path,
        )


def test_record_decision_rejects_unclassified_impact(tmp_path):
    """Scenario 4d: record_decision raises ValueError on missing or invalid impact."""
    log_path = tmp_path / "decisions_log.md"

    with pytest.raises(ValueError, match="requires impact to be one of 'high', 'medium', 'low'"):
        harness_utils.record_decision(
            title="X", decision="D", context="C", consequence="Cons",
            impact=None, log_path=log_path,
        )

    with pytest.raises(ValueError, match="requires impact to be one of 'high', 'medium', 'low'"):
        harness_utils.record_decision(
            title="X", decision="D", context="C", consequence="Cons",
            impact="", log_path=log_path,
        )

    with pytest.raises(ValueError, match="requires impact to be one of 'high', 'medium', 'low'"):
        harness_utils.record_decision(
            title="X", decision="D", context="C", consequence="Cons",
            impact="critical", log_path=log_path,
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
        impact="medium",
        log_path=log_path,
    )
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert content.startswith("# Decisions Log\n")
    assert "## 2026-01-01: Initial Setup" in content
    assert "- **Impact**: medium" in content


def test_record_decision_supports_extra_fields(tmp_path):
    """Verify record_decision appends extra labeled fields cleanly."""
    log_path = tmp_path / "decisions_log.md"

    harness_utils.record_decision(
        title="Release v1.4.10",
        decision="Delivered release",
        context="Governance hardening",
        consequence="All tests pass",
        date="2026-07-20",
        impact="high",
        extra_fields={"Gate Coverage Audit": "5 commits fail-opened due to NameError and were manually verified"},
        log_path=log_path,
    )

    content = log_path.read_text(encoding="utf-8")
    assert "- **Impact**: high" in content
    assert "- **Gate Coverage Audit**: 5 commits fail-opened due to NameError and were manually verified" in content


def test_record_decision_rejects_backdated_entry(tmp_path):
    """Verify record_decision refuses an entry dated earlier than the last existing entry."""
    log_path = tmp_path / "decisions_log.md"
    harness_utils.record_decision(
        title="Later Entry", decision="D", context="C", consequence="Cons",
        date="2026-06-01", impact="medium", log_path=log_path,
    )
    with pytest.raises(ValueError, match="earlier than"):
        harness_utils.record_decision(
            title="Earlier Entry", decision="D", context="C", consequence="Cons",
            date="2026-05-01", impact="medium", log_path=log_path,
        )


def test_record_decision_allows_same_date_entries(tmp_path):
    """Verify same-day entries are allowed (not considered 'backdated')."""
    log_path = tmp_path / "decisions_log.md"
    harness_utils.record_decision(
        title="First Today", decision="D", context="C", consequence="Cons",
        date="2026-06-01", impact="medium", log_path=log_path,
    )
    harness_utils.record_decision(
        title="Second Today", decision="D", context="C", consequence="Cons",
        date="2026-06-01", impact="medium", log_path=log_path,
    )
    content = log_path.read_text(encoding="utf-8")
    assert content.count("## 2026-06-01:") == 2


def test_archive_old_decisions_noop_under_threshold(tmp_path):
    """Verify archive_old_decisions does nothing when under the line threshold."""
    log_path = tmp_path / "decisions_log.md"
    archive_path = tmp_path / "decisions_log_archive.md"
    harness_utils.record_decision(
        title="Only Entry", decision="D", context="C", consequence="Cons",
        date="2026-06-01", impact="medium", log_path=log_path,
    )
    count = harness_utils.archive_old_decisions(threshold_lines=150, log_path=log_path, archive_path=archive_path)
    assert count == 0
    assert not archive_path.exists()


def test_archive_old_decisions_retains_high_impact(tmp_path):
    """Scenario 4e: High-impact entries remain in decisions_log.md regardless of age."""
    log_path = tmp_path / "decisions_log.md"
    archive_path = tmp_path / "decisions_log_archive.md"

    # Old high-impact entry
    harness_utils.record_decision(
        title="Old High Impact Architectural Precedent",
        decision="D" * 20, context="C" * 20, consequence="Cons" * 20,
        date="2026-01-01", impact="high", log_path=log_path,
    )

    # Subsequent medium/low entries pushing line count over threshold
    for i in range(2, 30):
        harness_utils.record_decision(
            title=f"Entry {i}",
            decision="D" * 20, context="C" * 20, consequence="Cons" * 20,
            date=f"2026-01-{i:02d}", impact="medium" if i % 2 == 0 else "low",
            log_path=log_path,
        )

    count = harness_utils.archive_old_decisions(threshold_lines=50, log_path=log_path, archive_path=archive_path)
    assert count > 0

    log_content = log_path.read_text(encoding="utf-8")
    assert "Old High Impact Architectural Precedent" in log_content


def test_archive_old_decisions_age_weighted_eviction_priority(tmp_path):
    """Scenario 4f: Eviction priority uses age_in_days / impact_weight."""
    log_path = tmp_path / "decisions_log.md"
    archive_path = tmp_path / "decisions_log_archive.md"

    now_date = datetime.datetime.now(datetime.timezone.utc).date()
    medium_date = (now_date - datetime.timedelta(days=40)).strftime("%Y-%m-%d")
    low_date = (now_date - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    harness_utils.record_decision(
        title="Medium Entry 40 Days Old",
        decision="D" * 30, context="C" * 30, consequence="Cons" * 30,
        date=medium_date, impact="medium", log_path=log_path,
    )
    harness_utils.record_decision(
        title="Low Entry 30 Days Old",
        decision="D" * 30, context="C" * 30, consequence="Cons" * 30,
        date=low_date, impact="low", log_path=log_path,
    )

    count = harness_utils.archive_old_decisions(threshold_lines=5, log_path=log_path, archive_path=archive_path)
    assert count == 1

    archive_content = archive_path.read_text(encoding="utf-8")
    assert "Low Entry 30 Days Old" in archive_content
    log_content = log_path.read_text(encoding="utf-8")
    assert "Medium Entry 40 Days Old" in log_content


def test_archive_old_decisions_all_high_fails_loud_archive_zero(tmp_path):
    """Scenario 4g: Log exceeding threshold with only high entries archives zero."""
    log_path = tmp_path / "decisions_log.md"
    archive_path = tmp_path / "decisions_log_archive.md"

    for i in range(1, 30):
        harness_utils.record_decision(
            title=f"High Entry {i}",
            decision="D" * 20, context="C" * 20, consequence="Cons" * 20,
            date=f"2026-01-{i:02d}", impact="high", log_path=log_path,
        )

    count = harness_utils.archive_old_decisions(threshold_lines=50, log_path=log_path, archive_path=archive_path)
    assert count == 0
    assert not archive_path.exists()


def test_archive_old_decisions_refuses_unsorted_log(tmp_path):
    """Verify archive_old_decisions refuses to run against a disordered log."""
    log_path = tmp_path / "decisions_log.md"
    log_path.write_text(
        "# Decisions Log\n"
        "## 2026-06-01: Later\n- **Decision**: D\n- **Context**: C\n- **Consequence**: Cons\n- **Impact**: medium\n"
        "## 2026-01-01: Earlier\n- **Decision**: D\n- **Context**: C\n- **Consequence**: Cons\n- **Impact**: medium\n",
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
        date="2026-01-01", impact="medium", log_path=log_path,
    )
    harness_utils.archive_old_decisions(threshold_lines=1, log_path=log_path, archive_path=archive_path)
    content = log_path.read_text(encoding="utf-8")
    assert "Sole Entry" in content



def test_record_decision_prevents_tab_corruption_and_preserves_leading_t(tmp_path):
    """Scenario 3 (BUG-19): record_decision preserves leading 't' character and strips literal tabs."""
    log_path = tmp_path / "decisions_log.md"
    harness_utils.record_decision(
        title="testing leading t",
        decision="the decision starts with t\twith tab inside",
        context="testing context",
        consequence="the consequence",
        date="2026-07-26",
        impact="medium",
        log_path=log_path,
    )
    content = log_path.read_text(encoding="utf-8")
    assert "## 2026-07-26: testing leading t" in content
    assert "- **Decision**: the decision starts with t with tab inside" in content
    assert "\t" not in content
