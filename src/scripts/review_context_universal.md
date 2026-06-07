# Universal Architecture Guidelines — AI Review Invariants
# Version: 1.0 (Framework-Owned)

> This file contains the framework's universal architectural guidelines and baseline
> micro-checks. It is managed by the governance harness and should not be modified.

---

## [RULE:SECRETS] Secrets and Credentials Protection
<!-- SECTION:secrets -->

Never commit secrets, API keys, passwords, database credentials, or tokens to version control.
Always use environment variables or a secure secret manager.

---

## [RULE:TDD-LAW] Test-Driven Development Iron Law
<!-- SECTION:tdd_law -->

Every new feature, bug fix, or service method must have corresponding tests.
Flag any staged code change that lacks test coverage or disables/weakens existing tests.

---

## [RULE:DATABASE-BYPASS] Bypassing Repository Layers
<!-- SECTION:database_bypass -->

Domain/business and presentation layers must not access database sessions or queries directly.
Always route database access through a Repository or Unit of Work pattern layer to ensure transactional safety.

---

## [RULE:CLEAN-CODE] Commented-out Code & Dead Code
<!-- SECTION:clean_code -->

Never commit commented-out code blocks or obsolete functions in source files.
Clean up dead imports and stale placeholders before staging.

---

## [RULE:DEPENDENCIES] Dependency Governance
<!-- SECTION:dependencies -->

Any addition, removal, or modification of dependencies in pyproject.toml, package.json, or other package files must be explicitly documented and listed for developer/user review.

---

## [SENSOR:DIFF-AUDIT] Universal Micro-Check Prompts
<!-- SECTION:micro_checks -->

When the staged diff contains any of the following patterns, check the corresponding requirement.

| If the diff adds or changes...                                    | Then check...                                                                                                                                                                              | Default severity |
|-------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| A new outbound HTTP call (`requests.*`, `httpx.*`, `urllib.*`)    | Does it specify an explicit `timeout=` parameter (both connect and read)?                                                                                                                  | MEDIUM           |
| A new `logger.error(...)` inside an `except` block               | Does it include `exc_info=True`?                                                                                                                                                           | LOW              |
| A new `Mapped[dict]` / `JSON` column in database models           | Is there a corresponding validation schema added in the same diff?                                                                                                                         | MEDIUM           |
| A new `*Create` or `*Update` schema                               | Does it forbid extra fields (`{"extra": "forbid"}`)?                                                                                                                                       | MEDIUM           |
| A new `retry` loop or exception-and-retry pattern               | Does it use exponential backoff with jitter rather than a fixed sleep?                                                                                                                    | LOW              |

---

## [APPENDIX:VOCABULARY] Engineering Vocabulary — AT/FM Codes

<!-- SECTION:vocabulary -->

When naming findings in your review verdict, use AT/FM codes where applicable.
State the specific reason the code applies — never the generic definition.
Example: "FM9: silent data corruption — log_unauthorized_access writes are
silently dropped on exception paths because the test fixture commits where
production get_db() does not."

### AT — Architecture Tradeoffs (10)

Every design decision resolves one of these.

| Code | Name                           | You are choosing between                          |
|------|--------------------------------|---------------------------------------------------|
| AT1  | Consistency vs Availability    | Correct data vs system stays up                   |
| AT2  | Latency vs Throughput          | Speed per request vs requests per second          |
| AT3  | Simplicity vs Flexibility      | Easy to understand vs easy to extend              |
| AT4  | Precomputation vs On-Demand    | Pay at write time vs pay at read time             |
| AT5  | Centralisation vs Distribution | Single authority vs no single point of failure    |
| AT6  | Generality vs Specialisation   | All cases vs common case optimised                |
| AT7  | Automation vs Control          | System decides vs human decides                   |
| AT8  | Coupling vs Cohesion           | Independent deployment vs co-located logic        |
| AT9  | Correctness vs Performance     | Right answer vs fast answer                       |
| AT10 | Synchronous vs Asynchronous    | Immediate response vs deferred processing         |

### FM — Failure Modes (12)

Every component introduces at least one.

| Code | Name                           | What goes wrong                                   |
|------|--------------------------------|---------------------------------------------------|
| FM1  | Single Point of Failure        | One component dies, system dies                   |
| FM2  | Cascading Failures             | One failure triggers the next                     |
| FM3  | Unbounded Resource Consumption | Memory / connections / threads grow without limit |
| FM4  | Data Consistency Failure       | Components disagree on state                      |
| FM5  | Latency Amplification          | Small latencies multiply across hops              |
| FM6  | Hotspotting                    | One node gets disproportionate load               |
| FM7  | Thundering Herd                | Mass simultaneous retry overwhelms recovery       |
| FM8  | Schema / Contract Violation    | One side of a boundary changes, other breaks      |
| FM9  | Silent Data Corruption         | Wrong data propagates without alerts              |
| FM10 | Security Breach                | Unauthorised access to data or compute            |
| FM11 | Observability Blindness        | System fails but team cannot see where            |
| FM12 | Split-Brain                    | Two nodes both think they are primary             |

### System Archetype Classification (project-specific)

Your project's archetype classification and the corresponding FM weights belong in
`review_context_project.md`, not here.

When `review_context_project.md` defines a system archetype, weight the associated
failure modes most heavily when reviewing diffs for that project.

**How to classify your project**: identify which of the six archetypes best describes
the system, or which combination applies:

| Code | Archetype                  | Core concern                   | FM weights        |
|------|----------------------------|--------------------------------|-------------------|
| A1   | Search & Discovery         | Relevance + latency            | FM6, FM3          |
| A2   | Social & Communication     | Delivery + fan-out             | FM3, FM6, FM7     |
| A3   | Marketplace & Transaction  | Correctness + consistency      | FM4, FM10         |
| A4   | Media Delivery             | CDN hit rate + storage         | FM6, FM8          |
| A5   | Data Intelligence          | Quality + freshness            | FM8, FM9          |
| A6   | Platform & API             | Reliability + backwards compat | FM2, FM8          |

Add to your `review_context_project.md`:

```
## System Archetype
[A1–A6 or combination — e.g. "A3 Marketplace & Transaction"]

### Archetype FM Weights
[List which failure modes to weight most heavily for this codebase
and map them to your project-specific architectural invariants]

Example (A3 project):
FM4 Data Consistency Failure → maps to: [your UoW/transaction rules]
FM10 Security Breach         → maps to: [your RBAC/auth rules]
FM8  Schema Violation        → maps to: [your migration detection rules]
FM9  Silent Data Corruption  → maps to: [your audit log path rules]
```

### Decision Block Format (ADVISORY check)

When a commit introduces a new architectural pattern — new service, new async boundary,
new data store, new external integration — check whether the referenced ADR contains a
decision block in this format:

```
Decision: [what was chosen]
Tradeoff: AT[N] — choosing [pole] because [reason]
Exposes:  FM[N] — [what could go wrong]
Mitigation: [how the failure mode is addressed]
```

A decision that cannot name its AT tradeoff or its exposed FM is an incomplete
architectural record. Flag as ADVISORY.

*Source: The Computing Series — computingseries.com (CC BY 4.0)*

## Gate Finding Output Format

Every FAIL and qualifying WARN finding in the gate verdict must use the decision
block format. A finding that cannot be expressed in this format is a suspicion,
not a finding — return suspicions as questions to the developer, not as blocking
concerns.

Required format for each FAIL or WARN finding:

```
Finding:      [one sentence — what the code does, not what it should do]
Tradeoff:     AT[N] — this code chose [specific pole] which [consequence for this system]
Exposes:      FM[N] — this creates [specific named risk]; [file:line if determinable]
Remediation:  [specific change that addresses the FM without reverting the AT intent]
```

Rules:
- AT and FM codes must come from the vocabulary tables above. No invented codes.
- The Tradeoff line names a specific pole, not just the tradeoff category.
  Incorrect: "AT1 — consistency vs availability"
  Correct:   "AT1 — this code chose availability; the cache write precedes the database
              commit, so a crash between the two leaves the cache holding a value the
              database will never confirm"
- The Exposes line names a specific risk in this codebase, not the generic FM definition.
  FM10 and FM4 findings at FAIL severity must include file:line.
- The Remediation addresses the FM. "Delete this" is not a remediation.
- PASS_FAST and PASS verdicts do not require the decision block.
- WARN verdicts require the decision block when the concern touches FM4, FM9, FM10,
  or FM12. For other WARN concerns it is encouraged but not required.

