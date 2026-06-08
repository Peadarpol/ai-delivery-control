# AI Delivery Control — Engineer's Map Improvement Plan (v2)
**Revised**: Post-review by Claude Code assessment, 2026-06-07
**Source analysis**: Capability Inventory v1.2.0.1 + Comprehensive Improvement Backlog + The Engineer's Map Field Edition (Harish Kumar, 2026)
**Delivery mode**: Primarily documentation — markdown files, config templates, workflow files.
Items 2, 3, and 8 include config stubs that require companion code tickets before they
have operational effect. All factual claims in this revision have been verified against the assessment.

---

## Revision notes (what changed from v1)

**Item 10 — FM9-01 retracted**: The capability inventory snapshot (2026-06-02) did not
capture BUG-11, which fixed the `check_type` → `blocking_concern` field name mismatch
in `distill_dream.py` on the same day. The current code at `distill_dream.py:329` reads:
```python
check_type = log.get("blocking_concern", log.get("check_type", "review_failure"))
```
FM9-01 is resolved. The "IMMEDIATE — HIGHEST PRIORITY" designation in v1 was wrong.
Item 10 has been revised to remove FM9-01 and reframe as a quarterly sweep process.

**Item 2 — Reclassified**: Per-capability AT9 weights are not documentation-only.
A `capability_calibration` config block that no code reads is governance theatre.
Item 2 is now explicitly a design specification + code ticket, not a config drop.

**Item 5 — Scoped down**: State machine contracts are convention documentation
without enforcement. Valuable as a reference, not as a governance mechanism.
The item is retained but its value claim is restated accurately.

**Items 1, 4, 6, 9 — Confirmed accurate**: The assessment validated these.
No material changes to their content.

**Items 3 and 8 — Reclassified**: Dream proposal staleness and log file size bounds
both follow the same structural pattern as the original Item 2 — config keys without
code to read them. Both are now classified as "design-ahead-of-code" with explicit
stub comments in the config blocks and companion backlog entries (HIB-HEALTH-01,
HIB-HEALTH-02) for the code implementation. The `docs/harness-health.md` sections
note that the checks are not operational until those items ship.

**Items 7 — Confirmed as visibility improvement**: Concurrency model config key
and architecture doc. No code reads `concurrency_model` yet; the key is a
declaration of intent, accurately framed as such.

---

## How to read this plan

Each item follows the same structure:
- **Engineer's Map source** — which AT/FM/Thread/Archetype observation motivated it
- **Problem statement** — what is currently wrong or missing, verified against live code
- **Delivery classification** — Documentation-only / Design + code ticket / Visibility
- **Files to change** — exact paths, what to add/change in each
- **Acceptance criteria** — how to verify the change is complete

Items are grouped by delivery wave at the end. Wave 1 (Items 1, 4) are the
highest-value documentation changes. Wave 2 (Item 6, Item 9) are architectural
additions. Waves 3–5 are supporting visibility and reference material.

---

## Item 1 — Decision Block Format in Gate System Prompt
**Engineer's Map source**: Chapter 6 §6.4 "Two Structures Worth Memorising"
**Delivery classification**: Documentation-only — extends `review_context_universal.md`
**Assessment verdict**: Confirmed genuine gap. The existing Decision Block section at
line 146 of `review_context_universal.md` is an ADVISORY for ADR authoring by agents.
It does not instruct the gate to use structured output for its own FAIL findings.
This is a real addition, not a duplicate.

### Problem
The gate's system prompt produces findings as prose judgements. The AT/FM vocabulary
(added T1-G-12) is present in context but not activated as an output constraint on
finding structure. A FAIL finding that cannot name its AT tradeoff and its FM risk
is not a finding — it is a suspicion. The decision block format closes this gap.

### Files to change

#### 1a. `review_context_universal.md`
Locate the existing Decision Block section (around line 146). That section instructs
agents writing ADRs to use the decision block. **Add a new, separate section** after
the AT/FM vocabulary tables titled `## Gate Finding Output Format`. Do not modify
the existing Decision Block section. Content:

```markdown
## Gate Finding Output Format

Every FAIL and WARN finding in the gate verdict must use the decision block format.
A finding that cannot be expressed in this format is not a finding — it is a
suspicion. Return suspicions as questions to the developer, not as blocking concerns.

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
  Correct:   "AT1 — this code chose availability; the cache write precedes the
              database commit, so a crash between the two leaves the cache holding
              a value the database will never confirm"
- The Exposes line names a specific risk in this codebase, not the generic FM
  definition. FM10 and FM4 findings at FAIL severity must include file:line.
- The Remediation addresses the FM. "Delete this" is not a remediation.
- For PASS_FAST and PASS verdicts, the decision block is not required.
- For WARN verdicts, the decision block is required when the concern touches
  FM4, FM9, FM10, or FM12. For other concerns at WARN level, it is encouraged.
```

#### 1b. `AGENTS.md` or `AGENTS_PROJECT.md`
In the gate guidance section (§8 or equivalent), add a subsection
`### Reading Gate Findings`:

```markdown
### Reading Gate Findings

From v1.3.3, gate FAIL and qualifying WARN findings use the decision block format:

- **Finding** — what the code does (not a judgment)
- **Tradeoff** — which AT tradeoff is being violated and in which direction
- **Exposes** — which FM failure mode this creates, with file:line for FM4/FM10
- **Remediation** — the specific change that resolves the FM

When contesting a finding via the rebuttal protocol (§8.6), address the **Exposes**
line specifically. A rebuttal that does not explain why the named FM does not apply
to this specific file and context will be rejected. Asserting that the code is
"intended behaviour" without explaining why the FM risk is not present is not
sufficient — the reviewing model already assumed the code is intentional.
```

#### 1c. `FRAMEWORK_ROADMAP.md`
Add to the v1.3.3 delivered items:
```
- T1-G-12 extension: Gate finding output now requires decision block format
  (Finding / Tradeoff / Exposes / Remediation) for FAIL and qualifying WARN
  findings. AT/FM codes function as output constraints, not only as vocabulary.
```

### Acceptance criteria
- `review_context_universal.md` contains a `## Gate Finding Output Format` section
  that is distinct from the existing Decision Block section at line 146
- AGENTS.md contains `### Reading Gate Findings` with decision block field descriptions
- FRAMEWORK_ROADMAP.md records the extension under v1.3.3

---

## Item 2 — Per-Capability AT9 Weights
**Engineer's Map source**: AT9 (Correctness vs Performance) — asymmetric cost of
wrong answers across capability domains
**Delivery classification**: Design specification + code ticket (NOT documentation-only)
**Assessment verdict**: The v1 plan misclassified this as documentation-only. A
`capability_calibration` config block that `ai_review.py` never reads produces no
governance effect. This item creates the design spec and a companion backlog entry
for the code implementation.

### Problem
The gate applies identical correctness/false-negative tolerance to all capability
domains. A missed `BRANCH_ISOLATION` finding (FM10 risk — cross-tenant data access)
carries the same weight as a missed `TEST_COVERAGE` finding. The rebuttal-rate data
by domain is tracked (T1-G-07) but never fed back to calibrate per-domain thresholds.

### Files to change

#### 2a. `docs/architecture/capability-calibration-design.md` (create)

```markdown
# Capability Calibration — Design Specification

## Status
DESIGN — not yet implemented. Code implementation required (see backlog item T1-G-14).
This document defines the configuration schema and the expected code behaviour.
Do not add the config block to config.yaml until the code implementation is delivered —
a config key that no code reads is governance theatre.

## Problem (AT9)

AT9 (Correctness vs Performance) is a dial, not a binary. The optimal position
on this dial differs by capability domain:

| Domain | FM risk | Cost of false negative | Cost of false positive |
|--------|---------|----------------------|----------------------|
| BRANCH_ISOLATION | FM10 — cross-tenant data access | Catastrophic (data breach) | Developer friction |
| TRANSACTIONAL_INTEGRITY | FM4 — data consistency failure | High (silent corruption) | Developer friction |
| MASS_ASSIGNMENT | FM10 — privilege escalation | Catastrophic | Developer friction |
| MIGRATIONS | FM8 — schema contract violation | High (hard to reverse) | Developer friction |
| CLEAN_ARCH | FM2 — coupling degrades slowly | Medium | Developer friction |
| TEST_COVERAGE | Advisory | Low | Trust erosion |

Currently all domains sit at the same AT9 position. This is the wrong trade for
FM10 and FM4 domains where the cost of a false negative is categorically higher.

## Proposed config schema

```yaml
# Add to .agent/config.yaml AFTER code implementation is delivered
capability_calibration:
  default_correctness_weight: 0.75
  overrides:
    BRANCH_ISOLATION: 0.95
    TRANSACTIONAL_INTEGRITY: 0.90
    MASS_ASSIGNMENT: 0.90
    RBAC: 0.90
    MIGRATIONS: 0.85
    CLEAN_ARCH: 0.70
    TEST_COVERAGE: 0.65
```

## Required code behaviour (for T1-G-14 implementation)

1. `ai_review.py` reads `capability_calibration` from `.agent/config.yaml` at startup
2. When building `RouteDecision`, the weight for each active capability is read from
   the calibration config
3. The weight is injected into the gate system prompt as a policy note:
   "BRANCH_ISOLATION weight: 0.95 — treat borderline findings as FAIL, not WARN"
4. The weight is included in the `route_decision.policy_notes` field of `ReviewVerdict`
   so it appears in the terminal output (T1-G-04 ✅) and in `.ai-review-log.jsonl`

## Calibration data source

The rebuttal rate by domain is the primary calibration signal. Until T1-D-02
(cross-project health report) delivers a `--rebuttal-by-domain` flag, manually:
```bash
grep '"rebuttal_type"' .ai-review-log.jsonl | python3 -c "
import sys, json, collections
counts = collections.Counter()
for line in sys.stdin:
    try:
        r = json.loads(line)
        concern = r.get('blocking_concern', 'unknown')
        counts[concern] += 1
    except: pass
for k,v in counts.most_common(): print(f'{v:4d}  {k}')
"
```
A domain with rebuttal rate > 0.30 is over-calibrated (correctness_weight too high).
Reduce by 0.05–0.10 and monitor for one sprint before reducing further.

## AT9 decision recorded

Decision: Per-domain correctness weights injected into gate policy notes.
Tradeoff: AT9 — choosing domain-specific correctness calibration over uniform
performance; higher-risk domains accept more false positives to minimise false negatives.
Exposes: FM11 — if weights are set incorrectly and never reviewed, the gate silently
over- or under-flags a domain without any observable signal.
Mitigation: Quarterly rebuttal-rate review per domain; harness_health.py to surface
domains with rebuttal rate > 0.30 as a calibration WARN.
```

#### 2b. Main backlog — add T1-G-14
In the `### T1-G: AI Review Gate Intelligence` section:

```markdown
| T1-G-14 | **Per-capability AT9 calibration weights** | Design spec at `docs/architecture/capability-calibration-design.md`. `ai_review.py` reads `capability_calibration.overrides` from config and injects domain weights as policy notes in `RouteDecision`. Borderline findings in high-weight domains are elevated from WARN to FAIL; low-weight domains have the inverse applied. Calibration data source: rebuttal rate by domain from `.ai-review-log.jsonl`. `harness_health.py` surfaces domains with rebuttal rate > 0.30 as a calibration WARN. Config block must NOT be added to `config.yaml` until this code is delivered. Dependency: T1-G-01 ✅, T1-G-03 ✅. | Medium | ⬜ v1.4.0 |
```

### Acceptance criteria
- `docs/architecture/capability-calibration-design.md` exists with the schema,
  required code behaviour, and AT9 decision block
- The document explicitly states config must not be added until code is delivered
- T1-G-14 is in the backlog under T1-G series
- `config.yaml` template is NOT modified by this item

---

## Item 3 — Dream Proposals Staleness in harness_health.py
**Engineer's Map source**: AT7 (Automation vs Control) / FM11 (Observability Blindness)
**Delivery classification**: Design-ahead-of-code — documentation + config stubs.
`harness_health.py` requires a companion code implementation (T1-C-03 extension,
see backlog entry below) to actually read these config keys and emit signals.
The config block added here is a stub; it does nothing until the code ships.
**Assessment verdict**: Legitimate visibility addition once code is delivered.
Config stubs are design documentation, not operational health checks.

### Problem
Dream proposals accumulate in `.agent/state/dream_proposals/` without any signal
that the human review step has not occurred. The AT7 loop is incomplete: automation
generates proposals, but there is no feedback mechanism when the control step lapses.

### Files to change

#### 3a. `docs/harness-health.md` (add section, or create if absent)

```markdown
### Dream Proposal Staleness

The health check monitors `__open.md` files in `.agent/state/dream_proposals/`
for age. An aging proposal signals that the AT7 control step (human review) has
not occurred.

**What it checks**: Reads the `Generated:` frontmatter field from each `__open.md`
file and computes age in days relative to today.

**Thresholds** (configurable in `.agent/config.yaml`):
- `staleness_warn_days` (default: 30) — WARN signal in health report
- `staleness_critical_days` (default: 90) — DEGRADING signal in health report
- `max_open_proposals` (default: 10) — DEGRADING if count exceeds this

**Interpreting the signal**:
- 1–3 open proposals with recent dates: healthy active improvement cycle
- Any proposal > 30 days old: monthly review cadence has lapsed
- Any proposal > 90 days old: likely stale; the pattern that generated it may no
  longer apply. Consider rejecting with a note rather than acting on it.

**Monthly cadence**: Before the dream phase runs its next cycle, run
`harness_health.py --dream-proposals` and close out stale proposals. An unreviewed
proposal is updated with new evidence by the next dream phase run — old stale
proposals accumulate evidence from sessions where the pattern may no longer apply.

**Scope note**: This check improves visibility. It does not prevent proposals from
accumulating — that requires T1-I-06 (retention policy, undelivered).
```

#### 3b. `.agent/config.yaml` template
Add under a `dream_proposals` key. Add the inline comment — it is the guard
against Gemini or a future reader treating these as operational:

```yaml
dream_proposals:
  # These thresholds are read by harness_health.py --dream-proposals.
  # Code implementation required before these keys have any effect.
  # Tracked as HIB-HEALTH-01. Until delivered, values here are design stubs.
  staleness_warn_days: 30
  staleness_critical_days: 90
  max_open_proposals: 10
```

#### 3c. Main backlog — add HIB-HEALTH-01

```markdown
| HIB-HEALTH-01 | **harness_health.py: dream proposal staleness check** | Implement `--dream-proposals` flag in `harness_health.py`. Reads `dream_proposals.staleness_warn_days`, `staleness_critical_days`, `max_open_proposals` from config. For each `__open.md` in `.agent/state/dream_proposals/`, reads `Generated:` frontmatter field, computes age in days, emits WARN or DEGRADING signal. Companion to the config stubs added in Item 3 of the Engineer's Map improvement plan. Low effort — stdlib only (pathlib, datetime). | Low | ⬜ v1.3.4 |
```

### Acceptance criteria
- `docs/harness-health.md` contains the Dream Proposal Staleness section with
  explicit note that the check requires HIB-HEALTH-01 code implementation
- Config template contains the three staleness keys **with the stub comment**
- HIB-HEALTH-01 is in the backlog

---

## Item 4 — State File Schema Reference Document
**Engineer's Map source**: FM8 (Schema/Contract Violation) / T7 (State Machines)
**Delivery classification**: Documentation-only — new reference document
**Assessment verdict**: Confirmed genuine gap. `docs/state-file-schema.md` does not
exist. The `harness_version: "2.0"` hardcode at `init_session.py:251` is confirmed
in live code and is a genuine FM8 instance.

### Problem
The framework has no authoritative schema reference for its own state files. Writers
and readers can drift apart silently (FM8). Known instances include the hardcoded
`harness_version` field and the UTC/local timestamp inconsistency between files.
Schema changes have no documented protocol, so contributors cannot know whether
their change is additive (safe) or breaking (requires migration).

### Files to change

#### 4a. `docs/state-file-schema.md` (create)

```markdown
# AI Delivery Control — State File Schema Reference

**Purpose**: Authoritative schema for every state file written by the framework.
Updated with every release that changes a schema field.
This is the FM8 (Schema/Contract Violation) defence for the framework's own data layer.

## Schema versioning convention

Every structured record MUST contain a `schema_version` field (`"MAJOR.MINOR"`).
MAJOR: breaking changes (field removal, type change, semantic rename).
MINOR: additive changes (new optional field).

Readers MUST check `schema_version` before parsing. Unknown higher versions:
parse only known fields, log a warning. Do NOT silently discard unknown-version records.

## Current schema versions

| File | Current version | Known issues |
|------|----------------|--------------|
| `harness_events.jsonl` | `1.0` | Severity casing inconsistent — see FM8-01 |
| `.ai-review-log.jsonl` | `1.1` | Timestamp uses local time, not UTC — see FM8-04 |
| `session_ledger.jsonl` | `1.0` | `harness_version` hardcoded `"2.0"` — see FM8-02; date uses local time — see FM8-03 |
| `session.json` | `1.0` | — |

---

## harness_events.jsonl — schema v1.0

**Writers**: `ai_review.py`, `check_halt.py`, `init_session.py`, `check_spec.py`
**Readers**: `init_session.py` (session inference), `distill_dream.py` (pattern input),
`harness_health.py` (verdict distribution)

Required fields (all records):
- `schema_version`: `"1.0"`
- `event_type`: string — see Event Type Registry below
- `timestamp_utc`: ISO 8601 UTC with trailing `Z`
- `session_id`: string (UUID v4) or `null`
- `agent`: string
- `severity`: `"INFO"` | `"WARNING"` | `"HIGH"` | `"ERROR"` | `"CRITICAL"` (all caps)
- `payload`: object (schema varies by event_type)

Optional: `commit_sha` (string or `null`)

**Known issue FM8-01**: `init_session.py` heartbeat writes `"info"` (lowercase).
`distill_dream.py` reads `evt.get("severity") == "critical"` — uppercase `"CRITICAL"`
events from `ai_review.py` are invisible to the dream phase bypass trigger.
Tracked as HIB-FM8-01. Until fixed, the dream phase bypass on critical events
does not fire for `ai_review.py`-sourced events.

### Event Type Registry

| event_type | Writer | payload fields |
|------------|--------|----------------|
| `commit_made` | `init_session.py --post-commit` | `branch`, `files_changed` |
| `halt_bypass` | `check_halt.py` | `bypass_reason`, `session_id` |
| `high_risk_gate_closed` | `ai_review.py` | `capability`, `file_path` |
| `high_risk_gate_override` | `ai_review.py` | `capability`, `skip_reason` |
| `gate_bypass` | `ai_review.py` | `rebuttal_type`, `finding_ids`, `evidence` |
| `spec_quality_check` | `check_spec.py` | `spec_id`, `verdict`, `clarity_score` |
| `state_anomaly` | convention (not yet implemented) | `file`, `field`, `found_value` |

---

## .ai-review-log.jsonl — schema v1.1

**Writers**: `ai_review.py` (all verdicts including rebuttal outcomes)
**Readers**: `init_session.py` (token aggregation), `distill_dream.py` (FAIL patterns),
`harness_health.py` (verdict distribution, rebuttal metrics)

Required fields:
- `schema_version`: `"1.1"`
- `timestamp`: ISO 8601 **local time** (not UTC — see FM8-04)
- `verdict`: `"PASS"` | `"WARN"` | `"FAIL"` | `"FAIL_OPEN"` | `"PASS_FAST"` |
  `"REBUTTAL_ACCEPTED"` | `"REBUTTAL_REJECTED"`
- `model`: string
- `verdict_tier`: `"cloud"` | `"local"` | `"preflight"`
- `provider`: string (added v1.1.5)
- `session_id`: string or `null`

Optional (populated on FAIL/WARN):
- `blocking_concern`: string — the specific capability that failed (e.g. `"BRANCH_ISOLATION"`)
- `issues`: array of `{severity, concern, location, description, remediation}`
- `route_decision`: serialised RouteDecision
- `token_usage`: dict
- `context_snapshot`: string

Rebuttal records additionally require:
- `strategy`: `"rebuttal"`
- `rebuttal_actor`, `rebuttal_type`, `normalized_diff_hash`, `findings_count`, `accepted_count`

**Known issue FM8-04**: `timestamp` uses local time. `harness_events.jsonl` uses UTC.
Cross-referencing the two logs by time requires timezone-aware comparison.
Standardisation to UTC deferred to T1-I-06 (retention policy).

---

## session_ledger.jsonl — schema v1.0

**Writer**: `init_session.py`
**Readers**: `init_session.py` (dream phase threshold check), `distill_dream.py`
(session outcomes for escalation rate)

Required fields:
- `schema_version`: `"1.0"`
- `session_id`: UUID v4
- `date`: `"YYYY-MM-DD HH:MM"` **local time** (see FM8-03)
- `action`: string
- `startup_checked`: boolean
- `agent`: string
- `outcome`: `"success"` | `"partial"` | `"abandoned"` | `"escalated"`
- `outcome_source`: `"inferred"` | `"agent_override"` | `"human_override"`
- `outcome_note`: string
- `harness_version`: string (see FM8-02)
- `token_usage`: object

**Known issue FM8-02**: `harness_version` is hardcoded `"2.0"` at
`init_session.py:251` regardless of the actual installed version. Forensic
"which harness version ran this session?" analysis cannot be trusted.
Fix: read from `harness_version.txt` at write time (T1-B-02, undelivered).
Tracked as HIB-FM8-02.

**Known issue FM8-03**: `date` uses local time. `harness_events.jsonl` uses UTC.
Same cross-reference problem as FM8-04.

---

## session.json — schema v1.0

**Writer**: `init_session.py` (create and close), `check_spec.py` (token_usage increment)
**Readers**: `check_halt.py`, `ai_review.py`, `check_spec.py`, `distill_dream.py`

Fields: `session_id` (UUID v4), `start_time` (ISO 8601 UTC), `last_activity` (ISO 8601 UTC),
`status` (`"ACTIVE"` | `"COMPLETED"`), `agent` (string), `task_magnitude`
(`"micro"` | `"standard"` | `"major"`), `task_magnitude_source` (`"auto"` | `"agent_override"`),
`token_usage` (dict with 8 integer fields), `outcome_override` (optional string),
`outcome_override_source` (optional string), `outcome_override_note` (optional string)

Planned additions (T1-N-01, undelivered): `parent_session_id`, `agent_role`

---

## Schema evolution protocol

When changing any schema field:
1. Update this document with new version number and changed fields
2. Update the writer to emit the new `schema_version`
3. Add a migration entry to `bootstrap/migrations/` if existing records need patching
4. Update `bootstrap/validate.py` if the new field is required for gate operation
5. MINOR for additive changes; MAJOR for breaking (removal, type change, semantic rename)

FM8 test before any change: "If a reader built for the old schema reads a record
written with the new schema, what breaks?" Nothing → MINOR. Misparse or silent
ignore → MAJOR with mandatory migration module.

---

## Known FM8/FM9 instances

| ID | Type | Location | Description | Status |
|----|------|----------|-------------|--------|
| FM8-01 | FM8 | `harness_events.jsonl` severity | Mixed casing: `"CRITICAL"` (ai_review.py) vs `"info"` (init_session.py). Dream phase bypass trigger misses uppercase events. | ⬜ HIB-FM8-01 |
| FM8-02 | FM9 | `session_ledger.jsonl` harness_version | Hardcoded `"2.0"` at init_session.py:251. Version forensics unreliable. | ⬜ HIB-FM8-02 |
| FM8-03 | FM8 | `session_ledger.jsonl` date | Local time vs UTC. Cross-file time correlation requires TZ awareness. | ⬜ T1-I-06 scope |
| FM8-04 | FM8 | `.ai-review-log.jsonl` timestamp | Local time vs UTC. Same cross-reference problem. | ⬜ T1-I-06 scope |
| ~~FM9-01~~ | ~~FM9~~ | ~~distill_dream.py check_type~~ | ~~Field name mismatch~~ | ✅ Fixed BUG-11 |

Note: FM9-01 was listed as unresolved in the initial Engineer's Map analysis.
It was fixed as BUG-11 on 2026-06-02. The current code uses:
`log.get("blocking_concern", log.get("check_type", "review_failure"))`.
The initial analysis was based on a capability inventory snapshot taken the same
day as the fix and did not capture it.
```

#### 4b. `CONTRIBUTING.md`
Add to the section on changing framework internals:

```markdown
### Schema changes

If your contribution writes new fields to any state file or changes the type or
semantics of an existing field:
1. Update `docs/state-file-schema.md` with the new version number
2. MINOR for additive, MAJOR for breaking
3. Add a migration module to `bootstrap/migrations/` for MAJOR changes

This is the FM8 (Schema/Contract Violation) defence for the framework's own data.
Undocumented schema changes silently break `distill_dream.py`, `harness_health.py`,
and any external tooling reading these files.

FM8/FM9 checklist for new state file writes:
- Field names match exactly what existing readers expect (check `docs/state-file-schema.md`)
- Severity values use uppercase: `"INFO"`, `"WARNING"`, `"HIGH"`, `"ERROR"`, `"CRITICAL"`
- New timestamp fields use UTC (not local time)
- Nullable fields use `record.get("field")` on the reader side, not `record["field"]`
```

#### 4c. Main backlog — add HIB items

In the HIB/bug fix section:
```markdown
| HIB-FM8-01 | **Severity casing normalisation** | `init_session.py` heartbeat writes `"info"` (lowercase); all other writers use uppercase. `distill_dream.py` reads `evt.get("severity") == "critical"` — uppercase `"CRITICAL"` from `ai_review.py` is invisible to the dream phase bypass trigger. Fix: (1) uppercase in `init_session.py` heartbeat; (2) case-insensitive comparison in `distill_dream.py` dream phase bypass check. One-line fixes in two files. | Low | ⬜ v1.3.4 |
| HIB-FM8-02 | **Fix hardcoded `harness_version: "2.0"` in session_ledger** | `init_session.py:251` hardcodes `"2.0"`. Fix: read from `harness_version.txt` at write time (same mechanism T1-B-02 will formalise). One-line fix. | Low | ⬜ v1.3.4 |
```

### Acceptance criteria
- `docs/state-file-schema.md` exists with schemas for all four state files
- Known issues are documented with backlog references
- FM9-01 is shown as ✅ Fixed with a note explaining the initial analysis error
- `CONTRIBUTING.md` contains the schema change protocol and FM8/FM9 checklist
- HIB-FM8-01 and HIB-FM8-02 are in the backlog

---

## Item 5 — State Machine Contracts
**Engineer's Map source**: T7 (State Machines) — framework lifecycle objects are
informal state machines
**Delivery classification**: Convention documentation — reference value, no enforcement added
**Assessment verdict**: The assessment is correct that this adds no enforcement. The
value is as a reference document for contributors and for incident recovery. Framed
accurately here as a reference, not a governance mechanism.

### Problem
Session status, spec status, dream proposal lifecycle, and rebuttal state are state
machines implemented informally. When an object is found in an unexpected state
(session.json status absent, spec at APPROVED with [Pending] assumptions), there is
no documented recovery protocol. Contributors adding new state transitions have no
canonical reference.

### Files to change

#### 5a. `docs/state-machine-contracts.md` (create)

```markdown
# AI Delivery Control — State Machine Contracts

**Scope note**: This document is a reference for contributors and incident recovery.
It describes valid state transitions. It does not add enforcement — that requires
code changes (not in scope for this document). Convention-based governance degrades
under pressure; treat this as a map of intent, not a safety net.

## Session status (`session.json` → `status` field)

States: `ACTIVE`, `COMPLETED`

Valid transitions:
- (absent) → `ACTIVE`: `init_session.py main()` on first-ever session
- `ACTIVE` → `COMPLETED`: `init_session.py infer_and_close_previous_session()`

Invalid: `ACTIVE` → `ACTIVE` without closing prior session. If encountered:
log `state_anomaly` to `harness_events.jsonl`, treat as first-ever session.

Recovery: If `session.json` has absent or unknown status, skip infer/close,
log `state_anomaly`, proceed with fresh session initialisation.

FM4 risk: Crash between `COMPLETED` write and `session_ledger.jsonl` append
leaves session closed with no ledger entry. `infer_and_close_previous_session()`
handles by checking the ledger for session_id before writing.

## Spec status (`**Status**:` field in SPEC-XXX.md)

States: `DRAFT`, `APPROVED`, `SUPERSEDED`

Valid transitions:
- (new spec) → `DRAFT`: `/ba` workflow Phase 4
- `DRAFT` → `APPROVED`: human sets status after all `[Pending]` assumptions resolved.
  `check_spec.py` Pass 1 validates and blocks if `[Pending]` entries remain.
- `APPROVED` → `SUPERSEDED`: manual, when a newer spec for the same feature is approved
- `DRAFT` → `SUPERSEDED`: manual, when a spec is abandoned

Automated guard: `check_spec.py` only. All other transitions are convention.

FM4 risk: Two specs can both be `APPROVED` for overlapping features.
Mitigation: T1-L-01a (Jaccard similarity check, undelivered).

## Dream proposal lifecycle (filename suffix convention)

States: `__open.md`, `__contradiction.md`, `__reviewed.md`

Valid transitions:
- (pattern above threshold) → `__open.md`: `distill_dream.py`
- (contradiction detected) → `__contradiction.md`: `distill_dream.py` before write
- `__open.md` → `__reviewed.md`: human renames after accept/reject decision
- `__contradiction.md` → `__reviewed.md`: human resolves, renames
- `__open.md` → `__open.md` (update): `distill_dream.py` appends evidence to existing

No automated guard on any transition. The decision step is purely human.
Staleness signal: `harness_health.py` dream proposal staleness check (Item 3).

## Rebuttal lifecycle

States: `pending` (`.agent/state/gate_rebuttal.json`), `accepted`, `rejected`
(both recorded in `.ai-review-log.jsonl`)

Valid transitions:
- Agent writes rebuttal → `pending`
- `ai_review.py --rebuttal` second LLM call → `accepted` or `rejected`

Convention: rebuttals should not be retried more than twice. A third rejection
signals a real finding; use `SKIP_AI_REVIEW=1` with structured SKIP_REASON
(T1-G-07) as the last resort, not a third rebuttal attempt.
```

#### 5b. `governance.md`
Add one sentence to the "Mandatory pre-task checks" section:

```markdown
State machine reference: `docs/state-machine-contracts.md` documents valid
transitions for session status, spec status, dream proposals, and rebuttals.
If you encounter an object in an undocumented state, log it to
`harness_events.jsonl` as `event_type: "state_anomaly"` before proceeding.
```

### Acceptance criteria
- `docs/state-machine-contracts.md` exists with all four state machines documented
- The scope note accurately describes this as reference documentation without enforcement
- FM4 risks are named for each state machine
- `governance.md` references the document

---

## Item 6 — GateContext Design Specification
**Engineer's Map source**: AT8 (Coupling vs Cohesion) — pre-commit chain components
operate independently on the same diff; findings are not shared
**Delivery classification**: Design specification — architecture doc + backlog entry.
Implementation deferred to v1.4.0.
**Assessment verdict**: Confirmed architecturally substantial. Real problem: `architecture_checks.py`
findings are never seen by `ai_review.py`. GateContext design is coherent and
aligns with roadmap direction.

### Problem
The pre-commit chain runs `architecture_checks.py`, `repo_map.py`, `co_change_check.py`,
and `ai_review.py` independently on the same diff. Architecture check findings
(deterministic, typed) are printed to the terminal and discarded. The LLM reviewer
re-derives what the static analysis already found, probabilistically. A diff that
fails architecture checks AND triggers a gate FAIL produces two unrelated findings
with no shared context.

### Files to change

#### 6a. `docs/architecture/gate-context-design.md` (create)

```markdown
# GateContext — Design Specification

**Status**: DESIGN — not yet implemented. Target: v1.4.0.
**Backlog**: T1-G-13

## Problem (AT8)

The pre-commit hook chain currently operates as four independent processes:

1. `architecture_checks.py` — AST boundary check; findings exit to stdout only
2. `repo_map.py` — PageRank computation; returns scores dict per call
3. `co_change_check.py` — blast radius; injects HIGH-confidence warnings
4. `ai_review.py` — reads diff, calls all three above independently, calls LLM

The AI review gate re-derives what architecture checks already computed.
Architecture check findings (deterministic) are invisible to the LLM reviewer.
This is AT8 taken too far toward decoupling: the components are independent,
but they lack cohesion around the shared artifact (the diff).

## Proposed design

A `GateContext` Pydantic model passed through the pre-commit chain via a
tempfile at `.agent/state/gate_context_current.json` (gitignored).
Each component reads the context, adds its findings, writes it back.
`ai_review.py` reads the fully-populated context before its LLM call.

Conceptual schema:
```python
class GateContext(BaseModel):
    diff_text: str
    diff_hash: str                          # for rebuttal matching
    changed_files: List[str]
    session_id: Optional[str]

    # Populated by architecture_checks.py
    arch_violations: List[ArchViolation] = []   # {file, line, rule, severity}
    adr_domains: List[str] = []                  # from # ADR: annotations

    # Populated by repo_map.py
    pagerank_scores: Dict[str, float] = {}
    review_intensity: Literal["standard","elevated","critical"] = "standard"
    repo_map_text: str = ""

    # Populated by co_change_check.py
    co_change_warnings: List[CoChangeWarning] = []   # {file, confidence, reason}

    # Populated and read by ai_review.py
    route_decision: Optional[RouteDecision] = None
    verdict: Optional[ReviewVerdict] = None
```

## Gate system prompt integration

With `GateContext` populated before the LLM call, the prompt gains a
`## Deterministic findings` section:

```
## Deterministic findings (pre-LLM, verified)
Architecture violations:
  {for each arch_violation: file:line — rule — severity}

Co-change warnings (HIGH confidence):
  {for each warning: file — blast-radius-partner — reason}

Review intensity: {review_intensity}
```

The LLM reviewer sees typed, located findings from static analysis and can
incorporate them into decision block format (Item 1) rather than re-deriving
them probabilistically. A finding that matches an architecture violation
becomes FM8-confirmed; one that doesn't requires the LLM to justify it
independently.

## Degradation contract

Each component MUST degrade gracefully if `GateContext` is absent or malformed:
- Fall back to current standalone behaviour
- Log a `state_anomaly` to `harness_events.jsonl` if the context file exists
  but fails validation

`GateContext` is an enhancement, not a hard dependency. The chain must
function without it (supports gradual rollout and air-gapped environments
where the tempfile path may be restricted).

## AT8 decision

Decision: Introduce `GateContext` as a shared artifact through the pre-commit chain.
Tradeoff: AT8 — choosing cohesion (shared findings object) over maximum decoupling.
Exposes: FM2 — if `GateContext` serialisation fails, it could cascade if degradation
contract is not honoured by all components.
Mitigation: Degradation contract above. Each component treats absent context as
normal standalone operation.

## Prerequisite for

- T1-G-11 (evidence-gathering pre-context) — pytest and TODO/FIXME signals are
  natural GateContext fields
- T1-G-09 (rigor profiles) — `lean` profile skips co_change and repo_map population;
  `exhaustive` populates all fields
- T1-K-06 (blocked_commands scan) — deterministic scan result belongs in GateContext
  alongside arch_violations
```

#### 6b. Main backlog — add T1-G-13

```markdown
| T1-G-13 | **GateContext shared object for pre-commit chain** | Design spec at `docs/architecture/gate-context-design.md`. Typed `GateContext` Pydantic model passed through the pre-commit chain via `.agent/state/gate_context_current.json`. Architecture violations, PageRank scores, co-change warnings, and ADR domains are written by their respective components and read by `ai_review.py` before the LLM call. Gate system prompt gains a `## Deterministic findings` section. Each component degrades gracefully to standalone behaviour if context is absent. Prerequisite for T1-G-11, T1-G-09, T1-K-06. Implementation target v1.4.0. | Medium | ⬜ v1.4.0 |
```

#### 6c. `FRAMEWORK_ROADMAP.md`
Add T1-G-13 to the v1.4.0 planned items with a one-line description.

### Acceptance criteria
- `docs/architecture/gate-context-design.md` exists with schema, system prompt integration,
  degradation contract, and AT8 decision in decision block format
- T1-G-13 is in the backlog
- `FRAMEWORK_ROADMAP.md` references T1-G-13 in v1.4.0

---

## Item 7 — Concurrency Model Config Key
**Engineer's Map source**: AT5 (Centralisation vs Distribution)
**Delivery classification**: Visibility improvement — config + documentation
**Assessment verdict**: Legitimate. The AT5 position is implicit and undeclared.
T1-N-02 delivered partial locking; the config key makes the coverage gaps visible.

### Files to change

#### 7a. `.agent/config.yaml` template

```yaml
# Concurrency model — AT5 (Centralisation vs Distribution)
# single_agent (default): one agent, one machine. Background subprocesses
#   (wiki_compile.py, distill_dream.py) are the only concurrent writes.
#   File locking covers .ai-review-log.jsonl and harness_events.jsonl (T1-N-02 ✅).
#   session.json covered by _lock_session(). Other state files unlocked.
# concurrent_local: multiple terminal sessions on one machine. All .jsonl
#   state file writes should be locked. session_ledger.jsonl and dream proposals
#   not yet fully safe. Use with awareness of partial coverage.
# multi_agent: requires Tier 2 infrastructure (T2-A-01). Not implemented.
concurrency_model: single_agent
```

#### 7b. `docs/architecture/concurrency-model.md` (create)

```markdown
# Concurrency Model

AT5 decision: AI Delivery Control v1.x operates in `single_agent` mode.

Decision: Single agent, centralised state files.
Tradeoff: AT5 — choosing centralisation (one writer at a time per state file)
for simplicity, accepting no concurrent multi-agent distribution.
Exposes: FM4 — two simultaneous processes writing to an unlocked state file
can interleave or truncate records.
Mitigation: File locking on the two highest-frequency files (T1-N-02, v1.3.1).
session.json locked via `_lock_session()`. Remaining files protected by the
`single_agent` operational assumption.

## Lock coverage (as of v1.3.1)

| File | Locked | Safe for concurrent_local |
|------|--------|--------------------------|
| `.ai-review-log.jsonl` | ✅ `_lock_file` | Yes |
| `harness_events.jsonl` | ✅ `_lock_file` | Yes |
| `session.json` | ✅ `_lock_session` | Yes |
| `session_ledger.jsonl` | ❌ | No |
| `dream_proposals/*.md` | ❌ | No |
| `wiki_compile_state.json` | ❌ | Spawned as subprocess only |

## Roadmap

- v1.4.0: Full `concurrent_local` lock coverage (T1-N-02 completion)
- v2.0.0: Multi-agent via Tier 2 MCP server (T2-A-01)
```

#### 7c. `docs/configuration-reference.md`
Add section `### concurrency_model` with three-value explanation and lock
coverage table reference pointing to `docs/architecture/concurrency-model.md`.

### Acceptance criteria
- `config.yaml` template contains `concurrency_model` with inline comments
- `docs/architecture/concurrency-model.md` records the AT5 decision in decision block format
- `configuration-reference.md` explains all three values

---

## Item 8 — Log File Size Bounds in harness_health.py
**Engineer's Map source**: FM3 (Unbounded Resource Consumption)
**Delivery classification**: Design-ahead-of-code — documentation + config stubs.
`harness_health.py` requires a companion code implementation (HIB-HEALTH-02)
to actually read `health_checks.state_file_size.*` keys and emit signals.
The config block added here is a stub; it does nothing until the code ships.
**Assessment verdict**: Legitimate FM3 signal once code is delivered. The repo
graph cache (synchronous pre-commit path) is the highest-urgency instance.

### Files to change

#### 8a. `docs/harness-health.md`

```markdown
### State File Size Health

Framework state files grow without bounds until T1-I-06 (retention policy) ships.
`harness_health.py` monitors file sizes and surfaces FM3 risk before it affects
commit latency.

**What it monitors**:

| File | WARN | DEGRADING | Path impact |
|------|------|-----------|-------------|
| `.ai-review-log.jsonl` | 5 MB | 20 MB | Subprocess — low urgency |
| `harness_events.jsonl` | 5 MB | 20 MB | Subprocess — low urgency |
| `session_ledger.jsonl` | 1 MB | 5 MB | Synchronous at startup |
| `repo_graph_cache.json` | 2 MB | 10 MB | **Synchronous in pre-commit hot path — HIGH** |
| `dream_proposals/` (total) | 500 KB | 2 MB | Manual review overhead only |

**repo_graph_cache.json** is the most acute FM3 risk: it is read synchronously before
every gate LLM call. A 10 MB cache adds measurable latency to every commit.
Action when DEGRADING: `rm .agent/state/repo_graph_cache.json` — it rebuilds on
the next commit with no data loss. No TTL-based eviction exists (mtime-based only);
a stable large codebase that changes infrequently accumulates a growing cache.

**FM3 vs T1-I-06**: These checks are the FM11 (Observability) complement to
T1-I-06 (retention policy, undelivered). Until T1-I-06 ships, health checks
surface the problem; manual archival is the mitigation.
```

#### 8b. `.agent/config.yaml` template
Add the inline comment — same pattern as Item 3:

```yaml
health_checks:
  state_file_size:
    # These thresholds are read by harness_health.py file size checks.
    # Code implementation required before these keys have any effect.
    # Tracked as HIB-HEALTH-02. Until delivered, values here are design stubs.
    ai_review_log_warn_mb: 5
    ai_review_log_critical_mb: 20
    harness_events_warn_mb: 5
    harness_events_critical_mb: 20
    session_ledger_warn_mb: 1
    session_ledger_critical_mb: 5
    repo_graph_cache_warn_mb: 2
    repo_graph_cache_critical_mb: 10
```

#### 8c. Main backlog — add HIB-HEALTH-02

```markdown
| HIB-HEALTH-02 | **harness_health.py: state file size checks** | Implement file size monitoring in `harness_health.py`. Reads `health_checks.state_file_size.*` thresholds from config. For each monitored file, checks `os.path.getsize()` against warn/critical thresholds, emits WARN or DEGRADING signal. Priority: `repo_graph_cache.json` first (synchronous pre-commit path — FM3 most acute here). Companion to config stubs added in Item 8 of the Engineer's Map improvement plan. Low effort — stdlib only (os, pathlib). | Low | ⬜ v1.3.4 |
```

### Acceptance criteria
- `docs/harness-health.md` contains the size health section with explicit note
  that checks require HIB-HEALTH-02 code implementation
- Config template contains `health_checks.state_file_size` keys **with stub comment**
- HIB-HEALTH-02 is in the backlog
- The repo graph cache special case (synchronous path) is called out

---

## Item 9 — Archetype-Keyed Domain Starter Packs
**Engineer's Map source**: F6 (System Archetypes) / AT8 (Coupling vs Cohesion)
**Delivery classification**: Documentation-only — new content for the config gap
left by S0-24
**Assessment verdict**: Confirmed real gap. S0-24 moved DOMAIN_REGISTRY to config
but left no starter content. New non-GymBase installs get empty wiki pages.

### Files to change

#### 9a. `docs/archetypes/A3-marketplace-transaction.md` (create)

```markdown
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
```

#### 9b. `docs/archetypes/A2-social-communication.md` (create)

```markdown
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
```

#### 9c. `docs/archetypes/A6-platform-api.md` (create)

```markdown
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
```

#### 9d. `docs/getting-started.md`
Add section `### Choosing your domain registry`:

```markdown
### Choosing your domain registry

The domain registry in `.agent/config.yaml` determines which architectural domains
the wiki layer compiles and which the gate uses for ADR injection.

**Step 1**: Classify your system using Engineer's Map F6:
- A1 Search & Discovery, A2 Social & Communication, A3 Marketplace & Transaction,
  A4 Media Delivery, A5 Data Intelligence, A6 Platform & API

**Step 2**: Copy the starter registry from `docs/archetypes/A[N]-[name].md` into
your `.agent/config.yaml` under `domain_registry`.

**Step 3**: For each domain, either point `adr_paths` at an existing ADR file,
or leave `adr_paths: []`. An empty `adr_paths` generates a placeholder wiki page
with the domain's FM/AT context — enough for the gate to produce relevant findings
without requiring authored ADRs on day one.

**Step 4**: Copy the `## System Archetype` template section from the archetype file
into `review_context_project.md`. This tells the gate which FM domains to weight most
heavily for your system.

Most systems combine archetypes. Start with your primary; add secondary domain
entries as the gate surfaces findings in those areas.
```

### Acceptance criteria
- `docs/archetypes/` contains A2, A3, and A6 files
- Each file contains a `domain_registry` yaml block and a `review_context_project.md` template
- `docs/getting-started.md` contains the four-step selection process

---

## Item 10 — FM8/FM9 Boundary Sweep Protocol
**Engineer's Map source**: A5 + A6 archetype combination predicts FM8/FM9 as dominant
**Delivery classification**: Documentation — audit protocol + known instances table.
Companion backlog items for two remaining code fixes.
**Assessment correction**: FM9-01 (`check_type` field) was fixed as BUG-11 on 2026-06-02.
It is NOT an open issue. The initial analysis was based on the capability inventory
snapshot taken the same day as the fix.

### Files to change

#### 10a. `docs/architecture/fm8-fm9-boundary-audit.md` (create)

```markdown
# FM8/FM9 Boundary Audit

**Archetype context**: AI Delivery Control is A5 (Data Intelligence) + A6 (Platform & API).
Both archetypes predict FM8 (Schema/Contract Violation) and FM9 (Silent Data Corruption).
This document records known instances and the quarterly sweep protocol.

## Known instances

| ID | Type | Location | Description | Status |
|----|------|----------|-------------|--------|
| FM8-01 | FM8 | `harness_events.jsonl` severity | Mixed casing across writers — `ai_review.py` uppercase, `init_session.py` heartbeat lowercase `"info"`. Dream phase bypass reads lowercase only. | ⬜ HIB-FM8-01 |
| FM8-02 | FM9 | `session_ledger.jsonl` harness_version | Hardcoded `"2.0"` at init_session.py:251. | ⬜ HIB-FM8-02 |
| FM8-03 | FM8 | `session_ledger.jsonl` date | Local time vs UTC in harness_events.jsonl. | ⬜ T1-I-06 scope |
| FM8-04 | FM8 | `.ai-review-log.jsonl` timestamp | Local time vs UTC. | ⬜ T1-I-06 scope |
| ~~FM9-01~~ | — | `distill_dream.py` | `check_type` vs `blocking_concern` field mismatch | ✅ Fixed BUG-11 (2026-06-02) |

**FM9-01 retraction note**: The initial Engineer's Map analysis flagged this as
"IMMEDIATE — HIGHEST PRIORITY." The capability inventory snapshot (2026-06-02) did
not capture BUG-11, which was fixed the same day. The fix at `distill_dream.py:329`:
```python
check_type = log.get("blocking_concern", log.get("check_type", "review_failure"))
```
This is a lesson in snapshot-based analysis: always verify "known bugs" against
live code before acting on them.

## Quarterly sweep protocol

Run before any major release or when adding new state file writers/readers.
Estimated time: 30 minutes.

**Step 1 — Writer inventory**: For each state file, list every script that writes
to it. Reference: `docs/state-file-schema.md` writer column.

**Step 2 — Reader inventory**: For each state file, list every script that reads
from it. Reference: `docs/state-file-schema.md` reader column.

**Step 3 — Field name crosscheck**:
```bash
# Verify distill_dream.py field names against schema
grep -n "\.get(" .agent/scripts/distill_dream.py | grep -E "(log|evt|record)"
# Compare field names against docs/state-file-schema.md
```

**Step 4 — Severity casing sweep**:
```bash
grep -rn '"severity"' src/ .agent/scripts/ | grep -v ".pyc"
# All values should be uppercase: INFO, WARNING, HIGH, ERROR, CRITICAL
```

**Step 5 — Timestamp convention check**:
```bash
grep -rn "datetime.now()" .agent/scripts/ src/scripts/
# Should use datetime.now(timezone.utc) or datetime.utcnow() for state files
# .ai-review-log.jsonl is a known exception (local time, documented)
```

**Step 6 — Document new findings**: Add to Known Instances table with ⬜ status
and add companion HIB backlog items.
```

#### 10b. Main backlog — add HIB items (same as Item 4b above)
HIB-FM8-01 and HIB-FM8-02 are added here — these are the two remaining
actionable code fixes from the sweep. See Item 4b for the exact backlog entries.

### Acceptance criteria
- `docs/architecture/fm8-fm9-boundary-audit.md` exists with the known instances table
- FM9-01 is shown as ✅ Fixed with the retraction note explaining the analysis error
- The quarterly sweep protocol is documented with runnable commands
- HIB-FM8-01 and HIB-FM8-02 are in the main backlog (added via Item 4b)

---

## Delivery wave summary

| Wave | Items | Rationale | Config.yaml changes |
|------|-------|-----------|---------------------|
| **Wave 1** | Items 1, 4 | Highest value — gate output format + schema reference. Item 4 also documents FM9-01 retraction accurately. | None |
| **Wave 2** | Items 6, 9 | Architectural additions — GateContext design doc + archetype starter packs | None |
| **Wave 3** | Items 2, 10 | Design specs requiring companion code tickets — write the design before the implementation sprint | None |
| **Wave 4** | Items 3, 8 | Visibility improvements — harness_health.md additions + config keys | `dream_proposals.*`, `health_checks.state_file_size.*` |
| **Wave 5** | Items 5, 7 | Reference and architectural contracts | `concurrency_model` |

Items in Waves 4 and 5 that modify `config.yaml` should be coordinated into
a single PR to avoid conflicts.

**New files created** (12 total):
- `docs/state-file-schema.md`
- `docs/architecture/gate-context-design.md`
- `docs/architecture/capability-calibration-design.md`
- `docs/architecture/concurrency-model.md`
- `docs/architecture/fm8-fm9-boundary-audit.md`
- `docs/state-machine-contracts.md`
- `docs/harness-health.md` (or sections added if exists)
- `docs/archetypes/A2-social-communication.md`
- `docs/archetypes/A3-marketplace-transaction.md`
- `docs/archetypes/A6-platform-api.md`

**Files modified** (7 total):
- `review_context_universal.md` (Item 1)
- `AGENTS.md` / `AGENTS_PROJECT.md` (Items 1, 5)
- `governance.md` (Item 5)
- `CONTRIBUTING.md` (Items 4, 10)
- `FRAMEWORK_ROADMAP.md` (Items 1, 6)
- `docs/getting-started.md` (Items 4, 9)
- `docs/configuration-reference.md` (Items 2, 7)

**New backlog entries** (7 total):
- T1-G-13 (GateContext design — Item 6)
- T1-G-14 (capability calibration code — Item 2)
- HIB-FM8-01 (severity casing — Items 4/10)
- HIB-FM8-02 (harness_version hardcode — Items 4/10)
- HIB-HEALTH-01 (dream proposal staleness code — Item 3)
- HIB-HEALTH-02 (state file size check code — Item 8)

---

## Pre-execution checklist for Gemini

Before starting any wave:
1. `python .agent/scripts/check_repo.py` — verify correct repo
2. `python .agent/scripts/check_halt.py` — exit 0 required
3. `python .agent/scripts/init_session.py` — session initialised
4. Verify `review_context_universal.md` line 146 (existing Decision Block section)
   before Item 1 — do not duplicate, add a new `## Gate Finding Output Format` section
5. Verify `distill_dream.py:329` contains `blocking_concern` (BUG-11 fix confirmed)
   before writing any Item 10 content — the FM9-01 retraction note must be accurate

**Spec reference**: Register this document as a SPEC in `docs/planning/specs/`
before implementation begins, per the `/ba` workflow Phase 4 protocol.
