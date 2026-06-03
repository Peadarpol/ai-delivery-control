# AI Delivery Control — Session Updates Consolidated
**Source**: Claude conversation, June 2026
**Purpose**: Complete set of backlog entries, roadmap additions, and plan amendments
for Gemini to apply to the framework repositories.
**Applies to**: `FRAMEWORK_BACKLOG.md`, `FRAMEWORK_ROADMAP.md`,
`v1.3.0 Sprint 1 Implementation Plan`, `harness_improvement_backlog.md`

---

## Part 1 — New Backlog Items for `FRAMEWORK_BACKLOG.md`

### Sprint 0 (pre-promotion quick wins) — add after S0-18

```markdown
| S0-19 | **OAGS / agent governance interoperability — recurring ecosystem monitor** |
At the start of each major milestone planning session (v1.3.0, v2.0.0, v3.0.0),
review progress on emerging open standards for agent governance interoperability
(OAGS, AgentHub, OpenAgentSpec or successor). If a credible standard has
consolidated, open a spike item before finalising that milestone's audit trail and
skill registry designs. Not an implementation item — a recurring review prompt.
Full context in `FRAMEWORK_ROADMAP.md` §Strategic Context. | Low | ⬜ (recurring) |

| S0-20 | **Competitive positioning statement — add to README and docs** | The
competitive landscape confirms the harness occupies genuinely open territory in
outer loop governance, session lifecycle, persistent memory, self-improvement, and
solo developer viability. No commercial tool covers more than 6 of the 15 capability
dimensions assessed. Add a concise "How this differs from AI code review tools"
section to README.md that makes the distinction explicit: those tools review PRs
submitted by humans; this framework governs sessions run by AI agents. Prevents the
harness being dismissed as "another CodeRabbit" by evaluators who scan the README
quickly. Documentation only, no code. | Low | ⬜ |

| S0-21 | **AI SBOM capability marker — future scope note** | Secure Code Warrior's AI
SBOM (tracking which AI model generated which commits as a compliance artefact) is
absent from the harness backlog. For Tier 3 compliance positioning (v3.0.0), this
becomes relevant — auditors in regulated industries will eventually ask "which model
generated this code and under what governance?" The harness already captures model
and provider in ReviewVerdict (T1-G-03) and harness_events.jsonl, meaning the raw
data exists. A future item should aggregate this into an AI SBOM export (per-commit:
model, provider, verdict, session_id). Captured here as a named future scope marker
for T3-C series. No implementation now. | — | ⬜ (future) |

| S0-22 | **CodeRabbit outer loop signal — add to OAGS ecosystem monitor (S0-19)** |
CodeRabbit ($88M raised, 100K+ open source projects) has traceability "coming via
MCP" on their roadmap. If they pursue spec governance seriously, they become the most
credible commercial entrant into currently open territory. Monitor specifically: does
CodeRabbit's MCP context pull expand from ticket linking to spec quality enforcement?
If yes, assess differentiation strategy. Add as a named watch item alongside the
OAGS/AgentHub standards monitor in FRAMEWORK_ROADMAP.md Strategic Context. |
Low | ⬜ (recurring) |

| S0-23 | **README pre-Reddit additions — three concrete sections** | Before any public
promotion (Reddit, LinkedIn, community posts), add three specific sections to
README.md: (1) **Gate verdict output block** — a realistic terminal output example
showing the gate in action: routing decision, specific finding with file:line
citation, fix suggestion, policy notes explaining what was checked vs skipped. Makes
the product visible in 30 seconds without installing. (2) **"What the gate caught"
paragraph** — one real incident from GymBase development where the gate caught a
specific bug (the branch isolation violation in the booking join query is the
canonical example): what the agent wrote, what the gate flagged, what would have
happened in production, how long the fix took. Visceral evidence that the gate works
on real bugs, not just style issues. (3) **"How this differs from CodeRabbit/Bito"
paragraph** — one short paragraph addressing the most likely dismissal: "those tools
review PRs submitted by humans; this framework governs sessions run by AI agents —
a different problem requiring a different mechanism." Human-authored, no code, no
agent session required. | Low | ⬜ |
```

---

### T1-B series — add T1-B-05a after T1-B-05, T1-B-07a after T1-B-07

```markdown
| T1-B-05a | **Interpreter skill pattern for deterministic governance skills** | The
LangChain Deep Agents "interpreter skills" pattern (May 2026) formalises a two-layer
skill structure: instruction layer (SKILL.md — when to use, how to call) + execution
layer (code module — deterministic procedure). This is a more precise articulation of
what T1-E-01 (Tool ABC subclasses) is building toward. When implementing T1-E-01,
apply this framing explicitly: governance-critical skills (branch-isolation,
schema-hardening, security-audit, migration-patterns) should implement their
deterministic checks as `run()` methods in the Tool subclass rather than as LLM
instructions. The LLM synthesises the overall verdict from typed Tool outputs; it
does not perform the checks itself. Design principle to encode in the Tool ABC
docstring: "discretion on the outside, determinism on the inside." The instruction
layer (SKILL.md) tells the agent when the skill applies; the execution layer
(tool.py) defines what actually runs. This also strengthens the eval signal
(T1-L-09): tests can assert "did the expected Tool method get called with the
expected inputs?" rather than "did the agent generally follow the skill instructions?"
Dependency: T1-E-01. No new implementation — a design constraint to apply during
T1-E-01 implementation. | Low | ⬜ |

| T1-B-07a | **Anti-rationalization tables as required skill element** | Addy Osmani's
Agent Skills (27K stars, May 2026) identifies prewritten anti-rationalization tables
as the most distinctive and effective element of production skill design. The
argument: LLMs are excellent rationalizers and will produce plausible justifications
for skipping governance steps unless those justifications are preemptively rebutted
in the skill itself. When implementing T1-B-07 (skill decomposition and remediation),
add an anti-rationalization section as a required element of the reformed skill format
for all high-risk skills (branch-isolation, schema-hardening, security-audit,
migration-patterns, verification-before-completion). Format: a small table of common
agent excuses paired with written rebuttals. This is the upstream deterrent that
complements the gate's downstream hard stop. Source: Osmani, "Agent Skills",
O'Reilly Radar, May 2026. | Low | ⬜ |
```

---

### T1-G series — add T1-G-09 after T1-G-08

```markdown
| T1-G-09 | **User-facing rigor profile system** | nWave's `/nw-rigor lean | standard |
thorough | exhaustive` profile system (499 stars, production-validated) demonstrates
that making the cost/benefit tradeoff explicit and user-controlled is a meaningful UX
improvement over automatic routing. The harness has `review_intensity: standard |
elevated | critical` routing (T1-G-01 ✅) and model tiering (T1-D-05 ✅) but no
user-facing dial. Add a `/harness-rigor` command (or `agent.rigor_profile` config
key) mapping to the existing routing infrastructure: `lean` (PASS_FAST threshold
lowered, budget model only, no elevated routing), `standard` (current default
behaviour), `thorough` (elevated routing on all changed files, review model always),
`exhaustive` (critical intensity, mutation testing gate enabled, fail-closed on
provider unavailability). Profile persists in `session.json` for the duration of the
session. Zero change to gate mechanics — purely a UX layer on top of existing
routing. Dependency: T1-G-01 ✅, T1-D-05 ✅. | Low | ⬜ |
```

---

### T1-L series — add T1-L-00 between T1-L series header and T1-L-01; add T1-L-01a after T1-L-01; add T1-L-08a after T1-L-08

```markdown
| T1-L-00 | **Outer loop methodology profile system** | The outer loop components
(T1-L-01 through T1-L-07) were designed against a specific SDLC philosophy: macro
scope known upfront, incremental delivery toward that known end state, formal spec
gate before each feature begins. This is a coherent and defensible position but is
not the only legitimate approach. Different harness users will operate under different
SDLC methodologies, and outer loop components that hard-enforce one methodology's
assumptions will create adoption friction for teams working differently — and may
actively harm them by forcing governance theatre rather than genuine governance.
**Three archetypes have been identified**: (1) **Discovery mode** — early-stage or
exploratory projects where the end state is genuinely unknown; scope emerges from
delivery; a blocking spec gate is inappropriate. (2) **Incremental-with-known-scope**
(current default) — macro scope is held by the architect, delivery is feature-by-
feature with a spec per feature; this is the harness's designed-for mode. (3)
**Contractual/regulated** — fixed requirements baseline, formal change control, full
traceability from requirement ID through test evidence to commit; the harness needs
to enforce the chain, not just recommend it. **Inner loop is unaffected**: commit
gate, architecture checks, session lifecycle, and skill governance are methodology-
independent and remain fully enforced regardless of `outer_loop.mode`. **Scope**:
(a) Add `outer_loop.mode: discovery \| incremental \| contractual` to
`.agent/config.yaml` with `incremental` as default. (b) Audit each outer loop item
(T1-L-01 through T1-L-07) and classify every hard-enforcement decision as either
*methodology-independent* (enforce universally) or *methodology-specific*
(configurable by mode). (c) For each methodology-specific enforcement, define
behaviour per mode — e.g. spec gate in `discovery` mode downgrades from BLOCK to
WARN with a logged advisory; in `contractual` mode T1-L-04 traceability check
becomes mandatory with no `--no-trace` flag available. (d) **Retrofit T1-L-01
(`check_spec.py`) and T1-L-02 (`/business-analyst` workflow)** — both were delivered
under the implicit `incremental` assumption; add mode-awareness so `discovery` mode
downgrades the spec gate to advisory and `contractual` mode tightens the assumption-
resolution requirement. Since both are early-stage delivered items with limited field
use, retrofit cost is low and correctness benefit is high. (e) Review the
`/business-analyst` and `/project-manager` workflows to determine whether named
per-mode variants are required or whether a single workflow with mode-conditional
steps is sufficient. (f) Document the default mode's assumptions explicitly in
`docs/getting-started.md` so users on other methodologies understand what they are
opting into or out of. **Sequencing**: T1-L-00 is a design gate for all remaining
outer loop work. The config schema and retrofit (steps a–d) should be completed
before T1-L-03 through T1-L-07 implementation begins. Steps e–f can be completed
in the same sprint. Estimated effort: Low (design + audit + config schema) + Low
(T1-L-01/T1-L-02 retrofit). No agent session required for the audit phase. |
Low | ⬜ |

| T1-L-01a | **Outcomes registry — design-time spec collision detection** | nWave's
outcomes registry (v3.14, May 2026) flags spec-level collisions before code is
written using type-shape + keyword Jaccard similarity. T1-L-01 (spec quality gate)
checks structural quality of individual specs but does not detect when two specs
describe overlapping behaviour. Add `nwave-ai outcomes check-delta`-equivalent
functionality to `check_spec.py`: when a new SPEC-XXX.md is submitted for approval,
scan existing approved specs in `docs/planning/specs/` for Jaccard similarity on
acceptance criteria keywords. Threshold: `similarity > 0.6` emits a WARN listing
the candidate overlapping spec(s); `similarity > 0.85` emits a BLOCK. False-positive
rate expected to be low since specs with genuinely different scope will have low
keyword overlap. Stdlib only: `collections.Counter` for term frequency, no external
NLP dependencies. Mode-aware per T1-L-00: in `discovery` mode, downgrades BLOCK to
WARN. Dependency: T1-L-01 ✅, T1-L-00. | Low | ⬜ |

| T1-L-08a | **Acceptance test generation from specs (future scope marker)** |
Machine-executable acceptance criteria — spec acceptance criteria that compile
directly to runnable test stubs — is out of scope for Tier 1 but is the research
ideal beyond T1-L-05. The LangChain interpreter skills pattern (T1-B-05a) and
nWave's DISTILL → DELIVER TDD terminal pair both point toward this capability.
Captured as a named future scope marker for Tier 2 outer loop planning. Depends on:
T1-L-00 (contractual mode is the natural home for this), T1-L-05 delivered. | — |
⬜ (future) |
```

---

### T1-M series — add T1-M-07 after T1-M-06

```markdown
| T1-M-07 | **"Context anxiety" — named concept for agent operations guide** |
LangChain names "context anxiety" (May 2026) as the phenomenon where models near
context window limits start taking shortcuts, compressing procedures, or producing
"good enough" outputs without following the required process. This is the named
failure mode that T1-I-07 (token budget WARN/HALT ✅), T1-M-06 (context compaction
template ✅), and the session lifecycle protocol are all designed to prevent. Add the
named concept to T1-M-01 (agent operations guide) when written: developers should
know the term, recognise the symptoms (agent re-reading same files, contradicting
earlier decisions, producing plausible-but-incomplete outputs), and know that the
token budget WARN at 80% is the early signal. Also relevant to T1-M-02 (spec writing
guide): under-scoped specs that expand mid-session are a primary trigger of context
anxiety in delivery agents. Also note the related "context drift" failure mode
(freeCodeCamp, May 2026): once a wrong architectural assumption enters the context,
the model keeps building on top of it — the discard-and-restart rule applies when
architectural assumptions are wrong, not just when small edits need correction.
Documentation note only — no code. | Low | ⬜ |
```

---

### T1-N series — new series, add after T1-M

```markdown
### T1-N: Multi-Agent Governance
*Source: Anthropic Opus 4.8 Dynamic Workflows (research preview, May 2026).
The single-agent-per-session assumption underlying Tier 1 mechanisms requires
explicit multi-agent governance foundations before Dynamic Workflows reaches
general availability.*

| T1-N-01 | **Multi-agent topology: session hierarchy schema** | Dynamic Workflows
(Opus 4.8, research preview) introduces parallel subagent execution — up to 16
concurrent agents in a single Claude Code session. The current session model assumes
a single execution thread. Add `parent_session_id` (nullable) and `agent_role`
(orchestrator | subagent | solo) fields to `session.json` schema and
`harness_events.jsonl` entry schema. Solo sessions (current default) set
`parent_session_id: null` and `agent_role: solo` — zero behaviour change for
existing users. Orchestrator sessions set `agent_role: orchestrator`. Subagent
sessions set `agent_role: subagent` and `parent_session_id` to the orchestrator's
session UUID. This is a schema extension, not a schema break. Implement in
`init_session.py` as an opt-in: `agent.role: solo | orchestrator | subagent` in
`config.yaml`, defaulting to `solo`. Dependency: none. | Low | ⬜ |

| T1-N-02 | **Gate concurrent write safety for parallel subagents** |
`.ai-review-log.jsonl` is a single append-only file written by `ai_review.py` at
commit time. Under Dynamic Workflows with multiple concurrent subagents committing
simultaneously, concurrent writes will produce corrupted JSONL entries. Add file
locking to `_persist_verdict()` in `ai_review.py`: `fcntl.flock()` on POSIX,
`msvcrt.locking()` on Windows, with a timeout of 5 seconds and a WARN verdict logged
if the lock cannot be acquired. Same pattern should be applied to
`harness_events.jsonl` writes in `governance_check.py` and `init_session.py`. This
is a correctness fix for concurrent use, not a feature. Zero behaviour change for
solo sessions. | Low | ⬜ |

| T1-N-03 | **HALT sentinel subagent propagation** | The HALT sentinel is checked by
`check_halt.py` at session start and by the pre-commit hook. In a Dynamic Workflow,
the orchestrator session may receive HALT while subagents are already in flight with
no mechanism to propagate the signal. For Tier 1 (all agents on the same machine):
add HALT file check to the pre-commit hook directly — any subagent committing will
check for HALT before the gate fires. Update `AGENTS.md` to instruct subagents to
check for HALT before each commit explicitly. For Tier 2 (distributed HALT via MCP
server, T2-B-01): the MCP-based HALT check becomes the correct solution for agents
on different machines. Document the limitation explicitly: Tier 1 HALT propagation
works for same-machine subagents only. | Low | ⬜ |

| T1-N-04 | **Prompt injection defence note for Opus 4.8 regression** | Opus 4.8
shows increased prompt injection vulnerability vs Opus 4.7 (9.6% vs 6.0% attack
success rate per Gray Swan red-teaming). The `<untrusted_*>` XML tag defence in
`pm_scaffold.py` and `acceptance_check.py` (Sprint 1) is the correct mitigation and
should be applied consistently to any new LLM-calling script. Add a note to
`docs/security/` (S0-18, when implemented) and to `review_context_universal.md`
flagging this regression and confirming the XML isolation pattern as the required
defence for all scripts passing untrusted content to LLM providers. Documentation
only. | Low | ⬜ |

| T1-N-05 | **`report_findings` structured output pattern for subagents** |
Anthropic's orchestration mode reference implementation (June 2026) uses a
`report_findings` tool that subagents call exactly once to return structured JSON:
`summary`, `findings[]` with `claim`, `evidence`, and `severity`. This is directly
compatible with the existing `ReviewVerdict` Pydantic model (T1-G-03 ✅) and the
T1-N-01 session hierarchy schema. When implementing T1-N-01 (multi-agent session
hierarchy), adopt the `report_findings` pattern for subagent output rather than
prose returns — subagents write structured findings, the orchestrator aggregates them
into a typed verdict. Enables cross-subagent finding deduplication and severity-
weighted aggregation in `harness_health.py`. Dependency: T1-N-01. | Low | ⬜ |

| T1-N-06 | **`pause_turn` stop reason handling** | Opus 4.8 introduces a `pause_turn`
stop reason indicating the model is mid-computation and needs to continue. The
current gate circuit breaker logic treats unexpected stop reasons as errors.
`pause_turn` must be handled as a continuation signal — not an error, not a verdict.
Add explicit `pause_turn` handling to `ai_review.py`'s response loop: when stop
reason is `pause_turn`, continue the conversation with an empty user turn (per
Anthropic's reference implementation pattern) rather than failing open or closed.
This is a correctness fix for Opus 4.8 compatibility, not a feature. | Low | ⬜ |
```

---

### harness_improvement_backlog.md — add HIB-NEW-01 through HIB-NEW-03

```markdown
| HIB-NEW-01 | **Review gate model diversification guidance** | Same-model review
creates correlated blind spots — a hallucination the writing agent produces may not
be caught by a reviewer using identical weights and priors (confirmed by multi-agent
monoculture research). Add guidance to `docs/configuration.md` and
`review_context_universal.md` recommending that `ai_review.provider` and
`ai_review.model` be configured to a *different model family* than the primary
writing agent where possible (e.g. writing on Claude Code → review gate on OpenAI or
Ollama). Document why same-model is still better than no gate, but flag the
limitation explicitly. No code change required — documentation and configuration
guidance only. Source: Deep Research gap analysis, June 2026. | Low | ⬜ |

| HIB-NEW-02 | **T1-E-01 sandboxing requirement** | Add explicit sandboxing
requirement to the T1-E-01 (Tool ABC subclasses) description before implementation
begins. Code-as-skill (Tool subclasses with `run()` methods) requires sandbox
execution — restricted builtins, no filesystem write outside the project path, no
network calls unless explicitly declared in `schema()`. The existing T1-G-05
(restricted globals for eval_runner.py) covers eval cases; T1-E-01 needs the same
treatment applied to the Tool ABC `run()` contract itself. Constraint should be
captured in the `Tool` base class design before the first concrete subclass is
written. Source: Deep Research gap analysis, June 2026. | Low | ⬜ |

| HIB-NEW-03 | **False-positive rate as proactive harness health metric** |
`harness_health.py` currently tracks verdict distributions but does not compute
per-capability false-positive rate as a trend. Add: for each capability
(BRANCH_ISOLATION, ANTI_PATTERNS, etc.), compute `bypass_rate =
structured_bypasses_last_30d / (FAIL_verdicts_last_30d +
structured_bypasses_last_30d)`. If `bypass_rate > 0.15` for any capability, emit a
DEGRADING signal and automatically generate a dream phase proposal flagging the
calibration issue — rather than waiting for a developer to file a rebuttal. Closes
the gap between reactive false-positive handling (T1-L-10 ✅, T1-G-06 ✅) and
proactive calibration monitoring. Source: Google's >10% false-positive threshold for
rule disablement; Deep Research gap analysis, June 2026. | Low | ⬜ |
```

---

## Part 2 — Additions to `FRAMEWORK_ROADMAP.md`

### 2a — Strategic Context section: add three new paragraphs after the existing "The Competitive Position" subsection

```markdown
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
```

---

### 2b — Recommended Execution Sequence section: add v1.3.0 pre-sprint gate block

Add this block immediately before the `### v1.3.0 Sprint` items in the execution
sequence:

```markdown
**v1.3.0 pre-sprint design gate**:
T1-L-00 (outer loop methodology profile system) must be completed before any
T1-L-03 through T1-L-07 implementation begins. Includes retrofit of already-
delivered T1-L-01 (check_spec.py) and T1-L-02 (/business-analyst workflow) to
add mode-awareness. Early-stage delivery means retrofit cost is low; correctness
benefit is high. Estimated: half-day design + audit, small code changes to
check_spec.py and business-analyst.md.
```

---

## Part 3 — Amendments to `v1.3.0 Sprint 1 Implementation Plan`

Six amendments to apply to the existing Sprint 1 plan document. Apply each as
an addition or replacement at the indicated location.

### Amendment 1 — T1-L-00 completion checklist

Add immediately after the existing `> [!CAUTION]` T1-L-00 pre-sprint gate block:

```markdown
> [!IMPORTANT]
> **T1-L-00 Completion Checklist — verify all six before proceeding**
> - [ ] `outer_loop.mode: discovery | incremental | contractual` added to
>       `bootstrap/templates/config.yaml.template` with `incremental` as default
> - [ ] `check_spec.py` retrofitted — `discovery` mode downgrades gate to advisory
>       (WARN + exit 0); `contractual` mode tightens assumption-resolution requirement
> - [ ] `business-analyst.md` updated — mode-conditional steps documented at each
>       phase where enforcement differs by mode
> - [ ] `outer_loop.mode` read and respected in `check_traceability.py` design
>       confirmed (discovery → advisory; contractual → no `--no-trace` available)
> - [ ] `outer_loop.mode` read and respected in `acceptance_check.py` design
>       confirmed (discovery → advisory; contractual → `--strict` implied)
> - [ ] Mode assumptions documented in `docs/getting-started.md` — users understand
>       which mode they are in and what it means for outer loop enforcement
```

### Amendment 2 — `pm_scaffold.py` offline fallback

Add to the `pm_scaffold.py` spec under "Decoupled Model Handshake":

```markdown
- **Offline fallback (`--offline` flag or when budget provider unreachable)**:
  Scaffolds directly from parsed Gherkin scenarios without LLM synthesis. Each
  scenario becomes a single task entry with description derived from the scenario
  label, layer inferred from keyword matching (`schema`/`migration` → DB/Migration,
  `endpoint`/`request` → API/Service, `page`/`screen` → UI), and a default estimate
  of `3 pts` with a `[Est: manual review required]` marker. Writes a
  `⚠️ OFFLINE MODE` header to the task file so the developer knows estimates need
  human review. Exits 0 — the outer loop remains functional without a provider.
```

Add to `tests/test_pm_scaffold.py` verification plan:
```markdown
- Test `--offline` flag produces skeleton task file with `[Est: manual review
  required]` markers and `⚠️ OFFLINE MODE` header.
- Test provider unavailability falls back to offline mode automatically (exits 0,
  not exits 1).
```

### Amendment 3 — Gherkin parser prose-only fallback

Add to the `pm_scaffold.py` spec under "Robust Semantic Parsing":

```markdown
- **No Gherkin detected fallback**: If the `# Acceptance Criteria` section contains
  no lines matching `\bGiven\b`, `\bWhen\b`, or `\bThen\b`, emit a clear warning:
  `⚠️ [PM_SCAFFOLD] No Gherkin scenarios detected in SPEC-XXX acceptance criteria.
  Falling back to prose extraction — estimates will require manual review.`
  Attempt LLM synthesis from prose directly (or offline skeleton if `--offline`).
  Does not exit 1 — prose specs are valid in `discovery` mode (per T1-L-00). Writes
  a `⚠️ NO GHERKIN` header to the task file.
```

Add to `tests/test_pm_scaffold.py`:
```markdown
- Test prose-only acceptance criteria triggers warning and fallback, not exit 1.
- Test mixed Gherkin + prose section parses Gherkin scenarios only, ignores prose.
```

### Amendment 4 — `AcceptanceVerdict` scenario label edge cases

Add to the `AcceptanceVerdict` field format note in Component 3:

```markdown
> **Label extraction edge cases**: The LLM prompt must handle three label formats
> found in practice:
> - Standard: `Scenario: User can log in with valid credentials`
>   → extracted as `"User can log in with valid credentials"`
> - Numbered: `Scenario 1: User can log in with valid credentials`
>   → extracted as `"User can log in with valid credentials"` (number stripped)
> - Unlabelled: `Scenario:` (no label text)
>   → extracted as `"Scenario {N}"` where N is the ordinal position in the spec
> The system prompt must instruct the LLM to normalise to these three patterns.
```

Add to `tests/test_acceptance_check.py`:
```markdown
- Test `AcceptanceVerdict` parse with numbered scenario labels (number stripped).
- Test `AcceptanceVerdict` parse with unlabelled scenario (ordinal fallback applied).
```

### Amendment 5 — HIB-042 pre-sprint verification note

Add as a note under the `check_traceability.py` pre-commit template section:

```markdown
> **Pre-sprint verification**: Confirm HIB-042 (Windows-only `cmd /c` hook pattern
> for all local hooks) exists in `docs/planning/harness_improvement_backlog.md`
> before closing the Sprint 1 PR. If absent, add it. The traceability hook
> deliberately matches the established template pattern — it does not worsen the
> existing situation; HIB-042 tracks the broader fix.
```

### Amendment 6 — Scenario 29 E2E LLM mock

Replace the current steps 9-11 of Scenario 29 with:

```markdown
9.  Add out-of-scope code, run `acceptance_check.py` with mocked provider returning
    fixture `AcceptanceVerdict(verdict="DIVERGED", scope_creep_findings=["..."],
    remediation_steps=["..."], ...)` → assert exit 1.
10. Add migration change without `[HIGH_RISK_SCHEMA_CHANGE]` in spec → assert hard
    DIVERGED (no LLM call required — static migration path check), exit 1.
11. Align code to Gherkin scenarios, run `acceptance_check.py` with mocked provider
    returning fixture `AcceptanceVerdict(verdict="SATISFIED", ...)` → assert exit 0.

> **Live LLM variant**: run `pytest tests/e2e/ --integration` to execute Scenario 29
> steps 9 and 11 against a real provider. Excluded from standard CI to avoid network
> dependency and token cost per run. Step 10 remains hermetic regardless — the
> migration path check is static and never calls the LLM.
```

---

## Part 4 — Summary counts for Gemini

| Target document | Action | Item count |
|---|---|---|
| `FRAMEWORK_BACKLOG.md` Sprint 0 | Add S0-19, S0-20, S0-21, S0-22, S0-23 | 5 items |
| `FRAMEWORK_BACKLOG.md` T1-B | Add T1-B-05a, T1-B-07a | 2 items |
| `FRAMEWORK_BACKLOG.md` T1-G | Add T1-G-09 | 1 item |
| `FRAMEWORK_BACKLOG.md` T1-L | Add T1-L-00, T1-L-01a, T1-L-08a | 3 items |
| `FRAMEWORK_BACKLOG.md` T1-M | Add T1-M-07 | 1 item |
| `FRAMEWORK_BACKLOG.md` T1-N | Add new series T1-N-01 through T1-N-06 | 6 items |
| `harness_improvement_backlog.md` | Add HIB-NEW-01, HIB-NEW-02, HIB-NEW-03 | 3 items |
| `FRAMEWORK_ROADMAP.md` Strategic Context | Add 4 named paragraphs | 4 blocks |
| `FRAMEWORK_ROADMAP.md` Execution Sequence | Add v1.3.0 pre-sprint gate note | 1 block |
| `v1.3.0 Sprint 1 Implementation Plan` | Apply 6 amendments | 6 changes |
| **Total** | | **32 changes** |

All items marked `Low` effort unless noted. All backlog items default to `⬜` status.
T1-L-00 is a **pre-sprint design gate** — it must be completed before T1-L-03
through T1-L-07 implementation begins.
