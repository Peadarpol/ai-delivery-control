"""
Unit Tests for check_spec.py — Specification Quality Gate checks.
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_ROOT / ".agent" / "scripts"))

# Safely import the module under test
import importlib.util
spec = importlib.util.spec_from_file_location("check_spec", WORKSPACE_ROOT / ".agent" / "scripts" / "check_spec.py")
check_spec = importlib.util.module_from_spec(spec)
sys.modules["check_spec"] = check_spec
spec.loader.exec_module(check_spec)


@pytest.fixture
def base_spec_content():
    return """# Specification: SPEC-001 — Test Feature

**Source Issue**: https://github.com/owner/repo/issues/42
**Date**: 2026-05-30
**Author**: Human Architect

---

## 1. Goal & Context
This is a test goal and context section.

---

## 2. Bounded Scope & Out of Scope
### In Scope
- Core logic

### Out of Scope
- Mobile support

---

## 3. Assumptions
- [Resolved: existing middleware] Auth handled.
- [Resolved: declared out of scope] Offline mode.

---

## 4. Acceptance Criteria (BDD / Gherkin format)
Scenario: Successful login
  Given the user is on the login page
  When they enter valid credentials
  Then they should be redirected to the dashboard

---

## 5. Architectural Constraints
None.

---

## 6. Decisions (ADRs referenced)
None.

---

## 7. Status & Sign-off
**Status**: APPROVED
**Signed-off by**: Architect
"""


# ── Pass 1 Structural Checks ──────────────────────────────────────────────────

class TestPass1Structural:
    def test_golden_path_passes(self, base_spec_content):
        ok, errors, high_risk = check_spec.run_pass1(base_spec_content, "SPEC-001")
        assert ok is True
        assert len(errors) == 0
        assert high_risk is False

    def test_missing_sections_fails(self, base_spec_content):
        # Remove Goal & Context section
        bad_content = base_spec_content.replace("## 1. Goal & Context", "## 1. Vague Header")
        ok, errors, _ = check_spec.run_pass1(bad_content, "SPEC-001")
        assert ok is False
        assert any("Goal & Context" in err for err in errors)

    def test_empty_source_issue_fails(self, base_spec_content):
        bad_content = base_spec_content.replace("https://github.com/owner/repo/issues/42", "[Placeholder URL]")
        ok, errors, _ = check_spec.run_pass1(bad_content, "SPEC-001")
        assert ok is False
        assert any("issue reference" in err.lower() for err in errors)

    def test_missing_gherkin_keywords_fails(self, base_spec_content):
        # Remove 'Then' keyword
        bad_content = base_spec_content.replace("Then they should be redirected", "And they should be redirected")
        ok, errors, _ = check_spec.run_pass1(bad_content, "SPEC-001")
        assert ok is False
        assert any("Gherkin validation" in err or "missing: Then" in err for err in errors)

    def test_strict_word_boundary_gherkin_matching(self, base_spec_content):
        # Use a word containing 'then' (e.g. authenticathenticate) but no actual 'Then' keyword
        bad_content = base_spec_content.replace("Then they should be redirected", "And authenticathenticate they should be redirected")
        ok, errors, _ = check_spec.run_pass1(bad_content, "SPEC-001")
        assert ok is False
        assert any("Gherkin validation" in err or "missing: Then" in err for err in errors)

    def test_lenient_assumptions_checks(self, base_spec_content):
        # Bullets without resolution prefix fail
        bad_content = base_spec_content.replace("- [Resolved: existing middleware] Auth handled.", "- Vague assumption bullet")
        ok, errors, _ = check_spec.run_pass1(bad_content, "SPEC-001")
        assert ok is False
        assert any("lenient assumptions check" in err.lower() for err in errors)

    def test_lenient_assumptions_ignores_blank_lines(self, base_spec_content):
        # Assumptions with blank lines or plain introductory paragraph (non-bullets) passes
        content_with_notes = base_spec_content.replace("## 3. Assumptions", "## 3. Assumptions\n\nSome introductory note here.\n\n")
        ok, errors, _ = check_spec.run_pass1(content_with_notes, "SPEC-001")
        assert ok is True

    def test_pending_assumptions_block_approval(self, base_spec_content):
        bad_content = base_spec_content.replace("[Resolved: existing middleware]", "[Pending: needs discussion]")
        ok, errors, _ = check_spec.run_pass1(bad_content, "SPEC-001")
        assert ok is False
        assert any("pending" in err.lower() for err in errors)

    def test_elevated_dba_risk_tag(self, base_spec_content):
        bad_content = base_spec_content.replace("## 5. Architectural Constraints\nNone.", "## 5. Architectural Constraints\n- [HIGH_RISK_SCHEMA_CHANGE] Proposed schema change.")
        ok, errors, high_risk = check_spec.run_pass1(bad_content, "SPEC-001")
        assert ok is True
        assert high_risk is True


# ── Draft Warning Bypasses ────────────────────────────────────────────────────

class TestDraftWarningBypass:
    def test_draft_passes_locally_with_warning(self, base_spec_content):
        draft_content = base_spec_content.replace("APPROVED", "DRAFT")
        with patch.dict(os.environ, {"PRE_COMMIT": "0"}):
            ok, errors, _ = check_spec.run_pass1(draft_content, "SPEC-001")
            # Local DRAFT bypass allowed
            assert ok is True
            assert len(errors) == 0

    def test_draft_blocked_during_commit(self, base_spec_content):
        draft_content = base_spec_content.replace("APPROVED", "DRAFT")
        with patch.dict(os.environ, {"PRE_COMMIT": "1"}):
            ok, errors, _ = check_spec.run_pass1(draft_content, "SPEC-001")
            # Committing DRAFT blocks
            assert ok is False
            assert any("APPROVED" in err for err in errors)


# ── Pass 2 Quality Checks (LLM Gate) ──────────────────────────────────────────

class TestPass2QualityGate:
    @patch("providers.get_provider")
    def test_pass2_verdict_pass(self, mock_get_provider, base_spec_content, tmp_path):
        mock_provider = MagicMock()
        mock_provider.call_llm.return_value = (
            '{"verdict": "PASS", "clarity_score": 9, "testable_criteria": true, "sharp_boundaries": true, "resolved_assumptions": true}',
            100, 20
        )
        mock_get_provider.return_value = mock_provider
        
        config = {"budget_provider": "anthropic", "budget_model": "claude-haiku"}
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-testkey"}), \
             patch("check_spec.SESSION_FILE", tmp_path / "session.json"), \
             patch("check_spec.log_harness_event"):
             
            exit_code, verdict = check_spec.run_pass2(base_spec_content, "SPEC-001", False, config)
            assert exit_code == 0
            assert verdict.verdict == "PASS"
            assert verdict.clarity_score == 9

    @patch("providers.get_provider")
    def test_pass2_verdict_fail(self, mock_get_provider, base_spec_content, tmp_path):
        mock_provider = MagicMock()
        mock_provider.call_llm.return_value = (
            '{"verdict": "FAIL", "clarity_score": 3, "testable_criteria": false, "sharp_boundaries": false, "resolved_assumptions": false, "blocking_concerns": ["Ambiguous Gherkin steps"]}',
            100, 20
        )
        mock_get_provider.return_value = mock_provider
        
        config = {"budget_provider": "anthropic", "budget_model": "claude-haiku"}
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-testkey"}), \
             patch("check_spec.SESSION_FILE", tmp_path / "session.json"), \
             patch("check_spec.log_harness_event"):
             
            exit_code, verdict = check_spec.run_pass2(base_spec_content, "SPEC-001", False, config)
            assert exit_code == 1
            assert verdict.verdict == "FAIL"
            assert "Ambiguous Gherkin steps" in verdict.blocking_concerns


# ── Configuration vs Availability Failure partitioning ─────────────────────────

class TestConfigVsAvailabilityFailures:
    @patch("providers.get_provider")
    def test_pass2_fail_open_on_network_timeout(self, mock_get_provider, base_spec_content, tmp_path):
        """TimeoutError or ConnectionError are availability failures -> degrade, exit 0."""
        mock_get_provider.side_effect = TimeoutError("Anthropic API request timed out")
        config = {"budget_provider": "anthropic", "budget_model": "claude-haiku"}
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-testkey"}), \
             patch("check_spec.SESSION_FILE", tmp_path / "session.json"):
             
            exit_code, verdict = check_spec.run_pass2(base_spec_content, "SPEC-001", False, config)
            # Fail-open!
            assert exit_code == 0
            assert verdict is None

    @patch("providers.get_provider")
    def test_pass2_fail_closed_on_auth_neglect(self, mock_get_provider, base_spec_content, tmp_path):
        """Authentication key errors or 401/403 are configuration failures -> fail-closed, exit 1."""
        mock_get_provider.side_effect = ValueError("Authentication failed: invalid api key (401)")
        config = {"budget_provider": "anthropic", "budget_model": "claude-haiku"}
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-testkey"}), \
             patch("check_spec.SESSION_FILE", tmp_path / "session.json"):
             
            exit_code, verdict = check_spec.run_pass2(base_spec_content, "SPEC-001", False, config)
            # Fail-closed!
            assert exit_code == 1
            assert verdict is None

    def test_pass2_fail_closed_on_missing_cloud_keys(self, base_spec_content, tmp_path):
        """Missing credentials for cloud model -> configuration failure, exit 1."""
        config = {"budget_provider": "anthropic", "budget_model": "claude-haiku"}
        
        with patch.dict(os.environ, {}, clear=True), \
             patch("check_spec.SESSION_FILE", tmp_path / "session.json"):
             
            exit_code, verdict = check_spec.run_pass2(base_spec_content, "SPEC-001", False, config)
            # Fail-closed due to configuration neglect!
            assert exit_code == 1
            assert verdict is None


# ── Conditional CI Skipping ───────────────────────────────────────────────────

class TestConditionalCISkip:
    def test_skip_ci_on_local_model(self, base_spec_content, tmp_path):
        """If CI and model is local Ollama -> skip Pass 2 gracefully."""
        config = {"budget_provider": "ollama", "budget_model": "gemma2"}
        
        with patch.dict(os.environ, {"CI": "1"}), \
             patch("check_spec.SESSION_FILE", tmp_path / "session.json"):
             
            exit_code, verdict = check_spec.run_pass2(base_spec_content, "SPEC-001", False, config)
            assert exit_code == 0
            assert verdict is None

    @patch("providers.get_provider")
    def test_run_ci_on_cloud_keys_present(self, mock_get_provider, base_spec_content, tmp_path):
        """If CI and cloud provider model with active keys -> run Pass 2 normally."""
        mock_provider = MagicMock()
        mock_provider.call_llm.return_value = ('{"verdict": "PASS", "clarity_score": 8, "testable_criteria": true, "sharp_boundaries": true, "resolved_assumptions": true}', 100, 20)
        mock_get_provider.return_value = mock_provider
        
        config = {"budget_provider": "anthropic", "budget_model": "claude-haiku"}
        
        with patch.dict(os.environ, {"CI": "1", "ANTHROPIC_API_KEY": "sk-ant-testkey"}), \
             patch("check_spec.SESSION_FILE", tmp_path / "session.json"), \
             patch("check_spec.log_harness_event"):
             
            exit_code, verdict = check_spec.run_pass2(base_spec_content, "SPEC-001", False, config)
            # Normal execution!
            assert exit_code == 0
            assert verdict is not None
            assert verdict.verdict == "PASS"


# ── Bypass Safety ─────────────────────────────────────────────────────────────

class TestBypassSafety:
    def test_bypass_fails_without_reason(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch("sys.argv", ["check_spec.py", "--skip-spec-gate"]):
            exit_code = check_spec.main()
            assert exit_code == 1

    def test_bypass_fails_with_short_reason(self):
        with patch.dict(os.environ, {"SKIP_REASON": "short"}), \
             patch("sys.argv", ["check_spec.py", "--skip-spec-gate"]):
            exit_code = check_spec.main()
            assert exit_code == 1

    def test_bypass_succeeds_with_valid_reason(self, tmp_path):
        with patch.dict(os.environ, {"SKIP_REASON": "Valid long explanation of the bypass reason"}), \
             patch("sys.argv", ["check_spec.py", "--skip-spec-gate"]), \
             patch("check_spec.log_harness_event") as mock_log:
            exit_code = check_spec.main()
            assert exit_code == 0
            assert mock_log.called
