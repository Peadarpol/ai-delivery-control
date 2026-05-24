# AI Delivery Control — Agent Capability Briefing

**Framework version**: v1.1.0
**Last updated**: 2026-05-24
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
any LLM-based agent (Claude Code, Gemini CLI, Cursor, Windsurf) through shim
files (`CLAUDE.md`, `GEMINI.md`, `.cursorrules`).

---

## Currently Delivered Capabilities (v1.0.0–v1.1.0)

### Session lifecycle management

`init_session.py` establishes a UUID-tracked session on startup. `check_halt.py`
detects a HALT sentinel file and stops the agent before any work begins.
`check_repo.py` verifies the agent is operating in the correct repository
(P-14 guard). Four markdown state files carry context across sessions:
`active_context.md`, `decisions_log.md`, `last_session_summary.md`,
`session_ledger.md`. Agents are required to update all four at session close.

### Pre-commit AI adversarial review gate

Every `git commit` fires a structured review gate (`src/scripts/ai_review.py`)
via pre-commit hooks at the `commit-msg` stage. The gate reads the diff, loads
two context layers (universal framework invariants + project-specific invariants),
and calls a cloud LLM (default: Claude Sonnet). It produces a typed verdict —
`PASS`, `PASS_FAST`, `WARN`, `FAIL`, or `FAIL_OPEN` — logged to
`.ai-review-log.jsonl`. `FAIL` blocks the commit. `PASS_FAST` is returned for
trivial diffs (docs, whitespace) without an API call. The gate is
provider-agnostic: Anthropic, OpenAI-compatible, or local Ollama via
`LLMProvider ABC`.

### Diff-aware capability routing

Before the LLM call, a `RouteDecision` step classifies the diff and selects
which review dimensions to activate (e.g. `BRANCH_ISOLATION` only when repository
files change, `ANTI_PATTERNS` only when schema files change). PageRank scores from
a repo map (`repo_map.py`) elevate review intensity for high-centrality files.
`# ADR: domain_name` annotations in source files inject the relevant compiled wiki
page into the review context.

### Architecture boundary enforcement

AST-based checks (`architecture_checks.py`) scan the diff for layer boundary
violations and forbidden import patterns as defined in `.agent/config.yaml`.
Config-driven — no hardcoded language assumptions.

### High-risk commit classification

When the Anthropic API is unavailable, low-risk commits (docs, config) fail open.
Commits touching high-risk files (`*/migrations/*`, `*/auth/*`, `*/rbac/*`,
`unit_of_work.py`, etc.) fail closed — they cannot proceed without
`SKIP_AI_REVIEW=1 SKIP_REASON="..."` explicitly set, which is logged to
`harness_events.jsonl`.

### 22 universal skills + 2 stack-packs

Each skill ships with an operating procedure, code examples (correct/incorrect),
an anti-patterns table, escalation triggers, and a `validate.py` script that must
exit 0 before the task is declared complete. Stack-packs (python-fastapi,
node-express) are auto-selected at install time. Skill routing is driven by
`skill_mapping.yaml`.

### 17 state-machine workflows

Named workflows in `.agent/workflows/` govern all non-trivial tasks:
feature-implementation, bug-fix, architect, dba, security, perf, qa, release,
CI/CD, deploy, infrastructure, UX, technical-writing, business-analyst,
project-manager, code-review, eval-pipeline. Agents must name the governing
workflow before writing any code.

### Compiled wiki layer

`wiki_compile.py` synthesises ADRs, review context sections, and skill rules into
domain-specific wiki pages (`.agent/wiki/{domain}.md`) using a local
Ollama/Gemma4 model. These are injected at review time via ADR annotations.

### Knowledge base lint

Weekly batch pass (`harness_health.py`) checks for staleness (identifiers in
`review_context.md` that no longer exist in `src/`), factual drift between wiki
pages and source ADRs, orphaned rules, and cross-file contradictions.

### Framework self-test suite

65 tests covering the gate (golden-path, adversarial, false-positive regression),
architecture checks, install script, and validate script.

### Incident-to-eval pipeline

`incident_to_eval.py` converts a production defect into a permanent regression
guard in the golden eval dataset, closing the feedback loop from production to
governed delivery.

---

## What the Agent Must Do (Non-Negotiable)

1. Run `check_halt.py` → `check_repo.py` → `init_session.py` before any work
2. Read `UNIVERSAL_CONTEXT.md`, `active_context.md`, `decisions_log.md`,
   `last_session_summary.md`
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

- Dream phase distillation (`distill_dream.py`) — pattern detection across sessions
- Session memory claim verification in `init_session.py`
- Retrospective session outcome inference
- MCP memory server (Tier 2 — requires shared infrastructure)
- SQLite cross-project state index
- HITL structured approval queue
- Spec quality gate and `/ba` workflow
- Requirement → commit traceability check
- All Tier 3 enterprise infrastructure (PostgreSQL, SSO, RBAC, compliance mappings)

Backlog detail: `docs/planning/FRAMEWORK_BACKLOG.md`.

---

## Capability Changelog

| Version | Date | Change |
|---------|------|--------|
| v1.1.0 | 2026-05-23 | LLMProvider ABC (Anthropic/OpenAI/Ollama), high-risk commit classification, 65-test self-test suite, gate calibration fix, PASS/PASS_FAST verdict logging, ADR domain→capability mapping |
| v1.0.0 | 2026-05-21 | Initial delivery: session lifecycle, pre-commit gate, diff-aware routing, architecture checks, PageRank repo map, ADR annotations, compiled wiki, 22 skills, 17 workflows |
