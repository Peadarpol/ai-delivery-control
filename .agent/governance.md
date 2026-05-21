# Agent Governance Rules

> **Scope**: These rules apply to ALL agents working in this project, including sub-agents spawned by orchestrating agents (e.g., when `/project-manager` delegates to `/architect` or `/qa`).

---

## 1. Mandatory Pre-Task Checks

Before starting any coding task, you MUST:

1. **Read domain context**: `docs/decisions/business_rules.md` (canonical source for domain and business rules).
2. **Read architecture**: `docs/architecture/ARCHITECTURE.md` — verify layer boundaries haven't changed.
3. **Identify the governing workflow**: Determine which workflow applies (e.g., `feature-implementation.md`, `bug-fix.md`). If unsure, ask the user.
4. **Check session state**: Read `.agent/state/active_context.md` and `.agent/state/decisions_log.md` for continuity and architectural truth.
5. **Confirm starting state**: You must be starting from IDLE, not resuming mid-workflow without context.

---

## 2. Escalation Triggers — STOP and Ask the Human

You MUST suspend execution and ask the user for guidance if **any** of the following conditions are true:

### Destructive Scope
- You are about to **delete or rename more than one file**.
- You are about to **drop, truncate, or irreversibly alter a database table**.
- You are about to **modify a database schema without creating a migration script**.
- You are about to **open a PR to `devops` with a new migration that has not passed the Docker staging Postgres stairway test** (Phase 3.5 of `/dba`).
- You are about to **commit in a different structure or sequence than explicitly approved in the implementation plan**.
- You are about to **remove or weaken a test assertion** to make a test pass.

### Domain Safety
- You are about to **modify an inviolable rule** listed in `docs/decisions/business_rules.md`.
- You are about to **change multi-tenant isolation logic** (`branch_id` filtering).
- You are about to **modify authentication, authorization, or RBAC code**.
- You are about to **change how sensitive data (PII, passwords, tokens) is handled**.

### Process Safety
- You have been **blocked at the same workflow state more than twice** with the same error.
- A **validate script has failed more than twice** with the same error.
- You are **unsure which workflow applies** to the current task.
- You encounter **contradictions between decision log files** (e.g., `business_rules.md` says X but `requirements_log.md` says Y).

### Infrastructure Safety
- You are about to **merge to main/master branch**.
- You are about to **deploy to staging or production**.
- You are about to **modify CI/CD pipeline configuration**.
- You are about to **change environment variable names** in production config.

---

## 3. Absolute Prohibitions — NEVER Do Without Explicit Human Instruction

The following actions are **unconditionally forbidden** unless the user explicitly requests them in the current session:

| # | Prohibition | Reason |
|---|---|---|
| P-01 | **Merge to main/master** | Requires human review and CI approval |
| P-02 | **Delete migration files** | Destroys database version history |
| P-03 | **Disable or weaken test assertions** to make tests pass | Masks real failures |
| P-04 | **Skip writing tests** for new functionality | Violates TDD Iron Law |
| P-05 | **Install new dependencies** without listing them for approval | Supply chain risk |
| P-06 | **Commit secrets, API keys, or credentials** to version control | Security violation |
| P-07 | **Use `pip install` directly** instead of `poetry add` | Breaks dependency lock |
| P-08 | **Import infrastructure from domain layer** | Architecture violation |
| P-09 | **Access database sessions directly** (bypass Repository/UoW) | Transactional safety |
| P-10 | Modify `.env` files without documenting the change | Environment drift |
| P-11 | Create or modify `task.json` (Phase 4 of `/pm`) | Process consistency |
| P-12 | Use `--no-verify` on any commit containing source code or agent scripts | Bypasses all harness gates; use `SKIP_AI_REVIEW=1` for AI-only false positives |
| P-13 | Stage agent-generated log files (`harness_events.jsonl`, `session_ledger.jsonl`, `dream_phase_state.json`, etc.) in git commits | Pollutes commit history; these are local-only state files, not source artefacts |
| P-14 | Perform any git add, commit, merge, or push without verifying the active repository matches the intended project. | Run `python .agent/scripts/check_repo.py` first. STOP immediately if the check fails — you are in the wrong project. |
| P-15 | Direct commits to `devops` for CI/CD fixes | Create a `fix/` branch, merge to `devops`, then merge `devops` back to the active feature branch to prevent divergence |

---

## 4. Handling Uncertainty

Agents do **not** generate numeric confidence scores for individual decisions. Instead, when facing uncertainty, follow this protocol:

### Before any destructive or wide-scope action:
1. Write a plain-English uncertainty statement:
   > "I am uncertain about **[X]** because **[reason]**. I will proceed only with **[Y limited scope]** unless you confirm the broader change."
2. **WAIT** for human confirmation before proceeding.

### When multiple approaches are viable:
1. Present no more than **3 options** with pros/cons.
2. Clearly recommend one and explain why.
3. Let the user decide.

### When you don't know:
1. Say "I don't know" explicitly.
2. Do **not** guess or generate plausible-sounding but unverified answers.
3. Suggest a specific investigation step to find the answer.

---

## 5. Skill Validation Enforcement

When a skill has a `scripts/validate.py` (or `validate.sh`):

1. The agent **MUST** run the validation script before declaring a task complete.
2. If the script exits non-zero, the task is **NOT complete** — fix the issue and re-run.
3. If the script fails more than twice with the same error, **escalate to the user** (see §2).

### Available Validate Scripts

| Skill | Script | What It Checks |
|---|---|---|
| `systematic-debugging` | `scripts/validate.py` | Fix verified, no regressions |
| `test-driven-development` | `scripts/validate.py` | Test exists, passes, lint clean |
| `refactoring` | `scripts/validate.py` | Test count stable, no regressions |
| `python-fastapi` | `scripts/validate.py` | Lint, mypy, tests, OpenAPI valid |
| `python-backend-guidelines` | `scripts/validate.py` | Layer boundaries, lint, mypy, tests |
| `database-design` | `scripts/validate_migration.py` | Migration safety, reversibility |
| `security-audit` | `scripts/validate.py` | Bandit clean (HIGH/CRITICAL), no new nosec, pip-audit clean |
| `code-review` | `scripts/validate.py` | No new type:ignore/noqa/skip, ruff clean, no regressions |
| `senior-architect` | `scripts/validate.py` | architecture_checks.py clean, mypy, no circular imports |
| `performance-optimization` | `scripts/validate.py` | No test regressions, mypy clean, p95 ≤ target (if baseline) |
| `api-design` | `scripts/validate.py` | OpenAPI schema valid, mypy API routes, ruff, no breaking changes |
| `agent-framework` | `.agent/scripts/circuit_breaker.py` | Operational limits (files, retries, time) |

### Circuit Breaker Enforcement
Before committing, agents SHOULD run:
```powershell
python .agent/scripts/circuit_breaker.py
```
If the exit code is non-zero, the agent **MUST** request user approval/limit override before proceeding.

### Incident Post-Mortem Protocol
After resolving any production bug or escaped failure:
1. Create a covering test (if not already present).
2. Run `python .agent/evals/incident_to_eval.py` to register the scenario.
3. Run `python .agent/evals/regression_runner.py --verify-only` to confirm registration.

---

## 6. Session Logging

At the end of every session:
1. Append a summary to `.agent/state/last_session_summary.md` documenting:
   - What was accomplished
   - What was left incomplete
   - Any decisions that were deferred
2. Append a row to `.agent/state/session_ledger.md` session history table.

---

---

## 7. Defensive Git Checkpoint Protocol

Before any change spanning **3 or more files**:

1. **Create checkpoint**: `git stash push -m "CHECKPOINT: [task description]"`
   - Or create a WIP commit: `git commit -m "WIP: checkpoint before [task]"`
2. **Make changes**
3. **Run validation** (validate.py, tests, lint)
4. **If validation fails**:
   - `git stash pop` (if stash was used)
   - Or `git reset --soft HEAD~1` (if WIP commit was used)
   - Report the failure to the user
5. **If validation passes**: Continue normally (squash WIP commits before PR)

### When to Skip
- Single-file edits (trivially reversible)
- Documentation-only changes
- Changes to `.agent/` configuration files

---

*Last Updated: 2026-04-17*
