# Loop Closure Verification Report
**Run Timestamp**: 2026-08-05 10:32:59 UTC
**Status**: 🟢 FULL CORPUS VERIFICATION COMPLETED

## Summary
- **Total Spec Files Scanned**: 16
- **Legacy Specs Skipped (No Gherkin)**: 9
- **Total Scenarios Evaluated**: 106
- **✅ VERIFIED (Real Entry Point)**: 1
- **✅ VERIFIED (Mock Only)**: 1
- **❌ UNVERIFIED**: 53
- **⏭️ SKIPPED (Non-Code / Tags)**: 51

---

## Scenario 1b Calibration & Error Rate Audit
Per SPEC-loop-closure-verification A 5, the following 10 scenarios represent raw data for manual calibration. This is raw data for manual review, not a completed calibration. The FP/FN rate has not yet been computed.

| # | Spec File | Scenario ID & Title | Components | Mocked | Then-Overlap | Final Classification |
|---|---|---|---|---|---|---|
| 1 | [SPEC-enforcement-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-enforcement-postures.md) | Scenario 1: Posture Resolution and Fail-Safe Defaults | `config, YAML` | No | Yes | `UNVERIFIED` |
| 2 | [SPEC-v1.4.11-installer-onboarding.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.11-installer-onboarding.md) | Scenario 1: Installer blocks wrong target directory (F-COLD-1) | `` | No | No | `SKIPPED` |
| 3 | [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md) | Scenario 1: Posture Resolution and Fail-Safe Defaults (T1-G-18) | `config, YAML` | No | Yes | `UNVERIFIED` |
| 4 | [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md) | Scenario 1: Ratchet posture grandfathers pre-existing architecture_checks.py violations (HIB-080) | `enforcement.posture: ratchet, baseline, FAIL, LAYER_BOUNDARY, architecture_checks` | No | Yes | `UNVERIFIED` |
| 5 | [SPEC-v1.4.14-punchcard-preparation.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.14-punchcard-preparation.md) | Scenario 1: Oversized diffs are routed into review, not silently failed open (HIB-068) | `` | No | No | `SKIPPED` |
| 6 | [SPEC-v1.4.9.1-first-commit-hotfix.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.9.1-first-commit-hotfix.md) | Scenario 1: Onboarding on a bare pip project | `` | No | No | `SKIPPED` |
| 7 | [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md) | Scenario 1: Spec-scenario cross-reference detects an unimplemented outcome assertion (Phase A) | `APPROVED` | No | No | `UNVERIFIED` |
| 8 | [SPEC-enforcement-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-enforcement-postures.md) | Scenario 2: Baseline Grandfathering and File-Edit Lapsing in Ratchet Posture | `enforcement.posture: ratchet, baseline, git diff --name-only HEAD, git diff --name-only HEAD^1, depth=1, HEAD^1, SHALLOW_CLONE_LAPSE_SKIPPED, HEAD` | No | Yes | `UNVERIFIED` |
| 9 | [SPEC-v1.4.11-installer-onboarding.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.11-installer-onboarding.md) | Scenario 2: Onboarding validation fails on unreachable API key (F-COLD-3) | `` | No | No | `SKIPPED` |
| 10 | [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md) | Scenario 2: Baseline Grandfathering and File-Edit Lapsing in Ratchet Posture (T1-G-18) | `enforcement.posture: ratchet, baseline, git diff --name-only HEAD, git diff --name-only HEAD^1, depth=1, HEAD^1, SHALLOW_CLONE_LAPSE_SKIPPED, HEAD` | No | Yes | `UNVERIFIED` |

---

## ❌ UNVERIFIED Scenarios
### `Scenario 1` in [SPEC-enforcement-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-enforcement-postures.md)
- **Title**: Posture Resolution and Fail-Safe Defaults
- **Status Reason**: Unconfirmed code-searchable component(s): YAML
  - Component `agent/config.yaml` (`config`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `YAML` (`YAML`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 2` in [SPEC-enforcement-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-enforcement-postures.md)
- **Title**: Baseline Grandfathering and File-Edit Lapsing in Ratchet Posture
- **Status Reason**: Unconfirmed code-searchable component(s): enforcement.posture: ratchet, git diff --name-only HEAD, git diff --name-only HEAD^1, depth=1, HEAD^1, SHALLOW_CLONE_LAPSE_SKIPPED, HEAD
  - Component `enforcement.posture: ratchet` (`enforcement.posture: ratchet`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `agent/baseline.json` (`baseline`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `git diff --name-only HEAD` (`git diff --name-only HEAD`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `git diff --name-only HEAD^1` (`git diff --name-only HEAD^1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `--depth=1` (`depth=1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `HEAD^1` (`HEAD^1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `SHALLOW_CLONE_LAPSE_SKIPPED` (`SHALLOW_CLONE_LAPSE_SKIPPED`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `HEAD` (`HEAD`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 3` in [SPEC-enforcement-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-enforcement-postures.md)
- **Title**: Baseline Tamper Detection and Fallback
- **Status Reason**: Unconfirmed code-searchable component(s): header.manifest_sha256, SHA-256, JSON, json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
  - Component `agent/baseline.json` (`baseline`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `header.manifest_sha256` (`header.manifest_sha256`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `posture.py` (`posture`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `SHA-256` (`SHA-256`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `entries` (`entries`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `JSON` (`JSON`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")` (`json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4` in [SPEC-enforcement-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-enforcement-postures.md)
- **Title**: Human-Only Baseline Generation
- **Status Reason**: Unconfirmed code-searchable component(s): AGENT_ID, sys.stdin.isatty, False, python .agent/scripts/baseline.py init, refresh
  - Component `AGENT_ID` (`AGENT_ID`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `sys.stdin.isatty()` (`sys.stdin.isatty`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `False` (`False`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `python .agent/scripts/baseline.py init` (`python .agent/scripts/baseline.py init`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `refresh` (`refresh`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 5` in [SPEC-enforcement-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-enforcement-postures.md)
- **Title**: Observe Posture Disposition Behavior
- **Status Reason**: Unconfirmed code-searchable component(s): enforcement.posture: observe, observe_expires, ISO, 8601, datetime.now(timezone.utc)
  - Component `enforcement.posture: observe` (`enforcement.posture: observe`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `observe_expires` (`observe_expires`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `ISO` (`ISO`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `8601` (`8601`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `UTC` (`UTC`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `datetime.now(timezone.utc)` (`datetime.now(timezone.utc)`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 6` in [SPEC-enforcement-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-enforcement-postures.md)
- **Title**: Invariant Floor Immunity for Hard Safety Rules
- **Status Reason**: Unconfirmed code-searchable component(s): enforcement.posture: observe, ratchet, H-01, H-09, AGENTS.md §4.1
  - Component `enforcement.posture: observe` (`enforcement.posture: observe`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `ratchet` (`ratchet`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `H-01` (`H-01`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `H-09` (`H-09`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `AGENTS.md §4.1` (`AGENTS.md §4.1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 7` in [SPEC-enforcement-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-enforcement-postures.md)
- **Title**: Bypass File Deprecation
- **Status Reason**: Unconfirmed code-searchable component(s): skip-ai-review, SKIP_AI_REVIEW=1
  - Component `skip-ai-review` (`skip-ai-review`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `SKIP_AI_REVIEW=1` (`SKIP_AI_REVIEW=1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 1` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Posture Resolution and Fail-Safe Defaults (T1-G-18)
- **Status Reason**: Unconfirmed code-searchable component(s): YAML
  - Component `agent/config.yaml` (`config`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `YAML` (`YAML`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 2` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Baseline Grandfathering and File-Edit Lapsing in Ratchet Posture (T1-G-18)
- **Status Reason**: Unconfirmed code-searchable component(s): enforcement.posture: ratchet, git diff --name-only HEAD, git diff --name-only HEAD^1, depth=1, HEAD^1, SHALLOW_CLONE_LAPSE_SKIPPED, HEAD
  - Component `enforcement.posture: ratchet` (`enforcement.posture: ratchet`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `agent/baseline.json` (`baseline`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `git diff --name-only HEAD` (`git diff --name-only HEAD`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `git diff --name-only HEAD^1` (`git diff --name-only HEAD^1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `--depth=1` (`depth=1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `HEAD^1` (`HEAD^1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `SHALLOW_CLONE_LAPSE_SKIPPED` (`SHALLOW_CLONE_LAPSE_SKIPPED`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `HEAD` (`HEAD`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 3` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Baseline Tamper Detection and Fallback (T1-G-18)
- **Status Reason**: Unconfirmed code-searchable component(s): header.manifest_sha256, SHA-256, JSON, json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
  - Component `agent/baseline.json` (`baseline`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `header.manifest_sha256` (`header.manifest_sha256`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `posture.py` (`posture`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `SHA-256` (`SHA-256`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `entries` (`entries`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `JSON` (`JSON`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")` (`json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Human-Only Baseline Generation (T1-G-18)
- **Status Reason**: Unconfirmed code-searchable component(s): AGENT_ID, sys.stdin.isatty, False, python .agent/scripts/baseline.py init, refresh
  - Component `AGENT_ID` (`AGENT_ID`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `sys.stdin.isatty()` (`sys.stdin.isatty`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `False` (`False`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `python .agent/scripts/baseline.py init` (`python .agent/scripts/baseline.py init`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `refresh` (`refresh`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 5` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Observe Posture Disposition Behavior (T1-G-18)
- **Status Reason**: Unconfirmed code-searchable component(s): enforcement.posture: observe, observe_expires, ISO, 8601, datetime.now(timezone.utc)
  - Component `enforcement.posture: observe` (`enforcement.posture: observe`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `observe_expires` (`observe_expires`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `ISO` (`ISO`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `8601` (`8601`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `UTC` (`UTC`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `datetime.now(timezone.utc)` (`datetime.now(timezone.utc)`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 6` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Invariant Floor Immunity for Hard Safety Rules (T1-G-18)
- **Status Reason**: Unconfirmed code-searchable component(s): enforcement.posture: observe, ratchet, H-01, H-09, AGENTS.md §4.1
  - Component `enforcement.posture: observe` (`enforcement.posture: observe`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `ratchet` (`ratchet`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `H-01` (`H-01`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `H-09` (`H-09`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `AGENTS.md §4.1` (`AGENTS.md §4.1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 7` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Bypass File Deprecation (T1-G-18)
- **Status Reason**: Unconfirmed code-searchable component(s): skip-ai-review, SKIP_AI_REVIEW=1
  - Component `skip-ai-review` (`skip-ai-review`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `SKIP_AI_REVIEW=1` (`SKIP_AI_REVIEW=1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 8` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Dynamic Pathing Bootstrap Across 11 Target Scripts (HIB-073)
- **Status Reason**: Unconfirmed code-searchable component(s): 11, circuit_breaker, co_change_core, onboarding, wiki_lint, validate, agent/scripts/, agent/skills/universal/*/scripts/
  - Component `11` (`11`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `check_spec.py` (`check_spec`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `circuit_breaker.py` (`circuit_breaker`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `co_change_core.py` (`co_change_core`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `co_change_reconciler.py` (`co_change_reconciler`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `init_session.py` (`init_session`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `onboarding.py` (`onboarding`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `wiki_compile.py` (`wiki_compile`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `wiki_lint.py` (`wiki_lint`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `repo_map.py` (`repo_map`): Tier=function, Mock=MOCKED, AssertOverlap=True -> **CONFIRMED**
  - Component `validate.py` (`validate`): Tier=function, Mock=REAL, AssertOverlap=False -> **UNCONFIRMED**
  - Component `harness_health.py` (`harness_health`): Tier=function, Mock=MOCKED, AssertOverlap=True -> **CONFIRMED**
  - Component `agent/scripts/` (`agent/scripts/`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `agent/skills/universal/*/scripts/` (`agent/skills/universal/*/scripts/`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 9` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Disambiguated Provider Exceptions (HIB-074)
- **Status Reason**: Unconfirmed code-searchable component(s): RuntimeError: Content too large
  - Component `RuntimeError: Content too large` (`RuntimeError: Content too large`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `ai_review.py` (`ai_review`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**

### `Scenario 10` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Traceability Self-Ratification Prevention (HIB-076)
- **Status Reason**: Unconfirmed code-searchable component(s): ID, HEAD
  - Component `ID` (`ID`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `HEAD` (`HEAD`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `is_root_commit()` (`is_root_commit`): Tier=function, Mock=MOCKED, AssertOverlap=True -> **CONFIRMED**

### `Scenario 11` in [SPEC-v1.4.12-governance-hardening-and-postures.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.12-governance-hardening-and-postures.md)
- **Title**: Multi-Table SQLite Schema Drift Migration (HIB-077)
- **Status Reason**: Unconfirmed code-searchable component(s): harness.db, sync_session_to_db
  - Component `harness.db` (`harness.db`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `sync_session_to_db()` (`sync_session_to_db`): Tier=function, Mock=REAL, AssertOverlap=False -> **UNCONFIRMED**
  - Component `state_persistence.py` (`state_persistence`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**

### `Scenario 1` in [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md)
- **Title**: Ratchet posture grandfathers pre-existing architecture_checks.py violations (HIB-080)
- **Status Reason**: Unconfirmed code-searchable component(s): enforcement.posture: ratchet, FAIL, LAYER_BOUNDARY
  - Component `enforcement.posture: ratchet` (`enforcement.posture: ratchet`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `agent/baseline.json` (`baseline`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `FAIL` (`FAIL`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `LAYER_BOUNDARY` (`LAYER_BOUNDARY`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `architecture_checks.py` (`architecture_checks`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**

### `Scenario 3` in [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md)
- **Title**: decisions_log.md rejects corrupting writes (BUG-19)
- **Status Reason**: Unconfirmed code-searchable component(s): t
  - Component `record_decision()` (`record_decision`): Tier=function, Mock=REAL, AssertOverlap=False -> **CONFIRMED**
  - Component `t` (`t`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 5` in [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md)
- **Title**: Gate findings are surfaced and frozen at rebuttal time (HIB-047 + HIB-048)
- **Status Reason**: Unconfirmed code-searchable component(s): FAIL
  - Component `FAIL` (`FAIL`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 6` in [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md)
- **Title**: Config-driven schema hardening exemptions preserve GymBase behavior while keeping framework source clean (Phase 5)
- **Status Reason**: Unconfirmed code-searchable component(s): schema_hardening
  - Component `enforce_hardened_schemas.py` (`enforce_hardened_schemas`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `analyze_schema.py` (`analyze_schema`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `schema_hardening` (`schema_hardening`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `agent/config.yaml` (`config`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**

### `Scenario 7` in [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md)
- **Title**: Import ceiling in test_ai_review.py remains strictly pinned at 32 (Phase 5)
- **Status Reason**: Unconfirmed code-searchable component(s): test_import_count_does_not_exceed_ceiling, test_ai_review
  - Component `src/scripts/ai_review.py` (`ai_review`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `test_import_count_does_not_exceed_ceiling` (`test_import_count_does_not_exceed_ceiling`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `tests/test_ai_review.py` (`test_ai_review`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 8` in [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md)
- **Title**: Upgrade preserves existing schema-hardening exemptions (Phase 5)
- **Status Reason**: Unconfirmed code-searchable component(s): 12, WHITELIST, exempt_tables, 13
  - Component `12` (`12`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `WHITELIST` (`WHITELIST`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `exempt_tables` (`exempt_tables`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `enforce_hardened_schemas.py` (`enforce_hardened_schemas`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `analyze_schema.py` (`analyze_schema`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `bootstrap/upgrade.py` (`upgrade`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `13` (`13`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 9` in [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md)
- **Title**: Decision logging works as a standalone CLI invocation (HIB-082)
- **Status Reason**: Unconfirmed code-searchable component(s): CWD, sys.path, PYTHONPATH, python .agent/scripts/log_decision.py "title" "what" "why" "impact
  - Component `CWD` (`CWD`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `sys.path` (`sys.path`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `PYTHONPATH` (`PYTHONPATH`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `python .agent/scripts/log_decision.py "title" "what" "why" "impact` (`python .agent/scripts/log_decision.py "title" "what" "why" "impact`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 10` in [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md)
- **Title**: No script duplicates the UTF-8 stdout/stderr wrap (HIB-083)
- **Status Reason**: Unconfirmed code-searchable component(s): 10, audit_logger, check_halt, check_repo, circuit_breaker, eval_runner, false_positive_to_eval, wiki_compile, wiki_lint
  - Component `10` (`10`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `session_health.py` (`session_health`): Tier=function, Mock=MOCKED, AssertOverlap=True -> **CONFIRMED**
  - Component `audit_logger.py` (`audit_logger`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `check_halt.py` (`check_halt`): Tier=function, Mock=REAL, AssertOverlap=False -> **UNCONFIRMED**
  - Component `check_repo.py` (`check_repo`): Tier=function, Mock=REAL, AssertOverlap=False -> **UNCONFIRMED**
  - Component `circuit_breaker.py` (`circuit_breaker`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `co_change_reconciler.py` (`co_change_reconciler`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `eval_runner.py` (`eval_runner`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `false_positive_to_eval.py` (`false_positive_to_eval`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `pm_scaffold.py` (`pm_scaffold`): Tier=function, Mock=MOCKED, AssertOverlap=True -> **CONFIRMED**
  - Component `wiki_compile.py` (`wiki_compile`): Tier=function, Mock=REAL, AssertOverlap=False -> **UNCONFIRMED**
  - Component `wiki_lint.py` (`wiki_lint`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 11` in [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md)
- **Title**: session_health.py runs cleanly under Windows cp1252 console (HIB-083 regression guard)
- **Status Reason**: Unconfirmed code-searchable component(s): UTF-8
  - Component `UTF-8` (`UTF-8`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `python .agent/scripts/session_health.py` (`session_health`): Tier=function, Mock=MOCKED, AssertOverlap=True -> **CONFIRMED**

### `Scenario 12` in [SPEC-v1.4.13-stabilization.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/archive/SPEC-v1.4.13-stabilization.md)
- **Title**: Spec status reflects delivery state (Phase 4)
- **Status Reason**: Unconfirmed code-searchable component(s): docs/planning/specs/archive/, Status
  - Component `docs/planning/specs/archive/` (`docs/planning/specs/archive/`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `Status` (`Status`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 1` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Spec-scenario cross-reference detects an unimplemented outcome assertion (Phase A)
- **Status Reason**: Unconfirmed code-searchable component(s): APPROVED
  - Component `APPROVED` (`APPROVED`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 1b` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Cross-reference heuristic is calibrated before its report is trusted
- **Status Reason**: Unconfirmed code-searchable component(s): UNVERIFIED, VERIFIED
  - Component `UNVERIFIED` (`UNVERIFIED`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `VERIFIED` (`VERIFIED`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4b` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Wiring audit flags a vacuous argument as a partial-wiring defect
- **Status Reason**: Unconfirmed code-searchable component(s): None
  - Component `baseline=` (`baseline`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `None` (`None`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4c` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Malformed or empty consumer manifest fails loud, not silent
- **Status Reason**: Unconfirmed code-searchable component(s): wiring_consumers
  - Component `wiring_consumers.yaml` (`wiring_consumers`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4d` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: record_decision() rejects an unclassified impact value
- **Status Reason**: Unconfirmed code-searchable component(s): high, medium, low
  - Component `record_decision()` (`record_decision`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `impact` (`impact`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `high, medium, low` (`high, medium, low`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4e` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: archive_old_decisions() retains high-impact entries across the line-count threshold
- **Status Reason**: Unconfirmed code-searchable component(s): decisions_log, 150
  - Component `decisions_log.md` (`decisions_log`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `150` (`150`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4f` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Eviction priority correctly orders mixed medium/low entries by age-weighted score, not recency alone
- **Status Reason**: Unconfirmed code-searchable component(s): age_in_days / impact_weight, low, medium
  - Component `age_in_days / impact_weight` (`age_in_days / impact_weight`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `low=` (`low`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `medium=` (`medium`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4g` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: A log exceeding threshold entirely from high-impact entries fails loud rather than silently evicting a pinned entry
- **Status Reason**: Unconfirmed code-searchable component(s): decisions_log, 150
  - Component `decisions_log.md` (`decisions_log`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `150` (`150`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4h` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Reproducing the staleness blind spot before the fix
- **Status Reason**: Unconfirmed code-searchable component(s): verification-before-completion__state_anomaly__open
  - Component `distill_dream.py` (`distill_dream`): Tier=function, Mock=MOCKED, AssertOverlap=False -> **CONFIRMED**
  - Component `verification-before-completion__state_anomaly__open.md` (`verification-before-completion__state_anomaly__open`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `report_dream_proposal_staleness()` (`report_dream_proposal_staleness`): Tier=function, Mock=REAL, AssertOverlap=False -> **CONFIRMED**

### `Scenario 4j` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Backfill closes the loop for the existing proposal, not just future ones
- **Status Reason**: Unconfirmed code-searchable component(s): 2026-06-13
  - Component `2026-06-13` (`2026-06-13`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4k` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Reproducing the hollow-gate discrepancy before the fix
- **Status Reason**: Unconfirmed code-searchable component(s): golden_dataset, regression_runner, verify-only
  - Component `golden_dataset.yaml` (`golden_dataset`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `regression_runner.py` (`regression_runner`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `--verify-only` (`verify-only`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `--run` (`run`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**

### `Scenario 4l` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Fix — empty dataset exits non-zero and states the escalation reason
- **Status Reason**: Unconfirmed code-searchable component(s): golden_dataset, regression_runner
  - Component `golden_dataset.yaml` (`golden_dataset`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `regression_runner.py` (`regression_runner`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4m` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Fix does not break the legitimate "no regressions yet" case
- **Status Reason**: Unconfirmed code-searchable component(s): golden_dataset, regression_runner
  - Component `golden_dataset.yaml` (`golden_dataset`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `regression_runner.py` (`regression_runner`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4n` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Reproducing the stale-path blind spot before the fix
- **Status Reason**: Unconfirmed code-searchable component(s): wiki_lint, review_context_universal, review_context_project, RULE, PATTERN, run_orphaned_rules_check, run_staleness_check
  - Component `wiki_lint.py` (`wiki_lint`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `review_context_universal.md` (`review_context_universal`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `review_context_project.md` (`review_context_project`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `RULE` (`RULE`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `PATTERN` (`PATTERN`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `run_orphaned_rules_check()` (`run_orphaned_rules_check`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `run_staleness_check()` (`run_staleness_check`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4o` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: (revised): Fix resolves context files by asking the real loader, not a hardcoded guess
- **Status Reason**: Unconfirmed code-searchable component(s): context_loader, wiki_lint
  - Component `context_loader.py` (`context_loader`): Tier=function, Mock=MOCKED, AssertOverlap=False -> **UNCONFIRMED**
  - Component `wiki_lint.py` (`wiki_lint`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4o-b` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Fix resolves architecture_checks.py by reusing the harness's own dual-path resolution
- **Status Reason**: Unconfirmed code-searchable component(s): agent/skills/universal/senior-architect/scripts, agent/skills/senior-architect/scripts, wiki_lint, ARCH_CHECKS_FILE
  - Component `harness_utils.py` (`harness_utils`): Tier=function, Mock=REAL, AssertOverlap=False -> **CONFIRMED**
  - Component `_setup_sys_path()` (`_setup_sys_path`): Tier=function, Mock=REAL, AssertOverlap=False -> **CONFIRMED**
  - Component `agent/skills/universal/senior-architect/scripts` (`agent/skills/universal/senior-architect/scripts`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `agent/skills/senior-architect/scripts` (`agent/skills/senior-architect/scripts`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `wiki_lint.py` (`wiki_lint`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `ARCH_CHECKS_FILE` (`ARCH_CHECKS_FILE`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4p` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Fix does not mask the subprocess NameError with a different silent failure
- **Status Reason**: Unconfirmed code-searchable component(s): _find_project_root
  - Component `_find_project_root()` (`_find_project_root`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `subprocess` (`subprocess`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**

### `Scenario 4q` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Post-fix baseline run establishes real findings, not asserted zero
- **Status Reason**: Unconfirmed code-searchable component(s): review_context_universal, review_context_project, wiki_lint
  - Component `review_context_universal.md` (`review_context_universal`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `review_context_project.md` (`review_context_project`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `architecture_checks.py` (`architecture_checks`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `wiki_lint.py` (`wiki_lint`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4r` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Fix detects a legacy, unloaded context file as its own finding
- **Status Reason**: Unconfirmed code-searchable component(s): review_context, review_context_universal, review_context_project, wiki_lint
  - Component `review_context.md` (`review_context`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `review_context_universal.md` (`review_context_universal`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `review_context_project.md` (`review_context_project`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `wiki_lint.py` (`wiki_lint`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 4s` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Fix works correctly against Gym_App without any Gym_App-specific code
- **Status Reason**: Unconfirmed code-searchable component(s): wiki_lint
  - Component `wiki_lint.py` (`wiki_lint`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 5` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: E2E scenario classification produces an accurate single-gate/cross-gate tally
- **Status Reason**: Unconfirmed code-searchable component(s): 29, run_e2e_verification
  - Component `29` (`29`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `tests/e2e/run_e2e_verification.py` (`run_e2e_verification`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 7` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Contract test catches a producer/parser mismatch retroactively (D1)
- **Status Reason**: Unconfirmed code-searchable component(s): distill_dream, Generated, D1
  - Component `distill_dream.py` (`distill_dream`): Tier=function, Mock=MOCKED, AssertOverlap=False -> **UNCONFIRMED**
  - Component `harness_health.py` (`harness_health`): Tier=function, Mock=MOCKED, AssertOverlap=True -> **CONFIRMED**
  - Component `Generated` (`Generated`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `D1` (`D1`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 8` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Tooling-path staleness check catches the wiki_lint.py defect retroactively (D2)
- **Status Reason**: Unconfirmed code-searchable component(s): wiki_lint, CONTEXT_FILE, ARCH_CHECKS_FILE, D2
  - Component `wiki_lint.py` (`wiki_lint`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `CONTEXT_FILE` (`CONTEXT_FILE`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `ARCH_CHECKS_FILE` (`ARCH_CHECKS_FILE`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `D2` (`D2`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 9` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Doc/code drift check catches the regression_runner.py discrepancy retroactively (D3)
- **Status Reason**: Unconfirmed code-searchable component(s): regression_runner, eval-pipeline, D3, golden_dataset
  - Component `regression_runner.py` (`regression_runner`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `eval-pipeline.md` (`eval-pipeline`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `D3` (`D3`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `golden_dataset.yaml` (`golden_dataset`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

### `Scenario 10` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Coverage-completeness check flags an untested-but-working loop (D4)
- **Status Reason**: Unconfirmed code-searchable component(s): session_ledger, retention_cleanup, LOOP-017, D4
  - Component `session_ledger.jsonl` (`session_ledger`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `init_session.py` (`init_session`): Tier=function, Mock=REAL, AssertOverlap=True -> **CONFIRMED**
  - Component `retention_cleanup.py` (`retention_cleanup`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `LOOP-017` (`LOOP-017`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**
  - Component `D4` (`D4`): Tier=none, Mock=n/a, AssertOverlap=False -> **UNCONFIRMED**

## 🟢 VERIFIED Scenarios (Real Entry Point)
### `Scenario 3` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Wiring audit reproduces the HIB-080 finding retroactively
  - Component `ai_review.py` (`ai_review`): Matched in `['tests/integration/test_ai_review_context_selection.py']` (['test_select_context_sections_always_includes_rule_sections'])
  - Component `architecture_checks.py` (`architecture_checks`): Matched in `['tests/test_architecture_checks.py']` (['test_check_adr_decision_blocks_advisory_missing'])

## 🟡 VERIFIED Scenarios (Mock Only)
### `Scenario 4i` in [SPEC-loop-closure-verification.md](file:///C:/projects/ai-delivery-control/docs/planning/specs/SPEC-loop-closure-verification.md)
- **Title**: Fix — proposal template emits a Generated field the existing parser can consume
  - Component `distill_dream.py` (`distill_dream`): Matched in `['tests/test_distill_dream.py']` (Mocked: MOCKED)

## ⚪ SKIPPED Scenarios (Non-Code / Spec Tags)
Total skipped scenarios: 51 (all components are spec/backlog tags or non-code text).