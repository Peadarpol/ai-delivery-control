> **Archived**: 2026-05-22. Unique content extracted to:
> - `docs/design/workflow-engine-design.md` (items H.1, H.2, H.4, H.7)
> - `FRAMEWORK_BACKLOG.md` cross-references (items H.3, H.9.2, H.9.5, K.1)

# RFC-002 — Scaffold V4: Outer Loop Delivery Orchestration

**Branch:** `feature/scaffold-v4-outer-loop`
**Status:** PROPOSED
**Author:** Peter Long
**Date:** 2026-05-10
**Related ADRs:** ADR-001 (Clean Architecture), ADR-002 (Branch Isolation), ADR-006 (Retrofit)
**Supersedes:** n/a
**Depends on:** V3 Sprint 1 COMPLETE ✅

---

## Implementation Status (as of 2026-05-18)

| RFC Phase | Harness Item | Status |
|-----------|-------------|--------|
| **Phase B** — Drift Detection | T1-I-04 (Staleness Detection) | ✅ Complete — PR #125, merged `devops` 2026-05-18 |
| **Phase L** — Dream Phase (partial) | T1-D-03 (Dream Phase Compiler) | 🔄 Fully specced — Chain B implementation queue |
| **Phase A** (A.4 — Session Lifecycle) | T1-C-01 (Outcome Inference + Post-commit Heartbeat) | 🔄 Fully specced — Chain B implementation queue |
| All other phases (C–K, M) | — | 📅 Deferred — Chain B takes priority |

**Current prioritisation**: Chain B (Self-Improvement Loop: `T1-D-00` → `T1-C-01` → `T1-I-03` → `T1-D-03`) is the active implementation target. RFC Phases D–G (outer loop delivery orchestration) are deferred until Chain B is complete and generating session outcome data. The Phase A.4 session lifecycle hook (T1-C-01) is being delivered as part of Chain B rather than as a standalone RFC phase.

**PostgreSQL gate**: The PostgreSQL stack migration (previously blocking all harness development) is complete and merged. This gate is lifted.

---

## 1. Problem Statement

The Agent Scaffold currently governs the **inner loop** of software delivery:

```
Roadmap item → Implement → Write tests → Gate chain → Commit → Pick up next item
```

It does **not** govern the **outer loop**:

```
Feature branch → Staging deploy → Deployment tests → UAT gate →
Merge to devops → Monitor CI/CD → Correct failures → UAT sign-off
```

The consequence is that the agent treats "commit passing the gate chain" as
"feature done." It does not know that a feature is undelivered until it has
passed staging, received UAT sign-off, and been merged to the devops branch.
This leaves the most consequential and error-prone steps of delivery as
entirely manual and untracked.

Additionally, three Tier 1 harness improvements from the V3 backlog remain
unimplemented: SQLite state persistence (PH-STATE-01–04), drift detection
(PD-01), and the eval pipeline (PE-01/PE-02). These are foundational to
multi-project harness operation and should be delivered in the same feature.

Additionally, the 17 workflow files in `.agent/workflows/` are markdown
prose documents the agent reads interpretively. There is no machine-readable
schema, no enforced step sequencing, and no way to configure workflows for
different users, teams, or task types without editing the source documents
directly. Someone who prefers a lighter-weight inner loop (e.g. skipping
the multi-persona audit, or reducing architecture options from 3 to 1) must
fork the workflow files. There is also no mechanism to assign the right
model to the right phase — a frontier model is used throughout even for
mechanical tasks (code generation from a confirmed spec, running migrations,
executing deployment commands) where an efficient or local model would
produce equivalent output at a fraction of the cost.

---

## 2. Scope

### 2.1 In scope

**Phase A — Harness State Persistence (Tier 1)**
Implement SQLite-backed state persistence so harness data is queryable,
cross-session durable, and filterable by project. Closes PH-STATE-01–04.

**Phase B — Drift Detection**
Implement dead code and stale skill detection. Closes PD-01.

**Phase C — Eval Pipeline**
Implement a skill evaluation standard and automated eval runner. Closes
PE-01 and PE-02.

**Phase D — Outer Loop Workflow Extension**
Extend the delivery workflow to cover the full lifecycle from feature branch
creation through UAT sign-off. New skills and workflow definitions.

**Phase E — Staging Deployment Automation**
Implement a deployment skill and executable deployment script with
pre-approved command set. Docker staging deployment becomes a gate, not a
manual step.

**Phase F — CI/CD Monitoring Loop**
Implement a delivery monitor that polls GitHub Actions, detects failures,
injects error context into the next session, and reports status.

**Phase G — UAT Gate Mechanism**
Implement the WAIT_UAT sentinel pattern, UAT checklist generator, and
release notes generator.

**Phase H — Workflow Configuration Engine**
Extract workflow step definitions from markdown prose into a machine-readable
YAML schema. Implement per-phase model assignment (frontier/efficient/local)
and a workflow runner that drives phase transitions from YAML config rather
than agent interpretation. Implement personal override support via a
gitignored `workflow.local.yaml`.

**Phase I — Harness Extraction & Portability**
Extract the harness framework into a standalone repository, separate from
Gym App. Implement bootstrap install and environment validation scripts.
Make architecture checks fully config-driven. Split `review_context.md`
into universal and project layers. Introduce stack-pack skill bundles and
template-driven tool supplement generation.

**Phase J — Environment Legibility**
Create `.agent/UNIVERSAL_CONTEXT.md` as the single canonical context source;
make `CLAUDE.md` and tool supplements thin shims. Add harness versioning and
changelog. Implement an onboarding workflow, skill deprecation `status` field,
and a `/create-skill` scaffold command.

**Phase K — Reliability Additions**
Implement a structured HITL approval queue (`pending_approvals.json`) for
escalation triggers that do not fit the UAT sentinel pattern. Add automated
GitHub issue creation when `harness_health.py` detects a CRITICAL condition.

**Phase L — Observability & Intelligence**
Implement dream phase distillation: a weekly batch script that reads
`session_ledger.md` entries, extracts recurring agent mistakes and escalation
patterns, and proposes additions to skill files as diffs for human approval.

**Phase M — Documentation & Shareability**
Complete the documentation suite required before any public sharing: getting-
started guide, configuration reference, customisation guide, refined AISDLC
bootloader, and harness README with the "8 interruptions → 3 checkpoints"
value proposition.

### 2.2 Out of scope

- Production deployment (remains human-initiated)
- Multi-agent concurrent session management (Tier 2)
- SQLite MCP server (Tier 2, PH-STATE-05)
- Distributed HALT sentinel (Tier 2, PH-STATE-06)

---

## 3. Architecture

### 3.1 Current state

```
.agent/
  skills/                    # Context Layer
  workflows/                 # Context Layer
  state/                     # Flat file state (markdown, jsonl, csv)
  config/
src/scripts/
  ai_review.py               # Adversarial reviewer
  harness_health.py          # Health report generator
  architecture_checks.py     # AST gate
```

### 3.2 Target state (additions only — nothing removed)

```
.agent/
  skills/
    delivery/                # NEW — outer loop skill library
      feature-branch.md      # Branch creation, naming, merge conventions
      staging-deployment.md  # Docker staging procedure, health checks
      uat-gate.md            # UAT checklist, sign-off procedure
      ci-cd-monitoring.md    # GitHub Actions monitoring, failure triage
  workflows/
    feature-delivery.md      # EXTENDED — inner + outer loop workflow (prose)
  config/
    workflow.schema.yaml     # NEW — universal step schema definition
    workflow.defaults.yaml   # NEW — base step sequence for all workflow types
    workflow.local.yaml      # NEW — personal overrides (gitignored)
    config.yaml              # AMENDED — adds models: registry section
  state/
    harness.db               # NEW — SQLite index (never source of truth)
    workflow_runs/           # NEW — per-run execution state (JSON)
    wait_uat/                # NEW — UAT sentinel files (one per feature)
    evals/                   # NEW — eval results per skill

src/scripts/
  harness_state.py           # NEW — shared state write library
  workflow_runner.py         # NEW — reads YAML config, drives phase transitions
  deploy_staging.py          # NEW — Docker staging deployment script
  delivery_monitor.py        # NEW — GitHub Actions polling + reporting
  generate_uat_checklist.py  # NEW — UAT checklist from feature branch diff
  generate_release_notes.py  # NEW — release notes from commits + RTM
  eval_runner.py             # NEW — skill eval execution
  drift_detector.py          # NEW — dead code + stale skill detection
  distill_dream.py           # NEW — dream phase distillation (Phase L)
  git_ops.py                 # NEW — skeleton Git operations (Phase H.8)
  hooks/
    validate_command.py      # NEW — pre-tool hook (Phase H.9.2)
    record_tool_use.py       # NEW — post-tool hook (Phase H.9.2)
  migrations/
    001_harness_schema.sql   # NEW — SQLite schema (Phase A.2)
    run_migrations.py        # NEW — migration runner (Phase A.2)

bootstrap/
  install.py                 # NEW — bootstrap install script (Phase I.2)
  validate.py                # NEW — environment validation (Phase I.3)

docs/
  getting-started.md         # NEW — getting-started guide (Phase M.1)
  configuration.md           # NEW — configuration reference (Phase M.2)
  customisation.md           # NEW — customisation guide (Phase M.3)

.agent/
  UNIVERSAL_CONTEXT.md       # NEW — single canonical context source (Phase J.1)
  review_context_universal.md  # NEW — universal review invariants (Phase I.5)
  workflows/
    onboarding.md            # NEW — first-session onboarding workflow (Phase J.3)
  state/
    pending_approvals.json   # NEW — HITL approval queue (Phase K.1)
    pending_approvals/       # NEW — per-approval context files (Phase K.1)
    dream_proposals/         # NEW — distillation proposals by date (Phase L.1)
    onboarding_baseline.json # NEW — health baseline at onboarding (Phase J.3)
```

---

## 4. Implementation Phases

### Phase A — Harness State Persistence
**Effort:** 2 days
**Closes:** PH-STATE-01, PH-STATE-02, PH-STATE-03, PH-STATE-04

#### A.1 — `harness_state.py` shared write library (PH-STATE-01)

Create `src/scripts/harness_state.py` with:

```python
class HarnessState:
    """
    Single entry point for all harness state writes.
    Writes to flat files (source of truth) AND SQLite (query index).
    SQLite is always reconstructible from flat files.
    """
    def write_gate_result(self, session_id, gate_name, verdict, detail): ...
    def write_violation(self, session_id, rule, file, line, detail): ...
    def write_session_start(self, session_id, branch, agent_persona): ...
    def write_session_end(self, session_id, outcome, commit_sha): ...
    def write_health_score(self, pillar_id, score, evidence): ...
```

All existing scripts that write to `.agent/state/` must be updated to
call `HarnessState` instead of writing directly. This ensures SQLite is
always in sync with flat files.

**Acceptance criteria:**
- `harness_state.py` passes mypy
- All flat file writes proxied through HarnessState
- SQLite writes are non-blocking (failure does not affect gate chain)

#### A.2 — `~/.aisdlc/harness.db` schema (PH-STATE-02)

Create migration script `src/scripts/migrations/001_harness_schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    agent_persona TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    outcome TEXT,
    commit_sha TEXT
);

CREATE TABLE IF NOT EXISTS gate_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    gate_name TEXT NOT NULL,
    verdict TEXT NOT NULL,  -- PASS | FAIL | WARN
    detail TEXT,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    rule TEXT NOT NULL,
    file_path TEXT,
    line_number INTEGER,
    detail TEXT,
    resolved_at TEXT,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS health_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    pillar_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    evidence TEXT,
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project);
CREATE INDEX IF NOT EXISTS idx_violations_rule ON violations(rule);
```

DB location: `~/.aisdlc/harness.db` (user-level, shared across projects).
Migration runner: `src/scripts/migrations/run_migrations.py`.

**Acceptance criteria:**
- Schema creates cleanly on empty DB
- Migration runner is idempotent
- DB location respects `AISDLC_DB_PATH` env var override

#### A.3 — Update `harness_health.py` (PH-STATE-03)

Add `--project` flag and `--cross-project` mode:

```
poetry run python src/scripts/harness_health.py
  --project gym-app           # Single project report (current behaviour)
  --cross-project             # All projects in harness.db
  --since 2026-01-01          # Date filter
```

Cross-project mode produces a comparison table: each project as a row,
pillars as columns, scores as cells.

**Acceptance criteria:**
- `--project gym-app` produces identical output to current behaviour
- `--cross-project` runs without error when DB has 1+ projects
- `--since` filters gate_results and violations correctly

#### A.4 — Session lifecycle hooks (PH-STATE-04)

The bootloader currently relies on the agent to call session start/end.
This is unreliable — if the agent crashes, session_end is never written.

Implement a pre-commit hook that calls `HarnessState.write_session_start()`
if no open session exists for the current branch, and a post-commit hook
that calls `write_session_end()` with the commit SHA.

Hooks must be idempotent. Session ID is derived from `branch + date`.

**Acceptance criteria:**
- Pre-commit hook creates session record if none exists
- Post-commit hook closes the session with commit SHA
- Hooks do not block commit on DB failure (graceful degradation)

---

### Phase B — Drift Detection
**Effort:** 1 day
**Closes:** PD-01

Create `src/scripts/drift_detector.py` with two detectors:

#### B.1 — Dead skill detection

Scans `.agent/skills/**/*.md` and checks each skill's `validate:` script
(if present) is still callable. Also checks whether the skill references
any files or patterns in `src/` that no longer exist.

```
poetry run python src/scripts/drift_detector.py --mode skills
```

Output: list of stale skills with reason (missing file, broken validate
reference, or last-modified > 90 days without any gate reference).

#### B.2 — Dead code detection

Wraps `vulture` (already in dev dependencies) with harness-aware output:
maps dead code to any skill that claims to test it. If a skill claims
coverage of a function that vulture flags as dead, the skill is stale.

```
poetry run python src/scripts/drift_detector.py --mode dead-code
```

**Pre-commit integration:** `drift_detector.py --mode skills` runs weekly
via a scheduled pre-commit stage (not blocking, WARN output only).

**Acceptance criteria:**
- `--mode skills` identifies at least 1 genuine stale skill in current state
- `--mode dead-code` runs without error on full `src/` tree
- Output is structured JSON consumable by `harness_health.py`

---

### Phase C — Eval Pipeline
**Effort:** 2 days
**Closes:** PE-01, PE-02

#### C.1 — Eval architecture (PE-01)

Each skill in `.agent/skills/` may have a corresponding eval definition in
`.agent/evals/<skill-name>/`. An eval definition is a YAML file:

```yaml
# .agent/evals/rbac/eval.yaml
skill: .agent/skills/rbac/SKILL.md
description: "Validates that the RBAC skill produces correct output"
cases:
  - id: rbac-001
    prompt: "Add a new endpoint that requires SYSTEM_ADMIN only"
    expected_patterns:
      - "require_permission"
      - "UserRole.SYSTEM_ADMIN"
    forbidden_patterns:
      - "if current_user.role =="
    tags: [rbac, permissions]
```

`eval_runner.py` runs each case against the Claude API with the skill
loaded, checks the output against patterns, and writes results to
`.agent/state/evals/<skill>/<date>.json`.

#### C.2 — Skill evaluation standard (PE-02)

Document the eval format in `.agent/skills/meta/eval-standard.md`.
Every new skill added to the library must include at minimum one eval case
before being accepted into the gate chain. Add this as a check to
`architecture_checks.py`: if a new skill file is added without a
corresponding eval definition, the commit is warned (not blocked — WARN
only until backlog is clear).

**Acceptance criteria:**
- `eval_runner.py` runs 3 existing skills without error
- Output JSON is machine-readable by `harness_health.py`
- `architecture_checks.py` warns on new skills without eval definition
- At least 3 skills have eval definitions by phase completion

---

### Phase D — Outer Loop Workflow Extension
**Effort:** 1 day

Extend `feature-delivery.md` workflow with outer loop steps.
The current workflow ends at step 6 (Commit & Report).
Add steps 7–13:

```
Step 7:  Create UAT checklist and release notes
Step 8:  Deploy to Docker staging [GATE: deployment health check]
Step 9:  Run full test suite against staging [GATE: all tests pass]
Step 10: Write WAIT_UAT sentinel — pause for human sign-off
Step 11: [HUMAN] Perform UAT — delete sentinel to resume
Step 12: Merge feature branch to devops [GATE: no merge conflicts]
Step 13: Monitor CI/CD — watch GitHub Actions, report status
```

Steps 8 and 9 are binary gates: failure halts delivery and reports to the
health log. Steps 10–11 are the human approval gate. Steps 12–13 are
automated with failure escalation.

Also create four new skill files:

**`.agent/skills/delivery/feature-branch.md`**
- Branch naming: `feature/<ticket-id>-<slug>`
- Branch creation: always from latest `devops`
- Merge target: `devops` (never `main` directly)
- Conflict resolution protocol

**`.agent/skills/delivery/staging-deployment.md`**
- Pre-deployment checklist
- Docker compose commands (pre-approved, no permission required)
- Health check endpoints and expected responses
- Rollback procedure

**`.agent/skills/delivery/uat-gate.md`**
- WAIT_UAT sentinel: `.agent/state/wait_uat/<branch>.md`
- UAT checklist template (generated per feature from diff)
- Sign-off: human deletes sentinel file to resume
- Escalation: if sentinel exists > 5 days, health report flags it

**`.agent/skills/delivery/ci-cd-monitoring.md`**
- GitHub Actions API polling procedure
- Failure categories: linting, tests, deployment, security scan
- Agent response per category
- Escalation: if >3 failed runs on same commit, write HALT and escalate

**Acceptance criteria:**
- `feature-delivery.md` workflow is syntactically valid YAML
- All four skill files pass the skill structure validator
- Workflow references all four skill files in its `skills:` section

---

### Phase E — Staging Deployment Automation
**Effort:** 1 day

#### E.1 — `deploy_staging.py`

```python
#!/usr/bin/env python3
"""
Deploys the application to Docker staging and runs health checks.
Pre-approved for agent execution — no permission prompt required.
Usage: python src/scripts/deploy_staging.py [--check-only]
Exit codes: 0 = healthy, 1 = deployment failed, 2 = health check failed
"""
```

Steps:
1. `docker compose -f docker-compose.staging.yml down --remove-orphans`
2. `docker compose -f docker-compose.staging.yml build --no-cache`
3. `docker compose -f docker-compose.staging.yml up -d`
4. Poll `GET /health` until 200 or timeout (60s)
5. Poll `GET /api/health/db` until `{"status": "ok"}` or timeout (30s)
6. Run smoke tests: `pytest tests/integration/test_startup_safety.py -x`
7. Write deployment record to `HarnessState`

#### E.2 — Pre-approved command list update

Add to `.agent/config/approved_commands.yaml`:

```yaml
staging_deployment:
  description: "Docker staging deployment — pre-approved, no prompt required"
  commands:
    - docker compose -f docker-compose.staging.yml down --remove-orphans
    - docker compose -f docker-compose.staging.yml build --no-cache
    - docker compose -f docker-compose.staging.yml up -d
    - python src/scripts/deploy_staging.py
    - python src/scripts/deploy_staging.py --check-only
```

**Acceptance criteria:**
- `deploy_staging.py --check-only` runs against current staging without rebuilding
- `deploy_staging.py` completes full deployment in < 5 minutes
- Exit codes are correct in all three scenarios
- HarnessState receives deployment record on success and failure

---

### Phase F — CI/CD Monitoring Loop
**Effort:** 2 days

#### F.1 — `delivery_monitor.py`

```python
"""
Polls GitHub Actions for the current branch's workflow runs.
Called by the agent after merging to devops.
Usage: python src/scripts/delivery_monitor.py --branch devops --wait
Exit codes: 0 = all workflows passed, 1 = failure detected, 2 = timeout
"""
```

Steps:
1. Poll `GET /repos/{owner}/{repo}/actions/runs?branch={branch}` every 30s
2. Detect run completion (conclusion: success | failure | cancelled)
3. On failure: fetch failed job logs, extract error context
4. Write structured failure report to `.agent/state/ci_failures/<run_id>.md`
5. Inject failure context into `review_context.md` for next session

#### F.2 — Failure triage categories

The monitor classifies failures into four categories, each with a defined
agent response:

| Category | Detection | Agent response |
|----------|-----------|----------------|
| Lint / format | Black/Ruff failure | Fix formatting, re-push |
| Test failure | pytest non-zero exit | Read failure log, fix, re-push |
| Deployment | Docker build failure | Read build log, fix Dockerfile/deps |
| Security scan | bandit/safety failure | Surface to human, write HALT |

Security failures always write a HALT sentinel — the agent must not
attempt to resolve them autonomously.

#### F.3 — GitHub token configuration

Requires `GITHUB_TOKEN` in environment (read-only, `repo:read` scope only).
Document in `README.md` and `.env.example`. Agent must not use a token
with write access for monitoring.

**Acceptance criteria:**
- `delivery_monitor.py --branch devops --wait` runs without error
- Lint/format failures produce an actionable fix in < 2 attempts
- Security failures always write HALT and do not attempt auto-fix
- Failure reports are structured JSON readable by `harness_health.py`

---

### Phase G — UAT Gate Mechanism
**Effort:** 1 day

#### G.1 — `generate_uat_checklist.py`

Generates a UAT checklist from:
- The feature branch diff (changed endpoints, UI components)
- The RTM (requirements mapped to the feature)
- The BDD scenarios tagged to the feature's domain

```markdown
# UAT Checklist — feature/member-history-view
**Generated:** 2026-05-10
**Branch:** feature/member-history-view
**RTM items:** REQ-045, REQ-046, REQ-047

## New endpoints to test
- [ ] GET /api/members/{id}/history — verify pagination, date filter
- [ ] GET /api/members/{id}/history/export — verify CSV download

## BDD scenarios to verify manually
- [ ] Member views own check-in history (domain-membership, scenario 142)
- [ ] Staff views member history with branch isolation (domain-access, scenario 143)

## Regression areas
- [ ] Check-in flow unchanged (smoke test passed in staging ✅)
- [ ] Member portal loads without error (Playwright E2E passed ✅)

## Sign-off
Delete `.agent/state/wait_uat/feature-member-history-view.md` to proceed.
```

#### G.2 — `generate_release_notes.py`

Generates release notes from git log between the feature branch and devops,
filtered through the RTM to map commit messages to requirement IDs:

```markdown
# Release Notes — v3.Sprint3.Feature: Member History View
**Date:** 2026-05-10

## Requirements delivered
- REQ-045: Member check-in history endpoint (GET /api/members/{id}/history)
- REQ-046: History export to CSV
- REQ-047: Staff access to member history with branch isolation

## Changes
- src/application/services/member_service.py — added get_history()
- src/presentation/api/routes/members.py — new /history endpoints
- tests/integration/test_member_history.py — 12 new integration tests
- tests/bdd/features/member_history.feature — 3 new BDD scenarios

## Test coverage
Integration: 12 new tests, all passing
BDD: 3 new scenarios, gate-tagged @domain-membership
Coverage: 87% (unchanged)
```

#### G.3 — WAIT_UAT sentinel

Sentinel file: `.agent/state/wait_uat/<branch-slug>.md`
Content: the generated UAT checklist (human-readable, human-editable).
Agent checks for sentinel at start of every session on that branch.
If sentinel exists: do not pick up new roadmap items. Print:

```
⏸  WAIT_UAT sentinel active for feature/<branch>.
   UAT checklist: .agent/state/wait_uat/<branch-slug>.md
   Delete the sentinel file to resume delivery.
```

**Acceptance criteria:**
- `generate_uat_checklist.py` produces valid markdown for any feature branch
- `generate_release_notes.py` correctly maps commits to RTM items
- Sentinel detection fires before roadmap scan in feature workflow
- `harness_health.py` reports stale sentinels (> 5 days old)

---

### Phase H — Workflow Configuration Engine
**Effort:** 2 days

This phase makes workflow step sequencing, model assignment, and personal
preferences data-driven rather than prose-driven. The analogy is a Telco
BSS CDR mediation system: stream types (workflow types) map to step
sequences (phases) via configuration tables, with per-step config and
enabled/disabled flags. The Java engine reads the tables; the workflow
runner reads the YAML.

#### H.1 — `workflow.schema.yaml` (universal schema definition)

Defines the valid structure of any workflow definition. Never edited
per-project — it is the contract all workflow YAML must conform to.

Three executor types are first-class:
- `agent` — the skeleton loads context and model, the agent executes, the skeleton evaluates the phase completion contract
- `tool` — the skeleton runs a deterministic script, no agent involved
- `human-gate` — the skeleton writes a sentinel and blocks until a human acts

```yaml
# .agent/config/workflow.schema.yaml
workflow:
  id: string
  name: string
  type: enum                          # feature | release | deploy | bug-fix |
                                      # hotfix | security | research | ops
  phases:
    - id: string                      # unique within this workflow
      name: string
      executor: enum                  # agent | tool | human-gate

      # --- agent executor fields ---
      skill: string                   # skill file path (relative to .agent/skills/)
      agent:
        model: enum                   # frontier | efficient | local
        persona: string
        context: enum                 # shared | clean
        plan_mode: boolean            # true = agent outlines plan before executing
                                      # human reviews plan before agent proceeds
        disallowed_tools: [string]    # tools the agent cannot call in this phase
                                      # e.g. adversarial-review: [Bash, Write, Task]
        output_style: string          # path to .claude/output-styles/<style>.md
                                      # shapes the structural format of agent output
        context_budget:               # context management for long-running phases
          warn_at_pct: integer        # warn when context reaches this % (default 70)
          compact_at_pct: integer     # trigger compaction at this % (default 85)
          compaction_model: string    # model for summarisation (default: efficient)
      contract:                       # what phase_complete.json must contain
        required_fields: [string]     # keys that must be present
        gate_checks: [string]         # boolean fields that must be true
        numeric_gates:                # numeric fields with thresholds
          - field: string
            operator: enum            # gte | lte | eq
            threshold: number
        allowed_verdicts: [string]    # for review phases: APPROVE | REQUEST_CHANGES | HALT
      config: object                  # phase-specific overridable values
      max_attempts: integer           # default 1; > 1 enables retry loop
      hooks:                          # intercept every tool call in this phase
        pre_tool:                     # fires before each tool execution
          - script: string            # path to validation script
            on_fail: enum             # halt | warn | skip_tool
        post_tool:                    # fires after each tool execution
          - script: string            # path to logging/recording script

      # --- orchestrator-workers fields (executor: agent, multi_agent: true) ---
      multi_agent:
        enabled: boolean              # true = orchestrator-workers pattern
        orchestrator_model: string    # model for task decomposition (default: frontier)
        worker_model: string          # model for parallel execution (default: efficient)
        max_workers: integer          # cap on parallel workers (default: 5)
        synthesizer_model: string     # model that aggregates results (default: frontier)

      # --- tool executor fields ---
      tool:
        script: string                # path to deterministic script
        args: [string]                # fixed arguments
        exit_code_gate: boolean       # true = non-zero exit fails the gate
        mcp_server: string            # optional: MCP server name from mcp_servers config

      # --- git_action fields (skeleton-controlled, any executor) ---
      git_action:
        type: enum                    # branch | commit | merge | push | tag
        timing: enum                  # before | after
        template: string              # commit message template

      # --- shared fields ---
      enabled: boolean                # false = skip entirely
      on_failure: enum                # halt | warn | skip | escalate | retry
      human_approval: boolean         # true = WAIT sentinel before advancing
      overridable: boolean            # false = local overrides rejected for this phase
```

#### H.2 — `workflow.defaults.yaml` (committed base configuration)

Extracts the current `feature-implementation.md` step sequence into
machine-readable YAML with model assignments, executor types, phase
completion contracts, and skeleton Git actions. The prose workflow files
remain as documentation and context for the agent within each phase —
they are not replaced, they are governed.

```yaml
# .agent/config/workflow.defaults.yaml
workflows:

  feature-implementation:
    name: Feature Implementation
    type: feature
    phases:

      - id: create-branch
        name: Create Feature Branch
        executor: tool
        tool:
          script: src/scripts/git_ops.py
          args: [branch, create]
          exit_code_gate: true
        git_action:
          type: branch
          timing: before
          template: "feature/{{roadmap_item_slug}}"
        enabled: true
        on_failure: halt
        overridable: false            # branch creation is always required

      - id: impact-analysis
        name: Impact & Gap Analysis
        executor: agent
        skill: project-manager/SKILL.md
        agent:
          model: frontier
          persona: project-manager
          context: shared
        contract:
          required_fields: [gap_analysis_path, affected_modules, risk_level]
          gate_checks: []             # informational — no hard gates
        on_failure: halt
        enabled: true
        human_approval: false

      - id: requirements
        name: Requirements Analysis
        executor: agent
        skill: business-analyst/SKILL.md
        agent:
          model: frontier
          persona: business-analyst
          context: shared
        contract:
          required_fields: [spec_path, bdd_scenario_count, rtm_updated]
          gate_checks: [rtm_updated]
          numeric_gates:
            - field: bdd_scenario_count
              operator: gte
              threshold: 3
        config:
          spec_template: .agent/templates/feature_spec.md
        on_failure: halt
        enabled: true
        human_approval: true          # SPEC GATE — mandatory
        overridable: false

      - id: architecture
        name: Architecture Design
        executor: agent
        skill: senior-architect/SKILL.md
        agent:
          model: frontier
          persona: architect
          context: shared
          plan_mode: true             # present options overview, await human selection
          output_style: .claude/output-styles/architect.md
        contract:
          required_fields: [options, selected_option, adr_path]
          gate_checks: []
        config:
          options_count: 3            # overridable
        on_failure: halt
        enabled: true
        human_approval: true          # overridable to false if options_count == 1
        overridable: true

      - id: multi-persona-audit
        name: Implementation Plan Audit
        executor: agent
        skill: project-manager/SKILL.md
        agent:
          model: frontier
          persona: project-manager
          context: shared
          output_style: .claude/output-styles/audit.md
        multi_agent:
          enabled: true               # orchestrator-workers: spawn only relevant personas
          orchestrator_model: frontier # analyses spec → selects 3-5 relevant personas
          worker_model: efficient      # each persona runs in parallel (not sequential)
          max_workers: 5
          synthesizer_model: frontier  # aggregates findings into unified risk report
        contract:
          required_fields: [audit_summary, risk_flags, confidence_score]
          gate_checks: []
        on_failure: warn
        enabled: true                 # overridable to false
        human_approval: false

      - id: db-prep
        name: Database & Test Data Preparation
        executor: agent
        skill: dba/SKILL.md
        agent:
          model: efficient
          persona: dba
          context: shared
        contract:
          required_fields: [migration_path, stairway_result]
          gate_checks: [stairway_result]
        on_failure: halt
        enabled: true
        human_approval: false

      - id: implementation
        name: Feature Implementation (TDD)
        executor: agent
        skill: python-backend-guidelines/SKILL.md
        agent:
          model: efficient
          persona: developer
          context: shared
          output_style: .claude/output-styles/developer.md
          context_budget:
            warn_at_pct: 70           # warn at 70% context usage
            compact_at_pct: 85        # trigger compaction at 85% — before overflow
            compaction_model: efficient # cheap model for summarisation
        contract:
          required_fields: [unit_tests_pass, mypy_errors, test_count_added]
          gate_checks: [unit_tests_pass]
          numeric_gates:
            - field: mypy_errors
              operator: eq
              threshold: 0
        config:
          test_command: "poetry run pytest tests/unit/ -v"
          type_check_command: "poetry run mypy src/"
        hooks:
          pre_tool:
            - script: src/scripts/hooks/validate_command.py  # checks against approved_commands.yaml
              on_fail: halt
          post_tool:
            - script: src/scripts/hooks/record_tool_use.py   # writes to HarnessState
        on_failure: halt
        max_attempts: 3
        enabled: true
        human_approval: false

      - id: quality-assurance
        name: Quality Assurance
        executor: agent
        skill: test-engineer/SKILL.md
        agent:
          model: efficient
          persona: test-engineer
          context: shared
        contract:
          required_fields: [coverage_pct, tests_passing, high_cve_count]
          gate_checks: [tests_passing]
          numeric_gates:
            - field: coverage_pct
              operator: gte
              threshold: "{{coverage_minimum}}"   # resolved from config
            - field: high_cve_count
              operator: eq
              threshold: 0
        config:
          coverage_minimum: 80        # overridable per project
          test_command: "poetry run pytest --cov=src --cov-report=json"
          performance_slo_p95_ms: 200 # overridable
        on_failure: halt
        enabled: true
        human_approval: false

      - id: documentation
        name: Documentation Update
        executor: agent
        skill: technical-writer/SKILL.md
        agent:
          model: efficient
          persona: technical-writer
          context: shared
        contract:
          required_fields: [docs_updated]
          gate_checks: []
        on_failure: warn              # non-blocking
        enabled: true                 # overridable to false
        human_approval: false

      - id: adversarial-review
        name: AI Adversarial Review
        executor: agent
        skill: code-reviewer/SKILL.md
        agent:
          model: frontier
          persona: code-reviewer
          context: clean              # CRITICAL: new context — no session bias
          disallowed_tools: [Bash, Write, Edit, Task, WebSearch]
                                      # reviewer reads diff only — cannot run code
                                      # or write files — pure evaluation
          output_style: .claude/output-styles/code-reviewer.md
                                      # enforces APPROVE/REQUEST_CHANGES/HALT
                                      # verdict structure that ContractEvaluator parses
        contract:
          required_fields: [verdict, findings]
          gate_checks: []
          allowed_verdicts: [APPROVE, REQUEST_CHANGES, HALT]
        on_failure: halt
        enabled: true
        human_approval: false
        overridable: false            # adversarial review is always required

      - id: commit-inner-loop
        name: Commit Inner Loop Deliverables
        executor: tool
        tool:
          script: src/scripts/git_ops.py
          args: [commit, inner-loop]
          exit_code_gate: true
        git_action:
          type: commit
          timing: after
          template: "[FEAT] {{roadmap_item_slug}}: inner loop complete — review APPROVED"
        enabled: true
        on_failure: halt
        overridable: false

      - id: uat-preparation
        name: Generate UAT Checklist and Release Notes
        executor: tool
        tool:
          script: src/scripts/generate_uat_checklist.py
          args: []
          exit_code_gate: true
        enabled: true
        on_failure: halt

      - id: deploy-staging
        name: Deploy to Staging
        executor: tool
        tool:
          script: src/scripts/deploy_staging.py
          args: []
          exit_code_gate: true
        config:
          health_poll_timeout_s: 60
          health_endpoint: /health
          staging_test_command: "poetry run pytest tests/integration/ --staging -v"
        on_failure: halt
        max_attempts: 2
        enabled: true

      - id: uat-gate
        name: UAT Sign-off
        executor: human-gate
        on_failure: halt
        enabled: true
        human_approval: true
        overridable: false            # UAT gate is always required

      - id: merge-devops
        name: Merge to Devops Branch
        executor: tool
        tool:
          script: src/scripts/git_ops.py
          args: [merge, to-devops]
          exit_code_gate: true
        git_action:
          type: merge
          timing: before
        config:
          conflict_resolver_model: efficient  # agent resolves conflicts if any
        on_failure: halt
        enabled: true
        overridable: false

      - id: cicd-monitor
        name: Monitor CI/CD Pipeline
        executor: agent             # agent + GitHub MCP — richer failure diagnosis
        skill: delivery/ci-cd-monitoring.md
        agent:
          model: efficient
          persona: devops
          context: shared
          disallowed_tools: [Write, Edit]  # read-only access to GitHub
          context_budget:
            compact_at_pct: 80
            compaction_model: efficient
        tool:
          mcp_server: github        # GitHub MCP server (100+ tools)
                                    # NOTE: requires Docker + GITHUB_TOKEN read-only
        contract:
          required_fields: [workflow_conclusion, failed_jobs]
          gate_checks: []
          allowed_verdicts: [success, lint_failure, test_failure,
                             security_failure, deploy_failure]
        config:
          poll_interval_s: 30
          timeout_minutes: 60
          auto_fix_categories: [lint, test]  # security always HALT
          max_fix_attempts: 3
        on_failure: escalate
        enabled: true

  bug-fix:
    name: Bug Fix
    type: bug-fix
    phases:
      - id: create-branch
        executor: tool
        tool: { script: src/scripts/git_ops.py, args: [branch, create] }
        git_action: { type: branch, timing: before, template: "fix/{{roadmap_item_slug}}" }
        on_failure: halt
        overridable: false

      - id: impact-analysis
        executor: agent
        agent: { model: frontier, persona: project-manager, context: shared }
        contract: { required_fields: [gap_analysis_path], gate_checks: [] }
        on_failure: halt

      - id: implementation
        executor: agent
        skill: python-backend-guidelines/SKILL.md
        agent: { model: efficient, persona: developer, context: shared }
        contract:
          required_fields: [unit_tests_pass, mypy_errors]
          gate_checks: [unit_tests_pass]
          numeric_gates: [{ field: mypy_errors, operator: eq, threshold: 0 }]
        on_failure: halt
        max_attempts: 3

      - id: quality-assurance
        executor: agent
        agent: { model: efficient, persona: test-engineer, context: shared }
        contract:
          required_fields: [tests_passing]
          gate_checks: [tests_passing]
        on_failure: halt

      - id: adversarial-review
        executor: agent
        skill: code-reviewer/SKILL.md
        agent: { model: frontier, persona: code-reviewer, context: clean }
        contract:
          required_fields: [verdict]
          allowed_verdicts: [APPROVE, REQUEST_CHANGES, HALT]
        on_failure: halt
        overridable: false

      - id: commit-inner-loop
        executor: tool
        tool: { script: src/scripts/git_ops.py, args: [commit, inner-loop] }
        git_action: { type: commit, timing: after,
                      template: "[FIX] {{roadmap_item_slug}}: fix — review APPROVED" }
        on_failure: halt
        overridable: false

      - id: merge-devops
        executor: tool
        tool: { script: src/scripts/git_ops.py, args: [merge, to-devops] }
        git_action: { type: merge, timing: before }
        on_failure: halt
        overridable: false

  hotfix:
    name: Hotfix (urgent, minimal gates)
    type: hotfix
    phases:
      - id: create-branch
        executor: tool
        tool: { script: src/scripts/git_ops.py, args: [branch, create] }
        git_action: { type: branch, timing: before,
                      template: "hotfix/{{roadmap_item_slug}}" }
        on_failure: halt
        overridable: false

      - id: implementation
        executor: agent
        skill: python-backend-guidelines/SKILL.md
        agent: { model: efficient, persona: developer, context: shared }
        contract:
          required_fields: [unit_tests_pass]
          gate_checks: [unit_tests_pass]
        on_failure: halt
        max_attempts: 2

      - id: quality-assurance
        executor: agent
        agent: { model: efficient, persona: test-engineer, context: shared }
        contract: { required_fields: [tests_passing], gate_checks: [tests_passing] }
        on_failure: halt

      - id: adversarial-review
        executor: agent
        skill: code-reviewer/SKILL.md
        agent: { model: frontier, persona: code-reviewer, context: clean }
        contract:
          required_fields: [verdict]
          allowed_verdicts: [APPROVE, REQUEST_CHANGES, HALT]
        on_failure: halt
        overridable: false
        human_approval: true          # human must also sign off on hotfixes

      - id: commit-inner-loop
        executor: tool
        tool: { script: src/scripts/git_ops.py, args: [commit, inner-loop] }
        git_action: { type: commit, timing: after,
                      template: "[HOTFIX] {{roadmap_item_slug}}: emergency fix" }
        on_failure: halt
        overridable: false

      - id: merge-devops
        executor: tool
        tool: { script: src/scripts/git_ops.py, args: [merge, to-devops] }
        git_action: { type: merge, timing: before }
        on_failure: halt
        overridable: false
```

#### H.3 — Model registry in `config.yaml`

Add a `models:` section to the existing `.agent/config/config.yaml`:

```yaml
# Appended to .agent/config/config.yaml
models:
  frontier:
    description: "High-reasoning model for planning, architecture, and review"
    provider: anthropic
    model: claude-opus-4-6
    fallback: claude-sonnet-4-6
    cost_tier: high
    use_for:
      - impact analysis and planning
      - requirements and spec writing
      - architecture option generation
      - adversarial code review
      - multi-persona audit

  efficient:
    description: "Fast model for mechanical implementation tasks"
    provider: google
    model: gemini-2.5-flash
    fallback: claude-haiku-4-5-20251001
    cost_tier: low
    use_for:
      - code generation from confirmed spec
      - database migrations and seed updates
      - test execution and coverage checks
      - documentation updates
      - deployment commands
      - CI/CD monitoring

  local:
    description: "Zero-cost local model for high-volume implementation"
    provider: ollama
    model: qwen3-coder-30b
    fallback: efficient              # if Ollama unavailable, use efficient
    cost_tier: zero
    use_for:
      - bulk code generation
      - repetitive pattern application
      - offline development
```

The model registry uses symbolic names (`frontier`, `efficient`, `local`)
throughout the workflow YAML. When a model or provider changes, only
`config.yaml` needs updating — no workflow files change.

#### H.4 — `workflow_runner.py` (FSM-backed phase transition engine)

The runner is implemented as a finite state machine using the Python
`transitions` library rather than a sequential array walker. This gives
mathematically precise state definitions, transition guards that map
directly to contract gate checks, explicit handling of retry loops, and
a clean migration path to Temporal at team scale.

Each phase in the YAML maps to a named FSM state. Transitions are
triggered by events fired from phase completion contracts and tool exit
codes. Guards enforce gate criteria before any advance is allowed.

```python
"""
workflow_runner.py — FSM-backed workflow orchestrator.

Manages state between phases. Does not execute agent work.
Reads phase completion contracts, evaluates gate criteria,
fires FSM transitions, records execution state to SQLite.

Usage:
  python src/scripts/workflow_runner.py start --workflow feature-implementation
  python src/scripts/workflow_runner.py resume [--run-id <id>]
  python src/scripts/workflow_runner.py status [--run-id <id>]
  python src/scripts/workflow_runner.py advance --phase <id> --result <path>

Exit codes:
  0 = transitioned — bootloader should invoke next phase
  1 = gate failure — halted
  2 = human approval required — sentinel written, waiting
  3 = phase skipped (enabled: false) — auto-advanced
  4 = max_attempts exceeded — halted
"""

from transitions import Machine

class WorkflowFSM:
    """
    Dynamically builds FSM from workflow.defaults.yaml merged with
    workflow.local.yaml. States from phase IDs; transitions from
    phase ordering, on_failure rules, max_attempts, and human_approval.
    """

    def __init__(self, workflow_id: str, run_id: str):
        self.workflow_id   = workflow_id
        self.run_id        = run_id
        self.config        = self._load_merged_config(workflow_id)
        self.phases        = self.config["phases"]
        self.attempt_counts: dict[str, int] = {}
        states, transitions = self._build_fsm_topology()
        self.machine = Machine(
            model=self, states=states, transitions=transitions,
            initial="idle", auto_transitions=False, send_event=True,
        )

    # ── Transition guards ─────────────────────────────────────────────

    def guard_gate_pass(self, event) -> bool:
        """Reads phase_complete.json and evaluates contract gate checks."""
        return ContractEvaluator(
            self._phase_cfg(event.kwargs["phase_id"])
        ).evaluate(event.kwargs["result_path"])

    def guard_verdict_approve(self, event) -> bool:
        result = json.loads(Path(event.kwargs["result_path"]).read_text())
        return result.get("verdict") == "APPROVE"

    def guard_verdict_halt(self, event) -> bool:
        result = json.loads(Path(event.kwargs["result_path"]).read_text())
        return result.get("verdict") == "HALT"

    def guard_attempts_remaining(self, event) -> bool:
        phase_id = event.kwargs["phase_id"]
        max_att  = self._phase_cfg(phase_id).get("max_attempts", 1)
        return self.attempt_counts.get(phase_id, 0) < max_att

    def guard_phase_enabled(self, event) -> bool:
        return self._phase_cfg(event.kwargs["phase_id"]).get("enabled", True)

    # ── FSM topology builder ──────────────────────────────────────────

    def _build_fsm_topology(self) -> tuple[list, list]:
        """
        Rules applied per phase:
          - Every phase → state
          - human_approval → additional <phase>_waiting state
          - adversarial-review verdict==REQUEST_CHANGES → retry loop back to implementation
          - max_attempts > 1 → retry transition back to same state
          - on_failure: halt → halted on gate failure
          - on_failure: warn → always advances regardless of gate result
          - executor: tool skipped phases → auto-advance via phase_skipped trigger
          - Terminal states: complete, halted
        """
        ...

    # ── Public interface ──────────────────────────────────────────────

    def advance(self, result_path: str) -> int:
        """Called after each phase. Fires FSM transition. Returns exit code."""
        phase_id = self.state
        self.attempt_counts[phase_id] = self.attempt_counts.get(phase_id, 0) + 1
        try:
            self.phase_complete(phase_id=phase_id, result_path=result_path)
            HarnessState().write_phase_result(
                self.run_id, phase_id, "complete", result_path)
            return 0 if self.state != "halted" else 1
        except MachineError as e:
            HarnessState().write_phase_result(
                self.run_id, phase_id, "failed", result_path, error=str(e))
            return 1

    def export_mermaid(self, output_path: str):
        """Exports the FSM as a Mermaid state diagram for documentation."""
        ...
```

**FSM state topology for `feature-implementation`** (condensed):

```
idle → create-branch → impact-analysis → requirements
requirements → [gate_pass] → requirements_waiting
requirements_waiting → [human_approved] → architecture
architecture → [options==1] → multi-persona-audit
architecture → [options>1] → architecture_waiting → [human] → multi-persona-audit
multi-persona-audit → [enabled] → db-prep | [skip] → db-prep
db-prep → [gate_pass] → implementation | [fail] → halted
implementation → [gate_pass] → quality-assurance
implementation → [gate_fail, attempts<max] → implementation
implementation → [gate_fail, attempts>=max] → halted
quality-assurance → [gate_pass] → documentation | [fail] → halted
documentation → [enabled] → adversarial-review | [skip] → adversarial-review
adversarial-review → [APPROVE] → commit-inner-loop
adversarial-review → [REQUEST_CHANGES] → implementation
adversarial-review → [HALT] → halted
commit-inner-loop → uat-preparation → deploy-staging
deploy-staging → [gate_pass] → uat-gate | [fail,retry] → deploy-staging | halted
uat-gate → [human_approved] → merge-devops
merge-devops → [gate_pass] → cicd-monitor | [fail] → halted
cicd-monitor → [success] → complete
cicd-monitor → [security_fail] → halted
cicd-monitor → [lint/test_fail] → cicd-monitor  (fix and re-monitor)
```

**`pyproject.toml` addition:**

```toml
[tool.poetry.dependencies]
transitions = "^0.9"
```

Run state is written to both:
- `.agent/state/workflow_runs/<run_id>.json` (flat file, source of truth)
- `harness.db → workflow_runs` table (SQLite, queryable)

#### H.5 — `workflow.local.yaml` (personal overrides, gitignored)

Add `workflow.local.yaml` to `.gitignore`. Document in README. Provide
a commented example template at `.agent/config/workflow.local.yaml.example`:

```yaml
# workflow.local.yaml — personal overrides, gitignored
# Copy this file to workflow.local.yaml and uncomment to customise.
#
# Overrides are merged onto workflow.defaults.yaml.
# Only specify what differs from the defaults.
# human_approval: true phases cannot be disabled.

overrides:
  feature-implementation:
    phases:
      architecture:
        config:
          options_count: 1          # I know the pattern — 1 option is enough

      multi-persona-audit:
        enabled: false              # I conduct this review mentally

      documentation:
        enabled: false              # I write docs at sprint end

      implementation:
        agent:
          model: local              # Use Qwen3-Coder locally for zero API cost
```

#### H.6 — SQLite workflow runs table

Add to the Phase A migration (`001_harness_schema.sql`):

```sql
CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,               -- branch + date slug
    workflow_id TEXT NOT NULL,         -- e.g. feature-implementation
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    current_phase_id TEXT,
    status TEXT NOT NULL               -- running | paused | completed | failed
);

CREATE TABLE IF NOT EXISTS workflow_phase_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    phase_id TEXT NOT NULL,
    model_used TEXT,                   -- actual model name used (not symbolic)
    started_at TEXT NOT NULL,
    completed_at TEXT,
    outcome TEXT,                      -- complete | skipped | failed | waiting
    gate_results TEXT,                 -- JSON array of gate outcomes
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_runs_project ON workflow_runs(project);
CREATE INDEX IF NOT EXISTS idx_phase_results_run ON workflow_phase_results(run_id);
```

#### H.7 — Phase Completion Contract

The phase completion contract is the interface between the skeleton and
the agent. Every agent-executed phase must write a structured JSON file
to `.agent/state/phase_results/<run_id>/<phase_id>.json` as its final
act before returning control to the skeleton. The skeleton reads this
file, evaluates it against the phase's `contract:` definition in
`workflow.defaults.yaml`, and fires the appropriate FSM transition.

**Contract schema:**

```json
{
  "phase_id": "implementation",
  "run_id": "feature-member-history-20260510",
  "status": "complete",
  "verdict": null,
  "gate_checks": {
    "unit_tests_pass": true,
    "mypy_errors": 0,
    "test_count_added": 12
  },
  "outputs": {
    "files_modified": ["src/application/services/member_service.py"],
    "files_created": ["tests/unit/test_member_history.py"],
    "spec_path": null,
    "migration_path": null,
    "adr_path": null
  },
  "model_used": "gemini-2.5-flash",
  "duration_seconds": 1847,
  "attempt": 1,
  "error_detail": null
}
```

**`ContractEvaluator` class:**

```python
class ContractEvaluator:
    \"\"\"
    Evaluates a phase_complete.json against a phase contract definition.
    Returns True (gate pass) or False (gate fail) with structured reason.
    \"\"\"

    def __init__(self, phase_config: dict):
        self.contract = phase_config.get("contract", {})

    def evaluate(self, result_path: str) -> bool:
        result = json.loads(Path(result_path).read_text())

        # 1. Required fields present
        for field in self.contract.get("required_fields", []):
            if field not in result.get("gate_checks", {}) and \
               field not in result.get("outputs", {}):
                self._fail(f"required field missing: {field}")
                return False

        # 2. Boolean gate checks
        for check in self.contract.get("gate_checks", []):
            val = result["gate_checks"].get(check)
            if not val:
                self._fail(f"gate check failed: {check} = {val}")
                return False

        # 3. Numeric threshold gates
        for gate in self.contract.get("numeric_gates", []):
            field    = gate["field"]
            operator = gate["operator"]
            threshold = gate["threshold"]
            # resolve {{config_key}} references
            if isinstance(threshold, str) and threshold.startswith("{{"):
                threshold = self._resolve_config(threshold)
            actual = result["gate_checks"].get(field)
            if not self._numeric_check(actual, operator, threshold):
                self._fail(f"numeric gate failed: {field} {operator} {threshold} "
                           f"(actual: {actual})")
                return False

        # 4. Verdict check (review phases only)
        allowed = self.contract.get("allowed_verdicts")
        if allowed:
            verdict = result.get("verdict")
            if verdict not in allowed:
                self._fail(f"verdict '{verdict}' not in {allowed}")
                return False

        return True

    @staticmethod
    def _verdict(event) -> str:
        result = json.loads(Path(event.kwargs["result_path"]).read_text())
        return result.get("verdict", "")
```

**Bootloader integration:**

The bootloader must be updated to call `workflow_runner.py status` at
session start and inject the result into the agent's context:

```
WORKFLOW_RUN_ID: feature-member-history-20260510
CURRENT_PHASE:  implementation (attempt 1 of 3)
CURRENT_MODEL:  gemini-2.5-flash (efficient)
SKILL_TO_LOAD:  python-backend-guidelines/SKILL.md
PHASE_CONTRACT: unit_tests_pass=true, mypy_errors=0, test_count_added>=1
NEXT_PHASE:     quality-assurance (if gate passes)
```

The agent knows exactly what phase it is in, what model it should be
using, what skill to load, and what the exit criteria are. It does not
need to figure any of this out from the workflow prose.

---

#### H.8 — Skeleton Git Operations (`git_ops.py`)

Git operations are deterministic infrastructure. The agent should never
decide when to branch, commit, or merge. All Git state changes are
performed by the skeleton, triggered by `git_action` entries in
`workflow.defaults.yaml`.

Create `src/scripts/git_ops.py`:

```python
\"\"\"
git_ops.py — All Git operations performed by the skeleton.

The agent never calls git directly. The skeleton calls this script
at the timing defined in workflow.defaults.yaml git_action entries.

Commands:
  branch create                     — creates feature/hotfix/fix branch from devops
  commit inner-loop                 — stages all, commits with templated message
  commit outer-loop                 — stages docs/release-notes, commits
  merge to-devops                   — merges current branch into devops
  merge conflict-resolve <patch>    — applies agent-resolved conflict patch
  tag release <version>             — tags a release commit
  push <remote> <branch>            — pushes to remote

All commands:
  - Log the operation to HarnessState
  - Write the resulting commit SHA to workflow_phase_results
  - Return exit code 0 on success, non-zero on failure
  - Never ask for user input — fail fast on unexpected state

Pre-approved for agent-initiated execution: NO
This script is called only by workflow_runner.py, never by the agent.
\"\"\"

def branch_create(template: str, context: dict) -> int:
    branch_name = template.replace("{{roadmap_item_slug}}", context["slug"])
    # git checkout -b <branch> devops
    # Fail if branch already exists — never clobber
    ...

def commit_inner_loop(template: str, context: dict) -> int:
    # git add -A
    # git commit -m <message>
    # Record SHA to HarnessState
    ...

def merge_to_devops(config: dict) -> int:
    # git checkout devops
    # git merge --no-ff <feature_branch>
    # On conflict: write conflict context to phase_results
    # for agent to resolve; return exit code 2 (conflict)
    ...

def push(remote: str, branch: str) -> int:
    # git push <remote> <branch>
    ...
```

**Conflict resolution flow** (the one case where git_ops.py invokes an agent):

```
merge_to_devops detects conflict
  → writes conflict diff to .agent/state/conflicts/<branch>.diff
  → exits with code 2
workflow_runner FSM fires conflict_detected trigger
  → transitions to resolving_conflict state
  → invokes agent with conflict diff as context (model: efficient)
  → agent writes resolved patch to .agent/state/conflicts/<branch>.patch
workflow_runner calls git_ops.py merge conflict-resolve <patch>
  → applies patch, completes merge
  → transitions to cicd-monitor state
```

The agent resolves conflict content; the skeleton applies it. The
agent never runs `git merge` itself.

**Acceptance criteria for H.8:**
- `git_ops.py branch create` creates a branch from devops, fails if
  branch already exists
- `git_ops.py commit inner-loop` stages all modified files and commits
  with the correct message template
- `git_ops.py merge to-devops` succeeds cleanly on a non-conflicting merge
- Conflict detection returns exit code 2 and writes the diff file
- Conflict resolution applies the patch and completes the merge
- All operations write to `HarnessState` with the resulting SHA
- The agent is never invoked by `git_ops.py` except for conflict resolution

---

#### H.9 — Cookbook-Derived Patterns

These patterns are drawn from Anthropic's official Claude Cookbook and
are incorporated into the harness design rather than treated as future
work. Each is referenced in H.1–H.2 above and documented here for
implementation guidance.

---

##### H.9.1 — Context Compaction (long-running agent phases)

Source: `automatic-context-compaction` and `session-memory-compaction`

Long implementation and QA sessions will exceed the 200k context limit
without intervention. Two variants apply:

- **Server-side compaction** (Opus 4.6 only): handled automatically
  by the Anthropic API. No SDK configuration required.
- **SDK-based compaction** (all other models): configure
  `compaction_control` with a threshold. When token usage exceeds it,
  the SDK injects a summary prompt, generates a structured summary,
  clears history, and resumes. A cheaper model handles summarisation.

The compaction summary prompt for harness phases should capture:

```
## Phase Context          — current phase_id, workflow_id, run_id
## Original Task          — the phase requirement and exit criteria
## Completed Actions      — what passed, what was confirmed working
## Failed Attempts        — what was tried, exact error messages
## Active Work            — what was being done at compaction point
## Remaining Criteria     — contract fields still needing satisfaction
## Critical Values        — file paths, test names, error codes to preserve
```

Implementation: the workflow runner monitors token usage per turn.
At `warn_at_pct`, it logs a warning to HarnessState. At
`compact_at_pct`, it fires the compaction prompt before overflow.
The `context_budget` phase schema fields (H.1) control these
thresholds per phase. Implementation and QA phases default to
`warn_at_pct: 70, compact_at_pct: 85`.

---

##### H.9.2 — Hooks for Gate Enforcement

Source: `chief-of-staff-agent` (Feature 3: Hooks), `sre-agent` (safety validation hooks)

Hooks intercept every tool call and fire synchronously. Two hooks per
phase: `pre_tool` validates before execution; `post_tool` records after.

**`src/scripts/hooks/validate_command.py`** (pre-tool):

Checks the proposed tool and arguments against `approved_commands.yaml`.
Returns exit code 0 (allow) or 1 (halt — cancels the tool call).
Writes any violation to HarnessState. This is the SRE cookbook
pattern applied: scope write access with a command allowlist.

**`src/scripts/hooks/record_tool_use.py`** (post-tool):

Records tool name, arguments, result summary, and timing to HarnessState.
Provides the audit trail without relying on the agent to self-report.

Add to the Phase A.2 SQLite migration:

```sql
CREATE TABLE IF NOT EXISTS tool_uses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    phase_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    input_summary TEXT,
    result_summary TEXT,
    duration_ms INTEGER,
    hook_verdict TEXT,               -- allowed | halted
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id)
);
```

This gives `harness_health.py` a complete picture of every tool call
in every phase — independent of the agent's self-reporting.

---

##### H.9.3 — Output Styles per Persona

Source: `chief-of-staff-agent` (Feature 2: Output Styles)

Output styles are markdown files in `.claude/output-styles/` that
modify the agent's output format structurally via the system prompt.
For the harness, each persona gets a style that enforces the
`phase_complete.json` contract format — not just through prompt
instructions but through the agent's underlying output configuration.

Four output style files required at minimum:

- **`developer.md`**: enforces `phase_complete.json` with `gate_checks`
  containing `unit_tests_pass`, `mypy_errors`, `test_count_added`
- **`code-reviewer.md`**: enforces `APPROVE / REQUEST_CHANGES / HALT`
  verdict JSON with `findings` and `security_issues` arrays; includes
  the explicit evaluator-only instruction: "You are evaluating only —
  not solving or implementing."
- **`architect.md`**: enforces the options array JSON before writing
  ADRs, with `selected_option: null` as the human approval checkpoint
- **`business-analyst.md`**: enforces the spec + BDD scenario count
  structure that the ContractEvaluator checks for requirements phase

The `output_style` field in H.1 wires a phase to its output style.
The `setting_sources: ["project"]` SDK option must be set for the
runner to load output styles from `.claude/output-styles/`.

---

##### H.9.4 — Orchestrator-Workers for Multi-Persona Audit

Source: `orchestrator-workers` (Anthropic, Dec 2024)

The multi-persona audit (Phase 2.5) replaces sequential single-agent
persona roleplay with the orchestrator-workers pattern:

1. **Orchestrator** (frontier) reads the feature spec and dynamically
   selects 3-5 relevant personas — not always the same 10. A payments
   feature gets security-auditor and DBA. A UI feature gets ux-reviewer
   and accessibility-auditor. The orchestrator's analysis determines
   which personas add value for this specific feature.

2. **Workers** (efficient, parallel) each receive the feature spec and
   their specific review scope. They run simultaneously, not sequentially.

3. **Synthesiser** (frontier) aggregates findings into a unified risk
   report with a confidence score.

This costs less than sequential frontier calls for 10 personas, produces
higher-quality output (each worker focuses on one domain), and takes less
wall time (parallel execution).

The `multi_agent` schema fields in H.1 control this. The workflow runner
detects `multi_agent.enabled: true` and routes the phase through the
orchestrator-workers executor rather than a single agent call.

---

##### H.9.5 — Tool Description Quality as First-Class Concern

Source: `sre-agent` — "Well-written tool descriptions are one of the
most important factors in agent effectiveness."

This validates and extends the skill library philosophy. Skills in the
harness ARE enriched tool descriptions. Each skill document should
follow a consistent structure:

```
# Skill: <name>
## Purpose           — one sentence: what this skill makes possible
## When to use       — specific triggers and phase context
## Tools available   — explicit list of tools this phase may call
## Rules             — what the agent MUST do
## Anti-patterns     — what the agent MUST NOT do
## Output contract   — what phase_complete.json must contain (mirrors YAML)
## Examples          — at least one worked example
```

The output contract section mirrors the `contract:` definition in
`workflow.defaults.yaml`. If they diverge, YAML takes precedence for
gate evaluation, but the skill document explains *why* each field
matters — which improves agent compliance.

**Action item:** Audit all 17 existing skill files against this
structure. Add the output contract section to each. This is a
documentation-only change but has direct impact on ContractEvaluator
pass rates. Track as a separate task alongside Phase C (eval pipeline).

---

**Acceptance criteria (Phase H — full)**

- `workflow_runner.py start --workflow feature-implementation` builds
  FSM topology correctly from YAML, prints phase sequence with model
  assignments, executor types, and new schema fields
- `workflow_runner.py resume` identifies current phase from SQLite and
  re-enters the FSM at the correct state
- FSM fires correct transition for all scenarios: gate pass, gate fail,
  human approval, retry, skip, REQUEST_CHANGES, HALT
- `ContractEvaluator` correctly passes/fails for all gate types:
  boolean, numeric, verdict, required fields
- `workflow.local.yaml` overrides applied for overridable phases;
  rejected with clear error for `overridable: false` phases
- `workflow.local.yaml.example` committed; `workflow.local.yaml`
  gitignored; pre-commit hook warns if staged
- `resolve_model('frontier')` returns correct model; falls back correctly
- Phase results written to both flat file and SQLite
- `human_approval: true` on `overridable: false` phases cannot be
  disabled via local overrides
- `git_ops.py` performs all Git operations correctly (see H.8)
- FSM exports a valid Mermaid state diagram
- `workflow_runner.py advance` with REQUEST_CHANGES re-enters
  implementation state correctly
- `transitions` added to `pyproject.toml`, passes `pip-audit`
- **H.9.1 Context compaction:** fires at `compact_at_pct` threshold;
  summary preserves all critical values across context reset
- **H.9.2 Hooks:** pre-tool hook fires before Bash/Write/Edit calls;
  post-tool hook records every tool use to `tool_uses` SQLite table
- **H.9.3 Output styles:** four style files created; `code-reviewer.md`
  includes evaluator-only instruction; ContractEvaluator pass rate
  improves for structured phases
- **H.9.4 Multi-agent audit:** orchestrator-workers pattern active for
  multi-persona-audit; parallel workers; synthesised risk report
- **H.9.5 Skill audit:** all 17 skill files have output contract section
  mirroring their `contract:` YAML definition

---

### Phase I — Harness Extraction & Portability
**Effort:** 3–4 days
**Closes:** T1-A-01, T1-A-02, T1-A-03, T1-A-04, T1-A-05, T1-A-06, T1-A-07

#### I.1 — Standalone harness repository (T1-A-01)

Extract the framework layer from Gym App into its own repository. The harness
becomes a dependency; Gym App becomes the first "project using the harness."
Separates generic framework files from project-specific config and workflows.

**Acceptance criteria:**
- Harness files live in a standalone repository
- Gym App references harness via a versioned install mechanism
- No project-specific rules exist in the harness repository itself

#### I.2 — Bootstrap install script (T1-A-02)

Create `bootstrap/install.py` — detects tech stack, copies framework files
into target project, scaffolds project config from templates, wires pre-commit
hooks, runs validation. Target: under 10 minutes from zero to working harness.

**Acceptance criteria:**
- `python bootstrap/install.py --project /path/to/new-project` completes in < 10 minutes
- All pre-commit hooks are wired in the target project on completion
- `bootstrap/validate.py` passes immediately after install

#### I.3 — Environment validation script (T1-A-03)

Create `bootstrap/validate.py` — confirms all required tools are installed
(git, Docker, poetry, gh CLI), pre-commit hooks are wired, validate.py scripts
pass, and regression runner returns clean. Also validates Docker daemon is
running and `GITHUB_TOKEN` is set with `repo:read` scope (prerequisites for
Phases E and F).

**Acceptance criteria:**
- Identifies missing Docker daemon as a FAIL (required for Phase E)
- Identifies missing or insufficient `GITHUB_TOKEN` as a FAIL (required for Phase F)
- Runs without error on a clean Gym App environment

#### I.4 — Config-driven architecture checks (T1-A-04)

Replace hardcoded Python/Clean Architecture rules in `architecture_checks.py`
with a config-driven rule set read from `.agent/config.yaml`. Any project can
define its own layer boundaries and forbidden patterns without code changes.

```yaml
# .agent/config/config.yaml — architecture section (addendum)
architecture:
  layers:
    - name: domain
      path: src/domain
      forbidden_imports: [src.infrastructure, src.presentation]
    - name: application
      path: src/application
      forbidden_imports: [src.infrastructure, src.presentation]
    - name: infrastructure
      path: src/infrastructure
      forbidden_imports: [src.presentation]
  forbidden_patterns:
    - pattern: "import requests"
      in_paths: [src/domain, src/application]
      message: "HTTP calls belong in infrastructure"
```

**Acceptance criteria:**
- `architecture_checks.py` reads all rules from config, nothing hardcoded
- Existing Gym App rules produce identical results before and after migration
- A new project can define custom layer boundaries without touching script code

#### I.5 — Two-layer review_context.md (T1-A-05)

Split `review_context.md` into:
- `.agent/review_context_universal.md` — framework-owned, generic invariants (committed in harness repo, never project-edited)
- `.agent/review_context.md` — project layer (user-maintained, project-specific patterns)

`ai_review.py` and `delivery_monitor.py` load and concatenate both. The
universal layer is never overwritten by session writes; only the project layer
receives injected CI failure context from Phase F's `delivery_monitor.py`.

**Acceptance criteria:**
- `ai_review.py` concatenates both layers for review
- `delivery_monitor.py` writes CI failure context to project layer only
- Universal layer is byte-for-byte unchanged after a full delivery cycle

#### I.6 — Universal + stack-pack skills (T1-A-06)

Split skills into:
- **Universal** — language-agnostic, always deployed: systematic-debugging, code-review, security-audit, architect, dba, and all Phase D delivery skills
- **Stack packs** — deployed based on detected tech stack: python-fastapi, node-express, go

The install script deploys universal skills to every project; stack pack
selection is driven by tech stack detection in `bootstrap/install.py`.

**Acceptance criteria:**
- Install script deploys universal skills to any project regardless of stack
- Stack pack selection is config-driven (not hardcoded)
- Phase D delivery skills (feature-branch, staging-deployment, uat-gate, ci-cd-monitoring) classified as universal

#### I.7 — Tool supplement generation (T1-A-07)

Install script generates `CLAUDE.md`, `GEMINI.md`, `.cursorrules` from
templates rather than requiring manual creation. Each is a thin shim pointing
at `.agent/UNIVERSAL_CONTEXT.md` (Phase J.1). Variables (project name, stack,
harness version) are substituted at install time.

**Acceptance criteria:**
- Generated `CLAUDE.md` passes existing harness pre-commit checks
- Template variables correctly substituted for project name and stack
- Regenerating does not overwrite project-specific additions made after install

---

### Phase J — Environment Legibility
**Effort:** 2 days
**Closes:** T1-B-01, T1-B-02, T1-B-03, T1-B-04, T1-B-05

#### J.1 — Universal context file (T1-B-01)

Create `.agent/UNIVERSAL_CONTEXT.md` as the single canonical context source.
`CLAUDE.md`, `GEMINI.md`, and `.cursorrules` become thin shims that reference
it. Eliminates three-copy drift risk across tool supplements.

**Acceptance criteria:**
- A change to `UNIVERSAL_CONTEXT.md` is visible to all three tool supplements
- Existing session startup behaviour is unchanged
- `CLAUDE.md` shrinks to a shim of < 20 lines after migration

#### J.2 — Harness versioning (T1-B-02)

Add `harness_version.txt` at framework root and `HARNESS_CHANGELOG.md`.
`init_session.py` logs the harness version with each session start.
`HarnessState.write_session_start()` (Phase A) extended with a
`harness_version` column in the `sessions` SQLite table.

**Acceptance criteria:**
- `harness_version.txt` is present and semver-formatted
- `sessions` table has `harness_version` column (additive migration to Phase A schema)
- `harness_health.py` includes harness version in the report header

#### J.3 — Onboarding workflow (T1-B-03)

`.agent/workflows/onboarding.md` — first-session workflow that:
1. Runs `bootstrap/validate.py` and reports environment health
2. Runs the full regression suite
3. Confirms all skill `validate.py` scripts pass
4. Runs `eval_runner.py` on available evals (Phase C)
5. Produces a "harness health at onboarding" baseline report written to `.agent/state/onboarding_baseline.json`

**Acceptance criteria:**
- Onboarding workflow completes without error on Gym App
- Baseline report written to `.agent/state/onboarding_baseline.json`
- Subsequent `harness_health.py` runs can compare against the baseline

#### J.4 — Skill deprecation mechanism (T1-B-04)

Add `status` field (`active` / `deprecated` / `experimental`) to each skill's
YAML frontmatter. `select_bdd_gate.py` and `skill_mapping.yaml` respect the
field. Deprecated skills are not loaded into the workflow runner context.
Phase D delivery skills should be created with `status: experimental` initially.

**Acceptance criteria:**
- `workflow_runner.py` skips deprecated skills without error
- `harness_health.py` reports skill status distribution
- At least one existing skill correctly marked deprecated

#### J.5 — Self-service skill authoring `/create-skill` (T1-B-05)

A workflow that scaffolds a new skill from a description: creates `SKILL.md`,
`validate.py`, `cases.csv`, and `eval.yaml` (Phase C format), then adds a
`skill_mapping.yaml` entry. Turns a 4-file manual process into a one-command
operation.

**Acceptance criteria:**
- `/create-skill` produces all four required files
- Generated skill passes the `architecture_checks.py` skill structure check
- Generated `eval.yaml` is valid against the Phase C eval schema

---

### Phase K — Reliability Additions
**Effort:** 2 days
**Closes:** T1-C-02, T1-C-03
*(T1-C-01 closed by Phase A.4)*

#### K.1 — Structured HITL approval queue (T1-C-02)

When an agent hits an escalation trigger that does not map to a named
human-gate phase (e.g. an unexpected mid-phase HALT, an architecture decision
requiring sign-off not anticipated in the workflow), it writes a structured
approval request to `.agent/state/pending_approvals.json`:

```json
{
  "id": "approval-20260510-001",
  "session_id": "feature-member-history-20260510",
  "phase_id": "implementation",
  "trigger": "ARCHITECTURE_DECISION_REQUIRED",
  "description": "Three valid migration strategies exist — human selection required.",
  "context_path": ".agent/state/pending_approvals/approval-20260510-001.md",
  "created_at": "2026-05-10T14:23:00",
  "approved": null,
  "approved_by": null,
  "approved_at": null
}
```

Human edits `approved: true` (or `false` with a reason). Agent checks for
unresolved approvals at session start before scanning roadmap items.

This is complementary to, not a replacement for, the WAIT_UAT sentinel
(Phase G). WAIT_UAT is for UAT sign-off; the approval queue is for mid-phase
escalations that don't fit a named workflow gate.

**Acceptance criteria:**
- Agent writes to `pending_approvals.json` on escalation trigger
- Session start checks for unresolved approvals before proceeding
- `harness_health.py` reports approvals pending > 2 days as WARN
- `HarnessState` records approval and resolution events to SQLite

#### K.2 — Harness health alerting to GitHub (T1-C-03)

If `harness_health.py` detects a CRITICAL recommendation card, automatically
create a GitHub issue tagged `[harness-critical]` via `gh issue create`.
Also creates issues for:
- WAIT_UAT sentinels older than 5 days (Phase G)
- Pending approvals older than 2 days (Phase K.1)
- Security scan HALT not resolved within 24 hours (Phase F)

Idempotent — checks for an existing open issue with the same trigger key
before creating a new one to avoid duplicates.

**Acceptance criteria:**
- CRITICAL health condition creates a GitHub issue with trigger detail
- Re-running `harness_health.py` does not create duplicate issues
- Issue body includes a link to the specific health report entry

---

### Phase L — Observability & Intelligence
**Effort:** 2 days
**Closes:** T1-D-03
*(T1-D-01/D-02 closed by Phase A; T1-D-04 closed by Phase H.3)*

#### L.1 — Dream phase distillation (T1-D-03)

Weekly batch script `src/scripts/distill_dream.py`:

1. Reads all `session_ledger.md` entries since last run date
2. Reads `governance_audit.jsonl` for violations and escalation patterns
3. Reads Phase F failure reports in `.agent/state/ci_failures/` for recurring CI failure types
4. Calls Claude API (efficient model) to extract recurring patterns
5. Proposes additions to relevant skill files as unified diffs
6. Writes proposals to `.agent/state/dream_proposals/<date>/`
7. Creates a GitHub issue (Phase K.2 mechanism) listing proposals for human review

The distillation prompt explicitly targets outer loop failure patterns:
- Staging deployment issues that recur across multiple features
- UAT findings that repeat (signal of spec gaps, not implementation bugs)
- CI failure categories the agent consistently takes > 1 attempt to fix
- Escalation triggers that fire more than twice in the same month

**Acceptance criteria:**
- `distill_dream.py` runs without error on 4+ weeks of session ledger data
- At least 1 genuine proposal generated from existing Gym App session history
- Proposals are valid unified diffs applicable to target skill files
- GitHub issue created with proposal summary for human review
- Runs are idempotent — second run on same data produces same proposals

---

### Phase M — Documentation & Shareability
**Effort:** 2–3 days
**Closes:** T1-E-01, T1-E-02, T1-E-03, T1-E-04, T1-E-05

#### M.1 — Getting-started guide (T1-E-01)

`docs/getting-started.md` — install to first AI review gate firing in under
10 minutes. Written for someone who didn't build the harness. References the
Phase I bootstrap install script as the entry point.

#### M.2 — Configuration reference (T1-E-02)

`docs/configuration.md` — every field in `config.yaml`, `workflow.schema.yaml`,
`workflow.defaults.yaml`, and `workflow.local.yaml.example` documented with
type, default, and example. Required for Phase H's YAML surfaces to be usable
by anyone other than the original author.

#### M.3 — Customisation guide (T1-E-03)

`docs/customisation.md` — how to:
- Add project-specific invariants to the project layer `review_context.md` (Phase I.5)
- Create custom skills using `/create-skill` (Phase J.5)
- Configure custom architecture checks in `config.yaml` (Phase I.4)
- Write `workflow.local.yaml` personal overrides (Phase H.5)
- Add a new stack-pack skill bundle (Phase I.6)

#### M.4 — Refined AISDLC bootloader (T1-E-04)

Update the bootloader document to:
- Reference the standalone harness repository (Phase I.1)
- Include `workflow_runner.py status` invocation at session start (Phase H)
- Include onboarding workflow reference for first sessions (Phase J.3)
- Reflect the two-layer `review_context.md` structure (Phase I.5)
- Include harness version logging at session start (Phase J.2)

#### M.5 — Harness README (T1-E-05)

Repository-level README covering: what this is, 5-minute install (link to M.1),
the "8 interruptions → 3 checkpoints" value proposition, and links to the
full documentation suite.

**Acceptance criteria (Phase M):**
- Getting-started guide tested end-to-end on a fresh machine
- Configuration reference covers all fields introduced in Phases H, I, J
- Customisation guide tested by adding 1 custom skill and 1 local override
- Bootloader correctly invokes `workflow_runner.py` at session start
- README renders correctly on GitHub

---

## 5. Merge Gates

Before merging `feature/scaffold-v4-outer-loop` to `devops`:

- [ ] All pre-commit gate chain passes (existing gates)
- [ ] `harness_state.py` — mypy clean, no direct flat file writes remain in existing scripts
- [ ] `harness.db` — schema creates cleanly, migration runner idempotent
- [ ] `deploy_staging.py` — end-to-end staging deployment completes in CI
- [ ] `delivery_monitor.py` — integration test against a known-passing branch
- [ ] `generate_uat_checklist.py` — produces valid output for 3 existing branches
- [ ] `eval_runner.py` — 3 skills evaluated without error
- [ ] `drift_detector.py` — runs on full codebase without crash
- [ ] All new skill files pass skill structure validator
- [ ] `workflow_runner.py` — FSM builds correct topology for feature-implementation
- [ ] `workflow_runner.py` — all transition scenarios tested: pass, fail, retry, skip, halt, REQUEST_CHANGES
- [ ] `ContractEvaluator` — all gate types tested: boolean, numeric, verdict, required fields
- [ ] `git_ops.py` — branch, commit, merge, conflict detection all tested
- [ ] `workflow.defaults.yaml` — passes schema validation
- [ ] `workflow.local.yaml` — gitignored; `.example` file committed
- [ ] `overridable: false` phases reject local overrides (validated)
- [ ] `workflow_runs` and `workflow_phase_results` tables in SQLite schema
- [ ] `transitions` dependency passes `pip-audit`
- [ ] Architecture checks pass (no new layer violations)
- [ ] Test suite: 1,492 tests, ≥ 80% coverage

**Phase I — Harness Extraction & Portability**
- [ ] `bootstrap/install.py` completes on a new project in < 10 minutes
- [ ] `bootstrap/validate.py` detects missing Docker and `GITHUB_TOKEN`
- [ ] `architecture_checks.py` fully config-driven; Gym App rules unchanged
- [ ] `review_context_universal.md` survives a full delivery cycle unmodified
- [ ] Stack-pack skill classification confirmed for all existing skills
- [ ] Generated `CLAUDE.md` passes pre-commit checks

**Phase J — Environment Legibility**
- [ ] `UNIVERSAL_CONTEXT.md` in place; `CLAUDE.md` reduced to shim
- [ ] `sessions` table has `harness_version` column (additive migration)
- [ ] Onboarding workflow completes without error; baseline JSON written
- [ ] Skill deprecation `status` field present in all skill frontmatter
- [ ] `/create-skill` produces four valid files for a test skill

**Phase K — Reliability Additions**
- [ ] `pending_approvals.json` written on escalation trigger
- [ ] Session start blocks on unresolved approvals
- [ ] `harness_health.py` creates GitHub issue on CRITICAL without duplicates

**Phase L — Observability & Intelligence**
- [ ] `distill_dream.py` produces at least 1 genuine proposal from existing ledger
- [ ] Proposals are valid unified diffs
- [ ] GitHub issue created with proposal summary; run is idempotent

**Phase M — Documentation & Shareability**
- [ ] Getting-started guide tested end-to-end on a fresh machine
- [ ] Configuration reference covers all fields from Phases H, I, J
- [ ] Customisation guide tested: 1 custom skill + 1 local override
- [ ] Bootloader document updated to invoke `workflow_runner.py` at session start
- [ ] README renders correctly on GitHub

---

## 6. Implementation Order and Dependencies

```
Phase A (harness_state.py + SQLite schema)
    └── Phase B (drift_detector.py — uses HarnessState for output)
    └── Phase C (eval_runner.py — uses HarnessState for results)
    └── Phase H (workflow_runner.py — uses SQLite workflow_runs table)

Phase H (workflow config engine)
    ├── H.1 + H.2 — YAML schema + defaults (no dependencies)
    ├── H.3 — model registry (no dependencies)
    ├── H.4 — FSM runner (depends on A for SQLite, H.2 for YAML)
    ├── H.5 — local overrides (depends on H.2)
    ├── H.6 — SQLite tables (depends on A for migration runner)
    ├── H.7 — ContractEvaluator (depends on H.4)
    └── H.8 — git_ops.py (depends on H.4 for state writing)

Phase D (outer loop skill files — now defined via H.2 executor:tool entries)
    └── Phase E (deploy_staging.py — referenced as tool in H.2)
    └── Phase G (UAT gate + generate_uat_checklist.py)
        └── Phase F (delivery_monitor.py — final outer loop piece)
```

**Recommended execution order:**
1. Phase A (foundation — SQLite schema, HarnessState)
2. Phase H.1–H.3 (YAML schema, defaults, model registry — no code yet)
3. Phase H.4 + H.7 (FSM runner + ContractEvaluator — core engine)
4. Phase H.8 (git_ops.py — skeleton Git control)
5. Phase H.5 + H.6 (local overrides + SQLite tables)
6. Phase D (outer loop skill files)
7. Phase E (staging deployment)
8. Phase G (UAT gate)
9. Phase F (CI/CD monitor)
10. Phase B (drift detection — independent)
11. Phase C (eval pipeline — independent)
12. Phase I (harness extraction — depends on A, C, H being stable)
13. Phase J (environment legibility — depends on I.1 standalone repo)
14. Phase K (reliability additions — depends on A for SQLite, G for UAT sentinel)
15. Phase L (dream phase distillation — depends on A, F, K.2 for GitHub alerting)
16. Phase M (documentation — depends on all prior phases being stable)

---

## 7. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| GitHub Actions API rate limiting | Low | Use conditional polling (only poll when push event detected) |
| Docker staging build failures blocking development | Medium | `--check-only` flag allows health check without rebuild |
| WAIT_UAT sentinel forgotten, blocking all future sessions | Medium | `harness_health.py` flags sentinels > 5 days old |
| SQLite DB corruption on concurrent write | Low | Single-writer design; SQLite WAL mode enabled |
| Eval runner false positives blocking skill library | Low | WARN-only in gate chain; human review before blocking |
| Agent auto-fixing security scan failures | None | Hard rule: security failures always write HALT |
| Efficient model producing lower-quality output on complex phases | Medium | Frontier model assigned to all reasoning/review phases; efficient only for mechanical execution |
| Ollama local model unavailable | Low | `fallback: efficient` in model registry; runner transparently degrades |
| workflow.local.yaml accidentally committed | Low | Gitignored; pre-commit hook warns if file is staged |
| Human approval phases disabled via local override | None | Validation in `workflow_runner.py` rejects overrides of `human_approval: true` phases |
| GitHub MCP server requires Docker (cicd-monitor phase) | Medium | Document Docker as a dependency for outer loop; fallback to `delivery_monitor.py` custom script if Docker unavailable |
| Context overflow mid-phase (implementation, QA) | Medium | `context_budget` fields + compaction prompt; server-side compaction for Opus 4.6 |
| Output styles not loaded (missing `setting_sources`) | Low | Document `setting_sources: ["project"]` requirement; add to runner invocation checklist |
| Orchestrator-workers adds latency to multi-persona-audit | Low | Parallel workers reduce wall time vs sequential; acceptable tradeoff for richer output |

---

## 8. Success Criteria

The feature is complete when:

**Outer loop delivery (Phases D–G):** The agent can, without human initiation
of individual steps, take a completed inner-loop commit and:
1. Generate a UAT checklist and release notes
2. Deploy to Docker staging
3. Run the full test suite against staging
4. Surface the UAT checklist for human review (WAIT_UAT sentinel)
5. After human sign-off, merge the feature branch to devops
6. Monitor GitHub Actions for the devops branch
7. Fix lint and test failures autonomously
8. Escalate security failures with HALT

**Workflow configurability (Phase H):** A developer with different
preferences can create `workflow.local.yaml` and:
1. Disable optional phases (e.g. multi-persona-audit) without touching committed files
2. Change the architecture options count from 3 to 1
3. Assign the local Qwen3 model to implementation phases to reduce API cost
4. Have those preferences persist across sessions via SQLite run state

**Mix-of-models (Phase H model registry):** The harness uses:
1. A frontier model for all planning, architecture, requirements, and review phases
2. An efficient model for all implementation, testing, deployment, and monitoring phases
3. Model assignments are visible in `harness_health.py` cost report
4. A single change in `config.yaml` updates model selection across all workflows

**Human involvement is required at exactly two points:**
- UAT sign-off (delete sentinel)
- Security failure resolution (always)

Everything else is governed, gated, logged, and model-assigned by the scaffold.

**Harness portability (Phase I):** The harness can be installed into a new
project via `bootstrap/install.py` in under 10 minutes. Architecture checks
are fully config-driven. The universal and project review context layers are
cleanly separated — `delivery_monitor.py` writes into the project layer only.

**Environment legibility (Phase J):** A single change to `UNIVERSAL_CONTEXT.md`
propagates to all tool supplements. Harness version is logged with every
session start and visible in `harness_health.py`. A new team member's first
session runs the onboarding workflow and produces a baseline health report.
Deprecated skills are not loaded. New skills can be scaffolded with one command.

**Reliability additions (Phase K):** Mid-phase escalation triggers are
structured, human-resolvable, and tracked in SQLite — not binary HALT/hope.
CRITICAL health conditions, stale UAT sentinels, and unresolved security
failures automatically create GitHub issues without human polling.

**Observability loop (Phase L):** The outer loop improves over time. Recurring
staging deployment failures, repeated UAT findings, and persistent CI failure
patterns are surfaced weekly as proposed skill improvements — not silently
accumulated. The distillation run is idempotent and GitHub-visible.

**Documentation complete (Phase M):** A developer unfamiliar with the harness
can install it, configure a personal `workflow.local.yaml`, add a custom skill,
and understand every config field — without reading the implementation source.
