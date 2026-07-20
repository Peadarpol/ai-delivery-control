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
