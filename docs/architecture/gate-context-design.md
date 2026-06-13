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
    schema_version: str = "1.0"
    generated_at: Optional[str] = None  # ISO timestamp, for staleness checks independent of schema version
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

## Write safety and staleness handling

Each pre-commit hook runs as a separate process. Hooks may run in any order,
may be skipped (e.g. `--no-verify`, hook not configured), or may crash
mid-write. The following three rules are mandatory for any component that
writes to `gate_context_current.json`:

### 1. Atomic writes via temp-file + rename

Never write directly to `gate_context_current.json`. Write to a temp file in
the same directory, then atomically replace:

```python
import json
import os

def write_gate_context(context: GateContext, path: str) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(context.model_dump(), f, indent=2)
    os.replace(tmp_path, path)  # atomic on POSIX and Windows
```

This guarantees no reader ever sees a partially-written file, even if two
hooks write concurrently or a process is killed mid-write.

### 2. Schema version field

`GateContext` includes a `schema_version: str` field (e.g. `"1.0"`). When
`ai_review.py` reads the file, it checks this field against the version it
expects. If the versions don't match (e.g. the file was written by a hook
from a previous harness version that hasn't been upgraded yet), `ai_review.py`
logs an ADVISORY and proceeds as if the file were absent — it does NOT raise
a validation error and does NOT block the commit. Stale or incompatible
context degrades to "no deterministic findings available," not a hard failure.

### 3. Absence and partial-data as defaults, not errors

Every field in `GateContext` that is populated by an optional component
(co-change estimator, PageRank repo map, ADR domain detector) must have a
sensible default (empty list, `None`, or zero) — not a required field. Three
cases must all degrade gracefully:

- **File absent entirely** (fresh clone, no hooks have run yet): `ai_review.py`
  proceeds with an empty `GateContext`, no deterministic findings section
  injected.
- **File present but a section is missing** (one hook ran, another didn't,
  e.g. repo_graph_cache.json doesn't exist yet so PageRank scores are absent):
  `ai_review.py` injects only the sections that are present.
- **File present but schema version mismatch**: treat as case 1 (absent).

In all three cases, this is a degraded-but-functional state, not a halt
condition. Each component's hook should also independently handle "my
upstream dependency hasn't run" — e.g. the co-change estimator should not
crash if the PageRank cache doesn't exist; it simply omits PageRank-weighted
co-change signals.

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
