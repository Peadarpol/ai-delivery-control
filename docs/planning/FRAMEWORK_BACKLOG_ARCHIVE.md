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
