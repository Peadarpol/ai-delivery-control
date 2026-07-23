# AI Delivery Control — Agent Capability Briefing

**Framework version**: v1.4.11
**Last updated**: 2026-07-24
**Update trigger**: Update this document when a backlog item moves to ✅ delivered,
when a capability is materially changed, or when a "not yet built" item ships.

---

## What This Framework Is

AI Delivery Control is a governance harness that sits between a human developer
and an AI coding agent. It does not increase agent autonomy — it maintains human
oversight at three mandatory checkpoints while the agent delivers code. The
governing principle is: **hard enforcement at the commit boundary, convention
everywhere else.**

It is installed into a target project via `bootstrap/install.py` and works with
any LLM-based agent (Claude Code, Gemini CLI, Cursor, Windsurf) through
`UNIVERSAL_CONTEXT.md` (the canonical context source) and thin shim files
(`CLAUDE.md`, `GEMINI.md`, `.cursorrules`) that load it.

---

## Currently Delivered Capabilities (v1.0.0–v1.4.11)

### Session lifecycle management

`init_session.py` establishes a UUID-tracked session on startup. `check_halt.py`
detects a HALT sentinel file and stops the agent before any work begins — now
enforced at every commit boundary as a pre-commit hook (BUG-15, v1.3.1) in
addition to session startup. `check_repo.py` verifies the agent is operating in
the correct repository (G-01 guard). Four markdown state files carry context
across sessions: `active_context.md`, `decisions_log.md`, `last_session_summary.md`,
`session_ledger.jsonl`. Agents are required to update all four at session close.

At session start, `init_session.py` also runs AST-based staleness detection
(T1-I-04, v1.3.1) — verifies that code patterns referenced in
`review_context_universal.md` and `review_context_project.md` still exist in
`src/`, outputting a warning card for any stale rules.

**Automatic session checkpoint (T1-J-01, v1.3.4)**: At session start, `init_session.py`
automatically creates a git stash checkpoint to prevent loss of original session-start state.
**Mid-task checkpoints (T1-J-01a, v1.3.4)** are established as a convention in `AGENTS.md`
for subprocess operations exceeding 60 seconds.

**Gemini CLI close protocol (HIB-GEMINI-01, v1.3.4)**: Establishes a structured close
protocol for Gemini CLI sessions using `.agent/state/agent_session_close.json` to record
outcomes, which is consumed at the next session start.

**Installer & validator onboarding hardening (SPEC-v1.4.11, v1.4.11)**: `bootstrap/install.py`
and `bootstrap/validate.py` enforce a target repository self-installation guard (`F-COLD-1`,
via `bootstrap/common.py::is_harness_repo()`), run an ephemeral git-sandbox dry-run validator
in `.agent/scratch/validate_sandbox/` with cross-platform URI formatting, bounded timeouts (30s
clone, 60s pre-commit), interrupt safety, and Windows read-only teardown (`remove_sandbox_dir`),
perform live API key preflight validation against Anthropic (`/v1/models`) and OpenAI (`/v1/models`)
endpoints with hard `<= 5.0s` socket timeouts and credential scrubbing, enforce regex-escaped
source paths (`re.escape()`, `F7`) in pre-commit exclusions for `black`, `ruff`, and `mypy`, and
provide standardized `--skip-validation` CLI flags.

### Retrospective session outcome inference

`init_session.py` infers the outcome of the previous session (success / partial /
abandoned / escalated) from git log, `.ai-review-log.jsonl`, and `harness_events.jsonl`
before the new session starts. Outcome is written to `session_ledger.jsonl`. The
agent is oriented at startup with a GFM Alert block matching the inferred outcome.
Post-commit heartbeat (`--post-commit` mode) updates `last_activity` in `session.json`
on every commit.

### Token budget tracking and enforcement

`session.json` tracks token consumption per session across 8 counters. `ai_review.py`
increments the counter after every LLM call (T1-I-07 wiring, v1.3.0 pre-sprint).
At 80% of the configured budget, a WARN is issued. At 100%, `check_halt.py` writes
a `token_budget_exhausted` HALT file atomically. `check_halt.py` is now wired as a
pre-commit hook, so a mid-session token exhaustion blocks commits automatically.

### Pre-commit AI adversarial review gate

Every `git commit` fires a structured review gate (`src/scripts/ai_review.py`)
via pre-commit hooks at the `commit-msg` stage. The gate reads the diff, loads
two context layers (universal framework invariants + project-specific invariants),
and calls a configured LLM provider. It produces a typed verdict — `PASS`,
`PASS_FAST`, `WARN`, `FAIL`, or `FAIL_OPEN` — logged to `.ai-review-log.jsonl`.
`FAIL` blocks the commit. `PASS_FAST` is returned for trivial diffs (docs,
whitespace) without an API call. The gate is provider-agnostic: Anthropic,
OpenAI-compatible, or local Ollama via `LLMProvider ABC`. Concurrent write
safety added via `_lock_file` (T1-N-02, v1.3.1).

**Blocked commands configuration (T1-K-06, v1.3.4)**: `.agent/blocked_commands.md`
is created as a standalone reference listing prohibited patterns (force push, drop table, etc.)
requiring human review, and `AGENTS.md` is updated to point to it as the canonical list.

**GateContext shared typed data bus (T1-G-13, v1.4.0)**: `gate_context.py` defines a `GateContext`
Pydantic object shared across the pre-commit hook chain. `architecture_checks.py` populates
`arch_violations` and `adr_domains`; `co_change_check.py` populates co-change warnings with
confidence tiers; `ai_review.py` prepends a deterministic "verified findings" block from this
context before the LLM call — architecture violations the model sees unconditionally regardless
of diff heuristics. Writes are atomic (`.tmp` + `os.replace()`); diff-hash mismatch degrades
gracefully to standalone mode.

**Evidence gathering (T1-G-11, v1.4.0)**: `pytest_collect_status` (test collection health) and
`todo_delta` (open TODO count change) are gathered before the LLM call and injected into the
review context as additional signals alongside the diff.

**Capability calibration (T1-G-14, v1.4.0)**: `capability_calibration.py` maintains a
per-capability TP/FP counter and weight (clamped to [0.5, 1.5]). Accepted rebuttals decay a
capability's weight 10%; rejected rebuttals grow it 5%. `ai_review.py` reads calibrated weights
at review time and downgrades HIGH-severity issues when a capability's weight falls below
threshold — reducing blocking FAILs on known-noisy checks without fully silencing any capability.
Weights respect manual `overrides` in `.agent/config.yaml`.

### Structured rebuttal protocol

When the gate returns `FAIL` on a finding the developer believes is a false
positive, `--rebuttal` mode provides a governed path to contest it. The rebuttal
argument is logged, a second model opinion is obtained, and accepted rebuttals
feed `false_positive_to_eval.py` as permanent regression guards.

### Diff-aware capability routing

Before the LLM call, a `RouteDecision` step classifies the diff and selects
which review dimensions to activate. PageRank scores from a repo map (`repo_map.py`)
elevate review intensity for high-centrality files. `# ADR: domain_name`
annotations in source files inject the relevant compiled wiki page into the
review context. Routing paths are config-driven — no hardcoded project assumptions
(S0-24, pre-sprint 2026-06-02).

**Co-change confidence tiers (T1-H-10, v1.4.0)**: Co-change warnings from
`co_change_check.py` are now classified as `EXTRACTED` (git history + AST import link),
`INFERRED` (git history only), or `AMBIGUOUS` (AST import only, no history). EXTRACTED
and INFERRED warnings are injected into the LLM context; AMBIGUOUS warnings route to
`route_decision.policy_notes` only — reducing noise from uncertain co-change signals.

### Architecture boundary enforcement

AST-based checks (`architecture_checks.py`) scan the diff for layer boundary
violations and forbidden import patterns as defined in `.agent/config.yaml`.
Config-driven — no hardcoded language assumptions.

**Fail-loud on misconfiguration (T1-K-08, v1.4.3)**: If architecture layers
are configured but zero Python files are found across all configured paths,
the check now exits 1 with a diagnostic explaining which paths were missing —
closing the "silent PASS on an unscanned codebase" failure mode.

**ADR decision block advisory (T1-L-13, v1.4.1)**: `check_adr_decision_blocks()`
scans ADR files for missing Decision Block scaffolding (AT/FM tradeoff
documentation). Non-blocking advisory printed alongside the verdict.

**Environment sanitisation (T1-K-05a, v1.4.1)**: All subprocess calls in
`architecture_checks.py`, `co_change_check.py`, and `repo_map.py` now use
`_safe_git_env()` — prevents credential exposure via inherited environment
variables in child processes.

### Governance consistency enforcement

**Framework consistency gate (T1-K-09, v1.4.3)**: `test_framework_consistency.py`
runs in CI and asserts that governance surfaces stay in sync:
- Every workflow slug in `AGENTS.md §2` maps to a real file in `.agent/workflows/`
- `blocked_commands.md` header references current H/S/C/G series labels (not
  stale P-series)
- Dead slug regression guards prevent `/perf` and `/qa` dead references
  returning
- `AGENTS.md §4.1` contains H/S/C/G series prohibition labels

**Prohibition table restructure (T1-K-10, v1.4.3)**: The flat P-01–P-15
prohibition table has been replaced with a three-tier structure in
`AGENTS.md §4`. `AGENTS.md §4.1` is now declared the single canonical source;
`governance.md §3` is a rationale+pointer document. All tool shim templates and
governance surfaces regenerated from the canonical table. Four universal series:
H (Honesty/Verification), S (Scope/Autonomy), C (Security), G (Version Control).
New universal prohibitions include: prompt injection guard (C-04), irreversibility
gate (S-03), compensating action prohibition (S-02), high-risk zone human review
flag (C-02), and sycophancy-in-planning prohibition (H-05).

**Session protocol single-sourcing (T1-K-10, v1.4.3)**: `governance.md §1`
(session startup) and `§6` (session close) converted to rationale+pointer
documents deferring to `AGENTS.md §1` and `§6` as canonical. Escalation
summary in `AGENTS.md §5` explicitly marked as summary-not-complete with
pointer to full 16-item list in `governance.md §2`.

**Stale branch detection (T1-K-11, v1.4.4)**: `harness_health.py` now surfaces
local branches with unmerged commits older than a configurable threshold
(default 14 days) as a DEGRADING signal — preventing silent accumulation of
unmerged delivery work.

### High-risk commit classification

When the LLM provider is unavailable, low-risk commits (docs, config) fail open.
Commits touching high-risk files (`*/migrations/*`, `*/auth/*`, `*/rbac/*`,
`unit_of_work.py`, etc.) fail closed — they cannot proceed without
`SKIP_AI_REVIEW=1 SKIP_REASON="..."` explicitly set, which is logged to
`harness_events.jsonl`.

### Requirement-to-commit traceability

`check_traceability.py` fires as a `commit-msg` hook. Non-trivial commits must
reference a `SPEC-\d+` ID that traces to an APPROVED spec in `docs/planning/specs/`.
Merge commits and documentation-only commits are fast-pathed. `--no-trace` bypass
requires a minimum 10-char reason and is logged. Mode-aware: advisory in
`discovery` mode, unavailable in `contractual` mode.

### Acceptance gate

`acceptance_check.py` evaluates the branch diff against the active spec's Gherkin
acceptance criteria before PR promotion. Returns a typed `AcceptanceVerdict`:
`SATISFIED`, `PARTIAL`, or `DIVERGED`. `DIVERGED` blocks. Static migration path
check fires before the LLM call — a schema migration without `[HIGH_RISK_SCHEMA_CHANGE]`
in the spec is a hard `DIVERGED` with no LLM cost. `--strict` upgrades `PARTIAL`
to blocking. `--fail-closed` blocks on LLM unavailability.

**Claude Code Stop hook (T1-L-05a, v1.4.0)**: `acceptance_hook.py` fires as a Claude Code
Stop hook when a session ends on a feature branch (`feat/`, `feature/`, `release/`). Scans
`git log main..HEAD` for `SPEC-\d+` references, checks each referenced spec's status, and
blocks the session close (exit 1) if any is not ACCEPTED. Gemini CLI sessions use the
`outcome_override` convention in `session.json` as the equivalent close-out signal —
the architectural asymmetry is intentional and documented.

### Spec quality gate and outer loop workflows

`check_spec.py` (two-tier) verifies structural completeness (Pass 1) and quality
via budget-tier LLM (Pass 2) before implementation begins. Mode-aware:
`outer_loop.mode` in `.agent/config.yaml` controls gate strictness (`discovery` /
`incremental` / `contractual`).

`/business-analyst` workflow governs requirement intake → assumption surfacing →
Gherkin BDD scenarios → spec drafting → human approval. Agent drafts; human approves.

`/project-manager` workflow governs APPROVED spec → sprint task backlog.
`pm_scaffold.py` parses Gherkin acceptance criteria and synthesises an atomic
task backlog via budget-tier LLM. Supports `--offline` fallback. Output:
`docs/planning/tasks/SPEC-XXX-tasks.md`.

**Spec collision detection (T1-L-01a, v1.3.4)**: computes keyword overlap
(Jaccard similarity) on acceptance criteria across active specs to warn of
overlaps before implementation starts.

**Spec grader per-criterion feedback (T1-L-12, v1.4.1)**: `check_spec.py`
Pass 2 now returns a per-criterion breakdown written to
`.agent/state/spec_grade_{SPEC_ID}.md` — each acceptance criterion assessed
individually (testable? specific? measurable?). The `/ba` workflow Phase 3
reads the grade card before finalising acceptance criteria.

**System archetype classification (T1-L-14, v1.4.1)**: Spec template §5
(Architectural Constraints) now includes an optional `System Archetype:` field
(A1–A6 from "The Engineer's Map"). A3 (Marketplace & Transaction) specs
receive heightened FM4/FM10 scrutiny. Field is optional — absence does not
block.

### Dream phase self-improvement loop

`distill_dream.py` reads 30 days of `harness_events.jsonl` and `.ai-review-log.jsonl`
at session start (weekly, when data thresholds are met). Detects recurring failure
patterns and generates structured improvement proposals in
`.agent/state/dream_proposals/`. Routes proposals to specific skill files via
`skill_ownership.yaml`. Contradiction detection runs before writing each proposal.
Proposals require human review before application.

**Dream phase fixes and threshold redesign (v1.3.4)**: Fixed `distill_dream.py` field matching schema bug
(reading summary and concerns instead of comments), added routing/catalog templates for `INTENT_MISMATCH`
(HIB-DREAM-02), and updated the compound threshold to use `OR` so high-frequency patterns qualify
on appearance rate alone without requiring escalated sessions (HIB-DREAM-03).

### Compiled wiki layer

`wiki_compile.py` synthesises project ADRs into domain-specific wiki pages
(`.agent/wiki/{domain}.md`) using a budget-tier model. Domains are config-driven
from `.agent/config.yaml` — not hardcoded (S0-24). Pages are injected at review
time via `# ADR: domain_name` annotations. Compilation uses `get_provider(tier="budget")`
(BUG-18, v1.3.1). Failed compilations use a 1-day retry cooldown (BUG-12).

### Universal context and layered governance

`UNIVERSAL_CONTEXT.md` is the single canonical context source — `CLAUDE.md`,
`GEMINI.md`, and `.cursorrules` are thin shims that load it (T1-B-01, v1.3.1).

`AGENTS.md` contains universal framework-owned governance. `AGENTS_PROJECT.md` is
the project-owned extension layer — never overwritten on upgrade (T1-A-09, v1.3.1).
`upgrade.py` migration detects custom sections in existing `AGENTS.md` and migrates
them to `AGENTS_PROJECT.md` automatically.

### Memory manager foundation

`memory_manager.py` implements file-based three-tier memory management (hot / warm /
cold). Moves session summaries older than 90 days to cold archive automatically
(T1-I-01 foundation, v1.3.1).

### SQLite cross-project state persistence

**SQLite persistence write layer (T1-D-01, v1.4.0)**: `state_persistence.py`
mirrors harness flat-file state to a SQLite index at `~/.aisdlc/harness.db` for
cross-project querying and analytics. Three sync functions are called automatically:
`sync_session_to_db()` at session init, `sync_review_event_to_db()` on every verdict,
and `sync_spec_acceptance_to_db()` via the acceptance hook. Flat files in `.agent/state/`
remain the canonical source of truth; SQLite is a derived, rebuildable index
(`rebuild_from_flat_files()`). No new pip dependencies (stdlib `sqlite3`). All sync
functions return `bool` and degrade gracefully — SQLite unavailability never blocks the
harness.

### Concurrent write safety

`_lock_file` context manager in `harness_utils.py` is wired into `.ai-review-log.jsonl`
and `harness_events.jsonl` append sites. Safe for concurrent agent writes
(T1-N-02, v1.3.1).

### Mid-session observability

**Lightweight session health CLI (T1-M-03, v1.3.4)**: `session_health.py` reports session duration,
tool calls, context load, and warning patterns (e.g. repetitive reads or remediation loops)
to help developers diagnose agent confusion.

### Harness health monitoring

**Harness health checks (v1.3.4)**: `harness_health.py` monitors dream proposal staleness
(HIB-HEALTH-01) and state file size thresholds (HIB-HEALTH-02) to maintain harness integrity and performance.

### 22 universal skills + 2 stack-packs

Each skill ships with an operating procedure, code examples (correct/incorrect),
an anti-patterns table, escalation triggers, and a `validate.py` script that must
exit 0 before the task is declared complete. Stack-packs (python-fastapi,
node-express) are auto-selected at install time. A default `skill_bdd_map.json`
template exists in `.agent/config/` — validate.py warns if absent (BUG-17, v1.3.1).

### 18 state-machine workflows

Named workflows in `.agent/workflows/` govern all non-trivial tasks:
feature-implementation, bug-fix, architect, dba, security, perf, qa, release,
CI/CD, deploy, infrastructure, UX, technical-writing, business-analyst,
project-manager, code-review, eval-pipeline, onboarding. Agents must name the
governing workflow before writing any code.

### Bootstrap and upgrade toolchain

`bootstrap/install.py` — installs the framework into a target project in under
10 minutes.
`bootstrap/upgrade.py` — version-to-version migration chain with contiguity
assertion, pre-flight check, atomic rollback, and conflict handling.
`bootstrap/downgrade.py` — mirrors upgrade for rollback.
`bootstrap/uninstall.py` — clean framework removal with developer content
preservation.
`bootstrap/validate.py` — environment validation with ERROR/WARN classification;
250 unit/integration tests + 30 E2E scenarios pass.

---

## What the Agent Must Do (Non-Negotiable)

1. Run `check_halt.py` → `check_repo.py` → `init_session.py` before any work
2. Read `UNIVERSAL_CONTEXT.md`, `AGENTS_PROJECT.md` (if present),
   `active_context.md`, `decisions_log.md`, `last_session_summary.md`
3. Name the governing workflow before writing code
4. Run `validate.py` for the relevant skill before declaring a task done
5. Update all four state files at session close
6. Stage named files only — never `git add .`
7. Stop and escalate if blocked at the same workflow state more than twice

Full protocol detail: `.agent/AGENTS.md` and `.agent/governance.md`.

---

## What Is Not Yet Built

The following are in the backlog but **not yet operational**. Do not assume these
exist when working in this project:

- Skill Tool ABC formalisation (`T1-E-01`) — skills are documentation-only, not
  typed Python objects with `run()` interfaces; planned v1.3.0 scope, still ⬜
- MCP memory server (Tier 2 — requires shared infrastructure; deferred v2.0.0)
- HITL structured approval queue (`T1-C-02`)
- Skill deprecation mechanism (`T1-B-04`)
- Governance file diff highlighting on upgrade (`T1-K-03`)
- All Tier 3 enterprise infrastructure (PostgreSQL, SSO, RBAC, compliance mappings)

Backlog detail: `docs/planning/FRAMEWORK_BACKLOG.md`.

---

## Capability Changelog

| Version | Date | Change |
|---------|------|--------|
| v1.4.10 | 2026-07-20 | Unified config parser rollout across all consumers (`T1-E-04`); dynamic risk-classification `override_defaults` + fail-closed protection (`T1-L-21`); root-commit exemption, versioned spec-ID regex & merge-gate aggregator (`T1-K-12`/`T1-K-13`); TTY-aware session-start recovery stashing (`HIB-ENV-02`/`T1-I-08`); SQLite schema drift auto-migration (`HIB-059`); fail-open audit taxonomy (`T1-K-14`); live log snapshotting on close (`HIB-063`); exception standards wrapper (`T1-K-15`/`AT-04`); append-only decisions log `record_decision()` & `archive_old_decisions()` helpers (`T1-L-20`) |
| v1.4.9.1 | 2026-07-19 | Onboarding defects fixes for bare-pip/no-Pydantic environments (F1, F2, F3, F5); post-merge code-quality remediation (FID-1 to FID-6); updated framework checksums registry |
| v1.4.9 | 2026-07-12 | Shipped configuration parser foundation in `harness_utils.py` (DEFAULTS, `load_harness_config()`, `get_harness_config()`) (`T1-E-04` foundation); `session.json` shared contract (`T1-E-03`); regex-based traceability ID checks (`HIB-062`); parser fail-closed on invalid escapes (`HIB-065`); `check_traceability.py` performance cache/size guard (`T1-L-22`); honest outcome labeling (`T1-B-11`) |
| v1.4.8 | 2026-07-07 | Added CodeQL configurations; regenerated checksums registry for version 1.4.3 and 1.4.4 |
| v1.4.7 | 2026-07-07 | Fixed `validate.py` pre-commit PATH validation check on Windows via `sys.executable` fallback check (HIB-046) |
| v1.4.6 | 2026-07-07 | Integrated reconciler with coupling decision records (CDRs); schema, pilot migration, and reconciler classification (Undeclared/Escalated/Tolerated/Accepted) with hub-scope exemption fix |
| v1.4.5 | 2026-07-06 | Decomposed `ai_review.py` into five helper modules (`roster_builder`, `context_loader`, `route_decision`, `rebuttal`, `gate_context`) to resolve structural coupling and circular imports |
| v1.4.4 | 2026-06-22 | Integration release — five unmerged branches recovered; BUG-04/05 (PASS verdict logging, ADR routing); T1-K-05a (subprocess env sanitisation via `_safe_git_env()`); T1-L-12 (SpecGradeCard per-criterion feedback); T1-L-13 (ADR decision block enforcement); T1-L-14 (system archetype classification A1-A6); T1-K-11 (stale branch detection in harness_health.py); 372 tests; 643 checksum files |
| v1.4.3 | 2026-06-22 | Prohibition table restructured into H/S/C/G four-series universal tier with project-specific (§4.2) and pattern-conditional (§4.3) sub-tiers (T1-K-10); `AGENTS.md §4` declared canonical single source of truth across all governance surfaces; consistency gate added (T1-K-09): workflow slug resolution, H/S/C/G label assertions, blocked_commands header currency; architecture_checks.py fail-loud on zero files scanned (T1-K-08); H-series procedural reframing + stale P-series cleanup (T1-M-14); nine new universal prohibitions with evidence base from 2025-2026 incident research |
| v1.4.0 | 2026-06-13 | GateContext shared typed data bus across pre-commit hook chain (T1-G-13); evidence gathering injecting pytest_collect_status and todo_delta into LLM context (T1-G-11); capability calibration per-capability TP/FP weight adjustment (T1-G-14); EXTRACTED/INFERRED/AMBIGUOUS co-change confidence tiers (T1-H-10); SQLite cross-project state persistence write layer (T1-D-01); Claude Code Stop hook acceptance gate (T1-L-05a) |
| v1.3.4 | 2026-06-12 | Automatic session-start stash checkpoint (T1-J-01) and mid-task checkpointing (T1-J-01a); spec collision detection (T1-L-01a); mid-session observability tool / session health CLI (T1-M-03); blocked_commands.md configuration (T1-K-06); Gemini CLI close protocol checklist (HIB-GEMINI-01); harness health checks for dream proposal staleness (HIB-HEALTH-01) and state file sizes (HIB-HEALTH-02); distill_dream.py wrong field name fix (HIB-DREAM-01), INTENT_MISMATCH routing (HIB-DREAM-02), and escalation_rate threshold redesign (HIB-DREAM-03) |
| v1.3.3 | 2026-06-07 | Dynamic versioning from harness_version.txt (HIB-FM8-02); severity casing normalization to uppercase (HIB-FM8-01); onboarding baseline relocation to `.agent/baseline/`; rebuttal_pass.json gitignore; docs/state-file-schema.md, docs/architecture/gate-context-design.md (T1-G-13) spec, and archetype domain starter packs |
| v1.3.1 | 2026-06-03 | UNIVERSAL_CONTEXT.md + tool shims (T1-B-01); AGENTS.md split + AGENTS_PROJECT.md (T1-A-09); concurrent write safety via _lock_file (T1-N-02); check_halt.py pre-commit hook (BUG-15); memory_manager.py three-tier foundation (T1-I-01); AST staleness detection in init_session.py (T1-I-04); T1-I-00a/00b audit log consolidation; BUG-14/16/17/18 fixes; 250 tests / 30 E2E scenarios |
| v1.3.0 | 2026-06-03 | /project-manager workflow + pm_scaffold.py (T1-L-03); requirement-to-commit traceability check_traceability.py (T1-L-04); acceptance gate acceptance_check.py (T1-L-05); pre-sprint: skill_ownership.yaml (T1-D-00), T1-I-07 token wiring, BUG-11/12/13, S0-24 de-GymBase-ify, T1-L-00 outer loop mode |
| v1.2.0.1 | 2026-05-31 | Bootstrap gitignore enforcement (BUG-10); validate.py HALT/session.json checks |
| v1.2.0 | 2026-05-30 | Spec quality gate check_spec.py (T1-L-01); /business-analyst workflow (T1-L-02); bootstrap/uninstall.py (S0-14); upgrade hardening HIB-036/037/038 |
| v1.1.5 | 2026-05-29 | bootstrap/upgrade.py (HIB-006); retrospective outcome inference + post-commit heartbeat (T1-C-01); outcome-aware session startup (T1-I-03); dream phase distill_dream.py (T1-D-03); token budget tracking (T1-I-02); structured rebuttal protocol (T1-G-06); context compaction template (T1-M-06); session_ledger converted to JSONL |
| v1.1.0 | 2026-05-23 | LLMProvider ABC (Anthropic/OpenAI/Ollama), high-risk commit classification, 65-test self-test suite, gate calibration fix, PASS/PASS_FAST verdict logging, ADR domain→capability mapping |
| v1.0.0 | 2026-05-21 | Initial delivery: session lifecycle, pre-commit gate, diff-aware routing, architecture checks, PageRank repo map, ADR annotations, compiled wiki, 22 skills, 17 workflows |

