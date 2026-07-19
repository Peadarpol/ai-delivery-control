# SPEC-v1.4.10-governance-hardening

**Status**: DRAFT  
**Author**: Gemini (AI execution mode)  
**Feeds into**: Release v1.4.10  
**Tracked under**: `T1-K-12` / `T1-L-21` / `T1-K-13` / `T1-K-14` / `HIB-063` / `T1-L-20` / `HIB-ENV-02` / `T1-I-08` / `HIB-059` / `HIB-061` / `T1-E-04`

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
  - Unify `config.yaml` parsing across ~20 files behind a single `harness_utils.py` loader contract (`load_harness_config`, `get_harness_config`), replacing hand-rolled regex/line parsers and inconsistent `yaml.safe_load` calls, and fixing the latent `HIB-061` defect in `check_traceability.py`'s config resolution path (delivering `T1-E-04`).
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

### Scenario 4: Config resolution precedence is consistent across consumers
* **Given** a config file where an unrelated top-level `mode: ignore` key exists above the `outer_loop: {mode: strict}` block
* **When** `check_traceability.py`, `acceptance_hook.py`, and `check_spec.py` each resolve their mode
* **Then** all three return `strict` via the shared `get_harness_config()` path
* **And** no consumer falls back to its own regex parsing.

---

## 5. Proposed Changes

### Component: Governance & Risk
#### [MODIFY] [route_decision.py](file:///c:/projects/ai-delivery-control/src/scripts/route_decision.py)
- **T1-L-21 (`high_risk_patterns` override)**: Refactor `_load_high_risk_patterns()` to load the `override_defaults` boolean flag (default: false) from `.agent/config.yaml`.
  * If `override_defaults: true` -> return only the config-defined list, skipping merging with hardcoded GymBase defaults.
  * If `override_defaults: false` or absent -> return the merged list (additive merge of defaults + config).
  * Refactor `classify_commit_risk()` and `get_high_risk_files()` to consume the list returned by the loader directly instead of doing manual list prepending themselves.
- **T1-L-20 (decisions log schema)**: Research-only pass. No code or schema changes are introduced in this release.

#### [MODIFY] [pre-commit-config.yaml.template](file:///c:/projects/ai-delivery-control/bootstrap/templates/pre-commit-config.yaml.template) and [.agent/scripts/check_traceability.py](file:///c:/projects/ai-delivery-control/.agent/scripts/check_traceability.py)
- **T1-K-12 & T1-K-13 (pre-local-merge checks & --no-trace aggregator)**: Set up a shared blocking gate check running at a pre-merge/pre-push stage (e.g. at the `pre-commit` stage by verifying `.git/MERGE_HEAD` presence, or at `pre-push` stage to inspect local branch merge commits). This shared hook aggregates two checks:
  1. **T1-K-12 check**: Sensitive-path modifications require a human override.
  2. **T1-K-13 check**: The `--no-trace` merge-gate aggregator.
- **Minor Clean-up in [governance_check.py](file:///c:/projects/ai-delivery-control/.agent/scripts/governance_check.py)**: Remove the unreachable `print("✅ Governance check complete.")` statement in `check_commit_sequence` located after `return None` (line 130).

### Component: Configuration Loading (T1-E-04)
#### [MODIFY] [harness_utils.py](file:///c:/projects/ai-delivery-control/src/scripts/harness_utils.py)
- **DEFAULTS table**: Define a single dictionary of all harness config defaults. No call site redefines defaults locally.
- **Lazy imports**: The `import yaml` statement must be lazy and try/except-guarded inside loading functions, not at module top-level (required for the no-PyYAML test path to actually exercise the fallback).
- **load_yaml_with_fallback**: Implement `load_yaml_with_fallback(path) -> dict` as a generic YAML loader: no caching, no defaults — safe for non-config YAML consumers (e.g. `coupling_decisions.yaml`).
- **load_harness_config**: Implement `load_harness_config(config_path=None) -> dict` using `load_yaml_with_fallback` under the hood.
- **Caching Semantics**: Define a module-level `_config_cache` dict keyed by resolved path to parse the config once per process. Add `_reset_config_cache()` for test isolation.
- **get_harness_config**: Implement `get_harness_config(section=None, key=None, default=None) -> Any`. Precedence chain: User Config Value → DEFAULTS table → caller's explicit default= argument → None.
- **Fallback parser**: Implement an indentation-aware fallback parser supporting block scalars (`|` or `>`), extending the pattern in `bootstrap/migration_base.py:validate_yaml_config`. It must fail per-key with a logged warning (via `log_harness_event` + `stderr`), never silently defaulting the whole file.

#### [MODIFY] Regex-parser call sites (replace with `get_harness_config()`):
- **[acceptance_hook.py](file:///c:/projects/ai-delivery-control/src/scripts/acceptance_hook.py)**: `mode` and `specs_path` extraction.
- **[check_traceability.py](file:///c:/projects/ai-delivery-control/.agent/scripts/check_traceability.py)**: See overlap note below.
- **[acceptance_check.py](file:///c:/projects/ai-delivery-control/.agent/scripts/acceptance_check.py)**: Hand-rolled config reading loop.
- **[pm_scaffold.py](file:///c:/projects/ai-delivery-control/.agent/scripts/pm_scaffold.py)**: `get_specs_path()` regex logic.
- **[check_spec.py](file:///c:/projects/ai-delivery-control/.agent/scripts/check_spec.py)**: `_load_outer_loop_mode` and main logic.
- **[init_session.py](file:///c:/projects/ai-delivery-control/.agent/scripts/init_session.py)**: Regex loop parsing.
- **[route_decision.py](file:///c:/projects/ai-delivery-control/src/scripts/route_decision.py)**: `_load_adr_capability_mappings()` regex loop.

#### [MODIFY] Remaining yaml.safe_load callers (second commit, bulk classification pass):
- Audit `ai_review.py`, `wiki_compile.py`, `retention_cleanup.py`, `circuit_breaker.py`, `harness_health.py`, `session_health.py`, `onboarding.py`, `providers.py`, `roster_builder.py`, `co_change_reconciler.py`, `wiki_lint.py`.
- For `config.yaml` consumers: replace with `get_harness_config()` or `load_harness_config()`.
- For non-config.yaml consumers (e.g. `coupling_decisions.yaml` in `co_change_reconciler.py`): replace with `load_yaml_with_fallback()`.

### File-Overlap & Sequencing Risks
- **[check_traceability.py](file:///c:/projects/ai-delivery-control/.agent/scripts/check_traceability.py)**: Touched by both `T1-K-13.1` and `T1-E-04` in this same release. `T1-K-13.1` modifies the backlog-ID verification logic to check against `git show HEAD:...` rather than the working tree. `T1-E-04` modifies the same file's config-resolution logic (specs_path/mode reading) and adds the `_setup_sys_path` bootstrap import fix. These are different functions in the same file — implement and test `T1-K-13.1` first (it's already sequenced after `T1-L-21` per §6), then apply `T1-E-04`'s config-loader refactor on top, and re-run both test suites together before committing. Do not let one change clobber the other.
- **[ai_review.py](file:///c:/projects/ai-delivery-control/src/scripts/ai_review.py)**: Touched by both `T1-K-14` and `T1-E-04`'s bulk-refactor commit. `T1-K-14` changes fail-open verdict semantics; `T1-E-04` changes how it reads config. Same rule: sequence `T1-K-14` first, then apply the config-loader swap, then run the full test suite once more.

### Component: Requirement Traceability
#### [MODIFY] [init_session.py](file:///c:/projects/ai-delivery-control/.agent/scripts/init_session.py)
- **T1-K-13 (Session Signature)**: On interactive session start (stdin is a TTY), prompt the operator once for authorization confirmation. Write the following block to `session.json` (used for attribution):
  ```json
  "authorization": {
    "signed_by": "<git config user.name or explicit input>",
    "signed_at": "<ISO 8601 timestamp>",
    "session_id": "<session_id>"
  }
  ```
  On non-interactive session start, either omit this block or inherit it from a parent session if one exists (never fabricate a signer). This block is written once on init and is not re-verified per commit.

#### [MODIFY] [check_traceability.py](file:///c:/projects/ai-delivery-control/.agent/scripts/check_traceability.py)
- **T1-K-13.1 (backlog-ID verification hardening)**: Modify the ID verification loop to verify backlog references (such as `HIB-*`, `BUG-*`, or `T1-*`) against the committed document contents at `HEAD` (via `git show HEAD:docs/...` or equivalent) rather than reading directly from the working-tree files, preventing self-ratifying IDs introduced in the same commit.
- **HIB-061 / AT-06 (root commit exemption)**: Integrate mode-dependent exemption checks. Explicitly handle initial project root commits containing code files in incremental mode (where `git rev-parse --verify HEAD` fails due to no existing commits), allowing them to pass the gate safely while maintaining strict validation on all subsequent commits.

#### [MODIFY] Shared Blocking Hook (built with `T1-K-12`)
- **T1-K-13 (Merge-Gate --no-trace Aggregator)**:
  * On merge trigger, enumerate all commits being merged into target branch (`git log <target>..<source>`).
  * For each commit, check for the `--no-trace` bypass marker in the commit message or trailer.
  * For each match, pull the attribution block from that commit's session.json in history (`git show <commit>:.agent/session.json`) to extract `signed_by` and `session_id`.
  * If zero matches: merge proceeds.
  * If >=1 matches: block the merge and print a summary:
    ```
    BLOCKED: merge contains N commit(s) using --no-trace:
      - <sha> (session <session_id>, signed_by <signer>): "<commit message>"
      - ...
    Re-run with --ack-no-trace "<reason>" to proceed.
    ```
  * Permit the merge to proceed only if re-invoked with the explicit `--ack-no-trace "<reason>"` acknowledgment flag. Log the acknowledgment and reason to `harness_events.jsonl` as the audit record.

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
* **T1-K-13 Aggregator Dependency**: The `T1-K-13` merge-gate aggregator must be implemented using the same hook mechanism as `T1-K-12`. These must be built together, or sequence `T1-K-12` hook scaffolding first since the aggregator depends on it existing.
* **T1-E-04 Sequencing**: The core loader (harness_utils.py additions) has no dependency on other v1.4.10 work and can be implemented first, in parallel with T1-L-21. However, the two regex-replacement call sites in check_traceability.py and ai_review.py must be applied after T1-K-13.1 and T1-K-14 respectively are complete and tested, per the overlap note above.

---

## 7. Verification Plan

### Automated Tests
- Run consistency validator:
  `.venv/bin/python -m pytest tests/test_framework_consistency.py` (macOS/Linux) or `.venv\Scripts\python -m pytest tests/test_framework_consistency.py` (Windows)
- Run SQLite concurrency/locking safety suites:
  `.venv/bin/python -m pytest tests/test_session_health.py` (macOS/Linux) or `.venv\Scripts\python -m pytest tests/test_session_health.py` (Windows)

### Additional Verification Test Coverage (T1-E-04)
#### New tests/unit/test_config_loader.py:
- **Fallback Parity Test**: Parse `bootstrap/templates/config.yaml.template` and `.agent/config.yaml` using both `yaml.safe_load` and the fallback parser. Assert the resulting dictionaries are identical.
- **No-PyYAML Execution**: Monkeypatch `sys.modules["yaml"] = None` during test setup to explicitly verify the lazy import triggers `ImportError` and the fallback parser executes successfully in a clean environment.
- **Caching**: Verify `load_harness_config` hits the cache, is correctly keyed by path, and `_reset_config_cache` clears it.
- **Consumer Section Awareness (Scenario 4)**: Provide a config where an unrelated top-level `mode: ignore` exists above the `outer_loop: {mode: strict}` block. Test consumer behavior directly: Call the actual mode-resolution functions exported by `check_traceability.py`, `acceptance_hook.py`, and `check_spec.py` and verify they return `strict`.
- **Self-Enforcing Defaults Rule**: Add a static grep-style test ensuring no consumer calls `get_harness_config(..., default=X)` for a key that already exists in the `DEFAULTS` table.

### Additional Verification Test Coverage (T1-L-21 & T1-K-13)
* **Risk Classification Override (`T1-L-21`)**:
  * Config with `override_defaults: true` + custom pattern list -> verify GymBase defaults (unit_of_work.py, base_repository.py, etc.) are absent from the effective pattern set.
  * Config with `override_defaults: false` (or key omitted) -> verify defaults + config patterns are both present (regression test for current behavior).
  * Config with `override_defaults: true` + empty pattern list -> verify this raises a loud warning or fails-closed (fails loudly rather than silently disabling all risk classification).
* **Merge-Gate `--no-trace` Aggregator (`T1-K-13`)**:
  * Branch with zero `--no-trace` commits -> verify merge proceeds without prompts.
  * Branch with `--no-trace` commits -> verify merge is blocked, and correct commits, sessions, and signers are printed.
  * Merge retried with `--ack-no-trace "<reason>"` -> verify merge proceeds, and `harness_events.jsonl` contains the ack record with the reason.
  * Squash-merge scenario: verify the aggregator successfully catches and blocks on `--no-trace` commits pre-squash.

---

## 8. Resolved Decisions

* **HIB-063 (Audit-log snapshot cadence)**: Resolved 2026-07-19. Snapshot cadence is set to per-session-close as the primary trigger, with a size-based safety valve that triggers mid-session snapshots if log sizes exceed a threshold.
* **T1-L-21 (High-Risk Override Design)**: Resolved 2026-07-19. Option A is selected. The loader reads `override_defaults: true` under `high_risk_patterns` in `config.yaml` to bypass defaults and use user-defined lists only.
* **T1-K-13 (Human Signature Verification & Enforcement)**: Resolved 2026-07-19. The session signature is captured once at interactive session start for attribution only. The merge-gate aggregator enforces check trace integrity pre-merge, requiring an explicit `--ack-no-trace "<reason>"` bypass confirmation at merge time. Other alternatives (such as real-time token exchange) were rejected due to unnecessary developer friction relative to risk, since the merge-to-main boundary represents the true trust threshold.
* **T1-E-04 (Config Loader Design)**: Resolved prior to v1.4.10 folding. Fallback parser is indentation-aware with block-scalar support, extending bootstrap/migration_base.py's pattern. Precedence chain is User Config → DEFAULTS table → caller's explicit default= → None, with the DEFAULTS table strictly winning over caller-supplied defaults. Fails per-key with a logged warning, never silently drops the whole config.
