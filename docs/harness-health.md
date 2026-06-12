# Harness Health Monitoring Specifications

This document defines the health monitoring checks, configuration parameters, and logic used by `harness_health.py` to ensure the integrity and performance of the AI Delivery Control system.

---

## Dream Proposal Staleness (HIB-HEALTH-01)

### Purpose
To detect when automatically synthesized dream proposals are going stale without human review, preventing accumulated drift and developer ignore loops.

### Configuration Schema
The following configuration parameters are defined under the `dream_proposals` namespace:
- `dream_proposals.staleness_warn_days` (default: `30`): Number of days before an open proposal triggers a warning.
- `dream_proposals.staleness_critical_days` (default: `90`): Number of days before an open proposal triggers a critical degradation alert.
- `dream_proposals.max_open_proposals` (default: `10`): Maximum number of open proposals allowed before generating a warning card.

### Behavior
For each proposal matching `*__open.md` in `.agent/state/dream_proposals/`:
1. Parse the frontmatter metadata for the `Generated: YYYY-MM-DD` field.
2. Compute the proposal's age in days against UTC timezone-naive datetime.
3. Emit a warning if age is greater than or equal to `staleness_warn_days`.
4. Emit a critical/degrading status if age is greater than or equal to `staleness_critical_days`.
5. Emit a warning if total open proposal count exceeds `max_open_proposals`.



---

## State File Size Checks (HIB-HEALTH-02)

### Purpose
To detect unbounded size growth in harness state files. This is especially critical for `repo_graph_cache.json` which lies directly in the synchronous pre-commit review path, preventing latency degradation (FM3 failure mode).

### Thresholds & Configuration
Configured under the `health_checks.state_file_size` namespace:

| Target File | Warn (MB) Key | Critical (MB) Key | Default Warn (MB) | Default Critical (MB) | Priority / Impact |
|-------------|---------------|-------------------|-------------------|-----------------------|-------------------|
| `.agent/state/repo_graph_cache.json` | `repo_graph_cache_warn_mb` | `repo_graph_cache_critical_mb` | 2 | 10 | High (Synchronous path, FM3) |
| `.agent/state/harness_events.jsonl` | `harness_events_warn_mb` | `harness_events_critical_mb` | 5 | 20 | Medium (Audit log) |
| `.ai-review-log.jsonl` | `ai_review_log_warn_mb` | `ai_review_log_critical_mb` | 5 | 20 | Medium (Review log) |
| `.agent/state/session_ledger.jsonl` | `session_ledger_warn_mb` | `session_ledger_critical_mb` | 1 | 5 | Low (Session history) |



---

## Dream Phase Threshold Logic (HIB-DREAM-03)

### GymBase Diagnosis
During framework analysis, it was identified that the Dream Phase was silently non-functional on the GymBase project. Across 79 active sessions, GymBase suffered 17 review FAILs, yet generated exactly 0 optimization proposals. The root cause was that well-functioning projects operating normally never escalate sessions (escalated counts = 0, rate = 0.0), but the existing threshold logic required the escalation rate condition to be met conjunctively alongside the appearance rate.

### Before/After Formulas

**Old Logic (Conjunctive, strict AND)**:
```python
is_flagged = (
    count >= 3 and escalation_rate >= 0.40 and appearance_rate >= 0.20
) or max_severity == "CRITICAL"
```

**New Logic (Disjunctive rate checks, OR)**:
```python
is_flagged = (
    count >= 3
    and (appearance_rate >= 0.20 or escalation_rate >= 0.40)
) or max_severity == "CRITICAL"
```
Under the new logic, any pattern appearing in $\ge 20\%$ of sessions within a 30-day window qualifies for a proposal card, regardless of whether those sessions resulted in escalations/halts.
