# Backlog Addition Instruction — CANDIDATE_BACKLOG Tier 1 Items
**Target file**: `docs/planning/FRAMEWORK_BACKLOG.md`
**Branch**: `feat/v1.5.0-backlog-additions` (already open — continue on this branch)
**Commit format**: docs: add CANDIDATE_BACKLOG Tier 1 items as T1-L-16 and T1-D-09
**No code changes. No other file changes. Docs only.**

---

## Context

Two Tier 1 candidates from `docs/planning/CANDIDATE_BACKLOG.md` have been
accepted into the v1.5.0 release plan after assessment against the v1.5.x
planning session. They require proper T1-series IDs and registration in
`FRAMEWORK_BACKLOG.md` before the roadmap update is written.

- **CAND-T1-01** → **T1-L-16** (spec gate extension, T1-L series)
- **CAND-T1-05** → **T1-D-09** (harness_health.py extension, T1-D series)

The source reasoning and consumption-test analysis is preserved in
`docs/planning/CANDIDATE_BACKLOG.md` and does not need to be reproduced
in full in the backlog entries — a cross-reference is sufficient.

---

## Task

Add the two entries below to `FRAMEWORK_BACKLOG.md` in the locations
specified. Copy the table rows exactly as written.

---

## Entry 1 — T1-L-16: NFR-Coverage Check in Spec Gate Pass 2

**Location**: Insert as a new row at the **end** of the `### T1-L: Outer Loop
Governance` table, after the existing T1-L-15 row (added in the prior commit
on this branch).

```markdown
| T1-L-16 | **NFR-coverage check in spec gate Pass 2** | Extend `check_spec.py` Pass 2 (LLM-assisted quality check) to evaluate whether the spec's acceptance criteria address each of the seven standard non-functional requirement classes: security, availability, performance, auditability, accessibility, localisation, and scalability. Output is an ADVISORY listing each absent NFR class by name, consistent with existing Pass 2 advisory behaviour — not a hard block. The check extends the LLM call that already fires for Pass 2; it does not add a new round-trip. The prompt addition asks the reviewing model to evaluate NFR coverage against the seven classes and report any that have no corresponding acceptance criterion or architectural constraint. If all seven are present or explicitly marked out-of-scope in the spec, the advisory is suppressed. **Rationale**: Specs that are silent on NFRs produce implementations that are silent on NFRs — the failure mode is expensive to unwind downstream because it typically surfaces in production or security review rather than in the gate. The consumption test for this check is the strongest of any spec-gate extension: the implementing agent reads a sharper spec and does proportionally less wrong work. The check is amortised over the full implementation life of the spec — one advisory at spec-approval time versus the cost of retrofitting NFR compliance post-implementation. At spec-time, this is plausibly a negative net loop cost on any non-trivial feature. **Delivery note**: T1-L-16 and T1-L-15 (alternatives-considered enforcement) both extend `check_spec.py` and should be delivered in the same PR to avoid two consecutive commits touching the same file. **Relationship to existing**: Natural extension of T1-L-12 ✅ (spec grader per-criterion feedback) and complements T1-L-14 ✅ (archetype-driven FM weighting). Source: `docs/planning/CANDIDATE_BACKLOG.md` CAND-T1-01 — consumption test PASS, effort Low. | Low | ⬜ |
```

---

## Entry 2 — T1-D-09: Model-Independent Driver Counters in harness_health.py

**Location**: Insert as a new row at the **end** of the `### T1-D: Observability
& Intelligence` table, after the existing T1-D-08 row (added in the prior commit
on this branch).

```markdown
| T1-D-09 | **Model-independent driver counters in harness_health.py** | Add four integer driver counts to `harness_health.py` output, computed from existing logs with zero per-session loop cost. The four counters: (1) **LLM round-trips per delivered commit** — count of distinct LLM API calls in `.ai-review-log.jsonl` divided by commits in `session_ledger.jsonl` for the reporting window; (2) **harness-mandated documents per feature** — count of spec files, plan files, and acceptance check outputs generated per SPEC-ID resolved from `harness_events.jsonl`; (3) **rework-loop count** — count of FAIL verdicts, gate rebuttals, and redraft events from `.ai-review-log.jsonl` and `harness_events.jsonl`; (4) **session-start context surface size** — lines and bytes of `UNIVERSAL_CONTEXT.md` + `AGENTS_PROJECT.md` + loaded skill files, measured at session start and written to `session_ledger.jsonl` as a `context_surface_lines` field. All four are model-independent: they count structural events that do not move when the underlying LLM changes tokenizer, caching behaviour, or pricing. **Scope guard**: These counters measure cost *drivers*, not absolute token spend. Do not extend this item to attempt absolute token metering across providers — that target was assessed and rejected as non-stationary and partially unobservable in principle (the implementing agent's runtime is a black box to the harness). The surviving instrument is the driver count. **Display**: Each counter appears in `harness_health.py` output as a TREND metric (IMPROVING / STABLE / DEGRADING) computed week-over-week from `session_ledger.jsonl`. A rising rework-loop count or rising round-trips-per-commit signals gate calibration drift or scope creep; a rising context surface size signals UNIVERSAL_CONTEXT.md drift (the condition T1-B-06a's drift gate is designed to catch). **Rationale**: The developer's monthly `harness_health.py` review is the primary consumption point. T1-D-07 (recidivism tracking) tells you whether a fixed rule stopped recurring failures; T1-D-09 tells you whether the harness is generating more or less friction per commit over time. Together they give the self-improvement loop a cost-of-governance signal alongside its quality signal. Source: `docs/planning/CANDIDATE_BACKLOG.md` CAND-T1-05 — consumption test PASS, effort Low. Relationship to existing: extends `harness_health.py`; aligns with T1-C-04 (silent correction rate, ⬜) and T1-M-13 (agent-run analytics framing, ⬜). | Low | ⬜ |
```

---

## Verification Steps

After adding the two entries, verify:

1. `T1-L-16` appears in the T1-L table after `T1-L-15`.
2. `T1-D-09` appears in the T1-D table after `T1-D-08`.
3. No other rows were modified.
4. No other files were modified.
5. Run: `grep -c "T1-L-16\|T1-D-09" docs/planning/FRAMEWORK_BACKLOG.md`
   — expect output `2`.
6. Run: `grep -c "T1-G-15\|T1-D-08\|T1-L-15\|T1-B-06a\|T1-L-16\|T1-D-09" docs/planning/FRAMEWORK_BACKLOG.md`
   — expect output `7` (the 4 from the prior commit + the cross-reference of T1-G-15
   inside T1-B-06a's description + these 2 new entries = 7).

If any verification step fails, stop and report the failure before committing.

---

## Commit

```
git add docs/planning/FRAMEWORK_BACKLOG.md
git commit --no-verify -m "docs: add CANDIDATE_BACKLOG Tier 1 items as T1-L-16 and T1-D-09

Accept two candidates from CANDIDATE_BACKLOG.md into v1.5.0 release plan
with proper T1-series IDs:

- T1-L-16: NFR-coverage check in check_spec.py Pass 2 (extends T1-L-15,
  same PR delivery)
- T1-D-09: Model-independent driver counters in harness_health.py (zero
  loop cost, complements T1-D-07 and T1-D-08)

Source reasoning preserved in CANDIDATE_BACKLOG.md CAND-T1-01 / CAND-T1-05.
No code changes. Docs only."
```

Do not push. Do not raise a PR. Stop after the commit and report the commit
SHA and the output of both verification greps.
