# SPEC-v1.4.10-governance-hardening

**Status**: DRAFT  
**Author**: Gemini (AI execution mode)  
**Feeds into**: Release v1.4.10  
**Tracked under**: `T1-K-12` / `T1-L-21` / `T1-K-13` / `T1-K-14` / `HIB-063` / `T1-L-20` / `HIB-ENV-02` / `T1-I-08` / `HIB-059` / `HIB-061`

---

## 1. Goal & Context

The goal of this release is to harden the harness's self-governance and downstream validation mechanics. Specifically, it closes gaps around unauthenticated bypasses, hardcoded risk classifications, silent fail-opens on large diffs/crashes, and unsafe stashing at session start.

---

## 2. Bounded Scope & Out of Scope

* **Bounded Scope**:
  - Implement dynamic `high_risk_patterns` classification overrides in `.agent/config.yaml` to decouple the codebase from GymBase-specific defaults (delivering `T1-L-21`).
  - Introduce pre-local-merge checks targeting modified files in main/develop branches, requiring an human override if sensitive paths are modified (delivering `T1-K-12`).
  - Secure the `--no-trace` option by validating the session metadata and human signature rather than allowing anonymous bypasses (delivering `T1-K-13`).
  - Audit all gate fail-open points (such as `DIFF_TOO_LARGE_FAILOPEN`) to ensure the system reports `FAIL_OPEN` or `INCOMPLETE` rather than masking failures as `PASS` (delivering `T1-K-14`).
  - Implement a safe-stash preflight routine during `init_session.py` to prompt the operator before stashing dirty files (delivering `HIB-ENV-02`).
  - Integrate Skip-With-Advisory preconditions (AT-04) and Root-Commit Traceability Exemptions (AT-06) into the core gate runtime.
* **Out of Scope**:
  - Rewriting the command-line grammar for pre-commit arguments.
  - Adding deep Starlark-based policy rules.

---

## 3. Assumptions

* `[Resolved: The developer uses Git CLI and executes commits through standard developer shell environments.]`
* `[Resolved: Config overrides in config.yaml take precedence over fallback stack-pack defaults.]`

---

## 4. Acceptance Criteria

### Scenario 1: Risk classification override in config
* **Given** a target project layout with no Repository or Unit-of-Work classes (e.g. a simple script library)
* **When** `high_risk_patterns` config overrides are specified in `.agent/config.yaml`
* **Then** `route_decision.py` uses the customized config file list to compute `elevated` or `critical` reviews
* **And** GymBase defaults are ignored if overridden.

### Scenario 2: Fail-open audit reports correct taxonomy
* **Given** a git commit diff exceeding the maximum token capacity (e.g. 700KB)
* **When** the pre-commit review gate runs
* **Then** the gate exits cleanly but reports `verdict: FAIL_OPEN` (or `INCOMPLETE`) to the session ledger
* **And** the commit metadata correctly logs the `large_diff_fail_open` event.

### Scenario 3: Precondition skip advisory
* **Given** a project running pre-commit check hooks where contextual files (such as exception standards tests) are absent
* **When** the hook execution wrapper fires
* **Then** the hook logs `verdict: SKIPPED-precondition` in `harness_events.jsonl`
* **And** exits with code `0`.

---

## 5. Proposed Changes

### Component: Governance & Risk (T1-L-21, T1-K-12)
#### [MODIFY] [route_decision.py](file:///c:/projects/ai-delivery-control/src/scripts/route_decision.py)
- Refactor `_load_high_risk_patterns()` to support full key replacement from `.agent/config.yaml` rather than merging additively only.

### Component: Gate Diagnostics (T1-K-14)
#### [MODIFY] [ai_review.py](file:///c:/projects/ai-delivery-control/src/scripts/ai_review.py)
- Refactor large diff limits and runtime error handlers to output `FAIL_OPEN` or `INCOMPLETE` instead of generic `PASS` values.

---

## 6. Verification Plan

### Automated Tests
- Run consistency validator:
  `poetry run pytest tests/test_framework_consistency.py`
- Run SQLite concurrency/locking safety suites:
  `poetry run pytest tests/test_session_health.py`
