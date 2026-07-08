# Harness Improvement Backlog

Ad-hoc observations, small findings, and design notes captured during development sessions.
These feed into `FRAMEWORK_BACKLOG.md` when they mature into formal items.

---

## HIB-001 — Scheduler shutdown RuntimeError on event loop close

**Date**: 2026-05-16
**Source**: Antigravity
**Pillar**: Stability / Lifecycle
**Status**: ✅ Backlog / Canary 2026-05-16

`scheduler.shutdown()` is called with `wait=False` in production to avoid blocking. If the event loop closes too fast, it raises a `RuntimeError` (previously swallowed, now surfaced as `warning`). This leaves background tasks in a zombie state (`asyncio_0` leak).

**Suggested change**: Monitor production logs for "SaaS: Scheduler shutdown RuntimeError". If frequent, reconsider `wait=True` in production or refine the shutdown sequence in `startup.py`.

---

## HIB-002 — circuit_breaker.py has no automatic enforcement

**Date**: 2026-05-18
**Source**: Claude (T1-I-00b diagnostic)
**Pillar**: Governance / Enforcement
**Status**: ✅ Complete (2026-05-27) — T1-C-01 delivered; circuit breaker limits checked at session start in `init_session.py`

`circuit_breaker.py` has no automatic enforcement — voluntary only. Gate exists in `governance.md` (line 119) as a "SHOULD run before committing" manual agent step but is not wired into the session or commit lifecycle. An agent that skips it faces no consequence from the harness. Pre-commit is the wrong hook stage (circuit breaker checks session-level limits, not commit-level limits).

**Suggested change**: Resolve as part of T1-C-01 (passive session lifecycle hooks) — check limits at session start, record metrics at session close. Not a standalone item. Correct wiring: check at session start in `init_session.py`; record final metrics at session close via Stop hook.

---

## HIB-003 — Fine-tuning from dream phase trajectory data (long-horizon)

**Date**: 2026-05-18
**Source**: Hermes comparison
**Pillar**: P7
**Status**: 📅 Long-horizon — dream phase now operational (T1-D-03 delivered 2026-05-27); actionable once 6+ months of trajectory data accumulates

Once T1-D-03 (dream phase) produces 6+ months of labelled session data, evaluate exporting harness trajectories in ShareGPT format for fine-tuning a codebase-specialist model. Hermes calls this "batch trajectory generation." Not actionable until dream phase is operational and producing quality labelled outcomes.

---

## HIB-004 — pip-audit suppression flags duplicated across two files

**Date**: 2026-05-21
**Source**: Claude (security audit, PR #126 CI)
**Pillar**: Security / CI Sync
**Status**: P6

pip-audit suppression flags exist in two places (`.pre-commit-config.yaml` AND `.github/workflows/ci.yml`). Discovered when CI failed on PR #126 after local pre-commit was fixed — the `--ignore-vuln` flags were not mirrored to the CI step.

**Suggested change**: Consider extracting shared args to a `pip-audit.toml` config if the suppression list grows beyond 5 entries, making the single source of truth unambiguous. For now, any suppression added to one file must be added to the other in the same commit.

---

## HIB-005 — README lacks pain point mapping for new developers

**Date**: 2026-05-21
**Source**: T1-F README
**Pillar**: Documentation
**Status**: ✅ Complete (2026-05-22)

README lacks introductory pain point mapping for developers new to agentic workflows.

**Suggested change**: Add "What it prevents" section to README.md detailing 4 concrete pain points: wrong repo commits, ungoverned AI changes, context loss between sessions, stale architectural rules. Each maps to a specific framework capability.

---

## HIB-006 — bootstrap/upgrade.py design specification

**Date**: 2026-05-21
**Source**: T1-A-upgrade
**Pillar**: T1-A series
**Status**: ✅ Complete (2026-05-27) — `bootstrap/upgrade.py` delivered in Phase 2 (487 lines); migration chain `v1_1_0_to_v1_1_5.py`, manifest, checksums, and downgrade script also delivered

Design specification for `bootstrap/upgrade.py` — safely update an existing AI Delivery Control installation to a newer framework version without overwriting developer customisations.

**File classification** (see `bootstrap/manifest.json`):

- **framework_owned** — always overwrite on upgrade (`.agent/scripts/`, `.agent/workflows/`, `.agent/skills/`, `.agent/governance.md`, `.agent/AGENTS.md`, `src/scripts/ai_review.py`)
- **project_owned** — never touch (`.agent/config.yaml`, `skill_ownership.yaml`, `review_context_project.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`)
- **migrate_on_upgrade** — additive changes only (`.agent/config.yaml` — new fields added, existing values preserved)

**Conflict detection**: Before overwriting any framework_owned file, compare SHA-256 of installed file against `bootstrap/checksums/{version}.json` baseline. If mismatch: developer has customised the file. Preserve developer version, save framework version as `{filename}.framework-v{version}`. Surface in the pre-upgrade report.

**Skill/workflow conflicts**: If developer has a skill or workflow with the same filename as a framework skill/workflow, preserve developer version as active, save framework version as `{filename}.framework-v{version}`, print advisory to developer.

**Pre-operation report** (required before any writes): Always print a categorised summary showing OVERWRITE (framework files to be replaced), SKIP (project-owned files being preserved), MIGRATE (config fields being added), CONFLICTS (files needing manual resolution), NEW (files being added for first time). Then prompt: "Proceed? [y/N]".

**CLI flags**: `--dry-run` (print report, make no changes), `--force` (skip confirmation prompt, CI use), `--diff` (show line-level diff for CONFLICT files).

**Fresh install behaviour**: Same pre-operation report applies. If `.agent/`, `CLAUDE.md`, or existing skills are detected, inventory them and apply the same conflict detection logic before writing anything.

**Migrations**: Version transition scripts live in `bootstrap/migrations/{from}_to_{to}.py`. Each reads existing config, adds new fields with defaults, preserves existing values. Upgrade script chains migrations from project's `framework.version` to current. Pattern identical to Alembic upgrade chain.

---

## HIB-007 — Skill discovery guidance (three-part design)

**Date**: 2026-05-21
**Source**: T1-F skill discovery
**Pillar**: T1-F series
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

Three-part skill discovery design:

1. **Post-install output** (`install.py`): After successful installation, print skill discovery prompt pointing to `agentskills.io`, `github.com/topics/agent-skills`, and `docs/skills.md` (curated list by stack). Show regardless of whether a stack pack was matched — ecosystem awareness is always useful.

2. **Dream phase extension** (`distill_dream.py`): When a capability gap appears in 3+ sessions without a governing skill, generate a SKILL DISCOVERY PROPOSAL (not a skill diff) pointing to community sources before suggesting authoring from scratch. Include session count and date range as evidence. Pattern: same as `__open.md` proposals but with action: search, not apply.

3. **docs/skills.md** (T1-F series): Curated list of recommended community skills by stack. Becomes anchor content on professional site alongside the framework itself.

**Note**: No standing instruction in AGENTS.md — mid-session suggestions are noise. Discovery is surfaced at install time (once) and by the dream phase (when evidence justifies it).

---

## HIB-008 — Restructure governance.md into Always/Ask First/Never

**Date**: 2026-05-21
**Source**: T1-B governance restructure
**Pillar**: T1-B series
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

Restructure `governance.md` into Always/Ask First/Never three-category framework (source: Osmani O'Reilly, Feb 2026 — "curse of instructions" research).

**Rationale**: Research shows agents follow the first few rules and overlook the rest when presented with a flat numbered list. A three-category decision framework gives agents a mental model they can apply to novel situations, not just a lookup table.

**Implementation**: Keep P-01 through P-14 as the canonical numbered reference (immutable audit trail). Add a new operational section above the prohibition table:

- **ALWAYS** (do without asking): Run `check_repo.py` before any git operation. Run tests before commits. Write tests before implementation code. Follow active workflow from start state.
- **ASK FIRST** (escalate to human): Database schema changes. Adding or removing dependencies. Modifying auth, RBAC, or security code. Commits touching more than 5 files. Anything that contradicts a rule in `domain_rules.md`.
- **NEVER** (absolute prohibition, maps to P-series): Merge to main/master without CI approval (P-01). Delete migration files (P-02). Disable or weaken test assertions (P-03). Commit secrets or API keys (P-06). Use `git commit --no-verify` (P-11). Full P-series remains authoritative.

Update AGENTS.md and `aisdlc-bootloader.md` to reference the three-category framing as the operational layer.

---

## HIB-009 — Skill authoring: "curse of instructions" rule-count principle

**Date**: 2026-05-21
**Source**: T1-B skill authoring principle
**Pillar**: T1-B series
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

Add "curse of instructions" principle to skill quality bar and T1-B-06 audit criteria (source: Osmani O'Reilly Feb 2026 — GitHub analysis of 2,500+ agent config files; confirmed by GPT-4/Claude research).

**Rationale**: When agents are presented with many rules simultaneously, they comply with the first few and overlook the rest. A skill with 5 well-enforced rules produces better agent behaviour than a skill with 20. This is not a length concern — it is a rule-count concern. A skill can be 80 lines and still be over-specified if it contains 15 rules.

**Implementation**:

1. Add to `docs/customisation.md` under skill authoring: "Prefer 3–5 high-consequence rules over 10–20 comprehensive ones. Agents follow the first few rules and overlook the rest (curse of instructions — Osmani, 2026). Every rule you add dilutes the ones above it."
2. Add to `docs/aisdlc-bootloader.md` skill quality bar table: new row — Rule count | ≤5 high-consequence rules per skill | Why: curse of instructions.
3. Update T1-B-06 audit criteria to check rule count in addition to line count. A skill with >7 distinct MUST/NEVER/ALWAYS rules is flagged AMBER regardless of line count. Add this check to `verify_install.py` skill metadata validation.
4. Update `/create-skill` workflow (T1-B-05) template to enforce the rule-count limit at authoring time, not just at audit time.

---

## HIB-010 — validate.py warns on absent review_context_project.md (legacy name)

**Date**: 2026-05-21
**Source**: validate.py legacy name
**Pillar**: T1-A series
**Status**: ✅ Complete (2026-05-22)

Warning for absent `review_context_project.md` fires on projects that predate the two-layer split and use the legacy `review_context.md` filename. `validate.py` should check for both filenames and suppress the warning if either exists.

---

## HIB-011 — Task magnitude classification at session start

**Date**: 2026-05-21
**Source**: Session overhead observation
**Pillar**: T1-C series
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

Harness currently applies identical governance weight to all tasks regardless of scope. A single markdown file edit triggered full regression suite (50 tests), complete startup protocol, and 4-file session state update. Observed during backlog entry addition.

**Proposed solution**: Add `task_magnitude` field to `session.json`: `micro` (docs/config only), `standard` (code changes), `major` (new feature/RFC). AGENTS.md should instruct agent to classify before starting. Micro tasks: skip regression suite, skip dream phase check, minimal context load. Mirrors T1-G-02 pre-flight shortcut logic but at session level not commit level.

This is the session-level equivalent of the commit-level pre-flight shortcut (T1-G-02). Same principle: trivial changes should not pay full governance cost.

---

## HIB-012 — ADR domain name not mapping to capability name in routing

**Date**: 2026-05-22
**Source**: Routing gap
**Pillar**: T1-G-01 fix
**Status**: ✅ Complete (2026-05-27) — BUG-05 fixed in v1.1.0; canonical ADR domain→capability mapping dict added at `ai_review.py:339`

ADR domain `branch_isolation` detected in `context_snapshot` but capability `BRANCH_ISOLATION` not activated — routing logic not mapping domain names to capability names. Check case/naming convention in `RouteDecision` build logic.

---

## HIB-013 — Gate calibration too aggressive — all verdicts are FAIL

**Date**: 2026-05-22
**Source**: Gate calibration
**Pillar**: T1-G-01 calibration
**Status**: ✅ Complete (2026-05-27) — BUG-06 fixed in v1.1.0; proportionate calibration applied (HIGH→FAIL, MEDIUM→WARN, LOW→info); false-positive guard and citation requirement added

All 4 GymBase gate verdicts are FAIL with none WARN or PASS. Gate is too aggressive — agents bypass a gate that blocks every commit. Review system prompt and verdict thresholds. FAIL should require HIGH severity finding. MEDIUM → WARN. LOW → informational only.

---

## HIB-014 — Silent gate bypass with no log entry

**Date**: 2026-05-22
**Source**: Silent bypass
**Pillar**: T1-G hardening
**Status**: ✅ Complete (v1.4.5) — `GATE_SKIPPED` logs and events written to `.ai-review-log.jsonl` and `.agent/state/harness_events.jsonl` when the gate exits early.

RFC-003 session completed with gate never firing. No log entry, no warning, no visible signal. Gate absence was invisible to both agent and developer. When gate is skipped/disabled, must write a `GATE_SKIPPED` entry to `.ai-review-log.jsonl` and print a visible warning. Silent gate absence is worse than a loud failure.

---

## HIB-015 — commit-msg hook not installed by bootstrap

**Date**: 2026-05-22
**Source**: Gate silent failure
**Pillar**: T1-A-02 fix
**Status**: ✅ Complete (2026-05-27) — BUG-01 confirmed present since initial commit (19683c2); `pre-commit install --hook-type commit-msg` present in `bootstrap/install.py` Phase 5

AI review gate configured at `commit-msg` stage but `commit-msg` hook not installed = gate never fires. Entire RFC-003 session ran without gate coverage. This creates a security vulnerability, as the gate's protections are bypassed, and the gate fails to enforce its policies.

**Suggested change**: Update `bootstrap/install.py` to ensure it runs `pre-commit install --hook-type commit-msg` in addition to the default `pre-commit install`.

---

## HIB-016 — validate.py does not check for commit-msg hook

**Date**: 2026-05-22
**Source**: Validate gap
**Pillar**: T1-A-03 fix
**Status**: ✅ Complete (2026-05-27) — BUG-02 confirmed present since initial commit; `commit-msg` hook checked in `bootstrap/validate.py` hook layout validation

`bootstrap/validate.py` checks for `pre-commit` and `pre-push` hooks but not `commit-msg` hook. Gate was absent for entire session and validation reported ✅.

**Suggested change**: Update `bootstrap/validate.py` to check for the presence of the `commit-msg` hook in addition to the other hooks in the hook layout check.

---

## HIB-017 — No GATE_SKIPPED entry when gate doesn't fire

**Date**: 2026-05-22
**Source**: Fail-open log
**Pillar**: T1-G hardening
**Status**: ✅ Complete (v1.4.5) — Handled by the `_log_gate_skipped` mechanism, writing to the JSONL log when fail-open or bypass occurs before a verdict.

When gate doesn't fire (wrong stage, missing hook, API key absent), no `GATE_SKIPPED` entry is written to `.ai-review-log.jsonl`. Silent absence is worse than loud failure. Session health check (T1-C proposed) should detect gate absence and warn.

---

## HIB-018 — Gate reads empty diff on git commit --amend

**Date**: 2026-05-22
**Source**: commit-msg diff gap
**Pillar**: T1-G-01 fix
**Status**: ✅ Complete (2026-05-27) — BUG-03 fixed in v1.1.0; ORIG_HEAD detection added + empty tree fallback for single-commit repos at `commit-msg` stage

Gate reads `git diff --staged` at `commit-msg` stage. For `git commit --amend`, staged diff is empty → pre-flight fires → PASS in 1.57s → no real review. Fix: at `commit-msg` stage, read `git show HEAD` (the commit being created) not `git diff --staged`.

---

## HIB-019 — PASS and PASS_FAST verdicts not written to audit log

**Date**: 2026-05-22
**Source**: PASS not logged
**Pillar**: T1-G-03 fix
**Status**: ✅ Complete (2026-05-27) — BUG-04 fixed; `_persist_verdict()` called for all verdict types including PASS_FAST

PASS and PASS_FAST verdicts not written to `.ai-review-log.jsonl`. Only FAIL verdicts visible. Gate history is incomplete — only failures are recorded. Fix logging path for all verdict types.

---

## HIB-020 — Gate stage tradeoff: commit-msg vs pre-commit vs dual-stage

**Date**: 2026-05-22
**Source**: Gate stage tradeoff
**Pillar**: T1-G-01 design
**Status**: ❌ Deprecated — Superseded (v1.4.3 H/S/C/G tier restructure)

`commit-msg` stage is correct for intent alignment but creates empty-diff problem for amends and rebases. Consider dual-stage: `pre-commit` for diff review, `commit-msg` for message format check only.

---

## HIB-021 — Commit msg not read at commit-msg stage (BUG-09)

**Date**: 2026-05-23
**Source**: Commit msg
**Pillar**: T1-G-01 fix
**Status**: ✅ Complete (v1.4.5) — `get_commit_message` updated to prioritize reading from `sys.argv[1]` file path passed by Git at hook execution.

When the gate runs at the `commit-msg` stage, it fails to read the commit message and reports "no commit message provided" even when a message exists. The current implementation looks for the commit message in a hardcoded path (e.g., `.ai-review-temp.md`), but Git actually creates the temporary commit message at a path under `.git/COMMIT_EDITMSG` and passes that path as an argument to the `commit-msg` hook.

**Suggested change**: Update the gate script to read the commit message from the file path provided via CLI argument (`sys.argv[1]`), which Git passes when the hook is invoked.

---

## HIB-022 — Automatic framework version bump

**Date**: 2026-05-23
**Source**: Framework sync
**Pillar**: T1-A-02 fix
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

Framework sync must automatically bump `framework.version` in `config.yaml` and `UNIVERSAL_CONTEXT.md` to the new version. Currently, this process is manual, making it easy to forget or get wrong.

**Suggested change**: Update `upgrade.py` or framework compile processes to automatically detect the new framework version and update `framework.version` in `config.yaml` and `UNIVERSAL_CONTEXT.md` accordingly.

---

## HIB-023 — ADR domain validation in environment checks

**Date**: 2026-05-23
**Source**: ADR Domains
**Pillar**: T1-A-03 enhancement
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

The gate could silently warn or fail if the ADR domain names defined in `adr_capability_mappings` do not correspond to actual ADR files in `docs/architecture/adr/`. Currently, there is no validation for this mapping alignment.

**Suggested change**: Add a check to `validate.py` and `bootstrap/validate.py` to ensure that all domain names referenced in `adr_capability_mappings` correspond to real ADR files in `docs/architecture/adr/`, producing a warning if a mismatch or missing file is detected.



---

## HIB-024 — Session memory treated as facts not claims

**Date**: 2026-05-24
**Source**: Shokunin v4.2.3 verify_file_path pattern
**Pillar**: T1-I-04 / Memory
**Status**: ❌ Deprecated — Design decision finalized (commit-msg)

`init_session.py` loads `active_context.md` and acts on its contents as if they
are current facts. They are claims from a frozen point in time — the branch may
have changed, commits may have been made, tasks may be stale.

**Suggested change**: Before orientation begins, cross-reference key claims in
`active_context.md` against git reality: claimed branch vs `git branch` output,
last commit claim vs `git log -1`, open file claims vs `git status`. Print WARN
for any mismatches. Costs one subprocess call per claim. Zero new dependencies.
This is the init_session.py equivalent of Shokunin's `verify_file_path` MCP tool
— treating memory as claims requiring verification, not facts.

---

## HIB-025 — Polite suggestions in AGENTS.md degrade compliance

**Date**: 2026-05-24
**Source**: Shokunin author observation (real operational experience with 62+ skills)
**Pillar**: T1-B governance
**Status**: ✅ Complete (v1.4.5) — Imperative language audit applied to AGENTS.md.

Shokunin author found through real operational use that "MANDATORY" and
imperative language produces materially better agent compliance than polite
suggestions. "Models respond to explicit commands." This was confirmed by the
Osmani curse-of-instructions research cited in HIB-009.

**Suggested change**: Audit AGENTS.md for governance-critical sections using
conversational framing ("should", "consider", "it is recommended"). Replace with
imperative language ("must", "always", "never") where compliance is
non-negotiable. The prohibition table already uses imperative language correctly.
Candidates for tightening: session startup protocol, workflow-first section,
escalation triggers. Do not change the conversational tone in non-governance
sections (agent conduct, skills guidance).

---

## HIB-026 — Typed memory entry classification for governance events

**Date**: 2026-05-24
**Source**: Shokunin v4.2.3 entry type system
**Pillar**: T1-C-01 / Memory
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

`harness_events.jsonl` uses governance-focused `event_type` (halt_event,
governance_observation, action_trace) but doesn't classify governance-relevant
content types that the dream phase and `init_session.py` need to reason about.

**Suggested change**: Add governance-relevant entry types (adapted from Shokunin,
governance context not general session capture):
- `decision` — architectural/governance decision made this session
- `checkpoint` — phase gate passed (plan approved, UAT passed, ORR complete)
- `claim_file` — file path verified to exist at this timestamp
- `claim_function` — function signature verified at this timestamp
- `session_end` — structured auto-generated close summary

NOT applicable from Shokunin: `preference`, `command`, `general` (personal
assistant types, not governance types — don't add these).

The `session_end` type is the most immediately valuable: auto-generated at
session close via Stop hook (Claude Code) or retrospective inference fallback.
Fields: commits_made, files_changed, gate_verdicts, decisions_logged,
open_tasks_remaining, outcome. Supplements agent-written last_session_summary.md
with a compliance-independent machine-generated record.

---

## HIB-027 — .agent/memory/ directory separation

**Date**: 2026-05-29
**Source**: Cole Medin / Anthropic large codebase blog post
**Pillar**: T1-B / Environment legibility
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

Cole Medin's implementation uses a dedicated `/memory` folder for agent memory
files, separate from operational state. The current harness mixes agent memory
files (e.g. `active_context.md`, `last_session_summary.md`) with operational
state files (circuit breaker counts, event log) under `.agent/state/`. This
reduces legibility — it is not obvious which files are agent-written memory and
which are harness-managed operational data.

**Suggested change**: Create `.agent/memory/` for agent-written memory files and
retain `.agent/state/` for harness-managed operational files only. Migration
scope:
- Move `active_context.md`, `last_session_summary.md`, and any session
  observation files to `.agent/memory/`
- Update path references in `init_session.py`, `AGENTS.md`,
  `UNIVERSAL_CONTEXT.md`, and any skill scripts that read/write these paths
- Add a migration module (`v1_x_x_to_v1_3_0.py`) to relocate files on upgrade
- Update `.gitignore` to cover `.agent/memory/session_observations_*.md`

Deferred to v1.3.0 T1-B environment legibility sprint to avoid churn mid-v1.1.x
series. No behaviour change — pure path reorganisation.

---

## HIB-028 — generate_checksums.py --verify misleading output on customised installations

**Date**: 2026-05-29
**Source**: BUG-09 / v1.1.5 release
**Pillar**: T1-A / Bootstrap integrity
**Status**: ✅ Resolved — direct fix shipped in v1.1.5 as BUG-09

`generate_checksums.py --verify` was designed to validate the framework author's
release artefacts, not installed projects. On customised installations it
produced false-positive failures because developer-modified files (legitimately
changed post-install) were compared against release-time checksums. The flag's
help text did not warn about this, making the output misleading for any consumer
other than the release pipeline.

**Resolution**: `generate_checksums.py --verify` now guards against project-context
misuse with an explicit warning and early exit when run outside the framework
source tree. See BUG-09 in `FRAMEWORK_BACKLOG.md` for the full fix record.

---

## HIB-029 — Session-end lightweight observation capture

**Date**: 2026-05-29
**Source**: Cole Medin / Anthropic large codebase blog post
**Pillar**: T1-D-03 / Dream Phase signal
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

The dream phase (T1-D-03) runs weekly and requires frequency thresholds before
generating improvement proposals. Observations that don't yet meet the threshold
are lost before the dream phase runs — the freshest signal (end of session, full
context) is discarded.

**Suggested change**: Add a lightweight session-end observation step to the
session close protocol in `AGENTS.md`. At session close the agent writes 3–5
bullet raw observations to `.agent/state/session_observations_{date}.md`:
patterns noticed, files referenced repeatedly, friction points, awkward code
patterns. No proposals, no structured schema — raw signal only. `distill_dream.py`
reads these alongside `harness_events.jsonl` when it runs. Gitignore the
observations directory.

This avoids the alignment problem Cole identifies (agents proposing self-serving
rule changes) because observations ≠ proposals — humans still decide what becomes
a skill or rule update. The dream phase governance layer is preserved; this only
feeds it richer signal. Cost: one paragraph in `AGENTS.md` and a gitignored
observations file.

---

## HIB-030 — Path-based skill activation in skill_ownership.yaml

**Date**: 2026-05-29
**Source**: Cole Medin / Anthropic large codebase blog post
**Pillar**: T1-H-04 / Skill routing
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

The harness activates skills based on capability type (`check_type`,
`event_type`, keyword). There is no mechanism to auto-load a skill when the
diff touches a specific directory — e.g. a security-audit skill activating
whenever `src/auth/` is touched, or UoW/soft-delete skills activating only for
`src/**/repositories/**`. Domain-specific skills end up either always-on (noisy)
or manually invoked (forgotten).

**Suggested change**: Add an optional `paths:` field to each entry in
`skill_ownership.yaml` alongside existing ownership rules. When the diff contains
files matching a configured path glob, the skill is included in the session
context regardless of capability routing. Pattern:

```yaml
paths:
  - "src/**/repositories/**"
  - "src/**/services/**"
```

Logic: path match OR capability match triggers inclusion — purely additive to
existing routing. Connects to T1-H-04 (auto-generated context at install time),
which could auto-populate initial path rules from the project's directory
structure at install time.

---

## HIB-031 — Sub-agent exploration patterns in workflow documentation

**Date**: 2026-05-29
**Source**: Cole Medin / Anthropic large codebase blog post
**Pillar**: T1-B / Workflow documentation
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

The harness workflows (`feature-implementation.md`, `architect.md`) do not
mention sub-agent exploration patterns. As projects grow and sessions regularly
hit context limits, the absence of this guidance causes agents to load full
exploration context into the primary session, crowding out implementation space.

**Suggested change**: Add a sub-agent exploration step to
`feature-implementation.md` Phase 1 (Plan) and `architect.md`. Before planning
or implementation begins, the agent dispatches a sub-agent to explore relevant
codebase sections and returns a summary. The primary session consumes only the
summary, not the full exploration context. Template language for `AGENTS.md`:

> "For tasks touching more than 3 service domains, dispatch a sub-agent with
> `Task()` to explore each domain independently before beginning the
> implementation plan. Consume only the summary in the primary session."

Low effort — documentation only, no code changes. Directly addresses the
context-bloat failure mode Cole identifies for large codebases.

---

## HIB-032 — Policy-as-code governance layer (Starlark) as long-horizon consideration

**Date**: 2026-05-29
**Source**: majiayu000/harness ecosystem research
**Pillar**: Governance architecture
**Status**: ❌ Deprecated — Mitigated (AGENTS.md H-01 rule)
  infrastructure exists

The majiayu000/harness project implements a Starlark-based execution policy
engine with a hardened parser dialect (no `load`, `def`, or `lambda`
permitted) for sandboxed rule evaluation. Starlark is a deterministic,
sandboxed subset of Python designed for configuration and policy expression.

This is architecturally more robust than markdown conventions for governance
rules: policies are machine-evaluatable, agents cannot modify the evaluation
language itself, and the hardened dialect prevents agents from using
full-Python constructs to escape policy constraints.

**Relevance to AI Delivery Control**: The current governance model relies on
markdown conventions (AGENTS.md, governance.md) that agents can read and
reason around, and Python scripts (architecture_checks.py) that are
framework-owned but language-specific. A Starlark policy layer would:
(1) make governance rules evaluatable without agent interpretation;
(2) be language-agnostic (not Python AST-specific);
(3) be auditable as committed policy files alongside application code.

Not actionable before Tier 2 infrastructure (v2.0.0). File as a design
input for the v3.0.0 compliance and enterprise governance milestone where
formal control mapping (SOCI Act, ISM, PSPF) requires machine-evaluatable
policies, not prose conventions.

---

## HIB-033 — Adversarial separation becoming ecosystem table stakes

**Date**: 2026-05-29
**Source**: Harness engineering ecosystem research; CodeRabbit analysis
**Pillar**: Positioning / competitive differentiation
**Status**: ❌ Deprecated — Non-actionable (Market monitoring)

When AI Delivery Control was conceived, the adversarial separation between
writing agent and reviewing model was a distinctive architectural claim. As
of May 2026, independent cross-agent review is appearing in multiple
ecosystem projects (majiayu000/harness explicitly prevents self-review by
architecture; CodeRabbit Plan uses separate models for planning vs
generation; the RALPH loop pattern is widely adopted).

**Implication**: The adversarial separation is becoming table stakes, not
a differentiator. The durable differentiation is shifting toward:
(1) hard enforcement at the commit boundary (most ecosystem harnesses are
soft governance — advisory rather than blocking);
(2) compliance-grade audit trail (harness_events.jsonl, ai-review-log.jsonl,
.framework_migration_state — none of the ecosystem tools have this);
(3) the self-improvement loop (dream phase producing project-calibrated
skill proposals — no fast-follower can replicate months of session data);
(4) the structured rebuttal protocol with incentive controls (the alignment
problem analysis is unique to AI Delivery Control).

**Suggested action**: Update the README Strategic Context section to
de-emphasise "adversarial separation is unique" and emphasise the harder-to-
replicate differentiators listed above. The positioning should lead with
the audit trail and self-improvement loop, not the two-model architecture
that the ecosystem is now converging on.

---

## HIB-034 — AGENTS.md length audit and line ceiling enforcement

**Date**: 2026-05-30
**Source**: v1.2.0 planning — context budget review
**Pillar**: Environment legibility / agent compliance
**Status**: ✅ Resolved — v1.2.0 hardening sprint

**Resolution**: Added `ALWAYS_LOADED_LINE_CEILING = 300` constant and ceiling checks for `.agent/AGENTS.md`, `.agent/governance.md`, and `src/scripts/review_context_universal.md` to `check_skills_hygiene.py`. Added 150-line archival check to `AGENTS.md` §6 Session Close checklist and to `business-analyst.md` Phase 5.

The framework enforces a 150-line limit on skills (validated by
T1-B-06/07) but has no equivalent ceiling on AGENTS.md — the document
agents read on every single session start. AGENTS.md has been extended
in every release: provider sections, workflow sections, rebuttal
hierarchy, task magnitude classification, context compaction protocol,
session budget rules. By v1.1.5 it is likely 400-600+ lines. The
v1.2.0 additions will extend it further.

The "curse of instructions" research (Osmani) validates the skill limit
and applies equally here: compliance per rule decreases as total rules
increase regardless of model capability. An AGENTS.md that requires
agents to process 600 lines on every session start is actively
counterproductive.

**Suggested changes**:
1. Run a line count audit on AGENTS.md in the current GymBase
   installation before any v1.2.0 content is added. If over 400 lines,
   prune before extending further.
2. Pruning principle: content that applies only within a specific
   workflow context (spec gate procedures, /ba session rules, /pm
   rules) belongs in that workflow's document and should be referenced
   from AGENTS.md, not duplicated. AGENTS.md should contain only global
   invariants — rules that are always true regardless of which workflow
   is active.
3. Establish a 300-line ceiling on AGENTS.md and enforce it as a
   pre-commit check (the Agent Skills Hygiene Scan hook is the natural
   home for this). This mirrors the 150-line skill limit and closes the
   inconsistency.
4. Apply the same ceiling to `governance.md` and
   `UNIVERSAL_CONTEXT.md` — any always-loaded document should have a
   governed length limit.

---

## HIB-035 — decisions_log.md retention policy (pre-T1-I-06 interim)

**Date**: 2026-05-30
**Source**: v1.2.0 planning — context budget review
**Pillar**: Memory / context management
**Status**: ✅ Resolved — v1.2.0 hardening sprint

**Resolution**: Added 150-line archival check to `AGENTS.md` §6 Session Close checklist and to `business-analyst.md` Phase 5 (archival prompt before writing new decisions). The formal retention policy (T1-I-06) remains deferred to v1.3.0.

`decisions_log.md` grows indefinitely with no retention policy.
A project with 50 active sessions could have a 2,000+ line decisions
log being injected into every adversarial review context. This
degrades review quality — the gate's context window fills with old
decisions that are no longer relevant to the current diff.

T1-I-06 (Memory Retention Policy, v1.3.0) is the formal solution.
Until it ships, an interim convention should be established:

**Suggested interim convention**: decisions older than 90 days that
have not been referenced in a recent session should be moved from the
active `decisions_log.md` to an archive file
`decisions_log_archive.md`. The review gate reads only
`decisions_log.md`. The /ba workflow Phase 4 step that writes new
decisions should also include a check: if `decisions_log.md` exceeds
150 lines, prompt the developer to archive the oldest entries before
adding new ones. Document this convention in `AGENTS.md` and the
agent operations guide (T1-M-01).

---

## HIB-036 — Atomic config migration rollback

**Date**: 2026-05-30
**Source**: Migration chain robustness review
**Pillar**: Bootstrap / upgrade reliability
**Status**: ✅ Resolved — v1.2.0 hardening sprint

**Resolution**: `upgrade.py` and `downgrade.py` both now snapshot `config.yaml` to `.yaml.migration_backup` before the migration chain executes, and restore from the backup on any exception. The backup is deleted on clean completion. Stale backup detection added to both CLIs with `--force` override. Scope limitation documented: framework file changes applied before an exception are not auto-rolled back.

**Problem**: If a migration chain partially completes — for example,
`v1_1_0_to_v1_1_5.py` succeeds but `v1_1_5_to_v1_2_0.py` fails
mid-execution — `.agent/config.yaml` is left in a partial state with
no clean recovery path. `.framework_migration_state` has not been
updated so a retry attempt will try to re-run from an incorrect
starting point, compounding the corruption.

The conflict file sidecar pattern in HIB-006 handles file conflicts
atomically. Config migrations have no equivalent protection.

**Suggested changes**:
1. At the start of the migration chain (before any module runs),
   snapshot `.agent/config.yaml` to
   `.agent/config.yaml.migration_backup`.
2. If any migration module raises an exception or exits with error,
   restore `.agent/config.yaml` from the backup, delete the backup
   file, and exit `upgrade.py` with a clear error message:
   `"Migration failed at vX.X → vX.X. Config restored to pre-upgrade
   state. No changes have been committed."`
3. On successful completion of the full chain, delete the backup file.
4. Write a `migration_backup_created` event to `harness_events.jsonl`
   at backup creation time, and a `migration_backup_deleted` event on
   successful completion or rollback, so the upgrade audit trail is
   complete.

---

## HIB-037 — Pre-flight installation state validation before migration

**Date**: 2026-05-30
**Source**: Migration chain robustness review
**Pillar**: Bootstrap / upgrade reliability
**Status**: ✅ Resolved — v1.2.0 hardening sprint

**Resolution**: `_pre_flight_check()` added to `upgrade.py`. Checks a deterministic 8-file sample set (`ai_review.py`, `providers.py`, `harness_utils.py`, `governance_check.py`, `init_session.py`, `AGENTS.md`, `check_halt.py`, `feature-implementation.md`) against the installed version's checksum registry. Halts on >3 mismatches; warns within threshold. `--skip-preflight` flag available for intentionally customised installations. `downgrade.py` gains matching `--skip-preflight` for full parity.

**Problem**: Nothing currently validates that the target installation
is in a healthy state before the migration chain runs. A developer who
interrupted a previous upgrade may have `.framework_migration_state`
declaring version v1.1.0 while their installed files are partially
v1.1.5. Running the migration chain on a broken installation produces
cascading failures with no clear diagnosis.

**Suggested changes**:
1. Add a `_pre_flight_check(project_root, declared_version)` function
   to `upgrade.py` that runs before migration discovery.
2. The function loads the checksum dictionary for `declared_version`
   from `bootstrap/checksums.py` and spot-checks a sample of
   FRAMEWORK_OWNED files (5-10 files, weighted toward high-change
   files like `ai_review.py` and `init_session.py`).
3. If mismatches exceed a configurable threshold (default: 3 files),
   print a clear warning:
   `"⚠️ Installation state mismatch detected for declared version
   vX.X.X. X of Y sampled files do not match expected checksums.
   Run bootstrap/validate.py before upgrading."`
   and exit 1, halting the upgrade before any changes are made.
4. If mismatches are within threshold (e.g. developer has made
   governed customisations), print a lower-visibility advisory and
   continue.
5. Add `--skip-preflight` flag for cases where the developer has
   intentionally customised files and understands the state.

---

## HIB-038 — Migration chain contiguity assertion

**Date**: 2026-05-30
**Source**: Migration chain robustness review
**Pillar**: Bootstrap / upgrade reliability
**Status**: ✅ Resolved — v1.2.0 hardening sprint

**Resolution**: `_assert_chain_contiguous()` added to `upgrade.py`. Uses `packaging.version.Version` for correct semver comparison. Walks from installed version to target using greedy fork resolution (selects largest `TO_VERSION ≤ target` at each fork). Halts on major/minor gaps; warns on patch gaps. `FROM_VERSION`, `TO_VERSION`, `MIGRATION_TYPE` constants added to all four migration modules. Fork at v1.1.5 (v1_1_5_to_v1_1_5_1 vs v1_1_5_to_v1_2_0) resolved by greedy selection of the minor-branch module when upgrading to v1.2.0.

**Problem**: The `discover_migrations()` function in `upgrade.py`
finds all migration modules between source and target version and runs
them in sequence. If a module is missing from the chain — deleted
accidentally, absent in a custom fork, or skipped in a branched
development — the discovery silently skips that version's config
changes. The developer gets no indication that a migration was omitted.

**Suggested changes**:
1. After `discover_migrations()` builds the ordered list of modules to
   run, assert the sequence is contiguous: each module's source version
   must equal the previous module's target version, forming an
   unbroken chain from installed version to target version.
2. If a gap is detected, halt with a specific error:
   `"Migration chain incomplete: no migration module found between
   vX.X.X and vX.X.X. Upgrade cannot proceed safely."`
3. For patch-level migrations that are deliberately no-ops (e.g.
   v1_1_5_to_v1_1_5_1.py), add a module-level constant
   `MIGRATION_TYPE = "patch"`. The contiguity check treats patch
   modules as optional — their absence generates a WARNING rather
   than a hard halt, since patch migrations by convention carry no
   config schema changes.
4. Document the `MIGRATION_TYPE` convention in `CONTRIBUTING.md` so
   future migration authors know to declare it.

---

## HIB-039 — Replace string-based YAML injection with ruamel.yaml

**Date**: 2026-05-30
**Source**: Migration chain robustness review
**Pillar**: Bootstrap / upgrade reliability
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

**Problem**: Migration modules currently append YAML blocks to
`.agent/config.yaml` using string-based injection. YAML is fragile
for string manipulation — indentation errors, comment displacement,
and key collision can silently produce malformed configs. This is most
likely to fail on heavily customised installations (as demonstrated by
the GymBase upgrade with 9 conflict files).

**Suggested changes**:
1. Replace string-based config mutations in all migration modules with
   `ruamel.yaml`, which preserves inline comments, handles indentation
   correctly, and produces valid YAML on round-trip.
2. Add `ruamel.yaml` as a bootstrap dependency (install-time only,
   not a runtime dependency of the gate scripts). Justify: bootstrap
   is the correct place for installation tooling dependencies.
3. Create a shared `_mutate_config(config_path, mutations_fn)`
   helper in `bootstrap/` that wraps ruamel.yaml loading, applies a
   caller-supplied mutation function, and writes back atomically. All
   migration modules use this helper rather than writing YAML
   manipulation inline.
4. Retrofit existing migration modules to use `_mutate_config()` when
   this HIB is implemented, ensuring consistency across the full
   migration chain.

**Note**: This is a lower priority than HIB-036/037/038 because the
string injection approach has worked in practice. It becomes higher
priority as the number of migration modules grows and the config
structure becomes more complex.

---

## HIB-040 — Context-injection attack surface: governance layer as a novel supply chain threat

**Date**: 2026-05-30
**Source**: Security review of framework distribution model
**Pillar**: Security / Trust Model
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

**Problem**: Traditional supply chain security (pip-audit, bandit, guarddog) focuses
on malicious executable code. AI governance frameworks introduce a qualitatively
different attack vector: an attacker who compromises a governance framework does not
need to inject malicious code — they need to inject malicious natural language
instructions.

A modified `AGENTS.md` could instruct agents to: generate code with specific
vulnerability patterns, approve commits that would otherwise be blocked, or exfiltrate
context through the review gate's API calls. A modified review gate system prompt
could selectively pass dangerous diffs. A modified workflow file could redirect
agent behaviour at critical decision points. None of this requires a single line of
malicious Python — and none of it is detectable by any current security scanner.

The "dark factory" risk amplifies this vector: a development team running agents
autonomously against an unreviewed governance framework is the high-value target.
The governance layer is trusted implicitly after installation. Nobody re-reads
AGENTS.md twice once it is installed.

**Why this is novel**: Traditional supply chain attacks embed malicious behaviour in
executable code or build scripts. This attack embeds malicious behaviour in natural
language documents that AI agents interpret as instructions. The harm unfolds through
AI reasoning rather than code execution. No existing scanner, SAST tool, or
dependency audit can detect it. The only defences are human review, content hashing,
and GPG-signed distribution — all of which rely on human vigilance in a way that
traditional supply chain security does not.

**Suggested changes**:
1. Publish a formal security review of the framework's context-injection attack
   surface as `docs/security/attack-surface-review.md` before broad community
   distribution (T1-K-02 in FRAMEWORK_BACKLOG.md).
2. Add `docs/security/` directory documenting every context injection point with
   expected content (S0-18) — creating a visibility baseline that makes malicious
   modifications harder to hide.
3. Implement `validate.py --security` mode (S0-17) so users can verify governance
   file hashes without reading Python source.
4. GPG-sign all releases (S0-16) so distribution-channel attacks cannot substitute
   a modified framework without invalidating the signature.
5. Add T1-K-03 (governance file diff highlighting on upgrade) so users cannot
   accidentally accept AGENTS.md changes without seeing exactly what changed.
6. Publish this threat model publicly in `SECURITY.md` — establishing the
   visibility baseline creates accountability for any future modifications.

**Resolution dependency**: S0-16 (GPG signing) is the highest-priority single
action. It addresses the distribution-channel attack vector that checksums alone
cannot close: an attacker who modifies both the framework files and the checksum
registry passes `--verify`. A GPG signature requires the private key and cannot
be forged.

**References**: `SECURITY.md` — "The Context-Injection Attack Vector" section.
`FRAMEWORK_BACKLOG.md` — T1-K-02, T1-K-03, S0-16, S0-17, S0-18.

---

## HIB-041 — Naive YAML parser is too strict on multi-line text blocks

**Date**: 2026-05-30
**Source**: Gym Management System upgrade failure (v1.1.5.2 to v1.2.0)
**Pillar**: Bootstrap / upgrade reliability
**Status**: ✅ Complete (v1.4.7) — Centralized validate_yaml_config helper created in migration_base.py supporting block scalars and refactored all migration files.

**Problem**: The `_validate_config` method implemented in several migration files (e.g., `v1_1_5_to_v1_2_0.py`, `v1_1_0_to_v1_1_5.py`) validates YAML syntax line-by-line using `":" not in line and not stripped.startswith("-")`. This fails on perfectly valid YAML multi-line block scalars (blocks starting with `|` or `>`) if a text line inside the block lacks a colon (such as comment lines or instruction steps like `"Dependabot auto-creates PRs..."`).

**Consequence**: During upgrades, the `UpgradeManager` runs config validation on `config.yaml`. If any multi-line block text contains a line without a colon, it throws a `ValueError: Malformed YAML`, halting the upgrade and triggering a full rollback.

**Suggested changes**:
1. Refactor `_validate_config` in all migration scripts to be robust against multi-line text blocks.
2. A simple state machine can track block scalar starts (e.g., detection of `|` or `>` at the end of a line) and bypass validation for lines indented deeper than the block key until indentation decreases back to the root or sibling level.
3. Alternatively, simplify `_validate_config` to check only basic structural sanity, or rely on a standard Python YAML parser try-except pattern during validation.

---

## HIB-042 — pre-commit-config.yaml.template uses Windows-only `cmd /c` for all local hooks

**Date**: 2026-05-31
**Source**: Sprint 1 implementation plan review — T1-L-04 traceability hook wiring
**Pillar**: Bootstrap / cross-platform portability
**Status**: ✅ Complete (v1.4.5) — Removed `cmd /c` prefix from all local hook entries in the template for cross-platform portability.

**Problem**: Every local hook in `bootstrap/templates/pre-commit-config.yaml.template` uses `cmd /c [PROJECT_PACKAGE_MANAGER] run python ...` as its `entry`. `cmd /c` is Windows shell syntax. On Linux and macOS, pre-commit's `language: system` invokes the entry string directly — `cmd` is not present and the hook fails to execute entirely. This affects all custom local hooks: mypy, architecture-checks, skills-hygiene, behaviour-checks, regression-check, governance-audit, session-heartbeat, and the AI adversarial review gate.

This was identified when specifying the T1-L-04 traceability hook (Sprint 1 plan) but the issue predates that — it is present in the existing template for every local hook.

**Impact**: Any non-Windows installation that runs `pre-commit install` from this template gets a set of hooks that silently fail. The AI review gate, the session heartbeat, and the architecture checks all appear installed but never execute on Linux/macOS.

**Suggested fix**: Replace `cmd /c [PROJECT_PACKAGE_MANAGER] run python` with a cross-platform entry pattern. The cleanest option compatible with `language: system` is to use the package manager directly without the shell wrapper:

```yaml
entry: uv run python .agent/scripts/check_traceability.py
```

Since `[PROJECT_PACKAGE_MANAGER]` is already a template placeholder, the installer substitutes it — the fix is to drop `cmd /c` from the wrapper and let the package manager binary handle subprocess creation cross-platform. Alternatively, use `python` directly if the project's virtual environment is activated by pre-commit's environment setup.

**Scope**: All local hooks in `pre-commit-config.yaml.template`. Also update `install.py` documentation and `getting-started.md` if it instructs non-Windows users on pre-commit setup.

---

## HIB-043 — Review gate model diversification guidance

**Date**: 2026-05-31
**Source**: Multi-agent monoculture research / gap analysis
**Pillar**: T1-G / Gate trust & calibration
**Status**: ✅ Complete (v1.4.5) — Model diversification section added to configuration.md.

**Problem**: The adversarial gate correctly separates writer context from reviewer context, but same-model review creates correlated blind spots. A hallucination the writing agent produces may not be caught by a reviewer using identical weights and priors — both models share the same training-time failure modes and are susceptible to the same class of coherent-but-wrong reasoning. This is confirmed by multi-agent monoculture research: diversity of model family (not just model instance) is required to achieve genuinely independent review.

**Suggested changes**:
1. Add a note to `docs/configuration.md` under the `model_routing:` section recommending that `review_provider` and `review_model` be configured to a *different model family* than the primary writing agent where possible (e.g. writing on Claude Code → review gate on OpenAI or Ollama; writing on GPT-4 → review gate on Anthropic or Ollama).
2. Add the same note to `review_context_universal.md` in the gate system prompt preamble so it surfaces during gate configuration.
3. Document explicitly: same-model review is still better than no gate (catches structural violations, format errors, and many semantic errors even with correlated priors), but the residual risk is correlated blind spots that only cross-family review eliminates.
4. No code change required — documentation and configuration guidance only.

---

## HIB-044 — T1-E-01 sandboxing requirement for Tool ABC subclasses

**Date**: 2026-05-31
**Source**: Gap analysis — T1-E-01 pre-implementation design requirement
**Pillar**: Security / Tool execution safety
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

**Problem**: T1-E-01 (Formalise skills as Tool ABC subclasses with `run()` methods) enables code-as-skill execution. Without an explicit sandboxing requirement in the `Tool` base class contract, concrete subclasses may inadvertently access unrestricted filesystem paths, make undeclared network calls, or use dangerous builtins (`exec`, `eval`, `__import__`). The existing T1-G-05 (restricted globals for `eval_runner.py`) covers evaluation cases; T1-E-01 needs the same treatment applied to the `Tool` ABC `run()` contract itself.

**Suggested changes**:
1. Before any concrete `Tool` subclass is implemented, add an explicit sandboxing contract to the `Tool` base class design:
   - **Restricted builtins**: `run()` methods must not use `exec`, `eval`, `__import__`, `open()` outside the declared project path, or `subprocess` without a declared `requires_subprocess: bool = True` in `schema()`.
   - **Filesystem boundary**: write access restricted to within `project_root` (resolved at instantiation from config). Reads outside project root require `requires_external_read: bool = True` in `schema()`.
   - **Network isolation**: no network calls unless `requires_network: bool = True` declared in `schema()`. Undeclared network access raises `ToolSandboxViolation`.
2. Add `ToolSandboxViolation` exception to the base class.
3. Add a static analysis check to `check_skills_hygiene.py` that scans `Tool` subclasses for undeclared dangerous builtins at commit time.
4. Update the T1-E-01 backlog description to reference this constraint.

**Note**: This constraint is a design gate for T1-E-01, not a separate implementation sprint. It should be captured in the `Tool` ABC interface document before the first concrete subclass is written.

---

## HIB-045 — False-positive rate as a proactive harness health metric

**Date**: 2026-05-31
**Source**: Gap analysis — reactive vs proactive false-positive handling; Google rule-disablement research
**Pillar**: T1-G / Gate trust & calibration; T1-D-03 / Dream phase
**Status**: ✅ Migrated (FRAMEWORK_BACKLOG.md)

**Problem**: `harness_health.py` tracks verdict distributions but does not compute per-capability false-positive rate as a trend metric. The current false-positive handling (T1-L-10 eval regression, T1-G-06 rebuttal protocol) is entirely reactive — a developer must file a rebuttal before the calibration issue is surfaced. Research finding: false-positive rate is the primary predictor of governance tool abandonment. Google's internal tooling uses >10% false-positive rate as the threshold for automatic rule disablement review. The harness has no equivalent proactive signal.

**Suggested changes**:
1. For each capability (BRANCH_ISOLATION, ANTI_PATTERNS, CLEAN_ARCH, etc.), compute:
   ```
   bypass_rate = structured_bypasses_last_30d / (FAIL_verdicts_last_30d + structured_bypasses_last_30d)
   ```
   where `structured_bypasses_last_30d` counts `SKIP_REASON` events and accepted rebuttals for that capability from `harness_events.jsonl` and `.ai-review-log.jsonl`.
2. If `bypass_rate > 0.15` for any capability, emit a `DEGRADING` signal in `harness_health.py` output.
3. Automatically generate a dream phase proposal flagging the calibration issue — rather than waiting for a developer to file a rebuttal. Proposal format: same as existing `__open.md` proposals but with `action: calibrate_capability`, `capability: BRANCH_ISOLATION`, `evidence: bypass_rate=0.22 over 30d (11 bypasses / 50 FAILs)`.
4. Add `bypass_rate` to the per-capability health report table in `harness_health.py` output regardless of whether it crosses the threshold — visibility is the first step.

**Rationale**: Closes the gap between reactive false-positive handling (T1-L-10, T1-G-06) and proactive calibration monitoring. The dream phase proposal mechanism (T1-D-03) is already in place — this HIB wires a new trigger signal into it.

---

## HIB-046 — validate.py pre-commit PATH check produces false positive on Windows when pre-commit is installed via Poetry virtual environment

**Date**: 2026-06-05
**Source**: Operational failure on Windows
**Pillar**: Bootstrap / validation accuracy
**Status**: ✅ Complete (v1.4.7) — Added sys.executable fallback check to validate_tools() in validate.py.

The hook wiring check (✅ Pre-commit Git Hook Layout) correctly confirms hooks are present and wired. The CLI tool check fires independently and cannot find `pre-commit` in the system PATH even when it's available in the Poetry venv. Fix: check for `pre-commit` using subprocess with the Poetry venv's Python rather than `shutil.which()` against system PATH.

---

## Bug Items

| ID | Bug | Description | Effort | Status |
|---|---|---|---|---|
|----|-----|-------------|--------|--------|
| BUG-14 | **governance.md missing P-14 and P-15** | Add rationale entries for P-14 (repository identity guard) and P-15 (CI branch commits) to governance.md §3. Consistency gap between AGENTS.md (15 prohibitions) and governance.md (13 documented). P-14 rationale: agents operating across multiple terminal windows or IDE instances may execute git operations against the wrong repository; check_repo.py prevents this. P-15 rationale: direct commits to deployment/devops branches bypass the PR review process and can trigger unintended deployments. Documentation only — no code changes. | Low | ✅ (v1.3.1) |
| BUG-15 | **check_halt.py missing pre-commit hook** | HALT is currently checked at session startup by convention only. With T1-I-07 wiring now active (ai_review.py increments session token counter after each review call), a realistic path exists where a token budget HALT file is written mid-session and the next commit proceeds without checking it. Add check_halt.py as a pre-commit hook stage in .pre-commit-config.yaml.template so HALT is enforced at every commit boundary, not just at session startup. One hook entry in the template plus a corresponding test in tests/test_validate.py verifying the hook entry is present. | Low | ✅ (v1.3.1) |
| BUG-16 | **session_ledger.jsonl harness_version hardcoded "2.0"** | In init_session.py, the harness_version field written to session_ledger.jsonl is hardcoded as "2.0" regardless of the actual installed framework version. The T1-B-02 forensic rationale ("which harness version was running when this incident happened") is defeated. Fix: read the version from harness_version.txt at session close time (same file that upgrade.py maintains). One-line change in init_session.py. Add a test asserting the written version matches harness_version.txt content. | Low | ✅ (v1.3.1) |
| BUG-17 | **select_bdd_gate.py non-functional — skill_bdd_map.json missing** | select_bdd_gate.py requires .agent/config/skill_bdd_map.json but this file does not exist in the framework source. The script fails immediately on any invocation with "Error: skill_bdd_map.json missing." This has been broken since v1.0.0 with no visibility because the script is called by agent convention, not automation. Two-part fix: (1) Create a default skill_bdd_map.json in bootstrap/templates/ mapping the 22 universal skills to sensible default BDD tag groups, copied to .agent/config/ by install.py. (2) Add a validate.py WARN check: if .agent/config/skill_bdd_map.json is absent, emit WARN "BDD gate non-functional: skill_bdd_map.json missing from .agent/config/". The validate.py check is the minimum — it surfaces the problem immediately on fresh installs without requiring the full skill_bdd_map.json work. | Low | ✅ (v1.3.1) |
| BUG-18 | **wiki_compile.py uses review_model tier instead of budget_model** | wiki_compile.py calls the LLM provider using the review_model routing key (intended for the full adversarial review gate) rather than budget_model. Wiki compilation runs weekly on potentially 13+ domains and should use the cheap model (Ollama/Haiku/budget tier) not the expensive review tier. T1-D-05 (model tiering configuration) is marked ✅ but this specific routing gap was not caught at delivery time. Fix: replace the review_model key with budget_model in wiki_compile.py's provider call. Single-line change. Verify the budget provider config key exists in config.yaml.template (it should from T1-D-05). | Low | ✅ (v1.3.1) |

---

### Rebuttal Protocol — Gate Governance Gaps (identified 2026-06-06)
*Source: GymBase SPEC-124 incident — 5 rebuttal attempts, forensic
analysis by Peter Long / Claude, 2026-06-06*

| ID | Issue | Description | Effort | Status |
|----|-------|-------------|--------|--------|
| HIB-047 | **Gate findings not surfaced to developer at rebuttal time** | At gate-fail time, the original finding text is stored in `.ai-review-log.jsonl` but never displayed when `--rebuttal` is invoked. The developer writes evidence blind against opaque FID labels with no inherent meaning. In the SPEC-124 incident this caused the first three rebuttal attempts to target the wrong concerns entirely. Fix: (1) Write findings to `.agent/state/gate_findings_{session_id}.json` at gate-fail time with full finding text, severity, location, and remediation suggestion; (2) When `--rebuttal` is invoked, display the original findings from that file before showing the rebuttal template; (3) Pre-populate `gate_rebuttal.json` with the frozen finding text in a `_finding_text` read-only comment field so the developer has the original concern visible while writing evidence. This is the single highest-leverage fix — most downstream rebuttal failures dissolve once the developer can see what the gate actually found. | High | ⬜ v1.3.3 |
| HIB-048 | **Gate findings non-deterministic across rebuttal runs** | The gate re-evaluates the diff on each rebuttal run. LLM temperature >0 means finding descriptions shift between runs under the same FID labels. In the SPEC-124 incident: FID-1 was "mass assignment" on Run 1 and "authorization gap on notes endpoint" on Run 3. Same diff hash, different findings. The developer wrote correct evidence for the Run 3 findings and was blocked by the limiter that did not account for the shift. Fix: Freeze finding text at first evaluation in `.agent/state/gate_findings_{session_id}.json`. Rebuttal evaluation assesses developer evidence against the frozen finding text only — the gate does not re-read the diff during rebuttal evaluation. For REMEDIATED type (HIB-049), the gate checks the current diff to confirm the concern is gone, but the frozen text remains the reference. Dependency: HIB-047 (the same `gate_findings` file serves both fixes). | High | ⬜ v1.3.3 |
| HIB-049 | **Missing REMEDIATED rebuttal_type causes false positive dataset pollution** | The `rebuttal_type` enum (`FALSE_POSITIVE`, `SPEC_REQUIREMENT`, `ARCHITECTURAL_INVARIANT`, `OUT_OF_SCOPE`) has no type for "true positive — fixed". When a developer fixes a real bug they must use `FALSE_POSITIVE` with evidence that the code changed. This is semantically wrong and pollutes dream phase calibration data — a REMEDIATED finding should not reduce gate sensitivity on that pattern, but recording it as `FALSE_POSITIVE` does exactly that. In the SPEC-124 incident the developer was forced to call a genuine security fix a false positive. Fix: Add `REMEDIATED` as a valid `rebuttal_type`. Evidence describes what was fixed and where (file, line, nature of change). Gate re-evaluates the current diff against the frozen finding (HIB-048) to confirm the concern is gone. `spec_reference` not required for REMEDIATED type. Update `gate_rebuttal_template.json` with REMEDIATED as an option with a worked example. Update `AGENTS.md §8.6` worked examples to show REMEDIATED vs FALSE_POSITIVE distinction — a REMEDIATED filing means "the gate was right; I fixed it"; a FALSE_POSITIVE filing means "the gate was wrong; here is why". | High | ⬜ v1.3.3 |
| HIB-050 | **Rebuttal limiter misfires when gate changes finding descriptions between runs** | The limiter blocks re-submission after one rejection per `(finding_id, diff_hash)`. This misfired in the SPEC-124 incident because the gate produced different finding descriptions on different runs under the same FID label. The developer wrote new evidence for the revised finding and was still blocked, forcing unnecessary code changes to generate a new diff hash. Fix: Track `(finding_id, diff_hash, finding_description_hash)` where `finding_description_hash` is a hash of the frozen finding text stored at first evaluation. Limiter fires only when all three match a prior rejected attempt. When the finding description changes the limiter permits a new rebuttal. Note: this fix becomes redundant once HIB-048 (finding freeze) is implemented — frozen findings make `finding_description_hash` stable. HIB-050 is a defensive fallback if HIB-048 ships later. Dependency: HIB-047 (gate_findings file), HIB-048 (frozen finding text). | Medium | ⬜ v1.3.3 |
| HIB-051 | **ARCHITECTURAL_INVARIANT silently requires spec_reference but template and error timing mislead the developer** | `gate_rebuttal.json` template writes `"spec_reference": ""` for all rebuttal types. `ARCHITECTURAL_INVARIANT` requires a non-empty `spec_reference` but this is validated only at submission time after the developer has written the full rebuttal. The Pydantic error is clear but arrives too late. Fix: (1) Update `gate_rebuttal_template.json` — replace the empty string with an inline `_comment_spec_reference` field reading `"REQUIRED for ARCHITECTURAL_INVARIANT: path to ADR, review_context rule ID, or decisions_log entry. Example: review_context_project.md [RULE:BRANCH-ISOLATION]"`; (2) Add early validation in `--rebuttal` mode that checks `rebuttal_type`/`spec_reference` combinations before any LLM call — if type is `ARCHITECTURAL_INVARIANT` and `spec_reference` is empty or still the default placeholder, fail immediately with a message naming exactly what is needed and giving an example path. | Low | ⬜ v1.3.3 |

> **GymBase Test Design Note (2026-06-06)**: The `_get_db_per_request` test fixture unconditionally commits after every request including exception paths. Production `get_db()` only closes the session without committing. Security-path side effects (audit log writes in `log_unauthorized_access`) pass in tests but are silently dropped in production. The gate caught this (FID-2, Run 1); the test suite did not. Recommendation: Add a separate test fixture variant that uses close-without-commit semantics for security-path tests to catch this class of bug before the gate sees it. Track in GymBase technical debt backlog, not here.

---

## HIB-052 — session_id: "unknown" clustering undercounts dream phase appearance_rate

**Date**: 2026-06-12
**Source**: Antigravity / Peter (v1.3.4 release verification)
**Pillar**: T1-D-03 / Dream Phase calibration
**Status**: ✅ Complete (v1.4.0)

Historical FAIL entries from sessions where `session.json` was absent at write time write `session_id: "unknown"` to `.ai-review-log.jsonl`. At dream phase distillation time (`distill_dream.py`), this causes all such historic failures to cluster into a single phantom `"unknown"` session, regardless of how many actual developer sessions they represent.
This systematically undercounts pattern spread (`appearance_rate` = `1 / total_sessions_30d`), preventing dominant patterns (like `INTENT_MISMATCH` in older datasets) from ever crossing the default 20% threshold.

**Suggested changes**:
1. Exclude `unknown` session IDs from the `appearance_rate` calculation denominator and numerator, or treat each `unknown` session ID log entry as a separate unique session for the purpose of the frequency analysis.
2. Alternatively, parse the timestamp of `unknown` sessions to group them into separate 1-hour/2-hour windows as an approximation of distinct sessions.

---

## HIB-056 — T1-I-05 status-marker drift (⬜ vs treated-as-delivered)

**Date**: 2026-06-22
**Source**: Claude (incidental finding while logging T1-D-07)
**Pillar**: Backlog integrity / marker drift
**Status**: ✅ Complete (2026-06-22) — Verified that contradiction checking is implemented in `distill_dream.py`; updated T1-I-05 status to ✅ (integrated into T1-D-03) across planning docs.

`FRAMEWORK_BACKLOG.md` marks **T1-I-05 (Memory contradiction detector) as ⬜ undelivered**, but two other places treat its functionality as already shipped: T1-I-05a's dependency line cites "T1-I-05 ✅ (contradiction detection)", and T1-D-03's description states the contradiction check (T1-I-05) "runs before writing each proposal" — and that contradiction-card logic is in fact present in `distill_dream.py` (writes `{skill}__{pattern_key}__contradiction.md`). So the capability appears delivered-as-integrated while its standalone status marker still reads ⬜. Surfaced while citing T1-I-05 as a dependency of the new T1-D-07; cited carefully there rather than stamped ✅, pending resolution here.

This is the same marker-drift class that v1.4.2's backlog-repair pass addressed (HIB-055 vocabulary filtering; the T1-L-13/T1-G-12 marker reconciliation). Left unresolved, it sits until the next capability-inventory-style audit rediscovers it independently.

**Suggested change**: Confirm by inspection whether T1-I-05's contradiction detector is fully delivered inside `distill_dream.py`. If yes, mark T1-I-05 **✅ (integrated into T1-D-03)** in `FRAMEWORK_BACKLOG.md` — consistent with how T1-I-05a and T1-D-03 already reference it — and reconcile any `CAPABILITY_INVENTORY.md` reference. If partial, downgrade the T1-I-05a citation from ✅ to match. Either way, the three references should agree. Low effort; pure status reconciliation, no code.

---

## HIB-057 — ReviewProvider missing call_llm method causing AttributeError

**Date**: 2026-07-02
**Source**: GymBase SPEC-127 verification run / check_spec.py
**Pillar**: Stability / Framework
**Status**: ✅ Complete (v1.4.7)

**Symptom**: `AttributeError: 'OllamaProvider' object has no attribute 'call_llm'` when running Pass 2 of the spec gate (`check_spec.py`).

**Root Cause**: `check_spec.py` invokes `provider.call_llm(...)` to run quality checks against specifications, but `call_llm` was never defined on the base `ReviewProvider` class or any of its subclasses (`OllamaProvider`, `AnthropicProvider`, `OpenAIProvider`) in `src/scripts/providers.py`.

**Suggested change / Fix**: Add a wrapper method `call_llm` to the base `ReviewProvider` class that routes requests to the existing `raw_completion` method and maps `self.last_token_usage` for token counting. This ensures parity with `check_spec.py`'s expectations across all LLM-backed providers. Note that this is a framework-wide fix, not a one-off patch, affecting any project running the spec gate under an LLM provider.

---

## HIB-058 — check_traceability.py does not verify Gherkin scenario coverage

**Date**: 2026-07-04
**Source**: GymBase, SPEC-127 pre-Phase-2 audit (external trigger, not a framework regression — same provenance pattern as HIB-057)
**Pillar**: Governance / Traceability
**Status**: 📅 Backlog — design exists (T1-L-18), not yet built

**Symptom**: `check_traceability.py` verifies only that a commit message references an approved SPEC-ID and that the spec file exists with `Status: APPROVED`. It does not check whether Gherkin scenarios in the spec's acceptance-criteria section have corresponding test implementations.

**Evidence**: In GymBase, the `cancelled_timely` refund scenario was fully specified in SPEC-127 §4 (signed off 2026-07-02). Multiple commits implementing partial cancellation logic all passed the traceability gate by referencing SPEC-127 in the commit message, but none implemented the refund path — no ledger entry, no balance change, no `is_paid` check. The gate never fired on this gap. It was found only by a direct code audit prior to Phase 2 architecture design, not by any automated check.

**Root cause**: The gate is a commit-message-to-spec-ID linker, not a scenario-to-implementation coverage checker. These are different concerns that were never separated in the gate's design. A requirement can satisfy "this commit references an approved spec" while leaving an entire acceptance scenario unimplemented, because nothing maps individual `Gherkin Scenario:` blocks to individual tasks/tests/commits.

**Design status**: This is not a new problem needing new design — a design already exists. See **T1-L-18** in `FRAMEWORK_BACKLOG.md` (formally assigned 2026-07-04, promoted from draft rev-5 content reasoned through five review rounds in the 2026-06-21 session).

**T1-L-18 core mechanism**: A completeness check added to `check_spec.py` Pass 2 — advisory by default (prose-based, flags normative "shall/must" statements with no corresponding testable acceptance criterion), blocking (FAIL) only for risk-tagged specs (`[HIGH_RISK_SCHEMA_CHANGE]`), gated on a new stable acceptance-criterion ID primitive scoped only to risk-tagged specs (to keep the authoring cost proportionate). Explicitly not: a new HARD STOP gate layer, runtime/PreToolUse interception (closed by design per README's "not a runtime guard" philosophy), or a universal per-spec ID requirement (rejected as a blanket authoring tax).

**Known limitation already logged in T1-L-18**: the risk tier is gated on a self-applied tag the drafting agent writes into its own spec — a structural backstop via `ai_review.py`'s `HIGH_RISK_PATTERNS` classifier exists for retrospective cross-checking, but isn't wired in yet; deliberately deferred to the dream phase to observe whether it's a real recurring pattern before building it.

**Proposed fix** (pending confirmation this matches T1-L-18, rather than being filed as a separate duplicate effort): a `check_scenario_coverage.py` gate, or an extension to `check_spec.py`, that for any SPEC ID referenced in a commit, enumerates `Gherkin Scenario:` blocks in the spec and verifies a named test function/file exists for each — following T1-L-18's severity-tiered design (advisory by default, blocking only for risk-tagged specs).

**Impact classification**: process gap, not a data integrity gap. No member data was corrupted in the GymBase instance — the missing refund implementation was caught and documented before the affected UI (member self-service cancellation) shipped. Classified high-priority-not-urgent in GymBase's own SPEC-127 tracking; the harness-level fix itself has no urgency deadline but represents a real, evidenced gap now that it's been triggered once in production-adjacent code.

**Cross-reference**: This HIB entry and T1-L-18 describe the same gap; do not develop them as independent efforts. Treat this HIB entry as the supporting evidence case for T1-L-18.



---

## HIB-062 — Large diffs failing open (DIFF_TOO_LARGE_FAILOPEN) is a critical gate design gap

**Date**: 2026-07-08
**Source**: Gate design gap
**Pillar**: T1-G-01 hardening
**Status**: ⬜ Not Started

Large diffs failing open (`DIFF_TOO_LARGE_FAILOPEN`) allows high-risk (large) commits to skip AI review and bypass governance entirely. This is a critical design gap.
Proof cases from today's review log:
- `GATE_SKIPPED / DIFF_TOO_LARGE_FAILOPEN`, session_id: "unknown", commit missing AI-Assisted trailers.
- (Additional entries cited by the operator in the review log where large diffs silently bypassed).
This fail-open behavior is in direct conflict with the T1-L-08 fail-closed precedent. The gate must enforce a fail-closed response for oversized diffs, or require explicit chunking and gated review.
