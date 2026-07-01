---
name: code-review
description: Expert code review providing thorough, constructive, and actionable feedback covering correctness, architecture, security, and project-specific invariants.
validate: scripts/validate.py
skill_type: universal
version: 1.0.0
---

# Code Review

Thorough, constructive, and actionable code review that covers generic quality concerns, exception safety, correctness, and security invariants.

## Review Feedback Format

For each issue found, provide:
- **Severity**: 🔴 Critical | 🟠 Important | 🟡 Suggestion | 💡 Nitpick
- **Location**: File and line number (or function name)
- **Issue**: Clear description of the problem
- **Rule**: The architectural rule or principle violated
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
3. Are there acceptance criteria or a linked spec?

---

## Pass 2 — Architecture & Layer Violations 🔴

These are **hard fails** — merge must be blocked until resolved.
- **Dependency Direction**: Internal/domain layers must NEVER import from outer/infrastructure/presentation layers. Entities must be persistence-ignorant (no database ORM imports inside domain layers).
- **Router/API Layer Discipline**: Routers/handlers must only route. Flag any route handler that contains business logic (validation beyond schema, state computation) or direct database access.
- **Unit of Work Contract**: Services must depend on a Unit of Work or transaction manager interface—never raw database connections or sessions directly. Repositories must never commit transactions.
- **DTO / Boundary**: Service boundaries must use Data Transfer Objects (DTOs) or schemas, not raw database entity model instances.

---

## Pass 3 — Exception Handling 🔴

**Hard fail: Catching generic exceptions without an immediate raise or wrapping in a new exception.**
- Catch the most specific exception possible. Swallowing errors masks real failures.
- Infrastructure failures must be re-wrapped as domain exceptions before propagating.
- Never use `pass` inside an `except`/catch block without explicit documentation.

---

## Pass 4 — Correctness & Logic 🟠

- **Architectural technical debt check (AI hallucination risk)**: AI-generated code is frequently *locally correct* but *globally inconsistent*. Confirm:
  - Does the new code follow the same patterns as adjacent code in the same layer?
  - Does it introduce a new pattern that duplicates existing infrastructure?
  - Is the naming consistent with the codebase conventions?
- **API hallucination check (AI hallucination risk)**: AI models generate calls to methods, functions, and class attributes that do not exist. Verify:
  - The method/function actually exists on the object/module being called.
  - Internal methods being called exist with the exact signature used.
- **Latent race condition check (AI hallucination risk)**: AI-generated code frequently introduces non-deterministic bugs in concurrent contexts. Flag any sequence where a value is read, a decision is made based on it, and a write occurs without an atomic lock or transaction boundary between read and write (check-then-act).

---

## Pass 5 — Security 🔴

- **Implicit security vulnerability check (AI hallucination risk)**: AI models embed known-vulnerable patterns. Check for:
  - Unparameterised query fragments (f-string or `.format()` used in database queries).
  - Auth token handling: tokens passed in URLs, stored insecurely, or logged in plaintext.
  - Unsafe deserialisation: unsafely loading user-supplied or external strings.
  - JWT algorithm `none` acceptance or missing signature verification.
- **Least Privilege**: Only grant the permissions necessary for the task.
- **Secrets Protection**: No secrets, API keys, or credentials in code, logs, or error messages.

---

## Pass 6 — Performance 🟡

- **N+1 queries**: Loops calling database or repository methods per iteration without eager loading.
- **Missing indexes**: New database tables or query columns lacking proper index declarations.
- **Unbounded queries**: Ensure list endpoints paginate and restrict max result sizes.

---

## Pass 7 — Testing 🟠

- **TDD Law**: New public functions and service methods must have at least one test.
- **Test Integrity**: Assert correct outcomes and state changes (e.g. transactions committed).
- **Test Boundaries**: Use unit tests for services (mocking external dependencies) and integration tests for end-to-end flows.

---

## Pass 8 — Documentation & Hygiene 💡

- **Public APIs**: Document inputs, outputs, and exceptions raised.
- **No commented-out code** or stale debug print statements in production.
- **No `# TODO`** without a linked issue number or tracking reference.

---

## Quick Invariant Checklist

Before approving any PR, confirm:
- [ ] No internal/domain layer importing from outer layers
- [ ] No business logic in handlers/routers
- [ ] No generic exception catching without raise
- [ ] New functionality has tests
- [ ] Methods called actually exist (API hallucination check)
- [ ] Concurrent read-modify-write sequences are lock-protected (latent race condition check)
- [ ] No unparameterised SQL queries or unsafe token logging (implicit security check)
- [ ] New code follows established project patterns, not locally-invented alternatives (architectural coherence check)
