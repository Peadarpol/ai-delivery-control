# AI Delivery Control — Agent Capability Briefing

**Framework version**: v1.2.0.1
**Last updated**: 2026-06-02
**Update trigger**: Update when a backlog item moves to ✅ delivered, when a
capability changes materially, or when a "not yet built" item ships.
**Source of truth**: `docs/planning/CAPABILITY_INVENTORY.md` (generated 2026-06-02).

---

## What This Framework Is

AI Delivery Control is a governance harness that sits between a human developer
and an AI coding agent. It does not increase agent autonomy — it maintains human
oversight at three mandatory checkpoints while the agent delivers code. The
governing principle is: **hard enforcement at the commit boundary, convention
everywhere else.**

It is installed into a target project via `bootstrap/install.py` and works with
any LLM-based agent (Claude Code, Gemini CLI, Cursor, Windsurf) through shim
files (`CLAUDE.md`, `GEMINI.md`, `.cursorrules`).

---

## Currently Delivered Capabilities (v1.0.0–v1.2.0.1)

### Session lifecycle management

`init_session.py` establishes a UUID-tracked session on startup. It
**retrospectively infers the previous session's outcome** (success / partial /
abandoned / escalated) by reading `git log`, `.ai-review-log.jsonl`, and
`harness_events.jsonl`, writes the result to `session_ledger.jsonl`, then
**orients the agent** with a GFM Alert block before initialising the new session.
A post-commit heartbeat (`--post-commit` mode) updates `last_activity` and logs
a `commit_made` event on every git commit, even if the session startup protocol
was skipped.

`check_halt.py` detects the `.agent/state/HALT` sentinel file. For
`token_budget_exhausted` halts, `BYPASS_HALT_REASON` env var provides an audited
escape path. For governance-violation halts, there is no bypass.

`check_repo.py` verifies the agent is operating in the correct repository by
comparing the git remote URL against the expected project name set at install
time (P-14 guard, convention-only — no pre-commit hook).

State files carrying context across sessions: `active_context.md`,
`decisions_log.md`, `last_session_summary.md`, and `session_ledger.jsonl`
(JSONL, one record per session).

### Pre-commit AI adversarial review gate

Every `git commit` fires `src/scripts/ai_review.py` via pre-commit hooks at the
`commit-msg` stage. The gate produces a typed `ReviewVerdict` Pydantic model:
`PASS`, `PASS_FAST`, `WARN`, `FAIL`, `FAIL_OPEN`. `FAIL` blocks the commit. All
verdicts — including PASS and PASS_FAST — are logged to `.ai-review-log.jsonl`.

**Pre-flight shortcut**: documentation-only (`.md`, `.rst`, `.txt`) and
whitespace/comment-only diffs return `PASS_FAST` with zero API calls.

**Provider abstraction (T1-E-02)**: the gate is provider-agnostic via
`src/scripts/providers.py`. Supported: Anthropic, OpenAI-compatible, local
Ollama. Provider selected from `.agent/config.yaml`.

**Diff-aware capability routing**: `build_route_decision()` classifies the diff
and activates relevant review dimensions (TRANSACTIONAL_INTEGRITY,
BRANCH_ISOLATION, MASS_ASSIGNMENT, RBAC, MIGRATIONS, CLEAN_ARCH). PageRank
scores from `repo_map.py` set review intensity: `standard` / `elevated` /
`critical`. Changes to top-3 PageRank files escalate WARN to FAIL
automatically. Policy notes explain what was checked vs skipped.

**High-risk fail-closed**: when the provider is unavailable and the commit
touches high-risk files (`*/migrations/*`, `*/auth/*`, `*/rbac/*`,
`unit_of_work.py`, `base_repository.py`, `models.py`, or high-risk ADR domains),
the gate fails **closed**, not open. Override requires
`SKIP_AI_REVIEW=1 SKIP_REASON="..."`, which is logged to `harness_events.jsonl`.

**Structured rebuttal protocol (T1-G-06)**: when the gate returns FAIL, the
agent can contest findings via `--rebuttal` mode with a structured
`gate_rebuttal.json` input. A second adversarial LLM call adjudicates each
finding (REBUTTAL_ACCEPTED / REBUTTAL_REJECTED). Accepted rebuttals
automatically feed `false_positive_to_eval.py`.

**Diff size stratification (T1-G-08)**: diffs above the configured threshold
(default 400 lines) are reviewed in stratified mode — high-risk sections at full
intensity, the remainder at reduced context injection.

### Architecture boundary enforcement

AST-based checks (`architecture_checks.py`) scan for layer boundary violations
and forbidden import patterns as configured in `.agent/config.yaml`. Runs as a
separate pre-commit hook before the AI review gate. Also provides
`extract_adr_annotations()` which reads `# ADR: domain_name` comments for use
by the gate's routing step.

### Repository intelligence

**PageRank repo map** (`repo_map.py`): builds an import graph from `src/**/*.py`,
runs `networkx.pagerank()` with changed files weighted 10× plus CamelCase
identifier personalisation. Generates a ≤600-token ranked structural map injected
before the LLM call. Cached in `.agent/state/repo_graph_cache.json`.

**ADR annotation + wiki injection**: `# ADR: domain_name` comments in source
files trigger injection of the corresponding compiled wiki page at review time.
Budget: ≤400 tokens, priority by PageRank score.

**Compiled wiki layer** (`wiki_compile.py`): LLM compiles ADRs and architectural
rules into domain wiki pages in `.agent/wiki/`. SHA-256 hash-based incremental
compilation (only rebuilds changed domains). Triggered weekly at session start.
Also compiles an AST-based branch isolation model roster sidecar
(`branch_isolation_roster.json`) for BRANCH_ISOLATION false-positive reduction.

**Co-change blast radius estimator** (`co_change_check.py`): combines git
co-change history (last 200 commits) with the import graph to surface HIGH and
MEDIUM confidence co-change warnings at review time.

**Knowledge base lint pass** (`wiki_lint.py`): fortnightly check for staleness,
factual drift between wiki and source ADRs, orphaned rules, and cross-file
contradictions.

### Dream phase self-improvement

`distill_dream.py` reads 30 days of `harness_events.jsonl` and
`.ai-review-log.jsonl`. Flags recurring patterns where
`(count ≥ 3 AND escalation_rate ≥ 0.40 AND appearance_rate ≥ 0.20) OR
severity == critical`. Generates `__open.md` proposal cards or `__contradiction.md`
cards (when the proposed rule conflicts with an existing SKILL.md rule) in
`.agent/state/dream_proposals/`. Triggered weekly at session start when ≥15
sessions spanning ≥14 days have accumulated.

> **⚠ Known gap**: `skill_ownership.yaml` (the routing map that directs proposals
> to specific skill files) does not yet exist. Until T1-D-00 is delivered, all
> event patterns route to `"agent-framework"` and all review FAILs route to
> `"code-review"` regardless of the actual failure domain. Proposals are generated
> but their skill attribution is not meaningful.

### Token budget management

`session.json` tracks token consumption per session. `check_halt.py` supports
a `token_budget_exhausted` HALT reason with an audited bypass path. The HALT
file mechanism and schema are in place; automated budget ceiling enforcement
requires additional wiring (see "Not Yet Built").

### Outer loop: requirements governance

**Spec quality gate** (`check_spec.py`, T1-L-01): two-pass gate before
`/feature-implementation` begins. Pass 1 (structural, zero LLM cost): required
headings, Gherkin keywords in Acceptance Criteria, `[Resolved`/`[Pending` markers
on all assumption bullets, APPROVED status. Pass 2 (quality, budget-tier LLM):
returns `SpecQualityVerdict` with clarity score, testable criteria, boundary
sharpness. ADVISORY is non-blocking; FAIL blocks. Pass 2 skips in CI for local
providers.

**Business analyst workflow** (`/ba`, T1-L-02): state-machine from issue intake
through assumption surfacing, INVEST stories, Gherkin BDD, spec compilation, and
decisions_log feed. Agent drafts; human sets APPROVED. Full description:
`.agent/workflows/business-analyst.md`.

**Project manager workflow** (`/pm`, T1-L-03): orchestration workflow for sprint
planning, task breakdown, and specialist delegation. Full description:
`.agent/workflows/project-manager.md`. Note: this workflow contains
`{{PLACEHOLDER}}` references to project-specific decision files; fill these
with actual file paths before first use.

### Bootstrap utilities

**Install** (`bootstrap/install.py`): stack detection, file copy, hook wiring,
gitignore update (idempotent operational state block — gitignores `session.json`,
`HALT`, wiki, etc. but never `harness_events.jsonl`), `validate.py` run.

**Validate** (`bootstrap/validate.py`): checks Python version, pre-commit hooks,
API key availability, context files, and gitignore correctness. ERROR vs WARN
classified; ERROR exits non-zero.

**Upgrade** (`bootstrap/upgrade.py`): versioned migration chain with chain
contiguity assertion, conflict detection (`.framework-vX.X.X` sidecar files),
pre-flight check, and atomic restore on failure.

**Uninstall** (`bootstrap/uninstall.py`): removes framework files identified by
manifest, preserves developer-created state files, confirmation prompts.

### Skills and workflows

**22 universal skills** in `.agent/skills/universal/`: api-design, c4-architect,
code-migration, code-review, database-design, debugging, devops-cicd, kaizen,
performance-optimization, playwright-skill, python-async, python-automation,
python-fastapi, python-testing, refactoring, security-audit, senior-architect,
systematic-debugging, test-driven-development, test-writing, testing-patterns,
verification-before-completion.

**18 state-machine workflows** in `.agent/workflows/`: feature-implementation,
bug-fix, architect, dba, security, performance, qa, release, devops, deploy,
infrastructure, ux, technical-writer, test-engineer, business-analyst,
project-manager, code-reviewer, eval-pipeline, onboarding.

Workflow routing table: AGENTS.md §2. Skill routing is by agent interpretation
of task type (no automated routing mechanism currently).

### Audit trails

- `.ai-review-log.jsonl` — every verdict (PASS, WARN, FAIL, PASS_FAST, FAIL_OPEN,
  rebuttal outcomes) with typed `ReviewVerdict` fields, token usage, provider
  name, and context snapshot on FAIL/WARN
- `.agent/state/harness_events.jsonl` — typed event log (commit_made,
  halt_bypass, high_risk_gate_closed, gate_bypass, spec_quality_check); this
  file is **committed** to version control and must not be gitignored
- `.agent/state/session_ledger.jsonl` — one JSONL record per closed session
  with outcome, outcome_source, token usage by category

### False positive → eval regression pipeline

`false_positive_to_eval.py` (T1-L-10): converts confirmed false positives
(from rebuttal acceptances or structured SKIP_REASON bypasses) into permanent
"must not flag" regression guards in `tests/data/false_positive_cases.csv`,
consumed by the framework self-test suite.

### Framework self-test suite

181 unit + integration tests. All pass. Covers: gate routing, pre-flight
shortcut, verdict parsing, rebuttal protocol, high-risk classification, spec
quality gate, session lifecycle, upgrade/downgrade migrations, install, validate,
architecture enforcement. 28 E2E scenarios. False-positive regression suite
at `tests/data/false_positive_cases.csv`.

---

## What the Agent Must Do (Non-Negotiable)

1. Run `check_halt.py` → `check_repo.py` → `init_session.py` before any work
2. Read `active_context.md`, `decisions_log.md`, `last_session_summary.md`
3. Name the governing workflow before writing code (AGENTS.md §2)
4. Stage named files only — never `git add .` (P-12)
5. Update `active_context.md`, `decisions_log.md`, `last_session_summary.md`
   at session close
6. Stop and escalate if blocked at the same workflow state more than twice

Full protocol: `.agent/AGENTS.md` and `.agent/governance.md`.

---

## What Is Not Yet Built

The following are in the backlog but **not operational**. Do not assume these
exist or function correctly when working in this project:

### Broken by missing prerequisite
- **`skill_ownership.yaml`** (T1-D-00) — dream phase routing map. Without it,
  all dream proposals attribute to `"agent-framework"` or `"code-review"`.
  Proposals are generated but skill attribution is not meaningful. **Must be
  delivered before dream phase output can be trusted.**
- **`skill_bdd_map.json`** — required by `select_bdd_gate.py`. File does not
  exist; the script exits with an error on any invocation.

### Session and memory
- **Automated token budget HALT trigger** (T1-I-07 partial) — the HALT
  mechanism and HALT file format are in place; no code path currently writes
  `token_budget_exhausted` HALT files automatically. The token budget ceiling
  is not enforced in practice.
- **Audit log consolidation** (T1-I-00a/00b) — `governance_audit.jsonl` and
  `audit_trail.jsonl` may still exist alongside `harness_events.jsonl` in
  existing installations. Dream phase pattern detection does not read them.
- **Memory tiering formalisation** (T1-I-01) — hot tier (last 3 sessions) is
  implemented; warm/cold tier definitions and explicit retention policies are not.
- **Memory retention cleanup** (T1-I-06) — no automated archival of records
  older than configured thresholds.
- **Memory staleness detection** (T1-I-04) — `check_drift.py` does not yet
  verify that identifiers referenced in `review_context.md` still exist in `src/`.

### Outer loop
- **Outer loop methodology profile** (T1-L-00) — no `outer_loop.mode` config
  key. The spec gate and /ba workflow always enforce `incremental` methodology
  assumptions; `discovery` mode downgrade is not implemented.
- **Requirement → commit traceability** (T1-L-04)
- **Acceptance gate** (T1-L-05)
- **Incident → backlog pipeline** (T1-L-07)
- **Mid-session observability** (T1-M-03)

### Reliability
- **Structured HITL approval queue** (T1-C-02) — escalation still uses the
  binary HALT + convention protocol; no structured `pending_approvals.json`.
- **Harness health alerting** (T1-C-03) — `harness_health.py` produces a report
  but does not auto-create GitHub issues for CRITICAL findings.
- **Concurrent write safety** (T1-N-02) — `.ai-review-log.jsonl` and
  `harness_events.jsonl` have no file locking; concurrent commits from parallel
  subagents can corrupt these files.

### Skills
- **Tool ABC subclasses** (T1-E-01) — skills are documentation-only SKILL.md
  files; no `tool.py` executable layer with `run()` interface.
- **Skill deprecation mechanism** (T1-B-04)
- **Self-service skill authoring** (T1-B-05)

### Security
- **`validate.py --security` mode** (S0-17) — hash-and-display governance files
  for integrity verification. Flag not implemented.
- **`docs/security/` context injection point documentation** (S0-18)
- **Formal attack surface review** (T1-K-02)
- **Governance diff highlighting on upgrade** (T1-K-03) — AGENTS.md and
  governance.md changes are not shown as diffs during upgrade unless they
  generate CONFLICT sidecars.
- **GPG-signed releases** (S0-16)

### Multi-agent governance
- **Multi-agent session hierarchy schema** (T1-N-01) — `parent_session_id` and
  `agent_role` fields not yet in `session.json`.
- **HALT sentinel subagent propagation** (T1-N-03)

### Infrastructure (Tier 2 / Tier 3)
- MCP memory server
- SQLite cross-project state index
- All Tier 2 shared-state features (T2-A through T2-D)
- All Tier 3 enterprise infrastructure (PostgreSQL, SSO, RBAC, compliance
  control mappings for SOCI Act / ISM / PSPF)

---

## Known Limitations in Delivered Capabilities

These capabilities are delivered but have material limitations to be aware of:

- **Wiki DOMAIN_REGISTRY is GymBase-specific**: `wiki_compile.py` references 13
  ADR files from the GymBase project. On a non-GymBase install, all compiled wiki
  pages contain `[FILE NOT FOUND]`. ADR injection at review time injects empty
  content. If you are configuring a new project, populate `.agent/config.yaml`
  and supply project-specific ADR files, or accept that ADR context injection is
  inactive until you do.

- **Gate routing uses GymBase path conventions**: `build_route_decision()` in
  `ai_review.py` checks for paths like `src/infrastructure/database/repositories/`
  to activate BRANCH_ISOLATION. Projects with different layouts will not trigger
  capability-specific routing unless they use `# ADR:` annotations or their paths
  happen to match. Use ADR annotations as the primary routing signal.

- **`project-manager.md` contains unresolved placeholders**: `{{PATH_ROADMAP}}`,
  `{{PATH_TECH_SPEC}}`, and ~15 others are GymBase-specific references. Replace
  these with actual file paths in your project before following the PM workflow.

- **`harness_version` in session ledger is hardcoded `"2.0"`**: the ledger field
  cannot be used to trace which harness version was running for a given session.

---

## Capability Changelog

| Version | Date | Key additions |
|---------|------|---------------|
| v1.2.0.1 | 2026-05-31 | BUG-10: gitignore operational state block; validate.py HALT→ERROR, session.json→WARN |
| v1.2.0 | 2026-05-30 | Spec quality gate (check_spec.py), /ba workflow, /pm workflow, uninstall script, upgrade docs, pre-flight validation, migration chain contiguity |
| v1.1.5 | 2026-05-28 | Rebuttal protocol (T1-G-06), token budget WARN/HALT mechanism, diff size stratification, model ORM roster, SKIP_REASON enforcement, false-positive eval pipeline, upgrade migration chain, 181 tests |
| v1.1.0 | 2026-05-23 | LLMProvider ABC, high-risk fail-closed, gate calibration, PASS/PASS_FAST logging, ADR domain mapping, 65-test suite |
| v1.0.0 | 2026-05-21 | Session lifecycle, pre-commit gate, diff-aware routing, architecture checks, PageRank repo map, ADR annotations, compiled wiki, dream phase, co-change estimator, 22 skills, 17 workflows |
