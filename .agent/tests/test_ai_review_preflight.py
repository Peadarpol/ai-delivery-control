import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

# Load ai_review directly from its absolute file path.
# The module lives outside the normal src package tree (src/scripts/), so
# importlib is the cleanest import approach.
#
# ai_review.py has a module-level side effect on Windows:
#   sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
# This replaces pytest's capture file descriptor and causes a crash.
# We suppress it by patching sys.platform to "linux" during module loading.
_AI_REVIEW_PATH = (
    Path(__file__).resolve().parents[2] / "src" / "scripts" / "ai_review.py"
)
_spec = importlib.util.spec_from_file_location("ai_review", _AI_REVIEW_PATH)
assert (
    _spec is not None and _spec.loader is not None
), f"Cannot locate ai_review.py at {_AI_REVIEW_PATH}"
ai_review = importlib.util.module_from_spec(_spec)
sys.modules["ai_review"] = ai_review
with patch("sys.platform", "linux"):
    _spec.loader.exec_module(ai_review)  # type: ignore[union-attr]

from ai_review import (  # noqa: E402
    PlanOutput,
    ReviewVerdict,
    RouteDecision,
    check_preflight_shortcut,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_diff(
    filename: str,
    added_lines: list[str],
    removed_lines: list[str] | None = None,
) -> str:
    """Build a minimal but realistic git-diff string for a single file."""
    removed = removed_lines or []
    body = "\n".join(
        [f"-{line}" for line in removed] + [f"+{line}" for line in added_lines]
    )
    return (
        f"diff --git a/{filename} b/{filename}\n"
        f"index 0000000..1111111 100644\n"
        f"--- a/{filename}\n"
        f"+++ b/{filename}\n"
        f"@@ -1,{len(removed)} +1,{len(added_lines)} @@\n"
        f"{body}\n"
    )


# Patch subprocess so check_preflight_shortcut does not shell out during tests.
def _patch_git_names(filenames: list[str]):
    """Return a context manager that patches git diff --cached --name-only."""
    mock_result = MagicMock()
    mock_result.stdout = "\n".join(filenames)
    return patch("ai_review.subprocess.run", return_value=mock_result)


# ── T1-G-02: Documentation-only diffs ─────────────────────────────────────────


class TestPreflightDocOnly:
    """All changed files have doc extensions → direct_pass_allowed."""

    def test_single_md_file(self):
        diff = _make_diff("README.md", [" added a line"])
        with _patch_git_names(["README.md"]):
            result = check_preflight_shortcut(diff)
        assert result.direct_pass_allowed is True
        assert result.requires_review is False
        assert "Documentation-only" in result.planner_note

    def test_multiple_doc_files(self):
        diff = _make_diff("docs/guide.rst", [" content"])
        with _patch_git_names(["docs/guide.rst", "CHANGELOG.txt"]):
            result = check_preflight_shortcut(diff)
        assert result.direct_pass_allowed is True

    def test_mixed_doc_and_code_not_fast(self):
        """A mix of .md and .py must NOT be fast-passed."""
        diff = _make_diff("docs/guide.md", [" content"])
        with _patch_git_names(["docs/guide.md", "src/foo.py"]):
            result = check_preflight_shortcut(diff)
        assert result.direct_pass_allowed is False
        assert result.requires_review is True


# ── T1-G-02: Whitespace-only diffs ────────────────────────────────────────────


class TestPreflightWhitespaceOnly:
    """Changed lines are blank or whitespace → direct_pass_allowed."""

    def test_blank_lines_added(self):
        diff = _make_diff("src/app.py", ["", "   ", "\t"])
        with _patch_git_names(["src/app.py"]):
            result = check_preflight_shortcut(diff)
        assert result.direct_pass_allowed is True
        assert "Whitespace or comment-only" in result.planner_note

    def test_trailing_whitespace_removed(self):
        diff = _make_diff("src/service.py", [], removed_lines=["   ", ""])
        with _patch_git_names(["src/service.py"]):
            result = check_preflight_shortcut(diff)
        assert result.direct_pass_allowed is True


# ── T1-G-02: Comment-only diffs ───────────────────────────────────────────────


class TestPreflightCommentOnly:
    """Lines that start with comment markers → direct_pass_allowed."""

    @pytest.mark.parametrize(
        "comment_line",
        [
            "# Python comment",
            "// JavaScript comment",
            "/* CSS block open */",
            "* continuation of block comment",
            "--> closing HTML comment",
            "<!-- opening HTML comment -->",
            '"""Python docstring line"""',
            "'''Another docstring'''",
        ],
    )
    def test_single_comment_type(self, comment_line: str):
        diff = _make_diff("src/module.py", [comment_line])
        with _patch_git_names(["src/module.py"]):
            result = check_preflight_shortcut(diff)
        assert (
            result.direct_pass_allowed is True
        ), f"Expected PASS_FAST for comment line: {comment_line!r}"

    def test_mixed_comment_and_blank(self):
        diff = _make_diff("src/styles.css", ["/* colour fix */", "", "  "])
        with _patch_git_names(["src/styles.css"]):
            result = check_preflight_shortcut(diff)
        assert result.direct_pass_allowed is True


# ── T1-G-02: Real code changes ────────────────────────────────────────────────


class TestPreflightCodeChanges:
    """Actual logic changes must NOT be short-circuited."""

    def test_python_function_change(self):
        diff = _make_diff("src/service.py", ["    return x + 1"])
        with _patch_git_names(["src/service.py"]):
            result = check_preflight_shortcut(diff)
        assert result.direct_pass_allowed is False
        assert result.requires_review is True
        assert "full adversarial review" in result.planner_note

    def test_javascript_code_change(self):
        diff = _make_diff("frontend/app.js", ["const x = getUser(id);"])
        with _patch_git_names(["frontend/app.js"]):
            result = check_preflight_shortcut(diff)
        assert result.direct_pass_allowed is False

    def test_mixed_comment_and_code_not_fast(self):
        """A diff with a comment AND a real code line must not be fast-passed."""
        diff = _make_diff(
            "src/repo.py",
            ["# Updated query", "    stmt = stmt.where(Model.id == id)"],
        )
        with _patch_git_names(["src/repo.py"]):
            result = check_preflight_shortcut(diff)
        assert result.direct_pass_allowed is False


# ── T1-G-03: ReviewVerdict Pydantic model ─────────────────────────────────────


class TestReviewVerdictModel:
    """Validates ReviewVerdict fields, defaults, and constraints."""

    def test_minimal_valid_pass_verdict(self):
        v = ReviewVerdict(verdict="PASS", model="claude-sonnet-4-20250514")
        assert v.verdict == "PASS"
        assert v.verdict_tier == "cloud"  # default
        assert v.context_snapshot is None  # not populated for PASS

    def test_pass_fast_sets_preflight_tier(self):
        v = ReviewVerdict(
            verdict="PASS_FAST",
            model="preflight",
            verdict_tier="preflight",
        )
        assert v.verdict_tier == "preflight"
        assert v.token_usage == {}

    def test_fail_verdict_with_context_snapshot(self):
        snapshot = "sections=branch_isolation,micro_checks; context_chars=4200"
        v = ReviewVerdict(
            verdict="FAIL",
            model="claude-sonnet-4-20250514",
            blocking_concern="BRANCH_ISOLATION",
            context_snapshot=snapshot,
            verdict_tier="cloud",
        )
        assert v.verdict == "FAIL"
        assert v.context_snapshot == snapshot
        assert v.blocking_concern == "BRANCH_ISOLATION"

    def test_warn_verdict_with_context_snapshot(self):
        v = ReviewVerdict(
            verdict="WARN",
            model="claude-sonnet-4-20250514",
            context_snapshot="sections=micro_checks; context_chars=100",
        )
        assert v.context_snapshot is not None

    def test_fail_open_verdict(self):
        v = ReviewVerdict(
            verdict="FAIL_OPEN",
            model="claude-sonnet-4-20250514",
            fail_open_reason="Network timeout",
        )
        assert v.verdict == "FAIL_OPEN"
        assert v.fail_open_reason == "Network timeout"

    def test_local_tier_for_fallback_verdict(self):
        """T1-D-05: Gemma4 fallback verdicts use verdict_tier='local'."""
        v = ReviewVerdict(
            verdict="PASS",
            model="gemma4:latest",
            verdict_tier="local",
        )
        assert v.verdict_tier == "local"

    def test_invalid_verdict_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ReviewVerdict(verdict="UNKNOWN_VERDICT", model="test")

    def test_invalid_verdict_tier_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ReviewVerdict(verdict="PASS", model="test", verdict_tier="quantum")

    def test_backward_compat_fields_present(self):
        """Existing log readers rely on intent_alignment, summary, issues."""
        v = ReviewVerdict(
            verdict="PASS",
            model="claude-sonnet-4-20250514",
            intent_alignment="The diff achieves what the commit message describes.",
            summary="No issues found.",
            issues=[
                {
                    "severity": "LOW",
                    "concern": "CODE_QUALITY",
                    "location": "general",
                    "description": "Minor",
                    "remediation": "Rename variable.",
                }
            ],
        )
        assert v.intent_alignment is not None
        assert v.summary is not None
        assert len(v.issues) == 1

    def test_model_dump_includes_new_fields(self):
        """Serialised log record must contain verdict_tier and context_snapshot."""
        v = ReviewVerdict(
            verdict="FAIL",
            model="claude-sonnet-4-20250514",
            verdict_tier="cloud",
            context_snapshot="sections=mass_assignment,micro_checks; context_chars=3000",
        )
        data = v.model_dump()
        assert "verdict_tier" in data
        assert "context_snapshot" in data
        assert data["verdict_tier"] == "cloud"
        assert "mass_assignment" in data["context_snapshot"]


# ── T1-G-03: RouteDecision and PlanOutput ─────────────────────────────────────


class TestRouteDecision:
    def test_defaults(self):
        rd = RouteDecision()
        assert rd.review_intensity == "standard"
        assert rd.selected_tools == []

    def test_invalid_intensity_raises(self):
        with pytest.raises(ValidationError):
            RouteDecision(review_intensity="extreme")


class TestPlanOutput:
    def test_direct_pass_plan(self):
        p = PlanOutput(
            requires_review=False,
            direct_pass_allowed=True,
            planner_note="Documentation-only change detected.",
        )
        assert p.direct_pass_allowed is True

    def test_full_review_plan(self):
        p = PlanOutput(
            requires_review=True,
            direct_pass_allowed=False,
            planner_note="Code edits present.",
        )
        assert p.requires_review is True
