# Capability Calibration Design (T1-G-14 prerequisite)

**Status**: Design specification — prerequisite for T1-G-14 implementation.
**Source**: Deep research into production calibration patterns (June 2026),
synthesised against the harness's existing audit trail (`.ai-review-log.jsonl`,
T1-G-06 rebuttal protocol).

## Problem statement (AT9)

The gate applies the same WARN/FAIL threshold to every review capability
(BRANCH_ISOLATION, SCHEMA_HARDENING, INTENT_ALIGNMENT, TEST_COVERAGE, etc.)
regardless of that capability's historical accuracy on this specific project.
A capability with a high false-positive rate erodes trust and increases
rebuttal overhead (T1-G-06). A capability with a high false-negative rate
(issues that slip through and get silently corrected in a later commit)
provides a false sense of coverage.

AT9 (Correctness vs Permissiveness): per-capability calibration is the
mechanism for resolving this tradeoff per-project, per-capability, rather
than globally and uniformly.

## Per-domain cost-of-false-negative table

| Capability | Cost of false negative | Cost of false positive | Initial bias |
|------------|------------------------|--------------------------|---------------|
| BRANCH_ISOLATION | High (cross-tenant data leak) | Medium (developer friction) | Favour FAIL |
| SCHEMA_HARDENING | High (migration irreversibility) | Medium | Favour FAIL |
| TRANSACTIONAL_INTEGRITY | High (data corruption) | Medium | Favour FAIL |
| INTENT_ALIGNMENT | Medium (scope drift, caught later by acceptance gate) | High (blocks legitimate work) | Favour WARN |
| TEST_COVERAGE | Low (caught by CI) | High (blocks minor changes) | Favour WARN |
| CODE_QUALITY | Low | High | Favour WARN |
| ANTI_PATTERNS | Medium | Medium | Neutral |

This table is a starting point — `harness_health.py` calibration WARN output
(below) is the mechanism that corrects these initial biases based on actual
project history.

## Calibration data source

`.ai-review-log.jsonl` already records, per commit, per capability:
- The verdict issued (PASS/WARN/FAIL)
- Whether a rebuttal was filed (T1-G-06 ✅) and its outcome
  (REBUTTAL_ACCEPTED / REBUTTAL_REJECTED)

This is sufficient — no new instrumentation required:

- **REBUTTAL_ACCEPTED** on a WARN/FAIL → false positive signal for that capability
- **REBUTTAL_REJECTED**, or a FAIL/WARN with no rebuttal filed → true positive signal
  (the finding stood)
- (Future, not in scope for T1-G-14 initial implementation) a PASS verdict
  followed by a subsequent commit that reverts/substantially modifies the
  same files within 2 commits — implicit false negative signal. This is
  T1-C-04 (silent correction rate), tracked separately. T1-G-14's initial
  implementation uses only the rebuttal-derived signal above.

## Calibration algorithm

### Cold start

Each capability starts with a Laplace prior: 1 false positive, 1 true
positive (i.e. assumed 50% precision). This avoids divide-by-zero and
avoids over-reacting to the first 1-2 data points.

### Running calculation

For each capability, maintain two counters in
`.agent/state/capability_calibration.json` (gitignored, derived data —
regenerable from `.ai-review-log.jsonl`):

```json
{
  "schema_version": "1.0",
  "capabilities": {
    "BRANCH_ISOLATION": {"tp": 1, "fp": 1, "weight": 1.0},
    "INTENT_ALIGNMENT": {"tp": 4, "fp": 9, "weight": 0.85}
  }
}
```

`precision = tp / (tp + fp)`.

### Weight update (multiplicative, not statistical interval)

On each new rebuttal outcome for a capability:
- REBUTTAL_ACCEPTED (false positive confirmed): `fp += 1`, `weight *= 0.9`
- REBUTTAL_REJECTED or uncontested (true positive): `tp += 1`, `weight *= 1.05`

Clamp `weight` to `[0.5, 1.5]`. A weight below 1.0 means "this capability's
findings are weighted down — borderline WARNs in this capability stay WARN
rather than escalating to FAIL." A weight above 1.0 means the inverse —
borderline findings escalate.

This multiplicative approach is deliberately simpler than a Wilson-score
confidence interval: fewer edge cases, easier to reason about, and the
clamped range prevents runaway drift from a small number of data points.

### Repeat-finding escalation (independent signal)

Independent of the precision-based weight: if the same finding (same
capability, same file, same `blocking_concern` text or a close match) appears
in `.ai-review-log.jsonl` on two consecutive commits to the same file without
being addressed, escalate that specific finding from WARN to FAIL regardless
of the capability's general weight. This is a per-finding signal, not a
per-capability one — "this was raised and ignored" is stronger evidence than
general capability precision.

## Required behaviour for ai_review.py

1. At startup, read `.agent/state/capability_calibration.json`. If absent,
   treat all weights as 1.0 (no calibration applied — current behaviour).
2. After the routing step (T1-G-01) determines which capabilities are active
   for this diff, apply each capability's weight to that capability's
   findings: a WARN-level finding in a capability with weight ≥ 1.1 is
   elevated to FAIL; a WARN-level finding in a capability with weight ≤ 0.9
   stays WARN even if the reviewing model's initial assessment leaned FAIL.
3. Inject the applied weight as a policy note: e.g.
   `"INTENT_ALIGNMENT findings treated as WARN-only (calibration weight 0.85,
   based on 9 false positives / 4 confirmed in this project's history)."`
   This makes calibration visible and auditable, not a silent adjustment.
4. After the gate verdict is finalised and any rebuttal is resolved, update
   `capability_calibration.json` with the new tp/fp counts and recalculated
   weight for the affected capability.

## harness_health.py integration

Add a "Capability Calibration" section to `harness_health.py` output:
- List each capability with current weight and precision
- Flag any capability with precision < 0.30 (rebuttal rate > 0.70) as
  DEGRADING — this capability is generating mostly false positives and its
  rules may need revision (feeds dream phase pattern detection, T1-D-03)
- Flag any capability with weight at the clamp boundary (0.5 or 1.5) as
  worth manual review — the automatic calibration has reached its limit and
  a rule change (not just a weight change) may be warranted

## config.yaml schema (documentation only — do NOT add to config.yaml yet)

```yaml
capability_calibration:
  enabled: true  # if false, all weights treated as 1.0
  overrides:
    # Manual override — pins a capability's weight regardless of computed value.
    # Use for capabilities where the cost table above should NOT be
    # auto-calibrated (e.g. BRANCH_ISOLATION should arguably never be
    # weighted down regardless of false-positive history, given the cost
    # asymmetry in the cost-of-false-negative table).
    BRANCH_ISOLATION: 1.0  # pinned, not auto-calibrated
```

This config block must NOT be added to `.agent/config.yaml` until T1-G-14
code ships — this section documents the intended schema only.

## AT9 decision block

```
Decision / Tradeoff: AT9 — choosing per-project calibration over uniform
  global thresholds because a capability's accuracy varies by codebase and
  by the specific patterns that recur in that codebase's history.
Exposes: FM-calibration-drift — a capability could drift toward weight 0.5
  (effectively disabled) purely from a run of unlucky false positives early
  in a project's history, before enough data accumulates to stabilise.
Mitigation: Laplace prior (1 TP, 1 FP) slows early drift; clamping to
  [0.5, 1.5] bounds the maximum effect; manual overrides in config allow
  pinning high-cost capabilities (BRANCH_ISOLATION, SCHEMA_HARDENING,
  TRANSACTIONAL_INTEGRITY) regardless of computed weight.
```
