# Candidate Backlog — Intent-Governance Extensions

**Status**: ITEMS PROMOTED — Candidates evaluated and selectively promoted to mainline roadmap (e.g., CAND-T1-01 to T1-L-16, CAND-T1-05 to T1-D-09). Remaining items explicitly pending.
**Source**: Assessment of four extension pillars proposed in a ChatGPT conversation
(traceability, artifact standards, interoperability/adapters, requirements quality checking),
re-scored against the framework's actual shipped + scoped state.
**Purpose**: Carry each candidate's lifecycle placement and cost-justification into the backlog
so the reasoning survives the conversation. Items use a provisional `CAND-` prefix to avoid
collision with real backlog IDs.

---

## Decision lens (the durable instrument)

Two framings emerged during analysis and govern every candidate below. They are recorded here
because they are model-independent and outlast any token measurement.

**1. The consumption test (primary).**
> A capability earns its tokens if and only if some downstream step *in the delivery loop*
> consumes its output to avoid larger rework. If nothing downstream reads it and changes
> behaviour because of it, the tokens spent generating it are ceremony.

This test is purely structural. It does not depend on what a token costs in any given month or
on which model is running underneath the harness.

**2. Cost is paid across the whole agentic loop, not just the gate.**
The adversarial gate's context budget (CONSTRAINT-01, ≤2,000 tokens) is one line item. The larger
recurring costs are: context-loading at every session start, harness-mandated document generation,
review round-trips, and rework loops. The two largest buckets (context-load, mandated-generation)
occur *inside the implementing agent's runtime* (Gemini CLI / Claude Code) and are **not observable
by the harness** — the harness can only meter its own API calls (gate, Pass 2, acceptance).

**Measurement note (resolved):** absolute token metering was considered and rejected as a stable
metric — it is partially unobservable in principle and non-stationary across model changes. What
survives is counting **model-independent drivers** as integer signals already present in the logs:
LLM round-trips per delivered commit, harness-mandated documents per feature, session-start context
surface size (bytes/lines, tokenizer-free), and rework-loop counts (FAIL verdicts, redrafts,
rebuttals). These count what *inflates* cost in units that do not move when the model does.

**Cost-placement rule of thumb derived from the above:**
- **Spec-time / intake-time / on-demand** → amortized or free → low bar to justify.
- **Per-commit gate hot path** → recurring forever, competes against CONSTRAINT-01 → high bar.
- **Mandated per-session generation with no in-loop consumer** → recurring tax, out-of-loop payback only → usually fails the test.

---

## Boundary articulation (positioning note, not a backlog item)

The sharpest output of the source conversation was a boundary statement worth lifting verbatim into
positioning material (candidate home: **S0-20** competitive positioning):

> AI Delivery Control does not discover intent. It ensures that intent — however obtained — is
> sufficiently clear, internally consistent, traceable, and governable to be transformed into
> reliable software.

All candidates below are tested against this boundary: they evaluate, normalize, or trace intent;
none of them generate intent.

---

## Tier 1 — Individual (solo, multi-project, local-only)

### CAND-T1-01 - Requirements quality: NFR-coverage check at spec-time (Promoted to T1-L-16)
**What**: Extend `check_spec.py` Pass 2 with a missing-non-functional-requirement check
(security, availability, performance, auditability, accessibility, localization, scalability).
Advisory output naming each absent NFR class, consistent with existing ADVISORY behaviour.
**Lifecycle placement**: Spec-time (Pass 2), once per spec — amortized over the spec's whole
implementation life. Extends an LLM call that already fires; adds prompt length, not a new round-trip.
**Consumption test**: PASS. The implementing agent reads a sharper spec and does less wrong work;
catches the failure class (silent-on-NFR specs → silently-wrong-on-NFR code) that is most expensive
to unwind downstream. Plausibly **negative net loop cost** on a non-trivial feature.
**Driver delta**: +0 round-trips (extends existing), +0 mandated docs, possible +1 spec redraft if it fires.
**Relationship to existing**: Natural extension of **T1-L-12** (spec grader per-criterion feedback, ✅ (v1.4.1))
and complements **T1-L-14** (archetype-driven FM weighting, ✅ (v1.4.1)).
**Tier rationale**: Strongest candidate even for a solo dev — pays for itself in avoided re-implementation.
**Effort**: Low.

### CAND-T1-02 - Requirements quality: intra-spec contradiction detection at spec-time (Pending)
**What**: At spec validation, scan acceptance criteria + assumptions for opposed-polarity statements
on the same subject (e.g. "orders editable after submission" vs "submitted orders immutable").
Reuse the keyword-overlap polarity heuristic already in `distill_dream.py`'s contradiction checker.
**Lifecycle placement**: Spec-time, advisory. Can run deterministically (no LLM) or as part of the
existing Pass 2 prompt.
**Consumption test**: PASS. Consumer is the implementer (avoids building a contradiction it then has
to unpick) and the human approver (resolves before APPROVED).
**Driver delta**: +0 round-trips if deterministic or folded into Pass 2.
**Relationship to existing**: Reuses `distill_dream.py` contradiction pattern; complements **T1-L-12**.
**Tier rationale**: Cheap, model-independent if implemented deterministically.
**Effort**: Low.

### CAND-T1-03 - Requirements quality: REQ-vs-ADR conflict check - SPEC-TIME ONLY (Pending)
**What**: At spec validation, check the spec's stated constraints against governing ADR domains
(reuse the compiled wiki / ADR injection already built for the gate).
**Lifecycle placement**: **Spec-time only.** Explicitly NOT at commit time.
**Consumption test**: PASS at spec-time (human resolves architectural conflict before approval).
**⚠ Cost guard**: The tempting variant is to run this on every commit because the ADR injection
machinery already exists in the gate. **Do not.** At commit time it competes against CONSTRAINT-01
on every commit forever; at spec-time it is amortized. The cost-placement rule is the whole point of
this item.
**Driver delta**: +0 round-trips at spec-time (reuses ADR context already compiled).
**Relationship to existing**: Reuses **T1-H-02** (ADR annotation + wiki injection, ✅).
**Effort**: Low.

### CAND-T1-04 - Traceability query layer (read-only, on-demand) (Pending)
**What**: A `traceability_query.py` answering "what does REQ/SPEC-X satisfy?" and "what depends on
SPEC-X?" by reading the existing SQLite index (`state_persistence.py`) joined through `git log`.
Bidirectional navigation, invoked by a human, not auto-maintained.
**Lifecycle placement**: On-demand. Zero per-session loop cost — nothing in the commit loop runs it.
**Consumption test**: PASS (consumer is a human asking a question; out-of-loop but zero recurring cost
means the bar is trivially met).
**Driver delta**: +0 across all per-session driver counts.
**Relationship to existing**: Read layer over **T1-D-01** (✅ v1.4.0). T1-D-02 (harness_health.py SQLite read-side) is ⬜ undelivered — reopened 2026-06-13 following code audit confirming no SELECT functions exist in `state_persistence.py` and no SQLite import in `harness_health.py`. This candidate's substrate (T1-D-02) must be delivered first.
**Tier rationale**: Free to users at any tier; safe to build whenever the read-side is confirmed.
**Effort**: Low.

### CAND-T1-05 - Model-independent driver counters in harness_health.py (Promoted to T1-D-09)
**What**: Add integer driver counts (NOT token metering) to `harness_health.py`: round-trips per
delivered commit, harness-mandated documents per feature, rework-loop count (FAIL/redraft/rebuttal),
and session-start context-surface size in lines/bytes.
**Lifecycle placement**: Read-only over existing logs (`.ai-review-log.jsonl`, `harness_events.jsonl`,
`session_ledger.jsonl`). Zero loop cost.
**Consumption test**: PASS — consumer is the developer's monthly review and any future
capability-vs-capability comparison. Honours the rejected-metering / surviving-driver-count distinction.
**Driver delta**: +0.
**Relationship to existing**: Extends `harness_health.py`; aligns with **T1-C-04** (silent correction
rate, ⬜) and **T1-M-13** (agent-run analytics framing, ⬜).
**⚠ Scope guard**: This counts cost *drivers*, not tokens. Do not let it drift into trying to meter
absolute token spend across providers — that target was assessed and rejected as non-stationary and
partially unobservable.
**Effort**: Low.

---

## Tier 2 — Team (multi-machine, shared state)

### CAND-T2-01 — Persistent cross-release traceability graph (bidirectional)
**What**: The auto-maintained, cross-release version of CAND-T1-04: REQ → TASK → COMMIT → TEST → PR
→ RELEASE links persisted to the shared store, surviving refactoring, navigable from any direction.
**Lifecycle placement**: Recurring per-session write if the agent maintains links automatically.
**Consumption test**: BORDERLINE → PASS at team scale only. At Tier 1 this *failed* (out-of-loop
payback, recurring write tax). At team scale the out-of-loop payback becomes large — teammates
navigating "what depends on REQ-042" across machines — and may justify the recurring write cost.
The cost/benefit inverts with team size, not with the capability.
**Driver delta**: +1 mandated artifact maintained per session (the cost that disqualified it at Tier 1).
**Relationship to existing**: Requires **T2-A-01** (MCP server wrapping SQLite). Builds on CAND-T1-04.
**Tier rationale**: This is genuinely a Tier 2 item — do not pull forward to Tier 1; the recurring
write cost has no in-loop consumer for a solo developer.
**Effort**: Medium.

### CAND-T2-02 — One concrete upstream adapter (issue tracker → Requirement contract)
**What**: A single adapter (most likely GitHub Issues for a starting team) normalizing a raw issue
into the harness's internal Requirement contract (`id, title, description, acceptance_criteria,
constraints, assumptions, priority, references`) consumed by the `/ba` workflow Phase 1 intake.
**Lifecycle placement**: Intake-time, once per requirement, outside the commit loop.
**Consumption test**: PASS. The BA workflow consumes the normalized contract and does *less*
prose-extraction in Phase 1 → neutral-to-negative loop cost. Per-session token cost to users ~zero.
**Driver delta**: ~0 (may reduce BA Phase 1 generation).
**Relationship to existing**: Operationalizes the `/ba` Phase 0 intake; precursor pattern to **T3-C-02**.
**⚠ Scope guard**: Build the **one** adapter the team uses. A generic multi-tool adapter *framework*
is Tier 3 (CAND-T3-02) — speculative framework-building is the maintenance trap.
**Tier rationale**: One adapter is worth it once a team shares a tracker; a framework is not.
**Effort**: Medium.

### CAND-T2-03 — Shared spec-quality policy (NFR checklist as team config)
**What**: Promote CAND-T1-01's NFR checklist to a team-level policy in shared config, so every
developer's specs are evaluated against the same NFR-coverage bar.
**Lifecycle placement**: Spec-time, config-driven.
**Consumption test**: PASS — consumer is every implementer on the team, enforcing consistent intent quality.
**Relationship to existing**: Team-config layer over CAND-T1-01.
**Effort**: Low (once CAND-T1-01 exists).

---

## Tier 3 — Enterprise (regulated, compliance-grade)

### CAND-T3-01 — Audit-grade traceability chain (REQ → … → RELEASE, immutable)
**What**: The compliance-grade form of CAND-T2-01: append-only, immutable, full chain from
requirement to release, answerable for "who approved this, what does it satisfy, what tests cover it."
**Lifecycle placement**: Persisted continuously; queried by auditors out-of-loop.
**Consumption test**: PASS — and arguably *mandatory*, not optional. Consumer is the compliance/audit
function; in SOCI Act / ISM / PSPF contexts this is a requirement, not a convenience.
**Relationship to existing**: Builds on **T3-B-02** (audit immutability) and **T3-C-04** (compliance
reporting); enterprise form of CAND-T2-01.
**Tier rationale**: The out-of-loop payback that was marginal at Tier 1 and borderline at Tier 2 becomes
compliance-mandatory at Tier 3.
**Effort**: Medium–High.

### CAND-T3-02 — Generic adapter framework (multi-tracker)
**What**: The "anything → normalized Requirement contract → harness" vision: Jira, Linear,
Azure DevOps, GitHub Issues, Markdown, each via an adapter behind a common contract interface.
**Lifecycle placement**: Intake-time, outside the loop.
**Consumption test**: PASS at enterprise scale only — where multiple trackers genuinely coexist and the
normalization layer is consumed by a single downstream BA workflow.
**Relationship to existing**: Generalizes **T3-C-02** (Jira/Linear integration) and CAND-T2-02.
**Tier rationale**: Only an enterprise with heterogeneous trackers justifies a *framework*; smaller
units justify a single adapter (CAND-T2-02).
**Effort**: High.

### CAND-T3-03 — Requirements quality as enforcing compliance gate
**What**: Promote CAND-T1-01/02/03 from advisory to *blocking* in `contractual` outer-loop mode —
missing mandated NFRs, unresolved contradictions, or ADR conflicts block APPROVED status.
**Lifecycle placement**: Spec-time, blocking.
**Consumption test**: PASS — consumer is the compliance posture; converts advisory intent-quality into
enforceable policy-as-code at the requirements layer.
**Relationship to existing**: Uses existing `outer_loop.mode: contractual` (**T1-L-00**, ✅);
extends CAND-T1-01/02/03.
**Effort**: Medium.

### CAND-T3-04 — Architecture-conflict checking against formal threat model
**What**: Extend CAND-T1-03's REQ-vs-ADR check to also evaluate requirements against a first-class
`threat_model.md` (adversarial scenarios / abuse paths), at spec-time.
**Lifecycle placement**: Spec-time.
**Consumption test**: PASS — consumer is the security-review function; catches requirements that
contradict the threat model before implementation.
**Relationship to existing**: Depends on **T1-K-05** (threat-model.md as first-class artifact, ⬜).
**Effort**: Medium.

---

### CAND-T3-05 — MCP Layer-4 server
**What**: A Layer-4 MCP server for integration with broader agent ecosystems or specialized capabilities, allowing the harness to be queried cross-project or exposed as a standard tool provider.
**Lifecycle placement**: Persistent service, out-of-loop.
**Consumption test**: PASS at enterprise/multi-agent scale — consumer is other autonomous agents or orchestration layers requiring structured access to intent/governance data.
**Relationship to existing**: Related to T2-A-04 (cross-project MCP-queryable decisions log).
**Tier rationale**: Exposing harness data programmatically across boundaries is an advanced integration pattern (Tier 3).
**Effort**: High.

## Negative space — assessed and argued AGAINST (recorded so they are not re-picked-up as unassessed)

### NEG-01 — Blanket artifact standards / stage contracts at every phase boundary
ChatGPT pillar #2 ("agents exchange structured artifacts, not prose": task.md, review.md,
escalation.md, acceptance.md, test.md at every stage).
**Verdict: do not adopt as a blanket mandate.**
**Reasoning**: Read literally, this mandates additional agent *generation* at every phase boundary —
each artifact is an LLM generation event, the expensive direction. Deterministic *validation* of such
artifacts is cheap; *generating* them is not. Fails the consumption test wherever the artifact is
self-documenting (no downstream gate eats it). Additionally, most of the useful subset already exists
or is scoped: typed verdicts (`ReviewVerdict`, `SpecQualityVerdict`, `AcceptanceVerdict`,
`RouteDecision`) are already structured contracts; the FSM-validated phase-contract version is already
**T1-W** (workflow engine, v1.6.0) and is deterministic by design; the escalation-artifact subset is
already **T1-C-02**, which the backlog *deliberately deprioritized* (rebuttal protocol covers the most
common contention path). The deterministic T1-W path is the only form worth pursuing, and it is already
scoped.

### NEG-02 — Mandated auto-maintained traceability artifact at Tier 1
The per-session "agent writes traceability.md every session" form.
**Verdict: do not adopt at Tier 1.** Recurring per-session generation tax with no in-loop consumer for
a solo developer; payback is entirely human-side and out-of-loop. Use the on-demand query layer
(CAND-T1-04) instead. The mandated form only earns its cost at team scale (CAND-T2-01).

### NEG-03 — Any of the above placed on the per-commit gate hot path
Specifically: REQ-vs-ADR or requirements-quality signals injected into the per-commit review context.
**Verdict: forbidden by the cost-placement rule.** Anything on the per-commit path competes against
CONSTRAINT-01's ceiling on every commit, forever, for every user. Keep all intent-quality work at
spec-time, where it is amortized.

### NEG-04 — Absolute token-cost metering as a stability metric
**Verdict: rejected.** Partially unobservable in principle (the implementing agent's runtime is a black
box to the harness) and non-stationary across model changes (tokenizer shifts, caching, reasoning
tokens). Replaced by model-independent driver counts (CAND-T1-05).

---

## One-screen summary

| ID | Candidate | Tier | Lifecycle placement | Consumption test | Effort |
|----|-----------|------|--------------------|------------------|--------|
| CAND-T1-01 | NFR-coverage check | Individual | Spec-time | PASS (strongest) | Low |
| CAND-T1-02 | Intra-spec contradiction check | Individual | Spec-time | PASS | Low |
| CAND-T1-03 | REQ-vs-ADR conflict (spec-time only) | Individual | Spec-time | PASS (⚠ not commit-time) | Low |
| CAND-T1-04 | Traceability query layer (read-only) | Individual | On-demand | PASS (zero loop cost) | Low |
| CAND-T1-05 | Driver counters (not token meter) | Individual | Read-only | PASS | Low |
| CAND-T2-01 | Persistent bidirectional traceability | Team | Per-session write | PASS at team scale | Medium |
| CAND-T2-02 | One issue-tracker adapter | Team | Intake-time | PASS (~0 user cost) | Medium |
| CAND-T2-03 | Shared NFR policy | Team | Spec-time | PASS | Low |
| CAND-T3-01 | Audit-grade traceability chain | Enterprise | Persisted | PASS (mandatory) | Med–High |
| CAND-T3-02 | Generic adapter framework | Enterprise | Intake-time | PASS at enterprise scale | High |
| CAND-T3-03 | Req-quality as compliance gate | Enterprise | Spec-time (blocking) | PASS | Medium |
| CAND-T3-04 | REQ vs threat-model conflict | Enterprise | Spec-time | PASS | Medium |
| CAND-T3-05 | MCP Layer-4 server | Enterprise | Persistent service | PASS at scale | High |
| NEG-01 | Blanket stage-contract artifacts | — | Per-phase generation | FAIL (= T1-W / typed verdicts) | — |
| NEG-02 | Mandated traceability artifact (T1) | — | Per-session generation | FAIL at Tier 1 | — |
| NEG-03 | Intent-quality on commit hot path | — | Per-commit | FORBIDDEN (CONSTRAINT-01) | — |
| NEG-04 | Absolute token metering | — | — | REJECTED | — |

---

*End of candidate collation. No items accepted. Next step (when ready): triage against shipped state —
several candidates extend existing items (T1-L-12, T1-L-14, T1-H-02, T1-D-01/02, T2-A-01, T3-C-02,
T3-B-02, T1-K-05) rather than standing alone, and CAND-T1-04 must verify the SQLite read-side is wired
before it has a substrate.*
