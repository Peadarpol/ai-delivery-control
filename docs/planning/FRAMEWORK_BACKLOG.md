# AISDLC Harness — Comprehensive Improvement Backlog
**Created**: 2026-05-09
**Source**: Consolidation of all improvements discussed in session
**Additional Sources**: MarkTechPost (2026-05-12) — Build a Hybrid-Memory Autonomous Agent with Modular Architecture and Tool Dispatch Using OpenAI. Patterns: Tool ABC, LLMProvider ABC, Reciprocal Rank Fusion hybrid search. MarkTechPost (2026-05-15) — MCP-Style Routed AI Agent System with Dynamic Tool Exposure, Planning, Execution, and Context Injection. Patterns: RouteDecision dynamic capability routing, PlanOutput fast-path shortcut, ToolResult structured validation, policy notes explainability, restricted globals sandbox. Repowise/MarkTechPost (2026-05-15) — Repository-Level Code Intelligence with Graph Analysis, Dead-Code Detection, Decisions, and AI Context. Aider repo-map (tree-sitter + PageRank). Decision-Linked Development / Jimmy Utterström (2026-03-25) — @decision annotation pattern. codegraph (tarunms7/codegraph) — token-budget-aware PageRank context. All implemented via Python stdlib ast + networkx + git log — no external services required. MongoDB (2025-07-09) — Memory-Augmented AI Agents (memory as fundamental differentiator). Usama Amjid (2026-02-06) — Autonomous AI Agents Memory Systems Guide (five memory types, episodic outcome tagging). Iniyarajan S./Medium (2026-04-01) — Persistent AI Agent Memory Systems (token budget management, memory tiering). arXiv 2603.07670 (2026-03) — Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers (staleness/contradiction detection, retention policy, observability). DEV.to/BookMaster (2026-04-16) — Building a Memory System for Autonomous AI Agents (store + index + retrieval architecture).
**Tiers**:
- **Tier 1** — Single developer, multiple projects. No server infrastructure. Works offline.
- **Tier 2** — Small team / multi-machine. Lightweight server required. Enables sharing.
- **Tier 3** — Enterprise / regulated. Full database infrastructure. Compliance-grade.

---

## Tier 1 — Solo Multi-Project
*Prerequisite: none. Implements on top of the existing Gym App harness.*

### T1-A: Harness Extraction & Portability ✅ Complete (2026-05-21)

| ID | Item | Description | Effort | Status |
|----|------|-------------|--------|--------|
| T1-A-01 | **Standalone harness repository** | Extract the framework layer from Gym App into its own repository. Gym App becomes the first "project using the harness." Separates generic framework from project-specific config. | Medium | ✅ |
| T1-A-02 | **Bootstrap install script** | `bootstrap/install.py` — detects tech stack, copies framework files into target project, scaffolds project config from templates, wires pre-commit hooks, runs validation. Target: under 10 minutes from zero to working harness. | Medium | ✅ |
| T1-A-03 | **Environment validation script** | `bootstrap/validate.py` — confirms all required tools are installed, pre-commit hooks are wired, validate.py scripts pass, regression runner returns clean. Run at install time and on-demand. | Low | ✅ |
| T1-A-04 | **Config-driven architecture checks** | Replace hardcoded Python/Clean Architecture rules in `architecture_checks.py` with a config-driven rule set read from `.agent/config.yaml`. Any project can define its own layer boundaries and forbidden patterns without code changes. | Medium | ✅ |
| T1-A-05 | **Two-layer review_context.md** | Split `review_context.md` into a universal base layer (framework-owned, generic invariants) and a project layer (user-maintained, project-specific patterns). `ai_review.py` loads and concatenates both. New users get working AI review immediately; it improves as they fill in project context. | Low | ✅ |
| T1-A-06 | **Universal + stack-pack skills** | Split skills into universal (language-agnostic: systematic-debugging, code-review, security-audit, architect, dba) and stack packs (python-fastapi, python-django, node-express). Install script deploys universal skills always, stack pack based on detected tech. | Medium | ✅ |
| T1-A-07 | **Tool supplement generation** | Install script generates `CLAUDE.md`, `GEMINI.md`, `.cursorrules` from templates rather than requiring manual creation. Each is a thin shim pointing at `.agent/UNIVERSAL_CONTEXT.md`. | Low | ✅ |

---

### T1-B: Environment Legibility

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-B-01 | **Universal context file** | Create `.agent/UNIVERSAL_CONTEXT.md` as the single canonical context source. `CLAUDE.md`, `GEMINI.md`, and `.cursorrules` become thin shims that load it. Eliminates three-copy drift risk across tool supplements. | Low |
| T1-B-02 | **Harness versioning** | Add `harness_version.txt` at framework root and `HARNESS_CHANGELOG.md`. `init_session.py` logs the harness version with each session. Enables forensic "which harness version was running when this incident happened." | Low |
| T1-B-03 | **Onboarding workflow** | `.agent/workflows/onboarding.md` — a first-session workflow that validates the environment, runs regression suite, confirms all skill validate scripts pass, and produces a "harness health at onboarding" baseline report. | Low |
| T1-B-04 | **Skill deprecation mechanism** | Add `status` field (active/deprecated/experimental) to each skill's metadata. `select_bdd_gate.py` and `skill_mapping.yaml` respect the field. Deprecated skills are not loaded. | Low |
| T1-B-05 | **Self-service skill authoring** | `/create-skill` workflow that scaffolds a new skill from a description: creates `SKILL.md`, `validate.py`, `cases.csv`, and adds `skill_mapping.yaml` entry. Turns a 4-file manual process into a one-command operation. | Medium |
| T1-B-06 | **Skill length diagnostic audit** | Run a line-count audit of all `.agent/skills/*/SKILL.md` files and categorise by length: GREEN (<100 lines), AMBER (100-150 lines), RED (>150 lines). For each RED file, manually review to identify whether content is (a) task workflow instructions (belongs in skill), (b) long-term project rules (belongs in `review_context.md` or `UNIVERSAL_CONTEXT.md`), or (c) multiple distinct failure modes bundled together (candidate for decomposition into sub-skills). Produce a diagnostic report in `.agent/state/skill_audit.md` listing each file, its line count, category, and recommended action. This is a read-only diagnostic — no files are modified. Source: mattpocock/skills principle: "one skill, one clear problem; the shorter it is, the easier it is to call correctly and maintain." | Low |
| T1-B-07 | **Skill decomposition and remediation** | Execute the recommendations from T1-B-06 diagnostic. Three actions per RED file: (1) Move rules-content sections to `review_context.md` (project invariants) or `UNIVERSAL_CONTEXT.md` (harness-wide conventions); (2) Split multi-failure-mode skills into focused sub-skills of <150 lines each, updating `skill_mapping.yaml` and `skill_ownership.yaml` for each new skill; (3) Add an explicit **Output Format** section to every skill specifying the expected structure (e.g., Plan → Execute → Verify → Report). Additionally: add a cross-reference to `governance.md §2` escalation triggers in any skill that touches high-risk code (RBAC, auth, multi-tenant isolation, financial). Soft limit: skills should target <100 lines, hard limit: no skill file exceeds 200 lines. Enforce in T1-B-05 (`/create-skill` workflow template). Dependency: T1-B-06 complete. | Medium |

---

### T1-C: Reliability & Recovery

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-C-01 | **Retrospective session outcome inference + post-commit heartbeat** | At the top of `init_session.py main()`, call `infer_and_close_previous_session()` before any other startup logic. If the previous session's `outcome` is null, infer it from current filesystem state: HALT file or halt_event in `harness_events.jsonl` → `escalated`; commits since session start AND no FAIL verdicts AND no open tasks → `success`; commits made AND (FAIL verdicts in `.ai-review-log.jsonl` OR open tasks in `active_context.md`) → `partial`; no commits and no HALT → `abandoned`. Write using three-field schema: `outcome` (success/partial/abandoned/escalated), `outcome_source` (inferred/agent_override/human_override), `outcome_note` (optional). Platform-agnostic — works for Claude Code, Gemini CLI, Codex, Cursor, Windsurf with no per-tool hook configuration. Handles first-ever session (no previous entry) gracefully. AGENTS.md §5 Session Close should note that agents may write `outcome_override` to `session.json` before closing; the next session's inference step uses the override if present. **Post-commit heartbeat (true agent-agnostic safety net)**: add a `post-commit` stage hook to `.pre-commit-config.yaml` calling `python .agent/scripts/init_session.py --post-commit`. This fires on every `git commit` from every agent and tool — no protocol compliance required. `--post-commit` mode: updates `last_activity` in `session.json`, writes a `commit_made` event to `harness_events.jsonl`; does NOT create a new UUID, does NOT trigger the dream phase. Ensures commit activity is always captured even if startup protocol was skipped; retrospective inference can then use `git log` as a reliable fallback signal. `.pre-commit-config.yaml` stanza: `{repo: local, hooks: [{id: session-heartbeat, name: Record commit to session, entry: python .agent/scripts/init_session.py --post-commit, language: python, stages: [post-commit], pass_filenames: false, always_run: true}]}`. **Claude Code optional enhancement**: Claude Code supports native Stop hooks via `.claude/settings.json`. Adding `{"hooks": {"Stop": [{"command": "python .agent/scripts/init_session.py --stop-hook"}]}}` writes outcome immediately on session end rather than waiting for retrospective inference; `outcome_source` becomes `"hook"` instead of `"inferred"`. This composes with the retrospective inference — the Stop hook fires on Claude Code, retrospective inference is the fallback for all other platforms. Not required but improves outcome accuracy on Claude Code. Dependency: T1-I-01 (session_ledger.jsonl) must be complete. | Medium |
| T1-C-02 | **Structured HITL approval queue** | When an agent hits an escalation trigger, it writes a structured approval request to `.agent/state/pending_approvals.json` and enters a waiting state. Human edits `approved: true/false`. Agent resumes on next session. Replaces the binary HALT/hope-the-agent-stopped pattern. | Medium |
| T1-C-03 | **Harness health alerting** | If `harness_health.py` detects a CRITICAL recommendation card, automatically create a GitHub issue tagged `[harness-critical]`. Closes the gap between "flywheel detected a problem" and "a human acted on it." | Low |

---

### T1-D: Observability & Intelligence

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-D-00 | **skill_ownership.yaml — dream phase routing map** | Create `.agent/config/skill_ownership.yaml` before implementing T1-D-03. Schema: each entry maps a skill name to a list of ownership rules: `{check_type: [...], event_type: [...], keyword: [...]}`. The dream phase uses this to route detected patterns to the correct skill file for proposal generation. Without it, `distill_dream.py` cannot route patterns and falls back to writing everything to `unrouted__YYYY-MM-DD.md`. Seed with ownership rules for the skills that currently have the most governance relevance: python-backend-guidelines, testing-patterns, security-audit, database-design, agent-framework. This file grows over time as unrouted patterns reveal ownership gaps. No code dependencies — pure configuration. | Low |
| T1-D-01 | **SQLite state index — single machine** | `~/.aisdlc/harness.db` SQLite file on the developer's machine. All projects write to it via a shared `harness_state.py` library. Flat files remain the source of truth; SQLite is the derived index. Four tables: sessions, governance_events, review_verdicts, decisions. | Medium |
| T1-D-02 | **Cross-project harness health** | Update `harness_health.py` to query SQLite with a `project=` filter for single-project reports, or omit the filter for a cross-project aggregate view. "Which project has the most BRANCH_ISOLATION violations this month?" | Low |
| T1-D-03 | **Dream phase distillation (distill_dream.py)** | Batch script in `.agent/scripts/distill_dream.py`, triggered at session start (not CI). Reads 30 days of `harness_events.jsonl` and `session_ledger.jsonl`. **Flagging logic**: `count ≥ 3 AND escalation_rate ≥ 0.40 AND appearance_rate ≥ 0.20` — OR — `count ≥ 1 AND severity == "critical"` in `harness_events.jsonl` (single critical-severity event always generates a proposal regardless of frequency; addresses the salience gap identified by Generative Agents: low-frequency, high-impact events must not be filtered by count threshold). Recency weighting: `weight = sum(1.0 / (days_ago + 1))` per occurrence so recent patterns outweigh old ones. Routes each pattern to the owning skill via `.agent/config/skill_ownership.yaml`; unroutable patterns written to `dream_proposals/unrouted__YYYY-MM-DD.md` (not silently discarded). De-duplicates against existing `__open` proposals: if `{skill}__{pattern_key}__open.md` exists, updates its `Last seen` date and appends new session IDs to Evidence rather than creating a duplicate. Proposal filename: `{skill}__{pattern_key}__open.md`. Proposal format: structured markdown with Status, Generated, Last seen, Evidence, Metrics, Confidence, proposed diff, and `Action: [ ] Accept [ ] Reject [ ] Modify` checkbox. CLI flags: `--dry-run` (print without writing), `--since YYYY-MM-DD`, `--min-sessions N` (default 15, exits 0 cleanly if below threshold), `--min-span-days N` (default 14, exits 0 if sessions span less than 2 weeks — prevents burst-sprint noise). Contradiction check (T1-I-05) runs before writing each proposal; writes `{skill}__{pattern_key}__contradiction.md` instead if conflict detected. **Scheduling — not CI**: CI runners cannot access gitignored local state files (`harness_events.jsonl`, `.ai-review-log.jsonl`). Wired into `init_session.py` via `maybe_run_dream_phase()`: fires at session start when ≥ 7 days have elapsed since last run and data thresholds are met. `maybe_run_dream_phase()` logic: (1) read `dream_phase_state.json`; if absent, treat `last_run_utc` as epoch zero; (2) if `(now - last_run_utc).days < 7`, return silently; (3) load `session_ledger.jsonl` and count sessions + span — if below `--min-sessions` or `--min-span-days` thresholds, print "Dream phase: N sessions found, minimum M required" and return with `sys.exit(0)`; (4) invoke `distill_dream.py` as subprocess, capture stdout; (5) print one-line summary to agent; (6) write updated `dream_phase_state.json`. Cooldown check runs before threshold check — avoids re-reading ledger on every session start. State tracked in `.agent/state/dream_phase_state.json` (gitignored, never committed). Schema: `{"last_run_utc": "2026-06-15T08:23:11Z", "last_session_count": 18, "last_span_days": 21, "proposals_generated": 3, "proposals_written": 2, "contradictions_found": 1, "unrouted_patterns": 0}`. `proposals_generated` vs `proposals_written` distinction: contradictions and unrouted patterns are generated but not written as `__open` files — reviewer sees "3 found, 2 became proposals" and knows to check `__contradiction.md` or `unrouted__.md` files. **Session-start output**: one-line summary only — `Dream phase ran: 3 proposals generated → .agent/state/dream_proposals/ (2 open proposals, 1 contradiction card — review before next release)`. Full proposal content is not injected at startup; it is read during monthly human review. **Verification gap**: skill verification is semantic only (contradiction check). Executable verification — running the proposed rule against session evidence — requires T1-E-01 (Tool ABC) to be complete. Known gap relative to Voyager's approach; proposals are approved by human judgement, not automated verification. Dependency: T1-C-01, T1-I-03, T1-D-00 (skill_ownership.yaml). | Medium |
| T1-D-04 | **Model-agnostic review gate** | Abstract the API call in `ai_review.py` to a provider interface (`AnthropicProvider`, `OpenAIProvider`, `OllamaProvider`). Config-driven provider selection. Protects against pricing changes, enables local model use for air-gapped environments. | Medium |
| T1-D-05 | **Model tiering configuration** | Document and configure the two-tier model architecture in `.agent/config.yaml`. Tier 1 (local, zero-cost): OllamaProvider with Gemma4 MoE for wiki compilation (T1-H-06), knowledge lint (T1-H-07), dream phase distillation (T1-D-03), RouteDecision classification (T1-G-01), and ADR description extraction (T1-H-02). Tier 2 (cloud): AnthropicProvider with Claude Sonnet for the AI adversarial review gate only. Config structure: `model_routing.local_tasks: [wiki_compile, knowledge_lint, dream_phase, route_classify, adr_extract]`, `model_routing.local_provider: ollama`, `model_routing.local_model: gemma4`, `model_routing.cloud_provider: anthropic`, `model_routing.cloud_model: claude-sonnet-4-20250514`. The OllamaProvider (T1-E-02) is the implementation; this item documents the canonical task-to-tier assignment. Also configure the degrade-to-local fallback: if AnthropicProvider fails (rate limit, outage), fall back to OllamaProvider for the review gate with verdict `PASS_LOCAL` (logged distinctly in `.ai-review-log.jsonl`). Depends on T1-E-02 (LLMProvider ABC and OllamaProvider implementation). | Low |

---

### T1-E: Code Architecture & Interfaces

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-E-01 | **Formalise skills as Tool ABC subclasses** | Define a `Tool` abstract base class in `.agent/scripts/tool_base.py` with three contracts: `name: str`, `run(**kwargs) -> str`, and `schema() -> Dict` (returns OpenAI-compatible function-calling schema). Each skill that has programmatic execution (not just documentation) implements a `tool.py` subclass alongside its existing `SKILL.md`. Add a `SkillRegistry` that auto-discovers all `Tool` subclasses from `.agent/skills/*/tool.py` at startup. Benefits: skills become testable as Python objects (mock input, call `run()`, assert output), the AI review gate can dynamically compose its tool set from the registry, and `schema()` enables auto-generated documentation. The markdown `SKILL.md` remains the documentation layer; the `Tool` subclass becomes the executable layer. Source: MarkTechPost hybrid-memory agent article (Tool ABC pattern). | Medium |
| T1-E-02 | **Apply LLMProvider ABC to ai_review.py** | Refactor `src/scripts/ai_review.py` to use a formal `ReviewProvider` abstract base class: `class ReviewProvider(ABC): def review(self, system: str, diff: str) -> ReviewVerdict`. Implement three concrete providers: `AnthropicProvider` (current behaviour), `OpenAIProvider` (OpenAI-compatible API), `OllamaProvider` (local model, enables air-gapped operation). Provider selection is driven by `config.yaml` (`ai_review.provider: anthropic\|openai\|ollama`). The review gate never references a specific API after this change. Extends T1-D-04 (model-agnostic review gate) with a clean interface template. Source: MarkTechPost hybrid-memory agent article (LLMProvider ABC pattern). | Medium |

---

### T1-F: Documentation & Shareability

| ID | Item | Description | Effort | Status |
|----|------|-------------|--------|--------|
| T1-F-01 | **Getting-started guide** | `docs/getting-started.md` — install to first AI review gate firing in under 10 minutes. Written for someone who didn't build the harness. | Low | ✅ |
| T1-F-02 | **Configuration reference** | `docs/configuration.md` — every config.yaml field documented with type, default, and example. | Low | ✅ |
| T1-F-03 | **Customisation guide** | `docs/customisation.md` — how to add project-specific invariants to review_context.md, create custom skills, configure architecture checks. | Low | ✅ |
| T1-F-04 | **Refined AISDLC bootloader** | Update the bootloader document (written for a friend's fresh install) to reference the new standalone harness repository. The bootloader becomes the agent-readable setup guide for the framework. | Low | ✅ (`docs/aisdlc-bootloader.md`) |
| T1-F-05 | **Harness README** | Repository-level README with: what this is, 5-minute install, the "8 interruptions → 3 checkpoints" value proposition, link to docs. | Low | ✅ (delivered in T1-A-07) |

---

### T1-G: AI Review Gate Intelligence
*Patterns sourced from: MarkTechPost (2026-05-15) — MCP-Style Routed AI Agent System with Dynamic Tool Exposure, Planning, Execution, and Context Injection*

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-G-01 | **Diff-aware capability routing with RouteDecision** | Add a routing step to `src/scripts/ai_review.py` executing before the LLM call. The router produces a structured `RouteDecision` (Pydantic model: `selected_tools: List[str]`, `review_intensity: Literal["standard","elevated","critical"]`, `rationale: str`, `policy_notes: List[str]`). **Three routing layers**: (1) File-path routing: BRANCH_ISOLATION and TRANSACTIONAL_INTEGRITY activate when repository or service files change; ANTI_PATTERNS activates when schema or model files change; INTENT_ALIGNMENT, CODE_QUALITY, TEST_COVERAGE always activate. (2) PageRank intensity: changed files in top 10 PageRank → `elevated`; top 3 → `critical` (treat WARNs as FAILs). (3) ADR domain overrides: `# ADR: branch_isolation` annotation always activates BRANCH_ISOLATION regardless of file path; `# ADR: schema_hardening` always activates ANTI_PATTERNS. **Model tiering**: the routing classification step (not the full review) can run on the OllamaProvider with Gemma4 MoE locally for cost reduction — the Gemma4 call classifies the diff; the Sonnet call performs the actual review on the selected dimensions only. The `RouteDecision` is embedded in the `ReviewVerdict` (T1-G-03) and persisted to `.ai-review-log.jsonl`. Depends on T1-E-02 (LLMProvider ABC), T1-G-03 (ReviewVerdict), T1-H-01 (PageRank scores), T1-H-02 (ADR annotations). | Medium |
| T1-G-02 | **Pre-flight shortcut (PlanOutput fast path)** | Add a pre-flight check at the start of `ai_review.py` before the routing step. If the diff meets a fast-pass threshold (documentation-only files: `.md`, `.rst`, `.txt`; or whitespace/comment-only changes), return PASS immediately with zero LLM calls and a `planner_note` explaining the shortcut. Structured as a `PlanOutput` equivalent: `requires_review: bool`, `direct_pass_allowed: bool`, `planner_note: str`. The fast path result is logged to `.ai-review-log.jsonl` with `verdict: "PASS_FAST"` to distinguish it from a full review pass. Benefits: eliminates token cost on trivial commits; reduces gate latency from ~5s to <100ms for documentation changes. Source: PlanOutput.direct_answer_allowed pattern. | Low |
| T1-G-03 | **Formalise ReviewVerdict as Pydantic model** | Replace the current dict-based verdict output in `ai_review.py` with a typed `ReviewVerdict` Pydantic model: `verdict: Literal["PASS","WARN","FAIL","FAIL_OPEN","PASS_FAST"]`, `blocking_concern: Optional[str]`, `concerns: List[str]`, `route_decision: Optional[RouteDecision]`, `planner_note: Optional[str]`, `fail_open_reason: Optional[str]`, `model: str`, `token_usage: Dict[str, int]`. Validation at parse time means malformed LLM responses raise a typed `ValidationError` rather than an opaque JSON parse failure. The typed model is consumed by `harness_health.py` and `governance_check.py` as a structured object rather than a raw dict. Builds on the `ReviewProvider` ABC (T1-E-02) and the `ToolResult` structured validation pattern from the source article. | Medium |
| T1-G-04 | **Policy notes in terminal review output** | Update the terminal output formatting in `ai_review.py` to include the `policy_notes` from the `RouteDecision` in the printed verdict. Example output: `✅ PASS — Active: INTENT_ALIGNMENT, CODE_QUALITY, TEST_COVERAGE / Skipped: BRANCH_ISOLATION (no repository files changed), ANTI_PATTERNS (no schema files changed)`. This closes the trust gap where developers cannot tell what the gate checked vs silently skipped. A gate's silence on a concern should be explicitly explained, not ambiguous. Zero token cost — purely output formatting. | Low |
| T1-G-05 | **Restricted globals sandbox for eval_runner.py** | Apply a whitelist-based restricted globals pattern to `.agent/scripts/eval_runner.py` when executing code assertions in skill eval cases (`cases.csv`). Restrict `__builtins__` to an explicit allowlist (abs, len, print, range, sorted, str, int, float, bool, list, dict, set, tuple, zip, enumerate, sum, min, max, round, any, all) and permitted libraries (re, json, pathlib). Prevents a malicious or accidental eval case from executing arbitrary system commands during automated eval runs. Source: `tool_python_exec` whitelist pattern. Dependency: T1-E-01 (Tool ABC and SkillRegistry) should be complete before this is implemented. | Low |

---

### T1-H: Repository Intelligence
*Lightweight implementation using Python ast + networkx + git log.
Single new dependency: `poetry add networkx`. No external services.*

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T1-H-01 | **PageRank repo map generator** | Create `.agent/skills/senior-architect/scripts/repo_map.py` extending the existing `dependency_analyzer.py` AST walker. Build a directed import graph using Python stdlib `ast`. For each file, extract both import edges (graph structure) AND symbol definitions (class names, function names, method names) as node labels — without definitions the map says "this file is important" but with them it says "this file is important and contains `BranchAwareRepository`, `_apply_branch_filter`." Run `networkx.pagerank()` with a two-level personalisation signal: (1) changed files weighted 10x; (2) CamelCase identifiers found in the diff text by regex scan — files defining or importing those identifiers get additional 10x weight boost (Aider diff-identifier technique). Generate a token-budgeted ranked structural map (compact text: file path + PageRank score + dependent file count + top 3 symbol definitions). Budget: ≤600 tokens. Cache the graph in `.agent/state/repo_graph.json` keyed by file mtimes — rebuild only when source files change. Integrate into `ai_review.py` as a third context source injected before the LLM call, after diff-aware section selection (PA-02) and pre-flight check (T1-G-02). Validate token budget against a representative Gym App diff before finalising allocation. Single new dependency: `networkx`. Governed by CONSTRAINT-01. | Medium |
| T1-H-02 | **ADR annotation convention and wiki page injection** | Establish `# ADR: domain_name` comment convention (domain-keyed, not file-specific, e.g. `# ADR: branch_isolation` not `# ADR: adr_002_multi_tenant_branch_isolation.md`) for annotating source code with the governing architectural domain. The domain key maps to a compiled wiki page (T1-H-06). Detection function in `architecture_checks.py` scans changed files for `# ADR:` annotations using `re` (stdlib only). **ADR propagation via import graph**: if file A has `# ADR: branch_isolation` and the diff modifies file B which imports file A (per T1-H-01 graph), also inject the `branch_isolation` wiki page for B's diff. **Injection format**: inject the compiled wiki page summary for each detected domain (from `.agent/wiki/{domain}.md`) rather than raw ADR content — the wiki page is already synthesised and cross-referenced. Include `→ Full document: docs/decisions/adr/adr_XXX.md` so the agent can read the full ADR if it judges the change to be in that territory. **Cap**: inject at most 4 ADR domains per review; direct annotations take priority over propagated ones. Budget: ≤400 tokens total. Seed annotations as a one-time sprint task: add `# ADR: {domain}` comments to the 15-20 highest-risk files identified by the nine existing ADRs. Depends on T1-H-06 wiki pages existing. Zero new dependencies. Governed by CONSTRAINT-01. | Low |
| T1-H-03 | **Co-change blast radius estimator (combined signals)** | Create `.agent/scripts/co_change_check.py` combining two signals: (1) `git log --name-only` (via subprocess, stdlib) to build an empirical co-change frequency map from the last 200 commits; (2) the import graph from T1-H-01 to identify structural co-change partners (files that import or are imported by the changed file). Merge both signals with confidence labels: `HIGH` when both git history AND import graph agree a file should co-change; `MEDIUM` when only one signal suggests it. Surface `HIGH` confidence warnings as pre-commit output and inject them into the AI review context; surface `MEDIUM` as advisory-only. Cache the git-derived co-change map in `.agent/state/co_change_map.json`, rebuilt weekly by `harness-drift.yml`. **Cache invalidation trigger**: if the most recent commit message contains `refactor`, `rename`, or `restructure`, invalidate the cache and rebuild immediately — stale co-change data during active refactoring produces misleading warnings. Budget: ≤200 tokens for co-change warnings injected into review. Governed by CONSTRAINT-01. Zero new dependencies. Depends on T1-H-01 for import graph. | Medium |
| T1-H-04 | **Auto-generated context files at install time** | Extend `bootstrap/install.py` with a post-copy analysis step that runs the repo map generator (T1-H-01) against the target project and auto-populates a starter `review_context_project.md`. Detects architectural layers from directory structure, identifies top 10 PageRank files, counts existing ADRs, and infers test framework from `pyproject.toml`. Writes a template file populated with structural facts that the installer reviews and extends rather than authors from scratch. Removes the blank-page problem for new project installations. Depends on T1-H-01. | Low |
| T1-H-05 | **Dead-code confidence scoring** | Extend the existing `vulture` step in `drift-detection.yml` to produce structured tiered output: SAFE (confidence ≥90%), REVIEW RECOMMENDED (70-89%), and write results to `.agent/state/dead_code_report.json`. Add a Dead Code section to `harness_health.py` reading this file and tracking count-by-tier as a weekly trend (IMPROVING / STABLE / DEGRADING). Extends the existing PD-01 dead code detection with structured confidence tiers and flywheel integration. No new dependencies — vulture already supports `--min-confidence`. | Low |
| T1-H-06 | **Compiled harness wiki layer** | Create `.agent/wiki/` directory with one markdown page per architectural domain (branch_isolation, schema_hardening, uow_pattern, rbac, migration_conventions, testing_patterns). Each page synthesises the governing ADR(s), the review_context.md section, the relevant skill file rules, the architecture_checks.py enforcement rule, and the last-validated date into a coherent 100-200 token summary. Create `wiki_compile.py` script: reads raw sources (ADRs, review_context.md sections, skill files), calls OllamaProvider with Gemma4 MoE locally to synthesise each domain page, writes to `.agent/wiki/{domain}.md`. Includes `→ Full document: path` reference for each source so agents can read the original. Compilation runs weekly via `init_session.py`'s `maybe_run_dream_phase()` trigger (same session-start logic, separate cooldown state in `wiki_compile_state.json`). Full recompile only when source files have changed since last run; incremental update otherwise. **Zero marginal cost** — runs on Gemma4 MoE locally via OllamaProvider. The wiki pages are what T1-H-02 injects at review time. Depends on T1-E-02 (OllamaProvider). Source: Karpathy LLM Wiki pattern (April 2026) — compile once at ingest time, serve cheaply at query time. | Medium |
| T1-H-07 | **Knowledge base lint pass** | Weekly batch pass checking cross-reference coherence across the entire harness knowledge base. Runs on Gemma4 MoE locally via OllamaProvider. Checks: (1) **Staleness** — do identifiers referenced in review_context.md sections still exist in `src/`? (extends T1-I-04 from check_drift.py into wiki context); (2) **Factual drift** — does a wiki page say X while its source ADR says Y? (3) **Orphaned rules** — rules in review_context.md or skill files that no architecture_checks.py rule enforces; (4) **Coverage gaps** — architectural patterns in src/ with no corresponding wiki page or review_context.md rule; (5) **Cross-file contradictions** — rules in skill files that contradict rules in review_context.md (holistic version of T1-I-05 which currently only runs at dream phase proposal time). Outputs: `LINT_PASS` (clean) or structured findings file `.agent/state/wiki_lint_findings.md` listing each issue with severity and suggested fix. Wire into `harness-drift.yml` weekly schedule. `harness_health.py` reads findings file and surfaces DEGRADING if lint findings are increasing week-over-week. **Zero marginal cost** — Gemma4 MoE local. Source: Karpathy LLM Wiki lint operation; arXiv 2603.07670 §7.3 staleness and drift. Depends on T1-H-06. | Medium |

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
| T1-I-04 | **Automated memory staleness detection** | Extend `check_drift.py` (PD-01, already in `harness-drift.yml`) to parse `review_context.md` sections and verify each referenced pattern still exists in `src/`. Uses the existing AST infrastructure from `dependency_analyzer.py` and `repo_map.py` (T1-H-01). For each invariant rule in `review_context.md` that references a specific Python pattern (e.g., `_apply_branch_filter`, `HardenedBaseModel`, `BranchAwareRepository`), check whether that identifier still appears in `src/`. If not, flag as `STALE_MEMORY` with the specific rule and the last commit where the pattern existed (from `git log`). Stale memories produce false-positive review verdicts that erode gate trust. Source: arXiv §7.3 staleness, contradictions, and drift. Zero new dependencies. | Medium |
| T1-I-05 | **Memory contradiction detector (integrated into T1-D-03)** | Not a standalone script — integrated as a pre-write check inside `distill_dream.py`. Before writing any proposal, scans the target skill file for `always/never/must/must not` on the same subject (extracted by simple noun-phrase regex). If a contradiction is detected, writes `{skill}__{pattern_key}__contradiction.md` (a CONTRADICTION CARD showing the existing rule, the proposed rule, and the conflict) instead of the normal proposal. The batch script moves on to the next proposal; contradiction cards accumulate separately for human resolution. Contradiction cards are never auto-archived — they require explicit human action (`__reviewed` rename) before `retention_cleanup.py` will touch them. | Low |
| T1-I-06 | **Memory retention policy** | Add explicit retention configuration to `.agent/config.yaml`: `session_ledger_retention_days: 90`, `governance_audit_retention_days: 365`, `review_log_retention_days: 90`. Add a weekly cleanup step in `harness-drift.yml` that archives records older than the configured retention period from the warm tier (flat files) to `~/.aisdlc/archive/` (cold tier). Archived records remain searchable via the MCP server (T2-A-01) but are excluded from session startup loading. Directly relevant for privacy and compliance contexts — Australian ISM, GDPR, and SOCI Act all have data handling requirements that apply to AI system audit trails. Source: arXiv §7.5 privacy, compliance, and deletion. **Also handles dream_proposals/ retention**: moves `__reviewed.md` files older than `dream_proposals_reviewed_retention_days` (config default: 365) from `dream_proposals/` to `dream_proposals/archive/`. `__open.md` and `__contradiction.md` files are never auto-archived — they require human action first. Add `dream_proposals_reviewed_retention_days: 365` to `.agent/config.yaml` as part of implementation. | Low |

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

## Tier 2 — Small Team / Multi-Machine
*Prerequisite: Tier 1 complete. Adds a lightweight server and sharing layer.*

### T2-A: Shared State Layer

| ID | Item | Description | Effort |
|----|------|-------------|--------|
| T2-A-01 | **MCP server wrapping SQLite** | Lightweight HTTP server (Palinode pattern) that wraps the SQLite database and exposes it as MCP tools: `get_session_history`, `get_decisions`, `get_review_verdicts`, `get_harness_health`, `search_memory`. Set up once on a shared machine; all tools on all machines point at it. | Medium |
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
| **Tier 1** | 58 items | 12–18 weeks | None |
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


*Last Updated: 2026-05-21 — T1-A series complete*
