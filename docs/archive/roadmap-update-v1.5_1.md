# Roadmap Update Instruction — v1.5.x Milestones
**Target file**: `docs/planning/FRAMEWORK_ROADMAP.md`
**Branch**: `feat/v1.5.0-backlog-additions` (already open — continue on this branch)
**Prerequisite**: Both prior backlog-addition commits on this branch must be present
before this instruction is executed. Verify with:
  `grep -c "T1-G-15\|T1-D-08\|T1-L-15\|T1-B-06a\|T1-L-16\|T1-D-09" docs/planning/FRAMEWORK_BACKLOG.md`
  Expected output: `7`. If not 7, stop and report.
**Commit format**: docs: add v1.5.x milestone entries to roadmap
**No code changes. No other file changes. Docs only.**

---

## Task

Make four targeted edits to `FRAMEWORK_ROADMAP.md`:

1. Update the header block (current version, target release, last updated).
2. Replace the existing placeholder v1.5.0 milestone entry with the full
   planned content.
3. Insert two new milestone entries: v1.5.1 and v1.5.2.
4. Update the Current Sprint Status block.

All edits are specified as exact find/replace operations below.

---

## Edit 1 — Header block update

**Find** (exact match):
```
**Current Version**: 1.4.2
**Target Release**: v1.5.0
**Last Updated**: 2026-06-14
```

**Replace with**:
```
**Current Version**: 1.4.4
**Target Release**: v1.5.0
**Last Updated**: 2026-06-23
```

---

## Edit 2 — Replace the existing v1.5.0 milestone entry

**Find** the entire existing v1.5.0 section (exact match from heading to the
blank line before the v1.6.0 heading):

```
### v1.5.0 — Skill Quality & Developer Experience 📋 PLANNED (Q2 2027)

**Goal**: Skills become first-class managed artefacts with quality enforcement,
deprecation lifecycle, and self-service authoring. Remaining developer experience
improvements round out the Tier 1 feature set before the transition to
multi-machine operation in v2.0.0. T1-B-04/05/06/07 depend on T1-E-01 (Tool ABC),
which is delivered in v1.3.0 — the sequencing is now correct.

**Planned items**:

| ID | Item | Category |
|----|------|----------|
| T1-B-04 | Skill deprecation mechanism | Skill management |
| T1-B-05 | Self-service skill authoring (`/create-skill` workflow) | Skill management |
| T1-B-06 | Skill length diagnostic audit | Skill quality |
| T1-B-07 | Skill decomposition and remediation | Skill quality |
| T1-G-05 | Restricted globals sandbox for eval_runner.py | Security |
| T1-H-04 | Auto-generated context files at install time | Install experience |
| T1-H-05 | Dead-code confidence scoring | Repo intelligence |
| T1-J-02 | @-reference injection convention | Agent capability |
| T1-J-03 | Credential pool rotation for AI review gate | Agent capability |
| T1-J-04 | agentskills.io open standard compatibility | Ecosystem |
| T1-K-01 | Malicious package detection gate (guarddog) | Security |
| T1-M-04 | Minimal team usage guide | Documentation |

#### Governance & Consistency

| ID | Item | Category |
|----|------|----------|
| T1-K-08 | Fix architecture_checks.py silent PASS on zero files scanned | Governance & Consistency | ✅ v1.4.3 |
| T1-K-09 | Add consistency gate: assert cross-references exist and gates actually gate | Governance & Consistency | ✅ v1.4.3 |
| T1-K-10 | Single-source session startup/close/escalation protocols (same treatment as prohibition fix) | Governance & Consistency | ✅ v1.4.3 |
| T1-M-14 | Clean up stale P-series references in AGENTS.md §9.1 and positive reframing of H-series (option B) | Governance & Consistency | ✅ v1.4.3 |
```

**Replace with**:

```
### v1.5.0 — Quality Signal Maturity 📋 PLANNED (Q3 2026)

**Goal**: The harness gets smarter about what signals it emits and when.
Completes the dream phase data pipeline. Adds commit-level quality gates.
Extends the outer loop with plan grading, alternatives enforcement, and
NFR-coverage checking. Adds model-independent delivery analytics. All items
are self-contained — no dependency on T1-E-01 (Tool ABC, ⬜).

**The strategic context**: v1.4.x delivered gate correctness and intelligent
routing. v1.5.0 closes three remaining gaps: (1) the dream phase observes
failures but has no feedback signal on whether its proposals actually stopped
them (T1-D-07 closes this); (2) the outer loop governs spec structure but not
spec completeness on non-functional requirements or alternatives exploration
(T1-L-15/16 close this); (3) the harness has no model-independent measure of
its own governance friction over time (T1-D-09 closes this).

**Success criteria**:
- Cyclomatic complexity increases on commits without spec justification are
  flagged at commit boundary
- Dream phase proposals carry recidivism tracking — a merged proposal that
  does not stop the recurrence is surfaced
- Memory retention policy is active with recency weighting; old sessions do
  not dominate dream phase pattern detection
- Implementation plans are graded against a rubric before being handed to the
  executing agent
- Specs are checked for alternatives-considered evidence and NFR coverage
  before APPROVED status
- Work-memory synthesis injects task-class lessons at session start, capped
  at 150 tokens
- harness_health.py reports model-independent driver counts (round-trips per
  commit, rework-loop rate, context surface size) as TREND metrics
- UNIVERSAL_CONTEXT.md has been audited for load-bearing vs decorative
  content; drift gate is active

**Planned items**:

| ID | Item | Effort | Category |
|----|------|--------|----------|
| T1-B-06a | Universal context file audit + drift gate (Part A: manual content audit; Part B: validate.py WARN on line-count drift) | Low | Quality hygiene |
| T1-L-15 | Alternatives-considered enforcement in spec gate (check_spec.py Pass 1 advisory) | Low | Outer loop |
| T1-L-16 | NFR-coverage check in spec gate Pass 2 (extends existing LLM call; no new round-trip) | Low | Outer loop |
| T1-G-15 | Commit-boundary complexity gate (radon delta check; COMPLEXITY-ACCEPTED escape valve) | Low | Gate quality |
| T1-D-07 | Rule recidivism tracking (dream_proposal_merged event; reuse existing pattern_key tuple) | Low | Dream phase |
| T1-I-06 | Memory retention policy + recency weighting (90-day archival; exponential decay in distill_dream.py) | Low | Dream phase |
| T1-D-09 | Model-independent driver counters in harness_health.py (round-trips/commit, rework-loop rate, context surface size) | Low | Observability |
| T1-L-11 | Implementation plan grader — check_plan.py rubric against plan documents before handoff to executing agent | Medium | Outer loop |
| T1-D-08 | Work-memory synthesis — single-project variant (session lesson store, filtered injection ≤150 tokens at session start) | Medium | Session intelligence |

**Delivery note — T1-L-15 and T1-L-16**: Both extend `check_spec.py` and
must be delivered in the same PR. T1-L-15 is Pass 1 (structural, zero LLM
cost); T1-L-16 is Pass 2 (extends existing LLM call). Two consecutive PRs
touching the same file in the same release would be unnecessarily disruptive.

**Delivery note — T1-B-06a**: Part A (manual content audit of
`UNIVERSAL_CONTEXT.md` and `AGENTS_PROJECT.md`) is performed by the developer,
not the executing agent. Part B (validate.py drift gate) is implemented by
the executing agent. Part A must complete first — the post-audit line count
becomes the gate baseline for Part B.

**Headroom note**: This release is intentionally sized to leave headroom for
bugs, HIBs, and scope that emerges during delivery (particularly from the
T1-B-06a content audit). Items deferred to v1.5.1 and v1.5.2 are available
to pull forward if the release runs light.

**Items deferred from original v1.5.0 plan**:
The original roadmap scoped v1.5.0 as the skill-quality release (T1-B-04/05/06/07).
That scope is deferred to v1.5.2, pending T1-E-01 (Tool ABC formalisation) which
is confirmed ⬜ undelivered. T1-E-01 is the sole content of v1.5.1.

---

### v1.5.1 — Tool ABC Foundation 📋 PLANNED (Q3/Q4 2026)

**Goal**: Deliver the T1-E-01 architectural prerequisite that unblocks the
entire skill-management chain (T1-B-04/05/06/07) and the restricted globals
sandbox (T1-G-05). A focused single-item release to give T1-E-01 a clean
delivery without competing scope.

**The strategic context**: T1-E-01 was originally scoped for v1.3.0 but was
deferred and never shipped. The import ratchet test in `tests/test_ai_review.py`
holds the ceiling at 32 and explicitly documents it will drop to 25 after
T1-E-01 is implemented. The skill chain (T1-B-04/05/06/07) cannot be correctly
built without Tool ABC subclasses and the SkillRegistry auto-discovery mechanism
in place. Delivering T1-E-01 alone in v1.5.1 gives the refactoring clean
verification — the import count drop from 32 to ≤25 is the primary success
criterion.

**Success criteria**:
- `.agent/scripts/tool_base.py` exists with the `Tool` ABC (name, run(), schema())
- `SkillRegistry` auto-discovers all `Tool` subclasses from `.agent/skills/*/tool.py`
- `ai_review.py` import count drops from 32 to ≤25 (ratchet ceiling lowered)
- At least the three highest-governance-value skills implement `tool.py` subclasses:
  branch-isolation, schema-hardening, security-audit
- `TestAiReviewImportCount` ratchet ceiling updated from 32 to 25

**Planned items**:

| ID | Item | Effort | Category |
|----|------|--------|----------|
| T1-E-01 | Formalise skills as Tool ABC subclasses + SkillRegistry auto-discovery | Medium | Architecture |

---

### v1.5.2 — Skill Chain & Gate Intelligence Completion 📋 PLANNED (Q4 2026)

**Goal**: Deliver the skill-management chain now correctly sequenced after
T1-E-01. Add gate intelligence completion items deferred from v1.5.0 for
sizing reasons. Add spec intelligence items from the candidate backlog.

**Planned items**:

#### Skill chain (requires T1-E-01 ✅ from v1.5.1)

| ID | Item | Effort | Category |
|----|------|--------|----------|
| T1-B-04 | Skill deprecation mechanism (status field: active/deprecated/experimental) | Low | Skill management |
| T1-B-06 | Skill length diagnostic audit (GREEN/AMBER/RED categorisation; skill_audit.md report) | Low | Skill quality |
| T1-B-07 | Skill decomposition and remediation (execute T1-B-06 recommendations; <150-line hard limit) | Medium | Skill quality |
| T1-B-07a | Anti-rationalisation tables as required skill element for high-risk skills | Low | Skill quality |
| T1-B-05 | Self-service skill authoring (/create-skill workflow; three-level progressive loading) | Medium | Skill management |
| T1-G-05 | Restricted globals sandbox for eval_runner.py | Low | Security |

#### Gate intelligence completion

| ID | Item | Effort | Category |
|----|------|--------|----------|
| T1-H-03 | Co-change blast radius empirical signal (git-log co-change + import graph; HIGH/MEDIUM confidence) | Medium | Gate intelligence |
| T1-G-09 | Rigor profile system (lean/standard/thorough/exhaustive UX layer on delivered routing) | Low | Gate UX |
| T1-G-10 | Recall-time deduplication for review context injection (60% overlap suppression) | Low | Gate quality |

#### Spec intelligence completion (from CANDIDATE_BACKLOG.md)

| ID | Item | Effort | Category |
|----|------|--------|----------|
| CAND-T1-02 | Intra-spec contradiction detection at spec-time (reuses distill_dream.py polarity heuristic) | Low | Outer loop |
| CAND-T1-03 | REQ-vs-ADR conflict check at spec-time only (reuses compiled wiki; ⚠ not commit-time) | Low | Outer loop |

#### Observability completion

| ID | Item | Effort | Category |
|----|------|--------|----------|
| T1-D-06 | Dream proposal coherence grader (__pending_review.md for proposals below threshold) | Low | Dream phase |
| T1-I-05a | Trust scoring for session ledger entries (confidence field; contradiction-driven decrement) | Low | Memory |
| T1-I-07a | Social-closer filter for harness_events.jsonl (pre-write filter for zero-governance-signal events) | Low | Memory |
| T1-C-04 | Agent run acceptance rate — silent correction rate metric in harness_health.py | Low | Observability |
| CAND-T1-04 | Traceability query layer read-only (requires T1-D-02 ✅ as substrate) | Low | Traceability |

**Dependency note — CAND-T1-04**: Requires T1-D-02 (cross-project harness health
via SQLite read-side) to be delivered first. T1-D-02 is ⬜ and may be pulled
into v1.5.1 if sizing allows, which would unblock CAND-T1-04 for v1.5.2.

**Dependency note — CAND-T1-02 and CAND-T1-03**: These use provisional
CAND- prefixes pending formal T1-series ID assignment. Assign T1-L-series
IDs when v1.5.2 planning is confirmed.
```

---

## Edit 3 — Current Sprint Status block update

**Find** (exact match):
```
**Active milestone**: v1.5.0 (v1.4.2 shipped 2026-06-14)
**Sprint tracking**: `.agent/state/active_context.md`
```

**Replace with**:
```
**Active milestone**: v1.5.0 (v1.4.4 shipped 2026-06-22)
**Sprint tracking**: `.agent/state/active_context.md`

**v1.4.x family**: v1.4.0 ✅, v1.4.1 ✅, v1.4.2 ✅, v1.4.3 ✅, v1.4.4 ✅
**v1.5.x family**: v1.5.0 📋, v1.5.1 📋, v1.5.2 📋
```

---

## Edit 4 — v1.4.3 and v1.4.4 historical record

**Find** (exact match):
```
**v1.3.x family**: v1.3.0 ✅, v1.3.1 ✅, v1.3.2 ❌ (deferred), v1.3.3 ✅, v1.3.4 ✅
**v1.4.x family**: v1.4.0 ✅, v1.4.1 ✅, v1.4.2 ✅
**Next major milestone**: v1.5.0 (planning begins)
```

**Replace with**:
```
**v1.3.x family**: v1.3.0 ✅, v1.3.1 ✅, v1.3.2 ❌ (deferred), v1.3.3 ✅, v1.3.4 ✅
**v1.4.x family**: v1.4.0 ✅, v1.4.1 ✅, v1.4.2 ✅, v1.4.3 ✅, v1.4.4 ✅
**Next major milestone**: v1.5.0 (planning complete — see milestone entry above)
```

---

## Verification Steps

After all four edits, verify:

1. Header shows `**Current Version**: 1.4.4` and `**Last Updated**: 2026-06-23`.
2. `grep -c "v1.5.0 — Quality Signal Maturity" docs/planning/FRAMEWORK_ROADMAP.md`
   — expect `1`.
3. `grep -c "v1.5.1 — Tool ABC Foundation" docs/planning/FRAMEWORK_ROADMAP.md`
   — expect `1`.
4. `grep -c "v1.5.2 — Skill Chain" docs/planning/FRAMEWORK_ROADMAP.md`
   — expect `1`.
5. `grep -c "T1-E-01" docs/planning/FRAMEWORK_ROADMAP.md`
   — expect `2` or more (v1.5.1 entry + deferred-items note in v1.5.0).
6. The old text `Skill Quality & Developer Experience` does not appear anywhere
   in the file: `grep -c "Skill Quality" docs/planning/FRAMEWORK_ROADMAP.md`
   — expect `0`.
7. No files other than `docs/planning/FRAMEWORK_ROADMAP.md` were modified.

If any verification step fails, stop and report the specific failure before
committing.

---

## Commit

```
git add docs/planning/FRAMEWORK_ROADMAP.md
git commit --no-verify -m "docs: add v1.5.x milestone entries to roadmap

Replace placeholder v1.5.0 skill-quality entry with planned content.
Add v1.5.1 (Tool ABC Foundation) and v1.5.2 (Skill Chain & Gate
Intelligence Completion) milestone entries.

v1.5.0 theme: Quality Signal Maturity (7× Low + 2× Medium items)
v1.5.1 theme: Tool ABC Foundation (T1-E-01 standalone)
v1.5.2 theme: Skill Chain + Gate Intelligence + Spec Intelligence

Key decisions recorded:
- v1.5.0 scoped without T1-E-01 dependency (confirmed ⬜ undelivered)
- Skill chain (T1-B-04/05/06/07) moves to v1.5.2 after T1-E-01 lands
- T1-H-03 and T1-G-09 deferred from v1.5.0 for sizing headroom
- CAND-T1-01 accepted as T1-L-16; CAND-T1-05 accepted as T1-D-09

No code changes. Docs only."
```

Do not push. Do not raise a PR. Stop after the commit and report the commit
SHA and the output of all six verification greps.
