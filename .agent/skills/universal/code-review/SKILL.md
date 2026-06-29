---
name: code-review
description: Expert code review for the Gym App. Provides thorough, constructive, and actionable feedback covering correctness, architecture, security, and project-specific invariants. Use when reviewing any PR, diff, or code change.
validate: scripts/validate.py
requires-context: [docs/architecture/ARCHITECTURE.md, docs/decisions/business_rules.md]
skill_type: universal
version: 1.0.0
---

# Code Review — Gym App Edition

Thorough, constructive, and actionable code review that covers generic quality
concerns **and** the Gym App's specific architectural contracts, business rules,
and security invariants.  Read `docs/architecture/ARCHITECTURE.md` and
`docs/decisions/business_rules.md` before reviewing any non-trivial change.

## Review Feedback Format

For each issue found, provide:
- **Severity**: 🔴 Critical | 🟠 Important | 🟡 Suggestion | 💡 Nitpick
- **Location**: File and line number (or function name)
- **Issue**: Clear description of the problem
- **Rule**: The architectural rule, BR reference, or principle violated
- **Fix**: Concrete suggestion or code snippet

## Review Tone
- Constructive, not critical — explain WHY something must change
- Acknowledge good patterns when you see them
- Ask clarifying questions when intent is unclear
- Focus on the code, not the person

---

## Pass 1 — Context & Purpose

Before raising any issue:
1. What is the purpose of this change? (Feature / Bug fix / Refactor / Performance)
2. Does it solve the stated problem?
3. Are there acceptance criteria or a linked BR/ADR?

---

## Pass 2 — Architecture & Layer Violations 🔴

These are **hard fails** — merge must be blocked until resolved.

### 2.1 Dependency Direction
- **Domain** layer (`src/domain/`) must NEVER import from `application/`,
  `infrastructure/`, or `presentation/`.  Entities must be persistence-ignorant
  (no SQLAlchemy imports inside `domain/`).
- **Application** layer may import from `domain/` only.
- **Infrastructure** may import from `domain/` and `application/` (implements
  interfaces).
- **Presentation** (routers, Streamlit pages) may import from `application/`
  and `domain/` only.

### 2.2 Router Discipline
Routers must **only** route.  Flag any router that contains:
- Business logic (validation beyond schema, state computation)
- Direct database access or ORM calls
- `if/else` branching on domain concepts

All domain work must be delegated to a service via `Depends()`.

### 2.3 Unit of Work Contract
The UoW contract is inviolable:
- Services must depend on `IUnitOfWork` — never raw `Session` or individual
  repositories directly.
- **Repositories must NEVER call `commit()`** — only `add()` or `flush()`.
- Services must call `uow.commit()` explicitly, after all operations and state
  changes are complete.
- If `uow.commit()` is not reached (exception, early return), the `UnitOfWork`
  context manager implicitly rolls back — this is intentional; do not suppress.
- Events must be published **after** `uow.commit()`, never before.

### 2.4 DTO / Entity Boundary
- Service method signatures must use **Pydantic DTOs** (from `src/domain/schemas/`
  or `src/application/schemas/`), not SQLAlchemy model instances.
- Use `Protocol` types (`src/domain/interfaces/protocols.py`) when a service
  needs to accept model-like objects — this ensures `mypy` compliance and
  decoupling from the ORM layer.
- `MemberRead.model_validate(entity)` is the correct conversion pattern at the
  repository boundary.

---

## Pass 3 — Exception Handling 🔴

**Hard fail: `except Exception:` (or `except BaseException:`) without an
immediate `raise` or `raise NewException(...) from e`.**

- Catch the most specific exception possible.
- Broad catches that swallow errors mask real failures and break the governance
  circuit-breaker.
- Infrastructure failures must be re-wrapped as domain exceptions before
  propagating to the service layer — never let SQLAlchemy or httpx exceptions
  leak into business logic.
- Never use `pass` inside an `except` block on anything other than explicitly
  documented no-op cases (add a comment explaining why).

---

## Pass 4 — RBAC & Authentication 🔴

### 4.1 Endpoint Protection
Every FastAPI endpoint that is not explicitly public must declare
`require_permission(Permission.SOME_PERMISSION)` as a `Depends()`.
A missing permission dependency is a **critical security gap**.

### 4.2 SYSTEM_ADMIN Short-Circuit
The `SYSTEM_ADMIN` short-circuit (always-allowed) is a **safety invariant**.
Flag any code that:
- Adds conditional logic around `SYSTEM_ADMIN` that could negate it
- Removes or weakens the short-circuit
- Adds a `SYSTEM_ADMIN` permission to the `ROLE_PERMISSIONS` matrix (it should
  bypass the matrix entirely, not be listed in it)

### 4.3 Enum-Based Role Checks
All role comparisons must use `UserRole` or `StaffRole` enums
(`src/domain/enums/user_roles.py`), never raw strings.  String comparisons
(`role == "admin"`) bypass the `_missing_` fallback and break with legacy data.

### 4.4 Table Isolation
Staff authenticate against the `Staff` table only.
Members authenticate against the `Member` table only.
Cross-table auth checks are a **critical security violation**.

### 4.5 IDOR Prevention
Member data access must always be scoped to the `member_id` derived from the
authenticated session token — never from a URL parameter alone.

---

## Pass 5 — Multi-Tenant & Branch Isolation 🔴

### 5.1 Branch Scoping
All operational records (`Staff`, `Member` home_branch, `Transaction`,
`CheckIn`, `Equipment`) must carry a `branch_id`.  Queries that omit the
`branch_id` filter on branch-scoped tables are a data-leakage risk.

### 5.2 Global Exceptions (Documented Carve-Outs)
Two operations are explicitly **not** branch-scoped by design — flag if this
is changed:
- `check_trainer_conflict()` — must check across ALL branches (BR-SCH-28 /
  ADR-010).  A trainer cannot physically be in two locations.
- `BranchSettingsResolver` fallback chain (Branch → Business → System) is
  intentional.

### 5.3 business_id Population
The SQLAlchemy `before_insert` listener in `models.py` populates `business_id`
from `gms_context` as a last-resort safety net.  Flag any code that:
- Bypasses this listener
- Sets `business_id = None` explicitly on inserts
- Disables or patches the listener in tests without a documented reason

### 5.4 Branch-Context Middleware
The `X-Gym-Branch-ID` header must be validated by middleware on all
branch-sensitive endpoints.  Flag endpoints that bypass this header or read
`branch_id` from request body without middleware validation.

---

## Pass 6 — Business Rule Invariants 🟠

These rules are defined in `docs/decisions/business_rules.md`.
Review that any code touching these domains correctly implements them.

| Rule | What to check |
|------|--------------|
| **BR-CON-01** | Creating a contract must call `check_overlapping_contracts()`. No overlap allowed except sequential end==start renewals (BR-CON-11). |
| **BR-POS-01** | Monetary values stored as integer **cents**. `float` for money is a hard fail. |
| **BR-AUD-01** | Members, Transactions, Contracts, PT Sessions, and Check-Ins use soft-delete (`is_deleted` flag). Hard deletes on these entities are a **critical** violation. |
| **BR-LOC-02** | All timestamps stored in UTC (`datetime.timezone.utc`). Display converts to branch local timezone. |
| **BR-INV-02** | Stock levels cannot go below zero — service must raise `StockLevelError` and rollback. |
| **BR-SCH-03** | Sessions must be booked ≥2 hours in advance. |
| **BR-SCH-07/28** | Trainer conflict check must be global (not branch-filtered). |
| **BR-FIN-05** | Debt suspension sets `Member.status = 'suspended'` automatically. |
| **BR-ACC-01** | Check-in requires a valid Entitlement. `EntitlementService.validate_access()` must be called. |
| **BR-ACC-05** | Entitlement consumption priority: SESSION_PACK > RECURRING_LIMITED > soonest expiry. |
| **BR-INV-05** | Test/staging environments must not send real emails (`SEND_INVOICE_EMAILS` env var). |
| **BR-CON-09** | Every contract creation must generate a corresponding Transaction record. |

---

## Pass 7 — Financial Precision 🟠

- Monetary values are **always integer cents** — `$19.99` stored as `1999`.
  Any use of `float` or `Decimal` for storage is a violation of BR-POS-01.
- GST calculation: `gst_amount = total_price_cents / 11` (integer division,
  round to nearest cent).  Never `total * 0.1`.
- Discount cannot produce a negative total (BR-POS-08).

---

## Pass 8 — Pydantic / Schema Hardening 🟠

- All schemas must declare `model_config = ConfigDict(extra="forbid")` (or
  inherit from `HardenedBaseModel`).  `extra="allow"` or `extra="ignore"` on
  request-facing schemas is a CWE-915 mass-assignment vulnerability.
- Validators must use `@field_validator` (Pydantic v2 style), not
  `@validator`.
- Enum fields must use the actual enum type, not raw `str` — prevents bypass
  of `_missing_` fallback logic.

---

## Pass 9 — Correctness & Logic

9.1) Does the code do what it claims?
9.0) **Architectural technical debt check (AI hallucination risk)**: AI-generated
   code is frequently *locally correct* but *globally inconsistent* — the
   implementation solves the immediate task but violates the established
   architecture of the surrounding system. Before reviewing correctness,
   confirm:
   - Does the new code follow the same patterns as adjacent code in the same
     layer? (e.g. if all other services use `self.uow.members.get_by_id()`,
     a new service calling the repository directly is a red flag)
   - Does it use the project's established abstractions (UoW, HardenedBaseModel,
     require_permission, BranchAwareRepository) or bypass them with local
     alternatives?
   - Does it introduce a new pattern that duplicates existing infrastructure
     (e.g. a custom auth check that reimplements what `require_permission()` does)?
   - Is the naming consistent with the codebase conventions (snake_case
     services, `*Create`/`*Update` schemas, `*Repository` persistence classes)?
   AI models optimise for local plausibility — they produce code that looks
   reasonable in isolation but contradicts decisions made elsewhere in the
   project. This check must be done with the full architectural context in mind,
   not just the diff.
9.2) Are edge cases handled?
   - Empty inputs, None values, zero quantities
   - Boundary dates (today, past, future)
   - Empty collections (list, queryset)
9.2a) **API hallucination check (AI hallucination risk)**: AI models generate
   calls to methods, functions, library APIs, and class attributes that do not
   exist — bearing plausible names but lacking any real implementation. This is
   the most common and hardest-to-spot AI failure mode because the code is
   syntactically valid and reads naturally. For every method call that was
   introduced or modified in this diff, verify:
   - The method actually exists on the object being called (check the class
     definition or imported module — do not rely on the name looking right)
   - Library functions exist in the version specified in `pyproject.toml`
     (AI models frequently call methods from future or past library versions)
   - Internal service/repository methods being called from a new call site
     exist with the exact signature used (parameter names, types, return type)
   - SQLAlchemy relationship attributes referenced in queries are declared on
     the model (AI frequently generates `.relationship_name` accesses on models
     that don't define that relationship)
   This check cannot be done by reading the diff alone — it requires verifying
   against the actual class/module source.
9.3) Are domain state transitions correct?  Check against BR-MEM-04,
   BR-CON-04, BR-SCH-11, BR-SCH-21.
9.4) Is concurrency handled correctly?
   - Entitlement credit deduction uses `SELECT FOR UPDATE` (BR-ACC-05)
   - Booking capacity check uses "first-to-commit-wins" pattern
   - No race condition between read and write in the same service method
   - **Latent race condition check (AI hallucination risk)**: AI-generated code
     frequently appears correct under synchronous execution but introduces
     non-deterministic bugs in concurrent contexts. Flag any sequence where a
     value is read, a decision is made based on it, and a write occurs without
     a lock between read and write (classic check-then-act without atomicity).
     Pay particular attention to: capacity checks before bookings, balance checks
     before debits, status checks before state transitions, and entitlement
     balance reads before consumption. These are the patterns where AI models
     generate plausible-looking but unsafe read-modify-write sequences.

---

## Pass 10 — Security

10.1) Input validation: all user-supplied data validated by Pydantic before
   reaching the service layer.
10.2) SQL injection: SQLAlchemy ORM or parameterized queries only — never
   f-string SQL.
10.2a) **Implicit security vulnerability check (AI hallucination risk)**: AI
   models embed known-vulnerable patterns without flagging them. Specifically
   check for:
   - Unparameterised query fragments (f-string or `.format()` used in any DB
     call, even partial)
   - Auth token handling: tokens passed in URL query parameters (logged by
     proxies), stored in `localStorage`, or logged in plaintext in any
     debug/info log statement
   - Unsafe deserialisation: `pickle.loads()`, `yaml.load()` without
     `Loader=yaml.SafeLoader`, `eval()` on any user-supplied or
     externally-sourced string
   - JWT `alg: none` acceptance or missing signature verification
   - These patterns are insidious in AI output because the surrounding code
     is correct — the vulnerability is localised to a single call.
10.3) Rate limiting declared on auth and financial endpoints (BR-AUD-03,
   BR-SEC-08).
10.4) No secrets, API keys, or credentials in code, logs, or error messages.
10.5) JWT `business_id` is re-verified from the live DB record on sensitive
   operations — not trusted from the token alone (tampering guard).
10.6) Password hashing uses `bcrypt` with salt (BR-SEC-02).  Plaintext
   password comparisons are a hard fail.

---

## Pass 11 — Performance

11.1) N+1 queries: any loop that calls a repository method per iteration
   without eager loading.
11.2) Missing indexes on columns used in `WHERE` or `JOIN` (flag new tables
   with no index declarations).
11.3) Synchronous blocking calls inside `async def` endpoints — use
   synchronous `def` for SQLAlchemy I/O (FastAPI offloads to thread pool).
   Only use `async def` for truly async libraries (httpx, aiofiles).
11.4) No unbounded queries — all list endpoints must paginate.
11.5) API response time target: p95 < 200ms; DB query target: p95 < 50ms
   (NFR-PERF-01).

---

## Pass 12 — Testing

12.1) New public functions and services have at least one test.
12.2) Tests use `FakeUnitOfWork` for service-layer unit tests, not deep
   mocking of individual repositories.
12.3) Tests verify `uow.committed is True` after successful operations.
12.4) Integration tests use a real (test) database with branch isolation
   (`branch_id` scoped to the test fixture).
12.5) No broad `except` blocks in test code that could swallow assertion
   errors.
12.6) Test names follow `test_<action>_<condition>_<expected_outcome>`.

---

## Pass 13 — Documentation & Hygiene

13.1) Public service methods have docstrings describing inputs, outputs, and
   exceptions raised.
13.2) New business rules are reflected in `docs/decisions/business_rules.md`.
13.3) New ADRs created for non-trivial architectural decisions.
13.4) No commented-out production code.
13.5) No `# TODO` without a linked issue number.
13.6) `CHANGELOG.md` updated for user-facing changes.

---

## Quick Invariant Checklist

Before approving any PR, confirm:

- [ ] No domain layer importing from outer layers
- [ ] No business logic in routers
- [ ] No `except Exception:` without `raise`
- [ ] All new endpoints have `require_permission()` dependency
- [ ] `SYSTEM_ADMIN` short-circuit is untouched
- [ ] Role checks use `UserRole`/`StaffRole` enums, not strings
- [ ] All queries on branch-scoped tables filter by `branch_id`
- [ ] Trainer conflict check is global (if touched)
- [ ] No monetary `float` — integer cents only
- [ ] Schemas use `extra="forbid"` or `HardenedBaseModel`
- [ ] Soft-delete used for Members/Transactions/Contracts/Sessions/CheckIns
- [ ] Timestamps stored in UTC
- [ ] Repositories do not call `commit()`
- [ ] Events published after `uow.commit()`
- [ ] New functionality has tests
- [ ] `uow.committed` asserted in service unit tests
- [ ] All new method calls verified to exist on the target class/module (API hallucination check)
- [ ] Read-modify-write sequences on shared state are atomic or lock-protected (latent race condition check)
- [ ] No f-string SQL, plaintext token logging, unsafe deserialisation, or unverified JWT alg (implicit security vulnerability check)
- [ ] New code follows established project patterns, not locally-invented alternatives (architectural coherence check)
