"""
Unit tests for check_spec.py (Pass 1 static structural checks & concept alias matching).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add .agent/scripts to path for importing check_spec
AGENT_SCRIPTS = Path(__file__).resolve().parent.parent.parent / ".agent" / "scripts"
if str(AGENT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(AGENT_SCRIPTS))

import check_spec


def test_pass1_nested_scenario_subheadings_not_treated_as_boundary():
    """Verify section-boundary depth tracking when a section contains nested subheadings.
    
    ## Acceptance Criteria followed by ### Scenario N subheadings must not cause
    section_contents['acceptance_criteria'] to be captured as empty.
    """
    fixture = """# Specification: SPEC-001 — Nested Subheading Test

**Source Issue**: https://github.com/Peadarpol/ai-delivery-control/issues/100

---

## 1. Goal & Context
Test goal and context.

---

## 2. Bounded Scope & Out of Scope
Scope details.

---

## 3. Assumptions
- [Resolved: test assumption] Auth handled by existing middleware.

---

## 4. Acceptance Criteria
### Scenario 1: First scenario
Given a valid user
When they log in
Then they see the dashboard

### Scenario 2: Second scenario
Given an invalid password
When they attempt login
Then an error message is displayed

### Scenario 3: Third scenario
Given a locked account
When they request reset
Then a reset token is generated

---

## 5. Status & Sign-off
**Status**: APPROVED
**Signed-off by**: Tester
**Sign-off Date**: 2026-07-20
"""

    res = check_spec.run_pass1(fixture, "SPEC-001", mode="incremental")
    assert res.passed is True, f"Expected Pass 1 to pass, but got errors: {res.errors}"
    assert len(res.errors) == 0


def test_pass1_default_aliases_match_actual_project_convention():
    """Verify Pass 1 passes against actual project spec conventions:
    **Status**: APPROVED and **Tracked under**: ... metadata lines without a dedicated ## Status & Sign-off section.
    """
    fixture = """# Specification: SPEC-v1.4.10-governance-hardening

**Status**: APPROVED
**Author**: Gemini (AI execution mode)
**Feeds into**: Release v1.4.10
**Tracked under**: T1-K-12 / T1-L-21 / T1-K-13

---

## 1. Goal & Context
Goal and context text.

---

## 2. Bounded Scope & Out of Scope
* **Bounded Scope**:
  - Feature A

---

## 3. Assumptions
* [Resolved: Git CLI usage] The developer uses Git CLI.

---

## 4. Acceptance Criteria
* **Given** a target project layout
* **When** config overrides are specified
* **Then** route decision uses customized config list
"""

    res = check_spec.run_pass1(fixture, "SPEC-v1.4.10", mode="incremental")
    assert res.passed is True, f"Expected actual project convention spec to pass, got errors: {res.errors}"


def test_pass1_legacy_convention_still_matches():
    """Verify Pass 1 passes against legacy convention (**Source Issue**: field, ## Status & Sign-off section)."""
    fixture = """# Specification: SPEC-002 — Legacy Style Test

**Source Issue**: https://github.com/Peadarpol/ai-delivery-control/issues/200

---

## Goal & Context
Context text.

---

## Bounded Scope & Out of Scope
Scope text.

---

## Assumptions
- [Resolved: assumption] Valid assumption.

---

## Acceptance Criteria
Given a condition
When an action occurs
Then an outcome happens

---

## Status & Sign-off
**Status**: APPROVED
**Signed-off by**: Architect
"""

    res = check_spec.run_pass1(fixture, "SPEC-002", mode="incremental")
    assert res.passed is True, f"Expected legacy style spec to pass, got errors: {res.errors}"


def test_pass1_custom_alias_override():
    """Verify custom section_aliases config overrides default aliases cleanly."""
    fixture = """# Specification: SPEC-003 — Custom Alias Test

**Upstream Ticket**: JIRA-9999

---

## Goal & Context
Context text.

---

## Bounded Scope & Out of Scope
Scope text.

---

## Assumptions
- [Resolved: assumption] Valid assumption.

---

## Acceptance Criteria
Given condition
When action
Then outcome

---

## Status
**Status**: APPROVED
"""

    custom_aliases = {
        "source": ["Upstream Ticket"],
        "scope": ["Bounded Scope & Out of Scope"],
        "assumptions": ["Assumptions"],
        "acceptance_criteria": ["Acceptance Criteria"],
        "status": ["Status"],
    }

    res = check_spec.run_pass1(fixture, "SPEC-003", mode="incremental", section_aliases=custom_aliases)
    assert res.passed is True, f"Expected custom alias spec to pass, got errors: {res.errors}"


def test_pass1_missing_concept_reports_all_tried_aliases():
    """Verify missing concept error message lists all attempted aliases."""
    fixture = """# Specification: SPEC-004 — Missing Status Test

**Source Issue**: https://github.com/Peadarpol/ai-delivery-control/issues/400

---

## Goal & Context
Context.

---

## Bounded Scope & Out of Scope
Scope.

---

## Assumptions
- [Resolved: assumption] Test.

---

## Acceptance Criteria
Given precondition
When trigger
Then result
"""

    res = check_spec.run_pass1(fixture, "SPEC-004", mode="incremental")
    assert res.passed is False
    assert any("Status & Sign-off, Status" in err for err in res.errors), f"Errors should report tried aliases: {res.errors}"


def test_pass1_assumptions_and_gherkin_checks_regression():
    """Verify Gherkin keyword and assumptions formatting checks trigger correctly on failures."""
    invalid_assumptions_fixture = """# Specification: SPEC-005 — Invalid Assumptions Test

**Source Issue**: https://github.com/Peadarpol/ai-delivery-control/issues/500

---

## Goal & Context
Context.

---

## Bounded Scope & Out of Scope
Scope.

---

## Assumptions
- Floating assumption without prefix.

---

## Acceptance Criteria
Given precondition
When trigger
Then result

---

## Status
**Status**: APPROVED
"""

    res = check_spec.run_pass1(invalid_assumptions_fixture, "SPEC-005", mode="incremental")
    assert res.passed is False
    assert any("Lenient assumptions check failed" in err for err in res.errors)

    missing_gherkin_fixture = """# Specification: SPEC-006 — Missing Gherkin Test

**Source Issue**: https://github.com/Peadarpol/ai-delivery-control/issues/600

---

## Goal & Context
Context.

---

## Bounded Scope & Out of Scope
Scope.

---

## Assumptions
- [Resolved: test] Valid.

---

## Acceptance Criteria
This text is missing the Gherkin keywords.

---

## Status
**Status**: APPROVED
"""

    res2 = check_spec.run_pass1(missing_gherkin_fixture, "SPEC-006", mode="incremental")
    assert res2.passed is False
    assert any("BDD Gherkin validation failed" in err for err in res2.errors)


def test_pass1_smoke_all_three_specs():
    """Live smoke test against real spec files in the repository."""
    specs = [
        "docs/planning/specs/archive/SPEC-v1.4.10-governance-hardening.md",
        "docs/planning/specs/archive/SPEC-v1.4.9.1-first-commit-hotfix.md",
        "docs/planning/specs/archive/SPEC-v1.4.11-installer-onboarding.md",
    ]

    checked_count = 0
    for rel_path in specs:
        spec_path = Path(__file__).resolve().parent.parent.parent / rel_path
        if not spec_path.exists():
            continue
        content = spec_path.read_text(encoding="utf-8")
        res = check_spec.run_pass1(content, spec_path.name, mode="incremental")
        assert res.passed is True, f"Spec {rel_path} failed Pass 1: {res.errors}"
        checked_count += 1

    assert checked_count >= 3, f"Expected to check at least 3 spec files, but only checked {checked_count}"
