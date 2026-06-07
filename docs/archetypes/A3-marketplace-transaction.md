# A3 — Marketplace & Transaction

**Core AT concerns**: AT1 (Consistency), AT9 (Correctness)
**Dominant FM concerns**: FM4 (Data Consistency), FM10 (Security Breach), FM12 (Split-Brain)
**GymBase classification**: A3

## Domain registry starter (copy to .agent/config.yaml → domain_registry)

```yaml
domain_registry:
  branch_isolation:
    description: "Multi-tenant data isolation — FM10"
    adr_paths: []    # Add: docs/decisions/adr/your-adr.md when authored
    review_context_section: "BRANCH_ISOLATION"
    at_weight: AT1
    fm_primary: FM10

  transactional_integrity:
    description: "ACID guarantees for financial/booking operations — FM4"
    adr_paths: []
    review_context_section: "TRANSACTIONAL_INTEGRITY"
    at_weight: AT9
    fm_primary: FM4

  mass_assignment:
    description: "Input validation and privilege escalation prevention — FM10"
    adr_paths: []
    review_context_section: "MASS_ASSIGNMENT"
    at_weight: AT9
    fm_primary: FM10

  schema_hardening:
    description: "Schema contract stability — FM8"
    adr_paths: []
    review_context_section: "MIGRATIONS"
    at_weight: AT3
    fm_primary: FM8
```

## review_context_project.md template section for A3

```markdown
## System Archetype
A3 — Marketplace & Transaction (Engineer's Map F6).
AT concerns: AT1 (Consistency), AT9 (Correctness).
FM concerns: FM4 (Data Consistency), FM10 (Security Breach), FM12 (Split-Brain).
Weight BRANCH_ISOLATION and TRANSACTIONAL_INTEGRITY findings at FAIL level.
A borderline WARN on FM10 or FM4 domains should be treated as FAIL for this archetype.
```
