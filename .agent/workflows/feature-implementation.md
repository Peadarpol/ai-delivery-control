---
description: Comprehensive SDLC workflow for implementing new features or requirements with AI Execution Mode
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->

# /feature-implementation - Comprehensive SDLC Workflow

## Trigger
Use when: A new requirement is requested, or an existing requirement needs to be implemented from scratch. This workflow orchestrates the entire SDLC by engaging specialist personas.

## Mindset
- **Orchestrator**: You are the conductor; other workflows are the instruments.
- **Impact-First**: Before changing code, understand what will break (Tests, Seeding, Docs).
- **Data-Driven**: If you can't seed it, you can't test it.
- **Traceability**: Ensure the thread from specific requirement to code to test is unbroken.
- **AI-First**: Default to AI Execution Mode for 20-50x speed improvement.

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all feature implementations unless user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human Team)**: 2-3 weeks
- **AI Mode (Agentic)**: 4-8 hours
- **User Time**: 45-60 min (approvals only)

**MANDATORY FIRST STEP: Read Decision Logs & Project State**

Before executing any phase, AI MUST read these files to maintain context and prevent hallucination:

1. `.agent/state/last_session_summary.md` - What happened in last session?
2. `docs/decisions/context.md` - Project background and constraints
3. `docs/requirements/{{PROJECT_REQUIREMENTS_FILENAME}}.md` - Full system requirements (canonical source)
4. `docs/decisions/requirements_log.md` - Validated requirements with status (do NOT implement items not here)
5. `docs/decisions/business_rules.md` - Business logic (follow EXACTLY)
6. `docs/testing/REQUIREMENTS_TRACEABILITY.md` - Current test coverage status
7. `docs/planning/PROJECT_ROADMAP.md` - Sprint context and feature priority
8. **GitHub Issue** (if ticket number provided): `gh issue view <N> --comments` — issue body + comments are the primary per-feature requirements source

---

## Phase 0: Verify Specification (Spec Quality Gate) **Skill**: /project-manager

**Goal**: Assert that a valid, approved specification exists and passes quality checks prior to executing any implementation phase or code modification.

**AI Executes** (2 min):
1. **Determine Active Specification**: Extract `SPEC_ID` from the active git branch name (matching regex `SPEC-\d+`) or environment.
2. **Run Spec Quality Gate**: Set `SPEC_ID` as an environment variable and execute the specification quality checks:
   ```bash
   python .agent/scripts/check_spec.py
   ```
   *If the gate fails (exits with code 1), execution MUST halt immediately. No code modifications or adjacent files may be edited.*
3. **Legacy Feature Bypass (Migration Note)**: Active features predating the spec gate must either backfill specs or execute the gate with the skip flag and migration rationale:
   ```bash
   SKIP_REASON="legacy-in-flight-feature" python .agent/scripts/check_spec.py --skip-spec-gate
   ```

---

## Phase 0.5: Impact & Gap Analysis (Deep Dive) **Skill**: /project-manager

**Goal**: Identify exactly what files, tests, data, and **external issues** will be affected by the new requirement BEFORE starting work.

**AI Executes** (10 min):
1.  **Scan for Artifacts**:
    - **Identify**: Locate relevant BRS, Requirements Log, and Traceability Matrix entries.
    - **Gap Check**: Does the new requirement contradict existing Business Rules?
    - **Status Check**: Is the requirement already partially implemented?

2.  **Read the GitHub Issue (Primary Requirements Source)**:
    - **Fetch**: `gh issue view <N> --comments` — read the full body AND all comments.
    - **Extract**: Capture acceptance criteria, constraints, linked designs, and any decisions recorded in comments.
    - **Search related**: `gh issue list --search "keyword"` — find open issues that contradict or duplicate this work.
    - **Action**: Flag any conflicts; if duplicate found, note it in the gap analysis.

3.  **Scan for Testing & Data Impact**:
    - **Seeding**: Search `{{PATH_INFRASTRUCTURE}}/database/seed.py` and `{{PATH_SOURCE_ROOT}}/scripts/seed_data.py`. Will new non-nullable fields break these?
    - **Performance**: Check `{{PATH_TEST_ROOT}}/performance/locustfile.py`. Does it rely on data structures that will change?
    - **Integration**: Check `{{PATH_TEST_ROOT}}/integration/test_*.py` for hardcoded payloads that might fail strict validation.
    - **UI Tests**: Check `{{PATH_TEST_ROOT}}/ui/playwright/` for form fillers that miss new mandatory fields.
    - **Branch Context (NEW!)**: Verify that the new requirement includes logic for `branch_id` isolation.


    - **Output (Scenario A: New Requirement)**:
    - Create a "Gap Analysis" section in the plan.
    - **Create GitHub Issue**: Run `python scripts/github/issue_manager.py create ...`
      - Issue automatically populated with gap analysis.
      - Automatically set to "In Progress".

    - **Output (Scenario B: Existing Issue from Sprint Backlog)**:
    - **Move to In Progress**: Run `gh project item-edit ...` (See `.github/GITHUB_OPERATIONS.md`).
    - **Initialize DoD**: Append the "AI-Managed Definition of Done" checklist to the issue body.
    - **Gap Analysis**: Post the gap analysis as a COMMENT on the existing issue.

    > **Note**: For exact commands and Project Board IDs, ALWAYS refer to `.github/GITHUB_OPERATIONS.md`.

---

## Phase 1: Requirements Analysis (AI Mode) **Skill**: /business-analyst

**Goal**: Convert feature request into testable user stories and update the Source of Truth.

**Traditional Time**: 1-2 days | **AI Mode Time**: 1.4 hours | **User Time**: 15 min

1. **Invoke `/business-analyst` (AI mode)**

   **AI Executes** (automated, 1.4h total):
   - **FIRST**: Copy `.agent/templates/feature_spec.md` → `docs/planning/specs/SPEC-XXX.md` and fill every section before writing any other output. Do not write a free-form spec.
   - Reads decision logs (context, requirements_log, business_rules)
   - Processes meeting transcript or requirements notes (3 min)
   - Extracts user stories in INVEST format (5 min)
   - Generates BDD scenarios in Gherkin (8 min)
   - Creates requirements traceability matrix (3 min)
   - **Update Requirements Log**: Update `docs/decisions/requirements_log.md` with new/refined requirements.
   - **Refine Traceability**: Update `docs/testing/REQUIREMENTS_TRACEABILITY.md`.

   **AI Output**:
   - `docs/planning/specs/SPEC-XXX.md` (Based on `.agent/templates/FEATURE_SPEC.md`)
   - `bdd/features/*.feature` (BDD scenarios)
   - `docs/requirements/USER_STORIES.md` (append new stories — do NOT overwrite existing entries)
   - `docs/testing/REQUIREMENTS_TRACEABILITY.md` (updated RTM)

2. **User Checkpoint** (15 min):
   - [ ] Review AI-generated user stories
   - [ ] Confirm no hallucinated requirements
   - [ ] Verify feature alignment with `docs/planning/PROJECT_ROADMAP.md`
   - [ ] Review §4 (Prior Decisions) — confirm no relevant `decisions_log.md` entries were missed
   - [ ] Review §5 (API Changes table) — confirm method, path, auth, and schemas are correct
   - [ ] Approve or request modifications — mark spec status as **APPROVED**

> [!WARNING]
> **Spec Gate — do NOT proceed to Phase 2 until the spec at `docs/planning/specs/SPEC-XXX.md`
> is marked APPROVED and every checkbox above is ticked.** An unapproved spec means scope is
> unconfirmed; proceeding risks rework across all subsequent phases.

---

## Phase 2: Architecture Design (AI Mode) **Skill**: /architect
**Skills**: See [.agent/config/skill_mapping.yaml](file:///c:/projects/[PROJECT_NAME]/.agent/config/skill_mapping.yaml) (workflow: feature-implementation, phase: 2)

**Goal**: Design solution with multiple options.

**Traditional Time**: 2-3 days | **AI Mode Time**: 38 min | **User Time**: 15 min

3. **Invoke `/architect` (AI mode)**

   **AI Executes** (automated, 23 min):
   - **FIRST**: Reads decision logs and Architecture Principles
   - Generates 3 complete architecture options
   - Each with ADR, C4 diagrams, pros/cons
   - Assigns confidence score to each

   **AI Output**:
   - `docs/decisions/adr/ADR-XXX.md` (for each option)
   - `docs/technical/Technical_Specification.md` (PROPOSED updates)

4. **User Checkpoint** (15 min):
   - [ ] Review 3 architecture options
   - [ ] Select preferred approach (or approve AI recommendation)

4.5. **Identify Domain Events (Mandatory)**:
   - **Question**: Does this feature trigger side effects (emails, syncs, metrics)?
   - **Action**: If yes, define the events in `src/domain/events.py` and handlers in `src/application/handlers/`.

5. **AI Auto-Implements** (automated, 5 min):
   - Generates directory structure
   - Creates base classes/interfaces
   - **Updates `docs/decisions/context.md`** with selected architecture decision

---

## Phase 2.5: Implementation Plan Multi-Persona Audit (Compulsory) **Skill**: /project-manager

**Goal**: Ensure the Implementation Plan is bulletproof and FULLY implemented.
**Triggers**: Completion of Architecture Design.
**Execution**: AI engages all personas to review the `implementation_plan.md`.

### 0. Implementation Plan Integrity (`/project-manager`)
- [ ] **Completeness**: Are ALL bullet points in the `implementation_plan.md` represented in the final `task.md`?
- [ ] **Validation**: Cross-reference the Proposed Changes with the Verification Plan.
- [ ] **Closure**: Ensure a final "Implementation Validation" step is added to the task list before calling it 'Done'.

**Audit Checklist**:

### 1. Product Manager (`/product-owner`)
- [ ] **Completeness**: Does plan cover all Core & Edge cases?
- [ ] **Traceability**: Does every change link to a Requirement ID?

### 2. Database Administrator (`/dba`)
- [ ] **Migration Safety**: Is the migration strategy explicit (up/down)?
- [ ] **Seeding Updates**: Explicitly state how `seed.py` and `seed_data.py` will be fixed?
- [ ] **Data Integrity**: Are default values defined for existing records?

### 3. Quality Assurance (`/qa`)
- [ ] **Test Pyramid**: Are Unit, Integration, and E2E tests specified?
- [ ] **Performance Impact**: Does the plan update `locustfile.py` payload?
- [ ] **Data Isolation**: Does the plan account for test data cleanup?

### 4. Security Engineer (`/security`)
- [ ] **PII**: Does this new field introduce PII? Need audit logging?
- [ ] **AuthZ**: Are permission checks explicit for new endpoints?

### 5. Architect (`/architect`)
- [ ] **Patterns**: Does this follow established patterns (Service Layer, Repository, **Unit of Work**)?
- [ ] **Transactional Integrity**: Does the plan use `IUnitOfWork` to ensure atomicity?
- [ ] **Idempotency**: Are jobs/scripts safe to run multiple times?

### 6. Performance Engineer (`/performance`)
- [ ] **Scaling**: Will this choke with 10k users? (e.g., `current_user` objects, huge lists)
- [ ] **Database**: Are new queries indexed?

### 7. DevOps Engineer (`/devops`)
- [ ] **Config**: Are new env vars documented?
- [ ] **Timezones**: Is precise time handling (AEST) enforced?

### 8. UX Designer (`/ux`)
- [ ] **Feedback**: Are error messages user-friendly?
- [ ] **Latency**: Will this interaction feel slow (>200ms)?

### 9. Code Reviewer (`/code-reviewer`)
- [ ] **Maintainability**: Is the code structure clean and typed?
- [ ] **Naming**: Do names match domain terminology?

### 10. Risk Assessment & Sign-off
- **Confidence Score**: [0-100%]
- **Critical Risks**: [List top 3]
- **Branch Isolation**: [ ] Explicitly verified that data is filtered by `branch_id`.


**Action: Customize Definition of Done (Mandatory)**
Based on the Audit results above, the Agent **MUST** update the GitHub Issue Body now:
1. Run `gh issue edit <ID> --body "..."` (keep existing body, append/edit DoD).
2. Locate the `Phase 3: Audit Specifics` section.
3. Replace the placeholder with concrete checkboxes for identified risks:
   - *Example*: `[ ] Security: Verify rate limiting on new login endpoint`
   - *Example*: `[ ] Performance: Verify search query under 200ms with 10k records`

**Gate Check**:
- [ ] Implementation Plan updated with missing items.
- [ ] **GitHub DoD Updated** with specific audit items.
- [ ] User has approved the Final Plan.

**Action: Instantiate Quality Gate Report (Mandatory)**
1. Copy `.agent/templates/quality_gate_report_template.md` →
   `docs/reviews/quality_gates/quality_gate_YYYY-MM-DD_feature-name.md`
2. Fill the report header: Feature, Branch, Generated timestamp, set Status to `⏳ IN PROGRESS`.
3. Pre-populate **§1 Requirements** from Phase 1 outputs (user stories count, BDD scenario count, RTM link).
4. Pre-populate **§2 Architecture** from Phase 2 output (option selected, ADR link, confidence score).
5. Leave all remaining sections as `[PENDING]` — they are filled in as each phase completes.

---

## Phase 3: Database & Test Data Preparation (AI Mode) **Skill**: /dba

**Goal**: Ensure the environment and test data are ready BEFORE code implementation.

**Traditional Time**: 2-3 hours | **AI Mode Time**: 31 min | **User Time**: 5 min

6. **Invoke `/dba` (AI mode)**

   **AI Executes** (automated, 26 min):
   - **Schema**: Designs schema and creates Alembic migration (`migrations/vXXX_*.py`).
   - **Migration Verification**: Tests migration (up/down) on local DB.
   - **Seeding Fixes**: Updates `{{PATH_INFRASTRUCTURE}}/database/seed.py` and `{{PATH_SOURCE_ROOT}}/scripts/seed_data.py` with new mandatory fields.
   - **Performance Test Updates**: Updates `{{PATH_TEST_ROOT}}/performance/locustfile.py` to ensure load tests won't fail with 422s.
   - **Integration Payload Updates**: Refactors `{{PATH_TEST_ROOT}}/integration/test_*.py` payloads to align with new schema.

7. **User Checkpoint**:
   - [ ] Review migration safety report
   - [ ] Confirm seeding scripts run successfully
   - [ ] **Update Quality Gate Report §3** (Database Schema): migration file path, tables/indexes added, safety score, stairway test result.

---

## Phase 4: Implementation (Test-First Development) **Skill**: /python-backend-guidelines
**Skills**: See [.agent/config/skill_mapping.yaml](file:///c:/projects/[PROJECT_NAME]/.agent/config/skill_mapping.yaml) (workflow: feature-implementation, phase: 4)

**Goal**: Implement feature following TDD principles.

**Traditional Time**: 8 days | **AI Mode Time**: 2-3 hours | **User Time**: 0 min

> [!IMPORTANT]
> **Defensive Checkpoint**: Before starting implementation across 3+ files,
> create a git checkpoint per governance §7.

8. **AI Implements (Test-First Auto-Debug Loop)**:

   **Step A: Create Tests FIRST** (Mandatory):
   1. **Status Update**: Move GitHub Issue Card to **"In Progress"** (Use `mcp_github_issue_write` or use the Project Board automation).
   2. **Write BDD scenarios** in `tests/bdd/features/[feature].feature`
   3. **Write unit test skeletons** for services/repos
   3. **(Aligned)** Integration tests should already be updated in Phase 3.

   **Step B: Implement Code** (TDD Red-Green-Refactor):
   1. Implement validation rules (Pydantic).
   2. Implement service logic.
   3. Update API routes.
   4. Update UI forms (Streamlit) to include new mandatory fields.

   **Step B.5: MANDATORY API Endpoint & Quality Verification** (Before UI Integration):
   > ⚠️ **NEVER skip this step** - it catches integration defects and quality violations early.

   1. **Run all unit tests**: `pytest tests/unit/ -v` - ALL MUST PASS
   2. **Run Architecture Quality Tests**: `pytest tests/quality/test_exception_standards.py` - MUST PASS (Ensures no broad exceptions without `raise`)
   3. **Run Type Checks**: `mypy src/` - MUST PASS (Zero errors allowed in modified/new code)
   4. **Verify endpoint exists in OpenAPI**:
      ```bash
      curl -s http://localhost:8000/openapi.json | Select-String "[endpoint-name]"
      ```
   3. **Test endpoint directly with curl/PowerShell**:
      ```bash
      # GET example
      $token = (Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/token" -Method POST -ContentType "application/x-www-form-urlencoded" -Body "username=admin&password=Admin123!").access_token
      Invoke-RestMethod -Uri "http://localhost:8000/api/v1/[endpoint]" -Headers @{"Authorization"="Bearer $token"}

      # POST example
      $body = '{"field":"value"}'
      Invoke-RestMethod -Uri "http://localhost:8000/api/v1/[endpoint]" -Method POST -Headers @{"Authorization"="Bearer $token"; "Content-Type"="application/json"} -Body $body
      ```
   4. **Expected Response**: 200/201 (NOT 404/422/500)
   5. **Only proceed to UI integration after API returns expected response**

   **Step C: Verify**:
   1. Run full test suite (unit + integration + BDD).
   2. Run `locust` smoke test (headless) to verify performance scripts.
   3. Run coverage check.

---

## Phase 5: Quality Assurance (Integration & Performance) **Skill**: /test-engineer
**Skills**: `/code-review`, `/python-testing`, `/testing-patterns`, `/security-audit`, `/performance-optimization`

**Goal**: Comprehensive automated quality checks.

10. **Parallel Quality Checks**:

    **10a. Invoke `/qa` (AI mode)**
    - Runs all tests.
    - **Performance Check**: Executes `locust` to verify no performance regression and valid payloads.
    - **UI Verification**: Runs Playwright tests (updated for new UI fields).

    **10b. Invoke `/code-reviewer` (AI mode)**
    - Checks code quality, naming, and style.

    **10c. Invoke `/security` (AI mode)**
    - Scans for vulnerabilities (Bandit, Snyk).

**Gate Check**:
- [ ] **Behavioural Audit**: `python .agent/evals/behaviour_checks.py` passes (Gov Rules compliance).
- [ ] **All tests passing** (Unit, Integration, BDD, UI, Performance Smoke).
- [ ] **Quality standards met** (No broad exceptions without `raise`, zero mypy errors).
- [ ] **Seeding scripts** verified working.
- [ ] **Coverage ≥80%**.
- [ ] No HIGH/CRITICAL security issues.
- [ ] **Update Quality Gate Report**:
  - **§4 Implementation**: files added/modified/deleted, formatting and type hint status.
  - **§5 Code Review**: auto-fixed issues by layer (quality, security, performance, best practices).
  - **§6 Testing**: unit/integration/E2E counts, coverage %, mutation score.
  - **§7 Security Audit**: scan tool results, auto-remediation applied, security score.

---

## Phase 6: Documentation (AI Mode) **Skill**: /technical-writer
**Skills**: `/docs` (technical-writer)

**Goal**: Auto-generate comprehensive documentation.

12. **Invoke `/technical-writer` (AI mode)**
    - Updates API docs, README, and CHANGELOG.
    - Updates `docs/technical/Technical_Specification.md`.
    - **Update Quality Gate Report §9** (Documentation): endpoints documented, README/CHANGELOG updated, confidence score.

---

## Phase 7: Deployment (AI Mode) **Skill**: /deploy
*Standard deployment process as per `/deploy`*

---

## Phase 8: Technical Handoff Decision **Skill**: /project-manager

17. **Pre-Review Quality Gate & Refresh** (Mandatory):
    - **Clean Slate**: Ensure local environment matches the "Expected State" for review (Full Stack).
    - **Action**:
        1. **Dependencies**: `pip install .` (Sync packages from pyproject.toml).
        2. **Configuration**: Check `.env` against `.env.example` (Ensure no secrets drift).
        3. **Database**:
            - Delete `gym.db`.
            - `alembic upgrade head`.
            - `python {{PATH_SCRIPTS}}/seed_data.py`.
        4. **Test Execution (Quality Gate)**:
            - **Unit Tests**: `pytest tests/unit` (Must have 100%_PASS_RATE).
            - **Integration Tests**: `pytest tests/integration` (Must have 100%_PASS_RATE).
            - **Validation**: If tests fail, YOU MUST FIX THEM before proceeding to review.
        5. **Containers**:
            - `docker compose build --no-cache` (Rebuild backend/frontend).
            - `docker compose up -d` (Deploy new images).
        6. **Verification**: `{{CAPABILITIES_RUN_BACKEND}}` (Launch smoke check).

18. **Complete & Gate on Quality Gate Report (Mandatory)**:
    - **Update §8 Performance**: profiling results, load test metrics (p95, p99, error rate, throughput).
    - **Update §10 Deployment**: pre-deployment checks, staging deployment status, smoke test results.
    - **Fill Overall Summary table** and set top-level Status: `✅ READY FOR PRODUCTION`, `⚠️ NEEDS ATTENTION`, or `❌ BLOCKED`.
    - **Verify all metric targets met**:
      - [ ] Coverage ≥80% — §6
      - [ ] Security score ≥90/100 — §7
      - [ ] p95 latency <200ms — §8
      - [ ] No open HIGH/CRITICAL issues across any section
    - If any target is unmet, resolve before proceeding. Do not raise a PR against a `❌ BLOCKED` report.

19. **Submit for Review**:
    - **Commit & Push**: Push feature branch (include completed quality gate report).
    - **Create PR**: Open Pull Request against `develop` (Use `mcp_github_create_pull_request`).
      - PR description **must link** the quality gate report:
        `Quality Gate Report: docs/reviews/quality_gates/quality_gate_YYYY-MM-DD_feature-name.md`
    - **Update Issue**: Add PR link and update DoD in the Issue (Use `mcp_github_add_issue_comment` or `mcp_github_issue_write`).

20. **Review Checkpoint (User Decision)**:
    - **Action**: Ask User: "Do you want to perform a Manual Technical Review, or should I auto-merge?"
    - **Path A: Manual Review Required**:
        - Move card to **"Technical Review"**.
        - **Add Technical Review Instructions** to GitHub Issue (see template below).
        - **STOP**. User will merge after review.
    - **Path B: Auto-Proceed (Preferred)**:
        - **Merge PR**: Merge feature branch into `develop`.
        - **Project Board Update**: Move card to **"Stakeholder Review"**.
        - **Add UAT Instructions**: Comment on issue using template from `.github/ISSUE_TEMPLATE/uat_instructions_template.md`.
            ```bash
            gh issue comment <issue_number> --repo {{TECH_STACK_GITHUB_REPO}} --body-file .github/ISSUE_TEMPLATE/uat_instructions_template.md
            ```
            **Note**: Customize the template placeholders:
            - `{FEATURE_DESCRIPTION}`: Brief summary of what was implemented
            - `{REQUIREMENT_ID}`: Link to FR-XXX-XX
            - `{MENU_PATH}`: Navigation instructions (e.g., "Admin → Members → Settle Account")
            - `{SCENARIO_DESCRIPTION}`: User-friendly test scenario
            - `{VALIDATION_POINT_1}`, `{VALIDATION_POINT_2}`: Success criteria
            - **TEST URL**: Use placeholder text "See deployment notifications" (IP changes per CD run)
        - **Update Issue**: Comment "Merged to develop. Deployed upon CI completion. Ready for UAT."

---

### Technical Review Instructions Template

When moving a GitHub issue to **"Technical Review"**, add the following comment:

```markdown
## 🔍 Technical Review Required

### Overview
[Brief description of what was implemented]

### What to Review

#### 1. Code Quality
- [ ] Review PR: [Link to Pull Request]
- [ ] Check adherence to **Unit of Work Pattern** (Services should not inject repositories)
- [ ] Verify transactional integrity via `uow.commit()`
- [ ] Verify type hints are complete
- [ ] Confirm no hard-coded values (use config/env vars)

#### 2. Database Changes
- [ ] Review migration: `migrations/versions/[migration_file].py`
- [ ] Verify migration has both `upgrade()` and `downgrade()`
- [ ] Check for proper indexing on foreign keys
- [ ] Confirm seeding scripts updated: `src/infrastructure/database/seed.py`

#### 3. Testing Coverage
- [ ] Unit tests exist for new services/repositories
- [ ] Integration tests cover API endpoints
- [ ] Run full test suite: `pytest` (must be 100% pass)
- [ ] Check coverage report: `pytest --cov`

#### 4. Security & Performance
- [ ] Sensitive endpoints have rate limiting
- [ ] PII fields are not logged
- [ ] N+1 queries prevented (use `joinedload` where applicable)
- [ ] Audit logging implemented for sensitive actions

#### 5. Documentation
- [ ] API endpoint documented in code docstrings
- [ ] BRS updated with detailed requirement
- [ ] REQUIREMENTS_TRACEABILITY.md updated

### Files Changed
[List key files that were modified/created]

### Test Commands
```bash
# Run unit tests
pytest tests/unit -v

# Run integration tests
pytest tests/integration -v

# Check migration
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### Approval Criteria
- ✅ All tests passing
- ✅ No linting errors (`ruff check .`)
- ✅ Code follows established patterns
- ✅ Migration is reversible

**Reviewer**: [Tag technical reviewer]
```

---

### Stakeholder UAT Instructions Template

When moving a GitHub issue to **"Stakeholder Review"**, add the following comment:

```markdown
## ✅ Ready for User Acceptance Testing (UAT)

### Feature Deployed
**Environment**: AWS TEST
**URL**: [TEST Environment URL - {{URL_APP_STAGING}}]
**Credentials**:
- Username: `admin`
- Password: `[Provided separately]`

---

### What Was Implemented
[Brief user-friendly description of the feature]

**Related Requirement**: [FR-XXX-XX: Requirement Name]

---

### How to Test This Feature

#### Step 1: Access the Feature
1. Navigate to: **[Specific Menu/Tab]** → **[Sub-section]**
2. You should see: [Description of what appears]

#### Step 2: Test [Primary Use Case]
**Scenario**: [User-friendly scenario description]

1. [Step-by-step instructions]
   - Click on [Button/Field]
   - Enter [Sample data]
   - Expected Result: [What should happen]

2. [Next step]
   - Expected Result: [What should happen]

**Success Criteria**:
- ✅ [Specific outcome to verify]
- ✅ [Another outcome]

#### Step 3: Test [Edge Case/Secondary Use Case]
**Scenario**: [Description]

1. [Instructions]
2. Expected Result: [What should happen - including error messages if applicable]

---

### Test Data Available
For your convenience, the TEST environment has been seeded with:
- **Members**: 10 test members (IDs 1-10)
- **Contracts**: 5 active contracts
- **Products**: Sample products in POS
- [Any other relevant test data]

**Suggested Test Member**:
- Name: John Smith
- ID: 1
- Email: john.smith@example.com

---

### What to Look For

#### ✅ Functional Validation
- [ ] Feature works as described in requirement
- [ ] All buttons/links are functional
- [ ] Data saves correctly
- [ ] Validation messages are clear

#### ✅ User Experience
- [ ] Interface is intuitive
- [ ] Loading times are acceptable (< 2 seconds)
- [ ] Error messages are user-friendly
- [ ] No broken layouts on different screen sizes

#### ⚠️ Report Issues If You See
- Any error messages
- Unexpected behavior
- Slow performance
- Confusing UI elements
- Missing functionality from the requirement

---

### How to Report Issues
1. Take a screenshot if possible
2. Note the exact steps you took
3. Comment on this issue with:
   - What you expected to happen
   - What actually happened
   - Screenshot (if applicable)

---

### Approval
Once you've validated the feature works as expected, please:
- Comment "✅ Approved for Production" on this issue

**Stakeholder**: [Tag stakeholder/client]
**Deadline**: [Date by which feedback is needed]
```

---


### Phase 9: Deployment & UAT **Skill**: /deploy

1.  **Deployment (Automated)**:
    - CI/CD detects merge to `develop` (triggered by User or Agent).
    - Auto-deploys to **AWS TEST Environment**.

2.  **Client UAT (Test Env)**:
    - Card is in **"Stakeholder Review"**.
    - **Client** accesses AWS Test URL.
    - Client verifies requirements.

3.  **Release**:
    - If Client approves: Tech Stakeholder merges to `main`.
    - Card moved to **"Done"**.

---

## Improvements Suggestion Checklist (Self-Correction)
- [ ] **Rollback**: Did I verify that the Alembic downgrade script actually works?
- [ ] **Secrets**: Did I introduce any new config/secrets? Are they in `.env.example`?
- [ ] **Dependencies**: Did I add a library? Is it in `pyproject.toml`?
