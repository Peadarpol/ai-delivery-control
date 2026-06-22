# Walked Execution Worked Example

This document illustrates a complete, end-to-end trace of the pre-commit review gate executing in two distinct scenarios: **Selective Routing (PASS)** and an **Adversarial Policy Violation (FAIL)**.

---

## Scenario 1: Selective Routing Decision (PASS)

In this scenario, a developer makes a documentation update and tweaks a presentation API controller. Since no database repositories or transactional service layers are modified, the orchestrator dynamically skips high-latency checks.

### 1. Developer Commits Changes
```bash
git add docs/api-spec.md src/presentation/controllers/user.py
git commit -m "docs: document user endpoint & clean up controller imports"
```

### 2. Pre-Commit Review Gate Output
```
⚙️  AI REVIEW DYNAMIC ROUTING DECISION
   Intensity: ELEVATED
   Rationale: Staged changes modify high-priority Top 10 PageRank files: user.py. Active capabilities: RBAC, CLEAN_ARCH.
   Policy Notes:
     ⚡ Enabled check: RBAC
     ⚡ Enabled check: CLEAN_ARCH
     🛡️  Skipped check: BRANCH_ISOLATION (no repository files changed or active ADR domain)
     🛡️  Skipped check: TRANSACTIONAL_INTEGRITY (no service or transaction files modified)
     🛡️  Skipped check: MIGRATIONS (no alembic migration files modified)
     🛡️  Skipped check: MASS_ASSIGNMENT (no schema files modified)
     🔍 Review intensity: ELEVATED (PageRank metrics: critical hits = 0, elevated hits = 1)
─ ──────────────────────────────────────────────────────────

🔍 Running AI review (anthropic/claude-sonnet-4-20250514, 1 pass)...

────────────────────────────────────────────────────────────
  AI ADVERSARIAL REVIEW  ✅ PASS
────────────────────────────────────────────────────────────

  Intent: Code successfully documents endpoints and updates import style.

  No issues found.

────────────────────────────────────────────────────────────
  ✅ AI review passed.
```

---

## Scenario 2: Adversarial Policy Violation (FAIL)

In this scenario, a developer introduces an optimized query inside a repository class, but accidentally bypasses multi-tenant branch isolation (Tier 3 rule PC-MT-02 — a query that could return rows across tenant boundaries; multi-tenant isolation is also a C-02 high-risk zone). The gate executes at full intensity, analyzes the AST roster, detects the violation, and blocks the commit with precise line citations and remediation advice.

### 1. Developer Commits Non-Compliant Code
```bash
git add src/infrastructure/database/repositories/booking.py
git commit -m "perf: optimize booking lookup query by bypassing ORM filter"
```

### 2. Pre-Commit Review Gate Output
```
⚙️  AI REVIEW DYNAMIC ROUTING DECISION
   Intensity: CRITICAL
   Rationale: Staged changes modify core Top 3 PageRank files: booking.py. Active capabilities: BRANCH_ISOLATION, CLEAN_ARCH.
   Policy Notes:
     ⚡ Enabled check: BRANCH_ISOLATION
     ⚡ Enabled check: CLEAN_ARCH
     🛡️  Skipped check: TRANSACTIONAL_INTEGRITY (no service or transaction files modified)
     🛡️  Skipped check: MIGRATIONS (no alembic migration files modified)
     🛡️  Skipped check: MASS_ASSIGNMENT (no schema files modified)
     🔍 Review intensity: CRITICAL (PageRank metrics: critical hits = 1, elevated hits = 0)
─ ──────────────────────────────────────────────────────────

🔍 Running AI review (anthropic/claude-sonnet-4-20250514, 1 pass)...

────────────────────────────────────────────────────────────
  AI ADVERSARIAL REVIEW  ❌ FAIL
  Blocking concern: BRANCH_ISOLATION
────────────────────────────────────────────────────────────

  Intent: Developer attempts to optimize booking query latency.

  🔴 [HIGH] <BRANCH_ISOLATION> src/infrastructure/database/repositories/booking.py:42-45
     The raw SQL query selects bookings without applying the mandatory branch-scoped filter.
     The code utilizes `select(Booking).where(Booking.id == id)` but skips calling `_apply_branch_filter(stmt)`.
     This is a critical security vulnerability that permits cross-tenant data leaks.
     💡 Fix: Modify query to include the branch isolation helper:
           stmt = select(Booking).where(Booking.id == id)
           stmt = self._apply_branch_filter(stmt)
           res = await self.session.execute(stmt)

────────────────────────────────────────────────────────────
  Summary: Perform query optimization safely. The optimization breaks multi-tenant branch isolation rules.

❌ Commit BLOCKED by AI review. Fix HIGH severity issues or run:
   SKIP_AI_REVIEW=1 SKIP_REASON='{"rebuttal_type":"FALSE_POSITIVE","finding_ids":["T1-G-07"],"evidence":"..."}' git commit ...  to bypass
   -- or create a .skip-ai-review file in the project root
```
