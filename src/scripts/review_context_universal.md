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
