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
`init_session.py:251` regardless of the actual installed version. Version forensics unreliable.
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
| FM8-01 | FM8 | `harness_events.jsonl` severity | Mixed casing: `"CRITICAL"` (ai_review.py) vs `"info"` (init_session.py). Dream phase bypass trigger misses uppercase events. | ✅ Fixed (v1.3.3) |
| FM8-02 | FM9 | `session_ledger.jsonl` harness_version | Hardcoded `"2.0"` at init_session.py:251. Version forensics unreliable. | ✅ Fixed (v1.3.3) |
| FM8-03 | FM8 | `session_ledger.jsonl` date | Local time vs UTC. Cross-file time correlation requires TZ awareness. | ⬜ T1-I-06 scope |
| FM8-04 | FM8 | `.ai-review-log.jsonl` timestamp | Local time vs UTC. Same cross-reference problem. | ⬜ T1-I-06 scope |
| ~~FM9-01~~ | ~~FM9~~ | ~~distill_dream.py check_type~~ | ~~Field name mismatch~~ | ✅ Fixed BUG-11 |
