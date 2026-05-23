# Workflow Engine Design

> **Status**: Future-state design for v1.3.0+ workflow automation.
> **Source**: Extracted from [RFC-002 — Scaffold V4: Outer Loop Delivery Orchestration](../archive/RFC-002-outer-loop-delivery.md), Phases H.1, H.2, H.4, H.7.
> **Extracted**: 2026-05-22

---

## Overview

This document describes a data-driven workflow engine that replaces prose-driven
agent interpretation of workflow files with machine-readable phase definitions,
model assignments, completion contracts, and FSM-backed state transitions.

The analogy is a Telco BSS CDR mediation system: stream types (workflow types)
map to step sequences (phases) via configuration tables, with per-step config
and enabled/disabled flags. The Java engine reads the tables; the workflow
runner reads the YAML.

**Four components**:
1. **Workflow Schema** (`workflow.schema.yaml`) — the universal contract all workflow YAML must conform to
2. **Workflow Defaults** (`workflow.defaults.yaml`) — committed base configuration with model assignments and phase contracts
3. **Workflow Runner** (`workflow_runner.py`) — FSM-backed phase transition engine
4. **Contract Evaluator** (`ContractEvaluator`) — gate enforcement mechanism

---

## 1. Workflow Schema (`workflow.schema.yaml`)

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

---

## 2. Workflow Defaults (`workflow.defaults.yaml`)

Extracts the current `feature-implementation.md` step sequence into
machine-readable YAML with model assignments, executor types, phase
completion contracts, and skeleton Git actions. The prose workflow files
remain as documentation and context for the agent within each phase —
they are not replaced, they are governed.

### 2.1 Feature Implementation (14 phases)

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
```

### 2.2 Bug Fix (7 phases)

```yaml
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
```

### 2.3 Hotfix (7 phases, stricter gates)

```yaml
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

### 2.4 Design Decisions Encoded in Workflow Defaults

| Decision | Rationale |
|----------|-----------|
| Adversarial review uses `context: clean` | Fresh context window prevents session bias from influencing the review |
| Adversarial review has `disallowed_tools: [Bash, Write, Edit, Task, WebSearch]` | Reviewer is read-only — pure evaluation, no execution |
| Implementation phase has `max_attempts: 3` | Allows retry on gate failure before halting |
| Hotfix requires `human_approval: true` on adversarial review | Stricter oversight for emergency changes |
| Bug-fix workflow skips UAT/staging entirely | Inner loop only — faster path for known issues |
| `overridable: false` on branch creation, adversarial review, commit, merge, UAT gate | Critical governance phases cannot be disabled by personal preferences |

---

## 3. Workflow Runner (`workflow_runner.py`) — FSM-Backed Phase Transition Engine

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

### 3.1 FSM State Topology for `feature-implementation`

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

### 3.2 Dependencies

```toml
[tool.poetry.dependencies]
transitions = "^0.9"
```

### 3.3 State Persistence

Run state is written to both:
- `.agent/state/workflow_runs/<run_id>.json` (flat file, source of truth)
- `harness.db → workflow_runs` table (SQLite, queryable)

---

## 4. Contract Evaluator — Gate Enforcement

The phase completion contract is the interface between the skeleton and
the agent. Every agent-executed phase must write a structured JSON file
to `.agent/state/phase_results/<run_id>/<phase_id>.json` as its final
act before returning control to the skeleton. The skeleton reads this
file, evaluates it against the phase's `contract:` definition in
`workflow.defaults.yaml`, and fires the appropriate FSM transition.

### 4.1 Contract Schema

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

### 4.2 Evaluator Implementation

```python
class ContractEvaluator:
    """
    Evaluates a phase_complete.json against a phase contract definition.
    Returns True (gate pass) or False (gate fail) with structured reason.
    """

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

### 4.3 Bootloader Integration

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
