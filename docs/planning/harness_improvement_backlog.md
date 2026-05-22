# Harness Improvement Backlog

| Date | Observed by | Observation | Suggested change | Pillar | Status |
|------|-------------|-------------|-----------------|--------|--------|
| 2026-05-16 | Antigravity | `scheduler.shutdown()` is called with `wait=False` in production to avoid blocking. If the event loop closes too fast, it raises a `RuntimeError` (previously swallowed, now surfaced as `warning`). This leaves background tasks in a zombie state (`asyncio_0` leak). | Monitor production logs for "SaaS: Scheduler shutdown RuntimeError". If frequent, reconsider `wait=True` in production or refine the shutdown sequence in `startup.py`. | Stability / Lifecycle | ✅ Backlog / Canary 2026-05-16 |
| 2026-05-18 | Claude (T1-I-00b diagnostic) | `circuit_breaker.py` has no automatic enforcement — voluntary only. Gate exists in `governance.md` (line 119) as a "SHOULD run before committing" manual agent step but is not wired into the session or commit lifecycle. An agent that skips it faces no consequence from the harness. Pre-commit is the wrong hook stage (circuit breaker checks session-level limits, not commit-level limits). Correct wiring: check at session start in `init_session.py`; record final metrics at session close via Stop hook. | Resolve as part of T1-C-01 (passive session lifecycle hooks) — check limits at session start, record metrics at session close. Not a standalone item. | Governance / Enforcement | 📅 Backlog — resolve with T1-C-01 |
| 2026-05-18 | Hermes comparison | Long-horizon: once T1-D-03 (dream phase) produces 6+ months  |
|            |                   | of labelled session data, evaluate exporting harness          |
|            |                   | trajectories in ShareGPT format for fine-tuning a            |
|            |                   | codebase-specialist model. Hermes calls this "batch           |
|            |                   | trajectory generation." Not actionable until dream phase      |
|            |                   | is operational and producing quality labelled outcomes.       | P7 |
| 2026-05-21 | Claude (security audit, PR #126 CI) | pip-audit suppression flags exist in two places (`.pre-commit-config.yaml` AND `.github/workflows/ci.yml`). Discovered when CI failed on PR #126 after local pre-commit was fixed — the `--ignore-vuln` flags were not mirrored to the CI step. | Consider extracting shared args to a `pip-audit.toml` config if the suppression list grows beyond 5 entries, making the single source of truth unambiguous. For now, any suppression added to one file must be added to the other in the same commit. | Security / CI Sync | P6 |
| 2026-05-21 | T1-F README | README lacks introductory pain point mapping for developers new to agentic workflows. | Add "What it prevents" section to README.md detailing 4 concrete pain points: wrong repo commits, ungoverned AI changes, context loss between sessions, stale architectural rules. Each maps to a specific framework capability. | Documentation | 📅 Backlog — T1-F series |
| 2026-05-21 | T1-A-upgrade | bootstrap/upgrade.py — Design specification:        |
|            |              |                                                      |
|            |              | PURPOSE: Safely update an existing AI Delivery       |
|            |              | Control installation to a newer framework version    |
|            |              | without overwriting developer customisations.        |
|            |              |                                                      |
|            |              | FILE CLASSIFICATION (see bootstrap/manifest.json):   |
|            |              | - framework_owned: always overwrite on upgrade       |
|            |              |   (.agent/scripts/, .agent/workflows/,               |
|            |              |    .agent/skills/, .agent/governance.md,             |
|            |              |    .agent/AGENTS.md, src/scripts/ai_review.py)       |
|            |              | - project_owned: never touch                         |
|            |              |   (.agent/config.yaml, skill_ownership.yaml,         |
|            |              |    review_context_project.md, CLAUDE.md,             |
|            |              |    GEMINI.md, .cursorrules)                          |
|            |              | - migrate_on_upgrade: additive changes only          |
|            |              |   (.agent/config.yaml — new fields added,            |
|            |              |    existing values preserved)                        |
|            |              |                                                      |
|            |              | CONFLICT DETECTION:                                  |
|            |              | Before overwriting any framework_owned file,         |
|            |              | compare SHA-256 of installed file against            |
|            |              | bootstrap/checksums/{version}.json baseline.         |
|            |              | If mismatch: developer has customised the file.      |
|            |              | Preserve developer version, save framework           |
|            |              | version as {filename}.framework-v{version}.          |
|            |              | Surface in the pre-upgrade report.                   |
|            |              |                                                      |
|            |              | SKILL/WORKFLOW CONFLICTS:                            |
|            |              | If developer has a skill or workflow with same       |
|            |              | filename as a framework skill/workflow:              |
|            |              | - Preserve developer version as active               |
|            |              | - Save framework version as                          |
|            |              |   {filename}.framework-v{version}                    |
|            |              | - Print advisory to developer                        |
|            |              |                                                      |
|            |              | PRE-OPERATION REPORT (required before any writes):   |
|            |              | Always print a categorised summary showing:          |
|            |              | - OVERWRITE: framework files to be replaced          |
|            |              | - SKIP: project-owned files being preserved          |
|            |              | - MIGRATE: config fields being added                 |
|            |              | - CONFLICTS: files needing manual resolution         |
|            |              | - NEW: files being added for first time              |
|            |              | Then prompt: "Proceed? [y/N]"                        |
|            |              |                                                      |
|            |              | CLI FLAGS:                                           |
|            |              | --dry-run: print report, make no changes             |
|            |              | --force: skip confirmation prompt (CI use)           |
|            |              | --diff: show line-level diff for CONFLICT files      |
|            |              |                                                      |
|            |              | FRESH INSTALL BEHAVIOUR:                             |
|            |              | Same pre-operation report applies. If .agent/,       |
|            |              | CLAUDE.md, or existing skills are detected,          |
|            |              | inventory them and apply the same conflict           |
|            |              | detection logic before writing anything.             |
|            |              |                                                      |
|            |              | MIGRATIONS:                                          |
|            |              | Version transition scripts live in                   |
|            |              | bootstrap/migrations/{from}_to_{to}.py               |
|            |              | Each reads existing config, adds new fields          |
|            |              | with defaults, preserves existing values.            |
|            |              | Upgrade script chains migrations from                |
|            |              | project's framework.version to current.              |
|            |              | Pattern identical to Alembic upgrade chain.          |
|            |              | | T1-A series |
| 2026-05-21 | T1-F skill discovery | Skill discovery guidance — three-part design:        |
|            |                      |                                                      |
|            |                      | 1. POST-INSTALL OUTPUT (install.py): After           |
|            |                      |    successful installation, print skill discovery    |
|            |                      |    prompt pointing to agentskills.io,                |
|            |                      |    github.com/topics/agent-skills, and               |
|            |                      |    docs/skills.md (curated list by stack).           |
|            |                      |    Show regardless of whether a stack pack was       |
|            |                      |    matched — ecosystem awareness is always useful.   |
|            |                      |                                                      |
|            |                      | 2. DREAM PHASE EXTENSION (distill_dream.py):         |
|            |                      |    When a capability gap appears in 3+ sessions      |
|            |                      |    without a governing skill, generate a SKILL       |
|            |                      |    DISCOVERY PROPOSAL (not a skill diff) pointing    |
|            |                      |    to community sources before suggesting authoring  |
|            |                      |    from scratch. Include session count and date      |
|            |                      |    range as evidence. Pattern: same as __open.md     |
|            |                      |    proposals but with action: search, not apply.     |
|            |                      |                                                      |
|            |                      | 3. DOCS/SKILLS.MD (T1-F series): Curated list of    |
|            |                      |    recommended community skills by stack. Becomes    |
|            |                      |    anchor content on professional site alongside     |
|            |                      |    the framework itself.                             |
|            |                      |                                                      |
|            |                      | NOTE: No standing instruction in AGENTS.md —        |
|            |                      | mid-session suggestions are noise. Discovery is     |
|            |                      | surfaced at install time (once) and by the dream    |
|            |                      | phase (when evidence justifies it).                 |
|            |                      | | T1-F series |
| 2026-05-21 | T1-B governance | Restructure governance.md into Always/Ask First/Never  |
|            | restructure     | three-category framework (source: Osmani O'Reilly,     |
|            |                 | Feb 2026 — "curse of instructions" research).          |
|            |                 |                                                        |
|            |                 | RATIONALE: Research shows agents follow the first few  |
|            |                 | rules and overlook the rest when presented with a flat |
|            |                 | numbered list. A three-category decision framework     |
|            |                 | gives agents a mental model they can apply to novel    |
|            |                 | situations, not just a lookup table.                   |
|            |                 |                                                        |
|            |                 | IMPLEMENTATION:                                        |
|            |                 | Keep P-01 through P-14 as the canonical numbered       |
|            |                 | reference (immutable audit trail). Add a new           |
|            |                 | operational section above the prohibition table:       |
|            |                 |                                                        |
|            |                 | ALWAYS (do without asking):                            |
|            |                 | - Run check_repo.py before any git operation           |
|            |                 | - Run tests before commits                             |
|            |                 | - Write tests before implementation code               |
|            |                 | - Follow active workflow from start state              |
|            |                 |                                                        |
|            |                 | ASK FIRST (escalate to human):                         |
|            |                 | - Database schema changes                              |
|            |                 | - Adding or removing dependencies                      |
|            |                 | - Modifying auth, RBAC, or security code               |
|            |                 | - Commits touching more than 5 files                   |
|            |                 | - Anything that contradicts a rule in domain_rules.md  |
|            |                 |                                                        |
|            |                 | NEVER (absolute prohibition, maps to P-series):        |
|            |                 | - Merge to main/master without CI approval (P-01)      |
|            |                 | - Delete migration files (P-02)                        |
|            |                 | - Disable or weaken test assertions (P-03)             |
|            |                 | - Commit secrets or API keys (P-06)                    |
|            |                 | - Use git commit --no-verify (P-11)                    |
|            |                 | - [full P-series remains authoritative]                |
|            |                 |                                                        |
|            |                 | Update AGENTS.md and aisdlc-bootloader.md to reference |
|            |                 | the three-category framing as the operational layer.   |
|            |                 | | T1-B series |
| 2026-05-21 | T1-B skill      | Add "curse of instructions" principle to skill quality |
|            | authoring       | bar and T1-B-06 audit criteria (source: Osmani         |
|            | principle       | O'Reilly Feb 2026 — GitHub analysis of 2,500+ agent    |
|            |                 | config files; confirmed by GPT-4/Claude research).     |
|            |                 |                                                        |
|            |                 | RATIONALE: When agents are presented with many rules   |
|            |                 | simultaneously, they comply with the first few and     |
|            |                 | overlook the rest. A skill with 5 well-enforced rules  |
|            |                 | produces better agent behaviour than a skill with 20.  |
|            |                 | This is not a length concern — it is a rule-count      |
|            |                 | concern. A skill can be 80 lines and still be          |
|            |                 | over-specified if it contains 15 rules.                |
|            |                 |                                                        |
|            |                 | IMPLEMENTATION:                                        |
|            |                 | 1. Add to docs/customisation.md under skill authoring: |
|            |                 |    "Prefer 3-5 high-consequence rules over 10-20       |
|            |                 |    comprehensive ones. Agents follow the first few     |
|            |                 |    rules and overlook the rest (curse of instructions  |
|            |                 |    — Osmani, 2026). Every rule you add dilutes the     |
|            |                 |    ones above it."                                     |
|            |                 |                                                        |
|            |                 | 2. Add to docs/aisdlc-bootloader.md skill quality bar  |
|            |                 |    table: new row — Rule count | ≤5 high-consequence   |
|            |                 |    rules per skill | Why: curse of instructions         |
|            |                 |                                                        |
|            |                 | 3. Update T1-B-06 audit criteria to check rule count   |
|            |                 |    in addition to line count. A skill with >7 distinct |
|            |                 |    MUST/NEVER/ALWAYS rules is flagged AMBER regardless  |
|            |                 |    of line count. Add this check to verify_install.py  |
|            |                 |    skill metadata validation.                          |
|            |                 |                                                        |
|            |                 | 4. Update /create-skill workflow (T1-B-05) template    |
|            |                 |    to enforce the rule-count limit at authoring time,  |
|            |                 |    not just at audit time.                             |
|            |                 | | T1-B series |
