---
name: verification-before-completion
description: Use before claiming any work is complete, fixed, passing, or ready to commit. Requires running actual verification commands and reading their output before making any success claim. Applies to all task types — feature implementation, bug fixes, refactoring, migrations, and CI gate work.
skill_type: universal
version: 1.0.0
---

# Verification Before Completion

Claiming work is complete without verification is not efficiency — it is
dishonesty.  **Evidence before assertions, always.**

**Core principle:** If you haven't run the verification command in this
message, you cannot claim it passes.

Violating the letter of this rule is violating the spirit of this rule.

---

## The Iron Law

```
NO COMPLETION CLAIM WITHOUT FRESH VERIFICATION EVIDENCE
```

Fresh means: run in **this message**, not recalled from a previous run, not
inferred from partial output, not assumed from "it looked right".

---

## The Gate Function

Before stating any of the following — *complete*, *fixed*, *passing*,
*resolved*, *done*, *ready to commit*, *all tests pass*, *no errors* — execute
this gate:

1. **IDENTIFY** — what command proves this claim?
2. **RUN** — execute the full command, unabridged
3. **READ** — read the complete output, check exit code, count failures
4. **VERIFY** — does output confirm the claim?
   - If **NO**: state the actual status with evidence; do not claim success
   - If **YES**: state the claim and quote the key confirming output

Never summarise from memory.  Never skip because "it passed last time".

---

## Verification Commands

Run the appropriate command(s) for the work being completed. The examples below use common Python tooling (pytest, ruff, mypy, alembic) — substitute your project's actual toolchain (npm test, go test, cargo test, etc.) where it differs.

### After any source code change

Example (Python/Poetry — adapt to your project's toolchain):
```powershell
# Lint — must be clean
poetry run ruff check src/

# Type check — must be clean
poetry run mypy src/

# Full test suite — all must pass
poetry run pytest tests/ --tb=short -q
```

### After any service or repository change

Example (Python/Poetry — adapt to your project's toolchain):
```powershell
# Unit + integration focused on changed area
poetry run pytest tests/unit/ tests/integration/ --tb=short -q

# Confirm any project-specific state-commit assertions are present in new tests
# (e.g. transaction committed, event published — check your project's testing
# conventions for the equivalent pattern)
```

### After any RBAC / auth change

Example (Python/Poetry — adapt to your project's toolchain):
```powershell
# Security-specific test suite
poetry run pytest tests/security/ -v --tb=short

# Static security scan — no HIGH findings allowed
poetry run bandit -r src/ -ll -q
```

### After any Alembic migration
```powershell
# Verify single head
poetry run alembic heads

# Verify upgrade runs cleanly
poetry run alembic upgrade head

# Verify downgrade is reversible
poetry run alembic downgrade -1
poetry run alembic upgrade head
```

### Before any commit (full harness gate)
```powershell
# Circuit breaker — must exit 0
python .agent/scripts/circuit_breaker.py

# Behaviour audit — must report no violations
python .agent/evals/behaviour_checks.py

# Pre-commit hooks (includes AI adversarial review)
git add -A && git status   # confirm staged files
# Then commit — hooks fire automatically
```

### After schema / Pydantic model change
```powershell
# Confirm extra="forbid" enforcement — run mass-assignment test
poetry run pytest tests/ -k "hardened or mass_assign or extra_forbid" --tb=short
```

### After a bug fix
```powershell
# Run the specific regression test that covers the fixed bug
poetry run pytest tests/path/to/test_specific_bug.py -v --tb=short

# Confirm it PASSED (was failing before the fix)
# Quote the PASSED line from output
```

---

## What Counts as Evidence

✅ **Acceptable** — paste the terminal output showing:
- Exit code 0, or
- `N passed` / `passed` with zero failures, or
- `Success` / `No issues found`

❌ **Not acceptable:**
- "I ran the tests and they passed" with no output
- Output from a previous message ("as we saw earlier...")
- Partial output ("here's the relevant part...")
- Inference ("since I only changed X, the tests should still pass")
- Recalling from memory without re-running

---

## Common Failure Modes

| Claim | What to actually run |
|-------|---------------------|
| "Tests pass" | `pytest tests/ --tb=short -q` → paste N passed line |
| "No lint errors" | `ruff check src/` → paste clean output or "All checks passed" |
| "Types are clean" | `mypy src/` → paste "Success: no issues found in N source files" |
| "Migration is safe" | `alembic heads` + `upgrade head` + `downgrade -1` + `upgrade head` |
| "No security issues" | `bandit -r src/ -ll -q` → paste issue count (must be 0 HIGH) |
| "Circuit breaker clean" | `python .agent/scripts/circuit_breaker.py` → paste exit 0 |
| "PR is ready" | All of the above, in sequence |

---

## Rationalisations to Reject

| Excuse | Why it fails |
|--------|-------------|
| "I only changed a comment" | Ruff can still flag it; run takes 2 seconds |
| "Tests passed 5 minutes ago" | Code may have changed; stale evidence is no evidence |
| "It's obviously correct" | Confidence is not verification |
| "The CI will catch it" | CI catches it after the commit; catch it before |
| "I'll verify in the next step" | Complete the gate before making the claim |
| "All the relevant tests pass" | "Relevant" is your judgment call; run the full suite |
| "This test is flaky, so I'll just skip or xfail it to unblock the build" | Flaky tests indicate latent concurrency or environmental bugs. Address the underlying cause rather than masking it. |
| "I loosened the assertion so it's not brittle" | Weakening assertions reduces test coverage and allows regressions to pass. Fix the mock or stabilize the state instead. |

---

## Scope

This skill applies to ALL completion claims:

- "Feature X is implemented" → run full suite + lint + mypy
- "Bug Y is fixed" → run the regression test, quote the PASSED line
- "Refactoring complete" → run full suite, confirm test count stable
- "Migration ready" → run alembic sequence above
- "PR is ready for review" → run full harness gate

No task type is exempt.
