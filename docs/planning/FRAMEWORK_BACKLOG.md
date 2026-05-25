# AISDLC Harness — Comprehensive Improvement Backlog
**Created**: 2026-05-09
**Source**: Consolidation of all improvements discussed in session
**Additional Sources**: MarkTechPost (2026-05-12) — Build a Hybrid-Memory Autonomous Agent with Modular Architecture and Tool Dispatch Using OpenAI. Patterns: Tool ABC, LLMProvider ABC, Reciprocal Rank Fusion hybrid search. MarkTechPost (2026-05-15) — MCP-Style Routed AI Agent System with Dynamic Tool Exposure, Planning, Execution, and Context Injection. Patterns: RouteDecision dynamic capability routing, PlanOutput fast-path shortcut, ToolResult structured validation, policy notes explainability, restricted globals sandbox. Repowise/MarkTechPost (2026-05-15) — Repository-Level Code Intelligence with Graph Analysis, Dead-Code Detection, Decisions, and AI Context. Aider repo-map (tree-sitter + PageRank). Decision-Linked Development / Jimmy Utterström (2026-03-25) — @decision annotation pattern. codegraph (tarunms7/codegraph) — token-budget-aware PageRank context. All implemented via Python stdlib ast + networkx + git log — no external services required. MongoDB (2025-07-09) — Memory-Augmented AI Agents (memory as fundamental differentiator). Usama Amjid (2026-02-06) — Autonomous AI Agents Memory Systems Guide (five memory types, episodic outcome tagging). Iniyarajan S./Medium (2026-04-01) — Persistent AI Agent Memory Systems (token budget management, memory tiering). arXiv 2603.07670 (2026-03) — Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers (staleness/contradiction detection, retention policy, observability). DEV.to/BookMaster (2026-04-16) — Building a Memory System for Autonomous AI Agents (store + index + retrieval architecture). RFC-003 session findings + external framework review (May 2026) — outer loop governance gaps, gate calibration issues, bootstrap hook wiring bugs, agent operations self-sufficiency.
**Tiers**:
- **Tier 1** — Single developer, multiple projects. No server infrastructure. Works offline.
- **Tier 2** — Small team / multi-machine. Lightweight server required. Enables sharing.
- **Tier 3** — Enterprise / regulated. Full database infrastructure. Compliance-grade.

---

## Tier 1 — Solo Multi-Project
*Prerequisite: none. Implements on top of the existing Gym App harness.*

### Sprint 0: Pre-Promotion Quick Wins
*Complete before any public sharing of the framework.
These are manual tasks — no agent session required.
Estimated effort: 2-3 hours total.*

| ID | Item | Notes | Status |
|----|------|-------|--------|
| S0-01 | **Remove `scratch/` directory from repo** | Add to `.gitignore`. Single biggest "personal workspace" signal to visitors. | ✅ |
| S0-02 | **Narrow README positioning claim** | Change "covers the full delivery lifecycle: specification → development → testing → deployment" to accurately reflect what v1.0.x actually governs. | ✅ |
| S0-03 | **Add `CONTRIBUTING.md`** | How to install, how to contribute a skill, how to report an issue. Table stakes for open source. | ⬜ |
| S0-04 | **Add GitHub issue templates** | Bug report, skill contribution, feature request. Signals a maintained project. | ⬜ |
| S0-05 | **Cut v1.0.0 GitHub release + tag** | 15 commits, 0 releases signals personal workspace. Release notes from CHANGELOG.md. | ⬜ |
| S0-06 | **Add CI badge to README** | Basic social proof. | ⬜ |
| S0-07 | **Document convention vs enforcement in README** | Explicit section: "what is hard enforcement vs convention." The gate is the only hard mechanism. Be honest about this. | ✅ |
| S0-08 | **Surface 2-3 representative skills in docs** | Link or embed SKILL.md content. Visitors can't evaluate skill quality without cloning. | ⬜ |
| S0-09 | **Add worked example to docs** | `docs/worked-example.md`: complete diff → routing decision → verdict → policy notes cycle. Shows the gate working in practice. | ⬜ |
| S0-10 | **Publish dream phase example** | `docs/dream-phase-example.md`: real proposals from real sessions with evidence and metrics. The temporal moat made visible. | ⬜ |
| S0-11 | **Add "What it prevents" section to README** | Four concrete pain points mapped to framework capabilities: wrong repo commits → P-14 guard, ungoverned AI changes → adversarial gate, context loss between sessions → session lifecycle, stale architectural rules → dream phase. Source: HIB-005. | ✅ |
| S0-12 | **Fix validate.py legacy filename warning** | `validate.py` warns on absent `review_context_project.md` even when legacy `review_context.md` exists. Check for both filenames, suppress warning if either is present. Source: HIB-010. | ✅ |

---

### T1-A: Harness Extraction & Portability ✅ Complete (2026-05-21)

*All 7 items delivered. Full descriptions archived in [FRAMEWORK_BACKLOG_ARCHIVE.md §T1-A](FRAMEWORK_BACKLOG_ARCHIVE.md#t1-a-harness-extraction--portability--complete-2026-05-21).*

---

### T1-B: Environment Legibility

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-B-01 | **Universal context file** | Create `.agent/UNIVERSAL_CONTEXT.md` as the single canonical context source. `CLAUDE.md`, `GEMINI.md`, and `.cursorrules` become thin shims that load it. Eliminates three-copy drift risk across tool supplements. | Low |
| T1-B-02 | **Harness versioning** | Add `harness_version.txt` at framework root and `HARNESS_CHANGELOG.md`. `init_session.py` logs the harness version with each session. Enables forensic "which harness version was running when this incident happened." | Low |
| T1-B-03 | **Onboarding workflow** | `.agent/workflows/onboarding.md` — a first-session workflow that validates the environment, runs regression suite, confirms all skill validate scripts pass, and produces a "harness health at onboarding" baseline report. | Low |
| T1-B-04 | **Skill deprecation mechanism** | Add `status` field (active/deprecated/experimental) to each skill's metadata. `select_bdd_gate.py` and `skill_mapping.yaml` respect the field. Deprecated skills are not loaded. | Low |
| T1-B-05 | **Self-service skill authoring** | `/create-skill` workflow that scaffolds a new skill from a description: creates `SKILL.md`, `validate.py`, `cases.csv`, and adds `skill_mapping.yaml` entry. Turns a 4-file manual process into a one-command operation. **2026-05-24 addendum — Progressive loading**: Framework currently loads all skills at session start. Community consensus (Microsoft skills repo, May 2026) is three-level loading: name+desc (~100 tokens always), full SKILL.md on demand, scripts/references when referenced. "Loading all skills causes context rot: diluted attention, wasted tokens, conflated patterns." The /create-skill workflow (this item) should scaffold skills with this three-level structure as the default format. Adopt agentskills.io Level 1/2/3 disclosure convention. | Medium |
| T1-B-06 | **Skill length diagnostic audit** | Run a line-count audit of all `.agent/skills/*/SKILL.md` files and categorise by length: GREEN (<100 lines), AMBER (100-150 lines), RED (>150 lines). For each RED file, manually review to identify whether content is (a) task workflow instructions (belongs in skill), (b) long-term project rules (belongs in `review_context.md` or `UNIVERSAL_CONTEXT.md`), or (c) multiple distinct failure modes bundled together (candidate for decomposition into sub-skills). Produce a diagnostic report in `.agent/state/skill_audit.md` listing each file, its line count, category, and recommended action. This is a read-only diagnostic — no files are modified. Source: mattpocock/skills principle: "one skill, one clear problem; the shorter it is, the easier it is to call correctly and maintain." **2026-05-24 addendum — Skill CI gate**: Skills should be validated by CI on every push, not just periodic audit. Validate: frontmatter present, rule count ≤5, SKILL.md under 150 lines, validate script syntax if present. Failing skill = failing CI. Source: Shokunin v4.0 — CI validates all skills on every push. | Low |

| T1-B-07 | **Skill decomposition and remediation** | Execute the recommendations from T1-B-06 diagnostic. Three actions per RED file: (1) Move rules-content sections to `review_context.md` (project invariants) or `UNIVERSAL_CONTEXT.md` (harness-wide conventions); (2) Split multi-failure-mode skills into focused sub-skills of <150 lines each, updating `skill_mapping.yaml` and `skill_ownership.yaml` for each new skill; (3) Add an explicit **Output Format** section to every skill specifying the expected structure (e.g., Plan → Execute → Verify → Report). Additionally: add a cross-reference to `governance.md §2` escalation triggers in any skill that touches high-risk code (RBAC, auth, multi-tenant isolation, financial). Soft limit: skills should target <100 lines, hard limit: no skill file exceeds 200 lines. Enforce in T1-B-05 (`/create-skill` workflow template). Dependency: T1-B-06 complete. **Blueprint**: RFC-002 §H.9.5 (skill structure standard with output contract section) — `docs/archive/RFC-002-outer-loop-delivery.md` lines 1808–1837. | Medium |

---

### T1-C: Reliability & Recovery

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-C-01 | **Retrospective session outcome inference + post-commit heartbeat** | At the top of `init_session.py main()`, call `infer_and_close_previous_session()` before any other startup logic. If the previous session's `outcome` is null, infer it from current filesystem state: HALT file or halt_event in `harness_events.jsonl` → `escalated`; commits since session start AND no FAIL verdicts AND no open tasks → `success`; commits made AND (FAIL verdicts in `.ai-review-log.jsonl` OR open tasks in `active_context.md`) → `partial`; no commits and no HALT → `abandoned`. Write using three-field schema: `outcome` (success/partial/abandoned/escalated), `outcome_source` (inferred/agent_override/human_override), `outcome_note` (optional). Platform-agnostic — works for Claude Code, Gemini CLI, Codex, Cursor, Windsurf with no per-tool hook configuration. Handles first-ever session (no previous entry) gracefully. AGENTS.md §5 Session Close should note that agents may write `outcome_override` to `session.json` before closing; the next session's inference step uses the override if present. **Post-commit heartbeat (true agent-agnostic safety net)**: add a `post-commit` stage hook to `.pre-commit-config.yaml` calling `python .agent/scripts/init_session.py --post-commit`. This fires on every `git commit` from every agent and tool — no protocol compliance required. `--post-commit` mode: updates `last_activity` in `session.json`, writes a `commit_made` event to `harness_events.jsonl`; does NOT create a new UUID, does NOT trigger the dream phase. Ensures commit activity is always captured even if startup protocol was skipped; retrospective inference can then use `git log` as a reliable fallback signal. `.pre-commit-config.yaml` stanza: `{repo: local, hooks: [{id: session-heartbeat, name: Record commit to session, entry: python .agent/scripts/init_session.py --post-commit, language: python, stages: [post-commit], pass_filenames: false, always_run: true}]}`. **Claude Code optional enhancement**: Claude Code supports native Stop hooks via `.claude/settings.json`. Adding `{"hooks": {"Stop": [{"command": "python .agent/scripts/init_session.py --stop-hook"}]}}` writes outcome immediately on session end rather than waiting for retrospective inference; `outcome_source` becomes `"hook"` instead of `"inferred"`. This composes with the retrospective inference — the Stop hook fires on Claude Code, retrospective inference is the fallback for all other platforms. Not required but improves outcome accuracy on Claude Code. Dependency: T1-I-01 (session_ledger.jsonl) must be complete. **2026-05-24 addendum — Typed entry classification + session_end entry**: Add governance-relevant entry types to harness_events.jsonl (adapted from Shokunin, governance context not general session capture): `decision` (architectural/governance decision made this session), `checkpoint` (phase gate passed: plan approved, UAT passed, ORR complete), `claim_file` (file path verified to exist at this timestamp), `claim_function` (function signature verified at this timestamp), `session_end` (structured auto-generated close summary). The session_end entry is generated at close time via Stop hook (Claude Code) or retrospective inference fallback. Fields: commits_made, files_changed, gate_verdicts {PASS/WARN/FAIL counts}, decisions_logged, open_tasks_remaining, outcome. This supplements agent-written last_session_summary.md with a compliance-independent machine-generated record. NOT applicable: preference, command, general (personal assistant types, not governance types). Also add markdown fallback: write a human-readable .md mirror of each session's events alongside the .jsonl file. Ensures session history is readable without tooling and survives agent non-compliance with close protocol. | Medium |
| T1-C-02 | **Structured HITL approval queue** | When an agent hits an escalation trigger, it writes a structured approval request to `.agent/state/pending_approvals.json` and enters a waiting state. Human edits `approved: true/false`. Agent resumes on next session. Replaces the binary HALT/hope-the-agent-stopped pattern. **Blueprint**: RFC-002 §K.1 (complete JSON schema for approval requests) — `docs/archive/RFC-002-outer-loop-delivery.md` lines 2062–2095. | Medium |
| T1-C-03 | **Harness health alerting** | If `harness_health.py` detects a CRITICAL recommendation card, automatically create a GitHub issue tagged `[harness-critical]`. Closes the gap between "flywheel detected a problem" and "a human acted on it." | Low |

---

### T1-D: Observability & Intelligence

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-D-00 | **skill_ownership.yaml — dream phase routing map** | Create `.agent/config/skill_ownership.yaml` before implementing T1-D-03. Schema: each entry maps a skill name to a list of ownership rules: `{check_type: [...], event_type: [...], keyword: [...]}`. The dream phase uses this to route detected patterns to the correct skill file for proposal generation. Without it, `distill_dream.py` cannot route patterns and falls back to writing everything to `unrouted__YYYY-MM-DD.md`. Seed with ownership rules for the skills that currently have the most governance relevance: python-backend-guidelines, testing-patterns, security-audit, database-design, agent-framework. This file grows over time as unrouted patterns reveal ownership gaps. No code dependencies — pure configuration. | Low |
| T1-D-01 | **SQLite state index — single machine** | `~/.aisdlc/harness.db` SQLite file on the developer's machine. All projects write to it via a shared `harness_state.py` library. Flat files remain the source of truth; SQLite is the derived index. Four tables: sessions, governance_events, review_verdicts, decisions. **Blueprint**: RFC-002 §H.6 + §H.9.2 (additional `workflow_runs`, `workflow_phase_results`, `tool_uses` table schemas) — `docs/archive/RFC-002-outer-loop-delivery.md` lines 1428–1458, 1730–1743. | Medium |
| T1-D-02 | **Cross-project harness health** | Update `harness_health.py` to query SQLite with a `project=` filter for single-project reports, or omit the filter for a cross-project aggregate view. "Which project has the most BRANCH_ISOLATION violations this month?" | Low |
| T1-D-03 | **Dream phase distillation (distill_dream.py)** | Batch script in `.agent/scripts/distill_dream.py`, triggered at session start (not CI). Reads 30 days of `harness_events.jsonl` and `session_ledger.jsonl`. **Flagging logic**: `count ≥ 3 AND escalation_rate ≥ 0.40 AND appearance_rate ≥ 0.20` — OR — `count ≥ 1 AND severity == "critical"` in `harness_events.jsonl` (single critical-severity event always generates a proposal regardless of frequency; addresses the salience gap identified by Generative Agents: low-frequency, high-impact events must not be filtered by count threshold). Recency weighting: `weight = sum(1.0 / (days_ago + 1))` per occurrence so recent patterns outweigh old ones. Routes each pattern to the owning skill via `.agent/config/skill_ownership.yaml`; unroutable patterns written to `dream_proposals/unrouted__YYYY-MM-DD.md` (not silently discarded). De-duplicates against existing `__open` proposals: if `{skill}__{pattern_key}__open.md` exists, updates its `Last seen` date and appends new session IDs to Evidence rather than creating a duplicate. Proposal filename: `{skill}__{pattern_key}__open.md`. Proposal format: structured markdown with Status, Generated, Last seen, Evidence, Metrics, Confidence, proposed diff, and `Action: [ ] Accept [ ] Reject [ ] Modify` checkbox. CLI flags: `--dry-run` (print without writing), `--since YYYY-MM-DD`, `--min-sessions N` (default 15, exits 0 cleanly if below threshold), `--min-span-days N` (default 14, exits 0 if sessions span less than 2 weeks — prevents burst-sprint noise). Contradiction check (T1-I-05) runs before writing each proposal; writes `{skill}__{pattern_key}__contradiction.md` instead if conflict detected. **Scheduling — not CI**: CI runners cannot access gitignored local state files (`harness_events.jsonl`, `.ai-review-log.jsonl`). Wired into `init_session.py` via `maybe_run_dream_phase()`: fires at session start when ≥ 7 days have elapsed since last run and data thresholds are met. `maybe_run_dream_phase()` logic: (1) read `dream_phase_state.json`; if absent, treat `last_run_utc` as epoch zero; (2) if `(now - last_run_utc).days < 7`, return silently; (3) load `session_ledger.jsonl` and count sessions + span — if below `--min-sessions` or `--min-span-days` thresholds, print "Dream phase: N sessions found, minimum M required" and return with `sys.exit(0)`; (4) invoke `distill_dream.py` as subprocess, capture stdout; (5) print one-line summary to agent; (6) write updated `dream_phase_state.json`. Cooldown check runs before threshold check — avoids re-reading ledger on every session start. State tracked in `.agent/state/dream_phase_state.json` (gitignored, never committed). Schema: `{"last_run_utc": "2026-06-15T08:23:11Z", "last_session_count": 18, "last_span_days": 21, "proposals_generated": 3, "proposals_written": 2, "contradictions_found": 1, "unrouted_patterns": 0}`. `proposals_generated` vs `proposals_written` distinction: contradictions and unrouted patterns are generated but not written as `__open` files — reviewer sees "3 found, 2 became proposals" and knows to check `__contradiction.md` or `unrouted__.md` files. **Session-start output**: one-line summary only — `Dream phase ran: 3 proposals generated → .agent/state/dream_proposals/ (2 open proposals, 1 contradiction card — review before next release)`. Full proposal content is not injected at startup; it is read during monthly human review. **Verification gap**: skill verification is semantic only (contradiction check). Executable verification — running the proposed rule against session evidence — requires T1-E-01 (Tool ABC) to be complete. Known gap relative to Voyager's approach; proposals are approved by human judgement, not automated verification. Dependency: T1-C-01, T1-I-03, T1-D-00 (skill_ownership.yaml). | Medium |
| T1-D-04 | ~~**Model-agnostic review gate**~~ | **Absorbed by T1-E-02** (LLMProvider ABC). T1-E-02 delivers the same provider abstraction with a cleaner interface design. This item is retained for cross-reference only. | — |
| T1-D-05 | **Model tiering configuration** | Document and configure the two-tier role-based model architecture in `.agent/config.yaml`. Tier 1 (budget, low-cost): OllamaProvider or other low-cost endpoint for wiki compilation (T1-H-06), knowledge lint (T1-H-07), dream phase distillation (T1-D-03), RouteDecision classification (T1-G-01), and ADR description extraction (T1-H-02). Tier 2 (review, high-performance): AnthropicProvider or other heavy endpoint for the AI adversarial review gate. Config structure: `model_routing.budget_tasks`, `model_routing.budget_provider`, `model_routing.budget_model`, `model_routing.budget_provider_timeout_seconds`, `model_routing.budget_base_url`, `model_routing.review_provider`, and `model_routing.review_model`. Also configure the degrade-to-budget fallback if the review provider is down. This role-based naming ensures topology independence. Depends on T1-E-02. | Low |

---

### T1-E: Code Architecture & Interfaces

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-E-01 | **Formalise skills as Tool ABC subclasses** | Define a `Tool` abstract base class in `.agent/scripts/tool_base.py` with three contracts: `name: str`, `run(**kwargs) -> str`, and `schema() -> Dict` (returns OpenAI-compatible function-calling schema). Each skill that has programmatic execution (not just documentation) implements a `tool.py` subclass alongside its existing `SKILL.md`. Add a `SkillRegistry` that auto-discovers all `Tool` subclasses from `.agent/skills/*/tool.py` at startup. Benefits: skills become testable as Python objects (mock input, call `run()`, assert output), the AI review gate can dynamically compose its tool set from the registry, and `schema()` enables auto-generated documentation. The markdown `SKILL.md` remains the documentation layer; the `Tool` subclass becomes the executable layer. Source: MarkTechPost hybrid-memory agent article (Tool ABC pattern). | Medium |
| T1-E-02 | **Apply LLMProvider ABC to ai_review.py** | Refactor `src/scripts/ai_review.py` to use a formal `ReviewProvider` abstract base class: `class ReviewProvider(ABC): def review(self, system: str, diff: str) -> ReviewVerdict`. Implement three concrete providers: `AnthropicProvider` (current behaviour), `OpenAIProvider` (OpenAI-compatible API), `OllamaProvider` (local model, enables air-gapped operation). Provider selection is driven by `config.yaml` (`ai_review.provider: anthropic\|openai\|ollama`). The review gate never references a specific API after this change. Extends T1-D-04 (model-agnostic review gate) with a clean interface template. Source: MarkTechPost hybrid-memory agent article (LLMProvider ABC pattern). **Blueprint**: RFC-002 §H.3 (three-tier model registry with symbolic names, provider fallbacks, and use-case assignments) — `docs/archive/RFC-002-outer-loop-delivery.md` lines 1193–1241. | Medium |

---

### T1-F: Documentation & Shareability ✅ Complete (2026-05-21)

*All 5 items delivered. Full descriptions archived in [FRAMEWORK_BACKLOG_ARCHIVE.md §T1-F](FRAMEWORK_BACKLOG_ARCHIVE.md#t1-f-documentation--shareability--complete-2026-05-21).*

---

### T1-G: AI Review Gate Intelligence
*Patterns sourced from: MarkTechPost (2026-05-15) — MCP-Style Routed AI Agent System with Dynamic Tool Exposure, Planning, Execution, and Context Injection*

| ID | Item | Description | Effort | Status |
|----|------|-------------|--------|--------|
| T1-G-01 | **Diff-aware capability routing with RouteDecision** | Add a routing step to `src/scripts/ai_review.py` executing before the LLM call. The router produces a structured `RouteDecision` (Pydantic model: `selected_tools: List[str]`, `review_intensity: Literal["standard","elevated","critical"]`, `rationale: str`, `policy_notes: List[str]`). **Three routing layers**: (1) File-path routing: BRANCH_ISOLATION and TRANSACTIONAL_INTEGRITY activate when repository or service files change; ANTI_PATTERNS activates when schema or model files change; INTENT_ALIGNMENT, CODE_QUALITY, TEST_COVERAGE always activate. (2) PageRank intensity: changed files in top 10 PageRank → `elevated`; top 3 → `critical` (treat WARNs as FAILs). (3) ADR domain overrides: `# ADR: branch_isolation` annotation always activates BRANCH_ISOLATION regardless of file path; `# ADR: schema_hardening` always activates ANTI_PATTERNS. **Model tiering**: the routing classification step (not the full review) can run on the OllamaProvider with Gemma4 MoE locally for cost reduction — the Gemma4 call classifies the diff; the Sonnet call performs the actual review on the selected dimensions only. The `RouteDecision` is embedded in the `ReviewVerdict` (T1-G-03) and persisted to `.ai-review-log.jsonl`. Depends on T1-E-02 (LLMProvider ABC), T1-G-03 (ReviewVerdict), T1-H-01 (PageRank scores), T1-H-02 (ADR annotations). | Medium | ✅ |
| T1-G-02 | **Pre-flight shortcut (PlanOutput fast path)** | Add a pre-flight check at the start of `ai_review.py` before the routing step. If the diff meets a fast-pass threshold (documentation-only files: `.md`, `.rst`, `.txt`; or whitespace/comment-only changes), return PASS immediately with zero LLM calls and a `planner_note` explaining the shortcut. Structured as a `PlanOutput` equivalent: `requires_review: bool`, `direct_pass_allowed: bool`, `planner_note: str`. The fast path result is logged to `.ai-review-log.jsonl` with `verdict: "PASS_FAST"` to distinguish it from a full review pass. Benefits: eliminates token cost on trivial commits; reduces gate latency from ~5s to <100ms for documentation changes. Source: PlanOutput.direct_answer_allowed pattern. | Low | ✅ |
| T1-G-03 | **Formalise ReviewVerdict as Pydantic model** | Replace the current dict-based verdict output in `ai_review.py` with a typed `ReviewVerdict` Pydantic model: `verdict: Literal["PASS","WARN","FAIL","FAIL_OPEN","PASS_FAST"]`, `blocking_concern: Optional[str]`, `concerns: List[str]`, `route_decision: Optional[RouteDecision]`, `planner_note: Optional[str]`, `fail_open_reason: Optional[str]`, `model: str`, `token_usage: Dict[str, int]`. Validation at parse time means malformed LLM responses raise a typed `ValidationError` rather than an opaque JSON parse failure. The typed model is consumed by `harness_health.py` and `governance_check.py` as a structured object rather than a raw dict. Builds on the `ReviewProvider` ABC (T1-E-02) and the `ToolResult` structured validation pattern from the source article. | Medium | ✅ |
| T1-G-04 | **Policy notes in terminal review output** | Update the terminal output formatting in `ai_review.py` to include the `policy_notes` from the `RouteDecision` in the printed verdict. Example output: `✅ PASS — Active: INTENT_ALIGNMENT, CODE_QUALITY, TEST_COVERAGE / Skipped: BRANCH_ISOLATION (no repository files changed), ANTI_PATTERNS (no schema files changed)`. This closes the trust gap where developers cannot tell what the gate checked vs silently skipped. A gate's silence on a concern should be explicitly explained, not ambiguous. Zero token cost — purely output formatting. | Low | ✅ |
| T1-G-05 | **Restricted globals sandbox for eval_runner.py** | Apply a whitelist-based restricted globals pattern to `.agent/scripts/eval_runner.py` when executing code assertions in skill eval cases (`cases.csv`). Restrict `__builtins__` to an explicit allowlist (abs, len, print, range, sorted, str, int, float, bool, list, dict, set, tuple, zip, enumerate, sum, min, max, round, any, all) and permitted libraries (re, json, pathlib). Prevents a malicious or accidental eval case from executing arbitrary system commands during automated eval runs. Source: `tool_python_exec` whitelist pattern. Dependency: T1-E-01 (Tool ABC and SkillRegistry) should be complete before this is implemented. | Low | ⬜ |
| T1-G-06 | **Structured Rebuttal Protocol** | When the gate returns FAIL, the agent currently has no governed path to contest specific findings other than `SKIP_AI_REVIEW=1` — a wholesale bypass. Add a `--rebuttal` mode to `ai_review.py`. When invoked, the agent provides a structured rebuttal file at `.agent/state/gate_rebuttal.json` with one entry per contested finding: `finding_id`, `rebuttal_type` (FALSE_POSITIVE / SPEC_REQUIREMENT / ARCHITECTURAL_INVARIANT / OUT_OF_SCOPE), `evidence`, `spec_reference` (optional). The gate performs a second LLM call via the existing `ReviewProvider` ABC (T1-E-02) with the original diff, findings, and rebuttal. The reviewer produces a `RebuttedVerdict` per finding: REBUTTAL_ACCEPTED (finding withdrawn) or REBUTTAL_REJECTED (finding upheld). A commit is unblocked only if all FAIL-level findings are either accepted or uncontested. All rebuttal outcomes are written to `.ai-review-log.jsonl`. A REBUTTAL_ACCEPTED outcome automatically triggers `false_positive_to_eval.py` (T1-L-10) — no manual invocation required. `AGENTS.md` updated to document the rebuttal path as the correct response to a FAIL believed to be a false positive; `SKIP_AI_REVIEW=1` repositioned explicitly as last resort. Dependency: T1-E-02 ✅, T1-G-03 ✅. | Medium | ⬜ |
| T1-G-07 | **Structured SKIP_REASON Enforcement** | `SKIP_AI_REVIEW=1 SKIP_REASON="..."` currently accepts free-text that cannot be programmatically analysed or cross-referenced with specific findings. For high-risk commits (T1-L-08 ✅), enforce `SKIP_REASON` as a JSON object: `rebuttal_type`, `finding_ids`, `evidence`, `spec_reference` (optional). If absent or malformed on a high-risk bypass, the bypass is rejected with an error explaining the required format. For low-risk commits, free text remains acceptable — overhead not justified. On a valid structured bypass: reason is written to `harness_events.jsonl` as a typed `gate_bypass` event, and `finding_ids` are passed to `false_positive_to_eval.py` (T1-L-10) automatically. `harness_health.py` gains a check on structured bypass rate by `rebuttal_type` — a rising FALSE_POSITIVE bypass rate on the same capability signals a calibration problem that feeds dream phase pattern detection (T1-D-03). Dependency: T1-L-08 ✅, T1-L-10. | Low | ⬜ |
| T1-G-08 | **Diff size review strategy** | Add a diff size classifier to `ai_review.py` running before the routing step. Diffs exceeding a configurable line threshold (config.yaml: `review.large_diff_threshold`, default 400 lines) trigger stratified review: sections matching the high-risk file classifier (T1-L-08 ✅) are reviewed at full intensity with full context injection; the remainder is reviewed at reduced context injection (review_context summary only, no repo map, no ADR injection). The stratified verdict is logged to `.ai-review-log.jsonl` with `strategy: "stratified"` to distinguish it from standard reviews. Bounds per-commit token cost on large feature commits without eliminating coverage on high-risk sections. Config: `review.large_diff_threshold: 400`, `review.large_diff_strategy: stratified`. Dependency: T1-L-08 ✅, T1-G-03 ✅. | Low | ⬜ |

---

### T1-H: Repository Intelligence
*Lightweight implementation using Python ast + networkx + git log.
Single new dependency: `poetry add networkx`. No external services.*

| ID | Item | Description | Effort | Status |
|----|------|-------------|--------|--------|
| T1-H-01 | **PageRank repo map generator** | Create `.agent/skills/senior-architect/scripts/repo_map.py` extending the existing `dependency_analyzer.py` AST walker. Build a directed import graph using Python stdlib `ast`. For each file, extract both import edges (graph structure) AND symbol definitions (class names, function names, method names) as node labels — without definitions the map says "this file is important" but with them it says "this file is important and contains `BranchAwareRepository`, `_apply_branch_filter`." Run `networkx.pagerank()` with a two-level personalisation signal: (1) changed files weighted 10x; (2) CamelCase identifiers found in the diff text by regex scan — files defining or importing those identifiers get additional 10x weight boost (Aider diff-identifier technique). Generate a token-budgeted ranked structural map (compact text: file path + PageRank score + dependent file count + top 3 symbol definitions). Budget: ≤600 tokens. Cache the graph in `.agent/state/repo_graph.json` keyed by file mtimes — rebuild only when source files change. Integrate into `ai_review.py` as a third context source injected before the LLM call, after diff-aware section selection (PA-02) and pre-flight check (T1-G-02). Validate token budget against a representative Gym App diff before finalising allocation. Single new dependency: `networkx`. Governed by CONSTRAINT-01. | Medium | ✅ |
| T1-H-02 | **ADR annotation convention and wiki page injection** | Establish `# ADR: domain_name` comment convention (domain-keyed, not file-specific, e.g. `# ADR: branch_isolation` not `# ADR: adr_002_multi_tenant_branch_isolation.md`) for annotating source code with the governing architectural domain. The domain key maps to a compiled wiki page (T1-H-06). Detection function in `architecture_checks.py` scans changed files for `# ADR:` annotations using `re` (stdlib only). **ADR propagation via import graph**: if file A has `# ADR: branch_isolation` and the diff modifies file B which imports file A (per T1-H-01 graph), also inject the `branch_isolation` wiki page for B's diff. **Injection format**: inject the compiled wiki page summary for each detected domain (from `.agent/wiki/{domain}.md`) rather than raw ADR content — the wiki page is already synthesised and cross-referenced. Include `→ Full document: docs/decisions/adr/adr_XXX.md` so the agent can read the full ADR if it judges the change to be in that territory. **Cap**: inject at most 4 ADR domains per review; direct annotations take priority over propagated ones. Budget: ≤400 tokens total. Seed annotations as a one-time sprint task: add `# ADR: {domain}` comments to the 15-20 highest-risk files identified by the nine existing ADRs. Depends on T1-H-06 wiki pages existing. Zero new dependencies. Governed by CONSTRAINT-01. | Low | ✅ |
| T1-H-03 | **Co-change blast radius estimator (combined signals)** | Create `.agent/scripts/co_change_check.py` combining two signals: (1) `git log --name-only` (via subprocess, stdlib) to build an empirical co-change frequency map from the last 200 commits; (2) the import graph from T1-H-01 to identify structural co-change partners (files that import or are imported by the changed file). Merge both signals with confidence labels: `HIGH` when both git history AND import graph agree a file should co-change; `MEDIUM` when only one signal suggests it. Surface `HIGH` confidence warnings as pre-commit output and inject them into the AI review context; surface `MEDIUM` as advisory-only. Cache the git-derived co-change map in `.agent/state/co_change_map.json`, rebuilt weekly by `harness-drift.yml`. **Cache invalidation trigger**: if the most recent commit message contains `refactor`, `rename`, or `restructure`, invalidate the cache and rebuild immediately — stale co-change data during active refactoring produces misleading warnings. Budget: ≤200 tokens for co-change warnings injected into review. Governed by CONSTRAINT-01. Zero new dependencies. Depends on T1-H-01 for import graph. | Medium | ⬜ |
| T1-H-04 | **Auto-generated context files at install time** | Extend `bootstrap/install.py` with a post-copy analysis step that runs the repo map generator (T1-H-01) against the target project and auto-populates a starter `review_context_project.md`. Detects architectural layers from directory structure, identifies top 10 PageRank files, counts existing ADRs, and infers test framework from `pyproject.toml`. Writes a template file populated with structural facts that the installer reviews and extends rather than authors from scratch. Removes the blank-page problem for new project installations. Depends on T1-H-01. | Low | ⬜ |
| T1-H-05 | **Dead-code confidence scoring** | Extend the existing `vulture` step in `drift-detection.yml` to produce structured tiered output: SAFE (confidence ≥90%), REVIEW RECOMMENDED (70-89%), and write results to `.agent/state/dead_code_report.json`. Add a Dead Code section to `harness_health.py` reading this file and tracking count-by-tier as a weekly trend (IMPROVING / STABLE / DEGRADING). Extends the existing PD-01 dead code detection with structured confidence tiers and flywheel integration. No new dependencies — vulture already supports `--min-confidence`. | Low | ⬜ |
| T1-H-06 | **Compiled harness wiki layer** | Create `.agent/wiki/` directory with one markdown page per architectural domain (branch_isolation, schema_hardening, uow_pattern, rbac, migration_conventions, testing_patterns). Each page synthesises the governing ADR(s), the review_context.md section, the relevant skill file rules, the architecture_checks.py enforcement rule, and the last-validated date into a coherent 100-200 token summary. Create `wiki_compile.py` script: reads raw sources (ADRs, review_context.md sections, skill files), calls OllamaProvider with Gemma4 MoE locally to synthesise each domain page, writes to `.agent/wiki/{domain}.md`. Includes `→ Full document: path` reference for each source so agents can read the original. Compilation runs weekly via `init_session.py`'s `maybe_run_dream_phase()` trigger (same session-start logic, separate cooldown state in `wiki_compile_state.json`). Full recompile only when source files have changed since last run; incremental update otherwise. **Zero marginal cost** — runs on Gemma4 MoE locally via OllamaProvider. The wiki pages are what T1-H-02 injects at review time. Depends on T1-E-02 (OllamaProvider). Source: Karpathy LLM Wiki pattern (April 2026) — compile once at ingest time, serve cheaply at query time. | Medium | ✅ |
| T1-H-07 | **Knowledge base lint pass** | Weekly batch pass checking cross-reference coherence across the entire harness knowledge base. Runs on Gemma4 MoE locally via OllamaProvider. Checks: (1) **Staleness** — do identifiers referenced in review_context.md sections still exist in `src/`? (extends T1-I-04 from check_drift.py into wiki context); (2) **Factual drift** — does a wiki page say X while its source ADR says Y? (3) **Orphaned rules** — rules in review_context.md or skill files that no architecture_checks.py rule enforces; (4) **Coverage gaps** — architectural patterns in src/ with no corresponding wiki page or review_context.md rule; (5) **Cross-file contradictions** — rules in skill files that contradict rules in review_context.md (holistic version of T1-I-05 which currently only runs at dream phase proposal time). Outputs: `LINT_PASS` (clean) or structured findings file `.agent/state/wiki_lint_findings.md` listing each issue with severity and suggested fix. Wire into `harness-drift.yml` weekly schedule. `harness_health.py` reads findings file and surfaces DEGRADING if lint findings are increasing week-over-week. **Zero marginal cost** — Gemma4 MoE local. Source: Karpathy LLM Wiki lint operation; arXiv 2603.07670 §7.3 staleness and drift. Depends on T1-H-06. | Medium | ✅ |
| T1-H-08 | **Branch-Isolated Model Roster in Compiled Wiki** | Extension of the compiled wiki layer (T1-H-06 ✅). The BRANCH_ISOLATION capability check currently flags join queries where branch filtering targets the outer model without knowing whether that model physically carries `branch_id` — producing false positives on correctly-written queries. Extend `wiki_compile.py` to perform an AST scan of the project's model definitions during `branch_isolation` domain page compilation. For each class inheriting from the configured ORM base, detect whether `branch_id` is declared as a `mapped_column` with a foreign key to the branches table. Write the confirmed roster into the `branch_isolation` wiki page: Model, Column, Nullable, Table. The BRANCH_ISOLATION routing check in `ai_review.py` reads this roster from the compiled wiki page before flagging a join — if the filtered model appears in the roster, the flag is suppressed with a policy note (`"BRANCH_ISOLATION: Booking confirmed branch-isolated (branch_id verified — wiki compiled YYYY-MM-DD). Skipped."`). Absent from the roster means unverified, not absent — the flag fires as normal. Roster regenerated on every wiki compilation cycle (weekly via the existing `maybe_run_dream_phase()` cadence — no new scheduling required). Model additions or removals are reflected within one week without manual updates. Dependency: T1-H-06 ✅, T1-H-01 ✅. | Low | ⬜ |

---

### T1-I: Memory System Formalisation
*Sources: MongoDB (2025-07-09) — Memory-Augmented AI Agents. Usama Amjid (2026-02-06) —
Autonomous AI Agents Memory Systems Guide. Iniyarajan S. (2026-04-01) — Persistent AI Agent
Memory Systems. arXiv 2603.07670 (2026-03) — Memory for Autonomous LLM Agents: Mechanisms,
Evaluation, and Emerging Frontiers. DEV.to / BookMaster (2026-04-16) — Building a Memory
System for Autonomous AI Agents.*

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-I-00a | **Consolidate governance_audit.jsonl + audit_trail.jsonl → harness_events.jsonl** | `governance_audit.jsonl` (2 entries, governance observations) and `audit_trail.jsonl` (1 entry, action trace test) are near-duplicates in intent — both record "something notable happened," both are JSONL, both are nearly empty. Merge into a single `.agent/state/harness_events.jsonl` with a unified schema: `schema_version`, `event_type` (governance_observation \| action_trace \| schema_verification \| halt_event), `timestamp_utc`, `session_id`, `commit_sha` (nullable), `agent`, `severity`, `payload`. Update `governance_check.py` to write to the new file. Update `audit_logger.py` to conform to the same schema. Delete the two source files after migration. Both have trivial entry counts — zero migration cost. One PR. | Low |
| T1-I-00b | **Audit audit_logger.py wiring** | Verify whether `audit_logger.py` is actually called anywhere during normal pre-commit or session lifecycle operations (`grep -rn "audit_logger" .agent/ src/`). If it has no callers beyond the init test, document it as vestigial in `decisions_log.md` and treat T1-I-00a as a simple rename rather than a merge. If it is wired, confirm it writes the correct `harness_events.jsonl` schema after T1-I-00a. This must be resolved before T1-I-01 (passive hooks enforcement) — you cannot enforce session lifecycle hooks if the action logger write path is unimplemented. | Low |
| T1-I-01 | **Memory tiering (hot/warm/cold)** | Formalise the scaffold's memory layers into three explicit tiers with defined retrieval policies. Hot tier (always loaded at session start): `active_context.md`, last 3 entries of `session_ledger.md`. Warm tier (loaded on relevance signal): `session_ledger.md` last 30 days, `.ai-review-log.jsonl` last 30 days, `governance_audit.jsonl` last 30 days. Cold tier (archive, loaded only on explicit search): older session history, archived backlog entries. Document tier definitions in `.agent/UNIVERSAL_CONTEXT.md` so all agents know which tier to load for which purpose. Aligns with the three-tier database architecture (SQLite → MCP → PostgreSQL) already designed. Source: all five memory articles; tiering pattern from Medium ConversationBuffer with max_age_hours. | Low |
| T1-I-02 | **Token budget tracking per session** | Add token consumption tracking to the session lifecycle. The `ReviewVerdict` Pydantic model (T1-G-03) already captures `token_usage` per review call. Extend `init_session.py` to initialise a session token budget counter, and the session close hook (T1-C-01) to write the total token expenditure per category to `session_ledger.md`: context load tokens, repo map tokens (T1-H-01), ADR injection tokens (T1-H-02), LLM call tokens. `harness_health.py` aggregates this as "average tokens per commit by category" trend (IMPROVING/STABLE/DEGRADING). Surfaces cost optimisation opportunities — if ADR injection is consuming 40% of the token budget, that signals the ADR injection strategy needs refinement. Source: Medium ConversationBuffer max_tokens pattern; arXiv §7.4 latency and cost. | Low |
| T1-I-03 | **Outcome-aware session startup orientation** | After `infer_and_close_previous_session()` runs, read the now-closed previous session's outcome and orient the starting agent: `escalated` → surface the halt context and the escalation reason from `harness_events.jsonl` before proceeding; `abandoned` → load `active_context.md` open tasks immediately and print "Previous session abandoned — N open tasks remain"; `partial` → print count of deferred tasks from last session's `active_context.md` snapshot; `success` → no special action (normal startup). Outcome-source weighting for dream phase: for `escalated` outcomes, prefer `inferred` (HALT file is objective; agents underreport). For `abandoned`, prefer `agent_override` (agent knows why it stopped; inference cannot distinguish knowledge gap from context window limit). For `partial`/`success` boundary, use `inferred` unless agent explicitly overrode. Dependency: T1-C-01. | Low |
| T1-I-04 | **Automated memory staleness detection** | Extend `check_drift.py` (PD-01, already in `harness-drift.yml`) to parse `review_context.md` sections and verify each referenced pattern still exists in `src/`. Uses the existing AST infrastructure from `dependency_analyzer.py` and `repo_map.py` (T1-H-01). For each invariant rule in `review_context.md` that references a specific Python pattern (e.g., `_apply_branch_filter`, `HardenedBaseModel`, `BranchAwareRepository`), check whether that identifier still appears in `src/`. If not, flag as `STALE_MEMORY` with the specific rule and the last commit where the pattern existed (from `git log`). Stale memories produce false-positive review verdicts that erode gate trust. Source: arXiv §7.3 staleness, contradictions, and drift. Zero new dependencies. **2026-05-24 implementation note — Claim verification (quick win)**: Add a verification function to init_session.py that runs before orientation begins. Cross-reference key claims in active_context.md against git reality: (1) claimed branch vs `git branch` output; (2) claimed last commit hash vs `git log -1`; (3) claimed open files vs `git status`. Print WARN for any mismatch. Costs one subprocess call per claim. No new dependencies. Treats session memory as claims from a frozen point in time, not facts — the same mental model as Shokunin's verify_file_path MCP tool. For Tier 2 (T2-A-01), expose this as an MCP tool. | Medium |
| T1-I-05 | **Memory contradiction detector (integrated into T1-D-03)** | Not a standalone script — integrated as a pre-write check inside `distill_dream.py`. Before writing any proposal, scans the target skill file for `always/never/must/must not` on the same subject (extracted by simple noun-phrase regex). If a contradiction is detected, writes `{skill}__{pattern_key}__contradiction.md` (a CONTRADICTION CARD showing the existing rule, the proposed rule, and the conflict) instead of the normal proposal. The batch script moves on to the next proposal; contradiction cards accumulate separately for human resolution. Contradiction cards are never auto-archived — they require explicit human action (`__reviewed` rename) before `retention_cleanup.py` will touch them. | Low |
| T1-I-06 | **Memory retention policy** | Add explicit retention configuration to `.agent/config.yaml`: `session_ledger_retention_days: 90`, `governance_audit_retention_days: 365`, `review_log_retention_days: 90`. Add a weekly cleanup step in `harness-drift.yml` that archives records older than the configured retention period from the warm tier (flat files) to `~/.aisdlc/archive/` (cold tier). Archived records remain searchable via the MCP server (T2-A-01) but are excluded from session startup loading. Directly relevant for privacy and compliance contexts — Australian ISM, GDPR, and SOCI Act all have data handling requirements that apply to AI system audit trails. Source: arXiv §7.5 privacy, compliance, and deletion. **Also handles dream_proposals/ retention**: moves `__reviewed.md` files older than `dream_proposals_reviewed_retention_days` (config default: 365) from `dream_proposals/` to `dream_proposals/archive/`. `__open.md` and `__contradiction.md` files are never auto-archived — they require human action first. Implement exponential recency weighting in distill_dream.py rather than treating all sessions equally. Add `dream_proposals_reviewed_retention_days: 365` to `.agent/config.yaml` as part of implementation. Session data older than 30 days should have reduced weight in dream phase pattern detection. Implement exponential recency weighting in distill_dream.py: weight = 1.0 / (days_ago + 1). A session from 180 days ago that triggered FAIL is less relevant than three FAIL verdicts from last week. Source: Shokunin v4.2.3 freshness decay (30-day half-life). **2026-05-24 addendum — Consolidation before archive + freshness decay**: (1) Before archiving sessions older than 90 days, run a Gemma4-local consolidation pass generating a structured consolidated_{YYYY-MM}.md summary per month: key decisions, recurring gate violations, architectural patterns. Dream phase reads consolidated summaries for sessions >30 days old, raw events for recent sessions. Enables long-horizon pattern detection without loading thousands of raw events. Zero new dependencies — uses existing OllamaProvider. Source: Shokunin consolidate_memories pattern. (2) Implement exponential recency weighting in distill_dream.py: weight = 1.0 / (days_ago + 1). A session from 180 days ago that triggered FAIL is less relevant than three FAIL verdicts from last week. Prevent stale sessions from dominating pattern detection. Source: Shokunin v4.2.2 freshness decay (30-day half-life). | Low |
| T1-I-07 | **Session token budget with WARN/HALT** | Add `session_token_budget` ceiling to `.agent/config.yaml`. `init_session.py` initialises a rolling token counter at session start (depends on T1-I-02 for per-call tracking). At 80% of the ceiling, the agent receives a compaction prompt referencing the context compaction template (T1-M-06). At 100%, the agent must close the session cleanly via the standard handoff protocol before continuing — no new LLM calls permitted until the next session is initialised. Transforms token cost from a surprise overage into a governed boundary. Default ceiling: configurable, no hardcoded value. Dependency: T1-I-02. | Low |

### T1-J: Agent Capability Enhancements
*Source: Hermes Agent (Nous Research, v0.14.0, MIT) — capabilities identified as
gaps in the AISDLC harness during comparative analysis, 2026-05-18.*

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-J-01 | **Automatic checkpoint before file changes** | Extend `governance.md §7` (Defensive Git Checkpoint Protocol) from a voluntary 3-file threshold to an automatic per-session checkpoint. At session start, `init_session.py` creates `git stash push -m "AUTO: session-start checkpoint [session_id]"` before any other action. A `/rollback` command in `AGENTS.md` pops the stash. Eliminates the compliance gap in the current protocol — agents that skip the manual stash step currently have no safety net. Hermes source: automatic working-directory snapshot before file changes via `/rollback`. | Low |
| T1-J-02 | **`@`-reference injection convention** | Document in `AGENTS.md` and `UNIVERSAL_CONTEXT.md` that agents should recognise `@path/to/file`, `@git:RANGE`, and `@url:URL` as inline context injection markers. Not a code change — a convention that Claude Code, Gemini CLI, and Cursor already support natively. Enables dynamic mid-session context loading without pre-loading everything at session start. Add to `UNIVERSAL_CONTEXT.md`: "Use `@` references to inject specific context at the point it is needed rather than loading all context at session start." Hermes source: `@`-reference injection that expands files, folders, git diffs, and URLs inline. | Low |
| T1-J-03 | **Credential pool rotation for AI review gate** | Add `ai_review.api_keys: [key1, key2, key3]` list to `.agent/config.yaml`. Update `ai_review.py` (or the `AnthropicProvider` class from T1-E-02) to rotate to the next key on 429 or 529 (rate limit / overload) responses before falling through to fail-open. Under burst commit periods (10-20 commits per hour during sprint finales), a single API key will eventually rate-limit. Pool rotation eliminates rate-limit-induced fail-open events without requiring SKIP_AI_REVIEW=1. Hermes source: credential pools with automatic rotation on rate limits. | Low |
| T1-J-04 | **agentskills.io open standard compatibility** | Align the harness skill format (`SKILL.md` + `validate.py` + `cases.csv`) with the agentskills.io open standard specification (https://agentskills.io/specification). Review the spec during implementation and document the required field additions or structural changes needed. Compatibility enables bidirectional skill exchange: import community-contributed skills directly into the harness; export GymBase-specific skills (branch isolation, HardenedBaseModel) back to the community skills hub. Extends T1-B-04 (skill deprecation mechanism). Also referenced in Hermes Agent docs and mattpocock/skills ecosystem. | Low |

### T1-K: Security Supply Chain Hardening
*Source: Supply chain malware attack vector discussion, 2026-05-18. Distinct from
pip-audit/bandit (CVE/SAST focus) — targets intentionally malicious packages.*

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-K-01 | **Malicious package detection gate (guarddog)** | Add `guarddog` (DataDog, open source) to the pre-commit security chain, positioned after `pip-audit` and before the architecture checks. Scope: fires only on commits that add or modify entries in `pyproject.toml` or `requirements*.txt` — not on every commit. `guarddog` uses static analysis heuristics to detect intentionally malicious packages: obfuscated code, network calls in `setup.py`, command execution at install time, suspicious metadata. This is distinct from `pip-audit` which detects CVEs — a package can be clean of CVEs and still be malware (typosquatting, dependency confusion attacks, post-compromise backdoor insertion). Also evaluate `osv-scanner` (Google) as a complementary tool covering malware advisories in the OSV database alongside CVEs. Relevant to Australian SOCI Act and ISM supply chain integrity requirements (T3-B-04). Install: `poetry add --dev guarddog`. | Low |

---

### T1-L: Outer Loop (Requirements Governance)
*Source: External framework review (May 2026) + RFC-003 session findings.
The framework governs delivery execution (development → gate → commit) well
but has no opinion on requirements origination, specification quality, or
acceptance traceability. The outer loop gap means a perfectly governed commit
can implement the wrong thing. This series closes that gap.*

*RFC-003 session evidence: The RFC document did not exist when implementation
was requested. The spec had to be drafted mid-session, clarification round
required, and the implementation plan needed a multi-persona review to catch
architectural gaps. All of this is outer loop governance that the framework
does not currently provide.*

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-L-01 | **Spec quality gate** | Before any `/feature-implementation` run begins, a SPEC-XXX.md must exist at `docs/planning/specs/` and pass a quality check. The gate verifies: acceptance criteria section present and non-empty, out-of-scope section stated, architectural constraints identified, status marked APPROVED by human. If absent or failing quality checks, the gate refuses to proceed and prints the specific missing sections. Implementation: `check_spec.py` in `.agent/scripts/`, wired into `feature-implementation.md` as the Phase 0 gate. `--skip-spec-gate` available for hotfixes with mandatory `SKIP_REASON` written to `harness_events.jsonl`. Closes the gap surfaced during RFC-003 delivery where the RFC document didn't exist and had to be drafted mid-session. Dependency: T1-L-02 (spec template must exist). | Medium |
| T1-L-02 | **`/business-analyst` workflow** | The `/ba` persona is referenced in `config.yaml` but has no workflow documentation. Create `.agent/workflows/business-analyst.md` as a full state-machine workflow covering: (1) requirement intake — how a business need is captured (GitHub issue, conversation, document); (2) user story extraction in INVEST format; (3) BDD scenario generation in Gherkin; (4) spec drafting — populates `docs/planning/specs/SPEC-XXX.md` from `.agent/templates/feature_spec.md`; (5) acceptance criteria definition — testable, specific, measurable; (6) requirements traceability matrix entry; (7) human approval gate — spec status set to APPROVED before workflow exits. Must clearly delineate agent responsibilities vs human input. Agent drafts; human approves. The workflow must encode institutional knowledge of what makes a spec AI-ready: bounded scope, unambiguous acceptance criteria, explicit out-of-scope statements, and architectural constraints that prevent mid-session surprises. Dependency: `feature_spec.md` template must exist. | Medium |
| T1-L-03 | **`/project-manager` workflow** | The `/pm` persona is referenced in `config.yaml` but has no workflow documentation. Create `.agent/workflows/project-manager.md` covering: (1) backlog grooming — how an approved SPEC becomes a prioritised backlog item with effort estimate and dependencies; (2) sprint planning — how items are selected for the current sprint with dependency resolution; (3) progress tracking — how the agent updates issue status and project board. Lightweight by design — not full project management tooling, but the minimal workflow needed to translate approved specifications into an ordered implementation queue. Dependency: T1-L-02 (SPEC is the input artefact). | Low |
| T1-L-04 | **Requirement → commit traceability** | Pre-commit check: non-trivial commits must reference a requirement ID in the commit message. The format matches the project's configured prefix (`SPEC-001`, `FR-003`, GitHub issue `#42`). New hook `check_traceability.py` in `.pre-commit-config.yaml.template`. Commits failing the check are blocked with a message explaining the required format. `--no-trace` flag available for infrastructure commits (chores, dependency updates) with reason recorded in `harness_events.jsonl`. The check reads valid requirement IDs from `docs/planning/specs/` and `docs/decisions/requirements_log.md`. Closes the spec-to-code chain: SPEC → acceptance criteria → implementation → commit → test. Without this, a commit that perfectly implements the wrong interpretation of an ambiguous requirement passes every gate. | Low |
| T1-L-05 | **Acceptance gate** | After implementation and before the PR is raised, a second AI review call checks intent alignment against the spec — not just code correctness. Loads the SPEC-XXX.md associated with the current feature branch and asks: "Does this implementation satisfy the acceptance criteria? Are any criteria untested? Are there tests validating behaviour not in the spec (scope creep)?" Produces a structured `AcceptanceVerdict`: `SATISFIED`, `PARTIAL` (some criteria met), or `DIVERGED` (implementation doesn't match spec intent). `PARTIAL` and `DIVERGED` block the PR. Implemented as `acceptance_check.py` in `.agent/scripts/` — separate from `ai_review.py`, runs once per feature branch not on every commit. Dependency: T1-L-01 (spec must exist with acceptance criteria), T1-E-02 (LLMProvider ABC for portability). **Blueprint**: RFC-002 §H.7 (ContractEvaluator class — simplified version of required_fields + gate_checks + numeric_gates + allowed_verdicts pattern) — `docs/design/workflow-engine-design.md` §4. | Medium |
| T1-L-06 | **Production scope statement** | The current README claims "covers the full delivery lifecycle: specification → development → testing → deployment" — this is inaccurate for v1.0.x. Narrow the claim to match what's actually built. Add an explicit "What this framework does not govern" section to `README.md` and `docs/getting-started.md`: production monitoring, alerting, incident response, infrastructure provisioning, model selection are all out of scope. Being honest about the boundary builds more trust than an inflated claim that a technical reader will see through. Documentation change only, no code. Highest credibility-per-effort ratio of any item in T1-L. | Low |
| T1-L-07 | **Incident → backlog pipeline** | When a production incident occurs, a structured entry enters the backlog with: root cause analysis, affected commit SHA (cross-referenced with `.ai-review-log.jsonl`), which gate should have caught it and why it didn't, and a proposed guard (skill rule addition, review invariant update, or new prohibition). `incident_to_backlog.py` in `.agent/scripts/` accepts `--commit SHA`, `--description "what went wrong"`, `--severity HIGH|MEDIUM|LOW`. The script reads the audit trail for the affected commit, cross-references the review log, and drafts a structured backlog entry for human review. Closes the production feedback loop: the framework learns from production failures, not just session patterns. Related to T1-D-03 (dream phase) but triggered on-demand rather than periodically. | Low |
| T1-L-08 | **High-risk commit classification** | The gate currently fails open uniformly when the API is unavailable. This is appropriate for documentation changes but not for schema migrations, auth code, or multi-tenant isolation logic. Add a risk classifier to `ai_review.py` running before the API call. High-risk indicators: files matching `*/migrations/*`, `*/auth/*`, `*/rbac/*`, `*/permissions/*`, `unit_of_work.py`, `base_repository.py`, any file annotated `# ADRs: branch_isolation`. If API unavailable AND commit touches high-risk files: fail closed (not open) with message explaining the risk classification; override requires `SKIP_AI_REVIEW=1 SKIP_REASON="..."`, with the reason written to `harness_events.jsonl` and flagged in the next harness health report. Low-risk fail-open (docs, config, CSS) is unchanged. Closes the gap: "The gate's value proposition collapses precisely at the highest-risk moments." | Medium |
| T1-L-09 | **Framework self-test suite** | The framework has no tests for its own governance mechanisms. A governance framework that can't verify its own rules is a governance risk. Create `tests/` at the framework root with: `test_ai_review.py` — golden-path tests (known-good diff → expect PASS), adversarial tests (known violation → expect FAIL on specific concern), false-positive regression tests (real PASS verdicts that should never become FAILs); `test_architecture_checks.py` — layer boundary detection, forbidden imports, config-driven loading, zero-config skip; `test_install.py` — stack detection, template rendering, non-destructive re-run, skill merging; `test_validate.py` — all checks, warning vs error classification. Migrate `test_wiki_compile.py`, `test_repo_map_and_annotations.py`, and `test_phase4_routing_and_cochange.py` from `.agent/tests/` into this suite. Target: >80% coverage of framework scripts. | Medium |
| T1-L-10 | **False Positive → Eval Regression Pipeline** | `incident_to_eval.py` converts production defects into permanent regression guards in the golden eval dataset. The inverse pipeline — confirmed false positives becoming "must not flag" guards — does not exist. Without it, false positives manually bypassed or confirmed via rebuttal leave no trace in the test suite and can resurface on future commits. Create `false_positive_to_eval.py` in `.agent/scripts/`. Accepts: `--finding-id "BRANCH_ISOLATION:session_repository.py:L42"`, `--rebuttal-type FALSE_POSITIVE | SPEC_REQUIREMENT | ARCHITECTURAL_INVARIANT`, `--evidence "brief factual statement with file:line citation"`, `--commit-sha SHA` (optional, defaults to HEAD). Reads the diff for the specified commit, generates a test case entry in `tests/data/false_positive_cases.csv`: diff snippet, expected verdict (PASS/WARN), capability that must not flag, evidence, date confirmed. This file is consumed by `test_ai_review.py`'s false-positive regression suite (T1-L-09 ✅ — the destination already exists). Invocation paths: automatic via rebuttal protocol (T1-G-06) on REBUTTAL_ACCEPTED; automatic via structured SKIP_REASON enforcement (T1-G-07) on a valid high-risk bypass; manual via AGENTS.md instruction when using an unstructured `SKIP_AI_REVIEW=1` bypass. Dependency: T1-L-09 ✅. | Low |

---

### RFC-003 Session: Gate and Bootstrap Bug Fixes
*Source: First real-world stress test of standalone AI Delivery Control
installation against GymBase RFC-003 delivery (2026-05-22).
These bugs were discovered during live feature delivery under the framework.*

| ID | Item | Description | Effort | Priority | Status |
|----|------|-------------|--------|----------|--------|
| BUG-01 | **commit-msg hook not installed by bootstrap** | `bootstrap/install.py` runs `pre-commit install` but does not run `pre-commit install --hook-type commit-msg`. The AI adversarial review gate is configured at `stages: [commit-msg]` but this hook stage is never wired automatically. The entire RFC-003 session ran without gate coverage because this step was missing. Fix: add `subprocess.run(["pre-commit", "install", "--hook-type", "commit-msg"], ...)` to Phase 5 (Git Hook Wiring) in `install.py`. Also add to `bootstrap/validate.py`: check `.git/hooks/commit-msg` exists alongside `pre-commit` and `pre-push` checks. | Low | CRITICAL | ✅ Already present since initial commit (19683c2). GymBase gap was environment-specific. |
| BUG-02 | **validate.py does not check commit-msg hook** | `bootstrap/validate.py` checks for `pre-commit` and `pre-push` hooks in `.git/hooks/` but not `commit-msg`. Reported ✅ "Pre-commit wired" while the gate hook was completely absent. Fix: add `commit-msg` to the hook layout check. | Low | HIGH | ✅ Already present since initial commit. |
| BUG-03 | **Gate reads staged diff at commit-msg stage — empty on amend** | The gate script reads `git diff --staged` to get the diff for review. At `commit-msg` stage during `git commit --amend`, the staged area is empty (nothing newly staged), producing an empty diff. The pre-flight shortcut classifies empty diffs as trivial and returns PASS_FAST in ~1.5s without any API call. The RFC-003 amend commit got a PASS_FAST verdict on an empty diff — the actual 1686-line RFC-003 diff was never reviewed. Fix: at `commit-msg` stage, detect amend context and read `git diff HEAD~1 HEAD` (the commit being created) rather than `git diff --staged`. | Medium | HIGH | ✅ Fixed in v1.1.0 (SE-01/SE-02 guards: ORIG_HEAD detection, empty tree fallback for single-commit repos). |
| BUG-04 | **PASS and PASS_FAST verdicts not written to log** | All 4 entries in GymBase `.ai-review-log.jsonl` are FAIL verdicts. PASS and PASS_FAST verdicts are either not being written or writing to a different path. A gate that only logs failures produces an incomplete and misleading audit trail — the framework appears to block everything when it actually passes most commits silently. Fix: ensure all verdict types (PASS, PASS_FAST, WARN, FAIL, FAIL_OPEN) write to `.ai-review-log.jsonl`. Verify the log write path is relative to the project root, not the script directory. | Low | HIGH |
| BUG-05 | **ADR domain names not mapping to capability names** | Context snapshot shows `adr_domains=['branch_isolation']` (detected) but policy notes show "Skipped check: BRANCH_ISOLATION (no matching path or ADR)". The domain name `branch_isolation` (from `# ADRs:` annotation) is not being mapped to the capability name `BRANCH_ISOLATION` in the routing logic. Case or naming convention mismatch in `RouteDecision.build_route_decision()`. Fix: normalise comparison — either uppercase both sides or maintain a canonical mapping dict from domain names to capability names. | Low | HIGH |
| BUG-06 | **Gate calibration too aggressive — all verdicts are FAIL** | All 4 logged GymBase gate verdicts are FAIL. All 3 logged ai-delivery-control gate verdicts are FAIL. A gate that returns FAIL on every commit loses developer trust and gets bypassed (which is what happened in the RFC-003 session). FAIL should require at least one HIGH severity finding. MEDIUM findings → WARN. LOW findings → informational only. Review the system prompt — the "assume wrong until proven otherwise" framing may be generating too many HIGH findings on legitimate code. | Medium | HIGH | ✅ Fixed in v1.1.0 (proportionate calibration, false-positive guard, citation requirement for FAIL). |
| BUG-07 | **Session heartbeat "files modified" failure on amend** | The `session-heartbeat` post-commit hook modifies `session.json` during the post-commit phase. Pre-commit detects the file modification, flags it as a hook auto-fix, and rolls back the change ("Stashed changes conflicted with hook auto-fixes... Rolling back fixes..."). The heartbeat update is lost. Fix: configure the heartbeat hook with `pass_filenames: false` and ensure it writes to a gitignored state file that pre-commit doesn't track. | Low | MEDIUM |
| BUG-08 | **`governance_check.py` uses deprecated `datetime.utcnow()`** | Warning surfaced during RFC-003 amend: `DeprecationWarning: datetime.datetime.utcnow() is deprecated`. Replace with `datetime.datetime.now(datetime.UTC)` throughout governance_check.py. | Low | LOW | ✅ Fixed in Sprint 0. |

---

### T1-M: Agent Operations and Self-Sufficiency
*Source: Second external framework review (May 2026).
The framework assumes developers already know how to work effectively
with AI agents. These items address the self-sufficiency gap.*

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-M-01 | **Agent operations guide** | Create `docs/agent-operations-guide.md` covering: (1) how to structure sessions to avoid context window collapse — scope one session to one logical unit, use spec gate to bound scope, recognise warning signs (agent re-reading same files repeatedly, contradicting earlier decisions); (2) what AI agents handle well vs where they consistently fail — good at elaboration, pattern application, and boilerplate; poor at novel architectural decisions, cross-cutting concerns, and scope discipline; (3) how to recognise when an agent has lost coherence mid-session — symptoms and recovery patterns; (4) delegation judgment — what to hand to the agent vs what to retain as human responsibility. Source material: RFC-003 session observations, GymBase development history. **Blueprint**: RFC-002 §H.9.1 (context compaction template for long-running phases — structured summary format preserving phase context, completed actions, failed attempts, remaining criteria) — `docs/archive/RFC-002-outer-loop-delivery.md` lines 1674–1706. | Low |
| T1-M-02 | **Spec writing guide** | Create `docs/spec-writing-guide.md` — the institutional knowledge of what makes a requirement AI-deliverable. Source directly from RFC-003 experience: (1) what sections a spec must have before an agent can act on it without surprises; (2) failure modes from under-specified requirements — context window collapse from unbounded scope, technically-correct-but-semantically-wrong implementation from ambiguous acceptance criteria, scope creep from missing out-of-scope statements; (3) the five clarification points that emerged from RFC-003 and what they reveal about spec quality; (4) how to scope a feature to a single agent session vs multi-session delivery. This document is both standalone guidance and the knowledge base for T1-L-02 (/ba workflow). | Low |
| T1-M-03 | **Mid-session observability** | Lightweight session health check: `python .agent/scripts/session_health.py` reports current session duration, tool call count (from harness_events.jsonl), context load estimate, and warning patterns (same file read 3+ times suggests agent confusion, same error appearing twice suggests remediation loop). Wire into AGENTS.md as a recommended voluntary mid-session check after each major phase. Not a monitoring system — a diagnostic tool the developer runs when something feels off. **Blueprint**: RFC-002 §H.9.2 (`tool_uses` SQLite table — per-call audit trail with tool name, input/result summary, duration, hook verdict) — `docs/archive/RFC-002-outer-loop-delivery.md` lines 1730–1743. | Medium |
| T1-M-04 | **Minimal team usage guide** | Create `docs/team-usage-guide.md` — answers the CTO question "what does this look like for three people?" without requiring Tier 2 infrastructure: who owns dream proposals on a shared repository (recommendation: skill domain owner, not whoever triggered the proposal); how gate verdicts are visible across developers (aggregate `.ai-review-log.jsonl` manually or via `harness_health.py`); branch ownership conventions when multiple developers use the harness on the same repo; how to introduce the framework to a team incrementally (one developer first, then expand). Honest about limitations: shared state requires Tier 2 (v2.0.0). | Low |
| T1-M-05 | **Stack coverage acknowledgment** | Add a "Stack Coverage" section to `README.md` and `docs/getting-started.md`: "Built for and validated against Python/FastAPI. The 22 universal skills are language-agnostic. The architecture checks, migration patterns, and stack pack are Python-shaped. Non-Python developers should evaluate adaptation effort before committing. Node.js stub exists. Go, Java, C# require custom stack packs." Prevents wasted evaluation time from developers on other stacks. | Low |
| T1-M-06 | **Context compaction template** | A concrete skill file (`.agent/skills/meta/context-compaction.md`) and companion `AGENTS.md` protocol update implementing the context compaction pattern referenced in T1-M-01's blueprint (RFC-002 §H.9.1). The skill defines a structured summary format the agent produces at natural phase boundaries — completed actions, key decisions, failed attempts, remaining criteria, open tasks. The compaction output is written to `last_session_summary.md` and replaces conversation history in the next session rather than appending to it. This makes multi-session delivery of large features materially cheaper than single-session context exhaustion. No code — skill file plus AGENTS.md protocol addition. Dependency: none (delivers standalone value; complements T1-I-07). | Low |

## Tier 2 — Small Team / Multi-Machine
*Prerequisite: Tier 1 complete. Adds a lightweight server and sharing layer.*

### T2-A: Shared State Layer

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T2-A-01 | **MCP server wrapping SQLite** | Lightweight HTTP server (Palinode pattern) that wraps the SQLite database and exposes it as MCP tools: `get_session_history`, `get_decisions`, `get_review_verdicts`, `get_harness_health`, `search_memory`. Set up once on a shared machine; all tools on all machines point at it. When implementing, study Shokunin's memory architecture: multi-strategy recall = vector + BM25 + temporal weighting + RRF fusion. BM25 is essential for exact-match queries on code symbols and function names — vector search alone misses these. Start with SQLite + BM25, add vector search only if BM25 recall proves insufficient. Source: github.com/rohitg00/agentmemory (production-tested). **2026-05-24 architecture note**: (1) Use stdin/stdout JSON-RPC transport, not HTTP — starts/stops with each agent session, no daemon, no port management. (2) Implement BM25 as primary search strategy (k1=1.5, b=0.75, RRF k=60). Add vector search only if BM25 proves insufficient. Source: Shokunin benchmark — 60% real-session hit rate for BM25+vector vs 0% for vector-only on lexically specific queries (code symbols, function names, file paths). Reference implementation: github.com/rohitg00/agentmemory (production-tested across Claude Code, Cursor, Gemini CLI). | Medium |
| T2-A-02 | **Cross-machine session continuity** | Session state survives machine changes. When a developer moves from laptop to workstation, the new machine's agent reads the shared session history from the MCP server and continues where the last session left off. | Low (once T2-A-01 exists) |
| T2-A-03 | **memweave-style hybrid search** | Add BM25 keyword + vector search across all markdown state files (session ledger, decisions log, governance audit, skill files). `search_memory("branch isolation violation")` returns ranked results across all projects and sessions. | Medium |
| T2-A-04 | **Shared decisions log** | The `decisions_log.md` from each project is queryable via the MCP server. A new team member's agent asks "what decisions have been made about database architecture?" and gets answers from all projects. | Low (once T2-A-01 exists) |
| T2-A-05 | **RRF hybrid search for search_memory()** | Implement Reciprocal Rank Fusion search in the MCP server's `search_memory()` function, combining vector similarity (cosine) and BM25 keyword search into a single ranked result list. Algorithm: `rrf_score = 1/(60 + vector_rank) + 1/(60 + bm25_rank)` where 60 is the standard RRF constant preventing domination by a single top-ranked result. Applies to all four SQLite tables (sessions, governance_events, review_verdicts, decisions). Enables queries like `search_memory("branch isolation violation")` to return results ranked by both semantic meaning and keyword relevance. Extends T2-A-03 (memweave-style hybrid search) with a reference implementation. Source: MarkTechPost hybrid-memory agent article (HybridMemory + RRF implementation). | Medium |
| T2-A-06 | **Community detection for auto-domain tag suggestions** | Using the import graph built by T1-H-01 (networkx required), run `greedy_modularity_communities()` on the undirected version of the graph to detect structural communities. Infer suggested BDD domain tag names from the dominant directory name in each community. Write suggestions to `.agent/state/community_suggestions.md` for human review before manually updating `skill_bdd_map.json`. Runs at install time and on-demand via `python .agent/scripts/repo_map.py --communities`. Does not auto-apply tags — recommends only. Depends on T1-H-01 graph infrastructure. | Low |

---

### T2-B: Governance & Access

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T2-B-01 | **Distributed HALT sentinel** | The HALT check in `check_halt.py` queries the MCP server in addition to checking the local file. Writing a HALT to the server stops all agents on all machines. Local file check is the fallback if the server is unavailable. | Low |
| T2-B-02 | **Role-based governance tiers** | Three tiers in `.agent/config.yaml`: `implementer` (executes against approved plans), `architect` (authors plans and ADRs), `principal` (full permissions, CODEOWNERS enforced). Governance check applies the appropriate prohibition set per configured role. | Medium |
| T2-B-03 | **Remote audit trail** | `governance_audit.jsonl` and `review_verdicts` are written to the shared MCP server on each event. Audit trail is accessible from any machine and browser. Survives laptop loss. | Low (once T2-A-01 exists) |
| T2-B-04 | **Team harness health dashboard** | `harness_health.py --team` mode queries the MCP server for cross-project, cross-developer aggregate signals. "Which team member's projects have the highest FAIL rate? Which skill is degrading across the team?" | Medium |

---

### T2-C: Collaboration & Onboarding

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T2-C-01 | **Team bootstrap install** | Install script variant that points all tool supplements at the shared MCP server rather than a local SQLite file. New team member installs the harness and immediately has access to full team decision history and session context. | Low (once T2-A-01 exists) |
| T2-C-02 | **Shared skill registry** | The MCP server hosts the team's canonical skill library. Individual projects can pull updates from the shared registry. A skill improvement made for one project becomes available to all. | Medium |
| T2-C-03 | **Dream phase — team consolidation** | Dream phase distillation (T1-D-03) runs at team level as well as project level. Session learnings from all team members contribute to shared skill improvement proposals. | Low (once T1-D-03 and T2-A-01 exist) |

---

### T2-D: Multi-Stack Portability

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T2-D-01 | **Node.js stack pack** | Skills and workflow adaptations for Node.js / Express / Jest projects. Extends the install script to detect and configure Node.js environments. | Medium |
| T2-D-02 | **Go stack pack** | Skills and workflow adaptations for Go projects. | Medium |
| T2-D-03 | **Stack-agnostic pre-commit chain** | Refactor the pre-commit chain configuration to be driven entirely from `config.yaml` rather than assuming Python/Poetry. Each stack pack contributes its own hook definitions. | Medium |
| T2-D-04 | **Ollama provider for local models** | Complete `OllamaProvider` implementation in the model-agnostic review gate. Enables air-gapped operation for environments where data cannot leave the network. Directly relevant to Australian regulated industry contexts. | Medium |

---

## Tier 3 — Enterprise / Regulated
*Prerequisite: Tier 2 complete. Replaces SQLite/file server with production database infrastructure.*

### T3-A: Production State Backend

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T3-A-01 | **PostgreSQL backend** | Swap SQLite for PostgreSQL using the identical schema. Same MCP server, different connection string. Enables multi-writer safety (multiple agents committing simultaneously), standard backup/replication, and connection pooling. | Low (once T2-A-01 exists — schema swap only) |
| T3-A-02 | **Database migration framework** | Alembic migrations for the harness state schema (consistent with the pattern already used in Gym App). Schema evolution without data loss as the harness develops. | Low |
| T3-A-03 | **High availability configuration** | PostgreSQL with read replicas and connection pooling (PgBouncer). MCP server stateless — horizontally scalable. Harness state survives any single machine failure. | High |

---

### T3-B: Security & Compliance

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T3-B-01 | **Row-level security** | PostgreSQL row-level security policies scoped by `project` and `team`. A developer on Project A cannot read Project B's governance audit or session history unless explicitly granted. | Medium |
| T3-B-02 | **Audit-grade immutability** | Governance events and review verdicts are append-only. No DELETE or UPDATE permitted on audit tables — only INSERT. Separate archival process moves old records to cold storage. Satisfies audit trail requirements for regulated industries. | Medium |
| T3-B-03 | **SSO / enterprise auth for MCP server** | MCP server authenticates via OAuth / SAML. User identity is recorded on every session, approval, and governance event. "Who approved this deployment?" is answerable. | High |
| T3-B-04 | **Data residency controls** | PostgreSQL deployment options for Australian data residency (AWS ap-southeast-2, Azure Australia East). Configuration documentation for SOCI Act, ISM, and PSPF compliance contexts. Relevant to the telco/government SA work in your background. | Medium |
| T3-B-05 | **RBAC with audit log** | Full role-based access control on the MCP server. Read/write permissions per project per user. Every permission change is logged. Satisfies the "who had access to what, when" question for compliance audits. | High |

---

### T3-C: Enterprise Integration

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T3-C-01 | **DORA metrics pipeline** | DORA metric collection formalised as a pipeline: deployment frequency, lead time, change failure rate, MTTR. Data stored in PostgreSQL, visualised in Grafana alongside product operational metrics. The harness becomes the measurement layer for engineering performance. | High |
| T3-C-02 | **Jira / Linear integration** | GitHub issue manager (`scripts/github/issue_manager.py`) extended to support Jira and Linear. Planning workflow (`/ba`, `/pm` personas) reads from and writes to the team's issue tracker directly. | Medium |
| T3-C-03 | **Harness-as-a-service API** | REST API wrapping the harness state backend. Enables non-developer stakeholders to query decision history, audit trails, and harness health without CLI access. Basis for a future web dashboard. | High |
| T3-C-04 | **Compliance reporting** | Scheduled reports (weekly/monthly) that aggregate governance audit events, decision counts, review verdict distributions, and schema hardening trends into a format suitable for engineering leadership or external auditors. | Medium |

---

## Design Constraints

These are not implementation items — they are constraints that must be satisfied before the
blocked items ship. Each blocked item's PR description must include a token measurement
confirming the constraint is met.

| ID | Constraint | Blocks | Rationale |
|----|------------|--------|-----------|
| CONSTRAINT-01 | **Context injection ceiling: ≤ 2,000 tokens total injected before LLM call.** Budget allocation: repo map (T1-H-01) ≤ 600 tokens, ADR injection (T1-H-02) ≤ 400 tokens, review_context sections (PA-02) ≤ 800 tokens, co-change warnings (T1-H-03) ≤ 200 tokens. `repo_map.py` must accept `max_tokens: int` as a parameter from day one. T1-G-01 routing enforces allocation by suppressing context sources when the budget is exhausted. | T1-H-01, T1-H-02, T1-H-03, T1-G-01 | Compound context injection without a budget creates context rot at scale — arXiv 2603.07670 identifies "confidently wrong retrieved context" as the top agent reliability failure mode. More injected context is not always better; beyond a threshold it degrades reasoning quality. |

---

## Summary by Effort and Tier

| Tier | Items | Est. total effort | Prerequisite |
|------|-------|-------------------|--------------|
| **Sprint 0** | 10 items | 2–3 hours (manual) | None |
| **Tier 1** | 80 items (incl. 8 bug fixes) | 16–24 weeks | None |
| **Tier 2** | 18 items | 4–7 weeks | Tier 1 |
| **Tier 3** | 12 items | 8–12 weeks | Tier 2 |

## Recommended Starting Sequence (Tier 1)

1. **T1-A-01** + **T1-B-01** + **T1-B-02** — Extract harness, universal context, versioning (1 week)
2. **T1-D-00** + **T1-C-01** + **T1-I-03** — skill_ownership.yaml prerequisite, retrospective outcome inference, outcome-aware startup (Chain B foundation)
3. **T1-A-02** + **T1-A-03** — Install + validate scripts (makes it shareable)
4. **T1-D-01** + **T1-D-02** — SQLite index + cross-project health report
5. **T1-A-04** + **T1-A-05** — Config-driven checks + two-layer review_context (portability)
6. **T1-F series** — Documentation (required before any public sharing)
7. **T1-D-03** — Dream phase (highest compounding value, needs log data to be meaningful)

**Memory chain implementation order (corrected sequence):**
1. T1-I-00a — consolidate governance_audit.jsonl + audit_trail.jsonl (prerequisite)
2. T1-I-00b — audit audit_logger.py wiring (prerequisite)
3. T1-I-04 — staleness detection via check_drift.py (independent, highest ROI)
4. T1-I-01 — migrate session_ledger.md → JSONL, enforce hot-tier in init_session.py
5. T1-I-06 — retention cleanup script
6. T1-D-01 — deferred until a second project exists or T1-D-02 is genuinely wanted

**AGENT_DIGEST.md note**: Once T1-D-03 (dream phase) is implemented, its weekly output
becomes the second always-loaded file alongside `active_context.md`. Hot tier = two small
always-current files. Everything else is warm or cold tier, loaded on signal or on demand.

**Chain A implementation sequence (structural understanding + review gate intelligence):**

Phase 1 — Review gate structure (no external dependencies):
  T1-G-02: Pre-flight shortcut — ships independently, immediate value
  T1-G-03: ReviewVerdict Pydantic model — structural prereq for all downstream items

Phase 2 — Wiki foundation (Gemma4 MoE local, zero cost):
  T1-H-06: Compiled harness wiki layer — compile ADRs + skills + review_context into
           domain wiki pages; establish .agent/wiki/ directory
  T1-D-05: Model tiering configuration — document Gemma4/Sonnet split in config.yaml

Phase 3 — Structural intelligence (networkx):
  T1-H-01: PageRank repo map — with definition extraction and Aider diff-identifier
           personalisation; validate 600-token budget after implementation
  T1-H-02: ADR annotations (revised) — seed # ADR: domain_name comments in 15-20
           high-risk files; wire wiki page injection into ai_review.py

Phase 4 — Enhanced routing (synergy phase):
  T1-H-07: Knowledge base lint pass — weekly, Gemma4 local
  T1-G-01: Routing with review_intensity + ADR domain overrides + Gemma4 tier
  T1-H-03: Co-change combined signals — git history + import graph, confidence labels

Phase 5 — Output and polish:
  T1-G-04: Policy notes in terminal output — trivial once T1-G-01 is populated

Deferred from Chain A:
  T1-H-04: Auto-generated context at install — belongs in T1-A (install script) sprint
  T1-H-05: Dead-code scoring — already partial in harness-drift.yml

CONSTRAINT-01 applies to all context-injecting items. Token budget validation
(measure actual output against representative diff) is mandatory before T1-H-01
is merged. Wiki pages (T1-H-06) may be richer — 150-200 tokens each — since
Gemma4 compilation is zero marginal cost.

**Note on Chain B sequencing (Self-Improvement Loop)**: T1-D-00 (skill_ownership.yaml) is a pure-config prerequisite with no code dependencies — write it first, before any Chain B code. T1-C-01 and T1-I-03 deliver immediately once T1-I-01 (session_ledger.jsonl, already done) is in place. T1-D-03 + T1-I-05 (distill_dream.py, integrated contradiction check) should be written and tested manually with `--dry-run` first; promote to the weekly `harness-drift.yml` schedule only after a clean dry-run confirms thresholds produce meaningful proposals (target: at least 15 sessions spanning 14+ days). T1-I-06 update (dream_proposals/ retention) is a small addition to the already-implemented cleanup script — deliver in the same PR as T1-D-03. Quarterly review checklist should reference `dream_proposals/` review at **monthly** cadence as the working expectation; quarterly is the backstop. Human reviewer renames accepted/rejected proposals to `__reviewed`; `retention_cleanup.py` archives `__reviewed` files older than 365 days automatically.

---

## Recommended Execution Sequence (Updated May 2026)
*Supersedes the original sequence above for items not yet delivered.
The original sequence documents the rationale for what has already been built
and should be preserved as historical record.*

### v1.1.5 Sprint — Beta Ready
Theme 1 (Beta Installer Experience): HIB-006, T1-B-03, S0-03, S0-04, S0-05,
S0-06, S0-08, S0-09 — S0-05 first, before beta invitations.
Theme 2 (Token Measurement & Calibration): T1-I-02, T1-I-07, T1-M-06, T1-G-08
— T1-I-02 before T1-I-07 (dependency).
Theme 3 (Gate Trust & Calibration): T1-H-08, T1-G-07, T1-L-10, T1-G-06 —
T1-G-06 last (medium effort, depends on no undelivered items but benefits from
T1-G-07 and T1-L-10 being in place).
Human-authored in parallel: T1-M-01, T1-M-02, T1-M-04.

### Immediate — Before Any Public Promotion (Sprint 0)
S0-01 through S0-10 — manual tasks, ~2-3 hours, no agent session required.
Complete all before any LinkedIn post or external sharing.

### v1.1.0 Sprint — Demonstrably Working
Priority order:
1. BUG-01 — commit-msg hook not installed ✅ (already present since initial commit 19683c2)
2. BUG-02 — validate.py missing commit-msg check ✅ (already present since initial commit)
3. BUG-03 — empty diff on amend at commit-msg stage ✅ (fixed: ORIG_HEAD guard + empty tree fallback)
4. BUG-04 — PASS verdicts not logged (HIGH, logging fix)
5. BUG-05 — ADR domain → capability name mismatch (HIGH, routing fix)
6. BUG-06 — gate calibration too aggressive ✅ (fixed: proportionate calibration, false-positive guard)
7. T1-E-02 — LLMProvider ABC ✅ (delivered: providers.py — Anthropic/OpenAI/Ollama, zero new deps)
8. T1-L-06 — production scope statement ✅ (Sprint 0)
9. T1-L-09 — framework self-test suite ✅ (delivered: tests/ — 60 tests, all passing)
10. T1-M-01 — agent operations guide (documentation)
11. T1-M-02 — spec writing guide (documentation)
12. T1-M-05 — stack coverage acknowledgment ✅ (Sprint 0)

### v1.2.0 Sprint — Outer Loop
T1-L-01 (spec quality gate)
T1-L-02 (/ba workflow with spec-writing guide as knowledge base)
T1-L-03 (/pm workflow)
T1-L-04 (requirement → commit traceability)
T1-L-05 (acceptance gate)
T1-L-07 (incident → backlog pipeline)
T1-M-03 (mid-session observability)

### v1.3.0 Sprint — Team-Ready and Reliability
T1-C-02 (HITL approval queue)
T1-J-01 (automatic checkpoint)
T1-K-01 (supply chain malware detection)
T1-M-04 (minimal team usage guide)
BUG-07 (session heartbeat file modification)
BUG-08 (deprecated datetime.utcnow)

### Existing T1 Backlog (remaining items, reprioritised)
High: T1-E-02 (moved to v1.1.0), T1-C-02, T1-K-01, T1-J-01
Medium: T1-B-04/05/06/07, T1-J-03/04
Lower: T1-D-01/02, T1-E-01, T1-G-05, T1-H-04/05


*Last Updated: 2026-05-23 — v1.1.0 items BUG-01/02 (already present), BUG-03/06 (fixed), T1-E-02 (delivered), T1-L-09 (60 tests), BUG-08 (Sprint 0) marked complete*

---

## Archived — Delivered Items
*Items marked ✅ in the sections above are duplicated here for reference.
Original entries remain in place with their ✅ status marker.
This archive section provides a single-view summary of what shipped.*

### v1.0.0 Delivered (2026-05-21)
- T1-A-01 through T1-A-07: Standalone repo, install script, validate script,
  config-driven checks, two-layer review context, universal skills, tool supplements
- T1-F-01 through T1-F-05: Getting-started, configuration reference,
  customisation guide, AISDLC bootloader, README
- T1-G-01 through T1-G-04: Diff-aware routing, pre-flight shortcut,
  ReviewVerdict Pydantic model, policy notes output
- T1-H-01 through T1-H-02: PageRank repo map, ADR annotation + wiki injection
- T1-H-06 through T1-H-07: Compiled wiki layer, knowledge base lint pass
- T1-D-05: Model tiering configuration

### v1.1.0 Delivered (2026-05-23)
- S0-01, S0-02, S0-07, S0-11, S0-12: Pre-promotion quick wins (completed subset)
- BUG-01/02: Already present since initial commit (confirmed, no fix needed)
- BUG-03: Amend diff detection (ORIG_HEAD guard + empty tree fallback)
- BUG-06: Gate calibration (proportionate framing, false-positive guard)
- BUG-08: datetime.utcnow() deprecation fixed
- T1-E-02: LLMProvider ABC (AnthropicProvider, OpenAIProvider, OllamaProvider)
- T1-L-06: Production scope statement
- T1-L-08: High-risk commit classification
- T1-L-09: Framework self-test suite (65 tests)
- BUG-04: PASS/PASS_FAST verdict logging fixed
- BUG-05: ADR domain → capability two-layer mapping
- T1-M-05: Stack coverage acknowledgment
