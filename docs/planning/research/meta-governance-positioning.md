# Positioning Paper: Meta-Governance Capability Cluster

**Artifact type:** Positioning paper — not a plan, not a specification, not backlog items. Written to be argued with, mined (backlog items and specs spring from it, citing it), and eventually superseded or absorbed — never "implemented" or "done." Deliberately carries minimal governance: versioned and supersedable, but no gates and no sign-off. It sits at the ungoverned end of the artifact chain: **positioning paper (argued) → backlog items (prioritised) → specs (gated) → commits (enforced)** — each hop adds governance weight.
**Status:** Draft, under discussion
**Date:** 2026-07-08
**Origin:** External gap-analysis report (largely discarded — see §10) → adversarial review of that report → three-way convergence between the report's reviewer, maintainer-side dependency analysis, and independent assessment, plus a product-phase (Individual/Team/Enterprise) framing added in discussion. This paper is the considered artifact from that exchange.
**Related:** HIB-032 (policy-as-code, v3.0.0 direction), HIB-033 (durable differentiators), HIB-003/007/029 (dream phase), T1-H-09 (ADR annotation density), S0-21 (archived AI SBOM export note)

---

## 1. Positioning

AI Delivery Control today is a set of enforcement mechanisms: hard commit-boundary gates, a compliance-grade audit trail, a self-improvement loop, and the rebuttal protocol (HIB-033). This paper proposes the next pillar: evolving from a collection of enforcement mechanisms into a **governance operating model**.

The claim, however, must be stated per product phase — because it is only a *sales* claim at one end of the scale:

| Product phase | The honest claim |
|---------------|-----------------|
| **Individual** | Useful, working code — reliably and quickly. Governance is the means, and it is invisible when working. The individual's stake in this cluster is narrow but real: *trusting the gate so they can go fast* (no silent control failures), and a harness that learns from their own failure patterns. |
| **Team** | Shared rules need owners, conflict checks, and blind-spot lists. Rules now accumulate from multiple people; "who approved this rule" has a meaningful answer (a teammate); coverage gaps become a tech-lead artifact. |
| **Enterprise** | The harness governs code delivery, **can prove it governed**, and **governs its own governance**. Who approved it, is it covered, does it conflict, can I prove it ran, and is it learning safely — territory most AI-governance frameworks never reach ("does this rule exist?" is where they stop). |

The architectural insight underneath: these are not five separate features. Once controls become explicit, versioned, attributable, evidence-backed **objects**, every capability below becomes a different *view over the same governance graph* rather than a new subsystem.

## 2. Scope origin

This paper descends from an external gap analysis whose findings were roughly 70% out of scope (MLOps platform responsibilities, DevSecOps platform responsibilities, and recommendations for tooling already shipped in `bootstrap/templates/`). After adversarial filtering, the surviving strategic items were:

- **A.** Supply-chain provenance (SBOM, signing, SLSA attestation)
- **B.** Policy-as-code with versioned, testable governance rules
- **C.** Compliance/control mappings (NIST SSDF, ISO 27001, PCI DSS)

The reviewer then identified five further capabilities (#1–#5 below). Verification against the repo showed three of the five are **embryonic, not absent** — partial implementations exist but lack the substrate to mature.

## 3. Capability inventory

Taxonomy: **Absent** (no concept, no implementation, no roadmap) · **Embryonic** (concept and partial implementation exist, substrate missing) · **Mature** (end-to-end with governance around it).

| # | Capability | Verified current state | Classification | Product phase |
|---|------------|------------------------|----------------|---------------|
| A | Release provenance (SBOM / signing / SLSA) | Commit-level provenance exists: `AI-Assisted` / `Harness-Version` / `Session-ID` git trailers (AGENTS.md §9.1) + `session_ledger.jsonl`. Release-boundary provenance absent. S0-21 shows it was once scoped and dropped. | Embryonic — extend commit provenance up to the release boundary | Team/Enterprise; mild **Individual** value for open-source publishers as registries push attestation |
| B | Formal control model + policy representation | Rule identity exists (H/S/C/G IDs, legacy P-series map in `governance.md`). Stated v3.0.0 direction (HIB-032: Starlark/OPA). No machine-readable control catalog. | Embryonic / roadmapped | **Phase-agnostic substrate** — belongs to no tier; makes the Enterprise tier possible without a rewrite (see §5) |
| C | Compliance mappings | HIB-032 names formal control mapping. Nothing implemented. | Roadmapped, absent | **Enterprise** only |
| 1 | Rule lifecycle (proposed→approved→active→retired, owner, supersession) | Identity + partial history via git and `decisions_log`. No lifecycle state, no owner field, no registry. | Mostly absent | **Team** (owner = a teammate) → **Enterprise** (approval authorities, boards) |
| 2 | Control assurance / evidence graph | Harness instruments its own gate richly (`harness_events.jsonl`, ~10 writers, verdicts + `GATE_SKIPPED`). Delegated tools (bandit, gitleaks, pip-audit) run as pre-commit hooks with **no captured results** — the harness knows its AI gate ran, not that gitleaks ran, at what version, with what exit code. | Embryonic — cheapest real gap to close | **Individual** in lite form ("no silent control failures" — a silently-skipped hook gives false confidence) → **Enterprise** for the full evidence graph |
| 3 | Governance coverage analysis | T1-H-09 is single-dimension coverage (ADR annotation density). No multi-domain control coverage. Directly attacks the documented "gate's own blind spots" boundary (Scope-and-Boundaries.md). | Embryonic (one dimension roadmapped) | **Team** — blind-spot lists are a tech-lead artifact |
| 4 | Policy conflict detection | §5 escalation lists "contradictory decision-log entries" as a human trigger. No automation. | Absent | **Team** — conflicts only accumulate when multiple people add rules |
| 5 | Governance evolution (class-aggregated, process-level proposals) | The dream phase (`distill_dream.py`, HIB-003/007/029) already proposes rule/skill additions from session history. Step-up: aggregate by failure class, propose process changes rather than lint rules. | Embryonic — extension, not new | **Individual** already (learns from your own failures); constitutional constraints (§7) are phase-agnostic and cheap |

## 4. Architecture: the formal control model is the keystone

An earlier draft of this analysis named policy-as-code (B) as the keystone. The corrected framing: **the keystone is a formal control model; policy-as-code is one implementation of it.** Starlark, OPA/Rego, Cedar, a YAML DSL, or a relational schema with an evaluation engine could all carry the same model. Choosing the model first preserves flexibility on representation.

The control object, approximately:

```
Control {
    id                  # stable identity (migrates from existing H/S/C/G IDs)
    owner               # accountable human/role
    scope               # where it applies
    preconditions       # when it applies (enables conflict analysis)
    severity
    tier                # constitutional | governance | skill  (see §7)
    supersedes / superseded_by
    lifecycle_state     # proposed → approved → active → retired
    evidence_required   # what must execute (e.g. gitleaks, bandit, harness review)
    evidence_collected  # what did execute: version, timestamp, exit code, artifact hash
    mappings            # NIST SSDF / ISO 27001 / PCI DSS control IDs
    provenance          # why it exists: origin evidence, approver, date (see §8)
}
```

Once controls are data instead of prose, the downstream capabilities become **computation rather than heuristics**:

```
        Formal Control Model  (keystone — phase-agnostic substrate)
                │
                ▼
        Policy Representation  (OPA / Starlark / DSL — deferred choice)
                │
                ├── C   Compliance mapping      (needs stable IDs to map)        [Enterprise]
                ├── #2  Evidence graph          (needs IDs to attach evidence to) [Individual-lite → Enterprise]
                ├── #3  Coverage analysis       (needs a denominator)             [Team]
                ├── #4  Conflict detection      (needs modelled preconditions)    [Team]
                └── #1  Lifecycle               (needs objects to version)        [Team → Enterprise]

        #1 Lifecycle ──safety-gates──▶ #5 Governance evolution                    [Individual today]
        A  Release provenance — parallel track, release boundary, no dependency on B
```

Why each dependency is real, not preferential:

- **C** has nothing to map to/from without a machine-readable catalog.
- **#3** has no denominator without one. "Security controls: 82%" is unfalsifiable unless the universe of controls that *should* exist is defined. Coverage without a catalog is theatre.
- **#4** cannot distinguish a genuine contradiction from a scoped exception without modelled preconditions. The canonical example — "every change requires architect approval" vs "hotfixes bypass approval" — is *not* a conflict; it is correct conditional precedence. Naïve detection fires a false positive on it. Real conflict detection needs scope, predicates, precedence, inheritance, and exception hierarchy — closer to SAT solving than string matching.
- **#2** needs a stable control identity to attach evidence to (resolved pragmatically in Phase 0, below).
- **#1 gates #5** as a safety requirement, not a convenience: an adaptive system that proposes *process* changes (not just lint rules) has real leverage to reshape its own constraints. HIB-029 already flags the self-serving-proposal risk. The harness must not propose "introduce a mandatory auth threat-model gate" unless a rule-approval lifecycle with a named human owner sits on the other side. **#1 is the seatbelt for #5.**

## 5. The product-phase principle

This cluster sits mostly at the Enterprise end of the Individual → Team → Enterprise scale, which creates a trap: building Enterprise machinery ahead of Team adoption is classic premature scaling. An Individual user does not care about the governance of the harness so long as it produces useful, working code reliably and quickly.

The escape is that the keystone can be adopted incrementally. Hence the governing principle for this whole cluster:

> **No capability ships ahead of the product phase that demands it — except the v0 control model, which is cheap, serves the Individual tier immediately (assurance-lite), and quietly lays the Enterprise rails.**

The control model is the one investment that must be made early, because retrofitting stable control identity under years of accumulated evidence and mappings is the expensive path. Everything else waits for demand:

| Delivery phase | Contents | Product phase served |
|----------------|----------|---------------------|
| **Phase 0 — quick win** | Control assurance lite (#2): `control_execution` events in `harness_events.jsonl` per delegated hook (tool, version, exit code, timestamp, artifact hash), built as the **first consumer of a v0 control model**. `control_id` populated from existing H/S/C/G IDs (or tool names), designed to migrate to catalog IDs — no rework. Individual-facing value: *the gate never silently skips*. This is the shift from policy enforcement ("harness: PASS") to evidence-based governance ("Control H-021 — evidence: gitleaks ✓ v8.18.2 exit 0 …"). | **Individual** |
| **Phase 1 — keystone** | Formal control model (B): schema, H/S/C/G migration, deferred representation choice. Existing HIB-032 direction with a sharper model/representation split. | Substrate (all) |
| **Phase 2 — Team capabilities** | Lands with Team adoption, in parallel once B exists: lifecycle (#1, owner = teammate), coverage (#3), conflict detection (#4, advisory-only v1 — see §9). | **Team** |
| **Phase 3 — Enterprise, demand-driven** | Compliance mapping (C), full evidence graph and retention, approval authorities on #1, and governance evolution (#5) — safety-gated behind #1, strictly human-in-the-loop, constitutionally constrained (§7). | **Enterprise** |
| **Parallel track — any time** | Release provenance (A): different boundary (release, not commit), no dependency on B, lowest conceptual novelty (Syft/CycloneDX, Sigstore, SLSA). Do **not** sequence behind the control-model work. Problem statement: extend commit-level provenance (git trailers + session ledger) up to the release boundary — *"can I prove this released artifact came from the approved governed workflow?"* | Team/Enterprise (+ Individual OSS publishers) |

## 6. Constitutional tier

Governance evolution introduces a hierarchy:

```
Constitution  →  Governance controls  →  Skills  →  Reviews  →  Commits
```

The dream phase may propose modifications to governance controls and skills — **never to the constitutional tier**. Two hard requirements:

1. **Structural, not conventional.** The proposal mechanism must be *unable* to emit proposals targeting `tier: constitutional` controls — enforced in the control model and the proposal pipeline, not by prompt instruction. A convention-based boundary is exactly what a self-optimising system erodes first.
2. **Human-only amendment.** Constitutional controls change only through an explicit human amendment process, recorded with full provenance.

Without this, the system gradually optimises away the very controls intended to constrain it. Note this protection is phase-agnostic and cheap: even the Individual tier benefits, since the dream phase already proposes rules today — the "human owner" solo is simply the individual.

## 7. Acceptance criterion: governance provenance

Governance provenance is deliberately **not** a workstream. It is the acceptance test of the whole architecture: if the capabilities above are truly views over one governance graph, then for any control the harness can answer, end-to-end:

> **Why does H-042 exist?**
> Introduced 2026-09-14 · Reason: repeated authentication failures (37 sessions, 12 failures) · Approved by: Architecture Review Board · Supersedes: H-017 · Mapped to: NIST SSDF PW.4, ISO 27001 A.8 · Last evidence: 2026-10-02, all required tools executed ✓

When that query resolves from the graph alone, the program is done. Framing it as a feature would invite scope; framing it as the exit criterion prevents it.

There is a recursion worth noting: the harness already enforces traceability downstream (commit → spec → requirement). This paper extends the chain one link upstream — backlog item → positioning paper. Backlog entries mined from this document should cite it, meaning "why does HIB-0xx exist?" resolves to *this paper, this argument*. The paper is an instance of its own acceptance criterion before the feature exists.

## 8. Risk register

| Risk | Where | Mitigation |
|------|-------|------------|
| **Premature enterprise scaling.** Building compliance mapping, approval boards, and evidence retention before Team adoption exists. | Whole cluster | The §5 principle: nothing ships ahead of the phase that demands it, except the v0 control model. Phase 3 is demand-driven, not calendar-driven. |
| **Goodhart on coverage.** A scalar "82%" becomes a target: add cheap controls to lift the number. Governance is not additive — one missing control (e.g. approval authority) can invalidate an entire domain. | #3 | Never report a headline percentage. Report *which controls are missing in which domain*, as actionable lists. A scalar is executive wallpaper. |
| **Conflict-detection false positives.** Precedence and scoped exceptions look like contradictions to naïve matching. A noisy oracle discredits the capability. | #4 | v1 is advisory-only: pairwise scope-overlap heuristics flag *candidate* conflicts for human review. Full predicate modelling deferred until B's precondition model is proven. |
| **Small-N statistics + self-serving proposals.** "73% of failures relate to auth" from a handful of sessions is not evidence; and HIB-029 flags agents proposing rules that loosen their own constraints. Small-N is *worse* at the Individual tier. | #5 | Strictly human-in-the-loop proposals; minimum sample thresholds; #1 lifecycle as hard prerequisite at Team+ scale; constitutional tier untouchable (§6). |
| **Migration break in evidence identity.** Phase 0 evidence attached to ad-hoc IDs could orphan when the catalog lands. | #2 → B | `control_id` field designed for migration from day one (H/S/C/G IDs now, catalog IDs later). |
| **A gets sequenced behind B by inertia.** | A | Explicitly independent parallel track; different boundary; mature off-the-shelf tooling. |
| **Premature representation lock-in.** Committing to OPA vs Starlark vs DSL before the model is defined. | B | Model first, representation second (§4). Representation is a deferred, reversible decision. |

## 9. Non-goals

Inherited from the discarded portions of the originating report, recorded here to prevent future scope creep. The harness is a governance harness that **composes with** engineering tooling; it does not implement it. (Terraform doesn't implement AWS; it orchestrates AWS. The harness doesn't implement Gitleaks; it verifies Gitleaks ran.)

Out of scope, permanently unless the project's mission changes:

- ML lifecycle: model registries, drift detection, experiment tracking, explainability (SHAP/LIME), fairness testing, dataset governance. The harness governs AI-assisted *software delivery*, not model training. Orthogonal concerns.
- Platform ownership: CI/CD servers, IAM, secrets vaults, SIEM, runtime monitoring/observability. The harness requires and evidences these; it does not become them.
- Re-shipping delegated scanners: SAST, dependency scanning, secret scanning, and linters already ship in the installed pre-commit template (`bootstrap/templates/`). Any future evaluation of the harness must assess the installed artifact, not the repo root.

## 10. Open questions

1. **Policy representation** — Starlark, OPA/Rego, Cedar, or a custom DSL/schema. Deferred until the control model stabilises; the model must be representable in at least two candidates before choosing (proof of the model/representation split).
2. **Catalog location and format** — single versioned file vs directory-per-domain; relationship to existing `governance.md`.
3. **Owner model** — individual, role, or board; how ownership interacts with the constitutional amendment process, and how it degrades gracefully to the solo case (owner = the individual).
4. **Evidence retention** — how long `control_execution` evidence is kept, and whether it feeds the release-provenance attestations (the one plausible future coupling between A and B).
5. **Team-phase trigger** — what adoption signal moves the cluster from Phase 0/1 into Phase 2 (multiple contributors to a governed repo? explicit team-mode configuration?).
6. **Backlog decomposition** — this paper should be decomposed into HIB/FRAMEWORK_BACKLOG entries in the repo's existing format, each citing this paper, with the B-keystone dependency and the #1→#5 safety gate noted explicitly.

---

*Provenance of this paper: synthesised 2026-07-08 from an external gap-analysis report (methodology flaw: evaluated repo root rather than `bootstrap/templates/`; ~70% of recommendations out of scope), the reviewer's retort and subsequent refinements (embryonic taxonomy, control model as keystone, constitutional constraints, governance provenance), maintainer-side dependency analysis (the DAG, the #1→#5 safety gate, verified repo state), and a product-phase framing (Individual/Team/Enterprise) added in discussion. Recorded here so the paper itself satisfies the standard it proposes.*
