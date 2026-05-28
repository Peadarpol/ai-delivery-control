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
**Status**: 📅 Backlog — T1-F series

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
**Status**: 📅 Backlog — T1-B series

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
**Status**: 📅 Backlog — T1-B series

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
**Status**: 📅 Backlog — T1-C series

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
**Status**: 📅 Backlog — BUG-related

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
**Status**: 📅 Backlog — BUG-related

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
**Status**: 📅 Design consideration

`commit-msg` stage is correct for intent alignment but creates empty-diff problem for amends and rebases. Consider dual-stage: `pre-commit` for diff review, `commit-msg` for message format check only.

---

## HIB-021 — Commit msg not read at commit-msg stage (BUG-09)

**Date**: 2026-05-23
**Source**: Commit msg
**Pillar**: T1-G-01 fix
**Status**: 📅 Backlog — BUG-09

When the gate runs at the `commit-msg` stage, it fails to read the commit message and reports "no commit message provided" even when a message exists. The current implementation looks for the commit message in a hardcoded path (e.g., `.ai-review-temp.md`), but Git actually creates the temporary commit message at a path under `.git/COMMIT_EDITMSG` and passes that path as an argument to the `commit-msg` hook.

**Suggested change**: Update the gate script to read the commit message from the file path provided via CLI argument (`sys.argv[1]`), which Git passes when the hook is invoked.

---

## HIB-022 — Automatic framework version bump

**Date**: 2026-05-23
**Source**: Framework sync
**Pillar**: T1-A-02 fix
**Status**: 📅 Backlog

Framework sync must automatically bump `framework.version` in `config.yaml` and `UNIVERSAL_CONTEXT.md` to the new version. Currently, this process is manual, making it easy to forget or get wrong.

**Suggested change**: Update `upgrade.py` or framework compile processes to automatically detect the new framework version and update `framework.version` in `config.yaml` and `UNIVERSAL_CONTEXT.md` accordingly.

---

## HIB-023 — ADR domain validation in environment checks

**Date**: 2026-05-23
**Source**: ADR Domains
**Pillar**: T1-A-03 enhancement
**Status**: 📅 Backlog

The gate could silently warn or fail if the ADR domain names defined in `adr_capability_mappings` do not correspond to actual ADR files in `docs/architecture/adr/`. Currently, there is no validation for this mapping alignment.

**Suggested change**: Add a check to `validate.py` and `bootstrap/validate.py` to ensure that all domain names referenced in `adr_capability_mappings` correspond to real ADR files in `docs/architecture/adr/`, producing a warning if a mismatch or missing file is detected.



---

## HIB-024 — Session memory treated as facts not claims

**Date**: 2026-05-24
**Source**: Shokunin v4.2.3 verify_file_path pattern
**Pillar**: T1-I-04 / Memory
**Status**: 📅 Quick win — no new dependencies

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
**Status**: 📅 Quick win — documentation only

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
**Status**: 📅 Backlog — T1-C-01 scope extension

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
**Status**: 📅 Backlog — v1.3.0 T1-B series

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
**Status**: 📅 Backlog — documentation only (AGENTS.md update)

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
**Status**: 📅 Backlog — schema extension

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
**Status**: 📅 Backlog — documentation only (AGENTS.md + workflow files)

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