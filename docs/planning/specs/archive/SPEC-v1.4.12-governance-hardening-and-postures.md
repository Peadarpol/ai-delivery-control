# SPEC: Release v1.4.12 — Gate Enforcement Postures & Governance Hardening

**Status**: DELIVERED — multi-persona review reconciled & synchronized
**Author**: Gemini / Antigravity (planning & spec drafting) — Claude architecture review reconciled
**Tracked under**: `v1.4.12`
**Source Issue**: v1.4.12 Scope Handoff (Milestone v1.4.12)
**Related**: `T1-G-18` (Gate Enforcement Postures) 📋, `HIB-073` (Pathing Hardening) 📋, `HIB-074` (Provider Exception Logging) 📋, `HIB-076` (Traceability Self-Ratification Gap) 📋, `HIB-077` (Schema Drift Verification) 📋, `T1-B-14`–`17` (v1.4.11 Bookkeeping) 📋
**Changelog**:
- v1.0 (Gemini, 2026-07-24): Initial release specification draft.
- v1.1 (Gemini/Claude, 2026-07-24): Multi-persona review reconciliation & scenario synchronization (canonical JSON hashing, AST entry indexing & fast-path skip condition, shallow-clone lapse fallback, test-only TTY monkeypatching, POSTURE_EXPIRED_WARNING banner copy, H-series session-level conduct scoping, GateContext 1.x schema version compatibility, eval runner posture override, and provider error telemetry summary).

---

## 1. Goal & Context

Release **v1.4.12** is the strategic bridge between the adoption/usability hardening releases (v1.4.9.1, v1.4.10, v1.4.11) and the upcoming v1.5.x capability series (Quality Signal Maturity / Tool ABC).

While v1.4.11 closed silent onboarding failure modes for brand-new projects, **v1.4.12** equips the harness for **brownfield enterprise adoption**. Mature existing codebases pointed at the harness's gates often hit a wall of pre-existing architectural violations on day one. v1.4.12 delivers **`T1-G-18` (Gate Enforcement Postures)**, enabling projects to operate in `ratchet` posture (grandfathering pre-existing debt in `.agent/baseline.json` while enforcing zero new debt in touched files) or `observe` posture (time-bounded assessment mode).

Additionally, v1.4.12 hardens script pathing across 11 remaining tooling scripts (`HIB-073`), disambiguates local runtime crashes from network provider outages (`HIB-074`), closes the traceability self-ratification gap (`HIB-076`), and expands SQLite schema-drift auto-migration across all tables (`HIB-077`).

---

## 2. Bounded Scope & Out of Scope

### In-Scope (Committed Scope)

#### 1. Core Feature: Gate Enforcement Postures (`T1-G-18`)
* **Spec Restructuring (Step 0)**: `SPEC-enforcement-postures.md` restructured to pass `check_spec.py` Pass 1 (completed).
* **Phase P1 (Severity Map & Disposition Engine)**:
  * `src/scripts/posture.py`: Shared disposition engine implementing `disposition(finding, posture, baseline, overrides, invariants) -> Disposition`.
  * `architecture_checks.py`: Replace fragile substring matching with an explicit `rule -> severity` map (`LAYER_BOUNDARY: FAIL`, `HIGH_COUPLING: WARN`, `ASGI_LIFESPAN: WARN`, etc.) and add explicit tag `TYPE_CHECKING_CAST: WARN`.
  * Integration of `strict` and `observe` posture disposition.
* **Phase P2 (Baseline Manifest & Human-Only CLI)**:
  * `.agent/baseline.json`: Versioned baseline manifest storing normalized region SHA-256 hashes (`{ rule, file, region_sha256, first_seen }`) and a self-contained header checksum (`manifest_sha256`) computed over the `entries` array.
  * `.agent/scripts/baseline.py`: CLI (`init|refresh|report`). Refuses `init`/`refresh` execution when `AGENT_ID` is set in the environment or `sys.stdin.isatty()` is `False` (human-only baseline generation; convention-based defense-in-depth guard).
  * Self-contained SHA-256 tamper detection (`header.manifest_sha256` verification) and audit event logging (`BASELINE_GENERATED` / `BASELINE_TAMPER_SUSPECTED` -> fail-safe fallback to `strict`).
  * `ratchet` posture integration: Grandfather pre-existing findings; lapsing grandfather status when a file is touched ("you touch it, you own it").
* **Phase P3 (Review Engine & Invariant Floor)**:
  * `src/scripts/ai_review.py`: Apply posture disposition after calibration and intensity stages.
  * Invariant floor: H-series hard safety prohibitions (H-01 through H-09) are immune to all posture modulation, baseline entries, or calibration weights (always `BLOCK`).
  * `rebuttal.py`: Rebuttal requests against advisory findings rejected cleanly.
* **Phase P4 (Bypass Deprecation & Onboarding Integration)**:
  * Deprecate `.skip-ai-review` / `SKIP_AI_REVIEW=1` bypasses with visible warnings pointing to `enforcement.posture: observe`. Log `GATE_SKIPPED` with `deprecated_bypass: true`.
  * `bootstrap/install.py` & onboarding workflow: Guide brownfield setup (`observe` -> `baseline.py init` -> `ratchet`).

#### 2. Backlog Bookkeeping (`T1-B-14` through `T1-B-17`)
* Update status markers for `T1-B-14` (Onboarding target check / F-COLD-1), `T1-B-15` (Cross-platform venv template / F-COLD-2), `T1-B-16` (API key reachability / F-COLD-3), and `T1-B-17` (Stale Python warning / F-COLD-5) to `✅ (v1.4.11)` in `FRAMEWORK_BACKLOG.md`.

#### 3. Script Pathing Bootstrap Hardening (`HIB-073`)
* Refactor 11 remaining scripts/skills to locate `src/scripts/harness_utils.py` via depth-agnostic git-root discovery (`_find_project_root()`) rather than hardcoded parent counting, invoking `_setup_sys_path()` cleanly across both 2-deep and 5-deep script locations:
  `check_spec.py`, `circuit_breaker.py`, `co_change_core.py`, `co_change_reconciler.py`, `init_session.py`, `onboarding.py`, `wiki_compile.py`, `wiki_lint.py`, `repo_map.py`, `validate.py` (api-design skill), `harness_health.py`.

#### 4. Provider Local Exception Disambiguation (`HIB-074`)
* Refactor `ai_review.py` and `providers.py` error handling to separate local validation/runtime exceptions (e.g. `RuntimeError: Content too large`, `JSONDecodeError`) from genuine external network/API outages (`PROVIDER_ERROR` / HTTP 503). Write distinct audit event types (`review_local_error` vs `review_network_error`).

#### 5. Traceability Gate Self-Ratification Prevention (`HIB-076`)
* Update `check_traceability.py` to resolve referenced IDs against the pre-commit state (`HEAD`) of backlog/planning files, or explicitly exclude staged diff additions from the ID-existence scan, preventing a commit from self-ratifying a newly introduced ID (resolves incident `9d51019`).

#### 6. Comprehensive SQLite Schema Drift Auto-Migration (`HIB-077`)
* Extend `_ensure_schema()` in `src/scripts/state_persistence.py` to perform column-drift inspection (`PRAGMA table_info`) and `ALTER TABLE` auto-migration across all SQLite tables (`sessions`, `review_events`, `spec_acceptance`).

---

### Out-of-Scope (Non-Goals)
* `v1.5.0` Quality Signal Maturity items (recidivism tracking `T1-D-07`, complexity gate `T1-G-15`, plan grader `T1-L-11`).
* `v1.5.1` Tool ABC foundation (`T1-E-01`).
* Per-hunk baseline tracking (file-level scoping only per decision §7 D2).
* Automated burndown metric UI/dashboards (advisory event logging only).

---

## 3. Assumptions

* `[Resolved: .agent/config.yaml remains the single source of truth for posture configuration and source path resolution.]`
* `[Resolved: AGENT_ID environment variable is present during agent executions, enabling baseline.py's human-only guard to reject agent-driven baseline generation.]`
* `[Resolved: check_traceability.py ID validation can inspect HEAD (pre-commit) state via git show or exclude staged diff additions.]`
* `[Resolved: GATE_ADVISORY audit-log volume under a busy ratchet posture is tracked under HIB-078 to evaluate batching and rotation requirements if high advisory event volume occurs.]`

---

## 4. Acceptance Criteria

### Scenario 1: Posture Resolution and Fail-Safe Defaults (T1-G-18)
Given a project executing the pre-commit review gate or architectural checks
When `.agent/config.yaml` is missing, unparseable (YAML syntax error or schema validation failure), or specifies an unknown posture name
Then the posture engine (`src/scripts/posture.py`) resolves to `strict`
And all `FAIL`-severity findings block commit execution with exit code 1.

### Scenario 2: Baseline Grandfathering and File-Edit Lapsing in Ratchet Posture (T1-G-18)
Given a project configured with `enforcement.posture: ratchet` and a valid `.agent/baseline.json`
When code is committed without modifying any file listed in `.agent/baseline.json` (as determined by `git diff --name-only HEAD`, or `git diff --name-only HEAD^1` for merge commits; if a shallow clone `--depth=1` lacks parent commit history for `HEAD^1`, lapse re-verification is skipped gracefully with a `SHALLOW_CLONE_LAPSE_SKIPPED` advisory event)
Then existing violations in those files disposition to `GRANDFATHERED` and emit `GATE_ADVISORY` events without blocking exit code (with `posture.py` indexing entries into `dict[str, list[BaselineEntry]]` for $O(1)$ lookups and skipping AST parsing for touched files with zero baseline entries)
When code is committed that modifies a file listed in `.agent/baseline.json` (appearing in staged or working-tree changes relative to `HEAD`)
Then region hashes (computed over the innermost enclosing `FunctionDef`/`AsyncFunctionDef`/`ClassDef` AST node via `hashlib.sha256(ast.unparse(node).encode('utf-8'))`, with whole-file fallback for top-level code) for that touched file are re-evaluated against current content, stale hashes lapse, and any remaining `FAIL` findings in the touched file block execution.

### Scenario 3: Baseline Tamper Detection and Fallback (T1-G-18)
Given an existing `.agent/baseline.json` manifest file containing `header.manifest_sha256`
When `posture.py` computes the SHA-256 hash of the `entries` array using canonical JSON serialization (`json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")`) and compares it to `header.manifest_sha256`
Then if a mismatch is detected, the posture engine logs a `BASELINE_TAMPER_SUSPECTED` audit event in `harness_events.jsonl`
And treats `.agent/baseline.json` as absent, enforcing `strict` blocking dispositions without relying on untracked log history.

### Scenario 4: Human-Only Baseline Generation (T1-G-18)
Given an environment where `AGENT_ID` is set in environment variables or `sys.stdin.isatty()` is `False`
When `python .agent/scripts/baseline.py init` or `refresh` is executed
Then the script prints an error message ("Baseline generation is human-only") and exits with code 1 without modifying `.agent/baseline.json` (noting `AGENT_ID` + TTY check is a convention-based guard, not an unbypassable security boundary; unit tests in `test_baseline.py` exercise this path using test-only `monkeypatch.setattr(sys.stdin, "isatty", lambda: True)` without adding a public CLI override flag).

### Scenario 5: Observe Posture Disposition Behavior (T1-G-18)
Given a project configured with `enforcement.posture: observe` and `observe_expires` ISO 8601 UTC date string
When code is committed before the `observe_expires` date boundary
Then all findings disposition to `ADVISORY` and emit `GATE_ADVISORY` events with exit code 0
When `observe_expires` is missing, malformed, or past `datetime.now(timezone.utc)`
Then `posture.py` automatically resolves effective posture to `ratchet` and prints a `POSTURE_EXPIRED_WARNING` banner:
`⚠️  [POSTURE EXPIRED] 'observe' posture expired on <date> UTC. Resolved to 'ratchet'.`
`    👉 Action: Run 'python .agent/scripts/baseline.py init' or update observe_expires in .agent/config.yaml.`

### Scenario 6: Invariant Floor Immunity for Hard Safety Rules (T1-G-18)
Given a project configured with `enforcement.posture: observe` or `ratchet`
When a diff triggers an H-series prohibition rule (H-01 through H-09 per `AGENTS.md §4.1`)
Then the finding dispositions to `BLOCK` regardless of configured posture, baseline entries, or calibration weights (noting H-series rules represent session-level agent conduct and honesty rules, enforced independently via HALT and escalation protocols; diff-level security capabilities marked invariant are explicitly pinned in `posture.py`'s registry at the capability level).

### Scenario 7: Bypass File Deprecation (T1-G-18)
Given a repository containing a `.skip-ai-review` file or `SKIP_AI_REVIEW=1` environment variable
When the review gate executes
Then the gate prints a visible deprecation warning pointing to `enforcement.posture: observe`
And logs a `GATE_SKIPPED` event with `deprecated_bypass: true` (preparing full bypass retirement in milestone `v1.5.0`).

### Scenario 8: Dynamic Pathing Bootstrap Across 11 Target Scripts (HIB-073)
Given any of the 11 target scripts: `check_spec.py`, `circuit_breaker.py`, `co_change_core.py`, `co_change_reconciler.py`, `init_session.py`, `onboarding.py`, `wiki_compile.py`, `wiki_lint.py`, `repo_map.py`, `validate.py` (api-design), and `harness_health.py`
When executed from any directory level (2-deep `.agent/scripts/` or 5-deep `.agent/skills/universal/*/scripts/`)
Then the script locates `src/scripts/harness_utils.py` via depth-agnostic git-root discovery (`_find_project_root()`) rather than hardcoded relative parent-counting and invokes `_setup_sys_path()` cleanly without `ModuleNotFoundError`.

### Scenario 9: Disambiguated Provider Exceptions (HIB-074)
Given a local execution exception (e.g. `RuntimeError: Content too large`) during `ai_review.py`
When the review engine catches the exception
Then it emits `review_local_error` containing the Python `traceback.format_exc()` string in the event payload
And does NOT report `API unavailable` or `PROVIDER_ERROR` network failure messages.

### Scenario 10: Traceability Self-Ratification Prevention (HIB-076)
Given a commit referencing a new ID (e.g. `HIB-076`) in its commit message
When the ID is only present in the staged diff additions of that same commit and absent in `HEAD` (with root commit exemption verified via `is_root_commit()`)
Then `check_traceability.py` rejects the commit with a missing-ID error
And requires the ID to exist in `HEAD` prior to commit execution.

### Scenario 11: Multi-Table SQLite Schema Drift Migration (HIB-077)
Given an existing `harness.db` created under an older schema version
When `sync_session_to_db()` or schema initialization executes in `state_persistence.py`
Then `_ensure_schema()` inspects columns via `PRAGMA table_info(<table_name>)` across `sessions`, `review_events`, and `spec_acceptance`
And issues `ALTER TABLE` only for columns confirmed missing by the `PRAGMA` check, avoiding exception handling entirely.

---

## 5. Verification Plan

### Automated Tests
* `tests/unit/test_posture.py`: Characterization tests for posture resolution, disposition pipeline, baseline region hash matching, tamper detection, and invariant floor immunity.
* `tests/unit/test_baseline.py`: Unit tests for `baseline.py` CLI modes (`init`, `refresh`, `report`), `AGENT_ID` + TTY guard, and SHA-256 manifest hash calculation.
* `tests/unit/test_check_traceability.py`: Unit tests verifying pre-commit `HEAD` ID resolution and prevention of self-ratifying staged diff IDs (`HIB-076`).
* `tests/unit/test_state_persistence.py`: Unit tests verifying multi-table schema drift auto-migration across `sessions`, `review_events`, and `spec_acceptance` (`HIB-077`).
* `tests/unit/test_providers.py`: Unit tests for provider error disambiguation (`HIB-074`).
* `tests/e2e/run_e2e_verification.py`: Full end-to-end verification run across all 29 E2E verification scenarios.
  * **Evaluation Posture Protection**: Benchmark and test harness runners must force `enforcement.posture: strict` (e.g. `--posture=strict`), ignoring repository config to prevent relaxed postures from skewing benchmark results.
  * **Telemetry Summary**: `run_e2e_verification.py` report output must summarize and report `review_local_error` vs `review_network_error` event counts (`HIB-074`).

### Manual Verification
* Execute `baseline.py init` on GymBase or reference brownfield codebase to generate `.agent/baseline.json`.
* Commit a clean change in `ratchet` posture verifying zero blocking violations on untouched files.
* Modify a grandfathered file in `ratchet` posture verifying that touch invalidates baseline region hash and enforces gate clearance.
