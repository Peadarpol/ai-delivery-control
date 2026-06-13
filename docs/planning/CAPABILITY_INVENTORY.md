# AI Delivery Control — Capability Inventory

**Generated**: 2026-06-13
**Framework Version**: 1.4.0 (current as of inventory date)
**Purpose**: Strategic review inventory. Cards reflect what the code actually does, not what the documentation intends. Discrepancies between documentation and implementation are called out explicitly.

---

## Gate Layer

---
## AI Adversarial Review Gate (`ai_review.py`)
**Delivered**: v1.0.0 (2026-05-21); significantly enhanced through v1.1.5.2
**Primary files**:
- `src/scripts/ai_review.py` — gate entry point and orchestrator (framework source, copied to `src/scripts/` of target project on install)
- `src/scripts/providers.py` — LLM provider abstraction (T1-E-02)
- `.ai-review-log.jsonl` — verdict audit trail (root of target project)

**What it does**: Fires as a pre-commit hook (`commit-msg` stage via `.pre-commit-config.yaml`). Reads the staged diff, loads a two-layer review context (universal + project), injects a PageRank repo map and prioritised ADR wiki pages, builds a `RouteDecision` describing which capabilities are active, shuffles diff hunks to counter positional bias, calls the configured LLM provider with an adversarial system prompt, parses the response into a typed `ReviewVerdict` Pydantic model, and blocks the commit on `FAIL` or allows it on `PASS`/`WARN`. All verdicts are appended to `.ai-review-log.jsonl`.

**What it prevents**:
- Ungoverned AI code landing in the repository: every commit passes an independent adversarial reviewer that has no access to the writing agent's reasoning
- Silent capability skipping: policy notes printed at every review explain which of TRANSACTIONAL_INTEGRITY, BRANCH_ISOLATION, MASS_ASSIGNMENT, RBAC, MIGRATIONS, CLEAN_ARCH were active and which were skipped with their reasons
- Token surprise on oversized diffs: skips review entirely (fail-open) above 5,000 lines / 200,000 chars rather than truncating (partial diffs cause hallucination)
- API-unavailable bypass on high-risk commits: if the provider is unavailable and the commit touches `*/migrations/*`, `*/auth/*`, `*/rbac/*`, `*/permissions/*`, `unit_of_work.py`, `base_repository.py`, `models.py`, or `branch_isolation`/`authentication`/`schema_hardening` ADR domains, the gate fails closed rather than open
- Malformed LLM responses: `ReviewVerdict` Pydantic validation at parse time raises a typed error rather than silently passing a structurally invalid verdict
- Token cost on trivial changes: pre-flight shortcut (`check_preflight_shortcut`) returns `PASS_FAST` with zero LLM calls for documentation-only (`.md`, `.rst`, `.txt`) and whitespace/comment-only diffs
- Untracked false positives: the rebuttal protocol provides a governed `--rebuttal` path for contesting specific FAIL findings; accepted rebuttals feed `false_positive_to_eval.py`

**How it integrates**:
- Called by: `.pre-commit-config.yaml` as the final hook at `commit-msg` stage
- Calls: `providers.py::get_provider()`, `repo_map.py::generate_repo_map()` / `get_pagerank_scores()`, `wiki_compile.py::DOMAIN_REGISTRY`, `architecture_checks.py::extract_adr_annotations()`, `co_change_check.py::run_co_change_estimator()`, `gate_context.py::load_gate_context()` / `write_gate_context()` (T1-G-13), `capability_calibration.py::get_calibrated_weight()` / `update_calibration_rebuttal()` (T1-G-14)
- Reads: `review_context_universal.md`, `review_context_project.md`, `.agent/config.yaml` (ADR mappings, high-risk patterns, large diff threshold), `.agent/wiki/` domain pages, `.agent/state/session.json` (for session_id in audit records), `.agent/state/gate_context_current.json` (if present — T1-G-13), `.agent/state/capability_calibration.json` (T1-G-14)
- Writes: `.ai-review-log.jsonl` (typed verdict log), `.agent/state/harness_events.jsonl` (high-risk gate events), `.agent/state/gate_rebuttal.json` (rebuttal input, when `--rebuttal` mode used), `rebuttal_pass.json` (one-time bypass token on accepted rebuttal), `.agent/state/gate_context_current.json` (updated with verdict and evidence — T1-G-13), `.agent/state/capability_calibration.json` (rebuttal counter updates — T1-G-14), `~/.aisdlc/harness.db` (review event row, best-effort — T1-D-01)

**Current limitations**:
- `RouteDecision` class has a docstring "Stub for T1-G-01 capability routing — forward-compatibility only" despite `build_route_decision()` being fully implemented — misleading comment surviving from an earlier draft
- Path-based routing in `build_route_decision()` is hard-coded to GymBase directory conventions (`src/infrastructure/database/repositories/`, `src/application/services/`, etc.); a generic install will not trigger TRANSACTIONAL_INTEGRITY or BRANCH_ISOLATION unless the project happens to share those paths or uses the `# ADR:` annotation
- `_persist_verdict()` file locking resolved: T1-N-02 ✅ v1.3.1 — `_lock_file` context manager wired into the append site in `ai-review-log.jsonl`
- Co-change estimator (`T1-H-03`) result is injected only if HIGH-confidence warnings exist; MEDIUM-confidence warnings are printed to console but not injected into the LLM context
- The test project copy was previously out-of-sync; now dynamically synchronized by the E2E verification test runner at runtime to prevent version drift.

**Backlog dependencies**:
- T1-G-05: Restricted globals sandbox for `eval_runner.py` — ⬜ undelivered
- T1-G-06: Rebuttal protocol — ✅ delivered; E2E test project synced (BUG-13 ✅ pre-sprint 2026-06-02)
- T1-G-07: Structured SKIP_REASON enforcement — ✅ delivered
- T1-G-08: Diff size review strategy — ✅ delivered
- T1-G-09: User-facing rigor profile system — ⬜ undelivered
- T1-G-11: Evidence gathering (pytest_collect_status, todo_delta injected into LLM context) — ✅ v1.4.0
- T1-G-13: GateContext shared typed object wiring arch findings into LLM call — ✅ v1.4.0
- T1-G-14: Capability calibration (AT9, per-capability TP/FP weight adjustment) — ✅ v1.4.0
- T1-H-10: EXTRACTED/INFERRED/AMBIGUOUS confidence tiers for co-change warnings — ✅ v1.4.0
- T1-I-07: Token counter wiring — ✅ completed pre-sprint 2026-06-02; `ai_review.py` now increments `session.json` token counters after each LLM call
- T1-N-02: Gate concurrent write safety — ✅ v1.3.1
- T1-N-06: `pause_turn` stop reason handling — ⬜ undelivered

---
## Gate Context (`gate_context.py`)
**Delivered**: v1.4.0 (2026-06-13) — T1-G-13
**Primary files**:
- `src/scripts/gate_context.py` — `GateContext` Pydantic schema and atomic read/write utilities
- `.agent/state/gate_context_current.json` — runtime state file (gitignored)

**What it does**: Defines `GateContext`, a Pydantic typed object that acts as a shared data bus across the pre-commit hook chain. `architecture_checks.py` populates `arch_violations` and `adr_domains`; `co_change_check.py` (via `ai_review.py`) populates `co_change_warnings` with EXTRACTED/INFERRED/AMBIGUOUS tiers (T1-H-10); `ai_review.py` populates `pytest_collect_status` (T1-G-11 evidence), `todo_delta` (T1-G-11 evidence), `review_intensity`, `pagerank_scores`, `route_decision`, and `verdict`. Before the LLM call, `ai_review.py` calls `build_deterministic_findings_section(gate_context)` to prepend a verified findings block to the prompt — architecture violations and high-confidence co-change warnings that the LLM sees unconditionally regardless of diff heuristics. Writes are atomic (`.tmp` + `os.replace()`). Schema version `"1.0"` is checked on load; mismatches degrade gracefully.

**Degradation contract**: If `gate_context_current.json` is absent, malformed, has a schema version mismatch, or has a diff-hash mismatch with the current commit, `ai_review.py` falls back to standalone behaviour (constructs an empty `GateContext` from the diff in memory) and logs a harness event.

**What it prevents**:
- Architecture violations escaping into LLM review silently: `arch_violations` become a deterministic "pre-LLM, verified" section the model sees unconditionally
- Stale context bleed: diff-hash comparison (`gate_context.diff_hash != current_diff_hash`) rejects a context written for a previous commit
- Two independent failure reports with no shared trace: architecture checks and AI review now share a single `gate_context_current.json` record

**How it integrates**:
- Written by: `architecture_checks.py` (arch_violations, adr_domains — written as early hook stage), `ai_review.py` (all remaining fields — updated at commit-msg stage)
- Read by: `ai_review.py` (loaded at startup; `build_deterministic_findings_section()` consumes arch_violations, co_change_warnings, pytest_collect_status, todo_delta, review_intensity)
- File: `.agent/state/gate_context_current.json` (gitignored)

**Current limitations**:
- `architecture_checks.py` must write `gate_context_current.json` as a pre-commit hook stage file that persists until the commit-msg stage in the same git operation — works on local machines but not in ephemeral CI containers where hook stages run in separate disposable environments
- Not session-scoped: overwritten on every commit. A parallel `git commit` from a second terminal would corrupt the context for both operations
- `review_intensity` field in the context is populated by `ai_review.py` after `build_route_decision()` runs; earlier hook stages (architecture checks, repo map) always see `review_intensity: "standard"` on whatever partial context was written before the commit-msg stage

**Backlog dependencies**:
- T1-G-11: Evidence gathering — ✅ v1.4.0
- T1-G-13: GateContext shared typed object — ✅ v1.4.0

---
## Capability Calibration (`capability_calibration.py`)
**Delivered**: v1.4.0 (2026-06-13) — T1-G-14
**Primary files**:
- `src/scripts/capability_calibration.py` — calibration data access layer
- `.agent/state/capability_calibration.json` — per-capability TP/FP counters and weights (gitignored)

**What it does**: Maintains a per-capability (concern label) calibration state that adjusts issue severity based on the project's historical false-positive rate. Each capability entry tracks `tp` (true positive count), `fp` (false positive count), and `weight` (float, clamped to [0.5, 1.5]). Weight starts at 1.0 and decays 10% per accepted rebuttal (REBUTTAL_ACCEPTED — false positive confirmed) or grows 5% per rejected rebuttal or uncontested finding. `ai_review.py` reads calibrated weights at review time and downgrades HIGH-severity issues when a capability's weight falls below a threshold; low-weight capabilities are flagged in `route_decision.policy_notes`. `update_calibration_rebuttal()` is called at the end of each rebuttal session. `get_calibrated_weight()` respects `capability_calibration.enabled` and `capability_calibration.overrides` from `.agent/config.yaml`, allowing manual weight locks. File writes are atomic (`.tmp` + `os.rename()`). `load_calibration()` and `save_calibration()` degrade gracefully on any file error.

**What it prevents**:
- Capability-level alert fatigue: a capability repeatedly generating accepted rebuttals automatically softens to MEDIUM, preventing blocking FAILs on known-noisy checks
- Permanent silencing: weight is clamped at 0.5, so a capability can be dampened but not fully disabled by calibration alone (requires explicit `overrides` in config)
- Manual override loss: `overrides` in `config.yaml` take precedence over the learned weight, allowing permanent weight pins regardless of history

**How it integrates**:
- Called by: `ai_review.py` (reads `get_calibrated_weight()` per-capability at review time; calls `update_calibration_rebuttal()` after each rebuttal session verdict)
- Reads/writes: `.agent/state/capability_calibration.json`
- Config: `capability_calibration:` block in `.agent/config.yaml` (`enabled`, `overrides` dict)

**Current limitations**:
- Calibration state is per-project, not global: the same noisy capability in every project accumulates independent weights; no cross-project convergence
- No minimum-count guard: a single accepted rebuttal on a brand-new capability immediately reduces its weight to 0.9, which may be premature on day one
- Dream phase (`distill_dream.py`) is unaware of calibration weights — a proposal for a capability with weight 0.5 generates the same proposal text as one with weight 1.5

**Backlog dependencies**:
- T1-G-14: Capability calibration (AT9) — ✅ v1.4.0

---
## Architecture Boundary Checks (`architecture_checks.py`)
**Delivered**: v1.0.0 (2026-05-21)
**Primary files**:
- `.agent/skills/universal/senior-architect/scripts/architecture_checks.py` — check engine and AST visitor
- `.agent/config.yaml` — all rules are loaded from `architecture_checks:` section

**What it does**: Runs as a pre-commit hook, reading layer boundary rules and forbidden pattern rules from `.agent/config.yaml`. Uses Python's `ast` module to parse each `.py` file under the configured layer paths and detects imports that cross forbidden layer boundaries via `LayerViolationVisitor`. Also runs regex-based `check_forbidden_patterns()` against configured path/pattern pairs. Additionally implements `extract_adr_annotations()` which scans source files for `# ADR: domain_name` comments, used by `ai_review.py` for ADR-aware routing. Falls back to a custom zero-dependency YAML parser (`parse_yaml_fallback`) if PyYAML is not installed.

**What it prevents**:
- Domain layer importing infrastructure layer modules (the Clean Architecture violation that the gate's system prompt discusses)
- Specific forbidden code patterns (configured per project) appearing in designated paths — e.g., raw `os.environ` access in domain code, direct `db.session` calls outside the repository pattern
- Layer boundary drift going undetected: failures block the commit with specific `file:line` citations

**How it integrates**:
- Called by: `.pre-commit-config.yaml` hook (separate entry from the AI review gate, runs earlier in the chain)
- Called by: `ai_review.py::build_route_decision()` (for ADR domain extraction), `ai_review.py::get_adr_context()` (same)
- Reads: `.agent/config.yaml` (all rules), project source files via `rglob("*.py")`
- Writes: nothing — returns violation strings to the pre-commit framework, which prints them and exits non-zero

**Current limitations**:
- Checks are skipped entirely if `.agent/config.yaml` is absent or if the `architecture_checks:` section is empty — there is no zero-config default ruleset applied to a fresh install
- `extract_adr_annotations()` uses a regex scan of the raw file text, not AST; comments embedded in strings would be falsely matched (low practical risk)
- The playwright locator check (`check_playwright_locators`) handles a very specific GymBase testing concern and is likely irrelevant to most installs; there's no config-driven way to disable it without modifying the script
- No check for whether the configured `path` values in `layers:` or `forbidden_patterns:` actually exist in the target project; silently skips missing paths

**Backlog dependencies**: None currently — all planned enhancements are in the ADR/wiki injection layer (T1-H-02 ✅) rather than in the check engine itself.

---
## Repository Identity Guard (P-14)
**Delivered**: v1.0.0 (2026-05-21); governance document P-14
**Primary files**:
- `.agent/scripts/check_repo.py` — single-file enforcement script
- `tests/e2e/test_project/.agent/AGENTS.md` — step 0 instruction ("Run `python .agent/scripts/check_repo.py` before reading any files")

**What it does**: Calls `git remote get-url origin`, extracts the repository name from the URL (handles both HTTPS and SSH formats), and compares it case-insensitively against a hardcoded `EXPECTED_REPO` constant that is set to the target project's name at install time. On mismatch, prints a prominent error and exits with code 1. On success, prints a confirmation line.

**What it prevents**:
- The failure mode where an agent working across multiple terminal windows or IDE instances executes git operations (add, commit, push) against the wrong repository — a consequence of agent context surviving across IDE project switches
- The specific version of this problem that appears when Claude Code or Gemini CLI hold session state while the developer manually switches directories

**How it integrates**:
- Called by: AGENTS.md session startup protocol (Step 0, mandatory) — convention only, no automation
- Called by: No pre-commit hook; no automation; no enforcement mechanism beyond the convention text
- Reads: Git remote URL via subprocess
- Writes: nothing

**Current limitations**:
- The guard is entirely convention-based. There is no pre-commit hook for `check_repo.py`. An agent that skips Step 0 (which is common when agents are given tasks without explicitly running `init_session.py` first) gets no protection
- The check inspects the remote URL, not the working directory path. A repository with a different name pointing to the same remote would pass; a local-only repository with no remote configured triggers the "no remote 'origin' found" warning and proceeds (does not block)
- `EXPECTED_REPO` is hardcoded in the script at `"ai-delivery-control"` in the framework's own copy; in a target project install, `install.py` substitutes the project name — but no test validates that this substitution actually occurs during install
- The ROADMAP marks this as "Hard / Blocks git operations in wrong repo" which is aspirationally correct (exit code 1) but the table entry is misleading since there is no hook enforcement; it only blocks if the agent voluntarily runs the script

**Backlog dependencies**:
- T1-N-01 would add `parent_session_id` to session schema, but doesn't address the identity guard's convention gap
- T1-J-01 (automatic session-start checkpoint) creates a git stash automatically at startup, which implicitly confirms the active repo is git-accessible

---

## Session Lifecycle

---
## Session Initialisation (`init_session.py`)
**Delivered**: v1.0.0 (2026-05-21); T1-C-01 and T1-I-03 added in v1.1.5; automatic checkpoint added in v1.3.4 (T1-J-01)
**Primary files**:
- `.agent/scripts/init_session.py` — single script, all session lifecycle logic
- `src/scripts/harness_utils.py` — provides `_lock_session()`, `log_harness_event()`, `_setup_sys_path()`

**What it does**: On each invocation (agent session startup), `main()` performs four steps in sequence: (1) `infer_and_close_previous_session()` — inspects the previous session's `session.json`, cross-references git log and `.ai-review-log.jsonl` and `harness_events.jsonl` to infer an outcome (success / partial / abandoned / escalated), writes the result to `session_ledger.jsonl`, and updates `session.json` to `COMPLETED`; (2) `orient_agent()` — prints a high-visibility GFM Alert block based on the inferred outcome (SUCCESS: NOTE, PARTIAL: IMPORTANT, ABANDONED: WARNING, ESCALATED: CAUTION); (3) `initialize_session()` — generates a new UUID session_id, timestamps, classifies task magnitude (micro/standard/major) from branch name and file state, clears any stale token-budget HALT, writes a fresh `session.json`; (4) checks whether to run dream phase, wiki compile, and wiki lint as background subprocesses (each with its own 7- or 14-day cooldown state file).

**What it prevents**:
- Session data loss from agent crash or context exhaustion: even if the previous session had no explicit close protocol, the retrospective inference reconstructs an outcome from objective filesystem state
- "Starting fresh" when open tasks remain: PARTIAL orientation explicitly surfaces the count of open tasks from `active_context.md`
- Token budget surprise: initialises the `token_usage` counter in `session.json` at zero so the budget enforcement subsystem has a clean baseline
- Spec-only session misclassification: detects when spec files were modified (even with no commits) and does not automatically classify the session as `abandoned`
- Dream phase trigger on sparse data: thresholds gate the dream phase (minimum 15 sessions, 14-day span) to prevent noise from low-data periods
- AST-based staleness detection (T1-I-04 ✅ v1.3.1): scans `review_context_universal.md` and `review_context_project.md` for referenced code patterns and verifies they still exist in `src/`, outputting a warning card for any stale rules

**How it integrates**:
- Called by: AGENTS.md session startup protocol (Step 0), business-analyst.md Phase 0, and feature-implementation.md Phase 0 by convention; `--post-commit` mode called by the post-commit hook in `.pre-commit-config.yaml`
- Calls: `distill_dream.py` (subprocess), `wiki_compile.py` (subprocess), `wiki_lint.py` (subprocess), `state_persistence.sync_session_to_db()` (best-effort optional import — T1-D-01)
- Reads: `session.json`, `session_ledger.jsonl`, `.ai-review-log.jsonl`, `harness_events.jsonl`, `active_context.md`, `.agent/state/dream_phase_state.json`, `.agent/state/wiki_compile_state.json`, `.agent/state/wiki_lint_state.json`, `.agent/config.yaml` (for specs_path)
- Writes: `session.json` (new session or COMPLETED update), `session_ledger.jsonl` (one entry per closed session), `~/.aisdlc/harness.db` (session row, best-effort — T1-D-01)

**Current limitations**:
- `_should_skip_background_tasks()` reads `task_magnitude == "micro"` from the previous session's `session.json` — it reads the stale previous session data, not the newly initialized one, which creates a one-session lag in the skip logic
- Task magnitude classification uses branch name regex patterns that are GymBase-specific (`hotfix/`, `fix/doc`, `rfc/`, `migration/`); projects with different branching conventions will classify most sessions as `standard` regardless of actual complexity
- The `spec_files_modified` check uses file mtime, which is timezone-naive on Windows; a small window of false negatives exists if the session start time and file modification time span a DST boundary
- `dream_phase_state.json` tracks only `last_run_utc` — `proposals_generated`, `proposals_written`, `contradictions_found`, and `unrouted_patterns` are in the backlog spec but NOT written to the file; the one-line summary printed to the agent is therefore always generic
- No `--stop-hook` mode (mentioned in T1-C-01 backlog as "Claude Code optional enhancement"); outcome is always inferred retrospectively rather than written on session end

**Backlog dependencies**:
- T1-C-01 post-commit heartbeat — ✅ delivered (--post-commit mode)
- T1-I-02 token budget tracking — ✅ delivered (token_usage initialised)
- T1-I-04 AST staleness detection — ✅ v1.3.1
- T1-I-07 session token budget WARN/HALT — ✅ delivered (via check_halt.py); wiring to session.json completed pre-sprint 2026-06-02
- T1-J-01 automatic checkpoint — ✅ delivered (v1.3.4) (creates a git stash automatically at startup in `init_session.py`)
- T1-N-01 multi-agent session hierarchy schema — ⬜ undelivered (parent_session_id not in session.json)

---
## Session State (`session.json` schema)
**Delivered**: v1.0.0 (2026-05-21); token_usage and task_magnitude fields added in v1.1.5
**Primary files**:
- `.agent/state/session.json` — state file, gitignored (enforced since v1.2.0.1)
- `.agent/scripts/init_session.py` — sole writer for session creation and close
- `src/scripts/harness_utils.py` — provides `_lock_session()` used by all writers

**What it does**: A single JSON file holding the current session's identity and running counters. Written atomically within a file lock (`_lock_session` uses `fcntl.flock` on POSIX, `msvcrt.locking` on Windows). Read by multiple framework scripts to obtain `session_id` for audit trail correlation.

**Schema (all fields)**:
- `session_id` — UUID v4, unique per session, used as foreign key in `session_ledger.jsonl`, `harness_events.jsonl`, `.ai-review-log.jsonl`
- `start_time` — ISO 8601 UTC timestamp of session initialisation
- `last_activity` — ISO 8601 UTC timestamp, updated by `--post-commit` heartbeat
- `status` — `"ACTIVE"` or `"COMPLETED"`
- `agent` — agent identifier string (from `--agent` CLI arg or `AGENT_ID` env var, defaults to `"Harness"`)
- `task_magnitude` — `"micro"` | `"standard"` | `"major"` (auto-classified or agent_override)
- `task_magnitude_source` — `"auto"` | `"agent_override"` (persists override across session reinit)
- `token_usage` — dict with 8 integer fields: `input_tokens`, `output_tokens`, `reasoning_tokens`, `cache_read_input_tokens`, `context_load_estimated_tokens`, `repo_map_estimated_tokens`, `adr_injection_estimated_tokens`, `call_count`
- `outcome_override` — (optional) written by agents at close; read by `infer_and_close_previous_session()` to short-circuit inference
- `outcome_override_source` — (optional) e.g., `"business_analyst"`
- `outcome_override_note` — (optional) free text

**What writes to it**: `init_session.py` (create and close), `check_spec.py` (token_usage increment), pre-commit heartbeat (`--post-commit` mode)
**What reads it**: `check_halt.py` (session_id for bypass audit), `ai_review.py` (session_id for verdict log), `check_spec.py` (token_usage), `distill_dream.py` (session context), `init_session.py` (previous session inference)

**What happens if absent**:
- `check_halt.py`: proceeds without session_id in audit records
- `ai_review.py`: proceeds without session_id in verdict records
- `init_session.py`: treats as first-ever session, skips infer/close step
- `check_spec.py`: skips token budget update (silent failure, no block)
- `bootstrap/validate.py`: emits `WARN` (not ERROR) since v1.2.0.1

**Current limitations**:
- `parent_session_id` and `agent_role` (T1-N-01) are not yet fields in the schema

**Backlog dependencies**:
- T1-I-02: token budget tracking — ✅ delivered (real-time updates and retrospective aggregation work)
- T1-N-01: multi-agent session hierarchy schema — ⬜ undelivered

---
## HALT Sentinel (`check_halt.py`)
**Delivered**: v1.0.0 (2026-05-21); token budget HALT differentiation added v1.1.5
**Primary files**:
- `.agent/scripts/check_halt.py` — sentinel check script
- `.agent/state/HALT` — sentinel file (gitignored since v1.2.0.1)

**What it does**: Reads `.agent/state/HALT`. If the file exists, parses it as JSON to extract `reason` and `message`. If `reason == "token_budget_exhausted"`: checks `BYPASS_HALT_REASON` env var — if present, logs a bypass event to `harness_events.jsonl` and exits 0; otherwise prints the token exhaustion message and exits 2. All other reasons (governance violations): prints the message and exits 2 unconditionally (no bypass path). If HALT is absent: exits 0 silently.

**How HALT is written**: The HALT file uses atomic writes via `.tmp` + `os.replace()` (from v1.1.5 CHANGELOG). The token budget HALT reason and governance violation HALT reason are the two supported `reason` values.
**Where it is checked**: AGENTS.md session startup (Step 0, mandatory convention). Also noted as a check in the pre-commit hook flow in T1-N-03 notes.
**What happens when it fires**: Exit code 2 blocks the session start; exit code 2 from a pre-commit hook would block the commit.

**Current limitations**:
- Pre-commit hook wiring: ✅ resolved (BUG-15 ✅ v1.3.1) — `check_halt.py` registered as a `pre-commit` stage hook with `fail_fast: true`. HALT is now enforced at every commit boundary, not just session startup
- T1-N-03 (HALT sentinel subagent propagation) is explicitly limited to same-machine subagents via the pre-commit hook — now wired (BUG-15), but multi-machine propagation remains T1-N-03
- The BYPASS_HALT_REASON escape is available for `token_budget_exhausted` only; governance violation HALTs are genuinely unbypassable, which is intentional

**Backlog dependencies**:
- T1-I-07: session token budget WARN/HALT — ✅ delivered; wiring completed pre-sprint 2026-06-02
- BUG-15: check_halt.py pre-commit hook — ✅ v1.3.1
- T1-N-03: HALT sentinel subagent propagation — ⬜ undelivered

---

## Memory and Audit

---
## `harness_events.jsonl`
**Delivered**: v1.0.0 (2026-05-21); unified schema formalised in v1.1.5
**Primary files**: `.agent/state/harness_events.jsonl` — the event log (committed, not gitignored)

**Schema** (each line is a JSON object):
- `schema_version` — `"1.0"`
- `event_type` — typed string (examples: `commit_made`, `halt_bypass`, `high_risk_gate_closed`, `high_risk_gate_override`, `gate_bypass`, `spec_quality_check`)
- `timestamp_utc` — ISO 8601 UTC string with trailing `Z`
- `session_id` — from `session.json`, nullable
- `commit_sha` — nullable (populated by heartbeat on commit events, null for gate events)
- `agent` — string (from `AGENT_ID` env var or script-specific default like `"ai_review"`, `"check_halt"`, `"git_hook"`)
- `severity` — `"INFO"` | `"WARNING"` | `"HIGH"` | `"ERROR"` | `"CRITICAL"` (all caps — casing normalized in v1.3.3 via HIB-FM8-01)
- `payload` — arbitrary dict, content varies by event_type

**What writes to it**: `ai_review.py` (high-risk gate events, gate bypass events), `check_halt.py` (halt bypass events), `init_session.py` (commit_made heartbeat), `check_spec.py` (spec_quality_check events)
**What reads it**: `init_session.py::infer_and_close_previous_session()` (looks for `halt_event` or `severity == "critical"` to classify escalated outcomes), `init_session.py::maybe_run_dream_phase()` (looks for critical events since last dream phase run to trigger bypass), `distill_dream.py` (primary input for pattern aggregation)

**Retention**: The file is committed to version control (explicitly excluded from the gitignore block since v1.2.0.1). No automated retention/archival is implemented (T1-I-06 is undelivered).

**Current fragmentation state**: ✅ RESOLVED v1.3.1. T1-I-00a consolidation delivered — `circuit_breaker.py` (confirmed as the single caller of `audit_logger.py` via grep 2026-06-03) now routes events to `harness_events.jsonl` via `harness_utils.py` logging helpers. T1-I-00b (audit `audit_logger.py` wiring) also closed — single caller confirmed. T1-N-07 event_type alignment between `circuit_breaker.py` and `skill_ownership.yaml` verified and corrected ✅ v1.3.1.

**Current limitations**:
- Severity casing normalized in v1.3.3 (HIB-FM8-01). The dream phase parser maps all severity values to uppercase, ensuring bypass checks for `"CRITICAL"` events trigger reliably.
- No schema validation on write — any dict can be appended; schema_version is hardcoded `"1.0"` in all writers but never validated on read
- Concurrent write safety — ✅ resolved (T1-N-02 ✅ v1.3.1 — `_lock_file` context manager wired into append site)

**Backlog dependencies**:
- T1-I-00a: consolidate governance_audit.jsonl + audit_trail.jsonl — ✅ v1.3.1
- T1-I-00b: audit audit_logger.py wiring — ✅ v1.3.1
- T1-I-06: memory retention policy — ⬜ undelivered
- T1-N-02: concurrent write safety — ✅ v1.3.1
- T1-N-07: event_type alignment — ✅ v1.3.1

---
## `ai-review-log.jsonl`
**Delivered**: v1.0.0 (2026-05-21); PASS/PASS_FAST logging fixed in BUG-04 (v1.1.0); typed ReviewVerdict serialisation added v1.1.0
**Primary files**: `.ai-review-log.jsonl` — verdict log at the project root (committed)

**Schema** (typed path via `ReviewVerdict.model_dump()` + envelope fields):
- `timestamp` — ISO 8601 local time (note: NOT UTC — different from `harness_events.jsonl`)
- `verdict` — `"PASS"` | `"WARN"` | `"FAIL"` | `"FAIL_OPEN"` | `"PASS_FAST"` | `"REBUTTAL_ACCEPTED"` | `"REBUTTAL_REJECTED"`
- `blocking_concern` — nullable, populated on FAIL
- `model` — model name string (or `"preflight"` for PASS_FAST)
- `verdict_tier` — `"cloud"` | `"local"` | `"preflight"`
- `context_snapshot` — string summarising active context sections, ADR domains, repo map size, and high-risk classification (populated on FAIL/WARN/PASS, null for PASS_FAST)
- `intent_alignment` — one-sentence alignment assessment
- `summary` — 2-3 sentence overall assessment
- `issues` — list of `{severity, concern, location, description, remediation}`
- `issue_count` — integer count of issues
- `concerns` — set of concern labels from issues
- `route_decision` — serialised RouteDecision (selected_tools, review_intensity, rationale, policy_notes)
- `token_usage` — dict of token counts from provider
- `provider` — provider name (added in v1.1.5 for audit trail)
- `fail_open_reason` — nullable, populated on FAIL_OPEN
- `session_id` — from session.json at write time (nullable)
- Rebuttal records additionally contain: `strategy: "rebuttal"`, `rebuttal_actor`, `rebuttal_type`, `normalized_diff_hash`, `findings_count`, `accepted_count`

**What writes to it**: `ai_review.py::_persist_verdict()` on every verdict including PASS, WARN, FAIL, PASS_FAST, FAIL_OPEN, and rebuttal outcomes
**What reads it**: `init_session.py::infer_and_close_previous_session()` (aggregates token stats and FAIL count for the previous session's token_usage record), `distill_dream.py` (primary input B: scans for FAIL verdicts to generate improvement proposals), `harness_health.py` (verdict distribution, rebuttal metrics)

**How it feeds harness_health.py**: `harness_health.py` reads the log to compute verdict distribution (PASS/WARN/FAIL rates), FAIL_OPEN frequency, rebuttal pass rate, and rebuttal average latency.

**Current limitations**:
- Timestamp uses local time (not UTC), unlike `harness_events.jsonl` which uses UTC. Cross-referencing the two logs by time requires timezone awareness
- File locking on append — ✅ resolved (T1-N-02 ✅ v1.3.1 — `_lock_file` context manager wired into append site)
- `distill_dream.py` field mismatch — ✅ resolved (BUG-11 ✅ pre-sprint 2026-06-02 — `distill_dream.py` now reads `blocking_concern` with fallback to `check_type` for backwards compatibility)

**Backlog dependencies**:
- T1-L-10: False positive → eval regression pipeline — ✅ delivered; writes to `tests/data/false_positive_cases.csv`
- T1-N-02: concurrent write safety — ✅ v1.3.1

---
## Session Ledger (`session_ledger.jsonl`)
**Delivered**: v1.0.0 (2026-05-21) as `session_ledger.md`; converted to JSONL in v1.1.5 (T1-C-01)
**Primary files**: `.agent/state/session_ledger.jsonl` — one JSONL record per completed session

**Schema** (each line):
- `session_id` — UUID from the completed session
- `date` — datetime string formatted `"YYYY-MM-DD HH:MM"` (local time, NOT UTC)
- `action` — string summary: first commit message if commits were made, spec file name if spec-only session, or `"No active commits made. Session abandoned."`
- `startup_checked` — boolean, always `True` when written by `init_session.py`
- `agent` — agent identifier string
- `outcome` — `"success"` | `"partial"` | `"abandoned"` | `"escalated"`
- `outcome_source` — `"inferred"` | `"agent_override"` | `"human_override"`
- `outcome_note` — free text explanation of outcome
- `harness_version` — hardcoded `"2.0"` (not the actual framework version from `harness_version.txt`)
- `token_usage` — dict with 6 fields: `input_tokens`, `output_tokens`, `context_load_estimated_tokens`, `repo_map_estimated_tokens`, `adr_injection_estimated_tokens`, `call_count`

**What is captured per session**: Identity, timing, outcome, and token expenditure by category. Token expenditure is aggregated from `.ai-review-log.jsonl` matching by session_id at close time.

**How it feeds the dream phase**: `distill_dream.py` reads `session_ledger.jsonl` to build `session_outcomes` (maps session_id → outcome) and `total_sessions_30d`. It uses the outcomes to compute `escalation_rate` (proportion of sessions with `outcome == "escalated"` in the occurrence's contributing sessions). `init_session.py::maybe_run_dream_phase()` reads the ledger to check minimum session count (15) and minimum span (14 days) thresholds before triggering.

**Current limitations**:
- `harness_version` hardcoded — ✅ resolved (BUG-16 partially v1.3.1; fully resolved in v1.3.3 via HIB-FM8-02 where the dynamic read from `harness_version.txt` is executed at ledger write time)
- The `date` field uses local time (not UTC), creating inconsistency with `harness_events.jsonl`'s UTC timestamps; cross-referencing sessions in the two logs across timezone-aware environments requires care
- The previous `.md` format (`session_ledger.md`) may still exist in projects that pre-date the JSONL conversion; `load_hot_tier()` reads only the `.jsonl` file and will miss old entries
- `token_usage.input_tokens` and `output_tokens` reflect only the calls where `ai_review.py` successfully wrote a `token_usage` field to `.ai-review-log.jsonl` with a `session_id` match; PASS_FAST verdicts report zero tokens (correct), FAIL_OPEN verdicts also report zero tokens (correct), but any FAIL or WARN verdict from a session where `session.json` was absent at write time will not have a session_id and will be excluded from the aggregation

**Backlog dependencies**:
- T1-I-01: Memory tiering (hot/warm/cold) — ✅ partial (v1.3.1) — `memory_manager.py` three-tier file-based architecture (hot/warm/cold) delivered; SQLite and MCP tiers deferred to v2.0.0
- T1-I-06: Memory retention policy — ⬜ undelivered
- BUG-16: harness_version.txt read dynamically — ✅ v1.3.1

---
## SQLite State Persistence (`state_persistence.py`)
**Delivered**: v1.4.0 (2026-06-13) — T1-D-01 / T1-D-02
**Primary files**:
- `src/scripts/state_persistence.py` — SQLite mirroring layer (stdlib `sqlite3` only, no new pip dependencies)
- `~/.aisdlc/harness.db` — global cross-project SQLite index (outside project root, not committed)
- `.agent/state/harness.db` — project-local fallback (used when `~/.aisdlc/` is not writable)

**What it does**: Mirrors harness flat-file state to a SQLite index for cross-project querying and analytics. **Flat files in `.agent/state/` remain the canonical source of truth**; SQLite is a derived, rebuildable index. Three sync functions: `sync_session_to_db()` (called by `init_session.py` at session creation — upserts a `sessions` row), `sync_review_event_to_db()` (called by `ai_review.py::_persist_verdict()` after every verdict — inserts a `review_events` row), `sync_spec_acceptance_to_db()` (called by `acceptance_hook.py` — upserts a `spec_acceptance` row). `rebuild_from_flat_files()` replays `session_ledger.jsonl` into the sessions table for initial population and disaster recovery. `cleanup_project_rows()` is called by `uninstall.py` for selective row-level cleanup. WAL journal mode and 10-second busy timeout prevent concurrent write failures. All public functions return `bool` and never raise; errors degrade gracefully with a warning log.

**Schema**:
- `sessions` — session_id (PK), project_root, agent, start_time, end_time, outcome, outcome_source, outcome_note, task_magnitude, harness_version
- `review_events` — id (PK autoincrement), session_id, project_root, timestamp_utc, verdict, diff_hash, input_tokens, output_tokens, call_count
- `spec_acceptance` — spec_id + project_root (composite PK), status, recorded_at

**What it enables**:
- Cross-project observability: a single SQLite query shows verdict distribution, session outcomes, and token usage across all harness-managed projects on the machine
- Disaster recovery: `rebuild_from_flat_files()` can reconstruct the index from the authoritative flat files at any time
- Row-level cleanup on uninstall: `cleanup_project_rows()` removes only the uninstalled project's rows, leaving other projects' data intact

**Current limitations**:
- `harness_health.py` does NOT yet query SQLite — it still reads `.ai-review-log.jsonl` line-by-line. The SQLite integration is write-side only; query-side integration is a future step
- `~/.aisdlc/harness.db` is shared across all projects on the machine; `project_root` isolates rows, but if `_get_project_root()` returns different strings for the same project (symlink vs real path), rows may appear duplicated
- Not suitable for ephemeral CI containers without a persistent `$HOME`; the fallback `.agent/state/harness.db` is used but is ephemeral and not shared across runs
- Schema version is stored in the `schema_version` table but there is no migration path for schema upgrades — a schema change requires deleting and rebuilding the DB

**Backlog dependencies**:
- T1-D-01: SQLite persistence write layer — ✅ v1.4.0
- T1-D-02: Cross-project analytics schema — ✅ v1.4.0

---

## Intelligence Layer

---
## PageRank Repo Map (`repo_map.py`)
**Delivered**: v1.0.0 (2026-05-21) as part of Chain A Phase 3
**Primary files**:
- `.agent/skills/universal/senior-architect/scripts/repo_map.py` — graph builder and map generator
- `.agent/state/repo_graph_cache.json` — cache keyed by file modification times (gitignored)

**What it does**: Scans `src/` (or the project source root) using Python's `ast` module to build a directed import graph with `networkx`. For each `.py` file, `ImportVisitor` and `ImportFromVisitor` extract import edges. Runs `networkx.pagerank()` with a two-level personalisation signal: (1) changed files (from git `--cached --name-only`) are weighted 10×; (2) CamelCase identifiers found in the diff text by regex scan — files defining those identifiers get an additional 10× weight boost (Aider diff-identifier technique). Generates a token-budgeted ranked structural map: each entry includes file path, PageRank score, dependent file count, and top 3 symbol definitions. Budget: ≤600 tokens.

**Cache behaviour**: Caches the graph in `.agent/state/repo_graph_cache.json` keyed by file modification times (file path → mtime dict). Rebuilds only when source files have changed since the last run. Cache expiry is based on file mtime, not a time-based TTL. A `_get_compilation_timeout()` reads from `.agent/config.yaml` or env vars, defaulting to 5.0 seconds.

**How it integrates**:
- Called by: `ai_review.py::main()` (generates both the repo map text and PageRank scores dict), `wiki_compile.py::roster_builder.py` integration (indirectly via the shared import graph concept)
- Reads: all `*.py` files under `src/`, `.agent/state/repo_graph_cache.json`
- Writes: `.agent/state/repo_graph_cache.json` on cache miss

**Current limitations**:
- Source path is hardcoded to `src/` relative to the project root. Projects with different source layouts (e.g., `app/`, a single-module layout, or a monorepo) will produce an empty or misleading graph
- The `get_pagerank_scores()` function returns scores relative to a graph built from whatever Python files are in `src/`; if `src/` is empty (fresh install), the function returns `{}` and review intensity is always `"standard"`
- The symbol definition extraction (top 3 per file) captures class and function names from the AST but does not track method definitions inside classes — a class with 20 methods is represented only by its name
- No mechanism to invalidate the cache on file renames or deletions — the mtime check only detects modifications

**Backlog dependencies**:
- T1-H-01: PageRank repo map — ✅ delivered
- T1-H-03: Co-change blast radius estimator — ✅ delivered (in `co_change_check.py`)
- T1-H-04: Auto-generated context at install time — ⬜ undelivered
- T1-H-10: EXTRACTED/INFERRED/AMBIGUOUS confidence tiers for co-change warnings — ✅ v1.4.0 (EXTRACTED = history + AST import link; INFERRED = history only; AMBIGUOUS = AST import only, no history — routed to policy notes rather than LLM context)

---
## ADR Annotation and Wiki Injection
**Delivered**: v1.0.0 (2026-05-21) as Chain A Phase 3 (T1-H-02)
**Primary files**:
- `architecture_checks.py::extract_adr_annotations()` — scanner
- `ai_review.py::get_adr_context()` — injector
- `.agent/wiki/` — compiled wiki pages

**What it does**: The `# ADR: domain_name` comment convention marks source files with their governing architectural domain. `extract_adr_annotations()` scans a file for `# ADR:` prefixed comments using regex and returns the list of domain names. `get_adr_context()` in `ai_review.py` scans all `src/*.py` files for annotations, maps each domain to its PageRank score, sorts by score descending, and injects the corresponding compiled wiki pages (from `.agent/wiki/{domain}.md`) up to a 400-token budget. Suppressed domains (beyond budget) produce a policy note. The cap of 4 domains in the backlog spec is not hard-coded in the implementation; it is implicitly enforced by the 400-token budget.

**Wiki page injection format**: The `_strip_wiki_headers()` function removes page scaffolding before injection (strips `# title`, `**Compiled**`, `**Sources**`, `→ Full source:`, `## Related Domains` sections), injecting only the substantive content.

**How it integrates**:
- `extract_adr_annotations()` is called by `ai_review.py::build_route_decision()` (for routing) and `ai_review.py::get_adr_context()` (for wiki injection)
- `ai_review.py` appends ADR policy notes to `route_decision.policy_notes`
- `wiki_compile.py::DOMAIN_REGISTRY` defines which domains have wiki pages

**Current limitations**:
- `DOMAIN_REGISTRY` in `wiki_compile.py` contains 13 domains that all reference GymBase-specific ADR files (e.g., `docs/decisions/adr/adr_002_multi_tenant_branch_isolation.md`). In a fresh install these files do not exist, so all domains compile to pages containing `[FILE NOT FOUND]` — the ADR injection injects empty or placeholder content into every review
- The "ADR propagation via import graph" described in the T1-H-02 backlog spec (if file A has `# ADR: branch_isolation` and the diff modifies file B which imports A, inject the branch_isolation wiki page for B) is NOT implemented in `get_adr_context()`; the current implementation scans only files matching `Path("src").rglob("*.py")` for annotations, not the import graph
- `get_adr_context()` scans all source files on every review call, not just changed files; this is O(n_files) per review and could become slow in large projects
- ADR domain names are matched against `DOMAIN_REGISTRY` which is hard-coded in `wiki_compile.py`; project-specific domains defined in `.agent/config.yaml` are not automatically added to the registry

**Backlog dependencies**:
- T1-H-02: ADR annotation and wiki injection — ✅ delivered
- T1-H-08: Branch-isolated model roster in compiled wiki — ✅ delivered (via `roster_builder.py`)

---
## Compiled Wiki Layer (`wiki_compile.py`)
**Delivered**: v1.0.0 (2026-05-21) as Chain A Phase 2 (T1-H-06); roster builder added v1.1.5 (T1-H-08)
**Primary files**:
- `.agent/scripts/wiki_compile.py` — compiler and state manager
- `.agent/wiki/` — output directory for compiled wiki pages
- `.agent/state/wiki_compile_state.json` — cooldown and hash state (gitignored)
- `src/scripts/roster_builder.py` — AST-based ORM model roster builder

**Which domains**: 13 domains in `DOMAIN_REGISTRY` (all GymBase-specific): clean_architecture, branch_isolation, multi_branch_schema, session_authentication, saas_architecture, public_brand_config_api, communication_system_strategy, payment_hardware_strategy, trainer_conflict_global_integrity, pos_booking_payments, pt_infrastructure_hardening, remove_uow_autocommit. Also generates `branch_isolation_roster.json` as a sidecar via `roster_builder.py`.

**How compilation works**: For each domain, reads the source ADR files listed in `DOMAIN_REGISTRY`, constructs a prompt in `COMPILE_PROMPT` format, calls the configured provider (Ollama/Anthropic/Gemini via `wiki_compile_provider` config key). Output target is ≤200 tokens. Uses SHA-256 hashing of source file contents to detect staleness; only recompiles when sources have changed. Generates `index.md` after each run.

**Staleness detection**: `get_hash(paths)` calculates a combined SHA-256 of all source files for a domain. Stored in `wiki_compile_state.json::last_source_hashes`. Domains whose hash hasn't changed are skipped (0 API cost). If a source file is missing, its contribution to the hash is the bytes `b"missing"` — a consistent placeholder — so the hash changes only if the file is added or removed, not just absent.

**Update cadence**: Triggered by `init_session.py::maybe_run_wiki_compile()` at session start when ≥7 days have elapsed since last run. The 7-day cooldown means a project with daily sessions recompiles weekly. Manual trigger available via `python .agent/scripts/wiki_compile.py`.

**Current limitations**:
- GymBase DOMAIN_REGISTRY coupling — ✅ resolved (S0-24 ✅ 2026-06-02) — `load_domain_registry()` now reads from `.agent/config.yaml`; projects without GymBase ADR files skip domains gracefully
- The wiki compile state file stores only `last_run_utc` and `last_source_hashes` — the backlog spec for `dream_phase_state.json` envisioned `proposals_generated`, `proposals_written`, etc. fields but these are not written
- `call_anthropic()` budget tier — ✅ resolved (BUG-18 ✅ v1.3.1 — now calls `get_provider(tier="budget").raw_completion()`)
- Cold-start failure on compilation error — ✅ resolved (BUG-12 ✅ pre-sprint 2026-06-02 — `last_failure_utc` written on failure; 1-day retry cooldown used instead of 7-day success cooldown)
- `check_cloud_privacy_gate()` prompts the user once on first cloud provider use and then never again (acknowledged flag persisted in state); subsequent sessions silently send ADR content to cloud APIs without any reminder

**Backlog dependencies**:
- T1-H-06: Compiled wiki layer — ✅ delivered
- T1-H-07: Knowledge base lint pass — ✅ delivered (in `wiki_lint.py`)
- T1-H-08: Branch-isolated model roster — ✅ delivered
- T1-D-05: Model tiering configuration — ✅ resolved via BUG-18 (wiki_compile.py now uses budget tier)
- BUG-18: wiki_compile budget tier fix — ✅ v1.3.1

---
## Dream Phase (`distill_dream.py`)
**Delivered**: v1.0.0 (2026-05-21) as Chain B capstone (T1-D-03); thresholds and recency weighting implemented
**Primary files**:
- `.agent/scripts/distill_dream.py` — pattern detection, contradiction check, proposal writer
- `.agent/config/skill_ownership.yaml` — routing map (NOT YET DELIVERED — T1-D-00)
- `.agent/state/dream_proposals/` — output directory for proposal and contradiction cards

**Pattern detection logic**: Reads up to 30 days of `harness_events.jsonl` and `.ai-review-log.jsonl`. Aggregates occurrences by `(skill_name, pattern_key)` tuple. For each aggregate, computes: `count`, `escalation_rate` (escalated-outcome sessions / total occurrences), `appearance_rate` (unique sessions / total sessions in 30-day window), `recency_weight` (sum of 1/(days_ago+1)), `max_severity`.

**Thresholds**: Flags a pattern when `(count >= 3 AND escalation_rate >= 0.40 AND appearance_rate >= 0.20) OR max_severity == "critical"`. The `OR max_severity == "critical"` path ensures single high-severity events always generate proposals regardless of frequency.

**Proposal format**: `{skill}__{pattern_key}__open.md` with metrics, proposed rule from `proposed_rules_catalog`, evidence list (capped at 10 items), and a proposed diff block. De-duplicates against existing `__open.md` files by merging evidence lists.

**Contradiction detection**: Before writing each proposal, `check_contradiction()` scans the target skill's `SKILL.md` for existing rules with opposite polarity (`never/must not/should not` vs `always/must/should`) on the same subject (2+ keyword overlap). Contradiction generates a `__contradiction.md` card instead of a proposal.

**Routing to skill_ownership.yaml**: `skill_ownership.yaml` is read at startup. Each entry maps a skill name to `check_type`, `event_type`, and `keyword` lists. The logic maps event patterns to their designated skill files and supports both singular and plural fields.

**Cooldown behaviour**: Managed by `init_session.py::maybe_run_dream_phase()`. Skipped if (a) fewer than 7 days since last run, OR (b) fewer than 15 sessions in ledger, OR (c) sessions span fewer than 14 days. Bypassed when previous session outcome is `"escalated"` or when critical events have occurred since the last run.

**Current limitations**:
- `proposed_rules_catalog` contains 11 hardcoded rule templates. Any `pattern_key` not in the catalog falls back to a generic rule. The catalog is not project-configurable.
- `check_type`/`blocking_concern` field mismatch — ✅ resolved (BUG-11 ✅ pre-sprint 2026-06-02 — `distill_dream.py` now reads `blocking_concern` with fallback to `check_type` for backwards compatibility; specific concern labels now correctly route proposals)
- `skill_ownership.yaml` routing — ✅ resolved (T1-D-00 ✅ pre-sprint 2026-06-02 — `.agent/config/skill_ownership.yaml` created; patterns now route to correct skill files)
- Contradiction detection uses keyword overlap (2+ non-stopword matches) which is a heuristic with both false positives (two unrelated rules sharing common technical vocabulary) and false negatives (antonymous rules with low word overlap)
- The `--min-sessions` and `--min-span-days` CLI flags documented in the backlog spec are not implemented in `distill_dream.py`; only `--dry-run` is present
- No `unrouted__YYYY-MM-DD.md` output for unroutable patterns (described in the backlog spec); patterns that don't match any skill route to the fallback skills rather than being flagged explicitly

**Backlog dependencies**:
- T1-D-00: skill_ownership.yaml — ✅ delivered (pre-sprint 2026-06-02)
- T1-I-05: Memory contradiction detector — ✅ integrated into distill_dream.py
- T1-D-03: Dream phase — ✅ delivered
- BUG-11: blocking_concern field fix — ✅ pre-sprint 2026-06-02

---

## Outer Loop

---
## Spec Quality Gate (`check_spec.py`)
**Delivered**: v1.2.0 (2026-05-30) as T1-L-01; spec collision detection added in v1.3.4 (T1-L-01a)
**Primary files**:
- `.agent/scripts/check_spec.py` — two-tier quality gate
- `docs/planning/specs/` — spec file directory (convention)

**Two-tier check**:
- **Pass 1 (structural, zero LLM cost)**: Verifies required headings (`Goal & Context`, `Bounded Scope & Out of Scope`, `Assumptions`, `Acceptance Criteria`, `Status & Sign-off`), non-empty `Assumptions` and `Acceptance Criteria` sections, Gherkin keyword presence in Acceptance Criteria (`Given`, `When`, `Then` with word-boundary matching), lenient assumption markers (`[Resolved` or `[Pending` prefix on all bullet list items), `[Pending]` entries block APPROVED status, `**Source Issue**:` field reference, `**Status**: APPROVED` check (bypassed in local non-CI mode with a warning). Also detects `[HIGH_RISK_SCHEMA_CHANGE]` marker to elevate DBA scrutiny in Pass 2.
- **Pass 2 (quality, budget-tier LLM)**: Calls `providers.get_provider(tier="budget")` with a spec quality auditor prompt. Uses XML tag isolation (`<specification_content>`) for prompt injection defence. Returns `SpecQualityVerdict`: `verdict` (PASS/ADVISORY/FAIL), `clarity_score` (1-10), `testable_criteria`, `sharp_boundaries`, `resolved_assumptions`, `advisories`, `blocking_concerns`. ADVISORY downgrades to non-blocking; FAIL blocks. Skips in CI when budget provider is local (Ollama) or cloud credentials are absent. Fails open on provider availability errors; fails closed on authentication/configuration errors.

**Assumption validation**: Every bullet list line in `# Assumptions` must contain `[Resolved` or `[Pending`. A `[Pending]` entry blocks APPROVED. The check is lenient on format (e.g., `[Resolved: promoted to criterion #X]` vs `[Resolved]` both pass); the guard is presence, not sub-format.

**Mode-awareness (T1-L-00)**: ✅ delivered (pre-sprint 2026-06-02). `outer_loop.mode` (`discovery` / `incremental` / `contractual`) now read from `.agent/config.yaml`. In `discovery` mode all Pass 1 blocks downgrade to advisories (exit 0); in `contractual` mode assumption resolution is tightened and `--skip-spec-gate` is unavailable. Mode is displayed in the output header. Spec ID resolution hardened with `active_context.md` as a fourth path.

**What blocks vs warns**: Pass 1 failure → exit 1, prints specific missing sections. Pass 2 FAIL → exit 1, prints blocking concerns. Pass 2 ADVISORY → exit 0, prints advisories (non-blocking).

**Current limitations**:
- `--skip-spec-gate` requires `SKIP_REASON` of at least 10 characters but does not require structured JSON (unlike the T1-G-07 structured SKIP_REASON enforcement for the review gate); free text is accepted
- Pass 2 is skipped in CI for local providers, meaning CI only validates structure (Pass 1) and never the quality judgment; spec quality regressions only surface locally
- Spec ID resolution has a 4-way fallback (SPEC_ID env var → git branch name matching `SPEC-\d+` → `active_context.md` scan → single-file scan of the specs directory); the multiple-specs edge case is now less likely to fail but remains possible if neither branch name nor active_context.md reference a spec
- T1-L-01a (spec collision detection via Jaccard similarity) is delivered in v1.3.4 (Jaccard similarity check on acceptance criteria keywords across active specs in check_spec.py)

**Backlog dependencies**:
- T1-L-00: Outer loop methodology profile system — ✅ delivered (pre-sprint 2026-06-02)
- T1-L-01a: Spec collision detection — ✅ delivered (v1.3.4)

---
## Business Analyst Workflow (`business-analyst.md`)
**Delivered**: v1.2.0 (2026-05-30) as T1-L-02
**Primary files**:
- `.agent/workflows/business-analyst.md` — state machine workflow
- `.agent/templates/feature_spec.md` — spec template (must exist for the workflow to reference)
- `docs/planning/specs/` — output location for compiled specs

**Phases**: Phase 0 (session init via `init_session.py`) → Phase 1 (upstream issue intake; reads source issue, records `**Source Issue**:` reference) → Phase 2 (explicit assumption surfacing; enumerates unstated assumptions, assigns HIGH/MEDIUM/LOW confidence, resolves each as promoted / out-of-scope / pending) → Phase 3 (INVEST stories + Gherkin BDD in Acceptance Criteria) → Phase 4 (spec compilation to `docs/planning/specs/SPEC-XXX.md` with auto-incrementing ID) → Phase 5 (decisions_log feed using a specific three-bullet schema; includes a 150-line archival prompt for oversized decisions_log.md).

**Human approval gates**: Explicit: any `[Pending]` assumption must be resolved by the human architect before APPROVED status can be set. Implicit: the spec's `**Status**: APPROVED` must be set by the human (the agent drafts, the human approves).

**Assumption surfacing step**: Phase 2 instructs the agent to assign `confidence: HIGH/MEDIUM/LOW` to each assumption; anything below HIGH must be `[Pending: human review]`. This is stricter than the Pass 1 structural check in `check_spec.py`, which only checks for the presence of `[Resolved` or `[Pending` markers.

**Decisions_log feed**: Phase 5 writes architectural decisions to `.agent/state/decisions_log.md` using a specific format (`## YYYY-MM-DD: [SPEC-XXX] [Title]` with Decision/Context/Consequence bullets). Includes a ceiling check: if `decisions_log.md` exceeds 150 lines, the workflow prompts for archival to `decisions_log_archive.md`.

**Handoff to /pm**: The workflow document explicitly states that effort estimation and sprint planning are out of scope; the handoff to `/project-manager` is by naming convention in AGENTS.md §2.

**Current limitations**:
- The Session Outcome Override Handshake (writing `outcome_override` to `session.json`) is described in the workflow but depends on the agent explicitly writing to the JSON file — there is no automation; an agent that misses this step will have its planning session logged as `"abandoned"`
- T1-L-00 mode-awareness retrofit — ✅ resolved (pre-sprint 2026-06-02 — mode-conditional steps added at Phase 0 and Phase 2)

**Backlog dependencies**:
- T1-L-00: Outer loop methodology profile system — ✅ delivered (pre-sprint 2026-06-02)
- T1-L-04: Requirement → commit traceability — ✅ delivered (v1.3.0)
- T1-L-05: Acceptance gate — ✅ delivered (v1.3.0)

---
## Project Manager Workflow (`project-manager.md` + `pm_scaffold.py`)
**Delivered**: v1.3.0 (2026-06-03) as T1-L-03 — workflow document replaced and `pm_scaffold.py` delivered
**Primary files**:
- `.agent/workflows/project-manager.md` — five-phase state-machine workflow
- `.agent/scripts/pm_scaffold.py` — Gherkin-to-task scaffold script

**Phases**: Phase 0 (`init_session.py`) → Phase 1 (resolve and assert APPROVED SPEC) → Phase 2 (read Gherkin scenarios, report count) → Phase 3 (invoke `pm_scaffold.py`, surface output) → Phase 4 (developer review and approval before handoff to `/feature-implementation`).

**pm_scaffold.py**: Reads approved `SPEC-XXX.md`, parses Gherkin acceptance criteria via line-oriented state machine, synthesises atomic task backlog via budget-tier LLM. Supports `--offline` fallback (skeleton from parsed Gherkin, no LLM). Prompt injection defence via `<untrusted_specification_content>` XML tags. Backup mechanics on re-run (`{output_path}.bak`). Output: `docs/planning/tasks/SPEC-XXX-tasks.md`. Estimation scale: Fibonacci (1, 2, 3, 5, 8, 13 pts). Audit trail event written to `harness_events.jsonl`.

**Output location**: `docs/planning/tasks/SPEC-XXX-tasks.md` (not `.agent/state/task.md` — task backlogs are planning artefacts committed alongside specs).

**GymBase placeholders**: ✅ resolved (S0-24 + T1-L-00 retrofit 2026-06-02 — `{{PLACEHOLDER}}` references replaced with generic config-driven paths).

**Current limitations**:
- No spec input gate: the workflow asserts APPROVED status manually in Phase 1 but does not call `check_spec.py`; the spec gate runs as part of `feature-implementation.md`
- `--offline` flag produces skeleton tasks with `[Est: manual review required]` markers — developer must adjust estimates before handoff
- Prose-only acceptance criteria (no Gherkin) triggers a warning and fallback extraction, not an exit 1 — valid in `discovery` mode but produces lower-quality estimates

**Backlog dependencies**:
- T1-L-00: Outer loop methodology profile — ✅ delivered (pre-sprint 2026-06-02)
- T1-L-03: pm_scaffold.py — ✅ v1.3.0

---
## Requirement-to-Commit Traceability (`check_traceability.py`)
**Delivered**: v1.3.0 (2026-06-03) — T1-L-04
**Primary files**:
- `.agent/scripts/check_traceability.py` — stdlib-only commit-msg hook (zero external dependencies)

**What it does**: Fires as a `commit-msg` pre-commit hook. Resolves the commit message from `sys.argv[1]`, falls back to `.git/COMMIT_EDITMSG` via `git rev-parse --git-dir` (list-based subprocess, `shell=False`). Exempts merge commits (exits 0 on `"Merge "` prefix). Fast-paths documentation-only commits (all staged files match `.md`/`.txt`/`.rst` or reside under `docs/` — exits 0). Reads `specs_path` from `.agent/config.yaml` via targeted regex (no PyYAML dependency). Scans commit message for `SPEC-\d+` pattern. If found: verifies spec file exists; checks `Status: APPROVED` — DRAFT status warns in local mode, blocks in CI (`CI=true` env var). If no SPEC tag and non-trivial commit: checks for `--no-trace` keyword with minimum 10-char reason, logs `traceability_bypass` event to `harness_events.jsonl`, exits 0. Without either: exits 1 with terminal diagnostic card. Mode-aware: `discovery` mode downgrades all blocks to advisory; `contractual` mode makes `--no-trace` unavailable.

**What it prevents**:
- Commits that cannot be traced to an approved requirement entering the repository
- Drift between what was specified and what was implemented, detected at commit time rather than PR review time
- Infrastructure commits bypassing governance silently — `--no-trace` forces an explicit documented reason

**How it integrates**:
- Called by: `.pre-commit-config.yaml` (`commit-msg` stage)
- Reads: `.agent/config.yaml` (`specs_path`, `outer_loop.mode`), `docs/planning/specs/SPEC-XXX.md` (status check), `.git/COMMIT_EDITMSG` (commit message)
- Writes: `harness_events.jsonl` (`traceability_bypass` events)

**Current limitations**:
- Spec ID resolution uses `SPEC-\d+` pattern only — projects using different ID schemes must use `--no-trace` bypass
- No support for multiple SPEC references in a single commit message
- DRAFT block in CI mode requires `CI=true` env var — not all CI environments set this automatically

**Backlog dependencies**:
- T1-L-04 → ✅ (v1.3.0)
- T1-L-01a: Spec collision detection — ✅ delivered (v1.3.4)

---
## Acceptance Gate (`acceptance_check.py`)
**Delivered**: v1.3.0 (2026-06-03) — T1-L-05
**Primary files**:
- `.agent/scripts/acceptance_check.py` — AI-driven acceptance grader

**What it does**: Command-line utility run once per feature branch before PR promotion. Resolves the active spec via multi-channel hierarchy (`--spec` flag → `SPEC_ID` env var → active branch name). Extracts the branch diff via `git diff {base}...HEAD` where base defaults to `acceptance_gate.base_branch` from config.yaml (default: `main`). Static migration path check: if a configured migration path appears in the diff AND `[HIGH_RISK_SCHEMA_CHANGE]` is absent from the spec — hard `DIVERGED` verdict with no LLM call. Isolates spec content and diff in separate `<untrusted_*>` XML tags for prompt injection defence. Calls budget-tier LLM. Parses response into typed `AcceptanceVerdict` Pydantic model: `verdict` (`SATISFIED`/`PARTIAL`/`DIVERGED`), `satisfied_scenarios`, `partial_scenarios`, `unimplemented_scenarios`, `scope_creep_findings`, `remediation_steps`, `rationale`. Scenario labels extracted as `"Scenario: <label>"` strings (not full Given/When/Then text). Handles standard, numbered (number stripped), and unlabelled (ordinal fallback) label formats. Exit routing: `SATISFIED` → 0, `PARTIAL` → 0 (1 with `--strict`), `DIVERGED` → 1 always. Fails open on LLM unavailability unless `--fail-closed`. Mode-aware: `discovery` mode makes all verdicts advisory; `contractual` mode implies `--strict`.

**What it prevents**:
- Implementation that satisfies tests but diverges from specified intent
- Scope creep — code changes that implement behaviour not in the spec
- Schema migrations shipped without explicit spec acknowledgement
- A feature branch being promoted to PR when acceptance criteria are only partially implemented

**How it integrates**:
- Called by: developer or CI pipeline, once per feature branch
- Reads: `.agent/config.yaml` (`acceptance_gate` config block), `docs/planning/specs/SPEC-XXX.md` (acceptance criteria)
- Writes: `harness_events.jsonl` (`spec_acceptance_gate` events)

**Current limitations**:
- Scenario label extraction depends on LLM normalisation — edge cases with non-standard Gherkin formatting may produce ordinal fallback labels
- `--strict` and `--fail-closed` are independent flags; CI pipelines must explicitly set both for maximum gate strictness
- No cross-spec acceptance checking — cannot detect when implementation satisfies SPEC-002 but was supposed to implement SPEC-001

**Backlog dependencies**:
- T1-L-05 → ✅ (v1.3.0)
- T1-L-05a: Stop hook acceptance gate (`acceptance_hook.py`) — ✅ v1.4.0

---
## Acceptance Hook (`acceptance_hook.py`)
**Delivered**: v1.4.0 (2026-06-13) — T1-L-05a
**Primary files**:
- `src/scripts/acceptance_hook.py` — Claude Code Stop hook script
- `bootstrap/templates/claude_settings_hooks.json` — hook registration template (wired to `.claude/settings.json` by `install.py`)

**What it does**: Fires as a Claude Code Stop hook when a session ends on a feature branch (`feat/`, `feature/`, `release/` prefixes). Reads all `SPEC-*.md` files from the specs directory, extracts `status:` fields. Scans `git log main..HEAD` for `SPEC-\d+` references in commit messages. For each referenced spec, prints its status and calls `state_persistence.sync_spec_acceptance_to_db()` (best-effort). Exits 1 if any referenced spec is not `ACCEPTED`. Exits 2 (skip) if not on a feature branch. Exits 0 if all referenced specs are ACCEPTED or no spec references are found in the branch commit log. Exit code 1 causes Claude Code to block the session close and display the diagnostic.

**What it prevents**:
- A feature branch being closed out in Claude Code without the developer confirming spec acceptance status — the Stop hook fires before Claude Code ends the session
- Silent non-acceptance: prints a diagnostic card naming each non-accepted spec and instructs the developer to set `status: ACCEPTED` or move acceptance to CI

**Important constraint — Claude Code only**: Gemini CLI has no equivalent Stop hook. Gemini-driven sessions rely on the `outcome_override` convention in `session.json` (documented in AGENTS.md §6 / GEMINI.md) for close-out fidelity. This is documented in the script's module docstring and is not a defect — the architectural asymmetry is intentional and documented.

**How it integrates**:
- Wired by: `bootstrap/install.py` via `bootstrap/templates/claude_settings_hooks.json` → `.claude/settings.json`
- Reads: `docs/planning/specs/SPEC-*.md` (status field), `.agent/config.yaml` (specs_path override), `git log main..HEAD`
- Calls: `state_persistence.sync_spec_acceptance_to_db()` (best-effort; never raises)

**Current limitations**:
- `_FEATURE_BRANCH_PATTERNS` is hardcoded to `feat/`, `feature/`, `release/` prefixes — not config-driven; projects with different feature branch naming conventions silently skip acceptance checking (exit 2)
- Spec `status:` field is matched anywhere in the file body using a case-insensitive regex; a spec with `status:` in an example code block or table would match falsely (low practical risk)
- No enforcement that the ACCEPTED status was set after the last commit — a spec set to ACCEPTED before the branch started satisfies the hook even if implementation diverges

**Backlog dependencies**:
- T1-L-05a → ✅ v1.4.0

---

## Skills System

---
## Skill Architecture (representative: `code-review/SKILL.md` + `skill_mapping.yaml`)
**Delivered**: v1.0.0 (2026-05-21)
**Primary files**:
- `.agent/skills/universal/[skill-name]/SKILL.md` — skill definition file
- `.agent/config/skill_bdd_map.json` — BDD tag mapping (consumed by `select_bdd_gate.py`)
- `.agent/skills/universal/senior-architect/scripts/` — executable scripts (not Tool ABC subclasses yet)

**SKILL.md format**: Each skill consists of a single `SKILL.md` markdown file. No formal frontmatter schema is enforced at framework level. The SKILL.md files vary in length and structure across the skill library. Some skills include additional resources directories.

**Validate.py contract**: A per-skill `validate.py` is referenced in backlog items (T1-L-09 mentions `test_ai_review.py` verifies all skill validate scripts pass) but these per-skill `validate.py` files are not consistently present in the universal skills directory.

**Progressive loading mechanism**: Described in T1-B-05 (three-level loading) as a future backlog item — NOT yet implemented. All skills are available at session start via AGENTS.md §7 (Skills to Create Before Starting Work) which lists planned work streams, but there is no automated progressive loading of skill content.

**How skills are selected**: AGENTS.md §2 lists a workflow-to-task mapping table. Skills are applied by agent interpretation of task type — there is no automated selection mechanism. `select_bdd_gate.py` reads `skill_bdd_map.json` to map active skills to BDD tags for pytest filtering, but `skill_bdd_map.json` does not exist in the framework source (`.agent/config/` directory has only `golden_dataset.yaml`), so this script will fail with "Error: skill_bdd_map.json missing."

**Current skill count**: 22 universal skills (api-design, c4-architect, code-migration, code-review, database-design, debugging, devops-cicd, kaizen, performance-optimization, playwright-skill, python-async, python-automation, python-fastapi, python-testing, refactoring, security-audit, senior-architect, systematic-debugging, test-driven-development, test-writing, testing-patterns, verification-before-completion) plus one stack pack embedded in senior-architect's scripts.

**Current limitations**:
- `skill_bdd_map.json` — ⚠️ partially resolved (BUG-17 ✅ v1.3.1 — default template created in `bootstrap/templates/` and copied to `.agent/config/` by `install.py`; `validate.py` now emits WARN on absence; full stub with all 22 universal skills mapped is still pending)
- T1-E-01 (Tool ABC subclasses) is undelivered — skills are documentation-only, not testable Python objects with typed `run()` interfaces
- T1-B-04 (skill deprecation mechanism) is undelivered — no `status` field in skill metadata; no protection against deprecated skills being loaded
- T1-B-05 (progressive loading) is undelivered — all skills are equally available at session start without lazy loading
- T1-B-06/07 (skill audit and decomposition) are undelivered — skill length and quality are not enforced

**Backlog dependencies**:
- T1-E-01: Tool ABC subclasses — ⬜ undelivered (v1.3.0)
- T1-B-04: Skill deprecation mechanism — ⬜ undelivered (v1.5.0)
- T1-B-05: Self-service skill authoring — ⬜ undelivered (v1.5.0)
- T1-B-06/07: Skill audit and decomposition — ⬜ undelivered (v1.5.0)

---
## BDD Gate (`select_bdd_gate.py`)
**Delivered**: v1.0.0 (2026-05-21)
**Primary files**:
- `.agent/scripts/select_bdd_gate.py` — tag selector
- `.agent/config/skill_bdd_map.json` — tag mapping config (does NOT exist in current framework source)

**What it does**: Reads `skill_bdd_map.json` to get `skill_mapping` (maps skill names to BDD tag lists) and `default_tags`. Given a list of skill names as CLI arguments, maps each to its tags and outputs a `pytest -m` expression (e.g., `"booking or member or auth"`). If no skills match, falls back to `default_tags`. Writes the selection as a `## BDD Gate Selection` section to `active_context.md`.

**When it fires**: Called manually by the agent per AGENTS.md §7 instructions, not automatically by any hook.

**What it checks**: Purely a tag-to-filter mapper. Does not verify test existence, test results, or coverage. The output string is intended for use as `pytest -m "output"` by the agent or automation.

**Current limitations**:
- `skill_bdd_map.json` — ⚠️ partially resolved (BUG-17 ✅ v1.3.1 — default template exists; script is functional with template config but full 22-skill tag mapping is still pending)
- No pre-commit hook wires this; it is purely a utility the agent is instructed to use
- No test coverage for the BDD gate selector itself

**Backlog dependencies**:
- T1-B-04: Skill deprecation mechanism — when delivered, `select_bdd_gate.py` should respect the `status` field and exclude deprecated skills

---

## Bootstrap and Install

---
## Install Script (`bootstrap/install.py`)
**Delivered**: v1.0.0 (2026-05-21) as T1-A-02; `update_gitignore()` added in v1.2.0.1 (BUG-10)
**Primary files**: `bootstrap/install.py`, `bootstrap/manifest.py`

**What it detects**: Python version (3.9+ required), project directory (creates if absent, initialises git if no `.git`), tech stack (language/package manager/test framework from `pyproject.toml`, `package.json`, `go.mod`, etc.), source path convention.

**What it copies**: Harness files listed in `manifest.py` — `.agent/` directory contents, `src/scripts/` harness scripts (ai_review.py, providers.py, harness_utils.py, roster_builder.py), `.pre-commit-config.yaml`, CLAUDE.md, GEMINI.md, `.cursorrules`, `bootstrap/` utilities. Also substitutes `[PROJECT_NAME]` placeholders in AGENTS.md and `check_repo.py` with the target project name.

**Hook wiring**: Installs and runs `pre-commit install` with both `pre-commit` and `commit-msg` hook stages. The `pre-commit-config.yaml.template` is rendered with project-specific paths.

**Gitignore update** (BUG-10 fix): `update_gitignore()` appends an idempotent operational state block to the target project's `.gitignore`: `session.json`, `HALT`, `*.lock`, `config.yaml.migration_backup`, `.agent/wiki/`, `.agent/state/dream_phase_state.json`, `wiki_compile_state.json`, `wiki_lint_state.json`, `.agent/state/repo_graph_cache.json`. Explicitly excludes `harness_events.jsonl` (must be committed).

**Validation run**: Calls `bootstrap/validate.py` at the end of install to confirm hooks are wired and config is valid.

**Current limitations**:
- Stack detection is heuristic; a Python project without `pyproject.toml` falls back to `pip`/`unittest` defaults which may not match the project's actual toolchain
- The `[PROJECT_NAME]` substitution in `check_repo.py` is done via string replacement; if the project name contains regex-special characters, the replacement could fail silently
- No T1-H-04 (auto-generated context at install time) — the install does not run the repo map generator to populate `review_context_project.md`; developers receive a blank-page problem for project context

**Backlog dependencies**:
- T1-H-04: Auto-generated context at install — ⬜ undelivered (v1.5.0)
- HIB-038: Migration chain contiguity assertion — ✅ delivered in upgrade.py

---
## Validate Script (`bootstrap/validate.py`)
**Delivered**: v1.0.0 (2026-05-21) as T1-A-03; hardened in v1.2.0.1 (BUG-10)
**Primary files**: `bootstrap/validate.py`

**All checks performed**:
- Python 3.9+ version check
- `pre-commit` binary availability
- `.pre-commit-config.yaml` existence and hook entries (both `pre-commit` and `commit-msg` stages)
- Commit-msg hook entry in the config (BUG-02 fix)
- `ANTHROPIC_API_KEY` env var presence (WARN if absent, not ERROR — allows Ollama-only installs)
- `.agent/config.yaml` existence
- `review_context_universal.md` existence (ERROR if absent — gate will fail without it)
- `review_context_project.md` OR `review_context.md` existence (WARN if absent — gate continues without project context)
- Gitignored states check (`validate_gitignored_states()`): HALT absent from `.gitignore` → ERROR; `session.json` absent from `.gitignore` → WARN; `harness_events.jsonl` excluded from verification (must be committed)
- `skill_bdd_map.json` presence (WARN if absent — BUG-17 ✅ v1.3.1)
- `outer_loop.mode` validity (WARN if value not in `discovery`/`incremental`/`contractual` — T1-L-00 ✅)
- Recent wiki compile failure (WARN if `last_failure_utc` within 48 hours — BUG-12 ✅ pre-sprint 2026-06-02)

**ERROR vs WARN classification**: ERROR blocks the validation (exits non-zero); WARN is informational. The distinction is intentional: ERRORs are conditions that will cause the gate to fail silently or incorrectly; WARNs are conditions that degrade experience but don't block operation.

**Security mode**: `--security` mode is a backlog item (S0-17) — **NOT implemented**. The `--security` flag does not exist in `validate.py`.

**Current limitations**:
- Validates hook configuration in `.pre-commit-config.yaml` but does not verify the hooks actually fire correctly (e.g., does not run a test commit); a misconfigured hook entry passes validation but fails silently in practice
- S0-17 (`--security` mode for hash-and-display governance files) is undelivered
- No check for `skill_bdd_map.json` presence (would detect the missing BDD gate config)
- No check that `DOMAIN_REGISTRY` ADR source files exist (would detect the wiki compile problem)

**Backlog dependencies**:
- S0-17: `validate.py --security` mode — ⬜ undelivered (v1.3.0)

---
## Upgrade Script (`bootstrap/upgrade.py`)
**Delivered**: v1.1.5 (2026-05-28) as HIB-006; hardened with HIB-036/037/038 in v1.2.0
**Primary files**: `bootstrap/upgrade.py`, `bootstrap/migrations/v*.py`

**Migration chain**: Version-to-version migrations live in `bootstrap/migrations/`. Each migration is a Python module with `upgrade()` and `downgrade()` functions. `upgrade.py` discovers all migration modules, asserts chain contiguity (`_assert_chain_contiguous()`), and executes them in order. Chain contiguity prevents applying partial migrations from a forked or stale clone. `_pre_flight_check()` (HIB-037) validates installation state before starting migration. `--skip-preflight` flag available but logs a warning.

**Conflict handling**: Files classified as OVERWRITE (framework owns them) receive silent replacement; files classified as CONFLICT (developer has customised them) receive a `.framework-vX.X.X` sidecar file containing the new framework version; the developer manually merges. CRLF normalization before comparison avoids spurious conflict detection on Windows.

**Governance diff highlighting (T1-K-03)**: A backlog item (⬜ undelivered). Currently only CONFLICT files show a diff (via `--diff` flag); OVERWRITE governance files (AGENTS.md, governance.md, workflow files) do not show diffs unless they happen to generate CONFLICT sidecars.

**Rollback support**: `bootstrap/downgrade.py` mirrors the upgrade structure for roll-back. Each migration must implement `downgrade()`. Atomic restore on mid-upgrade exception: the installer creates a pre-migration snapshot and restores it on failure.

**Current limitations**:
- T1-K-03 (governance file diff highlighting on upgrade) is undelivered — developers who upgrade AGENTS.md without reviewing diffs have implicitly accepted changes to agent instruction without knowing what changed
- The `--dry-run` completion described in v1.1.5 success criteria is implemented; a developer can validate upgrade compatibility before applying

**Backlog dependencies**:
- T1-K-03: Governance diff highlighting — ⬜ undelivered (v1.3.0)
- HIB-039: ruamel.yaml migration — ⬜ deferred to v1.3.0

---
## Uninstall Script (`bootstrap/uninstall.py`)
**Delivered**: v1.2.0 (2026-05-30) as S0-14
**Primary files**: `bootstrap/uninstall.py`, `bootstrap/manifest.py`

**What it removes**: Framework files identified by `manifest.py` from the target project — `.agent/` directory contents, harness scripts in `src/scripts/`, tool supplements (CLAUDE.md, GEMINI.md, `.cursorrules`), `.pre-commit-config.yaml` (or just the harness hook entries if the project had pre-existing hooks).

**What it preserves**: Developer-created files in `.agent/state/` (active_context.md, decisions_log.md, session_ledger.jsonl, harness_events.jsonl), specs in `docs/planning/specs/`. Only framework-owned files (from manifest) are targeted.

**Confirmation prompts**: Triggers a `y/N` confirmation prompt before removing `.agent/state/` if it contains developer content; before removing tool supplements if they appear customised (no longer matching framework checksums). `--dry-run` mode prints what would be removed without acting. `--force` mode bypasses prompts.

**Current limitations**:
- The definition of "customised" for tool supplements uses checksum comparison against the framework's manifest checksums — a developer who added project-specific instructions to CLAUDE.md will see a "customised" prompt, but a developer who only used GEMINI.md unchanged will not be prompted to review it before removal
- `pre-commit uninstall` is only called if the framework created `.pre-commit-config.yaml` from scratch (detected via manifest); if the project had pre-existing hooks, the framework only removes its own entries

**Backlog dependencies**: None — this was a standalone Sprint 0 item.

---

## Test Suite

---
## Framework Self-Test Suite (`tests/`)
**Delivered**: v1.1.0 (2026-05-23) as T1-L-09 (60 tests); expanded to 181 tests as of v1.2.0.1
**Primary files**:
- `tests/test_ai_review.py` — golden-path, adversarial, and false-positive regression tests
- `tests/test_providers.py` — provider abstraction tests
- `tests/test_check_spec.py` — spec quality gate tests
- `tests/test_downgrade.py` — downgrade script tests
- `tests/test_init_session.py` — session lifecycle tests
- `tests/test_phase3_enforcement.py` — architecture enforcement tests
- `tests/test_uninstall.py` — uninstall utility tests
- `tests/test_install.py` — install script tests
- `tests/test_upgrade.py` — upgrade migration tests
- `tests/test_validate.py` — validate script tests
- `tests/test_prompt.py` — system prompt tests
- `tests/unit/test_upgrade_units.py` — upgrade unit tests
- `tests/unit/test_gate_context.py` — GateContext schema, load/write, degradation contract (T1-G-13)
- `tests/unit/test_capability_calibration.py` — calibration weight update, config overrides, clamp bounds (T1-G-14)
- `tests/unit/test_state_persistence.py` — SQLite schema, upsert, rebuild, cleanup, graceful degradation (T1-D-01/T1-D-02)
- `tests/unit/test_acceptance_hook.py` — branch pattern matching, spec status extraction, exit codes (T1-L-05a)
- `tests/e2e/run_e2e_verification.py` — E2E scenario runner
- `tests/e2e/test_project/` — representative installed project for E2E testing

**Test count**: 343 unit/integration tests (as verified by `pytest --collect-only`). All 343 pass.

**Coverage by module**: `test_ai_review.py` — gate routing, pre-flight shortcut, verdict parsing, rebuttal protocol, high-risk classification; `test_check_spec.py` — two-tier gate, Pass 1 structural checks, Pass 2 mock-verdict modes; `test_init_session.py` — outcome inference logic, session lifecycle; `test_upgrade.py` and `test_downgrade.py` — migration chain; `test_install.py` — stack detection, template rendering, hook wiring; `test_validate.py` — all validation checks and ERROR/WARN classification; `test_phase3_enforcement.py` — architecture boundary check engine; `test_check_traceability.py` — commit traceability gate; `test_acceptance_check.py` — acceptance gate verdicts and AcceptanceVerdict parsing; `test_pm_scaffold.py` — Gherkin parsing, offline mode, backup mechanics; `test_distill_dream.py` — dream phase routing and YAML loading; `test_wiki_compile.py` — config-driven domain registry; `test_gate_context.py` — GateContext schema, atomic write, degradation contract; `test_capability_calibration.py` — TP/FP weight update, config overrides, clamping; `test_state_persistence.py` — SQLite upsert, rebuild, cleanup, graceful error paths; `test_acceptance_hook.py` — branch filtering, spec status extraction, exit codes.

**E2E scenario count**: 30 E2E scenarios as of v1.3.1 (per CHANGELOG). These are implemented in `tests/e2e/run_e2e_verification.py` and test the gate against the `test_project/` simulated installation.

**Golden-path vs adversarial tests**: `test_ai_review.py` covers known-good diffs (should produce PASS), known-violation diffs (should produce FAIL on specific concerns), and false-positive regression cases. `tests/data/false_positive_cases.csv` is the destination for entries from `false_positive_to_eval.py`.

**False-positive regression suite**: The `false_positive_to_eval.py` script writes entries to `tests/data/false_positive_cases.csv`. `test_ai_review.py` reads this file and generates regression tests ensuring previously-confirmed false positives never resurface as FAILs.

**Current limitations**:
- Stale test project `ai_review.py` — ✅ resolved (BUG-13 ✅ pre-sprint 2026-06-02 — E2E setup now copies the current framework source at runtime; stale copy removed from git tracking)
- `test_providers.py` — providers are tested with mock responses; no integration test exercises an actual live API call
- No tests currently cover `wiki_compile.py`, `distill_dream.py`, `harness_health.py`, `select_bdd_gate.py`, or `check_repo.py`
- `tests/data/false_positive_cases.csv` may be empty (no confirmed false positives yet entered); the regression suite would then be empty

**Backlog dependencies**:
- T1-L-09: Framework self-test suite — ✅ delivered
- T1-L-10: False positive → eval regression pipeline — ✅ delivered

---

## Governance Documents

---
## `AGENTS.md`
**Delivered**: v1.0.0 (2026-05-21); P-14 added (exact version TBC); P-15 added in v1.2.0; context compaction protocol added v1.1.5; split into universal + project layers in v1.3.1 (T1-A-09)
**Primary files**:
- `.agent/AGENTS.md` — universal framework-owned governance layer (OVERWRITE in upgrade manifest since v1.3.1)
- `.agent/AGENTS_PROJECT.md` — project-owned extension layer; never overwritten on upgrade (T1-A-09 ✅ v1.3.1)
- `tests/e2e/test_project/.agent/AGENTS.md` (installed project version)

**Prohibition table (P-01 to P-15)**:
| P# | Prohibition |
|----|-------------|
| P-01 | Merge to main/master |
| P-02 | Delete migration/schema files |
| P-03 | Disable or weaken test assertions |
| P-04 | Skip writing tests for new functionality |
| P-05 | Install new dependencies without user approval |
| P-06 | Commit secrets, API keys, credentials |
| P-07 | Use unapproved package installers |
| P-08 | Import infrastructure layer from domain/business layers |
| P-09 | Access database sessions directly, bypassing Repository/UoW |
| P-10 | Modify `.env` files without documenting the change |
| P-11 | Commit or push without completing local verification |
| P-12 | Use `git add .` or `git add -A` |
| P-13 | Stage agent-generated files or log files |
| P-14 | Perform git operations without verifying active repository |
| P-15 | Direct commits to deployment/devops branches for CI/CD fixes |

**Layered governance (T1-A-09 ✅ v1.3.1)**: Agents load `AGENTS.md` first (universal framework governance), then `AGENTS_PROJECT.md` if it exists (project conventions extend but do not override the universal layer). `upgrade.py` migration detects custom sections in existing `AGENTS.md` via `difflib.SequenceMatcher` and writes them to `AGENTS_PROJECT.md`.

**Workflow naming conventions**: §2 maps task type to governing workflow (feature, bug-fix, architect, dba, security, perf, qa, release).

**Escalation triggers**: §5 lists stop conditions: deleting/renaming >1 file, dropping/truncating DB tables, modifying multi-tenant isolation or auth/RBAC code, deploying to staging/production, modifying CI/CD, blocking at same state >2 times.

**Session startup protocol**: §1 defines Steps 0–5 (check_repo → check_halt → init_session → git log → active_context → decisions_log → last_session_summary → state in one sentence → identify workflow).

**Context compaction protocol**: §6 (added v1.1.5, T1-M-06) session close protocol with explicit steps for updating `active_context.md`, `decisions_log.md`, `last_session_summary.md`, and `session_ledger.md`.

**Current limitations**:
- The prohibition table is convention-based only; enforcement is by agent compliance with the AGENTS.md text. P-08, P-09, P-10, P-11, P-12, P-13 have no corresponding hard enforcement mechanisms in the gate or hook chain
- The framework template file still contains `[PROJECT_NAME]` placeholder and a placeholder skill gap table in §7 that needs to be populated per-project; a fresh install will show a generic `[Example Stream]` entry
- No structural validation of AGENTS.md correctness during install or upgrade

**Backlog dependencies**:
- T1-C-02: Structured HITL approval queue — ⬜ would replace the binary HALT described in §5 with a structured approval queue
- T1-K-03: Governance diff highlighting on upgrade — ⬜ would make AGENTS.md changes visible on upgrade

---
## `governance.md`
**Delivered**: v1.0.0 (2026-05-21)
**Primary files**: `.agent/governance.md`

**What it covers that AGENTS.md doesn't**:
- Full rationale and per-prohibition context for P-01 through P-13 in a more readable format (AGENTS.md has the table; governance.md has the prose)
- Mandatory pre-task checks (§1): read domain context files, architecture docs, identify governing workflow, check session state, confirm IDLE starting state
- Escalation triggers in granular categorisation: Destructive Scope (7 specific triggers), Domain Safety (4 triggers), Process Safety (4 triggers), Infrastructure Safety (4 triggers)
- Full prohibition list with reasons for each (§3)
- Defensive Git Checkpoint Protocol (§7, referenced in backlog): the "stash before major changes" protocol. However, §7 is not visible in the lines read — it may exist further in the file or may be referenced in the backlog speculatively

**Distinction from AGENTS.md**: `governance.md` provides the enforcement layer rationale and full trigger specification; `AGENTS.md` provides the agent-facing quick-reference summary. `governance.md` is the authoritative source that AGENTS.md summarises.

**Current limitations**:
- P-14 and P-15 rationale gap — ✅ resolved (BUG-14 ✅ v1.3.1 — P-14 repository identity guard rationale and P-15 CI branch commits rationale added to governance.md §3)
- The document assumes the `decisions_log.md` and `business_rules.md` referenced in §1 exist at conventional paths; these paths use GymBase conventions (`docs/decisions/business_rules.md`, `docs/architecture/ARCHITECTURE.md`) that may not exist in a generic install

**Backlog dependencies**:
- T1-K-02: Formal security review of context-injection attack surface — ⬜ undelivered (v1.3.0)
- S0-18: `docs/security/` context injection point documentation — ⬜ undelivered (v1.3.0)

---
## Universal Context File (`UNIVERSAL_CONTEXT.md`)
**Delivered**: v1.3.1 (2026-06-03) — T1-B-01
**Primary files**:
- `.agent/UNIVERSAL_CONTEXT.md` — single canonical context source for all agents and IDEs
- `CLAUDE.md` — thin shim that loads `UNIVERSAL_CONTEXT.md`
- `GEMINI.md` — thin shim that loads `UNIVERSAL_CONTEXT.md`
- `.cursorrules` — thin shim that loads `UNIVERSAL_CONTEXT.md`

**What it does**: `UNIVERSAL_CONTEXT.md` is the single canonical instruction block shared across all AI agents and IDEs. `CLAUDE.md`, `GEMINI.md`, and `.cursorrules` are converted to thin shims that load it. Eliminates three-copy drift — a governance document change now requires updating one file rather than three. Completes the two-layer architecture pattern for the tool supplement layer: `review_context` ✅, compiled wiki ✅, `AGENTS.md` ✅, tool supplements ✅.

**What it prevents**:
- Divergence between what Claude Code, Gemini CLI, and Cursor know about project governance after a governance document update
- Silent outdated context in one tool supplement when another is updated

**Current limitations**:
- Shim files retain minimal tool-specific configuration that cannot be universalised (e.g. Cursor-specific syntax in `.cursorrules`)
- No automated check that shim content matches the expected template

**Backlog dependencies**:
- T1-B-01 → ✅ (v1.3.1)

---
## Project Agent Guidelines (`AGENTS_PROJECT.md`)
**Delivered**: v1.3.1 (2026-06-03) — T1-A-09
**Primary files**:
- `.agent/AGENTS_PROJECT.md` — project-owned extension layer (classified NEVER_TOUCH in upgrade manifest)
- `.agent/AGENTS.md` — universal framework-owned layer (classified OVERWRITE in upgrade manifest)

**What it does**: `AGENTS_PROJECT.md` is the project-owned extension layer for agent governance. Agents load `AGENTS.md` first (universal framework governance), then `AGENTS_PROJECT.md` if it exists (project conventions extend but do not override). `install.py` creates `AGENTS_PROJECT.md` as a starter template on fresh install. `upgrade.py` classifies `AGENTS.md` as OVERWRITE and `AGENTS_PROJECT.md` as NEVER_TOUCH. Migration from v1.3.0: `upgrade.py` detects custom sections in existing `AGENTS.md` via `difflib.SequenceMatcher`, writes them to `AGENTS_PROJECT.md` under a `# Migrated from AGENTS.md` header, and logs the migration to `decisions_log.md`.

**What it prevents**:
- CONFLICT classifications on `AGENTS.md` during upgrade — universal governance improvements apply cleanly on every upgrade
- Accidental overwrite of project-specific team conventions during framework upgrade
- Governance integrity drift where developers modify `AGENTS.md` and later have their additions silently overwritten by a framework upgrade

**Current limitations**:
- Migration is best-effort via line diffing — complex inline edits to universal sections may not be fully detected
- No structural validation that `AGENTS_PROJECT.md` content does not contradict `AGENTS.md` universal prohibitions

**Backlog dependencies**:
- T1-A-09 → ✅ (v1.3.1)
- T1-K-03: Governance diff highlighting on upgrade — ⬜ undelivered

---
## Memory Manager (`memory_manager.py`)
**Delivered**: v1.3.1 (2026-06-03) — T1-I-01 foundation
**Primary files**:
- `.agent/scripts/memory_manager.py` — three-tier file-based memory architecture

**What it does**: Implements file-based three-tier memory management. Hot tier (always loaded at session start): `active_context.md` and the most recent session entries. Warm tier (loaded on relevance signal): session ledger entries from the last 30 days, matched by keyword/tag. Cold tier (archived historical): session summaries older than 90 days, moved to an archive folder automatically. Called from `init_session.py` during session startup.

**Current limitations**:
- Hot/warm/cold distinction is file-based only — no SQLite index or vector search for warm tier retrieval (T2-A-01 deferred to v2.0.0)
- Relevance matching for warm tier is keyword-based, not semantic
- Cold tier archival is time-based only — no relevance-decay scoring (T1-I-06 undelivered)

**Backlog dependencies**:
- T1-I-01 → ✅ partial (v1.3.1) — file-based foundation; SQLite index (T2-A-01) and MCP server deferred to v2.0.0
- T1-I-06: Memory retention policy — ⬜ undelivered

---

## Integration Map

At runtime, the framework's components connect in three distinct execution contexts: **pre-commit hook chain**, **session startup**, and **scheduled background**.

### Pre-Commit Hook Chain (fires on every `git commit`)

```
git commit
    │
    ├─ [pre-commit stage]
    │       └── architecture_checks.py
    │               ├── reads: .agent/config.yaml (layer rules, patterns)
    │               ├── scans: src/**/*.py (AST import graph)
    │               ├── writes: .agent/state/gate_context_current.json (arch_violations, adr_domains)
    │               └── exits 1 on violation
    │
    ├─ [commit-msg stage]
    │       └── ai_review.py
    │               ├── calls: check_preflight_shortcut()
    │               │       └── exits 0 PASS_FAST if docs/whitespace only
    │               ├── calls: gate_context.load_gate_context()   ← T1-G-13
    │               │       └── reads: .agent/state/gate_context_current.json
    │               ├── calls: providers.get_provider()
    │               │       └── reads: .agent/config.yaml (model_routing)
    │               ├── calls: repo_map.generate_repo_map() + get_pagerank_scores()
    │               │       ├── reads: src/**/*.py (AST import graph)
    │               │       └── reads/writes: .agent/state/repo_graph_cache.json
    │               ├── calls: architecture_checks.extract_adr_annotations()
    │               │       └── scans: src/**/*.py for # ADR: comments
    │               ├── calls: get_adr_context() → reads .agent/wiki/{domain}.md
    │               ├── calls: build_route_decision() → RouteDecision
    │               ├── calls: co_change_check.run_co_change_estimator()
    │               │       └── returns EXTRACTED/INFERRED/AMBIGUOUS warnings  ← T1-H-10
    │               ├── calls: build_deterministic_findings_section(gate_context)  ← T1-G-13
    │               ├── calls: capability_calibration.get_calibrated_weight()   ← T1-G-14
    │               ├── calls: LLM provider (ReviewVerdict)
    │               ├── calls: capability_calibration (issue severity adjustment)  ← T1-G-14
    │               ├── writes: .ai-review-log.jsonl (verdict)
    │               ├── writes: .agent/state/harness_events.jsonl (gate events)
    │               ├── writes: .agent/state/gate_context_current.json (verdict + evidence)
    │               └── writes: ~/.aisdlc/harness.db review_events row (best-effort)  ← T1-D-01
    │
    └─ [post-commit stage]
            └── init_session.py --post-commit
                    ├── reads: .agent/state/session.json
                    └── writes: .agent/state/harness_events.jsonl (commit_made)
```

### Session Startup (fires when agent runs `init_session.py`)

```
init_session.py
    ├── infer_and_close_previous_session()
    │       ├── reads: session.json, .ai-review-log.jsonl, harness_events.jsonl
    │       │         active_context.md, git log
    │       └── writes: session_ledger.jsonl, session.json (COMPLETED)
    ├── orient_agent() → prints outcome alert
    ├── initialize_session()
    │       ├── writes: session.json (new ACTIVE session)
    │       └── calls: state_persistence.sync_session_to_db() (best-effort)  ← T1-D-01
    │               └── writes: ~/.aisdlc/harness.db sessions row
    ├── maybe_run_dream_phase()  [if cooldowns + thresholds pass]
    │       └── subprocess: distill_dream.py
    │               ├── reads: harness_events.jsonl, .ai-review-log.jsonl
    │               │         session_ledger.jsonl, .agent/config/skill_ownership.yaml
    │               │         .agent/skills/*/SKILL.md (contradiction check)
    │               └── writes: .agent/state/dream_proposals/__open.md or __contradiction.md
    ├── maybe_run_wiki_compile()  [if 7+ days since last run]
    │       └── subprocess: wiki_compile.py
    │               ├── reads: docs/decisions/adr/*.md (GymBase ADRs)
    │               └── writes: .agent/wiki/{domain}.md, branch_isolation_roster.json
    └── maybe_run_wiki_lint()  [if 14+ days since last run]
            └── subprocess: wiki_lint.py
```

### Session Close — Claude Code Stop Hook (fires when Claude Code ends a session)

```
acceptance_hook.py                                 ← T1-L-05a
    ├── reads: git log main..HEAD (SPEC-* refs in commit messages)
    ├── reads: docs/planning/specs/SPEC-*.md (status fields)
    ├── calls: state_persistence.sync_spec_acceptance_to_db() (best-effort)
    │       └── writes: ~/.aisdlc/harness.db spec_acceptance row
    ├── exit 2 → not a feature branch (skip)
    ├── exit 1 → one or more specs not ACCEPTED (Claude Code blocks session close)
    └── exit 0 → all specs ACCEPTED or no spec refs found
```

Note: Gemini CLI has no Stop hook. Gemini sessions close via the `outcome_override` convention
in session.json rather than through this hook.

### Outer Loop (fired manually by agent following /ba or /pm workflows)

```
/ba workflow
    ├── check_spec.py (Pass 1 structural + Pass 2 quality LLM)
    │       ├── reads: docs/planning/specs/SPEC-XXX.md, session.json
    │       └── writes: harness_events.jsonl (spec_quality_check), session.json (token_usage)
    └── decisions_log.md feed (agent convention, no automation)

/feature-implementation workflow
    └── check_spec.py (gate before implementation begins)
```

### Seams and Integration Gaps

- **Wiki → Gate**: `wiki_compile.py` compiles `.agent/wiki/` pages at session start; `ai_review.py` reads them at commit time. If wiki compilation fails or runs on a stale schedule, the gate injects outdated or empty context. No version tracking links the wiki page that was injected to the compilation run that produced it.
- **Session → Gate**: `ai_review.py` reads `session.json` only for session_id correlation in audit records. The gate does not read `task_magnitude` from session.json — it does not adjust behaviour based on whether the session was classified as "major". This is a missed integration opportunity.
- **Dream Phase → Skills**: `distill_dream.py` proposes diffs to `SKILL.md` files. There is no automated application — proposals require human review and manual edits. The "routing to skill_ownership.yaml" link is broken (T1-D-00 undelivered).
- **Architecture checks → Gate**: ✅ Resolved v1.4.0 (T1-G-13). `architecture_checks.py` now writes `arch_violations` and `adr_domains` to `gate_context_current.json` before the commit-msg stage. `ai_review.py` loads the `GateContext` and injects a "Deterministic findings (pre-LLM, verified)" section into the LLM prompt. Architecture violations and AI review failures now share a single context record with a common diff hash.
- **Session ledger → Health**: `harness_health.py` reads `.ai-review-log.jsonl` but it is unclear whether it also reads `session_ledger.jsonl` for token trend analysis; the integration between the token budget tracking in the ledger and the health reporting layer is not verified in the code read.

---

## Observed Gaps Between Implementation and Backlog Intent

### 1. Dream Phase Routing (T1-D-00 gap) — ✅ RESOLVED (pre-sprint 2026-06-02)
**Resolution**: `skill_ownership.yaml` created at `.agent/config/skill_ownership.yaml`. All patterns now route to correct skill files. BUG-11 fixed the `blocking_concern` field mismatch in the same PR — specific failure domains (BRANCH_ISOLATION, MASS_ASSIGNMENT, etc.) now generate domain-specific proposals rather than generic `"review_failure"` proposals.
**Prior state for record**: `skill_ownership.yaml` did not exist; `distill_dream.py` read `log.get("check_type")` instead of `blocking_concern`. Both issues resolved together pre-sprint.

### 2. Wiki Compile Domain Registry (GymBase coupling) — ✅ RESOLVED (S0-24, 2026-06-02)
**Resolution**: `DOMAIN_REGISTRY` moved from hardcoded Python to config-driven `load_domain_registry()` reading `.agent/config.yaml`. Projects without GymBase ADR files skip domains gracefully (no `[FILE NOT FOUND]` injection). Generic installs now receive a clean wiki layer on day one.
**Prior state for record**: All 13 `DOMAIN_REGISTRY` entries referenced GymBase ADR paths; a generic install compiled wiki pages containing only `[FILE NOT FOUND]` placeholders.

### 3. Project Manager Workflow Placeholders — ✅ RESOLVED (S0-24 + T1-L-00, 2026-06-02; T1-L-03, v1.3.0)
**Resolution**: `{{PLACEHOLDER}}` references replaced with generic config-driven paths (S0-24). T1-L-00 retrofit added mode-aware steps. T1-L-03 delivered a clean replacement `project-manager.md` with five structured phases and `pm_scaffold.py` as the operative scaffold script. PM workflow is now functional for a fresh install.
**Prior state for record**: ~20 unresolved `{{PLACEHOLDER}}` references to GymBase-specific documents; workflow non-operational on fresh installs.

### 4. ai-review-log.jsonl Field Mismatch (distill_dream.py) — ✅ RESOLVED (BUG-11, pre-sprint 2026-06-02)
**Resolution**: `distill_dream.py` now reads `blocking_concern` with a fallback to `check_type` for backwards compatibility. Domain-specific FAIL patterns (BRANCH_ISOLATION, MASS_ASSIGNMENT, TRANSACTIONAL_INTEGRITY) now generate skill-specific proposals rather than generic `"review_failure"` proposals.
**Prior state for record**: `distill_dream.py` read `log.get("check_type")` which never matched the actual `blocking_concern` field; all FAILs classified as `"review_failure"`.

### 5. Rebuttal Protocol Visibility Gap — ✅ RESOLVED (BUG-13, pre-sprint 2026-06-02; T1-N-02, v1.3.1)
**Resolution**: BUG-13 synced the E2E test project — setup now copies the current framework source at runtime, eliminating the stale copy. T1-N-02 added concurrent write safety to the rebuttal write path via `_lock_file`. Rebuttal protocol is now covered by E2E tests.
**Prior state for record**: `tests/e2e/test_project/src/scripts/ai_review.py` was a stale modified copy that lacked the rebuttal code; E2E tests did not exercise the rebuttal protocol.

### 6. Token Budget Trigger Gap (T1-I-07) — ✅ RESOLVED (pre-sprint 2026-06-02)
**Resolution**: `ai_review.py` now increments `session.json` token counters after each LLM call via atomic write through `_lock_session()`. The 80% WARN and 100% HALT thresholds now have a live counter to fire against. The v1.1.5 success criterion is now met.
**Prior state for record**: `ai_review.py` did not write back to `session.json`; `session.json` token counters were only incremented by `check_spec.py`; the HALT mechanism existed but had no automatic trigger from the review gate.

### 7. Session Ledger harness_version Field — ✅ RESOLVED (BUG-16, v1.3.1)
**Resolution**: `init_session.py` now reads from `harness_version.txt` at session close time. Session ledger records now carry the actual installed framework version. Forensic analysis of "which harness version was running" is now accurate.
**Prior state for record**: `harness_version` was hardcoded `"2.0"` in `init_session.py` regardless of the actual installed version.

### 8. Select BDD Gate Missing Config — ⚠️ PARTIALLY RESOLVED (BUG-17, v1.3.1)
**Resolution**: Default `skill_bdd_map.json` template created in `bootstrap/templates/` and copied to `.agent/config/` by `install.py`. `validate.py` now emits WARN on absence. The BDD gate selector script is functional with the template config.
**Remaining gap**: Full skill-to-tag mapping for all 22 universal skills is not yet complete in the template. The template provides the structure; project teams must populate tag mappings for their skill selection to be meaningful.
**Prior state for record**: `skill_bdd_map.json` did not exist in the framework source; `select_bdd_gate.py` exited immediately with "Error: skill_bdd_map.json missing." on any invocation.

### 9. Check_Halt.py Token Budget has No Auto-Writer — ✅ RESOLVED (pre-sprint 2026-06-02)
**Resolution**: Same fix as Gap #6. `ai_review.py` now increments the session token counter after each LLM call. When the counter reaches 100% of the configured budget, the token exhaustion logic writes a `token_budget_exhausted` HALT file atomically. The auto-writer mechanism is now live.
**Prior state for record**: No code path automatically wrote a `token_budget_exhausted` HALT file; the HALT mechanism existed but the trigger was missing.

---

## Sequencing Observations

### A. T1-D-00 (skill_ownership.yaml) Should Have Been Delivered Before T1-D-03 — ✅ RESOLVED (pre-sprint 2026-06-02)

**Resolution**: `skill_ownership.yaml` created at `.agent/config/skill_ownership.yaml` as a pre-sprint priority item. Dream phase routing is now functional. BUG-11 fixed the field mismatch in the same PR. The sequencing gap has been closed.

**Historical note**: T1-D-03 was marked ✅ at delivery but T1-D-00 was missing; the inversion was caught by the capability inventory review (2026-06-02) and corrected before Sprint 1 began.

### B. T1-L-00 (Outer Loop Methodology Profile) is Required Before T1-L-03–T1-L-07 Proceed — ✅ RESOLVED (pre-sprint 2026-06-02)

**Resolution**: T1-L-00 delivered as a pre-sprint gate item. `outer_loop.mode` added to `config.yaml.template`; `check_spec.py` and `business-analyst.md` retrofitted with mode-conditional behaviour. T1-L-03 through T1-L-05 (Sprint 1) were built mode-aware from the start.

**Historical note**: The roadmap sequencing note was correct; T1-L-00 was enforced as a pre-sprint gate before Sprint 1 began.

### C. T1-I-00a/00b (Audit Log Consolidation) Prerequisite for T1-I-01 — ✅ RESOLVED (v1.3.1)

**Resolution**: T1-I-00b audit confirmed via grep (2026-06-03): `circuit_breaker.py` is the single caller of `audit_logger.py`. T1-I-00a delivered: `circuit_breaker.py` now routes events to `harness_events.jsonl` via `harness_utils.py` logging helpers. Single source of truth confirmed. T1-I-01 foundation (memory_manager.py) was then safely delivered in the same sprint.

**Historical note**: The recommendation to verify T1-I-00b first (a read-only grep) was followed; single caller confirmed and consolidated in the same PR.

### D. E1 (Tool ABC) Dependency Chain Creates Downstream Bottleneck

**Current state**: T1-E-01 (Formalise skills as Tool ABC subclasses) is planned for v1.3.0. Multiple downstream items depend on it: T1-B-04 (skill deprecation), T1-B-05 (self-service skill authoring), T1-B-07a (anti-rationalization tables), T1-G-05 (restricted globals sandbox), T1-D-03's "executable verification" gap.

**Impact**: v1.5.0 (Skill Quality) is entirely gated on T1-E-01. The verification gap in T1-D-03 (dream proposals are semantically verified by contradiction check but not executable-verified against session evidence) will remain open until T1-E-01 is delivered.

**Recommendation**: T1-E-01 is correctly sequenced in v1.3.0 before the v1.5.0 skill quality work. However, the downstream benefit for T1-D-03 executable verification is substantial and should be highlighted as a primary motivation for T1-E-01.

### E. GymBase Coupling Creates Adoption Barrier Before Any Promotion — ✅ RESOLVED (S0-24, 2026-06-02)

**Resolution**: S0-24 delivered three targeted de-coupling changes: (a) `SYSTEM_PROMPT` in `ai_review.py` extracted to a config-loaded template — GymBase-specific patterns moved to `review_context_project.md`; (b) `DOMAIN_REGISTRY` in `wiki_compile.py` moved to config-driven `load_domain_registry()` reading `.agent/config.yaml`; (c) hardcoded GymBase directory paths in `build_route_decision()` moved to config. Generic installs no longer receive irrelevant review instructions or blank wiki pages.

**Historical note**: The recommendation to open an explicit "de-GymBase-ify" backlog item was followed — S0-24 was created and completed as a pre-sprint prerequisite for S0-23.

### F. T1-N Series Timing — Dynamic Workflows Research Preview Warrants Monitoring — ✅ T1-N-02 RESOLVED (v1.3.1)

**Resolution**: T1-N-02 delivered as a reliability fix in v1.3.1 (not gated on Dynamic Workflows GA as recommended). `_lock_file` context manager in `harness_utils.py` wired into `.ai-review-log.jsonl` and `harness_events.jsonl` append sites. Concurrent write safety is now in place.

**Remaining**: T1-N-01 (multi-agent session hierarchy schema), T1-N-03 (HALT sentinel subagent propagation), T1-N-04 through T1-N-06 remain ⬜ undelivered, correctly gated on Dynamic Workflows reaching general availability. Monitor at v2.0.0 planning.

### G. `check_spec.py` Inferred Spec Resolution is Fragile

**Current state**: `check_spec.py` resolves the target spec from (1) env var, (2) git branch name, (3) single-file scan of specs directory. The third fallback breaks when multiple specs exist.

**Impact**: A project with an active feature spec AND a maintenance spec will cause the gate to fail with "target specification not found" whenever the branch doesn't follow `SPEC-NNN` naming convention. This affects the v1.3.0 scope where T1-L-03 through T1-L-07 will create multiple active specs.

**Recommendation**: Before T1-L-04 (requirement → commit traceability) is delivered — which would generate even more spec references — harden the spec resolution logic to prefer the spec most recently modified or the one whose ID appears in `active_context.md`.

### H. The 7-Day Wiki Compile Cooldown Creates a Cold-Start Problem — ✅ RESOLVED (BUG-12, pre-sprint 2026-06-02)

**Resolution**: `wiki_compile_state.json` now records `last_failure_utc` on compilation failure. Failed compilations use a 1-day retry cooldown instead of the 7-day success cooldown. `validate.py` emits WARN if `last_failure_utc` is within 48 hours. A developer without Ollama will see a validation warning on the next session rather than silently waiting a week.

**Historical note**: The recommendation was implemented exactly as described — failure writes `last_failure_utc` (not `last_run_utc`), leaving the success cooldown intact.

---

*End of Capability Inventory. 29 component cards + 3 analysis sections. Updated to v1.4.0 by reading implementation code directly; discrepancies with backlog documentation are noted inline.*
