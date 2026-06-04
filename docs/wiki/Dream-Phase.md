# The Dream Phase

The framework's self-improvement loop. It reads recurring failure patterns and proposes targeted updates to your project-specific review rules.

---

## What Is the Dream Phase?

Once a week (configurable), the framework:

1. **Collects data** from the past 30 days:
   - `.ai-review-log.jsonl` — gate verdicts and violations
   - `.harness_events.jsonl` — escalations, rebuttals, skips, halt events

2. **Analyzes patterns**:
   - Which rules trigger repeatedly?
   - Which rebuttals were accepted?
   - Which commits triggered gate contradictions?

3. **Generates proposals**:
   - Tighten a rule (reduce false negatives)
   - Loosen a rule (reduce false positives)
   - Add a new rule based on failure pattern
   - Deprecate a rule that's no longer needed

4. **Routes proposals** to skill files:
   - Proposal for architecture → routes to `.agent/skills/senior-architect/`
   - Proposal for testing → routes to `.agent/skills/test-engineer/`

5. **Requires human review**:
   - You review each proposal
   - Accept to apply it
   - Reject if it's not applicable

---

## Why It Exists

**Problem:** Generic frameworks make assumptions that don't fit your codebase.

**Solution:** Let the framework learn from your actual patterns.

**Example:**
- Week 1: Framework rejects "queries without tenant filters" (FAIL)
- You use rebuttal: "Our base repository class wraps all queries"
- Week 2: Dream phase detects the pattern (5 rebuttals accepted)
- Proposal: "Update BRANCH_ISOLATION rule to account for repository wrapping patterns"
- You accept
- Week 3+: No more false positives on wrapped queries

---

## Dream Phase Workflow

### 1. Trigger Conditions

Dream phase runs at session start if:
- ✅ **Data threshold met**: 30+ days of events + verdicts
- ✅ **Cooldown passed**: Last run was >7 days ago
- ✅ **Change detected**: Recent rebuttals, escalations, or halt events

Or it's forced by:
- Previous session was escalated (critical issue)
- Critical events detected in `harness_events.jsonl`

### 2. Data Collection

```json
// .ai-review-log.jsonl
{
  "timestamp_utc": "2026-06-04T10:30:00Z",
  "commit_sha": "abc123...",
  "verdict": "FAIL",
  "violation_id": "BRANCH_ISOLATION",
  "severity": "HIGH"
}

// .harness_events.jsonl
{
  "event_type": "rebuttal_accepted",
  "violation_id": "BRANCH_ISOLATION",
  "timestamp_utc": "2026-06-04T10:35:00Z",
  "payload": {
    "reason": "Dynamic wrapping accounts for isolation"
  }
}
```

### 3. Pattern Analysis

Dream phase calculates:
- **Frequency**: How often does rule X trigger?
- **Acceptance rate**: What % of rebuttals against rule X were accepted?
- **Contradiction**: Do rules X and Y ever conflict?
- **Drift**: Is the codebase pattern diverging from the rule?

**Thresholds for proposals:**
- **New rule**: 5+ violations in 30 days + consistent pattern
- **Tighten rule**: <30% rebuttal acceptance rate
- **Loosen rule**: >50% rebuttal acceptance rate
- **Deprecate rule**: 0 violations in 60 days

### 4. Proposal Generation

Dream phase creates a proposal file:

```markdown
# Proposal: BRANCH_ISOLATION Rule Update

**Generated**: 2026-06-04 (Dream Phase v1.3.1)
**Routed to skill**: `.agent/skills/senior-architect/`

## Analysis

- **Pattern detected**: 7 false positives on queries wrapped by base repository class
- **Rebuttal acceptance**: 100% (7/7 rebuttals accepted)
- **Recommendation**: Update rule to account for wrapping patterns

## Proposed Change

**File**: `src/scripts/review_context_project.md`
**Rule**: `[RULE:BRANCH_ISOLATION]`

**Current**:
```markdown
Every query must explicitly call _apply_branch_filter()
```

**Proposed**:
```markdown
Every query must apply branch isolation via:
1. Explicit _apply_branch_filter() call, OR
2. Base repository class wrapping (repositories/base.py)
```

## Acceptance Criteria

- [ ] Human reviews and accepts proposal
- [ ] Rule updated in `review_context_project.md`
- [ ] Next gate run uses updated rule
- [ ] No regression: existing passing commits still pass

---

## Risk Assessment

**False positive risk**: LOW (based on 100% rebuttal acceptance)
**Security risk**: NONE (rule is being clarified, not loosened)
**Effort**: 2 min to review and accept
```

### 5. Proposal Storage

Proposals are stored in:
```
.agent/state/dream_proposals/
├── proposal__2026-06-04__001__open.md
├── proposal__2026-06-04__002__open.md
└── proposal__2026-05-28__001__accepted.md
```

**States:**
- `__open.md` — waiting for human review
- `__accepted.md` — accepted and applied
- `__rejected.md` — human rejected

---

## Reviewing Proposals

### How to Find Proposals

At session start, init_session.py reports:
```
[DREAM] 3 open proposals awaiting review
  proposal__2026-06-04__001__BRANCH_ISOLATION.md
  proposal__2026-06-04__002__TEST_COVERAGE.md
  proposal__2026-06-04__003__NEW_RULE.md

Review and decide: accept / reject
```

### How to Review

1. **Open the proposal**
   ```bash
   cat .agent/state/dream_proposals/proposal__2026-06-04__001__open.md
   ```

2. **Evaluate:**
   - Is the pattern real?
   - Is the proposal reasonable?
   - Any edge cases the analysis missed?

3. **Accept or reject:**
   ```bash
   # Accept: move file to _accepted suffix
   mv proposal__2026-06-04__001__open.md proposal__2026-06-04__001__accepted.md
   git add .agent/state/dream_proposals/
   git commit -m "dream: accept proposal 001 (BRANCH_ISOLATION update)"
   ```

   ```bash
   # Reject: move file to _rejected suffix with reason
   mv proposal__2026-06-04__001__open.md proposal__2026-06-04__001__rejected.md
   # Edit file to add rejection reason
   ```

### Conflict Detection

If a proposal would contradict existing rules, dream phase warns:

```markdown
⚠️ CONFLICT DETECTED

Proposal updates BRANCH_ISOLATION rule.
Existing rule TRANSACTION_INTEGRITY may conflict:

BRANCH_ISOLATION (proposed): "Queries wrapped by base repository are OK"
TRANSACTION_INTEGRITY: "All DB changes must be wrapped in transactions"

Potential issue: Base repository wrapping applies isolation but not transactions?

Resolution: Review senior-architect skill and coordinate before accepting.
```

---

## Configuration

**File**: `.agent/config.yaml` → `dream_phase:`

```yaml
dream_phase:
  enabled: true
  run_interval_days: 7              # Run weekly
  data_window_days: 30              # Analyze past 30 days
  min_data_points: 5                # Minimum events for pattern
  min_rebuttal_acceptance: 0.50     # 50% = "loosen rule"
  max_rebuttal_acceptance: 0.70     # <70% = "rule is too strict"
  cooldown_days: 7                  # Don't run more than weekly
  force_on_escalation: true         # Run immediately if session escalated
```

---

## Example Proposal Timeline

### Day 1 (Monday)
Commit 1: Query missing branch filter → `FAIL` → You write rebuttal → `ACCEPTED`

### Day 3 (Wednesday)
Commit 2: Similar query missing filter → `FAIL` → Rebuttal again → `ACCEPTED`

### Day 7 (Sunday, Week 2)
Session starts. Dream phase detects pattern:
- 7 FAILs on BRANCH_ISOLATION
- 7/7 rebuttals accepted
- Conclusion: Rule is too strict

Proposal generated: "Loosen BRANCH_ISOLATION rule"

### Day 8 (Monday)
You review proposal:
- Reason: Base repository class wraps all queries
- Analysis: Correct
- Decision: Accept ✅

**Result:**
```markdown
✅ Accepted
Update review_context_project.md rule
Add note: "Base repository wrapping counts as applied isolation"
```

### Day 9 (Tuesday, Week 2)
Next commit: Similar query → `PASS` (rule updated)

---

## Tips for Using Dream Phase

### ✅ Do

- Review proposals promptly (they accumulate)
- Accept proposals that match your actual patterns
- Use rebuttals liberally (they feed dream phase)
- Document contradictions in rejected proposals

### ❌ Don't

- Ignore proposals for weeks
- Accept proposals that don't match your codebase
- Bypass gate instead of using rebuttals (dream phase won't learn)
- Disable dream phase just because proposals are inconvenient

---

## Monitoring Dream Phase Health

At session start, check:

```
[DREAM] Status: HEALTHY
  Last run: 2026-06-04
  Proposals: 3 open, 12 accepted, 1 rejected
  Coverage: 95% (rules are calibrated to your codebase)
```

**Health indicators:**
- **Proposals > 5 open** → Review them soon
- **>20% rejected** → Proposals are low quality; check data quality
- **0 proposals in 4 weeks** → Dream phase may be disabled or data threshold not met

---

## See Also

- **[Customization](Customization)** — Manual rule updates
- **[Gate Verdicts Explained](Gate-Verdicts-Explained)** — Understanding FAIL verdicts that feed dream phase
- **[Governance Rules](Governance-Rules)** — Full rule reference

---

*The dream phase is the framework learning from your codebase. Over 6 months, it becomes tailored to your patterns, not generic best practice.*