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
