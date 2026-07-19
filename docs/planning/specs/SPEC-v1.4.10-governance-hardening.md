# SPEC-v1.4.10-governance-hardening

**Status**: DRAFT  
**Author**: Gemini (AI execution mode)  
**Feeds into**: Release v1.4.10  
**Tracked under**: `T1-K-12` / `T1-L-21` / `T1-K-13` / `T1-K-14` / `HIB-063` / `T1-L-20` / `HIB-ENV-02` / `T1-I-08` / `HIB-059` / `HIB-061`

---

## 1. Goal & Context

The goal of this release is to harden the harness's self-governance and downstream validation mechanics. Specifically, it closes gaps around unauthenticated bypasses, hardcoded risk classifications, silent fail-opens on large diffs/crashes, database schema mismatches, and unsafe stashing at session start.

---

## 2. Bounded Scope & Out of Scope

* **Bounded Scope**:
  - Implement dynamic `high_risk_patterns` classification overrides in `.agent/config.yaml` to decouple the codebase from GymBase-specific defaults (delivering `T1-L-21`).
  - Introduce pre-local-merge checks targeting modified files in main/develop branches, requiring an human override if sensitive paths are modified (delivering `T1-K-12`).
  - Secure the `--no-trace` option by validating the session metadata and human signature rather than allowing anonymous bypasses (delivering `T1-K-13`).
  - Audit all gate fail-open points (such as `DIFF_TOO_LARGE_FAILOPEN`) to ensure the system reports `FAIL_OPEN` or `INCOMPLETE` rather than masking failures as `PASS` (delivering `T1-K-14`).
  - Implement a safe-stash preflight routine during `init_session.py` to prompt the operator before stashing dirty files (delivering `HIB-ENV-02`).
  - Drop the per-session `AUTO` checkpoint stash on clean close in `init_session.py` to avoid clutter (delivering `T1-I-08`).
  - Reconcile SQLite database schemas and fix misleading error messages (delivering `HIB-059`).
  - Integrity checks for root commits (delivering `HIB-061` / `AT-06`).
* **Out of Scope**:
  - Implementation of enforcement postures (strict/ratchet/observe, tracked under `T1-G-18`).
  - Implementation of decisions_log structured schemas (tracked under `T1-L-20` research pass).

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
- **T1-L-21 (`high_risk_patterns` override)**: Refactor `_load_high_risk_patterns()`, `classify_commit_risk()`, and `get_high_risk_files()` to support a replace-defaults override flag (`override_defaults: true`) under the `high_risk_patterns` config block in `.agent/config.yaml`. When set to true, do not prepend the hardcoded Python/GymBase defaults (`unit_of_work.py`, `base_repository.py`, `models.py`, `branch_isolation`, `authentication`, `schema_hardening`).
- **T1-L-20 (decisions log schema)**: Research-only pass. No code or schema changes are introduced in this release.

#### [MODIFY] [pre-commit-config.yaml.template](file:///c:/projects/ai-delivery-control/bootstrap/templates/pre-commit-config.yaml.template) and [.agent/scripts/check_traceability.py](file:///c:/projects/ai-delivery-control/.agent/scripts/check_traceability.py)
- **T1-K-12 (pre-local-merge sensitive-path check)**: Set up a blocking gate check targeting local merges to `main` or `develop` at a blocking stage (e.g. at the `pre-commit` stage by verifying `.git/MERGE_HEAD` presence, or at `pre-push` stage to inspect local branch merge commits). Refuse the action if sensitive paths are altered, unless an explicit reason-logged human override is provided. Note: This blocking logic cannot run in `governance_check.py` since it is a non-blocking `post-commit` hook.
- **Minor Clean-up in [governance_check.py](file:///c:/projects/ai-delivery-control/.agent/scripts/governance_check.py)**: Remove the unreachable `print("✅ Governance check complete.")` statement in `check_commit_sequence` located after `return None` (line 130).

### Component: Requirement Traceability
#### [MODIFY] [check_traceability.py](file:///c:/projects/ai-delivery-control/.agent/scripts/check_traceability.py)
- **T1-K-13 (`--no-trace` verification)**: Refactor bypass checks to validate session metadata and accountable developer signature, stopping anonymous `--no-trace` commit message bypasses.
- **T1-K-13.1 (backlog-ID verification hardening)**: Modify the ID verification loop to verify backlog references (such as `HIB-*`, `BUG-*`, or `T1-*`) against the committed document contents at `HEAD` (via `git show HEAD:docs/...` or equivalent) rather than reading directly from the working-tree files, preventing self-ratifying IDs introduced in the same commit.
- **HIB-061 / AT-06 (root commit exemption)**: Integrate mode-dependent exemption checks. Explicitly handle initial project root commits containing code files in incremental mode (where `git rev-parse --verify HEAD` fails due to no existing commits), allowing them to pass the gate safely while maintaining strict validation on all subsequent commits.

### Component: Gate Diagnostics
#### [MODIFY] [ai_review.py](file:///c:/projects/ai-delivery-control/src/scripts/ai_review.py)
- **T1-K-14 (fail-open gate audit)**: Update `DIFF_TOO_LARGE_FAILOPEN` and runtime exception boundaries to assert `FAIL_OPEN` or `INCOMPLETE` verdicts rather than defaulting to pass.

### Component: Session Lifecycle
#### [MODIFY] [governance_check.py](file:///c:/projects/ai-delivery-control/.agent/scripts/governance_check.py), [ai_review.py](file:///c:/projects/ai-delivery-control/src/scripts/ai_review.py), [init_session.py](file:///c:/projects/ai-delivery-control/.agent/scripts/init_session.py), and [.gitignore](file:///c:/projects/ai-delivery-control/.gitignore)
- **HIB-063 (snapshot-based audit-log)**: Implement an untracked live logs strategy to avoid git hook conflicts. Enumerate all log-writer sites to ignore: `harness_events.jsonl` (written by `governance_check.py` and `init_session.py`) and `.ai-review-log.jsonl` (written by `ai_review.py`). Ignore these files in the project `.gitignore`. A committed snapshot of the live logs is taken on clean session close.

#### [MODIFY] [init_session.py](file:///c:/projects/ai-delivery-control/.agent/scripts/init_session.py)
- **HIB-ENV-02 (stashing preflight control)**: Prevent silent/unconditional stashing at session start in `_create_session_checkpoint()`. If stdin is not a TTY (programmatic agent execution), the fail-safe behavior is to NOT stash and log a warning (retaining the dirty working copy). If stdin is a TTY (interactive developer), prompt the operator before stashing.
- **T1-I-08 (session-start stash accumulation cleanup)**: Refactor `infer_and_close_previous_session()` (which retrospectively closes the prior session at the start of the next session) to drop the session-start checkpoint stash matching the prior session's ID.
  * **Ordering Constraint**: The stash drop MUST occur after the session-close outcome is successfully written to `session.json`.

### Component: Session Database
#### [MODIFY] [state_persistence.py](file:///c:/projects/ai-delivery-control/src/scripts/state_persistence.py)
- **HIB-059 (SQLite schema drift detection & migration)**: Modify `_ensure_schema()` to detect database schema drift (e.g., verifying column presence via `PRAGMA table_info(sessions)` or checking a schema version table). On schema mismatch, execute an ALTER TABLE migration or safely DROP the stale index table and trigger the existing `rebuild_from_flat_files()` function. Update the SQLite `OperationalError` catch block in `sync_session_to_db` to distinguish true lock errors from schema mismatch errors and log details accordingly.

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

* **HIB-063 (Audit-log snapshot cadence)**: Resolved 2026-07-19. Snapshot cadence is set to per-session-close as the primary trigger, with a size-based safety valve that triggers mid-session snapshots if log sizes exceed a threshold.
* **T1-L-21 (High-Risk Override Design)**: [DECISION REQUIRED]
  * **Option A**: Build a replace-flag mechanism keeping the defaults. The config loader reads `override_defaults: true` under `high_risk_patterns` in `config.yaml` to bypass defaults.
  * **Option B**: Strip defaults down to genuinely language-neutral entries (e.g. `*/migrations/*`, `*/auth/*`, `*/security/*`) and remove the Python-idiom filenames entirely.
* **T1-K-13 (Human Signature Verification)**: [DECISION REQUIRED]
  * **Option A (Git identity)**: Validate the committing author against an authorized roster of developer usernames/emails using `git config user.name`/`user.email`.
  * **Option B (Session Token)**: Verify a unique signature token written in `session.json` by the initiating agent/human.
  * **Option C (Interactive Challenge)**: Prompt the committing operator interactively for verification.
