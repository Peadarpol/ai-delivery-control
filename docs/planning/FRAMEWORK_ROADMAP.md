# AI Delivery Control — Framework Roadmap

**Status**: Active Development
**Current Version**: 1.1.0
**Target Release**: v1.2.0
**Last Updated**: 2026-05-23

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
| T1-E-02 | LLMProvider ABC (AnthropicProvider, OpenAIProvider, OllamaProvider) | Provider portability | ✅ |
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

### v1.2.0 — Outer Loop 🔄 ACTIVE TARGET (Q3 2026)

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
| T1-H-08 | Branch-isolated model roster in compiled wiki | AST-generated roster of confirmed branch-isolated models injected into wiki; suppresses false-positive BRANCH_ISOLATION flags on verified models. Dependency: T1-H-06 ✅, T1-H-01 ✅. |
| T1-L-10 | False positive → eval regression pipeline | `false_positive_to_eval.py` — confirmed false positives create permanent "must not flag" guards in the T1-L-09 test suite; invoked automatically by rebuttal and structured bypass paths. Dependency: T1-L-09 ✅. |
| T1-G-07 | Structured SKIP_REASON enforcement | High-risk bypasses require structured JSON SKIP_REASON; malformed reasons rejected; valid reasons feed false positive pipeline automatically. Dependency: T1-L-08 ✅, T1-L-10. |
| T1-G-06 | Structured rebuttal protocol | FAIL verdict triggers a second-pass review with agent-provided structured evidence per finding; REBUTTAL_ACCEPTED unblocks commit and creates eval guard automatically. Dependency: T1-E-02 ✅, T1-G-03 ✅. |
| T1-L-01 | Spec quality gate | Before `/feature-implementation` begins, SPEC-XXX.md must exist and pass quality checks: acceptance criteria present, out-of-scope stated, architectural constraints identified, status APPROVED. Gate refuses to start without an approved spec. |
| T1-L-02 | `/business-analyst` workflow | Full state-machine workflow: requirement intake → user story extraction → BDD scenarios → spec drafting → acceptance criteria → traceability matrix → human approval gate. Agent drafts; human approves. |
| T1-L-03 | `/project-manager` workflow | How an approved SPEC becomes a prioritised backlog item with effort estimate and dependencies. Sprint planning and dependency resolution. |
| T1-L-04 | Requirement → commit traceability | Pre-commit check: non-trivial commits must reference a requirement ID. Closes the spec-to-code chain. `--no-trace` flag for infrastructure commits with reason logged. |
| T1-L-05 | Acceptance gate | Second AI review call with the spec as context, checking intent alignment not just code correctness. Produces `AcceptanceVerdict`: SATISFIED / PARTIAL / DIVERGED. Runs once per feature branch before PR. |
| T1-L-07 | Incident → backlog pipeline | `incident_to_backlog.py`: structured incident entry with root cause, affected commit SHA, which gate should have caught it, and proposed guard. Closes the production feedback loop. |
| T1-M-03 | Mid-session observability | Lightweight session health check: duration, tool call count, context load estimate, warning patterns. Diagnostic tool for when something feels off mid-session. |

---

### v1.3.0 — Self-Improvement & Reliability 📋 PLANNED (Q4 2026)

**Goal**: The dream phase becomes operational — the framework's temporal moat starts generating real proposals from real session data. Memory system foundations make session history queryable and durable. Reliability mechanisms replace voluntary compliance with structured recovery.

**The strategic context**: The adversarial gate is the same for every installation on day one. The dream phase is what makes each installation unique over time. This milestone is where the compound effect begins.

**Success criteria**:
- Dream phase produces at least one actionable proposal from real session data
- Session outcomes (success/partial/abandoned/escalated) are inferred and recorded automatically
- Memory tiering is formalised — hot/warm/cold with explicit retention policies
- Agent escalation produces a structured approval request, not a HALT file

**Chain B — Self-Improvement Loop** (implementation sequence from backlog):

| ID | Item | Category |
|----|------|----------|
| T1-I-00a | Consolidate audit logs → harness_events.jsonl | Memory prereq |
| T1-I-00b | Audit audit_logger.py wiring | Memory prereq |
| T1-D-00 | skill_ownership.yaml — dream phase routing map | Chain B prereq |
| T1-C-01 | Retrospective session outcome inference + post-commit heartbeat | Chain B foundation |
| T1-I-03 | Outcome-aware session startup orientation | Chain B |
| T1-D-03 | Dream phase distillation (distill_dream.py) | Chain B capstone |
| T1-I-05 | Memory contradiction detector (integrated into T1-D-03) | Chain B |

**Memory system & reliability**:

| ID | Item | Category |
|----|------|----------|
| T1-I-01 | Memory tiering (hot/warm/cold) | Memory |
| T1-I-04 | Automated memory staleness detection | Memory |
| T1-I-06 | Memory retention policy | Memory |
| T1-C-02 | Structured HITL approval queue | Reliability |
| T1-C-03 | Harness health alerting | Reliability |
| T1-B-01 | Universal context file (eliminates three-copy drift) | Environment |
| T1-B-02 | Harness versioning | Environment |
| T1-B-03 | Onboarding workflow | Reliability |
| T1-J-01 | Automatic checkpoint before file changes | Recovery |
| BUG-07 | Session heartbeat file modification failure | Bug fix |
| BUG-08 | Deprecated `datetime.utcnow()` in governance_check.py | Bug fix |

**Future epic — Workflow Engine** *(needs further analysis before implementation)*:
A data-driven workflow orchestrator replacing prose-driven agent interpretation with machine-readable phase definitions, FSM-backed state transitions, and per-phase completion contracts. Design document: [`workflow-engine-design.md`](file:///c:/projects/ai-delivery-control/docs/design/workflow-engine-design.md). Four components: workflow schema, workflow defaults YAML, `workflow_runner.py` (FSM via `transitions` library), and `ContractEvaluator`. Scope and backlog items to be defined after the Chain B items in this milestone are delivered.

---

### v1.4.0 — Intelligent Gate 📋 PLANNED (Q1 2027)

**Goal**: The gate becomes context-aware. PageRank identifies structurally important files. ADR annotations inject domain knowledge. Diff-aware routing activates only relevant review dimensions. The gate checks what matters, skips what doesn't, and explains its decisions.

**The strategic context**: The gate currently reviews every commit with the same intensity and the same dimensions. A documentation fix gets the same review as a migration touching branch isolation. This milestone gives the gate proportional intelligence — it focuses on what the diff actually affects and explains what it checked and what it skipped.

**Success criteria**:
- Gate routing adjusts review intensity based on PageRank centrality of changed files
- ADR annotations propagate domain context through the import graph
- Policy notes explain what was checked and what was skipped on every verdict
- Token budget per session is tracked and reported

**Chain A — Gate Intelligence** (follows backlog implementation phases):

| ID | Item | Phase | Category |
|----|------|-------|----------|
| T1-G-02 | Pre-flight shortcut (documentation/whitespace fast path) | 1 | Gate |
| T1-G-03 | ReviewVerdict Pydantic model | 1 | Gate structure |
| T1-H-06 | Compiled harness wiki layer (Gemma4 local, zero cost) | 2 | Wiki foundation |
| T1-D-05 | Model tiering configuration (Gemma4/Sonnet split) | 2 | Architecture |
| T1-H-01 | PageRank repo map generator | 3 | Repo intelligence |
| T1-H-02 | ADR annotation convention and wiki injection | 3 | Repo intelligence |
| T1-G-01 | Diff-aware capability routing with RouteDecision | 4 | Gate routing |
| T1-H-03 | Co-change blast radius estimator | 4 | Repo intelligence |
| T1-H-07 | Knowledge base lint pass | 4 | Quality |
| T1-G-04 | Policy notes in terminal output | 5 | Gate output |

**Observability**:

| ID | Item | Category |
|----|------|----------|
| T1-I-02 | Token budget tracking per session | Cost management |
| T1-D-01 | SQLite state index — single machine | State persistence |
| T1-D-02 | Cross-project harness health | Multi-project |

---

### v1.5.0 — Skill Quality & Developer Experience 📋 PLANNED (Q2 2027)

**Goal**: Skills become first-class managed artefacts with quality enforcement, deprecation lifecycle, and self-service authoring. Remaining developer experience improvements round out the Tier 1 feature set before the transition to multi-machine operation in v2.0.0.

**Planned items**:

| ID | Item | Category |
|----|------|----------|
| T1-B-04 | Skill deprecation mechanism | Skill management |
| T1-B-05 | Self-service skill authoring (`/create-skill` workflow) | Skill management |
| T1-B-06 | Skill length diagnostic audit | Skill quality |
| T1-B-07 | Skill decomposition and remediation | Skill quality |
| T1-E-01 | Formalise skills as Tool ABC subclasses | Architecture |
| T1-G-05 | Restricted globals sandbox for eval_runner.py | Security |
| T1-H-04 | Auto-generated context files at install time | Install experience |
| T1-H-05 | Dead-code confidence scoring | Repo intelligence |
| T1-J-02 | @-reference injection convention | Agent capability |
| T1-J-03 | Credential pool rotation for AI review gate | Agent capability |
| T1-J-04 | agentskills.io open standard compatibility | Ecosystem |
| T1-K-01 | Malicious package detection gate (guarddog) | Security |
| T1-M-04 | Minimal team usage guide | Documentation |

---

### v2.0.0 — Shared State (Tier 2) 📋 FUTURE

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

### v3.0.0 — Enterprise & Compliance (Tier 3) 📋 FUTURE

**Goal**: Production database infrastructure, compliance-grade audit trails, and formal regulatory control mappings.

**Compliance note**: Formal compliance control mappings (SOCI Act, ISM, PSPF) are planned for this milestone. Until those mappings exist with specific control references, audit trail output formats, and demonstrated compliance answers, the regulated industry claim is aspirational. v3.0.0 makes it concrete.

**Planned items** (Tier 3 — 12 items in backlog T3-A through T3-C):
- T3-A-01 through T3-A-03: PostgreSQL backend, migration framework, high availability
- T3-B-01 through T3-B-05: Row-level security, audit-grade immutability, SSO, data residency, RBAC
- T3-C-01 through T3-C-04: DORA metrics, Jira/Linear integration, harness-as-a-service API, compliance reporting

---

## Current Sprint Status

**Active milestone**: v1.2.0 (v1.1.0 shipped 2026-05-23)
**Sprint tracking**: `.agent/state/active_context.md`

**Priority order** (after current project work completes):
1. BUG-01 through BUG-06 — gate and bootstrap fixes (CRITICAL/HIGH)
2. Sprint 0 quick wins — manual, ~2–3 hours
3. T1-E-02 — LLMProvider ABC (provider portability)
4. T1-L-09 — framework self-test suite
5. T1-M-01/02/05 — agent operations, spec writing, stack coverage docs

---

## Strategic Context

### The Competitive Position

The framework's durable differentiation is not the context file patterns or named workflow conventions — these are being absorbed by IDE-native tooling. The durable differentiation is:

1. **The adversarial gate mechanism**: Separation of agents, adversarial framing, typed verdict schema, two-layer project context injection, persistent audit trail. Not assembled this way in any current vendor product.

2. **The self-improvement loop**: The dream phase creates a temporal moat. The longer the framework runs, the more calibrated its skills become to the specific failure patterns of the specific project. This cannot be fast-followed.

3. **The outer loop** *(v1.2.0)*: Specification quality governance and acceptance traceability are not things vendor tools will build because they require institutional governance knowledge.

4. **Compliance positioning** *(v3.0.0)*: SOCI, ISM, PSPF control mappings for Australian regulated industry contexts. Vendor tools will not go here.

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