# AI Delivery Control — Framework Roadmap

**Status**: Active Development
**Current Version**: 1.4.2
**Target Release**: v1.5.0
**Last Updated**: 2026-06-14

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

### v1.0.0 — Foundation ✅ SHIPPED (2026-05-21)

**Goal**: Extract the harness from its host project into a standalone installable framework.

**Delivered**:
- Bootstrap install script — under 10 minutes from zero to working harness
- Environment validation script
- Config-driven architecture checks
- Two-layer review context (universal + project)
- Universal + stack-pack skills (22 universal, python-fastapi stack pack)
- Tool supplement generation (CLAUDE.md, GEMINI.md, .cursorrules as thin shims)
- Pre-commit AI adversarial review gate with pre-flight shortcut, diff-aware routing, typed ReviewVerdict, policy notes output
- PageRank repository map injected into review context
- ADR annotation convention and compiled wiki layer (Gemma4 local)
- Dream phase self-improvement loop (session pattern detection, skill proposals, contradiction detection)
- Session lifecycle hooks (outcome inference, startup orientation, retention policy)
- Repository identity guard (P-14)
- Full documentation suite (getting started, configuration reference, customisation guide, AISDLC bootloader)

**Reference implementation**: GymBase (gym management SaaS, currently private). The framework was developed and validated over 6 months of active feature delivery. A public worked example is planned for v1.1.0.

---

### v1.1.0 — Demonstrably Working ✅ SHIPPED (2026-05-23)

**Goal**: Show the framework working in practice. The headline is the self-improvement loop producing real proposals from real sessions — not hygiene items. A developer landing on this project should be able to see the temporal moat in action, understand what makes the gate adversarial, and run the framework without an Anthropic account.

**Success criteria**:
- A public worked example shows a complete commit cycle: diff → routing decision → verdict → policy notes
- Dream phase outputs from real sessions are documented and visible
- The gate works with any LLM provider (Anthropic, OpenAI, Ollama)
- Repository signals a maintained project, not a personal workspace
- Convention vs enforcement is explicitly documented

**Planned items**:

| ID | Item | Category |
|----|------|----------|
| S0-01 | Remove `scratch/` directory | Repository hygiene |
| S0-02 | Narrow README positioning claim to match actual scope | Documentation |
| S0-03 | Add `CONTRIBUTING.md` | Community |
| S0-04 | Add GitHub issue templates | Community |
| S0-05 | Cut v1.0.0 GitHub release with release notes | Release |
| S0-06 | Add CI badge to README | Social proof |
| S0-07 | Document convention vs enforcement explicitly in README | Documentation | ✅ |
| S0-08 | Surface 2-3 representative skills in docs | Documentation |
| S0-09 | Add worked example: complete diff → routing → verdict cycle | Documentation |
| S0-10 | Publish dream phase example: real proposals from real sessions | Documentation |
| S0-11 | Add "What it prevents" section to README | Documentation | ✅ |
| S0-12 | Fix validate.py legacy filename warning | Validation | ✅ |
| S0-20 | Competitive positioning statement — add to README and docs | Documentation | |
| S0-24 | De-GymBase-ify functional code before public promotion | General framework decoupling | |
| T1-E-02 | LLMProvider ABC (AnthropicProvider, OpenAIProvider, OllamaProvider) | Provider portability | ✅ |

> **S0-24 scope note (identified 2026-06-02)**: Three targeted code changes —
> (a) extract `SYSTEM_PROMPT` in `ai_review.py` to a config-loaded template with
> project-neutral defaults (GymBase patterns move to `review_context_project.md`);
> (b) move `DOMAIN_REGISTRY` in `wiki_compile.py` from hardcoded Python to
> `.agent/config.yaml` so projects without GymBase ADR files skip gracefully;
> (c) move hardcoded directory paths in `build_route_decision()` to config.
> Must complete before S0-23 (README pre-Reddit additions) goes live.
| T1-L-06 | Explicit production scope statement in README and docs | Documentation | ✅ |
| T1-L-08 | High-risk commit classification for fail-open behaviour | Gate hardening | ✅ |
| T1-L-09 | Framework self-test suite (60 tests across 6 modules) | Testing | ✅ |
| BUG-01 | commit-msg hook not installed by bootstrap — already present since initial commit | Gate wiring | ✅ |
| BUG-02 | validate.py does not check commit-msg hook — already present | Validation | ✅ |
| BUG-03 | Gate reads empty diff on amend at commit-msg stage — ORIG_HEAD guard + empty tree fallback | Gate fix | ✅ |
| BUG-04 | PASS/PASS_FAST verdicts not written to audit log | Logging | ✅ |
| BUG-05 | ADR domain names not mapping to capability names | Routing fix | ✅ |
| BUG-06 | Gate calibration too aggressive — proportionate calibration + false-positive guard | Gate calibration | ✅ |
| T1-M-01 | Agent operations guide | Documentation | — (human-authored, deferred) |
| T1-M-02 | Spec writing guide | Documentation | — (human-authored, deferred) |
| T1-M-05 | Stack coverage acknowledgment | Documentation | ✅ |

**Note on T1-E-02 placement**: Provider agnosticism is moved from v1.3.0 to v1.1.0. Anthropic vendor lock-in is an immediate evaluation objection from any engineering team with data residency requirements. It should not remain a v1.3.0 problem for a framework positioning itself at governed delivery in constrained environments.

---

### v1.1.5 — Beta Ready ✅ SHIPPED (2026-05-29)

**Goal**: Ship a version that external developers can install, use, and upgrade
without hand-holding — while closing the two sharpest edges the framework
currently has (token surprise, gate false positives). Sits between v1.1.0 and
the Outer Loop milestone; does not pull forward any v1.2.0 outer loop content.

**The gap this addresses**: v1.1.0 delivered a working framework but not yet
an installable product. Beta testers need a clean upgrade path, a governed token
ceiling, and a gate that does not frustrate them with false positives before they
have built any trust in it. A beta tester who hits a $50 session overage or
cannot upgrade without manual file merging will not continue.

**Success criteria**:
- A developer with no prior framework knowledge can install, run the onboarding
  workflow, and make a governed commit in under 30 minutes
- A v1.1.0 installation upgrades to v1.1.5 without manual file merging
  (`upgrade.py --dry-run` completes cleanly)
- A session approaching the token budget ceiling receives a WARN before context
  exhaustion
- A gate FAIL on a false positive has a governed resolution path that does not
  require `SKIP_AI_REVIEW=1`
- Token consumption per session is visible in `session_ledger` by category

---

#### Theme 1 — Beta Installer Experience

| ID | Item | Effort | Status |
|----|------|--------|--------|
| HIB-006 | `bootstrap/upgrade.py` | Medium | ✅ |
| T1-B-03 | Onboarding workflow | Low | ✅ |
| S0-03 | `CONTRIBUTING.md` | Low | ✅ |
| S0-04 | GitHub issue templates | Low | ✅ |
| S0-05 | Cut v1.1.5 GitHub release + tag | Low | ✅ |
| S0-06 | CI badge | Low | ✅ |
| S0-08 | Surface representative skills in docs | Low | ✅ |
| S0-09 | Worked example (diff → routing → verdict cycle) | Low | ✅ |

Human-authored in parallel (no agent session required): T1-M-01 (agent
operations guide), T1-M-02 (spec writing guide), T1-M-04 (team usage guide).

S0-05 must be cut before any beta invitations are sent.

---

#### Theme 2 — Token Measurement & Calibration

| ID | Item | Effort | Status |
|----|------|--------|--------|
| T1-I-02 | Token budget tracking per session | Low | ✅ |
| T1-I-07 | Session token budget with WARN/HALT | Low | ✅ (2026-06-02 pre-sprint) — wiring of ai_review.py → session.json completed 2026-06-02 pre-sprint |
| T1-M-06 | Context compaction template | Low | ✅ |
| T1-G-08 | Diff size review strategy | Low | ✅ |

> **T1-I-07 resolved (2026-06-02 pre-sprint)**: The HALT mechanism, file format,
> and threshold logic existed at v1.1.5 delivery. The missing wiring —
> `ai_review.py` incrementing the session token counter after each review call —
> was completed as a pre-Sprint-1 item. The 80% WARN and 100% HALT thresholds
> now fire correctly during sessions that include review gate calls.

---

#### Theme 3 — Gate Trust & Calibration

| ID | Item | Effort | Status |
|----|------|--------|--------|
| T1-H-08 | Branch-isolated model roster in compiled wiki | Low | ✅ |
| T1-G-07 | Structured SKIP_REASON enforcement | Low | ✅ |
| T1-L-10 | False positive → eval regression pipeline | Low | ✅ |
| T1-G-06 | Structured rebuttal protocol | Medium | ✅ |

---

#### Recommended Sequencing

**Completed**: All items shipped in v1.1.5.2 patch release.

---

### v1.2.0 — Outer Loop ✅ SHIPPED (2026-05-31)

**Goal**: Govern the full delivery lifecycle from requirement to commit, not just from commit to repository.

**The gap this addresses**: The framework currently picks up governance at "an agent starts working." Everything before that — how a business need becomes a requirement, how a requirement becomes a spec good enough to build against — is ungoverned. A perfectly governed commit can implement the wrong thing. This milestone closes that gap.

**The deeper challenge**: The value of the outer loop is not in checking whether required fields are present in a spec file. It is in the institutional knowledge encoded in the `/business-analyst` and `/project-manager` workflows — what makes a requirement specific enough for an agent to act on, what acceptance criteria look like for AI-assisted delivery, how to scope work to avoid context window collapse mid-session. That knowledge is what the workflows need to capture.

**Success criteria**:
- A feature cannot start without an approved spec
- Every commit references the requirement it implements
- An acceptance gate checks intent alignment, not just code correctness
- The `/business-analyst` and `/project-manager` workflows encode actionable institutional knowledge, not just field validation

**Planned items**:

| ID | Item | Description |
|----|------|-------------|
| T1-L-01 | Spec quality gate | Before `/feature-implementation` begins, SPEC-XXX.md must exist and pass quality checks: acceptance criteria present, out-of-scope stated, architectural constraints identified, status APPROVED. Gate refuses to start without an approved spec. *Note: description enhanced with CodeRabbit two-tier check.* | ✅ |
| T1-L-02 | `/business-analyst` workflow | Full state-machine workflow: requirement intake → user story extraction → BDD scenarios → spec drafting → acceptance criteria → traceability matrix → human approval gate. Agent drafts; human approves. *Note: description enhanced with CodeRabbit Phase 0 intake, assumptions, and decisions_log feed.* Agent drafts; human approves. Scope: what to build and why. Effort estimation is T1-L-03's responsibility. | ✅ |
| T1-L-03 | `/project-manager` workflow | How an approved SPEC becomes a prioritised backlog item with effort estimate and dependencies. Sprint planning and dependency resolution. Receives an approved SPEC-XXX.md from T1-L-02. Owns effort estimates, task breakdown, dependency ordering, and sprint assignment. |
| T1-L-04 | Requirement → commit traceability | Pre-commit check: non-trivial commits must reference a requirement ID. Closes the spec-to-code chain. `--no-trace` flag for infrastructure commits with reason logged. |
| T1-L-05 | Acceptance gate | Second AI review call with the spec as context, checking intent alignment not just code correctness. Produces `AcceptanceVerdict`: SATISFIED / PARTIAL / DIVERGED. Runs once per feature branch before PR. |
| T1-L-07 | Incident → backlog pipeline | `incident_to_backlog.py`: structured incident entry with root cause, affected commit SHA, which gate should have caught it, and proposed guard. Closes the production feedback loop. |
| T1-M-03 | Mid-session observability | Lightweight session health check: duration, tool call count, context load estimate, warning patterns. Diagnostic tool for when something feels off mid-session. |

---

### v1.2.0.1 — Harness Gitignore Enforcements ✅ SHIPPED (2026-05-31)

**Goal**: Patch release resolving BUG-10 — bootstrap installations were not adding the required `.gitignore` block for operational state files, causing pre-commit conflict loops on fresh installs.

**The gap this addresses**: On every fresh install and upgrade, the harness creates files in `.agent/state/` that must not be committed (`session.json`, `HALT`, `.lock` files, `config.yaml.migration_backup`, the compiled wiki). Without the `.gitignore` block, these files appear as untracked changes. Developers staging them — inadvertently or deliberately — hit a pre-commit hook that rejects the commit, creating a conflict loop with no clear exit. Beta testers encounter this on their first governed commit.

**Delivered**:
- `bootstrap/install.py` — `update_gitignore()` appends the operational state block to the target project's `.gitignore` on every fresh install (idempotent; block is only appended if absent)
- `bootstrap/migrations/v1_2_0_to_v1_2_0_1.py` — migration module for existing v1.2.0 installations; safe header-anchored downgrade removes only the harness block
- `bootstrap/validate.py` — `validate_gitignored_states()` hardened: HALT absent from `.gitignore` → ERROR; `session.json` absent → WARN (not ERROR); `harness_events.jsonl` excluded (must be committed — it is the audit trail)
- `harness_version.txt`, `upgrade.py`, `downgrade.py` — version targets bumped to `1.2.0.1`
- Full test coverage: 184 tests pass (unit + integration)

| ID | Item | Category | Status |
|----|------|----------|--------|
| BUG-10 | Bootstrap does not write `.gitignore` block — pre-commit conflict loop on fresh installs | Install hardening | ✅ |

---

### v1.3.0 — Self-Improvement, Reliability & Security Foundations 📋 PLANNED (Q4 2026)

**Goal**: The dream phase becomes operational — the framework's temporal moat starts generating real proposals from real session data. Memory system foundations make session history queryable and durable. Reliability mechanisms replace voluntary compliance with structured recovery. Security foundations address the novel context-injection attack surface before broad community distribution.

**The strategic context**: The adversarial gate is the same for every installation on day one. The dream phase is what makes each installation unique over time. This milestone is where the compound effect begins.

**Success criteria**:
- Dream phase produces at least one actionable proposal from real session data
- Session outcomes (success/partial/abandoned/escalated) are inferred and recorded automatically
- Memory tiering is formalised — hot/warm/cold with explicit retention policies
- Agent escalation produces a structured approval request, not a HALT file

**Chain B — Self-Improvement Loop** (implementation sequence from backlog):

| ID | Item | Category | Status |
|----|------|----------|--------|
| T1-I-00a | Consolidate audit logs → harness_events.jsonl | Memory prereq | ⬜ |
| T1-I-00b | Audit audit_logger.py wiring | Memory prereq | ⬜ |
| T1-D-00 | skill_ownership.yaml — dream phase routing map | Chain B prereq | ✅ (2026-06-02 pre-sprint) |
| T1-C-01 | Retrospective session outcome inference + post-commit heartbeat | Chain B foundation | ✅ (v1.1.5) |
| T1-I-03 | Outcome-aware session startup orientation | Chain B | ✅ (v1.1.5) |
| T1-D-03 | Dream phase distillation (distill_dream.py) | Chain B capstone | ✅ (v1.1.5) |
| T1-I-05 | Memory contradiction detector (integrated into T1-D-03) | Chain B | ⬜ |

**Memory system & reliability**:

| ID | Item | Category | Status |
|----|------|----------|--------|
| T1-I-01 | Memory tiering (hot/warm/cold) | Memory | ⬜ |
| T1-I-04 | Automated memory staleness detection | Memory | ⬜ |
| T1-I-06 | Memory retention policy | Memory | ⬜ |
| T1-C-02 | Structured HITL approval queue | Reliability | ⬜ |
| T1-C-03 | Harness health alerting | Reliability | ⬜ |
| T1-B-01 | Universal context file (eliminates three-copy drift) | Environment | ⬜ |
| T1-B-02 | Harness versioning | Environment | ⬜ |
| T1-B-03 | Onboarding workflow | Reliability | ✅ (v1.1.5) |
| T1-J-01 | Automatic checkpoint before file changes | Recovery | ⬜ |
| BUG-07 | Session heartbeat file modification failure | Bug fix | ✅ |
| BUG-08 | Deprecated `datetime.utcnow()` in governance_check.py | Bug fix | ✅ |

**Security foundations** *(new — addresses context-injection attack vector before broad community distribution)*:

| ID | Item | Category | Status |
|----|------|----------|--------|
| S0-16 | GPG-sign all releases | Supply chain | ⬜ |
| S0-17 | `validate.py --security` mode — hash and display governance files interactively | Verifiability | ⬜ |
| S0-18 | `docs/security/` — document every context injection point as a visibility baseline | Transparency | ✅ (absorbed by T1-K-02) |
| T1-K-05 | Formal security review: context-injection attack surface published as `docs/security/attack-surface-review.md` | Security | ⬜ |
| T1-K-03 | Governance file diff highlighting on upgrade (AGENTS.md, governance.md, workflows) — on by default | Security | ⬜ |

**Architecture**:

| ID | Item | Category | Status |
|----|------|----------|--------|
| T1-E-01 | Formalise skills as Tool ABC subclasses | Architecture | ⬜ |

T1-E-01 is sequenced here for two reasons: (1) T1-D-03 (dream phase distillation) ships with a documented verification gap — executable verification of proposed rules against session evidence requires the Tool ABC and SkillRegistry to be in place; closing that gap while the dream phase is being established avoids it staying open for over a year. (2) Formalising skills as Tool subclasses discovered via SkillRegistry pulls skill execution responsibility out of `ai_review.py`, directly addressing the structural coupling that accumulates when all skill dispatch is centralised. The Workflow Engine epic that follows also benefits from skills being proper Tool objects.

**Self-governance note**: `ai_review.py` has 32 imports accumulated across six development phases (review gate, diff classifier, budget enforcer, rebuttal handler, PageRank router, roster checker). A CI ratchet test (`tests/test_ai_review.py::TestAiReviewImportCount`) enforces the current count as a ceiling — it must not grow further. The T1-E-01 refactoring should bring it to ≤25 by extracting skill responsibilities into separate modules. Lower the ratchet ceiling from 32 to 25 when that work is complete.

**Workflow Engine epic — scoped and backlogged for v1.6.0**:
A data-driven workflow orchestrator replacing prose-driven agent interpretation with machine-readable phase definitions, FSM-backed state transitions, and per-phase completion contracts. Design document: [`workflow-engine-design.md`](../design/workflow-engine-design.md). Five backlog items (T1-W-01 through T1-W-05): workflow schema, workflow defaults YAML, `workflow_runner.py` (FSM via `transitions` library), `ContractEvaluator`, and bootloader integration. Chain B prerequisites now delivered — scope defined in v1.6.0 milestone and backlog section T1-W.

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
| T1-K-02 | Formal security review: context-injection attack surface | Medium | Security | ✅ (v1.4.1) |
| T1-K-02a | Quarantine pattern as architectural context-injection mitigation | Low | Security | ✅ (v1.4.1) |
| T1-K-05a | Environment variable sanitisation in gate subprocess calls | Medium | Security | ✅ (v1.4.1) |
| T1-K-07 | Quarantine structural bypass mitigation | High | Security | ⬜ |

**Sprint planning notes (pre-v1.4.0)**:

- **Gemini CLI HALT coverage gap** (2026-06-08): T1-C-01 `--stop-hook` provides post-session governance for Claude Code only. No equivalent mechanism exists for Gemini CLI, making a completed Gemini session structurally indistinguishable from mid-task abandonment without manual spot-checks. Sprint planning should either scope a Gemini CLI stop-hook equivalent or establish a lightweight external verification protocol for all Gemini-executed delivery tasks. See decisions_log.md entry 2026-06-08 for full context.

---

### v1.4.1 — Outer Loop Quality & Security Review ✅ SHIPPED (2026-06-14)

**Goal**: Complete the outer loop grading/classification trio (spec grader, decision blocks, archetype classification) and deliver the formal context-injection security review before broader distribution. Split from v1.4.0 to keep that milestone's Medium/Medium-High gate-architecture work from compounding with this Medium-effort outer-loop and security batch.

**Planned items**:

| ID | Item | Effort | Category |
|----|------|--------|----------|
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

### v1.5.0 — Skill Quality & Developer Experience 📋 PLANNED (Q2 2027)

**Goal**: Skills become first-class managed artefacts with quality enforcement, deprecation lifecycle, and self-service authoring. Remaining developer experience improvements round out the Tier 1 feature set before the transition to multi-machine operation in v2.0.0. T1-B-04/05/06/07 depend on T1-E-01 (Tool ABC), which is delivered in v1.3.0 — the sequencing is now correct.

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

---

### v1.6.0 — Workflow Engine 📋 FUTURE

**Goal**: Replace prose-driven agent interpretation of workflow phases with a data-driven FSM-backed orchestrator. Agents stop inferring phase context from convention and start reading machine-readable state written and enforced by the framework.

**The strategic context**: Every workflow in the harness is currently a prose `.md` file that agents follow by reading and interpretation. There is no enforcement that an agent correctly identifies the current phase, satisfies phase exit conditions, or transitions in the correct order. The Workflow Engine makes phase enforcement as rigorous as commit-level enforcement — the gate checks commits; the runner checks phases. Design document: [`workflow-engine-design.md`](../design/workflow-engine-design.md).

**Prerequisites**: T1-E-01 (skills as Tool ABC subclasses, delivered v1.3.0) required before T1-W-03. T1-D-01 (SQLite state index, v1.4.0) is a soft dependency — flat-file state is the authoritative source of truth; SQLite adds queryability.

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
- T2-B-01: Distributed HALT sentinel
- T2-B-02 through T2-B-04: Role-based governance, remote audit trail, team dashboard
- T2-C-01 through T2-C-03: Team bootstrap, shared skill registry, team dream phase
- T2-D-01 through T2-D-04: Node.js/Go stack packs, stack-agnostic pre-commit, Ollama provider

### v3.0.0 — Enterprise & Compliance (Tier 3) (Enterprise Edition) 📋 FUTURE

**Goal**: Production database infrastructure, compliance-grade audit trails, and formal regulatory control mappings.

**Compliance note**: Formal compliance control mappings (SOCI Act, ISM, PSPF) are planned for this milestone. Until those mappings exist with specific control references, audit trail output formats, and demonstrated compliance answers, the regulated industry claim is aspirational. v3.0.0 makes it concrete.

**Planned items** (Tier 3 — 12 items in backlog T3-A through T3-C):
- T3-A-01 through T3-A-03: PostgreSQL backend, migration framework, high availability
- T3-B-01 through T3-B-05: Row-level security, audit-grade immutability, SSO, data residency, RBAC
- T3-C-01 through T3-C-04: DORA metrics, Jira/Linear integration, harness-as-a-service API, compliance reporting

**Enterprise Edition go-to-market note**: The enterprise product requires a fundamentally different go-to-market than the Developer Edition. The temporal moat (dream phase) that differentiates the Developer Edition is less relevant to enterprise procurement. Enterprise differentiators are compliance control mappings, policy-as-code governance (T1-K-05, HIB-032), audit-grade immutability (T3-B-02), and separation of duties (T2-B-02). The enterprise product should be considered a parallel workstream rather than a future milestone — potentially delivered as a services engagement wrapping the current Tier 1/2 framework before the full v3.0.0 infrastructure is built. The PE distribution channel identified in strategic context is accessible at Developer Edition maturity; it does not require v3.0.0. Source: strategic planning session, June 2026.

---

## Current Sprint Status

v1.x series = Developer Edition — solo developer to 3-person team, flat-file state, convention-heavy governance, installs in under 10 minutes.

**Active milestone**: v1.5.0 (v1.4.2 shipped 2026-06-14)
**Sprint tracking**: `.agent/state/active_context.md`

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

**Active milestone**: v1.4.2
**v1.3.x family**: v1.3.0 ✅, v1.3.1 ✅, v1.3.2 ❌ (deferred), v1.3.3 ✅, v1.3.4 ✅
**v1.4.x family**: v1.4.0 ✅, v1.4.1 ✅, v1.4.2 ✅
**Next major milestone**: v1.5.0 (planning begins)

---

## Strategic Context

> **Capability Inventory (2026-06-02)**: A direct code inspection inventory was
> generated at `docs/planning/CAPABILITY_INVENTORY.md`. It is the authoritative
> source of truth for what is actually delivered vs. what the backlog describes.
> Where inventory findings conflict with backlog ✅ markers, the inventory takes
> precedence. Key findings: T1-D-00 blocking dream phase routing; GymBase coupling
> in functional code (S0-24); T1-I-07 partial delivery; BUG-11/12/13.
> Sequencing observations in the inventory §3 should be reviewed before each
> milestone planning session.

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

**Private equity as a distribution channel (strategic signal, Nate B Jones, 2026)**:
PE firms own thousands of mid-market companies — finance, ops, support, procurement,
compliance — and are actively seeking AI governance frameworks to deploy across
portfolios. A framework that installs in under 10 minutes, provides a governed
delivery structure, and adapts to each project's failure patterns (dream phase) is
a portfolio-level governance standard, not just a per-developer tool. This
distribution path is distinct from individual developer adoption and from enterprise
direct sales. At v2.0.0 (shared state, team features), assess whether PE portfolio
deployment is a viable go-to-market motion alongside community adoption.

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