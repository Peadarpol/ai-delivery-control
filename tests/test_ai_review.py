"""
Tests for src/scripts/ai_review.py — diff handling, verdict persistence,
review context loading.

Tests are additive to .agent/tests/test_ai_review_preflight.py (QA-03).
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── BUG-03: Amend diff detection ─────────────────────────────────────────────


class TestGetStagedDiffAmend:
    """BUG-03: get_staged_diff() must detect amend and read HEAD~1..HEAD."""

    def _mock_run(self, commands_map):
        """Return a side_effect function that dispatches based on git args."""
        def side_effect(args, **kwargs):
            key = " ".join(args[:4])  # e.g. "git diff --staged --unified=3"
            result = MagicMock()
            result.stdout = commands_map.get(key, "")
            result.returncode = 0 if result.stdout != "__FAIL__" else 1
            if result.stdout == "__FAIL__":
                result.stdout = ""
            return result
        return side_effect

    def test_normal_commit_reads_staged(self, ai_review):
        """Normal commit: staged diff is non-empty, no fallback needed."""
        commands = {"git diff --staged --unified=3": "diff --git a/f.py b/f.py\n+code"}
        with patch.object(ai_review, "subprocess") as mock_sp:
            mock_sp.run.side_effect = self._mock_run(commands)
            result = ai_review.get_staged_diff()
        assert "diff --git" in result

    def test_amend_with_orig_head_reads_head_diff(self, ai_review):
        """SE-02: Amend at commit-msg stage triggers HEAD~1..HEAD fallback."""
        commands = {
            "git diff --staged --unified=3": "",
            "git rev-parse --verify ORIG_HEAD": "abc123",
            "git rev-list --count HEAD": "5",
            "git diff HEAD~1 HEAD": "diff --git a/f.py b/f.py\n+amended code",
        }
        with patch.object(ai_review, "subprocess") as mock_sp, \
             patch.dict(os.environ, {"PRE_COMMIT_HOOK_STAGE": "commit-msg"}):
            mock_sp.run.side_effect = self._mock_run(commands)
            result = ai_review.get_staged_diff()
        assert "amended code" in result

    def test_amend_no_orig_head_returns_empty(self, ai_review):
        """SE-02: Empty diff + commit-msg but no ORIG_HEAD = not amend."""
        commands = {
            "git diff --staged --unified=3": "",
            "git rev-parse --verify ORIG_HEAD": "__FAIL__",
        }
        with patch.object(ai_review, "subprocess") as mock_sp, \
             patch.dict(os.environ, {"PRE_COMMIT_HOOK_STAGE": "commit-msg"}):
            mock_sp.run.side_effect = self._mock_run(commands)
            result = ai_review.get_staged_diff()
        assert result.strip() == ""

    def test_amend_single_commit_uses_empty_tree(self, ai_review):
        """SE-01: Amend on initial commit uses empty tree hash."""
        empty_tree = "4b825dc642cb6eb9a060e54bf899d15f"
        captured_args = []

        def side_effect(args, **kwargs):
            captured_args.append(args)
            key = " ".join(args[:4])
            result = MagicMock()
            if key == "git diff --staged --unified=3":
                result.stdout = ""
            elif key == "git rev-parse --verify ORIG_HEAD":
                result.stdout = "abc123"
                result.returncode = 0
            elif key == "git rev-list --count HEAD":
                result.stdout = "1"
            elif empty_tree in str(args):
                result.stdout = "diff --git a/init.py b/init.py\n+initial code"
            else:
                result.stdout = ""
            result.returncode = 0
            return result

        with patch.object(ai_review, "subprocess") as mock_sp, \
             patch.dict(os.environ, {"PRE_COMMIT_HOOK_STAGE": "commit-msg"}):
            mock_sp.run.side_effect = side_effect
            result = ai_review.get_staged_diff()
        assert "initial code" in result
        # Verify empty tree hash was used
        tree_calls = [a for a in captured_args if empty_tree in str(a)]
        assert len(tree_calls) >= 1

    def test_amend_fallback_exception_is_caught(self, ai_review):
        """Diff retrieval must never crash the gate."""
        def side_effect(args, **kwargs):
            key = " ".join(args[:4])
            if key == "git diff --staged --unified=3":
                result = MagicMock()
                result.stdout = ""
                return result
            raise OSError("Simulated git failure")

        with patch.object(ai_review, "subprocess") as mock_sp, \
             patch.dict(os.environ, {"PRE_COMMIT_HOOK_STAGE": "commit-msg"}):
            mock_sp.run.side_effect = side_effect
            # Must not raise
            result = ai_review.get_staged_diff()
        assert isinstance(result, str)


# ── Verdict persistence ──────────────────────────────────────────────────────


class TestVerdictPersistence:
    """All verdict types must be persisted to .ai-review-log.jsonl."""

    def test_pass_verdict_persisted(self, ai_review, tmp_path):
        """PASS verdicts must be written to the log."""
        with patch.object(ai_review, "PROJECT_ROOT", tmp_path):
            verdict = ai_review.ReviewVerdict(
                verdict="PASS", model="test-model"
            )
            ai_review._persist_verdict(verdict_obj=verdict, provider_name="anthropic")

        log_path = tmp_path / ".ai-review-log.jsonl"
        assert log_path.exists()
        record = json.loads(log_path.read_text().strip())
        assert record["verdict"] == "PASS"
        assert record["provider"] == "anthropic"

    def test_pass_fast_verdict_persisted(self, ai_review, tmp_path):
        with patch.object(ai_review, "PROJECT_ROOT", tmp_path):
            verdict = ai_review.ReviewVerdict(
                verdict="PASS_FAST", model="preflight", verdict_tier="preflight"
            )
            ai_review._persist_verdict(verdict_obj=verdict)

        log_path = tmp_path / ".ai-review-log.jsonl"
        assert log_path.exists()
        record = json.loads(log_path.read_text().strip())
        assert record["verdict"] == "PASS_FAST"
        assert record["verdict_tier"] == "preflight"

    def test_fail_open_verdict_persisted(self, ai_review, tmp_path):
        with patch.object(ai_review, "PROJECT_ROOT", tmp_path):
            ai_review._persist_verdict(fail_open_reason="Network timeout")

        log_path = tmp_path / ".ai-review-log.jsonl"
        record = json.loads(log_path.read_text().strip())
        assert record["verdict"] == "FAIL_OPEN"
        assert record["fail_open_reason"] == "Network timeout"


# ── Review context two-layer ─────────────────────────────────────────────────


class TestReviewContextTwoLayer:
    """Universal + project context concatenation."""

    def test_universal_only(self, ai_review, tmp_path):
        universal = tmp_path / "review_context_universal.md"
        universal.write_text("UNIVERSAL RULES", encoding="utf-8")

        with patch.object(ai_review, "UNIVERSAL_CONTEXT_FILE", universal), \
             patch.object(ai_review, "PROJECT_CONTEXT_FILE", tmp_path / "none.md"):
            result = ai_review.load_review_context()
        assert "UNIVERSAL RULES" in result

    def test_both_layers(self, ai_review, tmp_path):
        universal = tmp_path / "review_context_universal.md"
        project = tmp_path / "review_context_project.md"
        universal.write_text("UNIVERSAL CONTENT", encoding="utf-8")
        project.write_text("PROJECT CONTENT", encoding="utf-8")

        with patch.object(ai_review, "UNIVERSAL_CONTEXT_FILE", universal), \
             patch.object(ai_review, "PROJECT_CONTEXT_FILE", project):
            result = ai_review.load_review_context()
        assert "UNIVERSAL CONTENT" in result
        assert "PROJECT CONTENT" in result
        assert result.index("UNIVERSAL") < result.index("PROJECT")

    def test_missing_universal_exits(self, ai_review, tmp_path):
        with patch.object(ai_review, "UNIVERSAL_CONTEXT_FILE", tmp_path / "missing.md"):
            with pytest.raises(SystemExit):
                ai_review.load_review_context()


# ── _build_user_message ──────────────────────────────────────────────────────


class TestBuildUserMessage:
    """ARCH-01: Message assembly in orchestrator."""

    def test_minimal_message(self, ai_review):
        result = ai_review._build_user_message("diff content", "feat: add thing", "")
        assert "## Commit Message" in result
        assert "feat: add thing" in result
        assert "## Staged Diff" in result
        assert "diff content" in result

    def test_all_context_layers(self, ai_review):
        result = ai_review._build_user_message(
            "diff", "msg", "arch context",
            repo_map="map", adr_context="adr", co_change_context="co-change"
        )
        assert "## Project Architecture Guidelines" in result
        assert "## Workspace Structure" in result
        assert "## Active ADR Contexts" in result
        assert "## Co-change Blast Radius Alerts" in result

    def test_empty_commit_message(self, ai_review):
        result = ai_review._build_user_message("diff", "   ", "")
        assert "(no commit message provided)" in result
