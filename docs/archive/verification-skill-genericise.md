# Genericise verification-before-completion/SKILL.md
**Repository**: `C:\projects\ai-delivery-control`
**Branch**: continue on the existing v1.4.6 cleanup branch (or cut a fresh
`fix/verification-skill-genericise` from main if the prior branch has already merged —
check `git log --oneline -5` and `git branch` first to confirm current state)
**File to modify**: `.agent/skills/universal/verification-before-completion/SKILL.md` only
**Single commit. Do not push. Do not raise a PR. Stop after the commit and report the SHA.**

---

## Context

This skill is marked `skill_type: universal` but carries GymBase-specific content:
the title "Verification Before Completion — Gym App Edition", a "Gym App Verification
Commands" section hardcoding Poetry/Alembic/Bandit-specific commands, a `BR-DEV-02`
business rule reference, and GymBase-specific test path assumptions (`tests/security/`,
`tests/unit/`, `tests/integration/`). A fresh installation of the harness onto a
non-GymBase project would inherit this content verbatim, despite none of it being
generalisable.

The core discipline in this skill (the Iron Law, the Gate Function, What Counts as
Evidence, Common Failure Modes, Rationalisations to Reject, Scope) is genuinely
universal and must be preserved exactly — only the GymBase-specific command examples
and branding need to change.

---

## The changes

### Change 1 — Title

Find:
```
# Verification Before Completion — Gym App Edition
```

Replace with:
```
# Verification Before Completion
```

### Change 2 — Section heading

Find:
```
## Gym App Verification Commands

Run the appropriate command(s) for the work being completed.
```

Replace with:
```
## Verification Commands

Run the appropriate command(s) for the work being completed. The examples below
use common Python tooling (pytest, ruff, mypy, alembic) — substitute your project's
actual toolchain (npm test, go test, cargo test, etc.) where it differs.
```

### Change 3 — Generalise the command examples

The six subsections under "Verification Commands" (now generic heading) currently
hardcode GymBase-specific paths and tools. Rewrite each to be illustrative of the
**pattern** rather than prescriptive of GymBase's exact toolchain. Apply this approach
to each subsection:

**"After any source code change"** — keep as a Python/Poetry example but make clear
it's illustrative:

```markdown
### After any source code change

Example (Python/Poetry — adapt to your project's toolchain):
\`\`\`powershell
# Lint — must be clean
poetry run ruff check src/

# Type check — must be clean
poetry run mypy src/

# Full test suite — all must pass
poetry run pytest tests/ --tb=short -q
\`\`\`
```

**"After any service or repository change"** — generalise the comment to remove the
GymBase-specific "UoW committed assertion" instruction, replacing with a generic
state-verification note:

```markdown
### After any service or repository change
\`\`\`powershell
# Unit + integration focused on changed area
poetry run pytest tests/unit/ tests/integration/ --tb=short -q

# Confirm any project-specific state-commit assertions are present in new tests
# (e.g. transaction committed, event published — check your project's testing
# conventions for the equivalent pattern)
\`\`\`
```

**"After any RBAC / auth change"** — remove the `BR-AUD-02` style reference, keep
the pattern generic:

```markdown
### After any RBAC / auth change
\`\`\`powershell
# Security-specific test suite
poetry run pytest tests/security/ -v --tb=short

# Static security scan — no HIGH findings allowed
poetry run bandit -r src/ -ll -q
\`\`\`
```

**"After any Alembic migration"** — keep as-is, Alembic is a generic tool name not
GymBase-specific (no change needed here, but verify no GymBase-specific table/column
names have crept in — there should not be any based on current content).

**"Before any commit (full harness gate)"** — keep as-is, this section already
references harness-generic scripts (`circuit_breaker.py`, `behaviour_checks.py`) not
GymBase-specific ones (no change needed).

**"After schema / Pydantic model change"** — keep the Pydantic-specific content since
Pydantic is a generic Python validation library, not GymBase-specific (no change
needed).

**"After a bug fix"** — already generic (no change needed).

### Change 4 — Remove BR-DEV-02 reference

Find any reference to `BR-DEV-02` (business rule numbering is GymBase-specific
project documentation, not a universal concept). Locate the exact line — it should
be in or near the RBAC/auth verification subsection — and remove the specific rule
ID reference, replacing with a generic phrase like "per your project's security
requirements" if the surrounding sentence structure needs it preserved.

### Change 5 — Verify "Common Failure Modes" table

Read the "Common Failure Modes" table. Confirm none of its rows reference
GymBase-specific paths or tools beyond the generic pytest/ruff/mypy/bandit/alembic
examples already addressed above. If the table is already generic (it appears to be,
based on current content), leave it unmodified.

---

## What must NOT change

Do not modify:
- The Iron Law section
- The Gate Function (4-step IDENTIFY/RUN/READ/VERIFY process)
- "What Counts as Evidence" section
- "Rationalisations to Reject" table
- "Scope" section
- The frontmatter (`name`, `description`, `skill_type: universal`, `version: 1.0.0`)

These are all genuinely universal and already well-written — the task is narrowly
scoped to removing GymBase-specific branding and command specifics, not rewriting
the skill's substance.

---

## Verification

After editing, read the file back in full and confirm:
1. No occurrence of "Gym App" anywhere in the file
2. No occurrence of "BR-DEV-02" or any other `BR-*` business rule reference
3. The Iron Law, Gate Function, Evidence, Rationalisations, and Scope sections are
   byte-for-byte unchanged from the original
4. The file still reads coherently as a complete skill document

```powershell
Select-String -Path ".agent\skills\universal\verification-before-completion\SKILL.md" -Pattern "Gym App|BR-DEV"
```

Expected: no output (zero matches).

---

## Commit

```
git add .agent/skills/universal/verification-before-completion/SKILL.md
git commit --no-verify -m "fix(skills): genericise verification-before-completion SKILL.md

Removed 'Gym App Edition' title branding, renamed 'Gym App Verification
Commands' section to 'Verification Commands', and generalised the six
command-example subsections to be illustrative of the pattern (with a note
to adapt to the project's actual toolchain) rather than prescriptive of
GymBase's exact stack. Removed BR-DEV-02 business rule reference.

Core discipline preserved unchanged: the Iron Law, the four-step Gate
Function, What Counts as Evidence, Rationalisations to Reject, and Scope
sections are byte-for-byte identical to the original — these are genuinely
universal and were already correctly written.

Continues the universal-vs-project content leak cleanup started in the
prior commit (security-audit/SKILL.md). code-review/SKILL.md requires a
larger structural split (universal passes vs GymBase business-rule passes)
and is tracked as separate follow-up work, not addressed here.

Part of post-v1.4.5 cleanup before v1.5.0 begins (not itself a backlog item)."
```

Report the commit SHA and the Select-String verification output (expect empty).
