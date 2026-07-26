# PunchCard Pre-Flight Checklist

**Purpose**: Verification and protocol-design items to close out before the PunchCard experiment (2×2 governed/ungoverned × model comparison) runs. Compiled 2026-07-25 from prior design sessions plus a check of current harness state. This is a pre-flight gate, not backlog work — nothing here is v1.5.0 scope, and none of it should be deferred behind v1.5.0 planning.

**Status of source artifacts**: `EXPERIMENT_PROTOCOL.md` and `SPEC_PUNCHCARD.md` were drafted in a prior session but are **not present anywhere in the `ai-delivery-control` repo** (checked `docs/`, `scratch/`, `parked/`). Confirm their actual location before treating any item below as "already handled" — if they don't exist elsewhere either, they need to be reconstructed, not just referenced.

---

## 1. RISK-001 — Antigravity CLI hook compatibility (blocking)

**Status**: Unverified (per `docs/planning/KNOWN_RISKS.md`, added 2026-06-28).

This is the single highest-priority item. If Antigravity's hook semantics diverged from the Gemini CLI conventions the harness was built against (`GEMINI.md` load, `TaskStart` → `init_session.py`, `agent_session_close.json`, `outcome_override`), the governed arm's session traceability and outcome recording could be silently broken — which would corrupt the exact data PunchCard exists to produce, the same failure class as HIB-GEMINI-01/HIB-053 but inside the experiment's own measurement path rather than production.

**Action**: Run the four-step verification already specified in `KNOWN_RISKS.md` RISK-001 in a real Antigravity session before any PunchCard arm executes. Do not substitute a dry run of the harness elsewhere — it has to be Antigravity specifically, since that's the governed arm's actual runtime.

---

## 2. Posture-awareness protocol decision (blocking — newly triggered)

**Status**: Deferred condition in `SPEC-enforcement-postures.md` §9 has now fired.

That spec explicitly parked this: *"Posture-aware behaviour for the PunchCard experiment cells — the 2×2 design predates postures; revisit protocol only if postures ship before execution."* Postures (T1-G-18) shipped in v1.4.12. Execution hasn't happened yet. The trigger condition is met.

**Action**: Explicitly decide and write into the protocol document which `enforcement.posture` the governed arm runs under. Almost certainly `strict` — PunchCard's task is a fresh, greenfield codebase with nothing to grandfather, so `ratchet`/`observe` shouldn't be in play. But it needs to be an explicit, documented choice in `EXPERIMENT_PROTOCOL.md`, not an implicit default the harness happens to fall back to. Note in passing: HIB-080 (the `architecture_checks.py` ratchet-baseline wiring gap) should not affect PunchCard either way under `strict`, but confirm that assumption once the posture decision is written down rather than leaving it implicit.

---

## 3. State persistence self-containment (verify)

**Status**: Identified as a pre-experiment validation step in a prior design session; no confirmation found that it was checked.

Confirm the harness's session/state persistence does not depend on Antigravity's internal `state.vscdb` — if it does, state could leak or desync between arms, or fail to persist at all outside an active Antigravity session, corrupting cross-arm comparability.

**Action**: Inspect a live session's `.agent/state/session.json` and confirm it's written and read independently of any Antigravity-internal state store.

---

## 4. HARD STOP enforcement mechanism under Cline (verify, conditional)

**Status**: Identified as needing verification; relevant only if any experimental arm runs under Cline rather than Antigravity/Claude Code.

Confirm whether HALT/HARD STOP enforcement is hook-based (reliable, structural) or instruction-based (convention, agent-compliance-dependent) under Cline. If any arm uses Cline, an instruction-based HALT is a confound — an ungoverned-looking failure could actually be a governed arm whose stop mechanism silently didn't fire.

**Action**: If Cline isn't in scope for this run, mark N/A explicitly in the protocol rather than leaving it unaddressed. If it is in scope, verify before running.

---

## 5. Task-demand normalization (D_task) — protocol methodology gap

**Status**: Identified in a prior session (Ian Johnson's Harness Engineering framework — D_task = L × H_tool × S_state × (1 + N_obs) × (1 − V_oracle)); not yet folded into the protocol as far as I can find.

Without normalizing for task demand, a raw governed-vs-ungoverned comparison risks comparing apples to oranges if any cell's task variant is inherently harder — the result would show "governed does better" without being able to attribute it correctly to governance rather than task difficulty variance.

**Action**: Before finalizing `EXPERIMENT_PROTOCOL.md`, either confirm all cells share an equivalent D_task profile by design (same task, same ambiguity points, same tooling — likely true here since it's a fixed spec across all 8 runs), or add a normalization step to the analysis plan. Given the design already fixes the task and Turn 1 instruction identically across runs, this may already be satisfied structurally — worth a one-line explicit confirmation in the protocol rather than leaving it as an open question.

---

## 6. Harness version pinning (operational, not yet confirmed)

Pin the experiment to a specific tagged harness commit before starting; record the exact hash in `EXPERIMENT_PROTOCOL.md`. No mid-run fixes — if a defect surfaces during a run, log it as a finding (HIB entry) rather than patching and continuing, or the arms end up testing different harness states.

**Action**: Given the open items in flight (v1.4.13 stabilization branch, HIB-080, the rebuttal-protocol cluster), decide explicitly whether PunchCard runs against the current `main` (v1.4.12) or waits for a clean, fully-verified v1.4.13 tag. Running against a version with known, documented open defects is fine as long as it's a deliberate choice recorded in the protocol — not an accident of timing.

---

## 7. Logging plan (operational, low risk but easy to under-scope)

Confirm the protocol captures, per arm: raw transcripts, gate trigger logs, token counts, and wall-clock time. The qualitative governed/ungoverned failure comparisons (e.g. the silent-assumption endpoint-invention failure mode already observed in smoke testing) are likely to matter more for any eventual write-up than the summary statistics — make sure the capture plan doesn't only save aggregates.

---

## 8. Not blocking, optional

- **Agent Health Framework (OpenSearch)** as a measurement instrument — evaluated in a prior session, never adopted or rejected. Not required; PunchCard can run with hand-rolled scoring. Worth a explicit decision (adopt / skip) so it doesn't linger as an open question, but it's not a gate.
- **Model selection** — Qwen3.6-35B-A3B via Ollama with PCIe offload — appears settled; smoke test passed and already demonstrated the target failure mode (invented endpoint, retroactive justification). No further action unless something changed since.

---

## Summary

| # | Item | Blocking? | Status |
|---|---|---|---|
| 1 | RISK-001 Antigravity hook compatibility | Yes | Unverified |
| 2 | Posture-awareness protocol decision | Yes | Not yet decided |
| 3 | State persistence self-containment | Yes | Not confirmed |
| 4 | HARD STOP under Cline | Conditional | Not confirmed |
| 5 | D_task normalization | Should confirm | Likely satisfied by design, not stated explicitly |
| 6 | Harness version pinning | Should decide | Not yet decided given v1.4.13 in flight |
| 7 | Logging plan completeness | Low risk | Assumed but not verified against current protocol draft |
| 8 | Agent Health Framework adoption | Optional | Undecided, non-blocking |
