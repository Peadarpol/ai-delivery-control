# A6 — Platform & API

**Core AT concerns**: AT3 (Simplicity vs Flexibility), AT8 (Coupling vs Cohesion)
**Dominant FM concerns**: FM2 (Cascading Failures), FM8 (Schema/Contract Violation)
**AI Delivery Control self-classification**: A6

## Domain registry starter

```yaml
domain_registry:
  api_versioning:
    description: "Backwards compatibility — FM8"
    adr_paths: []
    review_context_section: "API_VERSIONING"
    at_weight: AT3
    fm_primary: FM8

  dependency_isolation:
    description: "Plugin coupling boundaries — FM2"
    adr_paths: []
    review_context_section: "DEPENDENCY_ISOLATION"
    at_weight: AT8
    fm_primary: FM2

  schema_contracts:
    description: "Data contract stability across versions — FM8"
    adr_paths: []
    review_context_section: "SCHEMA_CONTRACTS"
    at_weight: AT3
    fm_primary: FM8
```

Note: AI Delivery Control uses this starter pack for its own domain registry.
The `harness_events.jsonl` schema, `ReviewVerdict` model, and `session.json`
are all A6 schema contracts documented in `docs/state-file-schema.md`.
