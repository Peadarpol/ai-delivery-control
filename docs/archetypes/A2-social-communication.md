# A2 — Social & Communication

**Core AT concerns**: AT1 (lean Availability), AT10 (Async)
**Dominant FM concerns**: FM3 (Unbounded Resource Consumption), FM6 (Hotspotting), FM7 (Thundering Herd)

## Domain registry starter

```yaml
domain_registry:
  fan_out_safety:
    description: "Message fan-out to subscribers — FM3/FM7"
    adr_paths: []
    review_context_section: "FAN_OUT"
    at_weight: AT10
    fm_primary: FM7

  rate_limiting:
    description: "Per-user and per-endpoint rate limits — FM3"
    adr_paths: []
    review_context_section: "RATE_LIMITING"
    at_weight: AT7
    fm_primary: FM3

  consistency_model:
    description: "Feed staleness tolerance — AT1 availability preference"
    adr_paths: []
    review_context_section: "CONSISTENCY_MODEL"
    at_weight: AT1
    fm_primary: FM4
```

## review_context_project.md template section for A2

```markdown
## System Archetype
A2 — Social & Communication (Engineer's Map F6).
AT concerns: AT1 (lean Availability), AT10 (Async fan-out).
FM concerns: FM3 (Unbounded Resource), FM6 (Hotspotting), FM7 (Thundering Herd).
Weight fan-out and rate-limiting findings heavily. Feed staleness is acceptable;
double-delivery and resource exhaustion are not.
```
