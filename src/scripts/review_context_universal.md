# Universal Architecture Guidelines — AI Review Invariants
# Version: 1.0 (Framework-Owned)

> This file contains the framework's universal architectural guidelines and baseline
> micro-checks. It is managed by the governance harness and should not be modified.

---

## [RULE:SECRETS] Secrets Protection
<!-- SECTION:secrets -->
No secrets, keys, or credentials in git. Use environment variables/secret managers.

---

## [RULE:TDD-LAW] TDD Law
<!-- SECTION:tdd_law -->
All new features, fixes, or service methods must have corresponding tests. Do not weaken/disable tests.

---

## [RULE:DATABASE-BYPASS] Repository Bypass
<!-- SECTION:database_bypass -->
Domain/business/API layers must route DB access through Repository/Unit of Work; no direct session/query access.

---

## [RULE:CLEAN-CODE] Dead Code
<!-- SECTION:clean_code -->
Clean up dead/commented-out code, obsolete functions, dead imports, and stale placeholders.

---

## [RULE:DEPENDENCIES] Dependency Governance
<!-- SECTION:dependencies -->
Document and list all pyproject.toml/package.json/dependency changes for review.

---

## [SENSOR:DIFF-AUDIT] Micro-Checks
<!-- SECTION:micro_checks -->
- HTTP calls (`requests`/`httpx`/`urllib`): check for explicit `timeout=` (connect & read) [MEDIUM]
- `logger.error` in `except`: check for `exc_info=True` [LOW]
- `Mapped[dict]`/`JSON` column: check for validation schema in same diff [MEDIUM]
- `*Create`/`*Update` schema: check for extra field restriction (`extra="forbid"`) [MEDIUM]
- `retry` loop: check for exponential backoff + jitter [LOW]

---

## [APPENDIX:VOCABULARY] AT/FM Vocabulary
<!-- SECTION:vocabulary -->
Use AT/FM codes in verdicts. Define specific reasons.
AT Tradeoffs: AT1 Consistency vs Availability, AT2 Latency vs Throughput, AT3 Simplicity vs Flexibility, AT4 Precomputation vs On-Demand, AT5 Centralisation vs Distribution, AT6 Generality vs Specialisation, AT7 Automation vs Control, AT8 Coupling vs Cohesion, AT9 Correctness vs Performance, AT10 Synchronous vs Asynchronous.
FM Failure Modes: FM1 Single Point of Failure, FM2 Cascading Failures, FM3 Unbounded Resource Consumption, FM4 Data Consistency Failure, FM5 Latency Amplification, FM6 Hotspotting, FM7 Thundering Herd, FM8 Schema/Contract Violation, FM9 Silent Data Corruption, FM10 Security Breach, FM11 Observability Blindness, FM12 Split-Brain.
Archetypes: A1 Search & Discovery, A2 Social, A3 Marketplace/Transaction, A4 Media, A5 Data Intelligence, A6 Platform/API.

---

## [RULE:ADR-DECISION-BLOCK] Decision Block Format (ADVISORY check)
<!-- SECTION:adr_decision_block -->
For new patterns (service, async boundary, data store, external integration), ADR must contain a decision block in format:
```
Decision: [what was chosen]
Tradeoff: AT[N] — choosing [pole] because [reason]
Exposes:  FM[N] — [what could go wrong]
Mitigation: [how the failure mode is addressed]
```
If missing, flag as ADVISORY.

## Finding Format
All FAIL/WARN verdicts must use format:
```
Finding:      [one sentence - what code does]
Tradeoff:     AT[N] - chose [specific pole] with [consequence]
Exposes:      FM[N] - [specific risk]; [file:line if FM4/FM10 FAIL]
Remediation:  [specific change addressing the FM without reverting AT intent]
```
Rules:
- Codes from vocabulary only. Tradeoff must name specific pole. Exposes must name specific risk.
- FM4/FM10 FAIL findings must include file:line.
- WARN requires format only for FM4/FM9/FM10/FM12. PASS/PASS_FAST do not require it.
