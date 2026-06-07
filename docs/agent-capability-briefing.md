# AI Delivery Control — Agent Capability Briefing

**Framework version**: v1.3.3
**Last updated**: 2026-06-07
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

## Currently Delivered Capabilities (v1.0.0–v1.3.1)

### Session lifecycle management

`init_session.py` establishes a UUID-tracked session on startup. `check_halt.py`
detects a HALT sentinel file and stops the agent before any work begins — now
enforced at every commit boundary as a pre-commit hook (BUG-15, v1.3.1) in
addition to session startup. `check_repo.py` verifies the agent is operating in
the correct repository (P-14 guard). Four markdown state files carry context
across sessions: `active_context.md`, `decisions_log.md`, `last_session_summary.md`,
`session_ledger.jsonl`. Agents are required to update all four at session close.

At session start, `init_session.py` also runs AST-based staleness detection
(T1-I-04, v1.3.1) — verifies that code patterns referenced in
`review_context_universal.md` and `review_context_project.md` still exist in
`src/`, outputting a warning card for any stale rules.

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

### Architecture boundary enforcement

AST-based checks (`architecture_checks.py`) scan the diff for layer boundary
violations and forbidden import patterns as defined in `.agent/config.yaml`.
Config-driven — no hardcoded language assumptions.

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

### Dream phase self-improvement loop

`distill_dream.py` reads 30 days of `harness_events.jsonl` and `.ai-review-log.jsonl`
at session start (weekly, when data thresholds are met). Detects recurring failure
patterns and generates structured improvement proposals in
`.agent/state/dream_proposals/`. Routes proposals to specific skill files via
`skill_ownership.yaml`. Contradiction detection runs before writing each proposal.
Proposals require human review before application.

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

### Concurrent write safety

`_lock_file` context manager in `harness_utils.py` is wired into `.ai-review-log.jsonl`
and `harness_events.jsonl` append sites. Safe for concurrent agent writes
(T1-N-02, v1.3.1).

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
- SQLite cross-project state index (T2-A-01 — deferred v2.0.0)
- HITL structured approval queue (`T1-C-02`)
- Skill deprecation mechanism (`T1-B-04`)
- Spec collision detection (`T1-L-01a` — Jaccard similarity on acceptance criteria)
- Automatic git stash checkpoint (`T1-J-01`) — planned v1.3.2
- Mid-session observability tool (`T1-M-03`) — planned v1.3.2
- Governance file diff highlighting on upgrade (`T1-K-03`)
- All Tier 3 enterprise infrastructure (PostgreSQL, SSO, RBAC, compliance mappings)

Backlog detail: `docs/planning/FRAMEWORK_BACKLOG.md`.

---

## Capability Changelog

| Version | Date | Change |
|---------|------|--------|
| v1.3.3 | 2026-06-07 | Dynamic versioning from harness_version.txt (HIB-FM8-02); severity casing normalization to uppercase (HIB-FM8-01); onboarding baseline relocation to `.agent/baseline/`; rebuttal_pass.json gitignore; docs/state-file-schema.md, docs/architecture/gate-context-design.md (T1-G-13) spec, and archetype domain starter packs |
| v1.3.1 | 2026-06-03 | UNIVERSAL_CONTEXT.md + tool shims (T1-B-01); AGENTS.md split + AGENTS_PROJECT.md (T1-A-09); concurrent write safety via _lock_file (T1-N-02); check_halt.py pre-commit hook (BUG-15); memory_manager.py three-tier foundation (T1-I-01); AST staleness detection in init_session.py (T1-I-04); T1-I-00a/00b audit log consolidation; BUG-14/16/17/18 fixes; 250 tests / 30 E2E scenarios |
| v1.3.0 | 2026-06-03 | /project-manager workflow + pm_scaffold.py (T1-L-03); requirement-to-commit traceability check_traceability.py (T1-L-04); acceptance gate acceptance_check.py (T1-L-05); pre-sprint: skill_ownership.yaml (T1-D-00), T1-I-07 token wiring, BUG-11/12/13, S0-24 de-GymBase-ify, T1-L-00 outer loop mode |
| v1.2.0.1 | 2026-05-31 | Bootstrap gitignore enforcement (BUG-10); validate.py HALT/session.json checks |
| v1.2.0 | 2026-05-30 | Spec quality gate check_spec.py (T1-L-01); /business-analyst workflow (T1-L-02); bootstrap/uninstall.py (S0-14); upgrade hardening HIB-036/037/038 |
| v1.1.5 | 2026-05-29 | bootstrap/upgrade.py (HIB-006); retrospective outcome inference + post-commit heartbeat (T1-C-01); outcome-aware session startup (T1-I-03); dream phase distill_dream.py (T1-D-03); token budget tracking (T1-I-02); structured rebuttal protocol (T1-G-06); context compaction template (T1-M-06); session_ledger converted to JSONL |
| v1.1.0 | 2026-05-23 | LLMProvider ABC (Anthropic/OpenAI/Ollama), high-risk commit classification, 65-test self-test suite, gate calibration fix, PASS/PASS_FAST verdict logging, ADR domain→capability mapping |
| v1.0.0 | 2026-05-21 | Initial delivery: session lifecycle, pre-commit gate, diff-aware routing, architecture checks, PageRank repo map, ADR annotations, compiled wiki, 22 skills, 17 workflows |
