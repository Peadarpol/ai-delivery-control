# Workflows Overview

The framework provides 18 named workflows covering every major task type in software delivery. Workflows are state machines—agents must progress through phases in order and cannot skip or backtrack without user instruction.

---

## Quick Routing Matrix

| Task Type | Workflow | Time | Phases |
|-----------|----------|------|--------|
| New feature request | `/feature-implementation` | 4-8 hrs | 6 phases + multi-persona audit |
| Production bug | `/bug-fix` | 1-2 hrs | 4 phases (reproduce, fix, test, close) |
| Architecture decision | `/architect` | 2-3 hrs | Design options with ADRs |
| Schema/migration | `/dba` | 1-4 hrs | Safety checks + migration strategy |
| Security concern | `/security` | 1-3 hrs | Threat modeling + remediation |
| Performance issue | `/perf` | 2-4 hrs | Profiling + optimization + benchmarks |
| Tests only | `/qa` / `/test-engineer` | 1-2 hrs | BDD scenarios + test coverage |
| Release/changelog | `/release` | 1 hr | Version bump + changelog |
| CI/CD pipeline | `/devops` | 1-2 hrs | Pipeline analysis + fixes |
| Infrastructure | `/infrastructure` | 2-4 hrs | IaC review + safety gates |
| Deployment | `/deploy` | 30-60 min | Pre-flight + rollout |
| Business analysis | `/business-analyst` | 1-2 hrs | Requirements → BDD scenarios |
| Spec → tasks | `/project-manager` | 30 min | Sprint task backlog synthesis |
| Code review | `/code-reviewer` | 1-2 hrs | Multi-pass adversarial review |
| UX design | `/ux` | 1-3 hrs | Design spec + accessibility |
| Technical writing | `/technical-writer` | 1-2 hrs | API docs, runbooks, guides |
| Evaluation pipeline | `/eval-pipeline` | 1 hr | Golden dataset + regression tests |
| Onboarding | `/onboarding` | 30 min | New developer/project setup |

---

## Workflow Categories

### Delivery Workflows (4)

**Purpose**: Execute requirements end-to-end

- **`/feature-implementation`** — End-to-end feature delivery (6 phases)
  - Phase 0: Spec quality gate
  - Phase 1: Requirements analysis
  - Phase 2: Architecture design
  - Phase 2.5: Multi-persona audit
  - Phase 3: Implementation
  - Phase 4: Acceptance & PR

- **`/bug-fix`** — Reproduce → fix → verify (4 phases)
  - Phase 1: Reproduction & diagnosis
  - Phase 2: Implementation (TDD)
  - Phase 3: Regression testing
  - Phase 4: Closure

- **`/dba`** — Schema/migration safety (3 phases)
  - Phase 1: Migration analysis
  - Phase 2: Implementation
  - Phase 3: Verification & rollback strategy

- **`/qa` / `/test-engineer`** — Test coverage & BDD (2 phases)
  - Phase 1: Test planning
  - Phase 2: Implementation & verification

### Architecture & Design (3)

**Purpose**: Make informed design decisions

- **`/architect`** — Architecture decisions with 3 options
  - Generates ADRs for each option
  - C4 diagrams
  - Pros/cons + confidence scores

- **`/security`** — Threat modeling & remediation
  - Threat analysis
  - Remediation implementation
  - Security testing

- **`/ux`** — Design spec + accessibility review
  - Design specifications
  - Accessibility compliance
  - Interaction patterns

### Infrastructure & DevOps (3)

**Purpose**: Infrastructure and deployment safety

- **`/devops`** — CI/CD pipeline fixes
  - Pipeline analysis
  - Fix implementation
  - Deployment verification

- **`/infrastructure`** — IaC review & provisioning
  - Infrastructure analysis
  - Terraform/CloudFormation review
  - Safety gates

- **`/deploy`** — Controlled deployment
  - Pre-flight checks
  - Rollout strategy
  - Rollback plan

### Quality & Performance (2)

**Purpose**: Non-functional requirements

- **`/perf`** — Performance optimization
  - Profiling & bottleneck analysis
  - Optimization implementation
  - Benchmark verification

- **`/eval-pipeline`** — Evaluation framework
  - Golden dataset management
  - Regression test suite
  - Metric tracking

### Planning & Management (3)

**Purpose**: Convert requirements to work

- **`/business-analyst`** — Requirement intake → BDD
  - Stakeholder interviews
  - User story extraction
  - Gherkin scenario generation

- **`/project-manager`** — Spec → sprint tasks
  - Task backlog synthesis
  - Dependency analysis
  - Effort estimation

- **`/code-reviewer`** — Multi-pass code review
  - Architecture review
  - Security review
  - Test coverage review

### Support Workflows (2)

**Purpose**: Special tasks

- **`/technical-writer`** — API docs, runbooks, guides
  - OpenAPI documentation
  - Runbook generation
  - User guide authoring

- **`/onboarding`** — Developer/project setup
  - Environment setup
  - Repository initialization
  - Framework installation

---

## Common Workflow Patterns

All workflows share structural patterns:

### Phase Structure

1. **Pre-flight**: Read decision logs, verify preconditions
2. **Main**: Execute the core task
3. **Validation**: Run tests/checks
4. **Closure**: Update state, mark complete

### Escalation Triggers

Each workflow stops if:
- **Destructive scope** — deleting multiple files, dropping tables
- **Access control** — modifying auth/RBAC
- **Deployment** — pushing to production
- **Context loss** — blocked at same state 2+ times

### Multi-Persona Audits

Complex workflows (feature-implementation, devops) engage multiple personas:
- Product manager
- Database administrator
- QA engineer
- Security specialist
- Infrastructure engineer

Each persona verifies one aspect before proceeding.

---

## How to Read a Workflow

Each workflow file (`.agent/workflows/{name}.md`) contains:

1. **Trigger** — When to use this workflow
2. **Mindset** — Key principles
3. **Phase N** — Steps, skills, validations
4. **Checkpoints** — Where human approval is required
5. **Troubleshooting** — Common blocks and recovery

**Example: `/feature-implementation`**
```
## Phase 0: Verify Specification
**Skill**: /project-manager
- Run spec quality gate
- If fails, halt immediately

## Phase 1: Requirements Analysis
**Skill**: /business-analyst
- Convert req to user stories
- Generate Gherkin scenarios

**User Checkpoint** (15 min):
- [ ] Review AI-generated stories
- [ ] Confirm no hallucinations
- [ ] Approve spec status
```

---

## When Workflows Conflict

Sometimes a task could use multiple workflows. Choose based on **primary objective**:

| Objective | Workflow |
|-----------|----------|
| Implement feature end-to-end | `/feature-implementation` |
| Fix production issue | `/bug-fix` |
| Review code quality | `/code-reviewer` |
| Improve performance | `/perf` |
| Fix schema problem | `/dba` |

If unclear, ask the human.

---

## Workflow Composition

Workflows can be composed for complex tasks:

```
Situation: "Add multi-tenancy to the codebase"

1. Start `/architect` → Design multi-tenancy pattern
2. In Phase 2: Propose migration strategy
3. Pivot to `/dba` → Execute schema migration
4. Pivot to `/feature-implementation` → Add tenant-awareness to features
5. End with `/security` → Verify data isolation
```

---

## Workflow State & Session Continuity

Each workflow maintains state across sessions:

- Active workflow name is stored in `session.json`
- Current phase is tracked
- All decisions are logged in `decisions_log.md`
- On session resume, agent reads state and picks up at the blocked phase

---

## See Also

- **[Governance Rules](Governance-Rules)** — Escalation triggers that stop workflows
- **[Quick Reference](Quick-Reference)** — Workflow router table
- **[Customization](Customization)** — Creating custom workflows (not yet supported)

---

*For detailed walkthrough of any workflow, see `.agent/workflows/{name}.md` in the framework repo.*