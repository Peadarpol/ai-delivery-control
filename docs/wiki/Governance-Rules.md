# Governance Rules

The 15 absolute prohibitions and escalation triggers that keep AI agents accountable.

## Absolute Prohibitions (P-01–P-15)

Never do these without explicit user instruction. These are the enforcement layer of the framework.

### P-01: Never Merge to `main`/`master`

**Why:** `main` is the source of truth. Uncontrolled pushes bypass review and testing gates.

**What to do instead:** Work on a feature branch. When complete, create a pull request and let the review gate and CI run. Only merge after all gates pass.

### P-02: Never Delete Migration/Schema Files

**Why:** Migrations are the audit trail of your database. Deleting them loses reversibility and breaks deployments to older environments.

**What to do instead:** Write a new migration that reverts the changes. Alembic supports downgrade paths.

### P-03: Never Disable or Weaken Test Assertions

**Why:** Tests are your contract. Weakening them to make them pass hides bugs, not fixes them.

**What to do instead:** Fix the code to make the test pass. If the test is wrong, fix the test *before* running it again.

### P-04: Never Skip Writing Tests for New Code

**Why:** This is TDD iron law. Code without tests is broken by definition.

**What to do instead:** Write tests *first*, then implement. If a feature seems untestable, its design is wrong—fix that first.

### P-05: Never Install Dependencies Without Approval

**Why:** Dependencies have security, licensing, and maintenance implications.

**What to do instead:** List the dependency and justification for the user. Wait for explicit approval before `pip install` or `npm install`.

### P-06: Never Commit Secrets, API Keys, or Credentials

**Why:** Once in git history, secrets are compromised. Even if deleted, they're in the log forever.

**What to do instead:** Use environment variables or a secrets manager. `.gitignore` is not sufficient—use `.env.example` with placeholders.

### P-07: Never Use Unapproved Package Installers

**Why:** The project defines a single package manager (poetry, pip, npm) for reproducibility. Using others breaks lock files.

**What to do instead:** Use `poetry add` or `pip install` (as configured for your project). Do not use `pip install` if project uses poetry.

### P-08: Never Import Infrastructure from Domain Layer

**Why:** This creates bidirectional coupling and breaks clean architecture.

**What to do instead:** Domain layer is pure business logic. Infrastructure (DB, HTTP, cache) is injected as dependencies or accessed through interfaces.

### P-09: Never Access Database Sessions Directly (When Pattern is Active)

**Why:** Repository or Unit of Work pattern centralizes database access. Direct access bypasses transaction management and data isolation checks.

**What to do instead:** Use the project's Repository or Unit of Work interface. If it doesn't exist, create it first.

### P-10: Never Modify `.env` Files Without Documenting

**Why:** `.env` sets the runtime environment. Undocumented changes break local development for teammates.

**What to do instead:** Update `.env` and commit a note to the PR or decisions log explaining what changed and why.

### P-11: Never Commit or Push Without Local Verification

**Why:** CI is a safety net, not a substitute for local verification. If it fails on CI, you've already consumed review bandwidth.

**What to do instead:** Run the full verification suite locally before every commit:
```bash
poetry run pytest
poetry run mypy
poetry run ruff check
```

### P-12: Never Use `git add .` or `git add -A`

**Why:** This stages files you didn't intend to commit—lock files, generated artifacts, agent state.

**What to do instead:** Stage files by name:
```bash
git add src/mymodule.py docs/change.md
```

### P-13: Never Stage Agent-Generated or Framework Files

**Why:** These files pollute the repo and should be in `.gitignore`.

**Never stage:**
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`
- `.harness_events.jsonl`, `.ai-review-log.jsonl`
- `session_ledger.jsonl`, `active_context.md`
- `decisions_log.md`, `last_session_summary.md`
- Framework internal state files

### P-14: Never Perform Git Operations Without Verifying the Active Repository

**Why:** Accidental commits to the wrong repo (e.g., the framework repo instead of your project) corrupt history.

**What to do instead:** Before any `git add`, `commit`, or `push`:
```bash
git remote -v
git branch
```

### P-15: Never Direct-Commit to CI/CD or Deployment Branches

**Why:** CI/CD branches need controlled, reviewed changes.

**What to do instead:** Create a short-lived fix branch:
```bash
git checkout -b fix/ci-issue
# Make fix
git commit
git push origin fix/ci-issue
# Create PR, merge
git checkout main && git pull
git merge fix/ci-issue
git branch -d fix/ci-issue
```

---

## Escalation Triggers

These conditions force the agent to stop and ask rather than proceed. **No autonomous action is permitted.**

### Destructive Scope

**Stop if you are about to:**
- Delete or rename more than one file
- Drop, truncate, or irreversibly alter a database table
- Revert more than 3 commits

**Why:** These actions can corrupt state or lose data. Human oversight required.

### Access Control Changes

**Stop if you are about to:**
- Modify tenant/multi-tenant isolation logic
- Modify authentication, authorisation, or RBAC code
- Change secret/credential handling
- Modify API rate limiting or resource quotas

**Why:** Security, data isolation, and compliance violations are irreversible. These require explicit review.

### Infrastructure & Deployment

**Stop if you are about to:**
- Deploy to staging or production
- Modify CI/CD pipelines
- Modify infrastructure as code
- Change database schema in a way that affects existing data

**Why:** Deployments affect real users. Infrastructure changes risk downtime.

### Context Loss

**Stop if you are about to:**
- Proceed after being blocked at the same workflow state more than twice
- Session duration exceeds `max_session_minutes` in config
- Token budget exhausted

**Why:** Repeated blocking suggests the task needs replanning or additional info. Long sessions lose focus.

---

## The Rebuttal Protocol

If the gate returns `FAIL` and you believe it's wrong:

1. **Understand why it failed** — read the gate output carefully
2. **Consider if the gate is right** — often it is, and fixing the code is better
3. **If truly a false positive:**
   - Create `.agent/state/gate_rebuttal.json`:
     ```json
     {
       "commit_sha": "abc123...",
       "violation_id": "RULE-TENANT-ISOLATION",
       "argument": "This query is scoped to tenant because...",
       "supporting_evidence": "Reference to code or docs..."
     }
     ```
   - The gate gets a second opinion from another model
   - If accepted, the rebuttal feeds into permanent regression guards
   - **Never bypass the gate without this protocol** — `SKIP_AI_REVIEW` is for emergencies only

---

## Convention vs. Hard Enforcement

The framework uses two enforcement styles:

| Mechanism | Enforcement |
|-----------|-------------|
| Pre-commit gate | **Hard** — blocks commit |
| Architecture checks | **Hard** — blocks commit |
| Prohibitions (P-01–P-15) | **Convention** — agent follows rules |
| Escalation triggers | **Convention** — agent asks before proceeding |
| Workflow phases | **Convention** — agent follows sequence |

**Why?** Hard enforcement at every point would be unusable. The gate blocks at the commit boundary where code becomes permanent. Everything before that is convention reinforced by clear structure. **Convention degrades under pressure. The gate does not.**

---

*For full rationale and examples, see [Architecture Decisions](Architecture-Decisions.md).*