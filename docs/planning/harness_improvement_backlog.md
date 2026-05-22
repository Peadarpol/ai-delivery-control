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
**Status**: 📅 Backlog — resolve with T1-C-01

`circuit_breaker.py` has no automatic enforcement — voluntary only. Gate exists in `governance.md` (line 119) as a "SHOULD run before committing" manual agent step but is not wired into the session or commit lifecycle. An agent that skips it faces no consequence from the harness. Pre-commit is the wrong hook stage (circuit breaker checks session-level limits, not commit-level limits).

**Suggested change**: Resolve as part of T1-C-01 (passive session lifecycle hooks) — check limits at session start, record metrics at session close. Not a standalone item. Correct wiring: check at session start in `init_session.py`; record final metrics at session close via Stop hook.

---

## HIB-003 — Fine-tuning from dream phase trajectory data (long-horizon)

**Date**: 2026-05-18
**Source**: Hermes comparison
**Pillar**: P7
**Status**: 📅 Long-horizon — not actionable until dream phase is operational

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
**Status**: 📅 Backlog — design spec captured

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
**Status**: 📅 Backlog — BUG-05

ADR domain `branch_isolation` detected in `context_snapshot` but capability `BRANCH_ISOLATION` not activated — routing logic not mapping domain names to capability names. Check case/naming convention in `RouteDecision` build logic.

---

## HIB-013 — Gate calibration too aggressive — all verdicts are FAIL

**Date**: 2026-05-22
**Source**: Gate calibration
**Pillar**: T1-G-01 calibration
**Status**: 📅 Backlog — BUG-06

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
**Status**: 📅 Backlog — BUG-01 (CRITICAL)

AI review gate configured at `commit-msg` stage but `commit-msg` hook not installed = gate never fires. Entire RFC-003 session ran without gate coverage. Fix: `bootstrap/install.py` must run `pre-commit install --hook-type commit-msg` in addition to `pre-commit install`. Already partially in spec — verify it's executed.

---

## HIB-016 — validate.py does not check for commit-msg hook

**Date**: 2026-05-22
**Source**: Validate gap
**Pillar**: T1-A-03 fix
**Status**: 📅 Backlog — BUG-02

`bootstrap/validate.py` checks for `pre-commit` and `pre-push` hooks but not `commit-msg` hook. Gate was absent for entire session and validation reported ✅. Add `commit-msg` to the hook layout check.

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
**Status**: 📅 Backlog — BUG-03

Gate reads `git diff --staged` at `commit-msg` stage. For `git commit --amend`, staged diff is empty → pre-flight fires → PASS in 1.57s → no real review. Fix: at `commit-msg` stage, read `git show HEAD` (the commit being created) not `git diff --staged`.

---

## HIB-019 — PASS and PASS_FAST verdicts not written to audit log

**Date**: 2026-05-22
**Source**: PASS not logged
**Pillar**: T1-G-03 fix
**Status**: 📅 Backlog — BUG-04

PASS and PASS_FAST verdicts not written to `.ai-review-log.jsonl`. Only FAIL verdicts visible. Gate history is incomplete — only failures are recorded. Fix logging path for all verdict types.

---

## HIB-020 — Gate stage tradeoff: commit-msg vs pre-commit vs dual-stage

**Date**: 2026-05-22
**Source**: Gate stage tradeoff
**Pillar**: T1-G-01 design
**Status**: 📅 Design consideration

`commit-msg` stage is correct for intent alignment but creates empty-diff problem for amends and rebases. Consider dual-stage: `pre-commit` for diff review, `commit-msg` for message format check only.