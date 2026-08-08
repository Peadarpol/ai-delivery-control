# `schema_hardening_fixture` — hermetic fixture project

Fixture project for **Scenario 6** of `SPEC-loop-closure-verification.md` (T1-K-19), consumed by
`tests/helpers/outcome_equivalence.py` and `tests/integration/test_outcome_equivalence.py`.

## What this is

A minimal, standalone project tree carrying **known operational schema-hardening exemption values**
in the same shape as the real incident described in the spec's §0 Motivation Gate: a refactor claimed
to preserve a project's `WHITELIST` / `exempt_tables` values while moving them from inline Python
constants to config-driven YAML, and silently emptied them instead. The full suite stayed green
because no test asserted the specific *data* survived — only that the code still ran.

## What this is deliberately NOT

Per §3's resolved assumption, this is **not** GymBase's real data and must never be replaced with it.
Every value here is prefixed `fixture_` or lives under `src/domain/schemas/fixture_*.py` precisely so
it cannot be mistaken for, or silently swapped with, a real project's operational config. Tests copy
this tree into a `tmp_path` before mutating it — the checked-in fixture is read-only in practice.

## Layout

```
schema_hardening_fixture/
  .agent/config.yaml                    # the tracked operational values (whitelist + exempt_tables)
  src/domain/schemas/fixture_alpha.py   # a whitelisted schema module, referenced by the whitelist
  src/domain/schemas/fixture_beta.py    # a second whitelisted schema module
```

The two `src/domain/schemas/fixture_*.py` modules exist so the whitelist entries point at real paths
within the fixture rather than at nothing — the same relationship `enforce_hardened_schemas.py`'s
`load_whitelist()` assumes against a live project.

## Tracked values

| Logical name | Artifact | Key path |
|---|---|---|
| `schema_whitelist` | `.agent/config.yaml` | `schema_hardening.whitelist` |
| `exempt_tables` | `.agent/config.yaml` | `schema_hardening.exempt_tables` |

These two are the fixture's entire point. Changing them requires updating
`tests/integration/test_outcome_equivalence.py`'s expectations in the same edit.
