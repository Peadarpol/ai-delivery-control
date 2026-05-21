---
description: Workflow for executing behavioral and regression evaluations on agentic skills
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Workflow for executing behavioral and regression evaluations on agentic skills
---

# /eval-pipeline - Behavioral & Regression Evaluation Workflow

## Trigger
Use when:
1.  A new skill is added or modified.
2.  A critical bug is fixed (regression seeding).
3.  Final validation is required before a PR merge.
4.  User explicitly requests `/eval-pipeline`.

## Mindset
- **Evidence-Based**: Trust no claim of "fixed" without a passing regression evaluation.
- **Deterministic-First**: Prioritize golden dataset regressions over probabilistic LLM evals.
- **Behavioral-Aware**: Evaluate the *way* the agent worked (TDD, governance) alongside the code produced.

---

## Phases

### Phase 1: Environment Readiness **Skill**: /devops-cicd
1.  **Status Check**: Ensure local DB is seeded and API is running if integration evals are required.
2.  **Path Verification**: Ensure `.agent/evals/regression_evals.jsonl` exists.

### Phase 2: Regression Execution (Blocking) **Skill**: /test-engineer
1.  **Execute**: `python .agent/scripts/eval_runner.py --regression-only`
2.  **Constraint**: Any failure in this phase is a BLOCKER. Do not proceed to skill evaluation until regressions pass.
3.  **Action**: If failure found, trigger `/systematic-debugging` on the failing case.

### Phase 3: Skill Evaluation (Non-Blocking/Advisory) **Skill**: /test-engineer
1.  **Identify Skill**: Determine which skill was primarily used in the current session.
2.  **Execute**: `python .agent/scripts/eval_runner.py --skill <skill-name>`
3.  **Review**: Examine `cases.csv` and `rubric.md` output.
4.  **Action**: If rubric score is < 80%, identify one concrete process improvement (Kaizen) for the next session.

### Phase 4: Audit & Synthesis **Skill**: /project-manager
1.  **Record Results**: Append a summary of eval results to `.agent/state/active_context.md`.
2.  **Update Traceability**: If a regression was cleared, update `docs/testing/REQUIREMENTS_TRACEABILITY.md`.

---

## Escalation Triggers
- **Deterministic Failure**: If a regression that passed 5 minutes ago now fails, escalate to human immediately (potential flaky test or state corruption).
- **Empty Dataset**: If `--regression-only` returns 0 cases, escalate to human (gate is hollow).
