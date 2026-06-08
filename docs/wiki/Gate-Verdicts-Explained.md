# Gate Verdicts Explained

Understanding what the pre-commit review gate verdict means and what to do about it.

---

## Verdict Types

### ✅ PASS

**Meaning:** Code meets all review requirements. Commit proceeds.

**What happened:**
1. Gate read the diff
2. Ran architecture boundary checks (AST-based)
3. Invoked LLM reviewer against universal + project rules
4. No violations found

**Your action:** Nothing. Commit is done.

**Example:**
```
✅ PASS — Code successfully documents endpoints and updates import style.
No issues found.
```

---

### ⚡ PASS_FAST

**Meaning:** Trivial diff (docs, whitespace, config only). Commit proceeds **without** LLM call.

**What happened:**
1. Gate detected no code changes, only:
   - Documentation (.md, .txt)
   - Whitespace/formatting
   - Configuration files
2. Skipped LLM call to save API cost

**Your action:** Nothing. Commit is done.

**When it triggers:**
```bash
git add docs/README.md              # ✅ PASS_FAST
git add -A  # only whitespace      # ✅ PASS_FAST
git add .env.example               # ✅ PASS_FAST
```

---

### ⚠️ WARN

**Meaning:** Issues detected but code can ship. Developer should address, but commit proceeds.

**What happened:**
1. LLM found violations of project rules
2. Classified as `WARN` (not blocking)
3. Commit is allowed to proceed

**Your action:** Review the warning. Address in a follow-up commit, or document why you're ignoring it.

**Example:**
```
⚠️  WARN — [STYLE] Missing docstring on public method
   File: src/services/user.py:42
   
   Public methods should have docstrings describing:
   - Purpose
   - Arguments
   - Return value
```

**Common WARN triggers:**
- Incomplete test coverage
- Missing docstrings
- Style issues
- Incomplete comments

---

### ❌ FAIL

**Meaning:** Code violates critical rules. **Commit is blocked.**

**What happened:**
1. LLM found violations of universal or project rules
2. Classified as `FAIL` (blocking)
3. Commit cannot proceed

**Your action:** Fix the underlying issue or use the rebuttal protocol.

**Example:**
```
❌ FAIL — [BRANCH_ISOLATION] Data leak detected
   File: src/infrastructure/repositories/booking.py:42-45
   
   The raw SQL query selects bookings without applying the mandatory
   branch-scoped filter. This is a CRITICAL security vulnerability
   that permits cross-tenant data leaks.
   
   🔴 [HIGH] BRANCH_ISOLATION violation
   
   Fix: Modify query to include the branch isolation helper:
        stmt = select(Booking).where(Booking.id == id)
        stmt = self._apply_branch_filter(stmt)  # ← Add this
        res = await self.session.execute(stmt)
```

**To fix:**
1. Read the gate output carefully—it explains the violation
2. Fix the code
3. Commit again

**Common FAIL triggers:**
- Security vulnerabilities (unscoped queries, exposed secrets)
- Data integrity violations (missing tenant filters)
- Architecture violations (importing from wrong layer)
- Test coverage gaps

---

### 🔄 FAIL_OPEN

**Meaning:** LLM provider is unavailable. Low-risk commits proceed; high-risk commits fail closed.

**What happened:**
1. Tried to reach LLM provider (Anthropic, OpenAI, Ollama)
2. Provider did not respond
3. Fallback logic activated:
   - **Low-risk diff** (docs, config) → allow commit
   - **High-risk diff** (migrations, auth, RBAC) → block, require `SKIP_AI_REVIEW=1`

**Your action:**
- If low-risk: commit proceeds automatically
- If high-risk: wait for provider to return, or explicitly skip with `SKIP_AI_REVIEW=1`

**Example (low-risk):**
```
🔄 FAIL_OPEN (provider unavailable, low-risk diff)
   Docs changed: docs/api.md
   → Commit allowed to proceed
```

**Example (high-risk):**
```
🔄 FAIL_OPEN (provider unavailable, high-risk diff)
   Files changed: src/auth/session.py, src/db/migrations/
   → Commit blocked. To proceed:
      SKIP_AI_REVIEW=1 SKIP_REASON="provider unavailable" git commit
```

---

## Reading Gate Output

### Structure

```
⚙️  AI REVIEW DYNAMIC ROUTING DECISION
   Intensity: ELEVATED
   Rationale: Staged changes modify high-priority files: user.py
   Active capabilities: RBAC, CLEAN_ARCH
   
   Policy Notes:
     ⚡ Enabled check: RBAC
     ⚡ Enabled check: CLEAN_ARCH
     🛡️  Skipped check: BRANCH_ISOLATION (no repo files changed)
   
   Review intensity: ELEVATED (PageRank metrics: hits = 1)
─────────────────────────────────────────

🔍 Running AI review (anthropic/claude-sonnet, 1 pass)...

────────────────────────────────────────────────
  AI ADVERSARIAL REVIEW ✅ PASS
────────────────────────────────────────────────

Intent: Code successfully updates controller imports.

No issues found.
```

### Key Components

**Routing Decision:**
- **Intensity** — How rigorously to review (LOW, NORMAL, ELEVATED, CRITICAL)
- **Active capabilities** — Which review dimensions are active
- **Skipped checks** — Why certain checks didn't run

**Intensity Levels:**
- **LOW** — Only docs/config changed → minimal review
- **NORMAL** — Standard changes → full review
- **ELEVATED** — High-centrality files changed → extra scrutiny
- **CRITICAL** — Core files (auth, migrations) → maximum scrutiny

**Review Context:**
- **Review model** — LLM used (e.g., `claude-sonnet-4-20250514`)
- **Pass count** — How many review passes were run (usually 1)

---

## Contesting a FAIL Verdict

If you believe the gate issued an incorrect `FAIL`, use the **structured rebuttal protocol**:

### Step 1: Understand Why It Failed

Read the gate output carefully. The LLM explains:
- Which rule was violated
- Why it's a violation
- Suggested fix

### Step 2: Decide if It's Actually Wrong

Before rebutting, ask:
- Is the rule correct?
- Is my code actually violating it?
- Is there a legitimate reason for the violation?

**Often the gate is right.** If unsure, ask a teammate or fix the code.

### Step 3: Create a Rebuttal

If you believe it's a false positive, create `.agent/state/gate_rebuttal.json`:

```json
{
  "commit_sha": "abc123def456...",
  "violation_id": "BRANCH_ISOLATION",
  "rule_id": "RULE:TENANT-ISOLATION",
  "argument": "This query is actually scoped to tenant because the _apply_branch_filter is called implicitly in the parent method during execution flow.",
  "supporting_evidence": "See src/infrastructure/repositories/base.py:73-81 where _apply_branch_filter is called for all queries through __getattribute__ interception.",
  "context": "Edge case: dynamic method wrapping makes static analysis difficult."
}
```

**Required fields:**
- `commit_sha` — Full commit SHA that failed
- `violation_id` — Rule that was triggered
- `argument` — Why you think it's wrong
- `supporting_evidence` — Code reference or documentation

### Step 4: Second Opinion

The gate:
1. Reads your rebuttal
2. Gets a second opinion from another LLM model
3. Decides: accept or reject

Output:
```
🔄 REBUTTAL MODE
   Violation ID: BRANCH_ISOLATION
   Your argument: [...]
   
   Second opinion: ACCEPTED (false positive)
   Reason: Dynamic wrapping via __getattribute__ does apply filters.
   
   Action: Rebuttal accepted. Commit allowed.
   Future improvement: Update rule to account for dynamic wrapping patterns.
```

### Step 5: Accepted Rebuttal Feeds Back

If accepted:
- The rebuttal is logged to `.ai-review-log.jsonl`
- Dream phase detects this pattern
- Next week, dream phase proposes updating the rule
- Prevents false positives in the future

---

## Emergency Bypass (Last Resort)

**Never do this first.** Use rebuttal protocol instead.

Only in true emergencies:

```bash
SKIP_AI_REVIEW=1 SKIP_REASON="critical-production-hotfix" git commit
```

**Consequences:**
- Bypass is logged to `harness_events.jsonl` for audit
- No second opinion is obtained
- Dream phase flags this as a risk
- You're responsible if the code was actually wrong

**When it's acceptable:**
- Production is down
- Revert must land immediately
- No time for full review cycle
- Human approves the bypass

---

## Common Scenarios

### Scenario: Query Missing Tenant Filter

**Gate Output:**
```
❌ FAIL — [BRANCH_ISOLATION]
   src/infrastructure/repositories/booking.py:42
   
   Query missing branch isolation filter.
   All queries on multi-tenant tables must include _apply_branch_filter().
```

**You should:**
1. Look at the code
2. Add the filter
3. Commit again

**You should NOT:**
1. Bypass the gate
2. Argue it's a false positive

---

### Scenario: Legitimate Edge Case

**Gate Output:**
```
❌ FAIL — [AUTHENTICATION]
   src/routes/public.md:8
   
   Public endpoint missing authentication.
```

**You should:**
1. Verify this endpoint is intentionally public (no auth required)
2. Create a rebuttal with supporting evidence
3. Include documentation reference

**Rebuttal:**
```json
{
  "commit_sha": "...",
  "violation_id": "AUTHENTICATION",
  "argument": "This is the /health endpoint. Public health checks are intentional and required by load balancers.",
  "supporting_evidence": "docs/api-design.md §2.3: Health endpoints are explicitly exempted from auth."
}
```

---

## See Also

- **[Governance Rules](Governance-Rules.md)** — Full list of violations
- **[Customization](Customization.md)** — How to add project-specific review rules
- **[Quick Reference](Quick-Reference.md)** — Gate verdict table

---

*For worked examples with real gate output, see `docs/worked-example.md`.*