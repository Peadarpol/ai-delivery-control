# Glossary

Essential terms used throughout the framework.

## Core Concepts

### Agent
An AI coding tool (Claude Code, Gemini CLI, Cursor, Windsurf) operating under framework governance. The agent reads mandatory context files and follows prescribed workflows.

### Pre-Commit Gate (AI Review Gate)
The enforcement mechanism that triggers on every `git commit`. An independent AI model reviews the diff against universal and project-specific review rules. Verdict determines whether the commit proceeds.

**Verdicts:**
- `PASS` — code meets all requirements
- `PASS_FAST` — trivial diff (docs, whitespace) bypasses LLM call
- `WARN` — code has issues but can ship; developer should address
- `FAIL` — code cannot ship; violates security, architecture, or data integrity rule
- `FAIL_OPEN` — LLM provider unavailable and diff is low-risk; commit proceeds

### Workflow
A named, state-machine task type. Before any substantive code change, the agent announces which workflow it's following. Examples: `/feature-implementation`, `/bug-fix`, `/architect`, `/security`.

### Skill
A portable, executable policy document describing how to approach a task type. Each skill has:
- A `SKILL.md` file with rules and approach
- An optional `validate.py` script that must exit 0 before task completion
- Universal skills ship with the framework; custom skills are project-specific

### Session
A contiguous period of work by an agent. Each session:
- Gets a unique UUID on startup
- Carries forward context from previous sessions
- Updates four state files at close: `active_context.md`, `decisions_log.md`, `last_session_summary.md`, `session_ledger.jsonl`
- Is logged in `harness_events.jsonl`

### Spec (Specification)
A requirements document written in Gherkin BDD syntax, approved by a human before implementation begins. Specs are traced in commits via `SPEC-\d+` references.

### Outer Loop
The full delivery path from business need to working code:
1. Requirement → `/business-analyst` workflow → spec drafted
2. Spec approved by human architect
3. Spec → `/project-manager` workflow → sprint tasks
4. Every commit references a spec via `SPEC-\d+`
5. Before PR, acceptance gate verifies implementation satisfies spec intent

### Dream Phase
A self-improvement loop that runs weekly. It:
1. Reads 30 days of failure patterns from `.ai-review-log.jsonl` and `harness_events.jsonl`
2. Identifies recurring issues
3. Generates structured proposals to fix them
4. Routes proposals to the right skill file
5. Requires human review before application

---

## Gate & Verdict Concepts

### Routing Decision
Pre-LLM classification of the diff. Based on file paths and a repo map (PageRank), it:
- Selects which review dimensions to activate
- Injects ADR domain annotations if present
- Elevates review intensity for high-centrality files

### ADR Domain Annotation
A comment in source code: `# ADR: domain_name`. It links that code to a domain-specific wiki page, which is injected into the review context for that diff.

### Architecture Boundary Check
AST-based validation that runs before the LLM call. It scans for:
- Layer boundary violations (e.g., domain layer importing infrastructure)
- Forbidden code patterns (e.g., `os.system`, `eval`)

### High-Risk Commit Classification
Diffs touching sensitive files (migrations, auth, RBAC) fail open only if the LLM provider is unavailable. They fail closed (require `SKIP_AI_REVIEW=1` with reason) if the provider is reachable.

### False Positive Protocol
When a developer believes the gate issued an incorrect `FAIL`:
1. Write `.agent/state/gate_rebuttal.json` with the argument
2. The gate gets a second opinion from another model
3. Accepted rebuttals feed back into permanent regression guards

---

## Session & State Concepts

### Active Context
File: `.agent/state/active_context.md`. Captures the current task, current branch, immediate next steps, and any blockers. Updated at session close.

### Decisions Log
File: `.agent/state/decisions_log.md`. Cumulative record of all technical, architectural, and business decisions made during this project's AI-assisted work. Never deleted.

### Session Ledger
File: `.agent/state/session_ledger.jsonl`. Timestamped inventory of all sessions: UUID, date, action summary, outcome classification.

### Session Summary
File: `.agent/state/last_session_summary.md`. What was accomplished in the most recent session, what's incomplete, and deferred decisions. Used to orient the next session.

### Harness Events
File: `.harness_events.jsonl`. Governance events: gate verdicts, escalations, rebuttal outcomes, skips, etc. Fed into the dream phase for self-improvement.

---

## Configuration & Customization

### Review Context
Two-layer document injected into every gate call:

| Layer | File | Owner | What |
|-------|------|-------|------|
| Universal | `src/scripts/review_context_universal.md` | Framework | Common failure modes (shipped with framework) |
| Project | `src/scripts/review_context_project.md` | You | Custom rules specific to your codebase |

### Architecture Layers
Config: `.agent/config.yaml` → `architecture.layers`. Each layer:
- Has a name and path (e.g., `domain: src/domain`)
- Lists forbidden imports (e.g., domain cannot import infrastructure)

### Domain Constraints
Config: `.agent/config.yaml` → `domain_constraints`. Plain-English list of inviolable rules (e.g., "tenant isolation on all multi-tenant queries").

### Capabilities Map
Config: `.agent/config.yaml` → `capabilities`. Maps logical operations to shell commands for your stack:
- `test.run_all` → `poetry run pytest`
- `db.migrate` → `poetry run alembic upgrade head`
- etc.

### Model Routing
Config: `.agent/config.yaml` → `model_routing`. Specifies which LLM provider/model handles each task:
- `review_provider` / `review_model` — the gate (usually Claude Sonnet)
- `budget_provider` / `budget_model` — low-cost tasks (wiki compile, etc.)

---

## Workflow & Task Concepts

### Workflow Phase
A named state in a workflow's state machine. Agents must progress through phases in order. Cannot skip or backtrack without explicit user instruction.

### Escalation Trigger
A condition that forces the agent to stop and ask rather than proceed. Examples:
- Deleting more than one file
- Modifying auth/RBAC code
- Being blocked at the same state twice

### P-01 through P-15
Absolute prohibitions. Never do these without explicit user instruction:
- P-01: Merge to main
- P-02: Delete migration/schema files
- P-03: Disable test assertions
- ... (15 total)

See [Governance Rules](Governance-Rules.md) for full list and rationale.

---

## Gate & Review Concepts

### Universal Rules
Framework-shipped review rules in `src/scripts/review_context_universal.md`. Read-only; covers common failure modes.

### Project Rules
Custom review rules in `src/scripts/review_context_project.md`. You define these using a structured format:
```markdown
## [RULE:YOUR-ID] Title
<!-- SECTION:section_id -->
Plain English description of what to check and what severity warrants FAIL vs. WARN.
```

### Micro-Check Table
Optional table in project rules listing specific patterns and what to check for:

| If the diff adds or changes... | Then check... | Severity |
|---|---|---|
| a new Pydantic schema | `extra="forbid"` is set | HIGH |

### Rule Severity
- `FAIL` — code cannot ship (security, data integrity, architecture)
- `WARN` — should be addressed but doesn't block (style, incomplete coverage)

---

## Skill Concepts

### Validate.py
Executable script paired with a skill. The agent runs it before declaring the task complete. Exit code:
- `0` (success) — task is complete
- `1` (failure) — something is wrong; blocks completion

### Skill Directory Structure
```
.agent/skills/
├── universal-skill-name/
│   ├── SKILL.md
│   └── validate.py
└── your-custom-skill/
    ├── SKILL.md
    └── validate.py (optional)
```

---

*Last updated: 2026-06-04*