# SPEC: v1.4.14 — PunchCard Preparation Release

**Status**: DRAFT
**Author**: Claude (drafting); Peter (review)
**Tracked under**: HIB-068
**Release**: v1.4.14
**Related**: PUNCHCARD_PREFLIGHT_CHECKLIST.md, KNOWN_RISKS.md (RISK-001), T1-K-14 (fail-open audit taxonomy — delivered v1.4.10, this spec extends its behavior), T1-L-08 (fail-closed precedent this spec restores parity with)
**Changelog**:
- v1.0 (2026-07-26, Claude): Initial draft. Corrected version from v1.4.15 → v1.4.14 (typo).

---

## 0. Motivation Gate (context, not blocking)

Peter is preparing to run the PunchCard experiment (2×2 governed/ungoverned × model comparison) and wants the harness itself verified ready first, following v1.4.13's merge to main. This spec is deliberately sequenced ahead of v1.4.14 (Loop Closure Verification) at Peter's direction — the two are independent and neither blocks the other.

Two categories of readiness work remain, identified via PUNCHCARD_PREFLIGHT_CHECKLIST.md and a full backlog scan (2026-07-26):

1. **One real code defect that could silently corrupt experimental data**: HIB-068 — large diffs failing open (`DIFF_TOO_LARGE_FAILOPEN`) bypasses governance entirely for oversized commits. If any PunchCard run in the governed arm happens to produce a large diff, that data point would look identical to the ungoverned arm for reasons unrelated to the experimental variable — a direct threat to measurement validity, not just a general code-quality concern.

2. **Verification actions, not code changes**: RISK-001 (Antigravity CLI hook compatibility, still `Unverified`) and state persistence self-containment both need to actually be exercised against a live session before the experiment runs, and the outcome recorded — these are evidence-gathering activities the harness's own standing practice already applies to backlog claims, now applied to itself.

Starting PunchCard without HIB-068 fixed risks a confounded governed-arm data point that could go unnoticed. Starting it without RISK-001 verified risks the entire governed arm's session traceability being silently unreliable.

---

## 1. Verification Note

Consistent with this project's practice of treating claims as hypotheses requiring evidence: HIB-068's status (⬜ Not Started) and its cross-reference to T1-K-14 were confirmed directly against `harness_improvement_backlog.md` and `FRAMEWORK_ROADMAP.md`'s v1.4.10 delivered-items list before drafting this spec — T1-K-14 delivered the audit taxonomy (`large_diff_fail_open` events, explicit `FAIL_OPEN` verdicts) but not a behavior change; the underlying fail-open path is confirmed still active.

---

## 2. Bounded Scope & Out of Scope

### In-Scope (Goals)

- **Phase 0 (code fix):** HIB-068 — replace the unconditional fail-open response on oversized diffs with either stratified/chunked review or an explicit fail-closed default requiring a deliberate override, per §3 Assumptions.
- **Phase 1 (verification, blocking):** RISK-001 — exercise a real Antigravity session against the four-step verification already specified in `KNOWN_RISKS.md`, and update its status from `Unverified` to a recorded, evidenced outcome.
- **Phase 2 (verification, blocking):** State persistence self-containment — confirm session/state persistence does not depend on Antigravity's internal `state.vscdb`, and record the outcome.
- **Phase 3 (decision, blocking):** Confirm `harness_version.txt` correctly reads `1.4.13` post-merge (or later, if additional releases land first), and record which harness version PunchCard will actually run against — a deliberate choice, not an accident of timing.

### Out-of-Scope (Non-Goals)

- Writing or maintaining `EXPERIMENT_PROTOCOL.md` / `SPEC_PUNCHCARD.md` themselves — those are Peter's own experiment-design artifacts, not harness backlog work, and don't live in this repo.
- D_task normalization, logging plan completeness, HARD STOP-under-Cline verification, and Agent Health Framework adoption — all remain on `PUNCHCARD_PREFLIGHT_CHECKLIST.md` as lower-priority or conditional items, deliberately not pulled into this spec's scope.
- HIB-078 (GATE_ADVISORY batching under ratchet) — not relevant; PunchCard's governed arm runs under `strict`, not `ratchet` (see Assumption below).
- Any change to T1-K-14's existing audit taxonomy — this spec extends the behavior on top of it, not the logging mechanism itself.

---

## 3. Assumptions

- **[Resolved: PunchCard's governed arm runs under `enforcement.posture: strict`]** per the earlier posture-awareness decision (`SPEC-enforcement-postures.md` §9 trigger). HIB-078 and ratchet-specific concerns are therefore genuinely out of scope for this experiment, not just deprioritized.

- **[Pending: HIB-068's exact fix mechanism]**. Two candidates:
  - **(a)** Route oversized diffs through the existing high-risk stratified-review fallback (already used for `high_risk_patterns`-classified paths per HIB-064's incident record) regardless of pattern classification, chunking the diff for review rather than skipping it.
  - **(b)** Default to fail-closed, blocking the commit unless an explicit escape-valve trailer is present (mirroring T1-G-15's `COMPLEXITY-ACCEPTED` pattern) — e.g. `OVERSIZED-DIFF-ACCEPTED: <reason>`.

  Implementation should confirm current `ai_review.py` behavior at the diff-size check before choosing, and prefer (a) if the stratified-review mechanism can be generalized without excessive rework, since it preserves review coverage rather than trading review for an audit trail of a skip.

- **[Resolved: RISK-001 and the state-persistence check are verification activities producing a recorded outcome in `KNOWN_RISKS.md`, not code changes]**. "Complete" for this spec means the verification was actually run against a live Antigravity session and its result — pass, fail, or partial — is documented with evidence, not that the risk was merely re-read and left `Unverified`.

---

## 4. Acceptance Criteria

### Scenario 1: Oversized diffs no longer fail open silently (HIB-068)

**Given** a commit whose diff exceeds `max_diff_lines`
**When** the AI review gate evaluates it
**Then** the gate does not return a bare `FAIL_OPEN` / `DIFF_TOO_LARGE_FAILOPEN` pass-through
**And** instead either completes a stratified/chunked review of the diff, or blocks the commit pending an explicit override trailer.

### Scenario 2: The escape valve (if chosen) is auditable

**Given** HIB-068 is implemented via the fail-closed-with-override approach
**When** a developer commits an oversized diff with the override trailer present
**Then** the commit proceeds, and an audit event distinct from the pre-existing `large_diff_fail_open` event type is written, recording that an explicit override was used (not a silent bypass).

### Scenario 3: Existing T1-K-14 audit taxonomy is preserved

**Given** the existing `large_diff_fail_open` event type and `FAIL_OPEN` verdict schema from T1-K-14
**When** HIB-068's fix lands
**Then** no existing consumer of that event type or verdict schema breaks — this is a behavior change on top of the taxonomy, not a replacement of it.

### Scenario 4: RISK-001 is genuinely verified, not just re-read

**Given** `KNOWN_RISKS.md`'s RISK-001 entry and its four-step verification procedure
**When** this spec's Phase 1 completes
**Then** RISK-001's status field reflects an actual outcome (`Verified` / `Verified with caveats` / `Failed — see remediation`) with the specific evidence recorded (e.g. hook fired, session traceability confirmed, outcome override worked correctly), not left as `Unverified` or updated without a real session having been run.

### Scenario 5: State persistence self-containment is verified

**Given** a live Antigravity session
**When** `.agent/state/session.json` is inspected during and after that session
**Then** its writes and reads are confirmed independent of any Antigravity-internal state store, with the specific check performed documented in `KNOWN_RISKS.md` or an equivalent record.

### Scenario 6: Harness version for the experiment is a recorded decision

**Given** `harness_version.txt`'s current value
**When** this spec's Phase 3 completes
**Then** a decision is recorded (via `record_decision()` / `log_decision.py`) stating which harness version PunchCard will run against and why, rather than the version being whatever happens to be checked out when the experiment starts.

---

## 5. Proposed Phasing

- **Phase 0** — HIB-068 fix. Independent of Phases 1–3; can proceed immediately.
- **Phase 1** — RISK-001 verification. Requires a live Antigravity session; blocking for the experiment regardless of Phase 0's status.
- **Phase 2** — State persistence verification. Can run in the same live session as Phase 1.
- **Phase 3** — Harness version decision. Trivial, can happen any time after Phase 0 lands (so the decision reflects the actually-current version).

Phases 1–3 do not require code changes and can proceed in parallel with Phase 0's implementation.

---

## 6. Alternatives Considered

- **A — Skip HIB-068 for this experiment, rely on PunchCard's task design to avoid large diffs.** Rejected: relying on the experiment's task design to avoid triggering a known gate defect is fragile — a single unexpectedly large agent-generated diff in the governed arm would silently invalidate that data point with no warning, and there's no way to confirm after the fact whether it happened without HIB-068's fix providing visibility.

- **B — Treat RISK-001 verification as optional, proceed with PunchCard and note it as a caveat in the writeup.** Rejected: RISK-001 is not a minor caveat — if session traceability is broken, the entire governed arm's outcome data becomes unreliable in a way that isn't a caveat, it's a validity failure. This needs to be resolved before, not disclosed after.

- **C (chosen) — Fix HIB-068 as real code, verify RISK-001 and state persistence as real actions with recorded evidence, treat everything else on the preflight checklist as lower-priority and out of scope for this specific release.**

---

## 7. Known Residual Risks

- HIB-068's exact fix mechanism (stratified review vs. fail-closed-with-override) is still open per §3 — implementation should confirm current `ai_review.py` behavior before choosing, rather than assuming either candidate matches the current code shape.
- Even with RISK-001 verified today, Antigravity itself could change between verification and the actual PunchCard run — the verification is a point-in-time check, not a permanent guarantee. Worth a quick re-check immediately before running if significant time elapses.
- This spec deliberately does not address D_task normalization or the logging plan — those remain real open items on the preflight checklist that need a decision before running, just not ones requiring harness code changes.

---

## 8. What Changes Where (Implementation Map)

| Component | Change | Phase |
|---|---|---|
| `src/scripts/ai_review.py` | Replace unconditional fail-open on oversized diffs with stratified review or fail-closed-with-override | 0 |
| New or extended test (`tests/test_ai_review.py` or similar) | Regression test seeding an oversized diff, asserting non-silent handling | 0 |
| `docs/planning/KNOWN_RISKS.md` | RISK-001 status updated with real verification evidence | 1 |
| `docs/planning/KNOWN_RISKS.md` (or new entry) | State persistence self-containment check outcome recorded | 2 |
| `.agent/state/decisions_log.md` (via `log_decision.py`) | Harness version decision for the PunchCard run recorded | 3 |

---

*Per standing protocol: this spec stops here for review and approval. No code, verification session, or decision-recording proceeds until sign-off.*
