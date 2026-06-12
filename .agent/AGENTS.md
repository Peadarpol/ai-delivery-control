# AGENTS.md — Cross-Tool Agent Standard

> **Scope**: Loaded automatically by Gemini CLI, Claude Code, Cursor, Windsurf, and other editors.
> This file contains portable, tool-agnostic rules shared across all AI agents in this project.
> Tool-specific additions live in `CLAUDE.md`, `GEMINI.md`, and `.cursorrules`.
> Full governance rules: `.agent/governance.md`. Commands & paths: `.agent/config.yaml`.

---

## Project Identity

**[PROJECT_NAME]** — [PROJECT_DESCRIPTION]
Clean Architecture or custom design patterns.
Type safety and defensive programming.

## Architectural Invariants

The canonical source for all architectural invariants (routing, DB patterns, business rules) is:
  `{{PATH_REVIEW_CONTEXT}}`

This file is injected into every AI review. Governance rules in this file and in `.agent/governance.md` are the enforcement layer; the review context is the specification layer.

---

## 1. Session Startup (mandatory — before touching any code)

## Step 0 — Verify Active Repository (mandatory)
Run `python .agent/scripts/check_repo.py` before reading any files
or taking any actions. If the check fails, stop the session immediately
and switch to the correct project in your IDE.

**Note**: If running in Claude Code, `init_session.py` is invoked automatically via
a SessionStart hook (`.claude/settings.json`). For other agents (Gemini CLI, Cursor,
etc.), Step 0 below remains a manual convention.

0. Run: `python .agent/scripts/check_halt.py`. If exit code 2: STOP. Do not proceed. Read the `.agent/state/HALT` file contents and report to the user.
   Run: `python .agent/scripts/init_session.py` to establish session traceability.
1. Run `git log --oneline -5` and `git branch` — establish ground truth on branch and recent work.
2. Read `.agent/state/active_context.md` — verify against git log; the file is often stale.
3. Read `.agent/state/decisions_log.md` — understand architectural/business decisions for the project.
4. Read `.agent/state/last_session_summary.md` — treat as hints, not facts if stale.
5. State in one sentence: current branch, what the last session did, what the current task is.
6. Identify the governing workflow (§2) before writing a single line of code.

---

## 2. Workflow-First (non-negotiable for non-trivial tasks)

Before any task involving code changes across more than one file or layer:

1. **Name the governing workflow** from `.agent/workflows/`. If none fits, say so and ask.
2. **Announce it** — e.g. "This is a `/feature-implementation` task, starting at Phase 2.5."
3. Follow the workflow phases in order. Direct user instructions do not override workflow phases.

**Quick-task exception**: Single-file fixes, docs edits, config tweaks — proceed directly.
**Ambiguous scope**: Ask before starting, not after three files have changed.

| Task type | Governing workflow |
|---|---|
| New feature or requirement | `/feature-implementation` |
| Production bug | `/bug-fix` |
| Architecture decision | `/architect` |
| Schema / migration change | `/dba` |
| Security concern | `/security` |
| Performance issue | `/perf` |
| Tests only | `/qa` or `/test-engineer` |
| Release / changelog | `/release` |

---

## 3. Agent Conduct

**No sycophancy.** Flag risks directly. Disagree when evidence supports it. A plan review is quality assurance, not approval-seeking — comfortable agreement at planning time is more expensive than an uncomfortable flag caught early.

**No placeholders.** Produce complete, usable output. If you cannot produce a complete solution, state what is missing — do not fill the gap with `# TODO: implement this` or stub functions. Incomplete implementations that pass review cause the same harm as missed requirements.

**No scope creep under obstacle.** Encountering a blocker mid-task does not authorise fixing adjacent problems, expanding scope, or taking compensating actions. Stop at the blocker, report it, and wait. The user decides what happens next.

**No out-of-scope file modification to unblock a task.** If a task fails because a file outside that task's scope contains an error, do not fix the out-of-scope file — stop and report. The file that caused the failure is not yours to change.

> Example: if a seeding task fails because a migration contains an error, the migration is out of scope — stop and report, do not fix the migration to unblock the seeding task.

---

## 4. Absolute Prohibitions (never without explicit user instruction)

| # | Never do this |
|---|---|
| P-01 | Merge to `main`/`master` |
| P-02 | Delete migration/schema files |
| P-03 | Disable or weaken test assertions to make tests pass |
| P-04 | Skip writing tests for new functionality (TDD Iron Law) |
| P-05 | Install new dependencies without listing them for user approval |
| P-06 | Commit secrets, API keys, or credentials |
| P-07 | Use unapproved package installers (always use project-specific package manager) |
| P-08 | Import infrastructure layer from domain/business layers |
| P-09 | Access database sessions directly, bypassing Repository/UoW (where pattern is active) |
| P-10 | Modify `.env` files without documenting the change |
| P-11 | Commit or push without completing local verification first — **CI is not a substitute for local verification. If you cannot verify locally, stop and say so. Do not commit and push hoping CI will catch it.** |
| P-12 | Use `git add .` or `git add -A` — always stage named files only |
| P-13 | Stage agent-generated files or log files (`AGENTS.md`, `harness_events.jsonl`, `session_ledger.jsonl`, `dream_phase_state.json`, brain files, session logs, etc.) in git commits |
| P-14 | Perform any git add, commit, merge, or push without verifying the active repository matches the intended project. |
| P-15 | Direct commits to deployment/devops branches for CI/CD fixes: Create a short-lived branch, merge to devops, then merge back to active feature branch |

Full rationale in `.agent/governance.md` §3.

---

## 5. Escalation — Stop and Ask the Human

> [!IMPORTANT]
> **"Report findings and wait" means no further action of any kind — no commits, no fixes, no staging, no compensating work.** Stop where you are and report.
>
> **If instructed to revert and report:** the revert is the first action. Nothing else happens before the revert is complete and the findings are reported. Do not fix, do not stage, do not push. Wait for explicit instruction.
>
> A push or commit made without explicit approval after a stop instruction is a governance breach regardless of whether the work was correct.

Stop immediately and ask if you are about to:
- Delete or rename more than one file
- Drop, truncate, or irreversibly alter a database table
- Modify tenant/multi-tenant isolation logic
- Modify authentication, authorisation, or RBAC code
- Deploy to staging or production, or modify CI/CD pipelines
- Proceed after being blocked at the same state more than twice

Full trigger list in `.agent/governance.md` §2.

---

## 6. Session Close (MANDATORY — do this before ending any session with code changes)

### Session state design principle

The goal of the session close protocol is that the next session can reconstruct its
starting position entirely from structured state files — without needing conversation
history. `active_context.md`, `decisions_log.md`, `last_session_summary.md`, and
`session.json` are the full context a fresh session needs.

Compaction is a fallback for when a session cannot be closed cleanly. A clean close
followed by a fresh session start is always preferable to a compacted continuation,
because a fresh session operates in the smart zone from the first token. A compacted
continuation carries sediment — prior reasoning, explored paths, discarded options —
that consumes context budget without contributing governance value.

When in doubt: close cleanly, write good state files, start fresh.

1. **MUST review the task magnitude auto-classification** in `session.json`. You **NEVER downgrade** a session from `major` to `micro` without explicit, documented justification in `session.json` (`task_magnitude_override_reason`).
2. **MUST run context compaction** (`python .agent/skills/meta/validate.py`) whenever the rolling spent has passed 80% of its budget ceiling.
3. **ALWAYS complete the compaction/handoff template** `.agent/skills/meta/context-compaction.md` in full prior to close.
4. **MUST update `.agent/state/active_context.md`** — current task, branch, blockers, immediate next steps.
5. **MUST update `.agent/state/decisions_log.md`** — document all technical, design, and business decisions made during this session. **Archival check**: if `decisions_log.md` exceeds **150 lines**, archive the oldest entries to `.agent/state/decisions_log_archive.md` before adding new ones — the review gate injects this file into every review context.
6. **MUST update `.agent/state/last_session_summary.md`** — what was done, what's incomplete, decisions deferred.
7. **MUST append a row to `.agent/state/session_ledger.jsonl` and `.agent/state/session_ledger.md`** — session ID, date, action summary.

---

## 7. Skills to Create Before Starting These Work Streams

The following planned work streams do not yet have covering skills.
**Before the first coding task in each stream, pause and create the required skills.**

| Planned work stream | Skills required before starting | Notes |
|---|---|---|
| **[Example Stream]** | `[example-skill]` | Description of what the skill needs to cover to support the team. |

Full gap analysis and rationale: `.agent/state/harness_improvement_backlog.md`.

---

## 8. Git Discipline

### 8.1 Staging rules

- **Always stage named files only.** `git add .` and `git add -A` are prohibited (P-12).
- **Never stage files outside the repository root.**
- **Never stage agent-generated files** (P-13): `AGENTS.md`, brain files, session logs, `active_context.md`, `decisions_log.md`, `last_session_summary.md`, `session_ledger.md`.
- **Documentation commits with code.** All documentation updates (walkthrough, task files, harness logs) must be committed in the same commit as the code they describe — never a follow-up commit. Prepare everything locally first, then commit once.

### 8.2 Verification before commit

> [!IMPORTANT]
> **Verification is mandatory before every commit and push. It is never optional and never skipped to save time.**
> - Verification must be run against a **clean state** — not an already-seeded or in-progress local database.
> - If you cannot run the verification suite (environment broken, tests hanging, tool unavailable), **stop and report**. Do not commit. Do not push. Do not defer to CI.
> - CI failure is not a substitute for local verification. A commit or push made without completing local verification is a governance breach.

### 8.3 Push timing

Before any `git push` to the devops/main branch, check if the deployment pipeline is already in progress from another push. Stage your changes locally and coordinate to prevent conflicts.

### 8.4 Branch Strategy for CI Fixes

When a CI/CD pipeline fails after a push:

1. Create a short-lived fix branch: `git checkout -b fix/ci-description`
2. Implement the fix
3. Merge to the build branch
4. Merge back to the active feature branch to prevent divergence
5. Delete the fix branch

**Exception**: Trivial one-line typo fixes may be made directly with a warning acknowledged in the commit message: `[direct-devops: trivial]`

### 8.5 Branching Conventions

All framework work must develop on dedicated feature branches before merging via Pull Request:
  `feat/framework-{item-id}-{short-description} → PR → main`

### 8.6 Gate Governance Escalation Hierarchy

When the AI review gate returns a `FAIL` verdict, agents and developers MUST adhere to the following escalation hierarchy:

1. **Fix the actual problem** (First Priority): Always attempt to resolve the underlying code quality, security, or architectural issue directly.
2. **Structured Rebuttal** (Governed Contest): If a finding is believed to be a false positive or is specifically required, create `.agent/state/gate_rebuttal.json`. 
   - **Agent Mandate**: **Agents MUST NOT self-execute the `--rebuttal` command.** Writing the rebuttal file and presenting the argument to the human operator is the agent's sole action. The human reviews the argument and explicitly runs: `python src/scripts/ai_review.py --rebuttal`.
   - **Rebuttal Evidence Checklist**: Assertions without verifiable facts will be rejected. Every rebuttal entry must satisfy this checklist:
     1. **Quote the actual commit message verbatim**.
     2. **State the spec ID and its current status** (e.g., SPEC-123, status APPROVED).
     3. **Cite the specific acceptance criteria** the diff implements.
     4. **Describe what the diff actually contains** — including file names, line count, and the exact nature of the change.
   - **Worked Example (Weak vs. Strong Evidence)**:
     ```json
     // WEAK EVIDENCE (Will be REJECTED)
     {
       "finding_id": "FID-123",
       "rebuttal_type": "FALSE_POSITIVE",
       "evidence": "This is a false positive. The warning is wrong, this is not domain code, it is safe to bypass."
     }

     // STRONG EVIDENCE (Verifiable Facts - ACCEPTED)
     {
       "finding_id": "FID-123",
       "rebuttal_type": "FALSE_POSITIVE",
       "spec_reference": "docs/planning/specs/SPEC-456.md#L20-L25",
       "evidence": "Commit message verbatim: 'feat: add local seed helper script'. Spec ID: SPEC-456 (Status: APPROVED). Implements Acceptance Criteria 3.1: 'Provide a standalone local CLI helper to seed test user profiles'. Diff details: New file 'src/infrastructure/database/seed_helper.py' (42 lines) containing utility functions only. This code resides entirely in the infrastructure layer, and is not imported by nor affects the domain or business layer core rules (ref: ARCH-02)."
     }
     ```
3. **Structured SKIP_REASON bypass** (Acknowledged Override): Only as a last resort in emergencies, use `SKIP_AI_REVIEW=1` with a structured bypass JSON to step aside.

### Reading Gate Findings

From v1.3.3, FAIL and qualifying WARN findings use the decision block format:

- **Finding** — what the code does (not a judgment)
- **Tradeoff** — which AT tradeoff is being violated and in which direction
- **Exposes** — which FM failure mode this creates, with file:line for FM4/FM10
- **Remediation** — the specific change that resolves the FM

When contesting a finding via the rebuttal protocol, address the **Exposes** line
specifically. A rebuttal that does not explain why the named FM does not apply to
this specific file and context will be rejected.

### 9 Environment Progression (mandatory gate sequence)

Before raising any PR, the agent must confirm which environment gates apply to this project. The project's environment progression is defined in .agent/config.yaml under environments: or in the governing workflow file.

No gate may be skipped. The sequence is always:
  Local verification → Local staging gate → CI →   Staging → UAT → Production

The specific commands, URLs, and UAT criteria for each gate are project-specific and live in the project's workflow files and config.
