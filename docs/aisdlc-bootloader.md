# AI Delivery Control — Agent Bootloader

> **Read this before your first session in a newly installed project.**
> `bootstrap/install.py` has already run. This document tells you what was installed,
> what you must configure, and how to operate the framework from session one.
> Read this entire document before taking any action.

---

## What Was Installed

`bootstrap/install.py` executed eight phases on this project. The result:

| Component | Location | Purpose |
|---|---|---|
| Harness directory | `.agent/` | Governance, scripts, skills, workflows, state |
| Session protocol | `.agent/AGENTS.md` | Mandatory startup and close sequence for all agents |
| Governance rules | `.agent/governance.md` | Prohibition rationale and escalation triggers (canonical rule list: `.agent/AGENTS.md` §4) |
| Project config | `.agent/config.yaml` | Stack commands, paths, and architecture rules |
| Universal context | `.agent/UNIVERSAL_CONTEXT.md` | Project identity, harness version, key file locations |
| Universal skills | `.agent/skills/` | 22 language-agnostic skill packages, each with `validate.py` |
| Stack-pack skill | `.agent/skills/[stack]/` | Framework-specific skill if stack was detected at install time |
| Delivery workflows | `.agent/workflows/` | 17 state-machine orchestrators covering the full SDLC |
| Pre-commit gate chain | `.pre-commit-config.yaml` | Architecture checks → AI adversarial review → secrets detection |
| AI review gate | `src/scripts/ai_review.py` | Claude-powered adversarial review of every commit diff |
| Universal review layer | `src/scripts/review_context_universal.md` | Framework-owned review invariants — do not edit |
| Project review layer | `src/scripts/review_context_project.md` | Your project-specific invariants — edit this |
| Tool supplements | `CLAUDE.md`, `GEMINI.md`, `.cursorrules` | Thin shims directing each tool to `UNIVERSAL_CONTEXT.md` |

The framework is at **L3 (Enforceable)** on the maturity ladder from day one. See
[Maturity Ladder](#maturity-ladder) for what L4 requires.

---

## Phase 0 — Verify Installation

Run the validator before any other action:

```bash
python bootstrap/validate.py --project-path .
```

All eight checks must pass:

```
✅ Required CLI Tools
✅ Harness Core Directory Layout
✅ Harness Core Files
✅ Repository Guard (G-01)
✅ Universal Context File
✅ Harness Configurations Validity
✅ Pre-commit Git Hook Layout
✅ AI Review Gate Setup
```

A warning on `Required CLI Tools` is acceptable if `pre-commit` is installed inside
a virtualenv that was not active at validation time. Any `FAIL` must be resolved before
proceeding.

Read `.agent/UNIVERSAL_CONTEXT.md`. This file is your project's identity card — project
name, language, package manager, source root, harness version, install date, and key file
locations. Do not proceed to Phase 1 until validation passes and you have read it.

---

## Phase 1 — Configure Your Project

Three files require developer input before the first AI session. Complete all three.

### 1. `.agent/config.yaml` — Architecture layer rules

The installer auto-populated `tech_stack`, `capabilities`, and `paths` from stack
detection. Review them and correct any misdetections. Then define your actual architecture:

```yaml
architecture:
  layers:
    - name: domain
      path: "src/domain"
      forbidden_imports:
        - "src.infrastructure"
        - "src.presentation"
    - name: application
      path: "src/application"
      forbidden_imports:
        - "src.infrastructure"
        - "src.presentation"
    - name: infrastructure
      path: "src/infrastructure"
      forbidden_imports:
        - "src.presentation"
  forbidden_patterns:
    - "os\\.system\\("      # add patterns specific to your codebase
  aggregate_roots: []        # list your domain aggregate root base class names
```

Replace `domain_constraints:` placeholders with your project's actual inviolable rules:

```yaml
domain_constraints:
  - "All database writes must occur inside a transaction"
  - "User data must never cross tenant boundaries"
```

See [Configuration Reference](configuration.md) for every field.

### 2. `src/scripts/review_context_project.md` — Project review invariants

This file is injected into the AI review gate on every commit, after the universal layer.
The installer scaffolded a template with placeholder examples. Replace them with your
project's actual architectural invariants before the first commit.

Minimum viable content:

```markdown
## [RULE:ARCH-BOUNDARIES] Layer boundaries must not be crossed
<!-- SECTION:arch_boundaries -->
Fail if any file in the domain layer imports from infrastructure or presentation.
Fail if any service bypasses the established repository pattern for database access.

## [SENSOR:DIFF-AUDIT] Project Micro-Checks
<!-- SECTION:micro_checks -->

| If the diff adds or changes...  | Then check...                          | Severity |
|---------------------------------|----------------------------------------|----------|
| a new database model            | isolation/scoping filter is present    | HIGH     |
| a new API endpoint              | authorisation check is explicit        | HIGH     |
| a new input schema              | unknown field rejection is configured  | MEDIUM   |
```

See [Customisation Guide](customisation.md) for format conventions.

### 3. `.agent/config/skill_ownership.yaml` — Dream phase routing map

This file routes recurring governance event patterns to the skill that owns them.
The installer scaffolded it from a template. Review the default ownership entries and
add rules for any domain-specific patterns your project is likely to generate.

Without accurate ownership entries, the dream phase writes all proposals to `unrouted/`
rather than the relevant skill files, making them harder to act on.

---

## Phase 2 — Seed ADR Annotations

If your project has architectural decisions documented, add `# ADR: domain_name` comments
to the highest-risk source files. The review gate will inject the relevant context
summary when those files appear in a commit diff.

```python
# ADR: branch_isolation
class TenantScopedRepository:
    ...

# ADR: schema_hardening
class CreateUserRequest(HardenedBaseModel):
    ...
```

Domain names should be consistent across the codebase. Common domains:
`branch_isolation`, `schema_hardening`, `uow_pattern`, `rbac`, `migration_conventions`.

This step can be deferred until the AI review gate begins flagging concerns in high-risk
areas — at that point, ADR annotations prevent the same concern from recurring.

---

## Phase 3 — First Governed Session

### Starting a session

Execute in order — do not skip steps:

```bash
python .agent/scripts/check_halt.py    # exit code 2 means STOP — read the HALT file
python .agent/scripts/check_repo.py    # non-zero means STOP — you are in the wrong project
python .agent/scripts/init_session.py  # establishes session traceability
```

Then read, in order:

1. `.agent/UNIVERSAL_CONTEXT.md` — project identity and key file locations
2. `.agent/state/active_context.md` — current task, branch, and blockers (verify against `git log`)
3. `.agent/state/last_session_summary.md` — what the previous session did (treat as hints if stale)
4. `.agent/AGENTS.md` — mandatory session protocol, workflow-first rules, prohibitions, and session close requirements

State in one sentence: current branch, what the last session did, what the current task is.
Name the governing workflow from `.agent/workflows/` before writing a single line of code.

### Closing a session

Before ending any session that included code changes, complete all four steps:

1. **`.agent/state/active_context.md`** — update: current task, branch, blockers, immediate next steps
2. **`.agent/state/decisions_log.md`** — record any architectural or business decisions made
3. **`.agent/state/last_session_summary.md`** — what was done, what is incomplete, decisions deferred
4. **`.agent/state/session_ledger.md`** — append a row: session ID, date, action summary

Skipping session close is a governance violation. State files are the mechanism for
continuity across sessions and across different agents working on the same project.

---

## Phase 4 — Skill Quality Bar

The 22 universal skills shipped by the framework meet this bar. Hold custom skills to
the same standard. A skill without a `validate.py` is not production-grade.

| Element | Why it matters | Minimum |
|---|---|---|
| **Operating procedure** | Step-by-step workflow the agent follows without ambiguity | 10+ numbered steps |
| **Code examples** | Show the right way (✅) and wrong way (❌) side by side | 2+ pairs |
| **Anti-patterns table** | Explicitly list what not to do and the reason why | 5+ entries |
| **Escalation triggers** | Conditions where the skill must stop and ask the human | 3+ conditions |
| **`validate.py` script** | Mechanical enforcement the agent cannot bypass | Must exit 0 before task is complete |

An agent invoking a skill **must** run `validate.py` before declaring the task done.
If the script exits non-zero, the task is not complete — fix the issue and re-run.
If the script fails more than twice with the same error, escalate to the user — do not retry indefinitely.

All `validate.py` scripts must include the cross-platform encoding fix at the top:

```python
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

See [Customisation Guide](customisation.md) for the full skill creation procedure.

---

## Phase 5 — Workflow Conventions

Workflows are state machines, not checklists. Each defines explicit **states**,
**transitions**, **guards** (conditions that must be true before a transition), and
**BLOCKED conditions** (what happens when a guard fails).

Before any task involving code changes across more than one file or layer:

1. Name the governing workflow from `.agent/workflows/`
2. Announce it — e.g. "This is a `/feature-implementation` task, starting at Phase 2."
3. Follow the workflow phases in order. Direct user instructions do not override workflow phases.
4. If blocked at the same state more than twice, stop and escalate — never retry indefinitely.

The quick-task exception: single-file fixes, documentation edits, and config tweaks may
proceed directly without naming a workflow.

The seventeen workflows in `.agent/workflows/` cover: feature implementation, bug fix,
architecture decisions, database and migrations, security, performance, quality assurance,
release, CI/CD, deploy, infrastructure, UX, technical writing, business analysis, project
management, code review, and eval pipeline. Read the governing workflow file before starting —
not after three files have changed.

---

## Phase 6 — The Self-Improvement Loop

The harness accumulates data automatically with every session. No configuration is required
beyond Phase 1. The loop operates as follows:

**Data accumulation (every session):**
- `init_session.py` writes a session record to `session_ledger.md`
- The pre-commit AI review gate logs structured verdicts to `.ai-review-log.jsonl` (gitignored)
- Governance events write to `.agent/state/harness_events.jsonl` (gitignored)

**Dream phase — not yet operational (T1-D-03, backlog):**
`distill_dream.py` is not yet implemented. Data accumulation above runs today and is
building the event history the dream phase will read once delivered. The intended
design when implemented:
- Threshold: ≥15 sessions spanning ≥14 days, with ≥7 days since last run
- `distill_dream.py` reads event patterns, identifies recurring failures, routes proposals to owning skills via `skill_ownership.yaml`
- Proposals appear in `.agent/state/dream_proposals/` as `{skill}__{pattern}__open.md`
- Monthly human review: Accept → apply + rename `__reviewed.md`; Reject → note + rename; Modify → apply modified version + rename
- `__open` and `__contradiction` proposals require explicit human action before archival

After any escaped defect reaches production, run:
```bash
python .agent/evals/incident_to_eval.py
```
This converts the incident into a permanent regression guard in the golden dataset.

---

## Maturity Ladder

The install script delivers **L3** on day one. L4 requires sustained operation.

| Level | Reached when... | Skills | Gates active | Context engine |
|---|---|---|---|---|
| **L1 Bootstrap** | Framework files in place | 3 skills, basic procedures | Standard linting only | `AGENTS.md` loaded at session start |
| **L2 Operational** | First project invariants added to review context | 8–12 skills with code examples | + type check, bandit, pip-audit | 10+ context docs; staleness thresholds set |
| **L3 Enforceable** ← *install delivers this* | All skills have `validate.py`; AI review gate active; architecture checks defined | All 22 framework skills; stack-pack installed; custom skills validated | + AST architecture checks + AI adversarial review + secrets detection | `review_context_project.md` populated; `UNIVERSAL_CONTEXT.md` version-stamped |
| **L4 Self-Improving** | Dream phase has fired; at least one proposal accepted into a skill | Skills evolving from real session incidents; regression runner in CI | + AI review trend analysis; behaviour EDD active; file churn detection | Incident-to-eval pipeline closing the learning loop; staleness detection on review context |

The single biggest accelerators to L4: populate `review_context_project.md` with real
invariants from your first month of use, review dream proposals when they appear, and run
`incident_to_eval.py` after every escaped defect.

---

## Governance Quick Reference

**The canonical prohibition list is [`.agent/AGENTS.md`](../.agent/AGENTS.md) §4.** It is
loaded by every agent tool and is the single source of truth. Rationale, failure modes, and
the legacy-ID map live in `.agent/governance.md` §3. This document does **not** restate the
rules — the previous P-series table here is retired to avoid a competing rule list.

Prohibitions are tiered:

- **Tier 1 — Universal** (`AGENTS.md` §4.1): the `H/S/C/G` series — Honesty/verification (H),
  Scope/autonomy (S), Security (C), and Version control (G) — apply to every project unconditionally.
- **Tier 2 — Project-Specific** (`AGENTS.md` §4.2) and **Tier 3 — Pattern-Conditional**
  (`AGENTS.md` §4.3): apply only given a project's stack choices or an active architectural pattern.

When an escalation trigger fires: stop immediately. No commits, no fixes, no compensating
work of any kind. Report findings and wait for explicit human instruction before proceeding.
