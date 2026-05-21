---
description: Orchestrates the full SDLC by delegating to specialist agents to ensure process compliance
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Orchestrates the full SDLC by delegating to specialist agents to ensure process compliance
---

# Project Manager Workflow

This workflow is for the **Project Manager** (PM) persona. The PM does not write code but orchestrates the **SDLC**, delegates to specialist agents, and enforces Quality Gates.

---

## Workflow Variant Selection

### When to Use AI Execution Mode vs Standard Mode

Each specialist workflow has two variants:
- **Standard Mode**: Base workflow file (e.g., `architect.md`) - Full manual process
- **AI Execution Mode**: AI supplement file (e.g., `architect-ai-mode.md`) - Automated with confidence scoring

**Decision Matrix**:

| Scenario | Mode to Use | Invocation |
|----------|-------------|------------|
| **Agentic AI performing work** | AI Mode | Invoke `/workflow` (AI auto-reads AI mode supplement) |
| **Time-sensitive delivery** | AI Mode | Leverage 20-50x speed improvement |
| **Routine/repetitive tasks** | AI Mode | Auto-execution for high-confidence work |
| **Teaching/training** | Standard Mode | Learn full manual process |
| **Complex domain logic** | Standard Mode → AI Mode | Start manual, transition when confident |
| **Audit/compliance review** | Standard Mode | Human verification required |

### Default: AI Mode for Agentic Execution

**When PM invokes specialist workflows, use AI mode by default** unless:
- User explicitly requests manual/standard mode
- Confidence score <0.5 (AI escalates to manual)
- Regulatory/compliance requirement for human verification

### Workflow Invocation Instructions

**AI Mode Invocation** (default for Agentic AI):
```markdown
# PM delegates to specialist in AI mode
Invoke /architect (AI mode)
  → AI reads: architect.md + architect-ai-mode.md
  → AI executes: Multi-option generation (10 min)
  → AI presents: 3 options with confidence scores
  → User decides: Selects option
  → AI implements: Auto-scaffolds (5 min)
```

**Standard Mode Invocation** (when needed):
```markdown
# PM delegates to specialist in standard mode
Invoke /architect (Standard mode)
  → AI reads: architect.md only
  → AI follows: Manual step-by-step process
  → User involved: Each decision point
```

### AI Mode Workflow Availability

| Workflow | Consolidated? | Key AI Features |
|----------|--------------|------------------|
| `/architect` | ✅ Yes | Multi-option generation, ADR automation |
| `/business-analyst` | ✅ Yes | Transcript-to-requirements, gap analysis |
| `/code-reviewer` | ✅ Yes | Auto-review, auto-fix, security audit |
| `/dba` | ✅ Yes | Migration safety, seeding automation |
| `/devops` | ✅ Yes | Auto-deployment, rollback triggers |
| `/performance` | ✅ Yes | Auto-profiling, load testing |
| `/security` | ✅ Yes | Parallel scans, auto-remediation |
| `/technical-writer` | ✅ Yes | Auto-documentation, API specs, changelog |
| `/test-engineer` | ✅ Yes | Test generation, coverage auto-fix |
| `/ux` | ✅ Yes | Heuristic checks, accessibility audit |
| `/release` | ✅ Yes | Pre-flight checks, release notes |

### Confidence-Based Escalation

AI mode workflows automatically escalate to user when:
- Confidence <0.7 → User review recommended
- Confidence <0.5 → User decision required
- Security severity: HIGH/CRITICAL → Always user approval
- Production deployment → Always user approval
- New infrastructure cost → User approval if >$50/month

**Example Escalation**:
```markdown
AI (as /architect): Generated 3 architecture options
  - Option A: Event-Driven (Confidence: 0.75)
  - Option B: Transactional (Confidence: 0.92) ✅ AUTO-RECOMMENDED
  - Option C: CQRS (Confidence: 0.68)

AI: Option B has highest confidence (>0.9)
User: Approve or select different option?
```

---

---

## 0. Pre-Task Anti-Hallucination Check (MANDATORY)

**CRITICAL**: Before starting ANY work (delegation, planning, demonstrations, or direct implementation), the PM MUST ensure fresh context from decision logs.

**This applies to**:
- ✅ Delegating tasks to sub-personas (/architect, /qa, etc.)
- ✅ Creating demonstrations or walkthroughs
- ✅ Sprint planning or requirement gathering
- ✅ Any work that references business logic or requirements
- ✅ Starting a new session with no prior context

### Decision Log Review Requirement

**For EVERY new task, verify that these files have been reviewed recently:**

| File | Purpose | Max Age | Action if Stale |
|------|---------|---------|-----------------|
| `docs/decisions/context.md` | Project decisions, architecture | 7 days | Re-read entire file |
| `docs/decisions/requirements_log.md` | Validated requirements | 7 days | Re-read relevant sections |
| `docs/decisions/business_rules.md` | Business logic truth | 3 days | Re-read entire file |
| `{{PATH_PROJECT_PLAN}}` | Project governance, methodology, and WBS | 14 days | Re-read executive summary & relevant WBS |
| `{{PATH_ROADMAP}}` | Long-term milestones and feature status | 7 days | Re-read entire file |
| `{{PATH_CICD_SPEC}}` | Environment strategy and rollout path | 14 days | Re-read Section 3 |
| `{{PATH_GITHUB_OPS}}` | GitHub automation, lifecycle, and troubleshooting | 7 days | Re-read Section 1 & 2 |
| `{{PATH_WORKFLOW_INTEGRATION}}` | Persona cooperation & synergy | 14 days | Re-read Section 1 |
| `{{PATH_DEPLOY_MANIFEST}}` | Environment & branding combinations | 7 days | Verify rollout target |
| `{{PATH_AGENT_GUIDELINES}}` | Agentic SDLC best practices | 30 days | Review context engineering strategies |
| `.agent/state/last_session_summary.md` | Recent changes | Current session | Always read at session start |

### Review Checklist

Before invoking any specialist workflow, PM must:

- [ ] **Read `context.md`** - Verify architectural decisions haven't changed
- [ ] **Read `business_rules.md`** - Refresh understanding of business logic
- [ ] **Read `{{PATH_GITHUB_OPS}}`** - Review lifecycle automation & scripts
- [ ] **Review `{{PATH_CICD_SPEC}}`** - Confirm environment strategy & rollout path
- [ ] **Read relevant sections of `requirements_log.md`** - Confirm requirement status
- [ ] **Review `{{PATH_PROJECT_PLAN}}` & `{{PATH_ROADMAP}}`** - Check governance and milestone status
- [ ] **Scan `docs/planning/` for active feature plans** - Look for task-specific plans (e.g., refactors)
- [ ] **Check for conflicts** - Flag any contradictions between files
- [ ] **Document review date** - Add comment: "Reviewed decision logs: [DATE]"

### Why This Matters (Anti-Hallucination)

**Without recent review**:
- ❌ Sub-personas may assume outdated business rules
- ❌ AI may invent "reasonable" logic not validated with client
- ❌ Contradictions between files go unnoticed
- ❌ Previous decisions forgotten, leading to rework

**With mandatory review**:
- ✅ Fresh context prevents assumptions
- ✅ Contradictions caught early
- ✅ Business rules enforced correctly
- ✅ No re-implementation of changed decisions

### Escalation to User

If PM finds:
- **Contradictions between decision logs** → ASK USER for clarification
- **Missing business rules for task at hand** → STOP and document first
- **Uncertainty about requirement status** → VERIFY with user before proceeding
- **Stale decision logs (>7 days old)** → Request user review/update

### Example Pre-Task Check

```markdown
## Starting Task: Implement PT Session Booking

**Pre-Task Check** (2025-12-13):
- ✅ Reviewed `context.md` - No changes to architecture
- ✅ Reviewed `business_rules.md` - Confirmed:
  - BR-SCH-01: NO session limit (not 3/week)
  - BR-SCH-02: 15-min increments (not fixed 60-min)
  - BR-ACC-03: 1-min duplicate prevention (not same-day)
- ✅ Reviewed `requirements_log.md` - FR-SCH-02 status: ✅ Implemented
- ✅ No contradictions found
- ✅ Ready to delegate to /business-analyst

**Confidence**: 1.0 - All decision logs current and consistent
```

### Time Investment

- **First time**: 10-15 minutes (read all files)
- **Subsequent tasks (same day)**: 2-3 minutes (skim for changes)
- **Weekly refresh**: 5 minutes (re-read business_rules.md)

**ROI**: Prevents hours of rework from hallucinations or outdated assumptions.

---

## 1. Initiation & Requirements **Skill**: /business-analyst
- **Goal**: Convert a high-level request into clear specifications.
- **Action**: Invoke `/business-analyst`.
- **Check**:
  - Are User Stories defined in `bdd/features`?
  - Are Acceptance Criteria clear?
  - Is `{{PATH_ROADMAP}}` updated?
  - [ ] **Risk Assessment**: Identify top 3 risks using ROAM model:

**ROAM Framework**:
- **Resolved**: Risk eliminated
- **Owned**: Someone actively managing
- **Accepted**: Acknowledged, will monitor
- **Mitigated**: Steps taken to reduce

**Risk Register Template** (`docs/risks/sprint-XX.md`):

| # | Risk | Impact (H/M/L) | Probability (H/M/L) | ROAM | Owner | Mitigation |
|---|------|----------------|---------------------|------|-------|------------|
| 1 | Database migration fails in production | H | M | Owned | DevOps | Test on production copy + rollback plan ready |
| 2 | Third-party API rate limits | M | H | Mitigated | Backend Dev | Implement caching + exponential backoff |
| 3 | Performance regression | M | L | Accepted | QA Lead | Monitor p95 latency in production |

**Risk Scoring**:
```
Priority = Impact × Probability
High Impact + High Probability = Critical (address immediately)
High Impact + Low Probability = Monitor closely
Low Impact + High Probability = Quick fix
Low Impact + Low Probability = Accept risk
```

## 2. Solution Design **Skill**: /senior-architect
- **Goal**: Ensure technical feasibility and architectural alignment.
- **Action**: Invoke `/architect`.
- **Check**:
  - Does the design use the Repository Pattern?
  - Are Database schema changes documented?
  - Is `{{PATH_TECH_SPEC}}` updated?

## 2.5 Roadmap <-> Issue Sync (Roadmap Reality Check)
- **Goal**: Ensure `{{PATH_ROADMAP}}` reflects live GitHub Issues.
- **Action**: Run `{{CAPABILITIES_GITHUB_ISSUE_LIST}}`.
- **Sync Logic**:
  - `[x]` in Roadmap AND `Closed` Issue -> ✅ Synced
  - `[x]` in Roadmap AND `Open` Issue -> ⚠️ Close Issue via `{{CAPABILITIES_GITHUB_ISSUE_CLOSE}} <id>`
  - `[ ]` in Roadmap AND `Closed` Issue -> ⚠️ Mark Roadmap `[x]`
  - New Roadmap Item AND No Issue -> ⚠️ Create Issue via `{{CAPABILITIES_GITHUB_ISSUE_CREATE}}`

> **Tip**: If automated syncing fails or Project Board columns don't update, refer to `.github/GITHUB_OPERATIONS.md` for manual troubleshooting commands.

## 3. Implementation Planning **Skill**: /project-manager
- **Goal**: Break down work into atomic steps for the AI Developer.
- **Action**: Create/Update `task.md`.
- **Strategy**:
  - **Sequential**: For dependent tasks (Schema → API → UI).
  - **Parallel**: For independent tasks (Docs, Tests).

---

## AI EXECUTION MODE **Skill**: /project-manager

### AI Sprint Planning (15-30 minutes)

**Context**: When Agentic AI performs development roles, sprint cadence accelerates from 2 weeks → 4-8 hours.

**User Input Required**:
- Sprint goal (e.g., "Enable PT session booking")
- Quality gates (coverage ≥80%, no high-severity security issues)
- Time box (2-8 hours recommended)
- Approval threshold (confidence score)

**AI Tasks** (Parallel, 10-15 min):
1. Break goal into user stories (invoke `/business-analyst`)
2. Estimate complexity using historical velocity
3. Generate task breakdown with dependencies
4. Auto-assign to AI personas (`/architect`, `/qa`, `/security`, etc.)

**Confidence Scoring System**:

| Confidence | Meaning | Action |
|------------|---------|--------|
| 0.9-1.0 | High confidence | Auto-proceed without user review |
| 0.7-0.8 | Medium confidence | User review optional |
| 0.5-0.6 | Low confidence | User review required |
| <0.5 | Very low confidence | User clarification needed |

**Example AI Output**:
```markdown
## Sprint 42: Enable PT Session Booking

**Sprint Goal**: Members can book PT sessions through mobile app
**Time Box**: 4 hours
**Quality Gates**: Coverage ≥80%, Security scan clean, All tests pass

### User Stories (Confidence: 0.92)
1. [HIGH] As a member, I want to view available PT trainers
2. [HIGH] As a member, I want to book a PT session
3. [MEDIUM] As a trainer, I want to manage my availability
4. [LOW] As a trainer, I want to cancel sessions

**Auto-Approved**: ✅ (confidence >0.9)
**Ready to Execute**: Awaiting user approval to start
```

**Auto-Start**: If user approves, AI begins parallel execution immediately.

### AI Parallel Execution Monitor

**Real-Time Dependency Tracking**:

AI orchestrates workflows based on dependencies:
```mermaid
graph LR
    Start[User Approves] --> Arch[/architect<br/>ADR + Design]
    Arch --> Dev1[Dev: DB Schema]
    Arch --> Dev2[Dev: API Routes]
    Dev1 --> DB[/dba<br/>Migration]
    Dev2 --> QA1[/qa<br/>API Tests]
    DB --> QA2[/qa<br/>Integration]
    QA1 --> Sec[/security<br/>Scan]
    QA2 --> Sec
    Sec --> Docs[/technical-writer<br/>API Docs]
    Docs --> Done[Ready for Review]
```

**Auto-Triggers** (No user intervention):
- `/architect` completes ADR → Auto-trigger `/dev` for scaffolding
- `/dev` completes feature → Auto-trigger `/qa` for tests
- `/qa` passes tests → Auto-trigger `/security` for scan
- All green → Auto-trigger `/technical-writer` for documentation

**User Intervention Points** (AI escalates only when needed):
- ⚠️ Architecture option selection (confidence <0.7)
- ⚠️ Failed quality gate (user decides: fix or accept risk)
- ⚠️ Production deployment approval (always manual)
- ⚠️ High/critical security findings

**Progress Visibility**:
- Real-time `task.md` updates (no daily standups needed)
- AI provides ETA updates every 30 minutes
- User can interrupt/adjust at any checkpoint

### Quality Gate Automation

**Auto-Remediation** (AI fixes without user approval):

| Gate | Threshold | AI Auto-Action | User Escalation Trigger |
|------|-----------|----------------|-------------------------|
| Test Coverage | ≥80% | Generate missing tests | Still <80% after 2 iterations |
| Code Quality | Ruff/Black clean | Auto-format code | Never (always auto-fixable) |
| Security (Low/Med) | 0 findings | Auto-fix + create PR | Can't auto-fix after 1 attempt |
| Documentation | All endpoints documented | Auto-generate docs | Never (always auto-fixable) |

**User Approval Required**:

| Gate | Threshold | AI Action | User Decision |
|------|-----------|-----------|---------------|
| Security (High/Critical) | 0 findings | Create fix PR + report | Approve fix or accept risk |
| Performance | p95 <500ms | Optimize queries/add indexes | Approve changes or relax SLO |
| Mutation Score | ≥80% | Strengthen test assertions | Accept current score or add tests |
| Production Deploy | All gates pass | Prepare deployment | Approve or delay deployment |

**Execution Time Comparison**:

| Activity | Human Team | AI Team | User Time |
|----------|------------|---------|----------|
| Sprint Planning | 4 hours | 15 min | 15 min |
| Development | 8 days | 2-3 hours | 0 min |
| Testing | 1 day | 15 min | 0 min |
| Code Review | 4 hours | 5 min | 10 min (spot check) |
| Deployment | 2 hours | 20 min | 2 min (approval) |
| **Total** | **2 weeks** | **4 hours** | **27 min** |

---

## 3.5: Sprint Planning Techniques

**Goal**: Transform backlog items into executable sprint commitments.

### Planning Meeting Structure

**Duration**: 2 hours per week of sprint (2-week sprint = 4 hours)

**Participants**:
- Product Owner (prioritizes backlog)
- Scrum Master (facilitates)
- Development Team (estimates & commits)

### Step-by-Step Process

**A. Define Sprint Goal**:
```
Example: "Enable members to book PT sessions through the mobile app"

Good Sprint Goal Criteria:
- Specific: Focuses on one feature area
- Measurable: Can be demoed at sprint review
- Valuable: Delivers user value
- Achievable: Realistic for team velocity
```

**B. Select Backlog Items**:
```bash
# Review product backlog priority
# In .agent/backlog.md or GitHub Project

Priority order:
1. Critical bugs (blocking production)
2. High-value features (based on user feedback)
3. Technical debt (if blocking future work)
4. Nice-to-have enhancements
```

**C. Estimation Techniques**:

> **⚠️ CRITICAL: Agentic AI vs Human Estimation**
>
> When **Agentic AI performs development work**, estimation models must account for 10-50x speedup compared to human developers. Traditional estimation scales (hours/days) are **calibrated for manual development** and will drastically overestimate AI execution time.

#### Estimation for Human Developers (Traditional)

**Planning Poker** (recommended for human teams):
1. Product Owner reads user story
2. Team asks clarifying questions
3. Each member secretly selects estimate (Fibonacci: 1, 2, 3, 5, 8, 13, 21)
4. All reveal simultaneously
5. Discuss highest and lowest estimates
6. Re-vote until consensus

**Human Estimation Scale**:
| Points | Meaning | Example | Human Hours |
|--------|---------|---------|-------------|
| 1 | Trivial | Update text label | 1-2 hours |
| 2 | Simple | Add validation field | 2-4 hours |
| 3 | Moderate | CRUD endpoint | 4-8 hours |
| 5 | Complex | Feature with DB migration | 1-2 days |
| 8 | Very complex | Multi-step workflow | 2-3 days |
| 13 | Epic | Needs to be broken down | > 3 days |

#### Estimation for Agentic AI Execution (AI Mode)

**Key Principle**: Estimate based on **tool call count** and **parallelization potential**, not human workflow time.

**Agentic AI Estimation Scale**:
| Points | Meaning | Example | AI Minutes | Speedup |
|--------|---------|---------|------------|---------|
| 1 | Single-file edit | Update text label | 1-2 min | 30-60x |
| 2 | Multi-file refactor | Add validation field | 3-5 min | 24-40x |
| 3 | Pattern application | CRUD endpoint | 5-10 min | 24-48x |
| 5 | Batch operations | Feature with DB migration | 10-20 min | 12-24x |
| 8 | Sequential dependencies | Multi-step workflow | 20-40 min | 12-18x |
| 13 | Research + execution | Complex domain logic | 40-90 min | 8-12x |

**Speedup Factors by Task Type**:

| Task Type | Human Time | AI Time | Factor | Why |
|-----------|-----------|---------|--------|-----|
| **Batch test fixes** | 4-6 hours | 8-15 min | 20-30x | Parallel edits, zero context switching |
| **Code refactoring** | 2-4 hours | 10-20 min | 12-24x | Pattern recognition, bulk operations |
| **Documentation** | 3-5 hours | 5-10 min | 18-36x | Auto-generation from code |
| **Test writing** | 4-8 hours | 10-20 min | 12-24x | Template-driven generation |
| **Bug investigation** | 2-6 hours | 15-30 min | 8-12x | Instant code analysis, no debugging overhead |
| **API integration** | 1-2 days | 30-60 min | 8-16x | Sequential steps, but no manual testing loops |
| **Requirements analysis** | 4-8 hours | 10-20 min | 12-24x | Instant file scanning, pattern extraction |

**AI Estimation Formula**:
```
AI_Time = (Tool_Calls × Avg_Tool_Time) + (Sequential_Loops × Loop_Time)

Where:
- Tool_Calls = Number of operations (file reads, edits, tests)
- Avg_Tool_Time = ~5-10 seconds per tool call
- Sequential_Loops = How many test-fix-verify cycles needed
- Loop_Time = ~2-3 minutes per iteration
```

**Example Calculation**:
```
Task: Fix 8 BookingService tests (Phase 3b actual example)

Human Estimate:
- Analyze code: 30 min
- Fix each test: 8 × 30 min = 4 hours
- Debug issues: 1 hour
- Total: 5.5 hours

Agentic AI Actual:
- Analyze code: 1 min (view_code_item)
- Fix helper: 2 min (1 edit)
- Fix 8 tests: 3 min (batch multi_replace)
- Run tests: 2 min (automated verification)
- Total: 8 minutes

Speedup: 5.5 hours / 8 min = 41x faster
```

**When to Use Each Model**:

- **Use Human Estimation** when:
  - Actual humans will do the work
  - AI confidence < 0.5 (requires extensive human review)
  - Domain expertise required (business rules, legal compliance)
  - Stakeholder communication time dominates technical work

- **Use Agentic AI Estimation** when:
  - AI will autonomously execute (AI mode workflows)
  - Task is batch-scopable (fix all X, update all Y)
  - Pattern-based work (testing, refactoring, documentation)
  - Quality gates are automated (tests, linting, security scans)

**Hybrid Estimation** (AI execution + Human review):
```
Total_Time = AI_Execution_Time + Human_Review_Time

Where:
- AI_Execution_Time = Use Agentic AI scale (minutes)
- Human_Review_Time = 10-30% of traditional human estimate
```

**Example**:
```
Task: Implement new API endpoint with tests

Traditional Human: 8 points = 2 days = 16 hours

Hybrid AI + Human:
- AI executes: 20 minutes (code + tests + docs)
- Human reviews: 2 hours (spot check logic, approve)
- Total: ~2.5 hours (vs 16 hours)
- Speedup: 6.4x
```

**D. Task Breakdown**:
```markdown
# Example: User Story "As a member, I want to book PT sessions"

Breaking down into tasks:
- [ ] Design database schema for PT bookings (2 pts)
- [ ] Create Alembic migration (1 pt)
- [ ] Implement booking API endpoint (3 pts)
- [ ] Add booking logic to service layer (3 pts)
- [ ] Create booking UI component (5 pts)
- [ ] Write unit tests (2 pts)
- [ ] Write integration tests (2 pts)
- [ ] Update API documentation (1 pt)

Total: 19 points
```

**E. Capacity Planning**:
```bash
# Calculate team capacity
Team velocity (last 3 sprints average): 40 points
Planned time off this sprint: 1 person (5 days)
Available capacity: ~32 points (80% of 40)

# Only commit to 32 points max
```

**F. Sprint Backlog Creation**:
- [ ] Create `docs/sprints/sprint-XX-backlog.md`
- [ ] Document sprint goal
- [ ] List committed user stories
- [ ] **Sync to GitHub**:
  ```bash
  # For each confirmed user story:
  gh issue create --title "User Story Title" --body "Acceptance Criteria..." --label "sprint-XX"
  ```
- [ ] Track daily progress in stand-ups

### Anti-patterns to Avoid
- ❌ Overcommitting (using 100% of velocity)
- ❌ Vague user stories ("Improve performance")
- ❌ No sprint goal (random collection of tasks)
- ❌ Estimating in hours instead of story points

## 4. Execution Oversight **Skill**: /project-manager
- **Goal**: Monitor progress and handle blockers.
- **Action**: Monitor the Coding Agent.
- **Intervention**:
  - **Project Board Sync**: Ensure active tasks are in **"In Progress"** column.
  - If tests fail, pause and invoke `/test-engineer`.
  - If security doubts arise, invoke `/security`.

## 4.5: Delegation Framework

**Goal**: Empower team members with appropriate autonomy.

### Jurgen Appelo's 7 Levels of Delegation

Use this framework to determine decision-making authority:

| Level | Name | Description | When to Use | Example |
|-------|------|-------------|-------------|---------|
| 1 | **Tell** | You decide, inform team | Critical decisions, tight deadlines | "We're using PostgreSQL for this project." |
| 2 | **Sell** | You decide, persuade team | Important decisions needing buy-in | "I've chosen FastAPI because..." |
| 3 | **Consult** | You ask input, then decide | Technical architecture choices | "Should we use Redis or Memcached?" |
| 4 | **Agree** | You and team decide together | Major feature priorities | Sprint planning commitments |
| 5 | **Advise** | Team decides, you advise | Implementation details | "Consider using async here." |
| 6 | **Inquire** | Team decides, explains after | Day-to-day technical choices | Code refactoring approaches |
| 7 | **Delegate** | Team decides, no report needed | Routine tasks | Variable naming, code formatting |

### Delegation Decision Tree

**Ask yourself:**
1. Is this a **strategic decision** (architecture, project scope)?
   → Use levels 1-3 (Tell, Sell, Consult)

2. Does it have **cross-team impact** (API contracts, database schema)?
   → Use level 4 (Agree together)

3. Is it a **technical implementation detail**?
   → Use levels 5-7 (Advise, Inquire, Delegate)

4. What's the **risk level**?
   - High risk (production deployment) → levels 1-4
   - Medium risk (feature development) → levels 3-5
   - Low risk (refactoring) → levels 5-7

### Delegation Board (for team alignment)

Create `docs/delegation-board.md`:

| Decision Type | Delegation Level | Owner | Notes |
|---------------|------------------|-------|-------|
| Technology stack | 3 (Consult) | PM + Tech Lead | Team provides input |
| API design | 4 (Agree) | Tech Lead | Team consensus |
| Code implementation | 6 (Inquire) | Developer | Explain in PR |
| Testing approach | 5 (Advise) | QA Lead | Team follows guidance |
| Deployment timing | 2 (Sell) | PM | Explain business need |

### Communication Templates

**Level 3 (Consult)**:
```
I'm considering [DECISION]. Before finalizing, I'd like your input:
- Option A: [pros/cons]
- Option B: [pros/cons]

Please share your thoughts by [DATE]. I'll make the final call by [DATE + 2 days].
```

**Level 5 (Advise)**:
```
You have full authority to decide on [DECISION]. My recommendation:
- Consider [OPTION] because [REASON]
- Watch out for [RISK]

Let me know what you decide, and I'm here if you need guidance.
```

## 5. Quality Assurance & Review **Skill**: /test-engineer
- **Goal**: Verify "Definition of Done" (DoD).
- **Checks**:
  - [ ] All Tests Passing (Unit, Integration, BDD)?
  - [ ] Code Coverage >= 70%?
  - [ ] Linting (Black/Ruff) clean?
  - [ ] Documentation updated?
  - [ ] CI/CD Pipeline Green?

## 6. Closure **Skill**: /release
- **Action**:
  - Invoke `/technical-writer` for final docs polish.
  - Finalize `walkthrough.md`.
  - **Update Project Management Artifacts**:
    - Update `{{PATH_ROADMAP}}` (Check off completed features).
    - Update `{{PATH_RTM}}`.
  - Signal readiness for Merge/Deployment.

## 6.5: Sprint Retrospective Techniques

**Timing**: Last 1-2 hours of sprint, after Sprint Review

**Goal**: Identify improvements for next sprint

### Retrospective Format Rotation

**Use different formats to keep retrospectives fresh:**

#### Format 1: Start, Stop, Continue (Classic)

**Template** (`docs/retrospectives/sprint-XX.md`):
```markdown
## Sprint XX Retrospective

**Date**: 2023-12-15
**Participants**: [Team members]

### 🟢 Start (New practices to adopt)
- Start using Pyinstrument for performance profiling
- Start adding examples to API documentation
- Start pair programming for complex features

### 🔴 Stop (Practices to abandon)
- Stop overcommitting in sprint planning (committed 45 pts, completed 32)
- Stop skipping code review comments
- Stop deploying on Fridays

### 🔵 Continue (Keep doing)
- Continue daily stand-ups at 9:30 AM (attendance: 100%)
- Continue using Conventional Commits
- Continue writing BDD scenarios before coding

### 📝 Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| Reduce sprint commitment to 35 points | PM | Next sprint | ✅ |
| Create PR review checklist | Tech Lead | 2023-12-20 | 🔄 |
```

**How to run**:
1. Give team 10 minutes to write sticky notes (Start/Stop/Continue)
2. Group similar themes
3. Vote on top 3 actions
4. Assign owners and deadlines

---

#### Format 2: Mad, Sad, Glad (Emotional Check-in)

**When to use**: After difficult sprints or team conflicts

```markdown
## Sprint XX Retrospective - Mad, Sad, Glad

### 😡 Mad (Frustrations)
- CI pipeline failures slowed us down (4 hours lost)
- Unclear requirements on User Story #42
- Production bug discovered after deployment

### 😢 Sad (Disappointments)
- Didn't finish PT booking feature
- No time for refactoring technical debt
- Missed original deadline

### 😊 Glad (Wins)
- Successfully migrated to async database driver
- Test coverage increased from 80% to 86%
- Resolved all security scan issues

### 💡 Insights
- Need better requirement clarification in sprint planning
- CI/CD optimization should be next sprint priority
```

---

#### Format 3: 4Ls (Comprehensive)

**When to use**: Quarterly or after major releases

```markdown
## Sprint XX Retrospective - 4Ls

### ❤️ Liked
- New deployment automation saved 2 hours per deploy
- Team collaboration improved with daily pair programming

### 🧠 Learned
- Pyinstrument is better than cProfile for FastAPI
- Database connection pooling reduced latency by 40%

### 😟 Lacked
- Clear acceptance criteria on 3 user stories
- Dedicated time for documentation updates

### 🌟 Longed For
- Automated performance testing in CI/CD
- More time for learning new technologies
- Better stakeholder communication
```

---

### Retrospective Best Practices

1. **Create Safe Space**:
   - "What's said in retro stays in retro"
   - No blame, focus on process not people
   - Everyone participates equally

2. **Actionable Outcomes**:
   ```markdown
   # Bad action item
   - "Communicate better"

   # Good action item
   - Create Slack channel #project-updates with daily summaries by 5 PM
   - Assign: John
   - Due: Next sprint start
   ```

3. **Track Progress**:
   - Review previous retrospective actions at start of next retro
   - Close completed items, escalate blockers

4. **Rotate Facilitator**:
   - Different team member facilitates each sprint
   - Keeps format fresh, builds ownership

5. **Time Management**:
   - Timebox each section (15 min gathering, 30 min discussion, 15 min action items)
   - Use timer to stay on track
