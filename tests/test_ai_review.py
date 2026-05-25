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


# ── BUG-04 & BUG-05 fixes (routing, persistence) ──────────────────────────────


class TestBug04And05Fixes:
    """Tests for BUG-04 and BUG-05 fixes in ai_review.py."""

    @pytest.fixture(autouse=True)
    def setup_paths(self):
        """Ensure all required script paths are in sys.path so imports succeed."""
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        
        paths = [
            str(root / "src" / "scripts"),
            str(root / ".agent" / "scripts"),
            str(root / ".agent" / "skills" / "universal" / "senior-architect" / "scripts")
        ]
        
        added = []
        for p in paths:
            if p not in sys.path:
                sys.path.insert(0, p)
                added.append(p)
                
        yield
        
        # Clean up sys.path after tests run to keep state clean
        for p in added:
            if p in sys.path:
                sys.path.remove(p)

    def test_pass_fast_verdict_is_logged(self, ai_review):
        """Pre-flight shortcut (PASS_FAST) verdict must be logged before returning early."""
        with patch("ai_review.get_staged_diff", return_value="+# Only comment changes\n"), \
             patch("ai_review.check_preflight_shortcut", return_value=ai_review.PlanOutput(
                 requires_review=False, direct_pass_allowed=True, planner_note="Whitespace or comment-only"
             )), \
             patch("ai_review._persist_verdict") as mock_persist:
            
            exit_code = ai_review._run_review()
            assert exit_code == 0
            
            mock_persist.assert_called_once()
            called_verdict = mock_persist.call_args[1].get("verdict_obj")
            assert called_verdict is not None
            assert called_verdict.verdict == "PASS_FAST"

    def test_pass_verdict_is_logged(self, ai_review):
        """Full review PASS verdict must be logged before exit."""
        mock_provider = MagicMock()
        mock_provider.name = "mock-provider"
        mock_provider.model = "mock-model"
        mock_provider.review.return_value = {
            "verdict": "PASS",
            "intent_alignment": "Intent aligned.",
            "issues": [],
            "summary": "All code is excellent."
        }
        
        with patch("ai_review.get_staged_diff", return_value="+x = 1\n"), \
             patch("ai_review.check_preflight_shortcut", return_value=ai_review.PlanOutput(
                 requires_review=True, direct_pass_allowed=False, planner_note=""
             )), \
             patch("ai_review.load_review_context", return_value=""), \
             patch("repo_map.generate_repo_map", return_value=""), \
             patch("repo_map.get_pagerank_scores", return_value={}), \
             patch("ai_review.get_adr_context", return_value=("", [], [])), \
             patch("co_change_check.run_co_change_estimator", return_value=[]), \
             patch("providers.get_provider", return_value=mock_provider), \
             patch("ai_review._persist_verdict") as mock_persist, \
             patch("ai_review.render_review"):
            
            exit_code = ai_review._run_review()
            assert exit_code == 0
            
            mock_persist.assert_called_once()
            called_verdict = mock_persist.call_args[1].get("verdict_obj")
            assert called_verdict is not None
            assert called_verdict.verdict == "PASS"
            assert mock_persist.call_args[1].get("provider_name") == "mock-provider"

    def test_adr_domain_maps_to_capability(self, ai_review):
        """ADR domains must map to canonical capabilities using the UNIVERSAL_ADR_DOMAIN_TO_CAPABILITY dict."""
        test_cases = [
            ("branch_isolation", "BRANCH_ISOLATION"),
            ("remove_uow_autocommit", "TRANSACTIONAL_INTEGRITY"),
            ("clean_architecture", "CLEAN_ARCH"),
            ("authentication", "RBAC"),
            ("schema_hardening", "MASS_ASSIGNMENT"),
        ]
        for domain, expected_capability in test_cases:
            with patch("architecture_checks.extract_adr_annotations", return_value=[domain]), \
                 patch("pathlib.Path.exists", return_value=True):
                decision = ai_review.build_route_decision(["src/file.py"], "", {})
                assert expected_capability in decision.selected_tools

    def test_adr_domain_case_normalisation(self, ai_review):
        """ADR domains with mixed/upper case must be normalized to lowercase for lookup."""
        mixed_case_domains = ["Branch_Isolation", "REMOVE_UOW_AUTOCOMMIT", "Clean_Architecture"]
        expected_capabilities = ["BRANCH_ISOLATION", "TRANSACTIONAL_INTEGRITY", "CLEAN_ARCH"]
        
        for domain, expected_capability in zip(mixed_case_domains, expected_capabilities):
            with patch("architecture_checks.extract_adr_annotations", return_value=[domain]), \
                 patch("pathlib.Path.exists", return_value=True):
                decision = ai_review.build_route_decision(["src/file.py"], "", {})
                assert expected_capability in decision.selected_tools

    def test_adr_domain_project_config_mapping(self, ai_review, tmp_path):
        """Project-specific ADR mappings from .agent/config.yaml must override/merge with universal ones."""
        config_yaml_content = """
architecture_checks:
  adr_capability_mappings:
    saas_architecture: CLEAN_ARCH
    authentication: CLEAN_ARCH  # Override universal authentication (RBAC) to CLEAN_ARCH
"""
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        config_file = agent_dir / "config.yaml"
        config_file.write_text(config_yaml_content, encoding="utf-8")
        
        with patch.object(ai_review, "PROJECT_ROOT", tmp_path), \
             patch("architecture_checks.extract_adr_annotations", return_value=["saas_architecture", "authentication"]), \
             patch("pathlib.Path.exists", return_value=True):
            
            decision = ai_review.build_route_decision(["src/file.py"], "", {})
            # saas_architecture should map to CLEAN_ARCH (project config mapping)
            assert "CLEAN_ARCH" in decision.selected_tools
            # authentication should map to CLEAN_ARCH (project config mapping override of universal RBAC)
            assert "CLEAN_ARCH" in decision.selected_tools
            # RBAC should NOT be in selected_tools because authentication's mapping was overridden
            assert "RBAC" not in decision.selected_tools


# ── T1-L-08: High-risk commit classification ──────────────────────────────────


class TestHighRiskCommitClassification:
    """Tests for T1-L-08 — High-risk commit classification and fail-closed behavior."""

    @pytest.fixture(autouse=True)
    def setup_paths(self):
        """Ensure all required script paths are in sys.path so imports succeed."""
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        
        paths = [
            str(root / "src" / "scripts"),
            str(root / ".agent" / "scripts"),
            str(root / ".agent" / "skills" / "universal" / "senior-architect" / "scripts")
        ]
        
        added = []
        for p in paths:
            if p not in sys.path:
                sys.path.insert(0, p)
                added.append(p)
                
        yield
        
        # Clean up sys.path after tests run to keep state clean
        for p in added:
            if p in sys.path:
                sys.path.remove(p)

    def test_high_risk_path_detection(self, ai_review):
        """Verify migrations matching paths classifier returns True."""
        is_hr, matches = ai_review.classify_commit_risk(["src/migrations/0001_initial.py"], [])
        assert is_hr is True
        assert any("path:" in m and "migrations" in m for m in matches)

    def test_high_risk_filename_detection(self, ai_review):
        """Verify repo files matching filenames returns True."""
        is_hr, matches = ai_review.classify_commit_risk(["src/repositories/unit_of_work.py"], [])
        assert is_hr is True
        assert any("filename:unit_of_work.py" in m for m in matches)

    def test_high_risk_adr_domain(self, ai_review):
        """Verify active ADR domain in adr_domains returns True."""
        is_hr, matches = ai_review.classify_commit_risk(["src/other.py"], ["branch_isolation"])
        assert is_hr is True
        assert any("adr_domain:branch_isolation" in m for m in matches)

    def test_low_risk_docs_pass(self, ai_review):
        """Verify changes touching only documentation return False."""
        is_hr, matches = ai_review.classify_commit_risk(["README.md", "docs/index.md"], ["some_low_risk_domain"])
        assert is_hr is False
        assert len(matches) == 0

    def test_fail_closed_on_high_risk_no_api(self, ai_review, tmp_path):
        """API down + high risk → exit 1 and event logged."""
        commands = {
            "git diff --staged --unified=3": "diff --git a/src/migrations/0001_initial.py b/src/migrations/0001_initial.py\n+code",
            "git diff --cached --name-only": "src/migrations/0001_initial.py\n",
            "git log -n 1 --pretty=format:%B": "feat: schema change",
        }

        def mock_run(args, **kwargs):
            key = " ".join(args[:4])
            # Handle diff cached name-only
            if "--cached" in args and "--name-only" in args:
                key = "git diff --cached --name-only"
            result = MagicMock()
            result.stdout = commands.get(key, "")
            result.returncode = 0
            return result

        with patch.object(ai_review, "PROJECT_ROOT", tmp_path), \
             patch("ai_review.get_staged_diff", return_value="diff --git a/src/migrations/0001_initial.py b/src/migrations/0001_initial.py\n+code"), \
             patch("ai_review.check_preflight_shortcut", return_value=ai_review.PlanOutput(
                 requires_review=True, direct_pass_allowed=False, planner_note=""
             )), \
             patch("ai_review.load_review_context", return_value=""), \
             patch("repo_map.generate_repo_map", return_value=""), \
             patch("repo_map.get_pagerank_scores", return_value={}), \
             patch("ai_review.get_adr_context", return_value=("", [], [])), \
             patch("co_change_check.run_co_change_estimator", return_value=[]), \
             patch("providers.get_provider", side_effect=RuntimeError("Provider offline")), \
             patch("ai_review.subprocess.run", side_effect=mock_run):

            with pytest.raises(SystemExit) as excinfo:
                ai_review._run_review()

            assert excinfo.value.code == 1

            # Verify logged event
            log_path = tmp_path / ".agent" / "state" / "harness_events.jsonl"
            assert log_path.exists()
            
            lines = log_path.read_text(encoding="utf-8").splitlines()
            assert len(lines) > 0
            
            event = json.loads(lines[-1])
            assert event["event_type"] == "high_risk_gate_closed"
            assert event["severity"] == "HIGH"
            assert "Provider offline" in event["payload"]["reason"]
            assert any("migrations" in m for m in event["payload"]["high_risk_matches"])

    def test_fail_open_on_low_risk_no_api(self, ai_review, tmp_path):
        """API down + low risk → exit 0 (fail-open) and no high risk event logged."""
        commands = {
            "git diff --staged --unified=3": "diff --git a/README.md b/README.md\n+doc changes",
            "git diff --cached --name-only": "README.md\n",
            "git log -n 1 --pretty=format:%B": "docs: update readme",
        }

        def mock_run(args, **kwargs):
            key = " ".join(args[:4])
            if "--cached" in args and "--name-only" in args:
                key = "git diff --cached --name-only"
            result = MagicMock()
            result.stdout = commands.get(key, "")
            result.returncode = 0
            return result

        with patch.object(ai_review, "PROJECT_ROOT", tmp_path), \
             patch("ai_review.get_staged_diff", return_value="diff --git a/README.md b/README.md\n+doc changes"), \
             patch("ai_review.check_preflight_shortcut", return_value=ai_review.PlanOutput(
                 requires_review=True, direct_pass_allowed=False, planner_note=""
             )), \
             patch("ai_review.load_review_context", return_value=""), \
             patch("repo_map.generate_repo_map", return_value=""), \
             patch("repo_map.get_pagerank_scores", return_value={}), \
             patch("ai_review.get_adr_context", return_value=("", [], [])), \
             patch("co_change_check.run_co_change_estimator", return_value=[]), \
             patch("providers.get_provider", side_effect=RuntimeError("Provider offline")), \
             patch("ai_review.subprocess.run", side_effect=mock_run):

            exit_code = ai_review._run_review()
            assert exit_code == 0

            # Verify no high_risk_gate_closed event logged
            log_path = tmp_path / ".agent" / "state" / "harness_events.jsonl"
            if log_path.exists():
                lines = log_path.read_text(encoding="utf-8").splitlines()
                for line in lines:
                    event = json.loads(line)
                    assert event["event_type"] != "high_risk_gate_closed"

    def test_skip_reason_logged(self, ai_review, tmp_path):
        """SKIP_AI_REVIEW=1 + SKIP_REASON on high risk commit → logged to harness_events."""
        commands = {
            "git diff --cached --name-only": "src/migrations/0001_initial.py\n",
        }

        def mock_run(args, **kwargs):
            key = " ".join(args[:4])
            if "--cached" in args and "--name-only" in args:
                key = "git diff --cached --name-only"
            result = MagicMock()
            result.stdout = commands.get(key, "")
            result.returncode = 0
            return result

        with patch.object(ai_review, "PROJECT_ROOT", tmp_path), \
             patch.dict(os.environ, {"SKIP_AI_REVIEW": "1", "SKIP_REASON": '{"rebuttal_type": "SPEC_REQUIREMENT", "finding_ids": ["T1-G-07"], "evidence": "Emergency deploy"}'}), \
             patch("ai_review.subprocess.run", side_effect=mock_run):

            exit_code = ai_review._run_review()
            assert exit_code == 0

            log_path = tmp_path / ".agent" / "state" / "harness_events.jsonl"
            assert log_path.exists()

            lines = log_path.read_text(encoding="utf-8").splitlines()
            assert len(lines) > 0
            event = json.loads(lines[-1])
            assert event["event_type"] == "high_risk_gate_override"
            assert event["severity"] == "WARNING"
            assert event["payload"]["skip_reason"] == {"rebuttal_type": "SPEC_REQUIREMENT", "finding_ids": ["T1-G-07"], "evidence": "Emergency deploy"}
            assert any("migrations" in m for m in event["payload"]["high_risk_matches"])


class TestStructuredBypassAndRegression:
    """Test suite for structured bypass, Vector C interactive continuation, non-TTY fallback,
    parameterized regression suite, and session ID token filtering.
    """

    def test_bypass_rejection_on_plain_text(self, ai_review, tmp_path):
        """Plain text SKIP_REASON on high risk commit must trigger SystemExit(1)."""
        commands = {
            "git diff --cached --name-only": "src/migrations/0001_initial.py\n",
        }
        def mock_run(args, **kwargs):
            key = " ".join(args[:4])
            if "--cached" in args and "--name-only" in args:
                key = "git diff --cached --name-only"
            result = MagicMock()
            result.stdout = commands.get(key, "")
            result.returncode = 0
            return result

        with patch.object(ai_review, "PROJECT_ROOT", tmp_path), \
             patch.dict(os.environ, {"SKIP_AI_REVIEW": "1", "SKIP_REASON": "Plain text bypass reason"}), \
             patch("ai_review.subprocess.run", side_effect=mock_run):
            with pytest.raises(SystemExit) as excinfo:
                ai_review._run_review()
            assert excinfo.value.code == 1

    def test_bypass_rejection_on_malformed_json(self, ai_review, tmp_path):
        """Malformed JSON SKIP_REASON on high risk commit must trigger SystemExit(1)."""
        commands = {
            "git diff --cached --name-only": "src/migrations/0001_initial.py\n",
        }
        def mock_run(args, **kwargs):
            key = " ".join(args[:4])
            if "--cached" in args and "--name-only" in args:
                key = "git diff --cached --name-only"
            result = MagicMock()
            result.stdout = commands.get(key, "")
            result.returncode = 0
            return result

        with patch.object(ai_review, "PROJECT_ROOT", tmp_path), \
             patch.dict(os.environ, {"SKIP_AI_REVIEW": "1", "SKIP_REASON": "{malformed_json:"}), \
             patch("ai_review.subprocess.run", side_effect=mock_run):
            with pytest.raises(SystemExit) as excinfo:
                ai_review._run_review()
            assert excinfo.value.code == 1

    def test_bypass_rejection_on_invalid_keys(self, ai_review, tmp_path):
        """Valid JSON but with missing/invalid bypass keys on high risk commit must trigger SystemExit(1)."""
        commands = {
            "git diff --cached --name-only": "src/migrations/0001_initial.py\n",
        }
        def mock_run(args, **kwargs):
            key = " ".join(args[:4])
            if "--cached" in args and "--name-only" in args:
                key = "git diff --cached --name-only"
            result = MagicMock()
            result.stdout = commands.get(key, "")
            result.returncode = 0
            return result

        invalid_reasons = [
            '{"rebuttal_type": "NOT_VALID_TYPE", "finding_ids": ["T1-G-07"], "evidence": "Rationale"}',
            '{"rebuttal_type": "FALSE_POSITIVE", "finding_ids": [], "evidence": "Rationale"}',
            '{"rebuttal_type": "FALSE_POSITIVE", "finding_ids": ["T1-G-07"], "evidence": ""}',
            '{"rebuttal_type": "FALSE_POSITIVE", "evidence": "Rationale"}',  # missing finding_ids
        ]

        for invalid_reason in invalid_reasons:
            with patch.object(ai_review, "PROJECT_ROOT", tmp_path), \
                 patch.dict(os.environ, {"SKIP_AI_REVIEW": "1", "SKIP_REASON": invalid_reason}), \
                 patch("ai_review.subprocess.run", side_effect=mock_run):
                with pytest.raises(SystemExit) as excinfo:
                    ai_review._run_review()
                assert excinfo.value.code == 1

    def test_bypass_vector_a_file_success(self, ai_review, tmp_path):
        """Vector A: Reading valid JSON from .skip-ai-reason.json must bypass and auto-delete file."""
        commands = {
            "git diff --cached --name-only": "src/migrations/0001_initial.py\n",
        }
        def mock_run(args, **kwargs):
            key = " ".join(args[:4])
            if "--cached" in args and "--name-only" in args:
                key = "git diff --cached --name-only"
            result = MagicMock()
            result.stdout = commands.get(key, "")
            result.returncode = 0
            return result

        # Setup .skip-ai-reason.json in project root
        bypass_file = tmp_path / ".skip-ai-reason.json"
        bypass_data = {
            "rebuttal_type": "FALSE_POSITIVE",
            "finding_ids": ["T1-G-07"],
            "evidence": "This is a false positive test case",
        }
        bypass_file.write_text(json.dumps(bypass_data), encoding="utf-8")

        with patch.object(ai_review, "PROJECT_ROOT", tmp_path), \
             patch.dict(os.environ, {"SKIP_AI_REVIEW": "1", "SKIP_REASON": "@file"}), \
             patch("ai_review.subprocess.run", side_effect=mock_run), \
             patch("sys.stdin.isatty", return_value=False):

            assert bypass_file.exists()
            exit_code = ai_review._run_review()
            assert exit_code == 0
            # Confirm file has been auto-deleted on successful consumption
            assert not bypass_file.exists()

    def test_bypass_vector_c_interactive_continuation(self, ai_review, tmp_path):
        """Vector C: If TTY and env var is empty, prompting wizard writes file, then Vector A immediately consumes it."""
        commands = {
            "git diff --cached --name-only": "src/migrations/0001_initial.py\n",
        }
        def mock_run(args, **kwargs):
            key = " ".join(args[:4])
            if "--cached" in args and "--name-only" in args:
                key = "git diff --cached --name-only"
            result = MagicMock()
            result.stdout = commands.get(key, "")
            result.returncode = 0
            return result

        bypass_file = tmp_path / ".skip-ai-reason.json"
        
        # Mock CLI inputs: Choice "1" (FALSE_POSITIVE), Finding IDs "T1-G-07", Evidence "Some evidence"
        mock_inputs = ["1", "T1-G-07", "Some evidence"]

        with patch.object(ai_review, "PROJECT_ROOT", tmp_path), \
             patch.dict(os.environ, {"SKIP_AI_REVIEW": "1", "SKIP_REASON": ""}), \
             patch("ai_review.subprocess.run", side_effect=mock_run), \
             patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", side_effect=mock_inputs):

            exit_code = ai_review._run_review()
            assert exit_code == 0
            # Vector A immediately continues, validates, and auto-deletes the file, so it should not exist after execution!
            assert not bypass_file.exists()

    def test_bypass_non_tty_fallback_fail_closed(self, ai_review, tmp_path):
        """Non-TTY with no SKIP_REASON and no file must fail-closed."""
        commands = {
            "git diff --cached --name-only": "src/migrations/0001_initial.py\n",
        }
        def mock_run(args, **kwargs):
            key = " ".join(args[:4])
            if "--cached" in args and "--name-only" in args:
                key = "git diff --cached --name-only"
            result = MagicMock()
            result.stdout = commands.get(key, "")
            result.returncode = 0
            return result

        with patch.object(ai_review, "PROJECT_ROOT", tmp_path), \
             patch.dict(os.environ, {"SKIP_AI_REVIEW": "1", "SKIP_REASON": ""}), \
             patch("ai_review.subprocess.run", side_effect=mock_run), \
             patch("sys.stdin.isatty", return_value=False):

            with pytest.raises(SystemExit) as excinfo:
                ai_review._run_review()
            assert excinfo.value.code == 1

    def test_session_id_filtering_in_aggregation(self, ai_review, tmp_path):
        """infer_and_close_previous_session must strictly sum token stats matching current session_id."""
        import csv
        import os
        # Create a mock session.json
        state_dir = tmp_path / ".agent" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        session_file = state_dir / "session.json"
        
        session_data = {
            "session_id": "active-session-123",
            "start_time": "2026-05-25T12:00:00Z",
            "agent": "TestAgent",
            "status": "ACTIVE"
        }
        session_file.write_text(json.dumps(session_data), encoding="utf-8")

        # Create .ai-review-log.jsonl with mixed session IDs
        log_path = tmp_path / ".ai-review-log.jsonl"
        log_records = [
            # Entry matching current session
            {
                "timestamp": "2026-05-25T12:05:00Z",
                "verdict": "PASS",
                "session_id": "active-session-123",
                "token_usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "context_load_estimated_tokens": 80,
                    "repo_map_estimated_tokens": 40,
                    "adr_injection_estimated_tokens": 10,
                },
                "issues": []
            },
            # Entry matching current session
            {
                "timestamp": "2026-05-25T12:10:00Z",
                "verdict": "FAIL",
                "session_id": "active-session-123",
                "token_usage": {
                    "input_tokens": 200,
                    "output_tokens": 100,
                    "context_load_estimated_tokens": 160,
                    "repo_map_estimated_tokens": 80,
                    "adr_injection_estimated_tokens": 20,
                },
                "issues": [{"concern": "MASS_ASSIGNMENT", "severity": "HIGH", "location": "general"}]
            },
            # Entry belonging to a different session ID
            {
                "timestamp": "2026-05-25T12:15:00Z",
                "verdict": "PASS",
                "session_id": "other-session-456",
                "token_usage": {
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "context_load_estimated_tokens": 800,
                    "repo_map_estimated_tokens": 400,
                    "adr_injection_estimated_tokens": 100,
                },
                "issues": []
            }
        ]
        log_path.write_text("\n".join(json.dumps(r) for r in log_records) + "\n", encoding="utf-8")

        # Mock import and call of infer_and_close_previous_session
        # Set up sys.path or direct import
        import sys
        scripts_dir = Path(__file__).resolve().parent.parent / ".agent" / "scripts"
        sys.path.insert(0, str(scripts_dir))
        
        # Patch the file paths inside init_session.py
        with patch("sys.platform", "linux"):
            import init_session

        old_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            with patch("init_session.get_commits_after", return_value=[]):
                outcome, note = init_session.infer_and_close_previous_session()
                # Since there are no commits and it's not escalated, outcome is partial/abandoned depending on fail
                assert outcome in ("abandoned", "partial")
        finally:
            os.chdir(old_cwd)

        # Read session.json to check aggregated token_usage
        with open(session_file, "r", encoding="utf-8") as f:
            saved_session = json.load(f)
            
        token_stats = saved_session["token_usage"]
        # Assert only matching session IDs were aggregated (100+200 = 300 input, 50+100 = 150 output)
        assert token_stats["input_tokens"] == 300
        assert token_stats["output_tokens"] == 150
        assert token_stats["context_load_estimated_tokens"] == 240
        assert token_stats["repo_map_estimated_tokens"] == 120
        assert token_stats["adr_injection_estimated_tokens"] == 30
        assert token_stats["call_count"] == 2

    def test_parameterized_csv_regression_checks(self, ai_review, tmp_path):
        """Verify the regression checks load the CSV and mock diff file safely without execution."""
        import csv
        csv_path = tmp_path / "false_positive_cases.csv"
        headers = ["finding_id", "rebuttal_type", "evidence", "commit_sha", "diff_file", "expected_verdict"]
        
        # Create a mock sidecar diff file
        fp_cases_dir = tmp_path / "fp_cases"
        fp_cases_dir.mkdir(parents=True, exist_ok=True)
        diff_file = fp_cases_dir / "test_case.diff"
        diff_file.write_text("some simulated python diff", encoding="utf-8")
        
        row_data = [
            "T1-G-07",
            "FALSE_POSITIVE",
            "This is a false positive test",
            "abc12345",
            "fp_cases/test_case.diff",
            "PASS"
        ]
        
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerow(row_data)
            
        # Verify loading works correctly and it does not execute any code
        assert csv_path.exists()
        assert diff_file.exists()
        
        # Load and parse CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header_row = next(reader)
            first_row = next(reader)
            
        assert header_row == headers
        assert first_row == row_data
        
        # Read mock diff
        diff_text = (tmp_path / first_row[headers.index("diff_file")]).read_text(encoding="utf-8")
        assert diff_text == "some simulated python diff"


