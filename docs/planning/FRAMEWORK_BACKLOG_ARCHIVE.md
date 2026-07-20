# AISDLC Harness — Delivered Items Archive

Sections moved here from `FRAMEWORK_BACKLOG.md` once fully delivered.
Each section retains its original description detail for audit and reference.
The main backlog carries a one-line pointer back to this file.

---

## T1-A: Harness Extraction & Portability ✅ Complete (2026-05-21)

| ID | Item | Description | Effort | Status |
|----|------|-------------|--------|--------|
| T1-A-01 | **Standalone harness repository** | Extract the framework layer from Gym App into its own repository. Gym App becomes the first "project using the harness." Separates generic framework from project-specific config. | Medium | ✅ |
| T1-A-02 | **Bootstrap install script** | `bootstrap/install.py` — detects tech stack, copies framework files into target project, scaffolds project config from templates, wires pre-commit hooks, runs validation. Target: under 10 minutes from zero to working harness. | Medium | ✅ |
| T1-A-03 | **Environment validation script** | `bootstrap/validate.py` — confirms all required tools are installed, pre-commit hooks are wired, validate.py scripts pass, regression runner returns clean. Run at install time and on-demand. | Low | ✅ |
| T1-A-04 | **Config-driven architecture checks** | Replace hardcoded Python/Clean Architecture rules in `architecture_checks.py` with a config-driven rule set read from `.agent/config.yaml`. Any project can define its own layer boundaries and forbidden patterns without code changes. | Medium | ✅ |
| T1-A-05 | **Two-layer review_context.md** | Split `review_context.md` into a universal base layer (framework-owned, generic invariants) and a project layer (user-maintained, project-specific patterns). `ai_review.py` loads and concatenates both. New users get working AI review immediately; it improves as they fill in project context. | Low | ✅ |
| T1-A-06 | **Universal + stack-pack skills** | Split skills into universal (language-agnostic: systematic-debugging, code-review, security-audit, architect, dba) and stack packs (python-fastapi, python-django, node-express). Install script deploys universal skills always, stack pack based on detected tech. | Medium | ✅ |
| T1-A-07 | **Tool supplement generation** | Install script generates `CLAUDE.md`, `GEMINI.md`, `.cursorrules` from templates rather than requiring manual creation. Each is a thin shim pointing at `.agent/UNIVERSAL_CONTEXT.md`. | Low | ✅ |

### T1-A: Harness Extraction & Portability — Complete (2026-06-03)

| ID | Item | Description | Effort | Status |
|----|------|-------------|--------|--------|
| T1-A-09 | **Split AGENTS.md into universal and project layers** | The current single AGENTS.md combines framework-owned universal governance (session startup protocol, prohibition table, escalation triggers, workflow naming) with project-specific content developers add post-install. This creates CONFLICT classifications during upgrade.py runs, blocking clean application of universal governance improvements. Every upgrade becomes a manual conflict resolution exercise on the most important governance file. Split into two files: (1) AGENTS.md — framework-owned universal layer containing session startup protocol (Steps 0-5), prohibition table (P-01+), escalation triggers, workflow naming conventions, skill invocation protocol, and context compaction protocol. Classified as OVERWRITE in upgrade manifest — upgrades apply cleanly without conflicts. (2) AGENTS_PROJECT.md — project-owned extension layer containing project-specific workflows, team conventions, custom escalation triggers, and any developer-added content. Classified as NEVER_TOUCH in upgrade manifest — never overwritten. Agents load both: AGENTS.md instructs agents to read AGENTS_PROJECT.md if it exists, with project layer extending but not overriding the universal layer. install.py creates AGENTS_PROJECT.md as a starter template on fresh install. upgrade.py removes AGENTS.md from CONFLICT classification and adds it to OVERWRITE. Existing projects: AGENTS_PROJECT.md is created empty on first upgrade post-delivery; developers migrate their project-specific content manually — nothing is deleted, project content in old AGENTS.md remains until migrated. Completes the two-layer architecture pattern already established for review_context (✅), wiki (✅), and tool supplements (T1-B-01). Dependency: T1-B-01 (Universal Context file) shares the same philosophy and should be delivered in the same sprint. | Medium | ✅ (v1.3.1) |

---

## T1-F: Documentation & Shareability ✅ Complete (2026-05-21)

| ID | Item | Description | Effort | Status |
|----|------|-------------|--------|--------|
| T1-F-01 | **Getting-started guide** | `docs/getting-started.md` — install to first AI review gate firing in under 10 minutes. Written for someone who didn't build the harness. | Low | ✅ |
| T1-F-02 | **Configuration reference** | `docs/configuration.md` — every config.yaml field documented with type, default, and example. | Low | ✅ |
| T1-F-03 | **Customisation guide** | `docs/customisation.md` — how to add project-specific invariants to review_context.md, create custom skills, configure architecture checks. | Low | ✅ |
| T1-F-04 | **Refined AISDLC bootloader** | Update the bootloader document (written for a friend's fresh install) to reference the new standalone harness repository. The bootloader becomes the agent-readable setup guide for the framework. | Low | ✅ (`docs/aisdlc-bootloader.md`) |
| T1-F-05 | **Harness README** | Repository-level README with: what this is, 5-minute install, the "8 interruptions → 3 checkpoints" value proposition, link to docs. | Low | ✅ (delivered in T1-A-07) |

---

## RFC-003 Session: Gate and Bootstrap Bug Fixes ✅ Complete (2026-05-27)

*Source: First real-world stress test of standalone AI Delivery Control
installation against GymBase RFC-003 delivery (2026-05-22).
These bugs were discovered during live feature delivery under the framework.*

| ID | Item | Description | Effort | Priority | Status |
|----|------|-------------|--------|----------|--------|
| BUG-01 | **commit-msg hook not installed by bootstrap** | `bootstrap/install.py` runs `pre-commit install` but does not run `pre-commit install --hook-type commit-msg`. The AI adversarial review gate is configured at `stages: [commit-msg]` but this hook stage is never wired automatically. The entire RFC-003 session ran without gate coverage because this step was missing. Fix: add `subprocess.run(["pre-commit", "install", "--hook-type", "commit-msg"], ...)` to Phase 5 (Git Hook Wiring) in `install.py`. Also add to `bootstrap/validate.py`: check `.git/hooks/commit-msg` exists alongside `pre-commit` and `pre-push` checks. | Low | CRITICAL | ✅ Already present since initial commit (19683c2). GymBase gap was environment-specific. |
| BUG-02 | **validate.py does not check commit-msg hook** | `bootstrap/validate.py` checks for `pre-commit` and `pre-push` hooks in `.git/hooks/` but not `commit-msg`. Reported ✅ "Pre-commit wired" while the gate hook was completely absent. Fix: add `commit-msg` to the hook layout check. | Low | HIGH | ✅ Already present since initial commit. |
| BUG-03 | **Gate reads staged diff at commit-msg stage — empty on amend** | The gate script reads `git diff --staged` to get the diff for review. At `commit-msg` stage during `git commit --amend`, the staged area is empty (nothing newly staged), producing an empty diff. The pre-flight shortcut classifies empty diffs as trivial and returns PASS_FAST in ~1.5s without any API call. The RFC-003 amend commit got a PASS_FAST verdict on an empty diff — the actual 1686-line RFC-003 diff was never reviewed. Fix: at `commit-msg` stage, detect amend context and read `git diff HEAD~1 HEAD` (the commit being created) rather than `git diff --staged`. | Medium | HIGH | ✅ Fixed in v1.1.0 (SE-01/SE-02 guards: ORIG_HEAD detection, empty tree fallback for single-commit repos). |
| BUG-04 | **PASS and PASS_FAST verdicts not written to log** | All 4 entries in GymBase `.ai-review-log.jsonl` are FAIL verdicts. PASS and PASS_FAST verdicts are either not being written or writing to a different path. A gate that only logs failures produces an incomplete and misleading audit trail — the framework appears to block everything when it actually passes most commits silently. Fix: ensure all verdict types (PASS, PASS_FAST, WARN, FAIL, FAIL_OPEN) write to `.ai-review-log.jsonl`. Verify the log write path is relative to the project root, not the script directory. | Low | HIGH | ✅ `_persist_verdict()` called for all verdict types. |
| BUG-05 | **ADR domain names not mapping to capability names** | Context snapshot shows `adr_domains=['branch_isolation']` (detected) but policy notes show "Skipped check: BRANCH_ISOLATION (no matching path or ADR)". The domain name `branch_isolation` (from `# ADRs:` annotation) is not being mapped to the capability name `BRANCH_ISOLATION` in the routing logic. Case or naming convention mismatch in `RouteDecision.build_route_decision()`. Fix: normalise comparison — either uppercase both sides or maintain a canonical mapping dict from domain names to capability names. | Low | HIGH | ✅ Canonical mapping dict at `ai_review.py:339`. |
| BUG-06 | **Gate calibration too aggressive — all verdicts are FAIL** | All 4 logged GymBase gate verdicts are FAIL. All 3 logged ai-delivery-control gate verdicts are FAIL. A gate that returns FAIL on every commit loses developer trust and gets bypassed (which is what happened in the RFC-003 session). FAIL should require at least one HIGH severity finding. MEDIUM findings → WARN. LOW findings → informational only. Review the system prompt — the "assume wrong until proven otherwise" framing may be generating too many HIGH findings on legitimate code. | Medium | HIGH | ✅ Fixed in v1.1.0 (proportionate calibration, false-positive guard, citation requirement for FAIL). |
| BUG-07 | **Session heartbeat "files modified" failure on amend** | The `session-heartbeat` post-commit hook modifies `session.json` during the post-commit phase. Pre-commit detects the file modification, flags it as a hook auto-fix, and rolls back the change ("Stashed changes conflicted with hook auto-fixes... Rolling back fixes..."). The heartbeat update is lost. Fix: configure the heartbeat hook with `pass_filenames: false` and ensure it writes to a gitignored state file that pre-commit doesn't track. | Low | MEDIUM | ✅ `pass_filenames: false` in template heartbeat hook. |
| BUG-08 | **`governance_check.py` uses deprecated `datetime.utcnow()`** | Warning surfaced during RFC-003 amend: `DeprecationWarning: datetime.datetime.utcnow() is deprecated`. Replace with `datetime.datetime.now(datetime.UTC)` throughout governance_check.py. | Low | LOW | ✅ Fixed in Sprint 0. |

## Archived 2026-07-20 — v1.0.0–v1.3.x Delivered Items

#### ### Sprint 0: Pre-Promotion Quick Wins (S0-01 to S0-09)
| S0-01 | **Remove `scratch/` directory from repo** | Add to `.gitignore`. Single biggest "personal workspace" signal to visitors. | ✅ |
| S0-02 | **Narrow README positioning claim** | Change "covers the full delivery lifecycle: specification → development → testing → deployment" to accurately reflect what v1.0.x actually governs. | ✅ |
| S0-03 | **Add `CONTRIBUTING.md`** | How to install, how to contribute a skill, how to report an issue. Table stakes for open source. | ✅ |
| S0-04 | **Add GitHub issue templates** | Bug report, skill contribution, feature request. Signals a maintained project. | ✅ |
| S0-05 | **Cut v1.1.5 GitHub release + tag** | Release notes from CHANGELOG.md. | ✅ |
| S0-06 | **Add CI badge to README** | Basic social proof. | ✅ |
| S0-07 | **Document convention vs enforcement in README** | Explicit section: "what is hard enforcement vs convention." The gate is the only hard mechanism. Be honest about this. | ✅ |
| S0-08 | **Surface 2-3 representative skills in docs** | Link or embed SKILL.md content. Visitors can't evaluate skill quality without cloning. | ✅ |
| S0-09 | **Add worked example to docs** | `docs/worked-example.md`: complete diff → routing decision → verdict → policy notes cycle. Shows the gate working in practice. | ✅ |

#### ### Sprint 0: Pre-Promotion Quick Wins (S0-11 to S0-15)
| S0-11 | **Add "What it prevents" section to README** | Four concrete pain points mapped to framework capabilities: wrong repo commits → P-14 guard, ungoverned AI changes → adversarial gate, context loss between sessions → session lifecycle, stale architectural rules → dream phase. Source: HIB-005. | ✅ |
| S0-12 | **Fix validate.py legacy filename warning** | `validate.py` warns on absent `review_context_project.md` even when legacy `review_context.md` exists. Check for both filenames, suppress warning if either is present. Source: HIB-010. | ✅ |
| S0-13 | **Claim "harness engineering" terminology in GitHub topics and README** | Add `agent-harness` and `harness-engineering` to the repository's GitHub topic tags. Add a sentence to the README introduction positioning the framework within the emerging harness engineering discipline. "Harness engineering" is crystallising as a defined category (dedicated awesome lists, GitHub topics, multiple frameworks). Claiming the terminology now while the field is being defined costs nothing and improves discoverability. | ✅ (v1.4.5) |
| S0-14 | **`bootstrap/uninstall.py` — clean framework removal script** | Beta testers need a governed exit path. A developer who can't cleanly remove the framework will either abandon honest feedback or delete their project. The uninstaller must: (1) remove `.agent/` directory with a confirmation prompt if `.agent/state/` or `docs/planning/specs/` contain developer content; (2) remove framework-owned scripts from `src/scripts/` — `ai_review.py`, `providers.py`, `harness_utils.py`; (3) remove tool shims `CLAUDE.md`, `GEMINI.md`, `.cursorrules` with a prompt if they appear customised; (4) remove harness hook entries from `.pre-commit-config.yaml` without destroying other hooks the project had pre-installation; (5) remove `.agent/.framework_migration_state` last. Run `pre-commit uninstall` only if the framework created `.pre-commit-config.yaml` from scratch. Low effort. High importance for beta confidence. | ✅ (v1.2.0) |
| S0-15 | **Document "pull latest ai-delivery-control before upgrading" in upgrade instructions** | The BUG-09 regex fix and the v1.1.5.2 dynamic segment parsing fix both live in `upgrade.py` in the framework repo — not in the target project. A developer with a stale clone of ai-delivery-control running an old `upgrade.py` will hit known fixed bugs with no guidance. Add a clearly visible prerequisite step to the upgrade documentation: "Before running `upgrade.py`, ensure you have the latest ai-delivery-control: `git pull` from the framework repo." Add this to `docs/getting-started.md`, the upgrade section of the README, and the `upgrade.py` help text. Must ship before v1.2.0 release. | ✅ (v1.2.0) |

#### ### T1-G: AI Review Gate Intelligence (T1-G-01 to T1-G-04)
| T1-G-01 | **Diff-aware capability routing with RouteDecision** | Add a routing step to `src/scripts/ai_review.py` executing before the LLM call. The router produces a structured `RouteDecision` (Pydantic model: `selected_tools: List[str]`, `review_intensity: Literal["standard","elevated","critical"]`, `rationale: str`, `policy_notes: List[str]`). **Three routing layers**: (1) File-path routing: BRANCH_ISOLATION and TRANSACTIONAL_INTEGRITY activate when repository or service files change; ANTI_PATTERNS activates when schema or model files change; INTENT_ALIGNMENT, CODE_QUALITY, TEST_COVERAGE always activate. (2) PageRank intensity: changed files in top 10 PageRank → `elevated`; top 3 → `critical` (treat WARNs as FAILs). (3) ADR domain overrides: `# ADR: branch_isolation` annotation always activates BRANCH_ISOLATION regardless of file path; `# ADR: schema_hardening` always activates ANTI_PATTERNS. **Model tiering**: the routing classification step (not the full review) can run on the OllamaProvider with Gemma4 MoE locally for cost reduction — the Gemma4 call classifies the diff; the Sonnet call performs the actual review on the selected dimensions only. The `RouteDecision` is embedded in the `ReviewVerdict` (T1-G-03) and persisted to `.ai-review-log.jsonl`. Depends on T1-E-02 (LLMProvider ABC), T1-G-03 (ReviewVerdict), T1-H-01 (PageRank scores), T1-H-02 (ADR annotations). | Medium | ✅ |
| T1-G-02 | **Pre-flight shortcut (PlanOutput fast path)** | Add a pre-flight check at the start of `ai_review.py` before the routing step. If the diff meets a fast-pass threshold (documentation-only files: `.md`, `.rst`, `.txt`; or whitespace/comment-only changes), return PASS immediately with zero LLM calls and a `planner_note` explaining the shortcut. Structured as a `PlanOutput` equivalent: `requires_review: bool`, `direct_pass_allowed: bool`, `planner_note: str`. The fast path result is logged to `.ai-review-log.jsonl` with `verdict: "PASS_FAST"` to distinguish it from a full review pass. Benefits: eliminates token cost on trivial commits; reduces gate latency from ~5s to <100ms for documentation changes. Source: PlanOutput.direct_answer_allowed pattern. | Low | ✅ |
| T1-G-03 | **Formalise ReviewVerdict as Pydantic model** | Replace the current dict-based verdict output in `ai_review.py` with a typed `ReviewVerdict` Pydantic model: `verdict: Literal["PASS","WARN","FAIL","FAIL_OPEN","PASS_FAST"]`, `blocking_concern: Optional[str]`, `concerns: List[str]`, `route_decision: Optional[RouteDecision]`, `planner_note: Optional[str]`, `fail_open_reason: Optional[str]`, `model: str`, `token_usage: Dict[str, int]`. Validation at parse time means malformed LLM responses raise a typed `ValidationError` rather than an opaque JSON parse failure. The typed model is consumed by `harness_health.py` and `governance_check.py` as a structured object rather than a raw dict. Builds on the `ReviewProvider` ABC (T1-E-02) and the `ToolResult` structured validation pattern from the source article. | Medium | ✅ |
| T1-G-04 | **Policy notes in terminal review output** | Update the terminal output formatting in `ai_review.py` to include the `policy_notes` from the `RouteDecision` in the printed verdict. Example output: `✅ PASS — Active: INTENT_ALIGNMENT, CODE_QUALITY, TEST_COVERAGE / Skipped: BRANCH_ISOLATION (no repository files changed), ANTI_PATTERNS (no schema files changed)`. This closes the trust gap where developers cannot tell what the gate checked vs silently skipped. A gate's silence on a concern should be explicitly explained, not ambiguous. Zero token cost — purely output formatting. | Low | ✅ |

#### ### T1-G: AI Review Gate Intelligence (T1-G-06 to T1-G-06b)
| T1-G-06 | **Structured Rebuttal Protocol** | When the gate returns FAIL, the agent currently has no governed path to contest specific findings other than `SKIP_AI_REVIEW=1` — a wholesale bypass. Add a `--rebuttal` mode to `ai_review.py`. When invoked, the agent provides a structured rebuttal file at `.agent/state/gate_rebuttal.json` with one entry per contested finding: `finding_id`, `rebuttal_type` (FALSE_POSITIVE / SPEC_REQUIREMENT / ARCHITECTURAL_INVARIANT / OUT_OF_SCOPE), `evidence`, `spec_reference` (optional). The gate performs a second LLM call via the existing `ReviewProvider` ABC (T1-E-02) with the original diff, findings, and rebuttal. The reviewer produces a `RebuttedVerdict` per finding: REBUTTAL_ACCEPTED (finding withdrawn) or REBUTTAL_REJECTED (finding upheld). A commit is unblocked only if all FAIL-level findings are either accepted or uncontested. All rebuttal outcomes are written to `.ai-review-log.jsonl`. A REBUTTAL_ACCEPTED outcome automatically triggers `false_positive_to_eval.py` (T1-L-10) — no manual invocation required. `AGENTS.md` updated to document the rebuttal path as the correct response to a FAIL believed to be a false positive; `SKIP_AI_REVIEW=1` repositioned explicitly as last resort. Dependency: T1-E-02 ✅, T1-G-03 ✅. | Medium | ✅ (v1.1.5) |
| T1-G-06a | **Rebuttal writing guidance in AGENTS.md** | Real-world use of the rebuttal protocol (GymBase, 2026-06-05) revealed that agents produce weak rebuttals because AGENTS.md documents that the protocol exists but not how to write verifiable evidence. Add to AGENTS.md §5 (or governance.md): a rebuttal evidence checklist: (1) quote the actual commit message verbatim; (2) state the spec ID and its current status; (3) cite the specific acceptance criteria the diff implements; (4) describe what the diff actually contains — file names, line count, nature of change. Assertions without verifiable facts will be rejected. Add a worked example showing weak vs strong evidence. | Low | ✅ (v1.3.1 — delivered 2026-06-05, triggered by real governance incident during GymBase SPEC-124 delivery. Rebuttal evidence checklist and worked example added to AGENTS.md §8.6) |
| T1-G-06b | **Rebuttal template file** | Create .agent/templates/gate_rebuttal_template.json with a pre-populated structure showing the required fields and inline comments explaining what constitutes verifiable evidence for each field. The template is copied by the agent when initiating a rebuttal rather than constructed from scratch. Reduces weak rebuttal rate by making the correct structure the path of least resistance. | Low | ✅ (v1.3.1 — .agent/templates/gate_rebuttal_template.json created with inline _comment_ guidance fields) |

#### ### T1-J: Agent Capability Enhancements (T1-J-01 to T1-J-01a)
| T1-J-01 | **Automatic checkpoint before file changes** | Extend `governance.md §7` (Defensive Git Checkpoint Protocol) from a voluntary 3-file threshold to an automatic per-session checkpoint. At session start, `init_session.py` creates `git stash push -m "AUTO: session-start checkpoint [session_id]"` before any other action. A `/rollback` command in `AGENTS.md` pops the stash. Eliminates the compliance gap in the current protocol — agents that skip the manual stash step currently have no safety net. Hermes source: automatic working-directory snapshot before file changes via `/rollback`. **Sprint 1 update**: Before T1-I-07, a session that went wrong could be manually unwound. Now that T1-I-07 wiring is active (ai_review.py writes HALT file when token budget is exhausted mid-session), there are realistic scenarios where an agent has made partial changes that can't be committed. Without an automatic stash at session start, recovery requires manual git archaeology. Promote from "v1.3.0 deferred" to Sprint 1 scope alongside the outer loop work. | Low | ✅ (v1.3.4) |
| T1-J-01a | **Mid-task checkpointing note for long subprocess runs** | T1-J-01 (automatic git stash at session start) covers the session-start checkpoint. Production agent guidance (TDS Sep 2025, Anthropic Dec 2024) additionally recommends mid-task checkpoints for operations exceeding ~1 minute. T1-J-01 addresses session-start checkpointing but mid-task checkpointing for long subprocess runs is not covered. Add to T1-J-01's implementation scope and to AGENTS.md §7: for any agent task that invokes a subprocess expected to run >60 seconds (wiki compilation, dream phase distillation, large spec quality check with Pass 2 LLM call), the agent should create a named git stash before invoking the subprocess: `git stash push -m "pre-subprocess: [task description]"`. This is a convention addition to AGENTS.md — no automation change. The automation version (stopping conditions with max iterations and auto-checkpoint) is a future workflow engine concern. Deliver in same PR as T1-J-01. | Low | ✅ (v1.3.4) |

#### ### HIB: Harness Improvement Backlog (HIB-HEALTH-01 to HIB-DREAM-03)
| HIB-HEALTH-01 | **harness_health.py: dream proposal staleness check** | Implement `--dream-proposals` flag in `harness_health.py`. Reads `dream_proposals.staleness_warn_days`, `staleness_critical_days`, `max_open_proposals` from config. For each `__open.md` in `.agent/state/dream_proposals/`, reads `Generated:` frontmatter field, computes age in days, emits WARN or DEGRADING signal. Config stubs added in v1.3.3 docs (`docs/harness-health.md`) are design-ahead-of-code — this item delivers the code. Low effort, stdlib only (pathlib, datetime). | Low | ✅ (v1.3.4) |
| HIB-HEALTH-02 | **harness_health.py: state file size checks** | Implement file size monitoring in `harness_health.py`. Reads `health_checks.state_file_size.*` thresholds from config. For each monitored file, checks `os.path.getsize()` against warn/critical thresholds, emits WARN or DEGRADING signal. Priority: `repo_graph_cache.json` first — it sits in the synchronous pre-commit hot path (FM3 most acute here). Config stubs added in v1.3.3 docs are design-ahead-of-code — this item delivers the code. Low effort, stdlib only. | Low | ✅ (v1.3.4) |
| HIB-GEMINI-01 | **Gemini CLI stop-hook equivalent or external verification protocol** | T1-C-01 `--stop-hook` provides post-session outcome governance for Claude Code only (`.claude/settings.json` Stop hook). Gemini CLI has no equivalent — a completed Gemini session is structurally indistinguishable from mid-task abandonment without manual spot-checks. Two options: (a) scope a Gemini CLI stop-hook equivalent if the CLI supports post-session hooks; (b) establish a lightweight external verification protocol — a mandatory post-session checklist Gemini writes to a structured file that `init_session.py` reads at next startup alongside the retrospective inference. Option (b) is convention-only but costs nothing. Verify Gemini CLI hook support before committing to option (a). Source: v1.3.3 delivery observation, 2026-06-08. | Low | ✅ (v1.3.4) |
| HIB-DREAM-01 | **distill_dream.py: wrong field name for review log keyword matching** | `distill_dream.py` reads `log.get("comments", ...)` for keyword matching and evidence text extraction from `.ai-review-log.jsonl`. The actual schema (documented in `docs/state-file-schema.md`) does not have a `comments` field — it has `summary`, `issues`, and `concerns`. Result: keyword matching against `skill_ownership.yaml` silently fails for all FAIL entries; every FAIL routes to the `code-review` default skill regardless of actual blocking concern; evidence text in proposals is always empty. Fix: replace `log.get("comments", "")` with a combined read of `log.get("summary", "") + " " + str(log.get("concerns", []))` for keyword matching, and `log.get("summary", "")` for evidence text. Discovered during GymBase dream phase diagnosis 2026-06-08 — 17 FAILs across 79 sessions produced 0 proposals due to this mismatch. | Low | ✅ (v1.3.4) |
| HIB-DREAM-02 | **Dream phase: INTENT_MISMATCH not in proposed_rules_catalog or skill_ownership.yaml** | The most frequent FAIL blocking_concern in GymBase sessions is `INTENT_MISMATCH` — implementation diverges from spec intent. This pattern key appears nowhere in `proposed_rules_catalog` (the hardcoded rule template catalog in `distill_dream.py`) and nowhere in `skill_ownership.yaml`. Result: every INTENT_MISMATCH FAIL falls through to a generic fallback rule and routes to the default skill. Fix has two parts: (1) add `INTENT_MISMATCH` to `proposed_rules_catalog` with a rule template targeting spec alignment; (2) add `INTENT_MISMATCH` to `skill_ownership.yaml` mapping it to the `verification-before-completion` skill (or a new `spec-alignment` skill if one is created). This is a data gap, not a code bug — the catalog was seeded from early GymBase patterns and did not include outer loop failure modes introduced in v1.2.0. Dependency: HIB-DREAM-01 (field name fix must land first so keyword matching actually reads the correct field). | Low | ✅ (v1.3.4) |
| HIB-DREAM-03 | **Dream phase: escalation_rate threshold permanently blocks proposals on projects without escalated sessions** | The dream phase threshold `escalation_rate >= 0.40` requires 40% of sessions exhibiting a pattern to have ended as `escalated`. In practice, `escalated` outcomes only occur when a HALT file is written or a `halt_event` appears in `harness_events.jsonl`. Projects operating normally — where sessions end as `success`, `partial`, or `abandoned` — will have `escalated = 0` permanently, making `escalation_rate = 0.0` for every pattern regardless of FAIL frequency. GymBase: 41 success, 32 None, 4 abandoned, 2 partial, 0 escalated across 79 sessions → 0 proposals despite 17 FAILs. **Fix (v1.3.4 scope)**: Change the compound threshold from `AND` to `OR` between the rate conditions: `(count >= 3 AND appearance_rate >= 0.20) OR (count >= 3 AND escalation_rate >= 0.40)` — high-frequency patterns can qualify on appearance_rate alone without requiring escalated sessions. The `OR max_severity == "CRITICAL"` bypass path remains correct and must not change. Document the revised threshold logic in `docs/harness-health.md`. Dependency: HIB-DREAM-01 and HIB-DREAM-02 must land first. Fractional weighting for `partial`/`abandoned` outcomes deferred to HIB-DREAM-03a. | Medium | ✅ (v1.3.4) |

#### ## Archived — Delivered Items (v1.0.0 through v1.3.4 Delivered sections)
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

### v1.1.5 Delivered (2026-05-29)
- Theme 1 (Beta Installer): HIB-006 (upgrade.py), T1-B-03 (onboarding.py), S0-03 (CONTRIBUTING.md), S0-04 (issue templates), S0-05 (GitHub release), S0-06 (CI badge), S0-08 (representative skills docs), S0-09 (worked example)
- Theme 2 (Token Calibration): T1-I-02 (token budget tracking), T1-I-07 (token ceiling WARN/HALT), T1-M-06 (context compaction template), T1-G-08 (diff size review strategy)
- Theme 3 (Gate Trust): T1-H-08 (model ORM roster), T1-G-07 (structured SKIP_REASON), T1-L-10 (false positive eval regression pipeline), T1-G-06 (structured rebuttal protocol)
- Additional delivered: HIB-011 (Task Magnitude Auto-Classification), BUG-05 (Dynamic routing path resolution), BUG-07 (post-commit hook), BUG-09 (upgrade.py version extraction), HIB-028 (checksums --project flag)

### v1.3.0 Delivered (2026-06-03)
- T1-L-03: /project-manager workflow + pm_scaffold.py (Gherkin-to-task, offline fallback, prompt injection defence)
- T1-L-04: check_traceability.py — stdlib-only commit-msg hook with SPEC-NNN verification, merge exemption, doc fast-path, --no-trace bypass
- T1-L-05: acceptance_check.py — AcceptanceVerdict Pydantic model, SATISFIED/PARTIAL/DIVERGED, --strict/--fail-closed flags, migration path detection
- Migration module v1_2_0_1_to_v1_3_0.py — traceability + acceptance_gate config blocks, idempotent, downgrade supported

### v1.3.1 Delivered (2026-06-03)
- T1-I-00a + T1-I-00b: circuit_breaker.py routed to harness_events.jsonl; single caller confirmed and closed
- BUG-15: check_halt.py registered as pre-commit hook with fail_fast: true
- T1-N-02: _lock_file generic context manager in harness_utils.py wired into ai-review-log.jsonl and harness_events.jsonl writes
- T1-B-01: UNIVERSAL_CONTEXT.md created; CLAUDE.md, GEMINI.md, .cursorrules converted to thin shims
- T1-A-09: AGENTS.md split into universal layer; AGENTS_PROJECT.md created; upgrade.py migration detects custom sections via difflib.SequenceMatcher
- T1-I-01 (foundation): memory_manager.py three-tier file-based architecture (hot/warm/cold) with >90 day archival
- T1-I-04: AST staleness detection in init_session.py
- T1-N-07: event_type alignment verified between circuit_breaker.py and skill_ownership.yaml
- BUG-14: governance.md P-14 and P-15 rationales added
- BUG-16: harness_version.txt read dynamically in init_session.py
- BUG-17: skill_bdd_map.json template created; validate.py WARN on absence
- BUG-18: wiki_compile.py refactored to use get_provider(tier="budget")

### v1.3.3 Delivered (2026-06-07)
- HIB-FM8-01: severity casing normalised to uppercase across all harness_events.jsonl writers
- HIB-FM8-02: harness_version field reads from harness_version.txt at ledger write time (forensic reliability fix)
- Onboarding baseline: onboarding.py writes baseline reports to .agent/baseline/ instead of project root
- Security: rebuttal_pass.json added to .gitignore
- T1-G-12: AT/FM vocabulary injected into review_context_universal.md; Gate Finding Output Format section added
- docs/state-file-schema.md (new): authoritative schema reference for harness_events.jsonl, .ai-review-log.jsonl, session_ledger.jsonl, session.json
- docs/archetypes/: A2/A3/A6 domain registry starter packs for new installations
- docs/architecture/gate-context-design.md (new): GateContext design spec (T1-G-13 v1.4.0 prerequisite, DOC-01)

### v1.3.4 Delivered (2026-06-08)
- HIB-DREAM-01/02/03: dream phase fixes — field name mismatch, INTENT_MISMATCH routing gap, appearance_rate threshold redesign
- HIB-HEALTH-01: harness_health.py --dream-proposals — staleness check for open dream proposals
- HIB-HEALTH-02: harness_health.py --file-sizes — state file size monitoring (repo_graph_cache.json priority)
- T1-M-03: session_health.py — mid-session diagnostic reporting duration, event count, warning patterns
- T1-J-01/T1-J-01a: automatic git stash checkpoint at session start + /rollback command in AGENTS.md §7
- HIB-GEMINI-01: Gemini CLI post-session verification protocol (structured close checklist)
- T1-K-06: .agent/blocked_commands.md — standalone prohibition artifact, wired into install.py
- T1-L-01a: spec collision detection — Jaccard similarity check on acceptance criteria across active specs
- docs/architecture/capability-calibration-design.md (new): T1-G-14 design spec (DOC-02)


