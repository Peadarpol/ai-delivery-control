# Multi-Persona Adversarial Review Report: SPEC-v1.4.10-governance-hardening

**Target Artifact**: [SPEC-v1.4.10-governance-hardening.md](file:///c:/projects/ai-delivery-control/docs/planning/specs/SPEC-v1.4.10-governance-hardening.md)  
**Review Date**: 2026-07-20  
**Reviewing Personas**:
1. 🛡️ **Senior Security & Governance Architect**
2. ⚙️ **Developer Ergonomics & Systems Engineer**
3. 🧪 **QA & Verification Engineer**
4. 📋 **Release & Product Manager**

---

## Executive Summary

[SPEC-v1.4.10-governance-hardening.md](file:///c:/projects/ai-delivery-control/docs/planning/specs/SPEC-v1.4.10-governance-hardening.md) is structurally sound, highly thorough, and successfully reconciles the 11 assigned technical tickets. However, this multi-persona adversarial review uncovered **1 Critical Architecture Defect**, **2 Security Edge Cases**, and **2 Operational Risk Items** that require resolution before the spec is marked `APPROVED`.

---

## 1. 🛡️ Senior Security & Governance Architect Review

### Finding S1 (CRITICAL): Untracked `session.json` breaks `git show <commit>:.agent/session.json` lookup
* **Location**: Section 5, Component: Requirement Traceability (`T1-K-13 Merge-Gate --no-trace Aggregator`, line 156).
* **Defect**: The spec states: *"For each match, pull the attribution block from that commit's session.json in history (`git show <commit>:.agent/session.json`) to extract `signed_by` and `session_id`."*
* **Security & Execution Flaw**: `.agent/state/session.json` is **untracked in git** (governed by `.gitignore` under operational state). Executing `git show <commit>:.agent/session.json` on past commits will fail with `fatal: path '.agent/session.json' does not exist in '<commit>'`.
* **Remediation**:
  Attribution metadata MUST be resolved using one of two valid channels:
  1. Parse the `session_id` from the commit message trailer (`Session-Id: <uuid>`) or search `.agent/state/session_ledger.jsonl` / `session_ledger.md` by commit SHA.
  2. Embed `Signed-off-by` / `Session-Id` as standard Git commit trailers at commit creation time.

### Finding S2 (MEDIUM): Non-Interactive Signature Inheritance Vulnerability
* **Location**: Section 5, Component: Requirement Traceability (`init_session.py`, line 146).
* **Defect**: The spec notes: *"On non-interactive session start... inherit it from a parent session if one exists (never fabricate a signer)."*
* **Security Risk**: If an autonomous subagent or prompt-injected script executes in a non-interactive background turn while a parent interactive session signed by a human operator exists, the autonomous step silently inherits human signature credentials.
* **Remediation**:
  The `authorization` block written to `session.json` MUST explicitly record `"is_interactive": false` when inherited. The merge aggregator MUST flag non-interactive inherited signatures separately during `--ack-no-trace` review.

### Finding S3 (MEDIUM): Empty High-Risk Patterns Array Bypass (`T1-L-21`)
* **Location**: Section 5, Component: Governance & Risk (`route_decision.py`, line 97).
* **Defect**: Setting `override_defaults: true` with `high_risk_patterns: []` winks out all default risk pattern checks.
* **Remediation**:
  If `override_defaults: true` and `high_risk_patterns` is empty, `route_decision.py` MUST emit a `CRITICAL_WARNING` to `stderr` and default to `elevated` review mode rather than running unshielded.

---

## 2. ⚙️ Developer Ergonomics & Systems Engineer Review

### Finding E1 (MEDIUM): Stash Accumulation vs Non-Interactive Dirty Tree (`HIB-ENV-02`)
* **Location**: Section 5, Component: Session Lifecycle (`init_session.py`, line 179).
* **Defect**: In non-interactive mode, `init_session.py` skips stashing to avoid destroying uncommitted state. However, if a previous session failed dirty, subsequent automated session starts inherit the dirty state without notice.
* **Remediation**:
  Non-interactive runs MUST execute `git stash push -m "AUTO: session-start checkpoint [session_id]"` (preserving working tree state or taking an explicit stash checkpoint) and log the active dirty file list in `session.json`.

### Finding E2 (LOW): Fallback YAML Parser Specification (`T1-E-04`)
* **Location**: Section 5, Component: Configuration Loading (`harness_utils.py`, line 116).
* **Defect**: The spec specifies block scalar support (`|`, `>`), but does not define behavior for boolean alias normalization (`yes`/`no` vs `true`/`false`).
* **Remediation**:
  Explicitly state in the spec that the fallback parser normalizes YAML 1.1 booleans (`yes`/`no`/`true`/`false`/`on`/`off`) to Python `bool`, and falls back safely to `DEFAULTS` on parse errors.

---

## 3. 🧪 QA & Verification Engineer Review

### Finding V1 (HIGH): Lack of Mocking Isolation Strategy for PyYAML Fallback Tests (`T1-E-04`)
* **Location**: Section 7, Additional Verification Test Coverage (line 207).
* **Defect**: Monkeypatching `sys.modules["yaml"] = None` in a pytest runner where PyYAML is already imported globally across other test modules can cause collateral failures in non-isolated test runs.
* **Remediation**:
  Specify that `test_config_loader.py` uses `importlib.reload(harness_utils)` inside a isolated `unittest.mock.patch.dict(sys.modules, {"yaml": None})` context manager, restoring module state cleanly upon teardown.

### Finding V2 (MEDIUM): Gherkin Scenario Step Ambiguity
* **Location**: Section 4, Scenario 6 (`Merge-gate --no-trace aggregator`, line 73).
* **Defect**: The scenario specifies `"When the pre-merge gate check fires"`, but doesn't state *which* git hook triggers it (`pre-commit` via `.git/MERGE_HEAD` vs `pre-push`).
* **Remediation**:
  Clarify in Scenario 6: *"When the pre-commit hook fires during `git merge` (evaluating `.git/MERGE_HEAD`) or pre-push stage..."*

---

## 4. 📋 Release & Product Manager Review

### Finding P1 (MEDIUM): `upgrade.py` Deployment Path for `check_exception_standards.py`
* **Location**: Section 5, Component: Gate Diagnostics (line 171).
* **Defect**: The new wrapper script `check_exception_standards.py` must be deployed to existing target projects during `bootstrap/upgrade.py`.
* **Remediation**:
  Add `[MODIFY] bootstrap/upgrade.py` to Section 5, ensuring `copy_framework_files()` installs `.agent/scripts/check_exception_standards.py` during project upgrades.

---

## Consensus & Recommendation Matrix

| ID | Persona | Severity | Target Section | Recommended Action |
|---|---|---|---|---|
| **S1** | Security Architect | **CRITICAL** | Section 5 (`T1-K-13`) | Fix git lookup channel (use commit trailers / ledger instead of `git show <sha>:.agent/session.json`). |
| **S2** | Security Architect | **MEDIUM** | Section 5 (`init_session.py`) | Tag inherited non-interactive session signatures with `is_interactive: false`. |
| **S3** | Security Architect | **MEDIUM** | Section 5 (`route_decision.py`) | Fail-closed to elevated review if `override_defaults: true` and pattern array is empty. |
| **E1** | Systems Engineer | **MEDIUM** | Section 5 (`init_session.py`) | Log dirty file manifest in `session.json` on non-interactive session start. |
| **E2** | Systems Engineer | **LOW** | Section 5 (`harness_utils.py`) | Define YAML 1.1 boolean normalization for fallback parser. |
| **V1** | QA Engineer | **HIGH** | Section 7 (`test_config_loader.py`)| Specify `importlib.reload` teardown context for PyYAML monkeypatch test. |
| **V2** | QA Engineer | **MEDIUM** | Section 4 (Scenario 6) | Disambiguate git trigger stage (`.git/MERGE_HEAD` / `pre-commit`). |
| **P1** | Product Manager | **MEDIUM** | Section 5 (`upgrade.py`) | Add `bootstrap/upgrade.py` to installer/upgrade manifest for new script distribution. |

---
