# HIB Collision Map — 2026-07

- **Source**: stash@{0}^3:hib_collisions.txt (Session 406db7b6)
- **FB**: Framework Backlog (docs/planning/FRAMEWORK_BACKLOG.md)
- **HB**: Harness Backlog (docs/planning/harness_improvement_backlog.md)
- **Purpose**: Input evidence for T1-L-20 and AT-00.

---

--- HIB-001 ---
FB: | HIB-001 | **Scheduler shutdown RuntimeError on event loop close** | Technical bug in asyncio event loop closure. | Low | ⬜ |
HB: ## HIB-001 — Scheduler shutdown RuntimeError on event loop close
--- HIB-003 ---
FB: | HIB-003 | **Fine-tuning from dream phase trajectory data** | Long-horizon v3.0.0 consideration. | High | ⬜ |
HB: ## HIB-003 — Fine-tuning from dream phase trajectory data (long-horizon)
--- HIB-004 ---
FB: | HIB-004 | **pip-audit suppression flags duplicated across two files** | Tech debt cleanup. | Low | ⬜ |
HB: ## HIB-004 — pip-audit suppression flags duplicated across two files
--- HIB-005 ---
FB: | S0-11 | **Add "What it prevents" section to README** | Four concrete pain points mapped to framework capabilities: wrong repo commits → P-14 guard, ungoverned AI changes → adversarial gate, context loss between sessions → session lifecycle, stale architectural rules → dream phase. Source: HIB-005. | ✅ |
HB: ## HIB-005 — README lacks pain point mapping for new developers
--- HIB-006 ---
FB: - Theme 1 (Beta Installer): HIB-006 (upgrade.py), T1-B-03 (onboarding.py), S0-03 (CONTRIBUTING.md), S0-04 (issue templates), S0-05 (GitHub release), S0-06 (CI badge), S0-08 (representative skills docs), S0-09 (worked example)
HB: ## HIB-006 — bootstrap/upgrade.py design specification
--- HIB-007 ---
FB: | HIB-007 | **Skill discovery guidance** | Three-part design documentation on finding skills. | Low | ⬜ |
HB: ## HIB-007 — Skill discovery guidance (three-part design)
--- HIB-009 ---
FB: | HIB-009 | **Skill authoring: "curse of instructions" rule-count principle** | Guidance on rule bloat. | Low | ⬜ |
HB: ## HIB-009 — Skill authoring: "curse of instructions" rule-count principle
--- HIB-010 ---
FB: | S0-12 | **Fix validate.py legacy filename warning** | `validate.py` warns on absent `review_context_project.md` even when legacy `review_context.md` exists. Check for both filenames, suppress warning if either is present. Source: HIB-010. | ✅ |
HB: ## HIB-010 — validate.py warns on absent review_context_project.md (legacy name)
--- HIB-011 ---
FB: - Additional delivered: HIB-011 (Task Magnitude Auto-Classification), BUG-05 (Dynamic routing path resolution), BUG-07 (post-commit hook), BUG-09 (upgrade.py version extraction), HIB-028 (checksums --project flag)
HB: ## HIB-011 — Task magnitude classification at session start
--- HIB-022 ---
FB: | HIB-022 | **Automatic framework version bump** | Automate bumping versions. | Medium | ⬜ |
HB: ## HIB-022 — Automatic framework version bump
--- HIB-023 ---
FB: | HIB-023 | **ADR domain validation in environment checks** | Ensure ADR domains are valid. | Low | ⬜ |
HB: ## HIB-023 — ADR domain validation in environment checks
--- HIB-026 ---
FB: | HIB-026 | **Typed memory entry classification for governance events** | Adding `decision` or `checkpoint` to memory. | Low | ⬜ |
HB: ## HIB-026 — Typed memory entry classification for governance events
--- HIB-027 ---
FB: | HIB-027 | **.agent/memory/ directory separation** | Separating memory from operational state. | Medium | ⬜ |
HB: ## HIB-027 — .agent/memory/ directory separation
--- HIB-028 ---
FB: NOT FOUND
HB: ## HIB-028 — generate_checksums.py --verify misleading output on customised installations
--- HIB-029 ---
FB: | HIB-029 | **Session-end lightweight observation capture** | Writing 3-5 bullet raw observations. | Low | ⬜ |
HB: ## HIB-029 — Session-end lightweight observation capture
--- HIB-030 ---
FB: | HIB-030 | **Path-based skill activation in skill_ownership.yaml** | Activate skills based on directory. | Medium | ⬜ |
HB: ## HIB-030 — Path-based skill activation in skill_ownership.yaml
--- HIB-031 ---
FB: | HIB-031 | **Sub-agent exploration patterns in workflow documentation** | Add sub-agent guidance. | Low | ⬜ |
HB: ## HIB-031 — Sub-agent exploration patterns in workflow documentation
--- HIB-032 ---
FB: | T1-K-05 | **threat-model.md as first-class governance artifact** | Artur Huk "Context as Code" (O'Reilly, June 2026) identifies the threat model as a distinct first-class governance artifact separate from architectural boundaries. Your framework currently combines threat-model content (cross-tenant leaks, UoW bypass, mass assignment, RBAC escalation) with architectural boundary content in review_context_project.md. Separate these into: (1) review_context_project.md — architectural invariants and boundary rules (what the system must always do); (2) threat_model.md — adversarial scenarios and abuse paths (what the system must never allow). The gate system prompt loads both. The key addition: each threat in threat_model.md is paired with a deterministic architecture_checks.py rule — the LLM is guided by the Markdown, the AST check enforces it mechanically. This is the bridge between the current framework and the enterprise product positioning — threat_model.md + deterministic rules is what enterprise procurement recognises as policy-as-code without requiring HIB-032's Starlark complexity. Delivers immediately for GymBase: document the four critical threat patterns as explicit threat_model.md entries paired with architecture_checks.py rules. Source: Artur Huk, O'Reilly Radar, June 2026. | Medium | ⬜ |
HB: ## HIB-032 — Policy-as-code governance layer (Starlark) as long-horizon consideration
--- HIB-034 ---
FB: | T1-L-20 | **Structured schema and enforcement for decisions_log.md** | Problem: decisions_log.md has no programmatic reader or writer anywhere in the codebase — confirmed by direct inspection of harness_utils.py, audit_logger.py, and check_state_freshness.py (which only checks the file's mtime, never its content), and by confirming distill_dream.py — the repo's actual learning-flywheel implementation — never ingests it, despite it being a rich decision-history source. It is pure agent-written prose governed by convention (likely the T1-L-02 /ba workflow instruction), not by any enforced shape. Concrete costs observed: verifying a specific historical decision (the aa40ad2 ratification, investigated this session) required manual git log -p excavation instead of reading a structured field; the file also shows narrow textual corruption in at least one entry (a leading "t" character replaced by a tab character), consistent with unvalidated free-text writes.<br><br>Existing partial infrastructure: decisions_log_archive.md already exists (size-triggered archival per HIB-034/035), but carries the same unstructured convention forward — ## Session N headers, no dated reasoning note, no schema.<br><br>Proposed direction: a fixed row schema — Date \| Direction \| Artifact/Topic \| Source \| Evidence \| Decision \| Owner \| Notes — with Evidence required to be checkable (a commit SHA, a quoted excerpt, a file:line reference), not a bare assertion. Archive entries should carry a dated reason plus the surviving principle, not just a batch dump.<br><br>Required before implementation — research pass:<br>1. Read what the /ba workflow (T1-L-02) currently instructs agents to write, so the new schema supersedes it cleanly.<br>2. Compare against Architecture Decision Records (ADRs, Nygard's convention) as established prior art, since much of this file's actual content already is architecture decisions. Decide whether decisions_log.md should become individual ADR files instead of one running ledger, or keep a single-ledger-row schema — these aren't obviously compatible; pick deliberately.<br>3. Decide whether this becomes code-enforced (a log_decision() function analogous to log_harness_event()) or stays convention-governed with a stricter template.<br>4. Flag (don't resolve here) whether feeding decisions_log.md into distill_dream.py's pattern-mining belongs in this ticket or a follow-up.<br><br>Related, explicitly out of scope: T2-A-04 (cross-project MCP-queryable decisions log) — this ticket is a prerequisite/enabler for that, not a merge.<br><br>Priority: unscored, pending the research pass above. | TBD | ⬜ |
HB: ## HIB-034 — AGENTS.md length audit and line ceiling enforcement
--- HIB-036 ---
FB: NOT FOUND
HB: ## HIB-036 — Atomic config migration rollback
--- HIB-037 ---
FB: NOT FOUND
HB: ## HIB-037 — Pre-flight installation state validation before migration
--- HIB-038 ---
FB: NOT FOUND
HB: ## HIB-038 — Migration chain contiguity assertion
--- HIB-039 ---
FB: NOT FOUND
HB: ## HIB-039 — Replace string-based YAML injection with ruamel.yaml
--- HIB-040 ---
FB: | HIB-040 | **Context-injection attack surface** | Governance layer as a novel supply chain threat. | High | ⬜ |
HB: ## HIB-040 — Context-injection attack surface: governance layer as a novel supply chain threat
--- HIB-044 ---
FB: | HIB-044 | **T1-E-01 sandboxing requirement for Tool ABC subclasses** | Explicit tool sandboxing rules. | High | ⬜ |
HB: ## HIB-044 — T1-E-01 sandboxing requirement for Tool ABC subclasses
--- HIB-045 ---
FB: | HIB-045 | **False-positive rate as a proactive harness health metric** | Analytics and telemetry. | Medium | ⬜ |
HB: ## HIB-045 — False-positive rate as a proactive harness health metric
--- HIB-048 ---
FB: | T1-G-12 | **AT/FM vocabulary injection in review_context_universal.md** | Harish Kumar "The Engineer's Map Field Edition" (2026, CC BY 4.0) provides a vocabulary of 10 Architecture Tradeoffs (AT1–AT10) and 12 Failure Modes (FM1–FM12) designed for injection into AI coding tool context files. Adding the AT/FM code tables to `review_context_universal.md` gives the gate's reviewing model a compressed, precise vocabulary for naming findings. A finding expressed as "FM9: silent data corruption in log_unauthorized_access on exception path" is more stable across runs than a prose description of the same concern. Directly addresses the non-determinism problem (HIB-048) — named codes are more likely to be stable across LLM evaluation runs than unanchored prose descriptions. Benefit: gate findings become specific claims rather than gestures, more educational for the developer, and more consistent across evaluation runs. Also added: GymBase archetype classification (A3 Marketplace & Transaction) so the reviewing model weights FM4 and FM10 most heavily for GymBase diffs. Decision block format documented as ADVISORY check for ADR completeness. Source: computingseries.com (CC BY 4.0). | Low | ✅ (v1.3.3 — delivered 2026-06-07) |
HB: | HIB-048 | **Gate findings non-deterministic across rebuttal runs** | The gate re-evaluates the diff on each rebuttal run. LLM temperature >0 means finding descriptions shift between runs under the same FID labels. In the SPEC-124 incident: FID-1 was "mass assignment" on Run 1 and "authorization gap on notes endpoint" on Run 3. Same diff hash, different findings. The developer wrote correct evidence for the Run 3 findings and was blocked by the limiter that did not account for the shift. Fix: Freeze finding text at first evaluation in `.agent/state/gate_findings_{session_id}.json`. Rebuttal evaluation assesses developer evidence against the frozen finding text only — the gate does not re-read the diff during rebuttal evaluation. For REMEDIATED type (HIB-049), the gate checks the current diff to confirm the concern is gone, but the frozen text remains the reference. Dependency: HIB-047 (the same `gate_findings` file serves both fixes). | High | ⬜ v1.3.3 |
--- HIB-052 ---
FB: | HIB-052 | **session_id "unknown" clustering in session-counting code** | Found during v1.3.4's dream phase validation. A subset of `harness_events.jsonl` / `session_ledger.jsonl` entries are written with `session_id: "unknown"` rather than the active session's UUID, causing these entries to cluster under a single synthetic "unknown" session in any session-counting or per-session aggregation. This degrades the accuracy of session-based pattern detection (T1-D-03) and any future per-session evidence gathering. **Scoped into T1-G-11 (v1.4.0)**: T1-G-11's evidence-gathering pre-context reads session/event data to build pytest-collect, co-change, and TODO-delta signals — this data must be correctly attributed by session_id before that pre-context is trustworthy. As part of T1-G-11 implementation: (1) audit the call sites that write `harness_events.jsonl` and `session_ledger.jsonl` entries to find where `session_id` is falling back to `"unknown"` (likely a missing read of `session.json` at write time, or a stale/uninitialised session context); (2) fix the fallback so entries always carry the active session's UUID, or are explicitly flagged as pre-session-init events with a distinguishable marker (not a shared `"unknown"` bucket); (3) add a regression test asserting no new `session_id: "unknown"` entries are written under normal session lifecycle. Do not fold into T1-H-10 — that item's confidence tagging is for repo-map/co-change structural signals, not session attribution, and has no direct dependency on this fix. **Delivered in b645830 (v1.4.0)**: `harness_utils.py`, `roster_builder.py`, `audit_logger.py` patched; `"pre-session-init"` marker reserved for genuine pre-init events; regression test added. | Low | ✅ (v1.4.0) |
HB: ## HIB-052 — session_id: "unknown" clustering undercounts dream phase appearance_rate
--- HIB-055 ---
FB: | T1-L-13 | **Decision block format for ADR annotations** | The decision block pattern (Harish Kumar "The Engineer's Map", 2026) formalises the ADR annotation format the framework already requires: `Decision / Tradeoff: AT[N] — choosing [pole] because [reason] / Exposes: FM[N] — [what could go wrong] / Mitigation: [how addressed]`. Currently ADR annotations are prose — the gate checks whether an ADR exists but not whether it names the tradeoff and the exposed failure mode. Enhance: add the decision block as the required format for new ADR frontmatter in `docs/adr/`. Update the `/architect` workflow to produce decision blocks automatically. The gate checks (via `review_context_universal.md` ADVISORY rule) that commits introducing new architectural patterns include a decision block in the referenced ADR. A decision that cannot name its AT tradeoff or its exposed FM is an incomplete ADR — flag as ADVISORY, not FAIL. (ADVISORY rule carved out to T1-L-13a; v1.4.1 shipped the `/architect` scaffold + deterministic `check_adr_decision_blocks()` only.) Dependency: T1-G-12 ✅ (AT/FM vocabulary in review_context) — note: T1-G-12's vocabulary did not reach the reviewer (HIB-055); fixed in v1.4.2. | Low | ✅ (v1.4.1) |
HB: NOT FOUND
--- HIB-056 ---
FB: | T1-D-07 | **Rule recidivism tracking** | The dream phase (T1-D-03 ✅) proposes a rule change once a failure pattern crosses the evidence threshold, and a human merges it into a skill file (SKILL.md/AGENTS.md). Nothing currently checks whether the merge actually *stopped* the recurrence — a rule can look correct and not work, with no signal that it didn't. **Why valuable now and at solo scale**: this needs only single-project session history (no cross-project/cross-developer data) and is, if anything, *more* valuable at solo scale than at team scale — a solo developer has no peer redundancy to independently notice a "fixed" rule didn't take, so the dream phase is the only thing watching for that failure. **Proposed mechanism**: reuse the existing `(skill_name, pattern_key)` tuple — already the dream phase's clustering key (`distill_dream.py`), so no new vocabulary. On proposal acceptance/merge, write a new `dream_proposal_merged` event to `harness_events.jsonl` carrying that tuple. Recidivism = count of *new* proposals generated for the same tuple after a prior merge event for that tuple. No new file format; one new `event_type`. **Comparator (verified, not inferred)**: jo-inc/pi-reflect tracks edit-count on the *target file section* ("a rule strengthened 3+ times isn't sticking; sections edited once and never again are resolved"), sidestepping the hard transcript-level attribution problem by not attempting it — coarser but robust and cheap. **Open question for implementation**: flagging threshold — reuse the dream-phase `count ≥ 3` convention, or set a lower bar since a fix that silently failed plausibly deserves earlier flagging than a fresh unaddressed pattern. **Dependencies**: none beyond delivered dream-phase infrastructure — T1-D-00 ✅, T1-D-03 ✅, and the contradiction-check path (T1-I-05, integrated into T1-D-03; standalone status marker is ⬜ — marker drift tracked as HIB-056). Source: comparator investigation vs great_cto / pi-reflect / CodeRabbit, 2026-06-22 — full findings: [`research/three-gaps-findings.md`](research/three-gaps-findings.md) (Gap 2). | Low | ⬜ |
HB: ## HIB-056 — T1-I-05 status-marker drift (⬜ vs treated-as-delivered)
--- HIB-058 ---
FB: | T1-L-18 | **Documentation-completeness check for the outer loop (severity-tiered)** | A completeness check added to `check_spec.py` Pass 2 - advisory by default (prose-based, flags normative "shall/must" statements with no corresponding testable acceptance criterion), blocking (FAIL) only for risk-tagged specs (`[HIGH_RISK_SCHEMA_CHANGE]`), gated on a new stable acceptance-criterion ID primitive scoped only to risk-tagged specs (to keep the authoring cost proportionate). **Core mechanism**: for any SPEC ID referenced in a commit, enumerate `Gherkin Scenario:` blocks in the spec's acceptance-criteria section and verify that a named test function/file exists for each. Implementation options: (a) a new `check_scenario_coverage.py` gate, or (b) an extension to `check_spec.py` Pass 2. **Explicitly not**: a new HARD STOP gate layer, runtime/PreToolUse interception (closed by design per README's "not a runtime guard" philosophy), or a universal per-spec ID requirement (rejected as a blanket authoring tax). **Known limitation**: the risk tier is gated on a self-applied tag the drafting agent writes into its own spec - a structural backstop via `ai_review.py`'s `HIGH_RISK_PATTERNS` classifier exists for retrospective cross-checking, but isn't wired in yet; deliberately deferred to the dream phase to observe whether it's a real recurring pattern before building it. **Evidence base**: HIB-058 (GymBase SPEC-127 pre-Phase-2 audit, 2026-07-04) - the `cancelled_timely` refund scenario was fully specified in SPEC-127 SS4 but never implemented; multiple commits passed the traceability gate referencing SPEC-127 while leaving the entire refund path unimplemented. Caught by manual code audit, not by any automated check. **Design history**: rev-5 draft from the 2026-06-21 session; reasoned through five review rounds before formal ID assignment (2026-07-04). Cross-reference: HIB-058 is the supporting evidence case - do not develop as independent efforts. | Low | ⬜ |
HB: ## HIB-058 — check_traceability.py does not verify Gherkin scenario coverage
--- HIB-062 ---
FB: | HIB-062 | **Traceability ID coverage regex expansion** | Extend `check_traceability.py` regex to accept `T1-\w+-\d+`, `HIB-\d+`, and `BUG-\d+` alongside `SPEC-\d+`. Layer-2 gap: the hook physically checks for `docs\planning\specs\<ID>.md` — HIB/BUG/T1 refs should instead check backlog files. | ✅ |
HB: ## HIB-062 — Large diffs failing open (DIFF_TOO_LARGE_FAILOPEN) is a critical gate design gap
--- HIB-067 ---
FB: | T1-K-13 | **--no-trace authentication gap** |The `--no-trace` flag has no authentication; any process can bypass the traceability hook by including the flag with a 10-character reason string, with no verification of who or what invoked it. This represents a governance gap where an unauthenticated bypass is available to any agent or script, rather than just the accountable human. (See HIB-067 for a documented incident of agent abuse of this gap). | Medium-High | ⬜ |
HB: ## HIB-067 — Agent self-authorized --no-trace bypass twice in one session, including once during correction of the first bypass, despite a valid non-bypass path being available.
