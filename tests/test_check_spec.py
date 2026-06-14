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
        result = check_spec.run_pass1(base_spec_content, "SPEC-001")

        ok = result.passed

        errors = result.errors

        high_risk = result.high_risk_dba
        assert ok is True
        assert len(errors) == 0
        assert high_risk is False

    def test_missing_sections_fails(self, base_spec_content):
        # Remove Goal & Context section
        bad_content = base_spec_content.replace("## 1. Goal & Context", "## 1. Vague Header")
        result = check_spec.run_pass1(bad_content, "SPEC-001")

        ok = result.passed

        errors = result.errors

        _ = result.high_risk_dba
        assert ok is False
        assert any("Goal & Context" in err for err in errors)

    def test_empty_source_issue_fails(self, base_spec_content):
        bad_content = base_spec_content.replace("https://github.com/owner/repo/issues/42", "[Placeholder URL]")
        result = check_spec.run_pass1(bad_content, "SPEC-001")

        ok = result.passed

        errors = result.errors

        _ = result.high_risk_dba
        assert ok is False
        assert any("issue reference" in err.lower() for err in errors)

    def test_missing_gherkin_keywords_fails(self, base_spec_content):
        # Remove 'Then' keyword
        bad_content = base_spec_content.replace("Then they should be redirected", "And they should be redirected")
        result = check_spec.run_pass1(bad_content, "SPEC-001")

        ok = result.passed

        errors = result.errors

        _ = result.high_risk_dba
        assert ok is False
        assert any("Gherkin validation" in err or "missing: Then" in err for err in errors)

    def test_strict_word_boundary_gherkin_matching(self, base_spec_content):
        # Use a word containing 'then' (e.g. authenticathenticate) but no actual 'Then' keyword
        bad_content = base_spec_content.replace("Then they should be redirected", "And authenticathenticate they should be redirected")
        result = check_spec.run_pass1(bad_content, "SPEC-001")

        ok = result.passed

        errors = result.errors

        _ = result.high_risk_dba
        assert ok is False
        assert any("Gherkin validation" in err or "missing: Then" in err for err in errors)

    def test_lenient_assumptions_checks(self, base_spec_content):
        # Bullets without resolution prefix fail
        bad_content = base_spec_content.replace("- [Resolved: existing middleware] Auth handled.", "- Vague assumption bullet")
        result = check_spec.run_pass1(bad_content, "SPEC-001")

        ok = result.passed

        errors = result.errors

        _ = result.high_risk_dba
        assert ok is False
        assert any("lenient assumptions check" in err.lower() for err in errors)

    def test_lenient_assumptions_ignores_blank_lines(self, base_spec_content):
        # Assumptions with blank lines or plain introductory paragraph (non-bullets) passes
        content_with_notes = base_spec_content.replace("## 3. Assumptions", "## 3. Assumptions\n\nSome introductory note here.\n\n")
        result = check_spec.run_pass1(content_with_notes, "SPEC-001")

        ok = result.passed

        errors = result.errors

        _ = result.high_risk_dba
        assert ok is True

    def test_pending_assumptions_block_approval(self, base_spec_content):
        bad_content = base_spec_content.replace("[Resolved: existing middleware]", "[Pending: needs discussion]")
        result = check_spec.run_pass1(bad_content, "SPEC-001")

        ok = result.passed

        errors = result.errors

        _ = result.high_risk_dba
        assert ok is False
        assert any("pending" in err.lower() for err in errors)

    def test_elevated_dba_risk_tag(self, base_spec_content):
        bad_content = base_spec_content.replace("## 5. Architectural Constraints\nNone.", "## 5. Architectural Constraints\n- [HIGH_RISK_SCHEMA_CHANGE] Proposed schema change.")
        result = check_spec.run_pass1(bad_content, "SPEC-001")

        ok = result.passed

        errors = result.errors

        high_risk = result.high_risk_dba
        assert ok is True
        assert high_risk is True


# ── Draft Warning Bypasses ────────────────────────────────────────────────────

class TestDraftWarningBypass:
    def test_draft_passes_locally_with_warning(self, base_spec_content):
        draft_content = base_spec_content.replace("APPROVED", "DRAFT")
        with patch.dict(os.environ, {"PRE_COMMIT": "0"}):
            result = check_spec.run_pass1(draft_content, "SPEC-001")

            ok = result.passed

            errors = result.errors

            _ = result.high_risk_dba
            # Local DRAFT bypass allowed
            assert ok is True
            assert len(errors) == 0

    def test_draft_blocked_during_commit(self, base_spec_content):
        draft_content = base_spec_content.replace("APPROVED", "DRAFT")
        with patch.dict(os.environ, {"PRE_COMMIT": "1"}):
            result = check_spec.run_pass1(draft_content, "SPEC-001")

            ok = result.passed

            errors = result.errors

            _ = result.high_risk_dba
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


    @patch("providers.get_provider")
    def test_pass2_malformed_json_degrades_cleanly(self, mock_get_provider, base_spec_content, tmp_path):
        mock_provider = MagicMock()
        # Return valid JSON but missing required Pydantic fields to trigger fallback
        mock_provider.call_llm.return_value = (
            '{"clarity_score": 9}',
            100, 20
        )
        mock_get_provider.return_value = mock_provider
        
        config = {"budget_provider": "anthropic", "budget_model": "claude-haiku"}
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-testkey"}), \
             patch("check_spec.SESSION_FILE", tmp_path / "session.json"), \
             patch("check_spec.PROJECT_ROOT", tmp_path), \
             patch("check_spec.log_harness_event") as mock_log:
             
            exit_code, verdict = check_spec.run_pass2(base_spec_content, "SPEC-001", False, config)
            assert exit_code == 0
            assert verdict.verdict == "ADVISORY"
            assert "Per-criterion feedback unavailable" in verdict.advisories[0]
            
            # Assert pass2_parse_failure event was logged
            mock_log.assert_any_call({
                "event_type": "pass2_parse_failure",
                "severity": "WARNING",
                "payload": {
                    "spec_id": "SPEC-001",
                    "reason": "Pass 2 response malformed; fell back to top-level verdict"
                }
            })
            
            # Assert spec_grade card was written
            grade_card = tmp_path / ".agent" / "state" / "spec_grade_SPEC-001.md"
            assert grade_card.exists()
            assert "Spec Grade Card: SPEC-001" in grade_card.read_text("utf-8")

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


# ── T1-L-00: Outer Loop Methodology Mode ─────────────────────────────────────


class TestOuterLoopMode:
    """T1-L-00 — mode-conditional Pass 1 and contractual bypass rejection."""

    def test_discovery_mode_downgrades_block_to_warn(self, base_spec_content):
        """Missing heading in discovery mode → exit 0 (advisory only)."""
        bad = base_spec_content.replace("## 1. Goal & Context", "## 1. Vague Header")
        result = check_spec.run_pass1(bad, "SPEC-001", mode="discovery")

        ok = result.passed

        errors = result.errors

        _ = result.high_risk_dba
        assert ok is True, "Discovery mode must never block on structural checks"
        assert errors == [], "No errors should accumulate in discovery mode"

    def test_incremental_mode_blocks_missing_heading(self, base_spec_content):
        """Missing heading in incremental mode → exit 1 (existing behaviour unchanged)."""
        bad = base_spec_content.replace("## 1. Goal & Context", "## 1. Vague Header")
        result = check_spec.run_pass1(bad, "SPEC-001", mode="incremental")

        ok = result.passed

        errors = result.errors

        _ = result.high_risk_dba
        assert ok is False
        assert any("Goal & Context" in e for e in errors)

    def test_discovery_mode_skips_gherkin_requirement(self, base_spec_content):
        """Missing Gherkin keywords in discovery mode → advisory, not a block."""
        bad = base_spec_content.replace("Then they should be redirected", "And they should proceed")
        result = check_spec.run_pass1(bad, "SPEC-001", mode="discovery")

        ok = result.passed

        errors = result.errors

        _ = result.high_risk_dba
        assert ok is True
        assert errors == []

    def test_contractual_mode_blocks_draft_locally(self, base_spec_content):
        """DRAFT status in local (non-CI) mode blocks in contractual — no local bypass."""
        draft = base_spec_content.replace("**Status**: APPROVED", "**Status**: DRAFT")
        with patch.dict(os.environ, {"PRE_COMMIT": "0", "CI": "0"}, clear=False):
            result = check_spec.run_pass1(draft, "SPEC-001", mode="contractual")

            ok = result.passed

            errors = result.errors

            _ = result.high_risk_dba
        assert ok is False
        assert any("APPROVED" in e for e in errors)

    def test_contractual_mode_rejects_skip_flag(self):
        """--skip-spec-gate in contractual mode → exit 1 with explanation."""
        with patch("sys.argv", ["check_spec.py", "--mode-override", "contractual",
                                "--skip-spec-gate"]):
            exit_code = check_spec.main()
        assert exit_code == 1

    def test_contractual_mode_blocks_pending_assumption(self, base_spec_content):
        """[Pending] assumption in contractual mode → exit 1 (no local bypass)."""
        pending = base_spec_content.replace(
            "- [Resolved: existing middleware] Auth handled.",
            "- [Pending: needs discussion] Auth approach unclear.",
        )
        with patch.dict(os.environ, {"PRE_COMMIT": "0", "CI": "0"}, clear=False):
            result = check_spec.run_pass1(pending, "SPEC-001", mode="contractual")

            ok = result.passed

            errors = result.errors

            _ = result.high_risk_dba
        assert ok is False
        assert any("pending" in e.lower() for e in errors)

    def test_mode_displayed_in_output(self, base_spec_content, tmp_path, capsys):
        """Any mode → header line contains 'mode: {mode}'."""
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True)
        spec_file = specs_dir / "SPEC-001.md"
        spec_file.write_text(base_spec_content, encoding="utf-8")

        with patch("sys.argv", ["check_spec.py", "--mode-override", "discovery", "SPEC-001"]), \
             patch.object(check_spec, "PROJECT_ROOT", tmp_path), \
             patch("check_spec.run_pass2", return_value=(0, None)):
            check_spec.main()

        captured = capsys.readouterr().out
        assert "mode: discovery" in captured


# ── T1-L-00: Spec ID Resolution Hardening ─────────────────────────────────────


class TestSpecIdResolution:
    """T1-L-00 — 5-step spec ID resolution including active_context.md."""

    def test_spec_id_from_active_context(self, tmp_path):
        """active_context.md containing SPEC-042 → resolved as SPEC-042."""
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "SPEC-042.md").write_text("# Spec 042", encoding="utf-8")

        state_dir = tmp_path / ".agent" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "active_context.md").write_text(
            "## Current Task\nWorking on SPEC-042 feature.\n", encoding="utf-8"
        )

        with patch.object(check_spec, "PROJECT_ROOT", tmp_path), \
             patch.dict(os.environ, {}, clear=True), \
             patch("check_spec.get_active_branch_spec", return_value=None):
            result = check_spec.resolve_spec_file(None, "docs/planning/specs/")

        assert result is not None
        spec_id, spec_path = result
        assert spec_id == "SPEC-042"

    def test_active_context_missing_falls_through(self, tmp_path):
        """No active_context.md → resolution falls through to next step."""
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "SPEC-005.md").write_text("# Spec 005", encoding="utf-8")

        # No active_context.md, no env var, no branch match → single-file scan
        with patch.object(check_spec, "PROJECT_ROOT", tmp_path), \
             patch.dict(os.environ, {}, clear=True), \
             patch("check_spec.get_active_branch_spec", return_value=None):
            result = check_spec.resolve_spec_file(None, "docs/planning/specs/")

        # Should fall through to single-file scan and find SPEC-005
        assert result is not None
        assert result[0] == "SPEC-005"

    def test_multiple_specs_no_env_exits_with_error(self, tmp_path, capsys):
        """Multiple spec files, no env var, no branch → exit 1 with list of specs."""
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "SPEC-001.md").write_text("# Spec 001", encoding="utf-8")
        (specs_dir / "SPEC-002.md").write_text("# Spec 002", encoding="utf-8")

        with patch.object(check_spec, "PROJECT_ROOT", tmp_path), \
             patch.dict(os.environ, {}, clear=True), \
             patch("check_spec.get_active_branch_spec", return_value=None), \
             patch("check_spec.get_spec_from_active_context", return_value=None):
            result = check_spec.resolve_spec_file(None, "docs/planning/specs/")

        assert result is None
        captured = capsys.readouterr().err
        assert "Multiple spec files found" in captured
        assert "SPEC-001.md" in captured
        assert "SPEC-002.md" in captured


class TestSpecCollisionCheck:
    def test_collision_detected(self, tmp_path):
        """Verify collision is detected if keyword overlap >= threshold."""
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True)
        
        # Spec A (Target)
        spec_a = specs_dir / "SPEC-001.md"
        spec_a.write_text("""# Spec 001
status: APPROVED
## Acceptance Criteria
Scenario: user login
  Given they enter username and password credentials
  Then dashboard is displayed
""", encoding="utf-8")
        
        # Spec B (Collision)
        spec_b = specs_dir / "SPEC-002.md"
        spec_b.write_text("""# Spec 002
status: APPROVED
## Acceptance Criteria
Scenario: admin login
  Given they enter admin username and password credentials
  Then dashboard is displayed
""", encoding="utf-8")
        
        collisions = check_spec._check_spec_collision("SPEC-001", spec_a, specs_dir, threshold=0.4)
        assert len(collisions) == 1
        assert collisions[0][0] == "SPEC-002"
        # Overlap score should be >= 0.4
        assert collisions[0][1] >= 0.4

    def test_no_collision_detected(self, tmp_path):
        """Verify no collision if overlap < threshold."""
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True)
        
        spec_a = specs_dir / "SPEC-001.md"
        spec_a.write_text("""# Spec 001
status: APPROVED
## Acceptance Criteria
Scenario: user login
  Given they enter username and password credentials
""", encoding="utf-8")
        
        spec_b = specs_dir / "SPEC-002.md"
        spec_b.write_text("""# Spec 002
status: APPROVED
## Acceptance Criteria
Scenario: billing invoice payment
  Given billing invoice is generated for customer service account
  Then payment status is paid
""", encoding="utf-8")
        
        collisions = check_spec._check_spec_collision("SPEC-001", spec_a, specs_dir, threshold=0.4)
        assert len(collisions) == 0

    def test_single_spec_no_other_specs(self, tmp_path):
        """Verify no collision if no other APPROVED/DRAFT specs exist."""
        specs_dir = tmp_path / "docs" / "planning" / "specs"
        specs_dir.mkdir(parents=True)
        
        spec_a = specs_dir / "SPEC-001.md"
        spec_a.write_text("""# Spec 001
status: APPROVED
## Acceptance Criteria
Scenario: user login
  Given they enter username and password credentials
""", encoding="utf-8")
        
        collisions = check_spec._check_spec_collision("SPEC-001", spec_a, specs_dir, threshold=0.4)
        assert len(collisions) == 0

