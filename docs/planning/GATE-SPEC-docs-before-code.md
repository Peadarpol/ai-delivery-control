# Spec: Documentation-Completeness Check for the Outer Loop (severity-tiered)

**Proposed ID**: T1-L-XX (Outer Loop series — an enhancement to `check_spec.py` (T1-L-01), plus one new primitive scoped to risk-tagged specs)
**Layer**: UNIVERSAL_CONTEXT.md (cross-project — GymBase, PunchCard, future projects)
**Type**: Severity-tiered quality check added to the existing spec gate — **not** a new HARD STOP gate, and **not** a runtime guard
**Status**: DRAFT (rev 5 — gutted to the general kernel after grounding against the framework's stated design philosophy. History of what was cut, and why, is in §7.)

---

## 1. Problem Statement — the general blind spot

A normative requirement ("the system **shall** charge a late-cancellation fee") that lives only as **prose** in a spec, and never becomes a testable acceptance criterion, is invisible to the **entire** outer-loop chain:

- `/business-analyst` only carries forward what becomes a Gherkin acceptance criterion.
- `/project-manager` (`pm_scaffold.py`) generates tasks **only** from Gherkin scenarios — it parses each `Scenario:` and emits `Implement scenario: {title}` ([pm_scaffold.py:84-86](.agent/scripts/pm_scaffold.py#L84-L86), [:139](.agent/scripts/pm_scaffold.py#L139)). No criterion → no task.
- No task → no traceable commit (`check_traceability.py`) → nothing for the acceptance gate (T1-L-05) to check intent against.

So a requirement that never crosses the prose→criterion boundary silently falls out of governance at step one. This is the BR-BKG-05 late-cancellation-fee shape, and it is **general** to anyone using the outer loop — not specific to one project's epics. Closing it strengthens the harness for the target audience (solo devs / small teams who rely on the outer loop precisely because they don't have the institutional habit of checking this by hand).

## 2. What this is, and is not

- **Is**: a completeness check — *did every normative requirement become a testable criterion that a task can cover?* — added to `check_spec.py` at the **plan gate** (checkpoint #1), where specs are approved.
- **Is not**: a new gate layer, a commit-time blocker beyond the existing chain, or any form of pre-commit/per-tool-call runtime interception (see §7 — the framework rules that out by design).

## 3. The check is severity-tiered

The two prior review findings that shaped this — *(a)* a deterministic diff needs a stable identifier, and *(b)* the framework's own calibration licenses acting on a single severe case, not only on recurrence — are **coupled**: you can only safely **block** on a signal that is **deterministic**; an advisory can tolerate fuzzy prose-matching, a hard FAIL cannot. That coupling sets the tiers:

| Spec class | Behavior | Mechanism | Cost |
|---|---|---|---|
| **Default** (any spec) | **Advisory.** Flags normative "shall/must" statements with no corresponding testable acceptance criterion. Prose-based, fuzziness-tolerant. Surfaced at spec-approval time. | New advisory in `check_spec.py` Pass 2 (which already emits `advisories`). | No new primitive. |
| **Risk-tagged** (`[HIGH_RISK_SCHEMA_CHANGE]`) | **Blocking (FAIL).** A normative requirement with no covering criterion blocks approval. | Rides the **existing** `high_risk_dba` → Pass 2 "reject with FAIL" path ([check_spec.py:357-358](.agent/scripts/check_spec.py#L357-L358), [:412-418](.agent/scripts/check_spec.py#L412-L418)). Requires the §4 stable-ID primitive so the coverage signal is deterministic enough to block on. | The one net-new primitive (§4), scoped here only. |

Severity (the licence to block) comes from the framework's own rule: the dream-phase threshold is `(count>=3 AND …) OR max_severity=="critical"` ([CAPABILITY_INVENTORY.md:518](docs/planning/CAPABILITY_INVENTORY.md#L518)), and `ai_review.py` fails closed on high-risk surfaces with no recurrence requirement. The framework acts on n=1 *when it is severe enough* — so a blocking tier on risk-tagged specs is consistent, while a blanket hard stop would not be.

## 4. The one net-new primitive: stable criterion IDs (scoped to risk-tagged specs)

The deterministic coverage diff is a set difference:

```
{normative requirements in spec} − {requirements cited by a covering criterion/task} = uncovered
```

This requires a **stable identifier** on each normative requirement. **The framework has none today** — the spec template numbers nothing (acceptance criteria are bare `Scenario: [description]` blocks — [feature_spec.md:43-50](.agent/templates/feature_spec.md#L43-L50)), and downstream linkage is by **prose title**, which breaks on any rewording ([pm_scaffold.py:84-86](.agent/scripts/pm_scaffold.py#L84-L86), [:139](.agent/scripts/pm_scaffold.py#L139)). So a stable ID is not optional decoration; it is the missing structural prerequisite for any deterministic diff.

**Scoped deliberately to risk-tagged specs only.** Requiring stable IDs on every spec would be exactly the kind of universal authoring tax the framework's cited "curse of instructions" principle warns against ([FRAMEWORK_ROADMAP.md:775](docs/planning/FRAMEWORK_ROADMAP.md#L775)). Confining the discipline to the minority of specs that already carry `[HIGH_RISK_SCHEMA_CHANGE]` ceremony makes the cost proportionate to the severity that justifies it. (Note: the `BR-XXX` naming from earlier drafts is dropped — the framework's unit is the acceptance criterion, so the ID attaches to criteria, not a parallel business-rule register.)

## 5. Mode-awareness

Follows the existing `outer_loop.mode` contract that every neighboring gate already uses ([check_spec.py:254-261](.agent/scripts/check_spec.py#L254-L261)):

- **discovery** — advisory only, both tiers (looser exploration by design).
- **incremental** — default advisory; risk-tagged blocking applies at commit/PR gate.
- **contractual** — risk-tagged blocking applies locally too; bypass unavailable.

## 6. Escape hatch

Reuses the existing mode-narrowing hatches (`--skip-spec-gate` + `SKIP_REASON`, `--no-trace`) — typed, logged, human-authored, unavailable in contractual. No bespoke hatch is introduced.

## 7. Resolved (closed) & Watched (logged, not built)

**Closed by framework design — not open questions, not deferred:**

- **Effort-waste / `PreToolUse` interception.** Removed. The README states the framework is *"Not a runtime guard — … it does not intercept tool calls, API calls, or file operations an agent makes during a session before any commit is made"* ([README.md:287](README.md#L287)), and the roadmap's governance model is *"hard enforcement at the commit boundary, convention everywhere else"* with a deliberate three-checkpoint design ([FRAMEWORK_ROADMAP.md:50](docs/planning/FRAMEWORK_ROADMAP.md#L50), [:76-80](docs/planning/FRAMEWORK_ROADMAP.md#L76-L80)). This question was carried as "open" across three earlier revisions; it was never open — it was answered in writing, on purpose. Closed.
- **Structural-surface trigger ("3+ components").** Cut entirely. It required per-project directory configuration — the exact GymBase coupling S0-24 spent effort removing ([FRAMEWORK_ROADMAP.md:149-158](docs/planning/FRAMEWORK_ROADMAP.md#L149-L158)) — and was uncalibrated against the real population. The risk-tag condition already exists in code and needs no config.
- **Coverage-diff automation level.** Resolved by the §3 severity tiers: advisory+prose by default, deterministic+blocking (on the §4 IDs) for risk-tagged specs.
- **ID family / "first HARD STOP" framing.** This is a T1-L quality-check enhancement, not a gate; the earlier "first true HARD STOP" framing was retracted in rev 3 (the framework already hard-blocks in several places).

**Watched limitation — logged, deliberately not built:**

- **The severity tier is gated on a self-applied tag.** `[HIGH_RISK_SCHEMA_CHANGE]` is text the spec-drafting agent writes into its own document. This is the **same self-exemption shape** that §2's trigger redesign was built to close — an agent under context pressure (or simply to avoid the §4 ID-tagging discipline now coupled to the tag) has a live incentive to omit it, silently routing itself to the cheap advisory-only path on exactly the spec where blocking should apply. The fix for §2 was not carried over here, and this reintroduces the vulnerability one layer up.
  - **A structural backstop exists** — `ai_review.py`'s `HIGH_RISK_PATTERNS` (paths/filenames/ADR domains) is a non-narrated classifier that does not trust the author to self-report risk ([ai_review.py:587-595](src/scripts/ai_review.py#L587-L595)).
  - **But timing forbids using it at the decision point.** Spec approval happens before any code exists; the structural classifier runs on a *diff*. So the tag is necessarily a best-effort self-assessment at spec time. The only thing that *can* be structural is a **retrospective commit-time cross-check**: if a commit touches a structurally high-risk surface but its originating spec was never risk-tagged, that is a detectable contradiction — a one-line addition at `check_traceability.py`'s existing commit-msg position, not new infrastructure.
  - **Deliberately not built now.** Building that cross-check preemptively, from a single anecdote, would repeat the exact over-fit-to-one-incident move corrected elsewhere in this spec's review. The framework's own answer is to let the dream phase observe whether it's a real pattern: if commits start landing against high-risk structural paths from specs that were never tagged, that recurring, observable signal is precisely what the dream phase exists to catch and propose a guard for. Logged here so the gap is named and watched, not silently absent.

## 8. Net build

- **New**: one advisory completeness check in `check_spec.py` Pass 2 (default tier); a stable acceptance-criterion ID convention scoped to risk-tagged specs (template + BA workflow + `pm_scaffold.py` parser preservation); wiring the risk-tagged blocking path through the existing `high_risk_dba` → FAIL branch.
- **Reused, not built**: severity-conditional FAIL path, `outer_loop.mode` machinery, the existing bypass hatches, the commit-msg hook position.
- **Not built**: runtime/PreToolUse interception (closed), structural-surface trigger (cut), the self-tag cross-check (watched).

## 9. Rollout note — staging is a resourcing decision, not an evidence one

If sequencing pressure forces shipping the **default advisory tier** before the **risk-tagged blocking tier**, that is legitimate — but it is a *resourcing* deferral (the blocking tier touches the template, the BA workflow, and `pm_scaffold.py`'s parser at once), **not** an evidence deferral. The blocking tier's justification is the framework's **severity** path (`max_severity=="critical"` bypasses the frequency requirement — [CAPABILITY_INVENTORY.md:518](docs/planning/CAPABILITY_INVENTORY.md#L518)), and BR-BKG-05 already *is* the severe n=1 case that clears it. Do **not** frame staging as "let the dream phase validate the blocking tier first" — that applies the recurrence gate (`count≥3`) to a finding already justified under the severity gate, and it recreates the original "soft locally for exactly the population that should be hard" gap in the new check. The dream-phase watch in §7 applies only to the self-tag cross-check, whose pattern is genuinely unobserved — it does not extend to the blocking tier. If you stage, say "I'm staging for hours," not "I'm waiting for evidence."

---

*The general, load-bearing value is the completeness check: ensuring a normative requirement cannot fall out of governance by never becoming a testable criterion. Everything else in earlier drafts — BR-ID naming, the structural trigger, PreToolUse — was delivery practice pulling the spec toward one project's discipline rather than fixing a general blind spot. Rev 5 keeps the kernel and the framework's grain.*
