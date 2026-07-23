# AI Delivery Control — Framework Roadmap

**Status**: Active Development
**Current Version**: 1.4.11
**Target Release**: v1.4.12 (Installer & validator onboarding hardening shipped in v1.4.11; see decisions_log.md 2026-07-23)
**Last Updated**: 2026-07-24 (v1.4.11 shipped; installer & validator onboarding hardening, sandbox dry-run, API preflight)

---

## Vision

AI Delivery Control is a governance harness for AI-assisted software delivery. It sits between the human architect and the AI coding agent — not replacing human judgment, but ensuring it remains in the loop at the moments that matter.

Most AI delivery frameworks optimise for autonomy. This one optimises for accountability. Agents are capable but not accountable. Humans remain responsible for what ships. The harness is the mechanism that keeps it that way without making it burdensome.

**You govern. Agents deliver.**

The framework is designed for developers and teams who need to explain their delivery decisions — to a client, a technical lead, or themselves six months later. It is particularly relevant for regulated industry contexts, though formal compliance control mappings are planned for v2.0.0 and are not a current capability.

---

## Scope

### What This Framework Governs

- **Delivery execution**: Session lifecycle, workflow discipline, pre-commit AI adversarial review, architecture boundary enforcement, co-change blast radius estimation.
- **Commit governance**: Every commit passes a structured gate with typed verdicts (PASS / WARN / FAIL), policy notes explaining what was checked, and a persistent audit trail.
- **Self-improvement**: The harness observes its own sessions, detects recurring failure patterns, and proposes skill improvements for human approval. The framework improves itself over time.
- **Operational readiness**: Before any promotion to production, an ORR checklist confirms the release meets governance standards.
- **Requirements governance** *(v1.2.0)*: Specification quality gate, business-analyst workflow, requirement → commit traceability, and acceptance gate.

### What This Framework Does Not Govern (Explicitly Out of Scope)

- **Production monitoring and alerting**: Observability tooling, dashboards, and on-call processes are outside scope. The framework ends at the commit and the ORR sign-off.
- **Incident response**: The framework provides an incident → backlog pipeline (T1-L-07) so production events feed back into governed delivery, but real-time incident response is not governed.
- **Infrastructure provisioning**: Cloud configuration and infrastructure-as-code are outside scope. The framework governs the code that gets deployed, not the infrastructure it runs on.
- **Model selection and fine-tuning**: The framework uses LLMs as review tools. It has no opinion on which model to use beyond the model tiering configuration.
- **Compliance control mappings**: SOCI Act, ISM, and PSPF control mappings are planned for v2.0.0. Until those exist, the framework is relevant to regulated industries but not formally mapped to any compliance standard.

---

## The Governance Model

### Hard Enforcement vs Convention

**Honest declaration**: The pre-commit AI review gate and architecture boundary checks are the only fully hard-enforced mechanisms. Every other governance behaviour depends on agent compliance with AGENTS.md, governance.md, and the workflow protocols.

This is a deliberate design choice, not a limitation. Hard enforcement of every rule would make the framework unusable. The gate is hard because it operates at the commit boundary — the moment where ungoverned code becomes permanent. Everything before the commit is convention reinforced by structured context.

Convention-based governance degrades under pressure. The gate does not. Design principle: hard enforcement at the commit boundary, convention everywhere else.

| Mechanism | Type | Enforcement |
|-----------|------|-------------|
| Pre-commit AI review gate | Hard | Blocks commit on FAIL verdict |
| Architecture boundary checks | Hard | Blocks commit on violations |
| Repository identity guard (P-14) | Hard | Blocks git operations in wrong repo |
| Session startup protocol | Convention | Agent compliance via AGENTS.md |
| Workflow phases | Convention | Agent compliance via workflow file |
| Prohibition table (P-01 to P-17) | Convention | Agent compliance via AGENTS.md |
| ORR checklist before main | Convention | Required by P-01 (never merge to main) |

### What Makes the Gate Adversarial

The review gate is adversarial in a specific technical sense — not in the sense of "it reviews code" (GitHub Copilot Code Review does that) but in the sense of:

1. **Separation of agents**: The writing agent and the reviewing model are separate. The reviewing model has no access to the writing agent's reasoning, only the diff and the review context. It cannot rationalise the implementation.
2. **Proportionate system prompt**: The reviewer is instructed to identify genuine problems with specificity and proportionality — HIGH for actual bugs and security issues, MEDIUM for quality concerns, LOW for style. FAIL requires a specific file:line citation. The reviewer does not manufacture findings.
3. **Structured verdict schema**: PASS / WARN / FAIL with a typed `ReviewVerdict` Pydantic model — not a prose review. Malformed LLM responses raise validation errors rather than silently passing.
4. **Two-layer review context**: Universal architectural invariants (framework-owned) plus project-specific rules (developer-maintained) are injected into every review. The reviewer knows the project's rules, not just general best practice.
5. **Persistent audit trail**: Every verdict is logged to `.ai-review-log.jsonl`. Verdict history can be analysed for patterns; the dream phase uses this data.

This combination — separation, adversarial framing, typed schema, project context, audit trail — is not packaged in any current IDE or vendor tooling.

### Three Checkpoints

Not zero checkpoints (full autonomy). Not eight checkpoints (SDLC overhead). Three:

1. **Plan gate**: Before implementation begins, the spec is approved and the implementation plan is reviewed by the human.
2. **Commit gate**: Before code enters the repository, the AI adversarial review fires.
3. **Release gate**: Before code enters production, the ORR checklist is completed.

---

## The Self-Improvement Loop (Temporal Moat)

The dream phase is the mechanism that makes the framework improve over time — and the mechanism that cannot be fast-followed without months of operational data.

**How it works**: At session start (weekly, when data thresholds are met), `distill_dream.py` reads 30 days of `harness_events.jsonl` and `session_ledger.jsonl`. It applies pattern detection: if the same failure mode, escalation type, or capability gap appears in 3+ sessions with sufficient frequency, it generates a structured improvement proposal in `.agent/state/dream_proposals/`. The developer reviews, accepts, or rejects each proposal. Accepted proposals become diffs applied to skill files.

**Why this creates a moat**: The adversarial gate is the same for every installation on day one. The dream phase-calibrated skills are unique to each project and get better with every session. A framework installed on a project for six months has proposals derived from real failure patterns in that codebase — a fast-follower cannot replicate that without running the framework for six months.

**The compound effect**: A skill improved from a dream proposal produces fewer WARN verdicts. Fewer WARN verdicts means less developer friction. Less friction means the governance is more likely to be followed. Better compliance generates better session data. Better session data generates better proposals. The loop compounds.

---

## Release Milestones

> **Historical milestones v1.0.0 – v1.2.0.1** (Foundation, Demonstrably Working, Beta Ready,
> Outer Loop, Harness Gitignore Enforcements) have been moved to
> [`FRAMEWORK_ROADMAP_Archive.md`](FRAMEWORK_ROADMAP_Archive.md) to keep this file smaller for
> agent context budgets. Nothing was summarised or reworded — full detail is preserved there
> verbatim. This file picks up at v1.3.0.

---

### v1.4.0 — Intelligent Gate ✅ SHIPPED (2026-06-13)

**Goal**: The gate gains deterministic pre-context (evidence gathering, shared `GateContext`, per-capability calibration) and a confidence model for structural signals. Most of the original "Chain A — Gate Intelligence" scope (PageRank repo map, ADR injection, diff-aware routing, wiki layer, model tiering, policy notes) shipped earlier than planned — see Capability Inventory note below. v1.4.0 narrows to the remaining gate-context and calibration work plus state persistence.

**The strategic context**: The gate already routes by PageRank centrality, injects ADR domain context, and explains policy notes (all ✅ as of v1.3.4). What remains is making the gate's pre-LLM evidence gathering richer (T1-G-11), giving components a shared typed context object instead of ad-hoc files (T1-G-13), calibrating capability sensitivity from rebuttal history (T1-G-14), and upgrading confidence labels on structural signals from HIGH/MEDIUM to EXTRACTED/INFERRED/AMBIGUOUS (T1-H-10).

**Success criteria**:
- `GateContext` shared object is live; architecture violations, PageRank scores, co-change warnings, and ADR domains flow through it with graceful degradation
- Evidence-gathering pre-context (pytest collect, co-change, TODO delta) is injected before the LLM call
- Per-capability calibration weights are derived from rebuttal rate and surfaced in `harness_health.py`
- Co-change and repo map confidence signals use the three-tier EXTRACTED/INFERRED/AMBIGUOUS model
- Token budget and cross-project health are queryable via SQLite

> **Capability Inventory note**: A prior version of this table listed T1-G-01/02/03/04, T1-H-01/02/03/06/07, and T1-D-05 as v1.4.0 Chain A phases. Per `FRAMEWORK_BACKLOG.md`, all of these are now ✅ delivered (most shipped in v1.0.0–v1.3.4, ahead of this milestone's original schedule). They are retained here only as historical record of the original Chain A sequencing — no remaining work against them is in scope for v1.4.0.

**Gate context & calibration**:

| ID | Item | Effort | Category |
|----|------|--------|----------|
| T1-G-13 | GateContext shared object for pre-commit chain | Medium | Gate architecture |
| T1-G-14 | Per-capability AT9 calibration weights | Medium | Gate calibration |
| T1-G-11 | Evidence-gathering pre-context for review gate (pytest collect, co-change, TODO delta; HIB-052 session-counting fix delivered as part of this item) | Medium | Gate |
| T1-H-10 | Three-tier confidence tagging (EXTRACTED/INFERRED/AMBIGUOUS) for co-change and repo map signals | Medium-High | Repo intelligence |
| T1-L-05a | Stop hook for acceptance_check.py on feature branch close | Low-Medium | Outer loop |

**Observability**:

| ID | Item | Category |
|----|------|----------|
| T1-I-02 | Token budget tracking per session | Cost management *(✅ delivered v1.1.5 — retained for cross-reference)* |
| T1-D-01 | SQLite state index — single machine | State persistence |
| T1-D-02 | Cross-project harness health | Multi-project |

**HIB-052 — session_id "unknown" clustering** ✅ **Delivered in T1-G-11, commit b645830 (v1.4.0)**: Found during v1.3.4's dream phase validation. Real sessions were collapsing into a shared `"unknown"` bucket rather than carrying their UUID, degrading per-session aggregation and pattern detection. Fixed as part of T1-G-11 delivery: `harness_utils.py`, `roster_builder.py`, and `audit_logger.py` patched to read the active session UUID at write time; `"pre-session-init"` marker now reserved exclusively for genuine pre-init events (not a shared fallback bucket); regression test added. See FRAMEWORK_BACKLOG.md HIB-052 for full detail.

**Deferred to v1.4.1** (split out to keep v1.4.0 scoped — see decisions_log.md for rationale):

| ID | Item | Effort | Category |
|----|------|--------|----------|
| T1-L-12 | Spec grader per-criterion feedback | Medium | Outer loop |
| T1-L-13 | Decision block format for ADR annotations | Low | Outer loop |
| T1-L-14 | System archetype classification in spec template | Low | Outer loop |

> **Security batch, delivered v1.4.1** (full descriptions in that milestone's table, not repeated here): `T1-K-02` (formal security review), `T1-K-02a` (quarantine pattern mitigation), `T1-K-05a` (env var sanitisation in gate subprocess calls).

| ID | Item | Effort | Category | Status |
|----|------|--------|----------|--------|
| T1-K-07 | Quarantine structural bypass mitigation — active contexts and dream proposals bypass structural validation before ingestion; close the isolation-marker attack surface gap identified in T1-K-02 | Medium | Security | ⬜ (still open — see Unscheduled Backlog, Security foundations) |

**Sprint planning notes (pre-v1.4.0)**:

- **Gemini CLI HALT coverage gap** (2026-06-08): T1-C-01 `--stop-hook` provides post-session governance for Claude Code only. No equivalent mechanism exists for Gemini CLI, making a completed Gemini session structurally indistinguishable from mid-task abandonment without manual spot-checks. Sprint planning should either scope a Gemini CLI stop-hook equivalent or establish a lightweight external verification protocol for all Gemini-executed delivery tasks. See decisions_log.md entry 2026-06-08 for full context.

---

### v1.4.1 — Outer Loop Quality & Security Review ✅ SHIPPED (2026-06-14)

**Goal**: Complete the outer loop grading/classification trio (spec grader, decision blocks, archetype classification) and deliver the formal context-injection security review before broader distribution. Split from v1.4.0 to keep that milestone's Medium/Medium-High gate-architecture work from compounding with this Medium-effort outer-loop and security batch.

**Planned items**:

| ID | Item | Effort | Category | Status |
|----|------|--------|----------|--------|
| HIB-053 | `outcome_override` write-before-commit flaw — cross-check commits exist before accepting success override in `infer_and_close_previous_session()` | Low | Bug fix | ✅ (v1.4.1) |
| HIB-054 | `false_positive_to_eval.py` Windows UnicodeEncodeError on emoji print; audit `incident_to_eval.py` for same pattern | Low | Bug fix | ✅ (v1.4.1) |
| T1-L-12 | Spec grader per-criterion feedback | Medium | Outer loop | ✅ (v1.4.1) |
| T1-L-13 | Decision block format for ADR annotations | Low | Outer loop | ✅ (v1.4.1) |
| T1-L-14 | System archetype classification in spec template | Low | Outer loop | ✅ (v1.4.1) |
| T1-K-02 | Formal security review: context-injection attack surface (`docs/security/attack-surface-review.md`) | Medium | Security | ✅ (v1.4.1) |
| T1-K-02a | Quarantine pattern as architectural context-injection mitigation (delivered in same doc as T1-K-02) | Low | Security | ✅ (v1.4.1) |
| T1-K-05a | Environment variable sanitisation in gate subprocess calls | Medium | Security | ✅ (v1.4.1) |

**Dependency note**: T1-L-13 depends on T1-G-12 ✅ (AT/FM vocabulary, delivered v1.3.3) — no blocker. T1-L-14 depends on T1-G-12 ✅ and benefits from T1-L-12 landing first (natural delivery companion per backlog). T1-K-02a delivers inside the T1-K-02 document — sequence as one PR.

---

### v1.4.2 — Gate Correctness & Backlog Repair ✅ SHIPPED (2026-06-14)

**Goal**: Restore universal-rule enforcement at review time — the gate's universal RULE layer and AT/FM vocabulary were silently filtered out of the LLM context (HIB-055). Also repair backlog/roadmap integrity drift discovered post-v1.4.1, and fix a sibling false-success bug in session close inference (HIB-053b).

**Delivered**:

| ID | Item | Effort | Category | Status |
|----|------|--------|----------|--------|
| HIB-055 | Universal RULE sections + AT/FM vocabulary reach the reviewer (always-inject RULE sections; trigger-gate vocabulary on ADR presence) | Medium | Gate correctness | ✅ (v1.4.2) |
| T1-L-13a | ADR decision-block ADVISORY rule (LLM-side), consuming HIB-055's vocabulary trigger | Low | Outer loop | ✅ (v1.4.2) |
| HIB-053b | Spec-mtime false-success in `infer_and_close_previous_session()` — cap commitless spec work at partial; use `git status` not mtime | Medium | Bug fix | ✅ (v1.4.2) |
| (repair) | Backlog repair: re-register HIB-055, HIB-053c; reconcile T1-L-13/T1-G-12 markers; roadmap reconciliation | Low | Hygiene | ✅ (v1.4.2) |

---

### v1.4.5 — Gate Reliability, Cross-Platform Portability & Polish ✅ SHIPPED (2026-06-30)

**Goal**: Close a cluster of low-effort, high-value reliability and portability gaps that have been open since v1.0.0. Keeps v1.5.0 scoped to its Quality Signal Maturity theme without bundling unrelated polish work into it.

**The gap this addresses**: Three categories of day-one friction for new users and existing installations: (1) silent gate bypasses leaving no audit trail, (2) pre-commit hooks that appear wired but never execute on Linux/macOS, and (3) AGENTS.md governance language that was advisory rather than imperative — violating the Osmani "curse of instructions" principle the framework itself cites.

**Delivered**:

| ID | Item | Category | Status |
|----|------|----------|--------|
| HIB-014/017 | GATE_SKIPPED audit event on all early-exit paths | Gate reliability | ✅ |
| HIB-021/BUG-09 | Commit message read from sys.argv[1] at commit-msg stage | Gate reliability | ✅ |
| HIB-042 | Remove Windows-only cmd /c from pre-commit hook template | Cross-platform portability | ✅ |
| HIB-025 | AGENTS.md governance language audit (must/always/never) | Governance compliance | ✅ |
| HIB-043 | Cross-family review model recommendation in docs/configuration.md | Documentation | ✅ |
| T1-B-08 | validate.py warning states display ⚠️ not ✅ | UX polish | ✅ |
| S0-13 | GitHub topics named in README | Discoverability | ✅ |
| (skill) | AI hallucination detection checks added to code-review SKILL.md | Skill quality | ✅ |

**Migration**: `bootstrap/migrations/v1_4_4_to_v1_4_5.py` — patch migration, no config schema changes. Copies updated framework-owned files to the target installation. Note: `ai_review.py` was decomposed into smaller single-responsibility modules (`roster_builder.py`, `context_loader.py`, `route_decision.py`, `rebuttal.py`, and `gate_context.py`), resulting in a maintenance-only refactoring bump with no external API changes.

---

### v1.4.6 — Code Review Skill Split & Genericisation ✅ SHIPPED (2026-06-30, tag `20c6959`)

**Goal**: Remove project-specific terminology leaks from universal skills and close two ReDoS vulnerabilities discovered in the migration toolchain.

**Delivered**:
- Decomposed the monolithic `code-review/SKILL.md` (previously exceeding the 150-line limit) into `branch-isolation/SKILL.md` (generic tenancy validation) and `schema-hardening/SKILL.md` (schema constraint validation), both including anti-rationalisation tables
- Ported generic RBAC checks into `security-audit/SKILL.md`; genericised `testing-patterns/SKILL.md` by replacing project-specific role/model references with generic exemplars
- Cleaned legacy attribution links from 12 skill files
- Fixed regex backtracking (ReDoS) vulnerabilities in `upgrade.py` and `downgrade.py` — replaced unbounded `\s*` matchers with horizontal-only `[ \t]*`

**Note**: This release completes the skill-decomposition work scoped in `PLAN_code-review-skill-split.md` (removed post-delivery, 2026-07-06 — confirmed delivered via this tag, backlog ✅ marker, and no remaining references).

---

### v1.4.7 — Gate Reliability & Migration Hardening ✅ SHIPPED (2026-07-02, tag `ce36183`)

**Goal**: Close a spec-gate-blocking provider bug and centralise fragile ad-hoc YAML validation across the migration chain.

**Delivered**:
- HIB-057 — Fixed `call_llm` `AttributeError` in `ReviewProvider` that was blocking spec gate Pass 2 reviews
- HIB-041 — Centralised naive YAML configuration validation into a `validate_yaml_config` helper in `bootstrap/migration_base.py`, supporting multi-line block scalars; all 16 migration script modules refactored to use it
- HIB-046 — Added a `python-precommit` fallback module check inside `validate_tools()` in `validate.py`, preventing false-positive warnings on Windows
- Framework checksum registry regenerated for v1.4.7

---

### v1.4.8 — Coupling Management Foundations ✅ SHIPPED (2026-07-08, branch `feat/coupling-management`)

**Goal**: Give the harness a vocabulary and a working mechanism for reasoning about software coupling deliberately — detecting emergent cross-boundary coupling, recording human judgments about it, and using those judgments to filter noise on every subsequent run. Extends the governance model from "what code looks like in one commit" to "how the system's structure evolves across many commits" — the harness's first genuinely temporal governance signal, alongside the existing point-in-time gates.

**The gap this addresses**: The pre-commit review gate and architecture boundary checks are point-in-time — they see one diff at a time and cannot detect coupling that accretes silently across dozens of individually-unremarkable commits. This milestone adds that second clock, deliberately kept lightweight (on-demand CLI, no daemon) and evidence-driven (every design decision validated against the harness's own real commit history before being finalised).

**Status**: All items below are implemented and merged to `main`.

**Delivered on branch**:

| ID | Item | Status |
|----|------|--------|
| T1-G-17 | Co-change core extraction (`co_change_core.py`) — parameterised, characterization-test-guarded extraction of git co-change logic from the pre-commit advisor, reusable by the reconciler | ✅ |
| T1-B-10 | Harness minimal self-config (`architecture.layers`) — declares the harness's own architectural boundaries so coupling detection has something to check crossings against | ✅ |
| T1-B-09 | Co-change reconciler CLI (`co_change_reconciler.py`) — on-demand, boundary-crossing-aware, frequency-gated and probability-ranked detector for emergent coupling; proven against the harness's own history | ✅ |
| T1-B-12 | CDR (Coupling Decision Record) ledger — schema, pilot migration of 3 real evidence-backed decisions covering three distinct coupling archetypes (derived/mechanical, model, functional), and full reconciler integration (matching, classification into Undeclared/Escalated/Tolerated/Accepted, escalation detection with hub-scope exemption fix) | ✅ |

**Governance vocabulary added**: `governance.md §8` — coupling evaluated as a strength/distance/volatility triple (not a single good/bad score); integration strength levels (intrusive → functional → model → contract); the balance rule (strong coupling only acceptable at short distance, or when volatility is low).

**Not yet built (deliberately deferred)**:
- Reliable session startup for non-frontier agents (T1-B-11) — surfaced during this work, not yet implemented
- Session.json explicit shared contract (T1-E-03) — improvement path identified during CDR-002's investigation, not urgent (low volatility)
- config.yaml parser unification (T1-E-04) — latent inconsistency identified, not yet fixed
- Core bare-`{}` return on git failure (HIB-060) — minor hardening, not yet fixed
- `check_traceability.py` alignment check with new config.yaml (HIB-061) — not yet verified
- Brownfield baseline bulk-population tooling for the CDR ledger — the general mechanism now has an ID: T1-G-18 (gate enforcement postures) proposes a project-wide baseline manifest pattern; revisit whether the CDR ledger's own bulk-population need is served by that work or still wants a dedicated tool.
- Active-model/cost-tier indicator at session start (T1-B-13) — unrelated finding surfaced during this work, filed separately

**Success criteria for merge to main**:
- Full test suite green on `main` after merge (currently 436+ passing on the branch)
- Backlog and roadmap accurately reflect delivered scope (this entry)
- No regression in existing pre-commit advisor behaviour (guaranteed by T1-G-17's characterization tests)

---

### v1.4.3 — Governance & Consistency ✅ SHIPPED (2026-06-22)

**Goal**: Restructure the prohibition model into a tiered universal/project/pattern-conditional system, and close a round of consistency gaps between what the framework claims to enforce and what it actually enforces.

**Delivered**:

| ID | Item | Category | Status |
|----|------|----------|--------|
| T1-K-08 | `architecture_checks.py` fail-loud on zero files scanned (previously silent PASS) | Governance & Consistency | ✅ |
| T1-K-09 | Consistency gate: workflow slug resolution, `blocked_commands` header, H/S/C/G label assertions | Governance & Consistency | ✅ |
| T1-K-10 | Session protocol single-sourcing (startup/close/escalation) | Governance & Consistency | ✅ |
| T1-M-14 | Stale P-series reference cleanup in AGENTS.md; H-series positive reframing | Governance & Consistency | ✅ |
| (restructure) | Prohibition restructure: universal / project-specific / pattern-conditional three-tier model | Governance | ✅ |

---

### v1.4.4 — Integration Release ✅ SHIPPED (2026-06-22)

> **Known discrepancy**: `CHANGELOG.md`'s v1.4.4 entry also lists `T1-L-12`, `T1-L-13`,
> `T1-L-14`, and `T1-K-05a` as delivered here. `FRAMEWORK_BACKLOG.md` (the canonical
> item-status source) and this roadmap's own v1.4.1 entry both confirm all four
> actually shipped in **v1.4.1**, three versions earlier — the CHANGELOG.md v1.4.4
> entry is a duplicate/erroneous re-listing and still needs correcting there.
> Excluded from the table below.

**Goal**: Fold five unmerged feature branches into `main` in a single integration release, closing a batch of gate-correctness and observability gaps found across those branches.

**Delivered**:

| ID | Item | Category | Status |
|----|------|----------|--------|
| BUG-04 | PASS/PASS_FAST verdicts now written to audit log | Logging | ✅ |
| BUG-05 | ADR domain names correctly mapped to capability names in routing | Routing fix | ✅ |
| HIB-053 | Additional hardening: further guards on session close inference against write-before-commit race | Bug fix | ✅ |
| T1-K-11 | Stale branch detection in `harness_health.py` — surfaces branches with unmerged commits older than 14 days | Observability | ✅ |
| (CI) | CodeQL scanning scoped to Python only via `.github/codeql/codeql-config.yml` | CI | ✅ |

**Test suite**: 372 tests passing (up from 358 at v1.4.2); checksum registry covers 643 files.

---

### v1.4.9 — System Consolidation ✅ SHIPPED (2026-07-12)

**Goal**: System consolidation, scope repair, traceability hardening, and parser unification.

**Delivered items**:
- ~~T1-E-04: config.yaml parser unification~~ *(correction 2026-07-20: only the harness_utils.py foundation — DEFAULTS table, load_harness_config(), get_harness_config() — landed in v1.4.9. Consumer rollout across ~20 files was never completed; this is now scoped as remaining v1.4.10 work. See SPEC-config-loader.md, folded into SPEC-v1.4.10-governance-hardening.md.)*
- T1-E-03: session.json shared contract enforcement
- HIB-062: Traceability ID coverage regex expansion
- HIB-065: Parser-robustness failure mode (invalid-escape) — fail-closed via _handle_parse_failure
- T1-L-22: check_traceability.py robustness (single-scan cache, missing-docs messaging, size guard)
- T1-B-11: Honest outcome labeling for non-code sessions (narrowed scope)
- ~~HIB-055: Universal review-context RULE sections orphaned~~ *(correction 2026-07-12: this shipped in v1.4.2, not v1.4.9 — erroneous duplicate entry, retained struck through rather than silently deleted)*
- T1-B-13: Active-model/cost-tier indicator (built and deliberately reversed)

---

### v1.4.9.1 — First-Commit Hotfix ✅ SHIPPED (2026-07-19)

**Goal**: Fix the confirmed, root-caused defects that block or silently corrupt a brand-new project's first commit. Split out from Governance Hardening (below) to keep that milestone's policy-decision work from being delayed by mechanical fixes that need no design debate. See `SPEC-v1.4.9.1-first-commit-hotfix.md` (spec-first per standing practice).

**Delivered items**:
- F1 (installer PM/venv detection), F2 (Pydantic fallback + 3-stage precedence), F3 (CWD-relative path fix), F5 (_strip_json_fences restore) — commit `9938f24`
- FID-1 through FID-6 post-merge remediation — commit `267dad5`
- HIB-069 (checksums size-ceiling fix) and HIB-074 (error-mislabeling defect, filed for follow-up) noted as related items surfaced during delivery

---

### v1.4.10 — Governance Hardening ✅ SHIPPED (2026-07-20, tag `v1.4.10`)

**Goal**: Hardened requirement traceability and merge governance, completed unified configuration parser rollout across all consumers, established append-only decisions log discipline with O(1) backdating guard, fixed SQLite schema drift, and added live log snapshotting.

**Delivered items**:
- T1-E-04: Complete config.yaml parser unification rollout across `route_decision.py`, `check_traceability.py`, `acceptance_check.py`, `acceptance_hook.py`, `pm_scaffold.py`, `init_session.py`, + 6 unit tests in `test_config_loader.py`.
- T1-L-21: Dynamic `high_risk_patterns.override_defaults` with fail-closed protection on empty pattern set (`CRITICAL_WARNING_ZERO_HIGH_RISK_PATTERNS`).
- T1-K-12 & T1-K-13: Root-commit exemption predicate (`is_root_commit()`), spec-ID regex for versioned specs & archive fallback, merge-gate `--check-merge-trace` / `--ack-no-trace` CLI mode & pre-push hook stage template, and 12-char SHA session ledger fallback attribution (`_get_session_ledger_attribution()`).
- HIB-ENV-02 & T1-I-08: TTY-aware session-start recovery stash prompt and clean stash drop on close.
- HIB-059: `PRAGMA table_info` SQLite schema drift auto-migration in `state_persistence.py`.
- T1-K-14: Fail-open audit taxonomy (`large_diff_fail_open` events & explicit `FAIL_OPEN` verdicts).
- HIB-063: Live log snapshots on close (`harness_events_<session_id>.jsonl` and `ai_review_log_<session_id>.jsonl` to `.agent/state/snapshots/`).
- T1-K-15 / AT-04: `check_exception_standards.py` wrapper script and pre-commit template entry.
- HIB-061 / AT-06: Root commit traceability exemption.
- T1-L-20: `record_decision()` append-only helper with O(1) backdating guard, `archive_old_decisions()` helper with ascending-order check, and AGENTS.md governance rule update.
- Framework Upgrade Manager migration script `v1_4_9_to_v1_4_10.py` and checksums registry bump.

**Spec**: `SPEC-v1.4.10-governance-hardening.md` (spec-first per standing
practice). Inputs: `GOVERNANCE-HARDENING-INPUTS.md` (AT-04/05/06 findings
from `ANALYSIS-PLAN-v1.4.10.md`), `hib-collision-map-2026-07.md`,
`incident-chain-2026-07-15.md`.

---

### v1.4.11 — Installer & Onboarding Hardening ✅ SHIPPED (2026-07-24)

**Goal**: Close the silent and semi-silent failure modes a genuinely new user
hits before or during their first install — distinct from v1.4.9.1's loud
first-commit crashes, these are cases where the harness reports success while
something is actually wrong or unclear. Formalised as its own milestone
2026-07-18 after a live cold-start observation session surfaced five findings
in ninety minutes, on top of the two design items (F7, F8) already parked here
from the original v1.4.9 first-commit assessment.

**The gap this addresses**: `bootstrap/validate.py` currently reports "0
errors, 0 warnings" based on file presence, not on whether the harness will
actually function correctly for this user, on this machine, right now. Field
evidence (`cold-start-field-observations-2026-07-18.md`) shows this gap is not
hypothetical: a real first-time user hit a wrong install target, macOS venv
path failures, an undiscoverable API key requirement, and a silently
downlevel toolchain from a stale `.venv` — all while the installer reported
clean.

**Planned items**:
- F7: Framework-owned files being mutated by project formatters (black/ruff);
  checksum drift risk.
- F8: Validator dry-run redesign — presence-checking → runnability-checking.
  Now scoped to include three named preflight checks (see below).
- F-COLD-1: Wrong install-target detection (user cloned the harness's own
  repo, expected it to function as their project) + "you are here" diagram in
  getting-started.md/README (doc fix ships independently, no analysis needed).
- F-COLD-2: Cross-platform path/interpreter assumptions — macOS `.venv/bin/`
  vs Windows `Scripts/` — extends AT-01's rendering matrix with a
  platform × venv-tool dimension.
- F-COLD-3: Adversarial-review API key setup has no discoverable path —
  installer feature + validator reachability check.
- F-COLD-5: Stale venv Python silently downgrades enforcement tooling
  (black/ruff/mypy resolve to years-old versions with no warning).
- Genesis-mode spec (day-zero posture: behavioral rules on, artefact gates
  arm on precondition, from the earlier genesis-mode discussion).

**Spec**: `SPEC-v1.4.11-installer-onboarding.md` (spec-first per standing
practice). Input: `cold-start-field-observations-2026-07-18.md`.

---

### Deferred Scope Candidates — Under Consideration

**F-COLD-4 — Retrofit mode** (identified 2026-07-18, live cold-start session):
no guided path exists today for a user who arrives with working code but no
requirements, architecture documentation, or backlog — the "vibe-coded
prototype" entry point. Distinct from genesis mode (empty project, above) and
from T1-G-18 brownfield postures (mature project with existing architecture
and tests) — this is a third posture: real code, zero governance artefacts.
Possible shape: a detection step, a reverse-engineering-first workflow (agent
reads existing code, proposes a first-draft architecture doc and backlog for
human review, rather than starting from a blank spec template), a
`RETROFIT_BASELINE.md` artefact analogous to the CDR ledger's coupling
snapshot but one level up (requirements/architecture rather than coupling
debt), and the same staged `observe` → `ratchet` promotion already designed
for brownfield/genesis. Deliberately unscheduled and unscored pending a second
observed instance or a scoping decision — see
`cold-start-field-observations-2026-07-18.md` Finding 4 for the full argument
that this may be the modal adoption path rather than an edge case.

---

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
touch the same file in the same release would be unnecessarily disruptive.

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

#### Governance & Consistency

| ID | Item | Category | Status |
|----|------|----------|--------|
| T1-K-08 | Fix architecture_checks.py silent PASS on zero files scanned | Governance & Consistency | ✅ v1.4.3 |
| T1-K-09 | Add consistency gate: assert cross-references exist and gates actually gate | Governance & Consistency | ✅ v1.4.3 |
| T1-K-10 | Single-source session startup/close/escalation protocols (same treatment as prohibition fix) | Governance & Consistency | ✅ v1.4.3 |
| T1-M-14 | Clean up stale P-series references in AGENTS.md §9.1 and positive reframing of H-series (option B) | Governance & Consistency | ✅ v1.4.3 |

### v1.6.0 — Workflow Engine 📋 FUTURE

**Goal**: Replace prose-driven agent interpretation of workflow phases with a data-driven FSM-backed orchestrator. Agents stop inferring phase context from convention and start reading machine-readable state written and enforced by the framework.

**The strategic context**: Every workflow in the harness is currently a prose `.md` file that agents follow by reading and interpretation. There is no enforcement that an agent correctly identifies the current phase, satisfies phase exit conditions, or transitions in the correct order. The Workflow Engine makes phase enforcement as rigorous as commit-level enforcement — the gate checks commits; the runner checks phases. Design document: [`workflow-engine-design.md`](../design/workflow-engine-design.md).

**Prerequisites**: T1-E-01 (skills as Tool ABC subclasses — **⬜ confirmed undelivered**; see v1.5.1, the sole content of which is delivering this item) required before T1-W-03. T1-D-01 (SQLite state index, v1.4.0) is a soft dependency — flat-file state is the authoritative source of truth; SQLite adds queryability.

**Planned items**:

| ID | Item | Category |
|----|------|----------|
| T1-W-01 | workflow.schema.yaml — universal workflow contract | Schema |
| T1-W-02 | workflow.defaults.yaml — machine-readable feature/bug/hotfix phase sequences | Workflow definitions |
| T1-W-03 | workflow_runner.py — FSM-backed phase transition engine (`transitions` library) | Core engine |
| T1-W-04 | ContractEvaluator — per-phase completion gate | Gate enforcement |
| T1-W-05 | Bootloader integration — workflow state injection at session start | Agent context |

Full item descriptions in backlog section T1-W.

---

### v2.0.0 — Shared State (Tier 2) (Team Edition) 📋 FUTURE

**Goal**: Multi-machine, small-team operation. Shared state layer enables cross-developer session history, decision visibility, and distributed governance.

**The strategic context**: The inner loop mechanisms (context files, workflow conventions) are being absorbed by Cursor, GitHub Copilot Workspace, and IDE-native agent tooling. The defensible territory is the governance philosophy, the gate mechanism, and the compliance positioning — where vendor tooling will not go because it requires institutional governance knowledge, not just coding features.

**Planned items** (Tier 2 — 18 items in backlog T2-A through T2-D):
- T2-A-01: MCP server wrapping SQLite — shared session history, decisions, verdicts queryable across machines
- T2-A-02: Cross-machine session continuity
- T2-A-03 through T2-A-06: Hybrid search, shared decisions, RRF search, community detection
- T2-A-07: Cross-project calibration convergence (deferred — design alongside shared-state work, not standalone)
- T2-B-01: Distributed HALT sentinel
- T2-B-02 through T2-B-04: Role-based governance, remote audit trail, team dashboard
- T2-C-01 through T2-C-03: Team bootstrap, shared skill registry, team dream phase
- T2-D-01 through T2-D-04: Node.js/Go stack packs, stack-agnostic pre-commit, Ollama provider

### v3.0.0 — Enterprise & Compliance (Tier 3) (Enterprise Edition) 📋 FUTURE

**Goal**: Production database infrastructure, compliance-grade audit trails, and formal regulatory control mappings.

**Compliance note**: Formal compliance control mappings (SOCI Act, ISM, PSPF) are planned for this milestone. Until those mappings exist with specific control references, audit trail output formats, and demonstrated compliance answers, the regulated industry claim is aspirational. v3.0.0 makes it concrete.

**Planned items** (Tier 3 — 13 items in backlog T3-A through T3-C):
- T3-A-01 through T3-A-03: PostgreSQL backend, migration framework, high availability
- T3-B-01 through T3-B-05: Row-level security, audit-grade immutability, SSO, data residency, RBAC
- T3-C-01 through T3-C-04: DORA metrics, Jira/Linear integration, harness-as-a-service API, compliance reporting
- T3-C-05: Human approval-quality drift detection (parked — pair with compliance work; lowest-evidence comparator)

**Enterprise Edition go-to-market note**: The enterprise product requires a fundamentally different go-to-market than the Developer Edition. The temporal moat (dream phase) that differentiates the Developer Edition is less relevant to enterprise procurement. Enterprise differentiators are compliance control mappings, policy-as-code governance (T1-K-05, HIB-032), audit-grade immutability (T3-B-02), and separation of duties (T2-B-02). The enterprise product should be considered a parallel workstream rather than a future milestone — potentially delivered as a services engagement wrapping the current Tier 1/2 framework before the full v3.0.0 infrastructure is built. The PE distribution channel identified in strategic context is accessible at Developer Edition maturity; it does not require v3.0.0. Source: strategic planning session, June 2026.

---

## Current Sprint Status

v1.x series = Developer Edition — solo developer to 3-person team, flat-file state, convention-heavy governance, installs in under 10 minutes.

**Active milestone**: v1.4.12 (v1.4.11 shipped 2026-07-24)
**Sprint tracking**: `.agent/state/active_context.md`

**v1.4.x family**: v1.4.0 ✅, v1.4.1 ✅, v1.4.2 ✅, v1.4.3 ✅, v1.4.4 ✅, v1.4.5 ✅, v1.4.6 ✅, v1.4.7 ✅, v1.4.8 ✅, v1.4.9 ✅, v1.4.9.1 ✅, v1.4.10 ✅, v1.4.11 ✅
**v1.5.x family**: v1.5.0 📋, v1.5.1 📋, v1.5.2 📋

**v1.2.0 Phase 1 + Hardening Sprint — DELIVERED**:
- ✅ T1-L-01 — Spec quality gate (`check_spec.py`, two-tier BDD + field validation)
- ✅ T1-L-02 — `/business-analyst` workflow (state-machine phases, assumption surfacing, decisions_log feed)
- ✅ S0-14 — `bootstrap/uninstall.py` — clean framework removal utility
- ✅ S0-15 — Upgrade prerequisite documentation (getting-started.md, README.md, upgrade.py help)
- ✅ HIB-034/035 — Context length governance (AGENTS.md ceiling check, decisions_log archival prompt)
- ✅ HIB-036 — Atomic config migration rollback (upgrade.py + downgrade.py)
- ✅ HIB-037 — Pre-flight installation state validation (`_pre_flight_check`, `--skip-preflight`)
- ✅ HIB-038 — Migration chain contiguity assertion (`_assert_chain_contiguous`, fork resolution)
- ✅ BUG-10 — Harness Gitignore Enforcements (v1.2.0.1 patch release, 2026-05-31)

**Pre-sprint items — all delivered ✅ (2026-06-02)**:

These items were identified by direct code inspection (`docs/planning/CAPABILITY_INVENTORY.md`,
2026-06-02) as blocking core value propositions. All were completed before Sprint 1 began.

1. ✅ **T1-D-00 + BUG-11** (same PR) — Create `.agent/config/skill_ownership.yaml`.
   The dream phase (T1-D-03 ✅) is live but routing ALL patterns to fallback
   skills because the routing map was never created. Every dream proposal
   generated today is mis-attributed. Configuration file only, no code required.
   BUG-11: fix `distill_dream.py` reading `log.get("check_type")` when
   `.ai-review-log.jsonl` uses `blocking_concern` — all AI review FAILs are
   classified as `"review_failure"` regardless of actual concern. One-line fix.

2. ✅ **BUG-12** — Fix wiki compile cold-start failure. `wiki_compile.py` updates
   the 7-day cooldown timestamp even when compilation fails (Ollama not running,
   ADR files missing). A developer without Ollama silently has no wiki context
   for their first week. Fix: do not update `last_run_utc` on failure; use 1-day
   retry cooldown on failure instead of 7-day success cooldown.

3. ✅ **BUG-13** — Sync E2E test project `ai_review.py`. The file at
   `tests/e2e/test_project/src/scripts/ai_review.py` is stale (git status shows
   M) and does not include the rebuttal protocol (T1-G-06 ✅). E2E tests do not
   test what ships. Sync to current framework source.

4. ✅ **T1-I-07 wiring** — Wire `ai_review.py` token counts to `session.json`.
   The HALT mechanism and file format exist. No code path currently increments
   the session token counter from review gate calls — the v1.1.5 success
   criterion ("a session approaching the token budget ceiling receives a WARN")
   is not met. After each successful LLM call in `ai_review.py`, read
   `session.json`, add `token_usage` from the `ReviewVerdict` to the running
   session totals, write back atomically via `_lock_session()`.

5. ✅ **S0-24** — De-GymBase-ify functional code (see S0-24 scope note in v1.1.0
   section). Must complete before S0-23 (README pre-Reddit additions) goes live.

6. ✅ **T1-L-00** — Outer loop methodology profile system. Design gate for all
   remaining T1-L work. Retrofit `check_spec.py` and `/business-analyst` workflow
   to add `outer_loop.mode` awareness (`discovery` / `incremental` / `contractual`).
   Estimated: half-day design + audit, small code changes.

**v1.3.0 pre-sprint design gate**:
T1-L-00 (outer loop methodology profile system) must be completed before
any T1-L-03 through T1-L-07 implementation begins. Includes retrofit of
already-delivered T1-L-01 (check_spec.py) and T1-L-02 (/business-analyst
workflow) to add mode-awareness. Early-stage delivery means retrofit cost
is low; correctness benefit is high. Estimated: half-day design + audit,
small code changes to check_spec.py and business-analyst.md.

Note: T1-L-00 is now ✅ delivered as of the pre-sprint foundations work.
This note is preserved as a historical record of the sequencing decision.

---

**v1.3.0 Sprint 1 — DELIVERED (2026-06-03)**
- ✅ T1-L-03 — /project-manager workflow + pm_scaffold.py
- ✅ T1-L-04 — Requirement → commit traceability (check_traceability.py)
- ✅ T1-L-05 — Acceptance gate (acceptance_check.py)
- ✅ Migration module v1_2_0_1_to_v1_3_0.py
- ✅ 29 E2E scenarios passing, checksums frozen at v1.3.0

**v1.3.1 Sprint 2 — DELIVERED (2026-06-03)**
- ✅ T1-I-00a/T1-I-00b — circuit_breaker.py routed to harness_events.jsonl
- ✅ BUG-15 — check_halt.py as pre-commit hook with fail_fast
- ✅ T1-N-02 — concurrent write safety via _lock_file in harness_utils.py
- ✅ T1-B-01 — UNIVERSAL_CONTEXT.md, tool shims converted
- ✅ T1-A-09 — AGENTS.md split, AGENTS_PROJECT.md created
- ✅ T1-I-01/T1-I-06 (partial) — memory_manager.py three-tier foundation
- ✅ T1-I-04 — AST staleness detection in init_session.py
- ✅ BUG-14 through BUG-18 — all five closed
- ✅ T1-N-07 — event_type alignment verified
- ✅ 250 tests passing, 30 E2E scenarios passing, checksums frozen at v1.3.1

**v1.3.2 — Outer Loop Completion & Recovery Foundations**
❌ DEFERRED — scope folded into v1.4.0 sprint planning

T1-L-01a, T1-J-01, T1-J-01a, T1-M-03 reprioritised; v1.3.3 advanced to carry bug fixes and documentation backlog from Engineer's Map analysis.

Scope:
1. T1-L-01a — Spec collision detection (deferred to v1.3.4)
2. T1-J-01 + T1-J-01a — Automatic session checkpoint + mid-task convention (deferred to v1.3.4)
3. T1-M-03 — Mid-session observability (session_health.py) (deferred to v1.3.4)

---

**v1.3.3 — Bug Fixes & Documentation Backlog**
✅ DELIVERED (2026-06-07)

Theme: Carry critical bug fixes for casing issues and version reading, and publish the documentation backlog (including state file schemas and GateContext design specification).

Scope:
1. HIB-FM8-02 — Dynamic version reading from harness_version.txt
2. HIB-FM8-01 — Normalise severity casing to uppercase ("INFO", "CRITICAL") across all events and log files, fixing dream phase bypass trigger
3. Onboarding baseline path — Move baseline reports from project root to `.agent/baseline/`
4. Security — Add `rebuttal_pass.json` to `.gitignore`
5. docs/state-file-schema.md — Authoritative schema reference for all state files (harness_events.jsonl, .ai-review-log.jsonl, session_ledger.jsonl, session.json)
6. src/scripts/review_context_universal.md — Add gate finding output format (decision block required for FAIL and WARN)
7. docs/archetypes/ — Create starter domain packs for A2, A3, and A6
8. docs/architecture/gate-context-design.md — Design specification for the GateContext shared object (T1-G-13)

---

**v1.3.4 — Health, Observability & Recovery Safety Net** ✅ SHIPPED (2026-06-12)

Theme: Close out v1.3.2 deferred debt, deliver the health check code backing the v1.3.3 config stubs, and fix the dream phase field name and threshold bugs discovered during GymBase live operation.

Scope:
1. HIB-HEALTH-01 — Dream proposal staleness check (`harness_health.py --dream-proposals`)
2. HIB-HEALTH-02 — State file size checks (`harness_health.py`, priority: `repo_graph_cache.json`)
3. T1-L-01a — Spec collision detection (`check_spec.py` Jaccard similarity extension)
4. T1-J-01 + T1-J-01a — Automatic session checkpoint + mid-task convention (`init_session.py` + `AGENTS.md`)
5. T1-M-03 — Mid-session observability (`session_health.py`)
6. HIB-GEMINI-01 — Gemini CLI post-session verification protocol (convention + `init_session.py` read)
7. T1-K-06 — `blocked_commands.md` creation + `AGENTS.md` update
8. HIB-DREAM-01 — `distill_dream.py` wrong field name for review log keyword matching (`comments` → `summary` + `concerns`)
9. HIB-DREAM-02 — `INTENT_MISMATCH` pattern missing from `proposed_rules_catalog` and `skill_ownership.yaml`
10. HIB-DREAM-03 — `escalation_rate` threshold redesign: compound threshold fix (`AND` → `OR`) and `partial`/`abandoned` outcome weighting

**Dream phase fix sequencing**: HIB-DREAM-01 and HIB-DREAM-02 are prerequisites for HIB-DREAM-03. The field name fix (01) ensures keyword matching reads the correct schema fields; the catalog addition (02) ensures `INTENT_MISMATCH` patterns route correctly. Both must land before HIB-DREAM-03 so the revised threshold has valid, correctly-routed input data to test against. Deliver 01 and 02 in the same commit; 03 in a subsequent commit after verifying dry-run output.

**Active milestone**: v1.4.12 (v1.4.11 shipped 2026-07-24)
**v1.3.x family**: v1.3.0 ✅, v1.3.1 ✅, v1.3.2 ❌ (deferred), v1.3.3 ✅, v1.3.4 ✅
**v1.4.x family**: v1.4.0 ✅, v1.4.1 ✅, v1.4.2 ✅, v1.4.3 ✅, v1.4.4 ✅, v1.4.5 ✅, v1.4.6 ✅, v1.4.7 ✅, v1.4.8 ✅, v1.4.9 ✅, v1.4.9.1 ✅, v1.4.10 ✅, v1.4.11 ✅
*v1.4.5 Note: Refactored and decomposed ai_review.py into roster_builder, context_loader, route_decision, rebuttal, and gate_context modules with no API changes.*
**Next major milestone**: v1.5.0 (planning complete — see milestone entry above)

---

## Strategic Context

> **Capability Inventory** (generated 2026-06-02, last reviewed 2026-06-22): A direct code inspection inventory lives at `docs/planning/CAPABILITY_INVENTORY.md`. It is the authoritative source of truth for what is actually delivered vs. what the backlog describes. Where inventory findings conflict with backlog ✅ markers, the inventory takes precedence. The original pre-sprint findings (T1-D-00 dream phase routing gap, GymBase coupling S0-24, T1-I-07 partial delivery, BUG-11/12/13) were all resolved before Sprint 1 began (2026-06-02) — retained here only as historical record, not current gaps. The inventory has not yet been updated for the v1.4.6–v1.4.8 releases (see coupling-management arc, v1.4.8); this is a known gap, not an omission — Capability Inventory updates are deliberately held until `feat/coupling-management` merges to `main`.
> Sequencing observations in the inventory §3 should be reviewed before each milestone planning session.

### The Competitive Position

The framework's durable differentiation is not the context file patterns or named workflow conventions — these are being absorbed by IDE-native tooling. The durable differentiation is:

1. **The adversarial gate mechanism**: Separation of agents, adversarial framing, typed verdict schema, two-layer project context injection, persistent audit trail. Not assembled this way in any current vendor product.

2. **The self-improvement loop**: The dream phase creates a temporal moat. The longer the framework runs, the more calibrated its skills become to the specific failure patterns of the specific project. This cannot be fast-followed.

3. **The outer loop** *(v1.2.0)*: Specification quality governance and acceptance traceability are not things vendor tools will build because they require institutional governance knowledge.

4. **Compliance positioning** *(v3.0.0)*: SOCI, ISM, PSPF control mappings for Australian regulated industry contexts. Vendor tools will not go here.

**Context Compilation Pattern (Artur Huk, O'Reilly Radar, June 2026)**: The framework implements what Huk terms the "Context Compilation Pattern" — treating governance documentation as the new compiler. His six-step pipeline (context artifacts → context compiler → boundary hierarchy → generation → adversarial verification → acceptance verification) maps directly onto the harness delivery lifecycle. His phrase for the harness's core function: "automating the word NO." His philosophy statement: "The highest-value engineering skill is no longer writing syntax. It's engineering the conditions under which correct syntax can emerge." Both phrases belong in the README positioning work (S0-20, S0-23). Missing artifact identified: threat_model.md as a distinct first-class governance artifact separate from review_context_project.md (tracked as T1-K-05). DIR (github.com/huka81/decision-intelligence-runtime) governs runtime execution; the harness governs delivery — complementary layers of the same governance stack. BrainAPI (github.com/Lumen-Labs/brainapi2) is the most sophisticated open-source implementation of the T2-A memory architecture — evaluate as Team Edition memory backend foundation.

**Emerging ecosystem signal — agent governance interoperability (monitor from
v1.3.0 onward)**:
A nascent push toward open standards for agent governance is emerging, including the
Open Agent Governance Spec (OAGS) and AgentHub concepts. Key proposals include:
canonical agent identity manifests (model + prompt hash as a verifiable identity),
cryptographically signed audit evidence records, append-only event logs as a
first-class interoperability primitive, and package registries for agents and skills
with signed provenance. None of these are stable standards as of mid-2026 — they are
active proposals, not ratified specifications. However, if an open standard
consolidates in the 2027–2028 timeframe, being an early compatible implementation
would be a meaningful strategic advantage, particularly for the compliance positioning
(v3.0.0) and the Tier 2 shared state layer (v2.0.0). **Review trigger**: at the
start of each major milestone (v1.3.0, v2.0.0, v3.0.0 planning), check for
consolidation in this space before finalising the milestone's audit trail and skill
registry designs. Search terms: "OAGS agent governance spec", "AgentHub agent
manifest", "OpenAgentSpec", "agentic SDLC interoperability standard". If a credible
standard has emerged, open a spike item to assess compatibility cost before the
milestone sprint begins. Also monitor: CodeRabbit ($88M raised) has traceability
"coming via MCP" on their roadmap — if they pursue spec quality enforcement
seriously, they become the first credible commercial entrant into currently open
territory (see S0-22).

**Dynamic Workflows / parallel subagent governance (monitor from v1.3.0 onward)**:
Anthropic's Opus 4.8 (May 2026) introduced Dynamic Workflows in Claude Code — up to
1,000 total subagents, 16 concurrent, orchestrated from a single session. This is a
research preview. When it reaches general availability, the single-agent-per-session
assumption underlying most Tier 1 harness mechanisms will need explicit multi-agent
governance support. T1-N-01 through T1-N-03 lay the schema and concurrency
foundations. Full multi-agent governance (per-subagent audit trails, distributed
HALT propagation, swarm-level gate coordination) is planned for Tier 2 (v2.0.0).
**Review trigger**: at v2.0.0 planning, assess whether Dynamic Workflows has reached
general availability and what the production usage patterns look like before
finalising the Tier 2 multi-agent governance design. Key design rule established:
read-only agents (Read, Grep, Glob access only) are safe to run in parallel;
write agents (Edit, Write, Bash access) must run sequentially in their own lane
(source: freeCodeCamp software factory analysis, May 2026).

**The implementation layer — component mapping (Nate B Jones, 2026)**:
The following mapping validates that the harness covers the implementation layer
components identified as the primary value location in enterprise agentic workflows
(source: "The Trillion Dollar Agentic Workflow Opportunity"):

| Implementation layer component | Harness equivalent |
|---|---|
| Workflow design — which decisions the model makes, where handoffs are, what counts as done | Named workflows, three-checkpoint model, AGENTS.md prohibition table |
| Authority — what the agent is allowed to do, write vs read risk profiles | Governance gate, HALT sentinel, escalation triggers, high-risk commit classification (T1-L-08 ✅) |
| Evals — scoring adherence to specific business rules | Adversarial review gate, ReviewVerdict, false-positive eval pipeline (T1-L-10 ✅) |
| Audit trails — what gets logged, what an auditor can reconstruct | harness_events.jsonl, ai-review-log.jsonl, session ledger |
| Recovery and ongoing ownership — what happens when it goes wrong, who keeps it tuned | Dream phase self-improvement (T1-D-03 ✅), HITL approval queue (T1-C-02), incident→backlog (T1-L-07) |

The one component not owned by the harness is **data access** (which sources of
truth the agent reads, row/field-level permissions) — deliberately out of scope, as
this is contested territory between Salesforce, SAP, and data platform vendors. The
harness governs the delivery process, not the data layer. The labs themselves
(OpenAI, Anthropic) have acknowledged that the bottleneck for enterprise AI is the
implementation layer, not the model — validating that governance frameworks are the
defensible territory, not model wrappers.


### What the Research Validates

Two pieces of research directly validate specific framework mechanisms (not just the general domain):

- **Ford & Newman (O'Reilly, 2026)**: "Agents don't know what good looks like." Their `assert True` failure mode example — an agent replacing a failing test assertion rather than fixing the code — is precisely what the adversarial gate's system prompt is designed to catch. The separation between writing agent and reviewing model, and the "assume wrong until proven otherwise" framing, are the direct technical response to the novice-to-advanced-beginner limitation they describe.

- **Osmani (O'Reilly, 2026)**: "How to write a good spec for AI agents." The "curse of instructions" research (more rules → lower compliance per rule, even for GPT-4 and Claude) directly validates the 150-line skill length limit and the rule-count audit in T1-B-06/07. Fewer, clearer rules outperform comprehensive ones.

---

## Backlog Reference

Full implementation detail: `FRAMEWORK_BACKLOG.md`

| Document | Purpose | Audience |
|----------|---------|----------|
| `FRAMEWORK_ROADMAP.md` (this file) | Strategic direction, milestones, scope boundaries | Humans, first-time evaluators |
| `FRAMEWORK_BACKLOG.md` | Tactical implementation detail, item-by-item | Agents executing sprints |
| `harness_improvement_backlog.md` | Ad-hoc session observations, small findings | Ongoing capture |
| `CHANGELOG.md` | What shipped in each release | All |

---

*Extracted from and validated against GymBase, a multi-tenant SaaS gym management platform in active development. Public worked example planned for v1.1.0.*

---

### Unscheduled Backlog — Pending Foundations & Improvements

**Goal**: Memory system foundations make session history queryable and durable.
Reliability mechanisms replace voluntary compliance with structured recovery.
Security foundations address the novel context-injection attack surface before
broad community distribution.

> **Chain B — Self-Improvement Loop: fully delivered**, removed from this list.
> All seven items (`T1-I-00a`, `T1-I-00b`, `T1-D-00`, `T1-C-01`, `T1-I-03`,
> `T1-D-03`, `T1-I-05`) are confirmed ✅ in `Current Sprint Status` (v1.1.5,
> v1.3.1 Sprint 2) and the archived v1.1.5 milestone entry. The dream phase is
> live and producing proposals — the goal this table existed to track is met.

**Success criteria remaining open**:
- Memory tiering is formalised — hot/warm/cold with explicit retention policies (T1-I-01 partial, T1-I-06 tracked in v1.5.0)
- Agent escalation produces a structured approval request, not a HALT file (T1-C-02, still open)

**Memory system & reliability — still open**:

| ID | Item | Category | Status |
|----|------|----------|--------|
| T1-I-01 | Memory tiering (hot/warm/cold) | Memory | ⬜ (partial foundation delivered v1.3.1 — `memory_manager.py` three-tier scaffold; full tiering/retention not complete) |
| T1-I-06 | Memory retention policy | Memory | ⬜ (superseded — see v1.5.0 planned items for current scope: 90-day archival + recency weighting) |
| T1-C-02 | Structured HITL approval queue | Reliability | ⬜ |
| T1-C-03 | Harness health alerting | Reliability | ⬜ |
| T1-B-02 | Harness versioning | Environment | ⬜ |

> **Removed from this table (confirmed shipped elsewhere, previously shown ⬜ in error)**:
> `T1-I-00a`/`T1-I-00b` (Chain B, above), `T1-B-01` (✅ v1.3.1 Sprint 2 — UNIVERSAL_CONTEXT.md/tool shims),
> `T1-I-04` (✅ v1.3.1 Sprint 2 — AST staleness detection), `T1-B-03` (✅ v1.1.5),
> `T1-J-01` (✅ v1.3.4 — automatic session checkpoint + mid-task convention),
> `BUG-07`, `BUG-08` (both ✅, closed bug fixes with no remaining tracking value).

**Security foundations** *(addresses context-injection attack vector before broad community distribution)*:

| ID | Item | Category | Status |
|----|------|----------|--------|
| S0-16 | GPG-sign all releases | Supply chain | ⬜ |
| S0-17 | `validate.py --security` mode — hash and display governance files interactively | Verifiability | ⬜ |
| S0-18 | `docs/security/` — document every context injection point as a visibility baseline | Transparency | ✅ (absorbed by T1-K-02) |
| T1-K-07 | Quarantine structural bypass mitigation — active contexts and dream proposals bypass structural validation before ingestion; close the isolation-marker attack surface gap identified in T1-K-02 (cross-referenced from v1.4.0's deferred table) | Security | ⬜ |
| T1-K-05 | threat_model.md as a first-class governance artifact, separate from review_context_project.md; each threat paired with a deterministic `architecture_checks.py` rule (policy-as-code bridge to enterprise positioning) | Security | ⬜ |
| T1-K-03 | Governance file diff highlighting on upgrade (AGENTS.md, governance.md, workflows) — on by default | Security | ⬜ |

**Architecture**:

| ID | Item | Category | Status |
|----|------|----------|--------|
| T1-E-01 | Formalise skills as Tool ABC subclasses | Architecture | ⬜ |

T1-E-01 is sequenced here for two reasons: (1) T1-D-03 (dream phase distillation) ships with a documented verification gap — executable verification of proposed rules against session evidence requires the Tool ABC and SkillRegistry to be in place; closing that gap while the dream phase is being established avoids it staying open for over a year. (2) Formalising skills as Tool subclasses discovered via SkillRegistry pulls skill execution responsibility out of `ai_review.py`, directly addressing the structural coupling that accumulates when all skill dispatch is centralised. The Workflow Engine epic that follows also benefits from skills being proper Tool objects.

**Self-governance note**: `ai_review.py` has 32 imports accumulated across six development phases (review gate, diff classifier, budget enforcer, rebuttal handler, PageRank router, roster checker). A CI ratchet test (`tests/test_ai_review.py::TestAiReviewImportCount`) enforces the current count as a ceiling — it must not grow further. The T1-E-01 refactoring should bring it to ≤25 by extracting skill responsibilities into separate modules. Lower the ratchet ceiling from 32 to 25 when that work is complete.

**Workflow Engine epic — scoped and backlogged for v1.6.0**:
A data-driven workflow orchestrator replacing prose-driven agent interpretation with machine-readable phase definitions, FSM-backed state transitions, and per-phase completion contracts. Design document: [`workflow-engine-design.md`](../design/workflow-engine-design.md). Five backlog items (T1-W-01 through T1-W-05): workflow schema, workflow defaults YAML, `workflow_runner.py` (FSM via `transitions` library), `ContractEvaluator`, and bootloader integration. Chain B prerequisites now delivered — scope defined in v1.6.0 milestone and backlog section T1-W.