# Findings: Three Gaps in AI Delivery Control

Direct investigation, replacing the prior deep-research output which produced a research-planning document instead of findings. Each gap below: verified comparator mechanisms, feasibility against your stated constraints, a concrete integration proposal, and explicit flags where I could not verify something.

---

## Gap 1: Cross-project calibration convergence

### Comparator 1 — great_cto (verified, with one unresolved discrepancy)

Two of great_cto's own sources describe the promotion mechanism differently, and I can't resolve which is accurate without reading source code:

- **The repo README** describes a single-incident path: *"After a P0 incident, agents extract a structured pattern. `/crystallize` promotes it to a global pattern after your approval. The pattern surfaces in every agent's Step 0 across all your projects."* This implies one P0 incident + one manual approval is sufficient to promote.
- **A design-rationale blog post by the same author** (dev.to/great_cto) describes a different threshold: *"Per-org (`~/.great_cto/decisions.md`). Patterns confirmed across ≥3 projects. Promoted from per-project after manual review."*

These could be two different mechanisms (P0-incident-triggered crystallization vs. a separate general pattern-confirmation pipeline), or the blog post could describe an earlier/aspirational design not reflected in the shipped README. **Flagging this as genuinely unresolved** — worth a direct look at the actual `/crystallize` implementation if you want certainty before borrowing the design, since the two descriptions imply different evidence bars (1 incident vs. 3 confirmed projects).

What's consistent across both sources: a four-tier memory model (session → per-project → per-org → cross-project incident hash), local files only (`~/.great_cto/decisions.md`), human approval gate on promotion, and an explicit claim of *"94% MTTR reduction on second occurrence"* for the incident-pattern tier specifically — note this is a self-reported metric with no third-party verification I could find.

### Comparator 2 — CodeRabbit's "Learnings" system (concept match, constraint mismatch)

CodeRabbit, a commercial PR-review SaaS, has a feature doing roughly the same job: "The AI learns your team's patterns over time, reducing false positives" via what reviews describe as a "Learnings" system that "suppresses repeated false positives". This validates that the underlying problem (calibration noise compounding across repos/teams) is real and commercially significant enough that a funded product built a feature for it.

**Does not fit your constraints as implemented**: CodeRabbit is hosted SaaS — the "learning" happens server-side across a customer's repos, which only works because CodeRabbit already has multi-repo, multi-org visibility from a central service. There's no local-first analog described in public docs. Useful as validation that the problem is real, not as an implementation template.

### Comparator 3 — none found that's both local-first and cross-project

I could not find a third tool that does local-first, no-server, cross-project calibration specifically. This appears to be a genuine gap in the public tooling landscape, not just something I missed — most "learns over time" features in this space are attached to hosted products (CodeRabbit, Qodo, Greptile) where centralization is free because the product is already centralized. Worth treating this as a point in favor of building it yourself rather than adopting something — there doesn't seem to be a local-first off-the-shelf option to borrow from wholesale.

### Feasibility & concrete proposal

Fits your constraints well. You already have the right structural piece sitting unused for this: `~/.aisdlc/harness.db`, the global SQLite index introduced in v1.4.0, currently write-only and used only for analytics (per your own capability inventory: *"harness_health.py does NOT yet query SQLite"*).

Concrete proposal: add a `capability_calibration_global` table to the existing global DB (not a new file), keyed on `(capability, project_root)`. On session start, `capability_calibration.py` checks: does this capability's local weight match (within some tolerance) its weight across N≥3 other projects in the global DB? If so, surface an advisory — not an automatic promotion — suggesting the human run an explicit promote command, mirroring great_cto's manual-approval gate. This reuses existing infrastructure, requires no new dependency, and keeps the human-approval requirement that's consistent with your own design philosophy. The "is this genuinely confirmed across projects or just coincidentally similar" question is exactly the kind of judgment call your existing `--no-trace`-style structured human gate is built for — don't auto-promote even if great_cto's README implies a lighter bar.

---

## Gap 2: Rule recidivism tracking

### Comparator 1 — pi-reflect (verified directly from source, mechanism confirmed)

Pulled the actual README. The mechanism is exactly what the brief speculated, and it's simpler than I expected: "Rule Recidivism — which sections get edited repeatedly. A rule strengthened 3+ times isn't sticking. Sections edited once and never again are resolved."

This is **section-level edit-count tracking on the target markdown file itself**, not transcript-pattern matching. Every time `/reflect` runs and edits a section of `AGENTS.md` (or `MEMORY.md`/`SOUL.md`), that's logged. If the same section gets touched 3+ times across separate `/reflect` runs, it's flagged as "not sticking." This sidesteps the hard attribution problem I raised in the brief (matching a *new* failure to a *specific prior* rule) by not attempting it — it just counts edits to the same file location over time, which is much cheaper and more robust than semantic matching, at the cost of being coarser (it tells you a section is unstable, not which specific failure pattern keeps recurring within it). Every edit is also auto-committed to git, so `git log AGENTS.md` / `git diff HEAD~5 SOUL.md` gives a free audit trail of how the file evolved — no separate logging mechanism needed.

### Comparator 2 — none found with a more sophisticated attribution mechanism

I looked for a tool that does the harder version (attributing a *new* failure instance to the *specific prior rule* that was supposed to prevent it, rather than just file-section edit counting) and didn't find one in the coding-agent space. This may mean pi-reflect's simpler approach is actually the practical sweet spot — building the harder attribution version (which is closer to what AI Delivery Control's existing `check_contradiction()` keyword-overlap heuristic gestures at, with known limitations per your own inventory) may not be worth the complexity if nobody else has solved it cleanly either.

### Feasibility & concrete proposal

Directly buildable, and cheaper than the version I proposed in the brief. You don't need to re-derive attribution from `harness_events.jsonl` pattern-matching at all — pi-reflect's approach suggests a much simpler analog:

When `distill_dream.py` writes a proposal to `.agent/state/dream_proposals/{skill}__{pattern_key}__open.md` and a human accepts it (merging the corresponding `SKILL.md`/`AGENTS.md` edit), record that merge event with the `(skill, pattern_key)` tuple in `harness_events.jsonl` (a new `event_type`, e.g. `dream_proposal_merged`). Then recidivism tracking becomes a simple count: how many times has the *same* `(skill, pattern_key)` tuple generated a **new** proposal *after* a prior merge for that same tuple? That's a direct reuse of data you already collect (the tuple is already the dream phase's own clustering key), with one new event type, no new file format, and no semantic matching required — closer to pi-reflect's "count repeated touches to the same target" simplicity than the harder attribution version I originally sketched.

---

## Gap 3: Human approval-quality drift

### Comparator 1 — great_cto's `/inbox` (mechanism unverified — flagging honestly)

I could not find published detail on what signal `/inbox` actually uses to surface "rubber-stamping drift" beyond the one-line description in its own README (*"Not deterministic — LLM-generated outputs. Every gate verdict should be sanity-checked; `/inbox` surfaces rubber-stamping drift."*). No blog post, docs page, or source excerpt I found explains the underlying signal (latency-based? comment-presence-based? approval-rate-trend-based?). **This is a case where I should say "couldn't verify" rather than guess** — unlike Gap 2, where pi-reflect's actual mechanism was published and findable, great_cto doesn't appear to document this one in public-facing material.

### Comparator 2 — academic literature on automation complacency (real, citable, relevant)

This is a case, as the brief anticipated, where the useful prior art is research literature rather than another repo:

- A peer-reviewed study found that human-in-the-loop systems increase reliance on automated recommendations while *decreasing* the accuracy of the resulting decisions — directly relevant to whether "the human is in the loop" is actually doing the job it's assumed to do. The same paper notes participants were "less likely to intervene with the least accurate recommendations" — i.e., complacency was worse exactly when it mattered most, a finding worth taking seriously given your own gate produces FAIL verdicts at varying confidence.
- There's a validated psychometric instrument for this specific phenomenon: the "Automation-Induced Complacency Potential" scale — a real, peer-reviewed measurement tool, though it measures a person's general disposition toward complacency rather than something derivable from session logs. Useful as a grounding citation for *why* this matters, not as something to implement.
- A practitioner-level pattern worth taking seriously, since it's directly implementable: "Random sampling: Routinely surface 1–5% of auto-approved cases for audit. Stratified sampling: Oversample edge cases—low confidence, high-value transactions, new customer segments." This sidesteps the hard "detect drift automatically" problem entirely — instead of trying to infer whether review quality has degraded, it just periodically re-surfaces a small random (or risk-weighted) sample of past approvals for a fresh look. Much simpler to build than a drift-detection algorithm, and doesn't depend on a signal you'd have to invent and validate.

### Feasibility & concrete proposal

The stratified-sampling pattern is the only one of the three approaches here that's both fully specified and trivially compatible with your constraints — no new signal to invent, no ML, no dependency. Concrete version: a small script, run manually or via `init_session.py` on some cadence, that pulls N past `APPROVED` specs or accepted dream-phase proposals from your existing logs (weighted toward ones touching high-risk paths, reusing `ai_review.py`'s existing `HIGH_RISK_PATTERNS` classifier as the stratification signal) and resurfaces them for a fresh look — "did this hold up." This requires no new instrumentation beyond what you already log.

### Honest opinion on scope (as explicitly requested)

I'd lean toward **not building this as a dedicated mechanism right now**, for a different reason than complexity. Your harness's design center is *governing the agent*, and every other mechanism in it — gates, traceability, calibration — has the agent as the subject under scrutiny. This gap flips that: it's the human's behavior under scrutiny. That's not wrong in principle (the cyber-defense literature above is explicit that this is a known failure mode), but it's a real shift in what the tool is *for*, and it's the one gap of the three where the comparator's own mechanism is undocumented even by its own author — which might itself be a signal that it's hard to do well, or hard to justify clearly, even for someone who built it. The stratified-sampling version above is cheap enough that I'd suggest it as a lightweight addition if you're already touching this area, but I wouldn't prioritize it as a standalone build the way I would Gaps 1 and 2, both of which have a clear mechanism, a clear data source, and a clear "this closes a real hole" case.

---

## Summary

| Gap | Buildable now? | Best path |
|---|---|---|
| 1: Cross-project calibration | Yes | Extend existing `~/.aisdlc/harness.db`; advisory-only promotion suggestion, human approves |
| 2: Rule recidivism | Yes, simpler than originally scoped | Reuse `(skill, pattern_key)` tuple already in dream phase; one new event type in `harness_events.jsonl` |
| 3: Approval drift | Possible, but lower priority | Stratified-sampling re-audit, not drift detection; honest case for deprioritizing as a dedicated mechanism |
