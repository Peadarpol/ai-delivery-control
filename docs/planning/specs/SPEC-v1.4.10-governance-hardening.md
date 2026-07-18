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

### Component: Governance & Risk
#### [MODIFY] [route_decision.py](file:///c:/projects/ai-delivery-control/src/scripts/route_decision.py)
- **T1-L-21 (`high_risk_patterns` override)**: Refactor `_load_high_risk_patterns()` to support full key replacement from `.agent/config.yaml` rather than merging additively only. Decouple hardcoded defaults.
- **T1-L-20 (posture configuration)**: Implement configuration routing for enforcement postures (`lean`, `standard`, `thorough`, `exhaustive`) to scale check intensity and review model routing.

#### [MODIFY] [pre-commit-config.yaml.template](file:///c:/projects/ai-delivery-control/bootstrap/templates/pre-commit-config.yaml.template) and [governance_check.py](file:///c:/projects/ai-delivery-control/.agent/scripts/governance_check.py)
- **T1-K-12 (pre-local-merge sensitive-path check)**: Set up checks targeting local merges to `main` or `develop`. Refuse fast local merges if high-risk paths are altered, unless an explicit reason-logged override is provided by the developer.

### Component: Requirement Traceability
#### [MODIFY] [check_traceability.py](file:///c:/projects/ai-delivery-control/.agent/scripts/check_traceability.py)
- **T1-K-13 (`--no-trace` verification)**: Refactor bypass checks to validate session metadata and accountable developer signature, stopping anonymous `--no-trace` commit message bypasses.
- **HIB-061 / AT-06 (root commit exemption)**: Integrate mode-dependent exemption checks to permit initial project commits (discovery/genesis mode) while maintaining gating integrity on subsequent commits.

### Component: Gate Diagnostics
#### [MODIFY] [ai_review.py](file:///c:/projects/ai-delivery-control/src/scripts/ai_review.py)
- **T1-K-14 (fail-open gate audit)**: Update `DIFF_TOO_LARGE_FAILOPEN` and runtime exception boundaries to assert `FAIL_OPEN` or `INCOMPLETE` verdicts rather than defaulting to pass.

### Component: Session Lifecycle
#### [MODIFY] [governance_check.py](file:///c:/projects/ai-delivery-control/.agent/scripts/governance_check.py)
- **HIB-063 (snapshot-based audit-log)**: Implement automated checks to capture session event logs (`harness_events.jsonl`) and snapshot them at commit time, tracking changes and preventing bypasses.

#### [MODIFY] [init_session.py](file:///c:/projects/ai-delivery-control/.agent/scripts/init_session.py)
- **HIB-ENV-02 (stashing preflight control)**: Prevent automated/silent stashing of uncommitted files at session startup. Verify dirty files exist, print diagnostic information, and require confirmation before executing `git stash`.

#### [MODIFY] [state_persistence.py](file:///c:/projects/ai-delivery-control/src/scripts/state_persistence.py) and [NEW] [.agent/state/lessons_learned_schema.json](file:///c:/projects/ai-delivery-control/.agent/state/lessons_learned_schema.json)
- **T1-I-08 (session lessons index schema)**: Implement indexing and compaction workflows to extract post-mortem lessons learned from session trajectories.

### Component: Session Database
#### [MODIFY] [state_persistence.py](file:///c:/projects/ai-delivery-control/src/scripts/state_persistence.py)
- **HIB-059 (SQLite thread safety)**: Harden connection management by introducing concurrency locks and enabling Write-Ahead Logging (WAL) mode to protect the SQLite database from thread lock faults.

---

## 6. Sequencing Constraints

* **T1-K-12 Dependency**: Implementation of `T1-K-12` (pre-local-merge sensitive-path check) **must** occur after `T1-L-21` (override-capable classifier) has been successfully implemented and verified, as `T1-K-12` depends directly on reusing the generalized risk classifier.

---

## 7. Verification Plan

### Automated Tests
- Run consistency validator:
  `.venv/bin/python -m pytest tests/test_framework_consistency.py` (macOS/Linux) or `.venv\Scripts\python -m pytest tests/test_framework_consistency.py` (Windows)
- Run SQLite concurrency/locking safety suites:
  `.venv/bin/python -m pytest tests/test_session_health.py` (macOS/Linux) or `.venv\Scripts\python -m pytest tests/test_session_health.py` (Windows)

---

## 8. Resolved Decisions

* None in this draft.
