---
description: Code review best practices and PR workflows
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Code review best practices and PR workflows
---

# /review - Code Reviewer Workflow

## 0. Pre-Task Anti-Hallucination Check
Before reviewing, you **MUST** verify the project's coding standards:

| Artifact | Purpose | Placeholder |
| :--- | :--- | :--- |
| **Technical Spec** | Dev standards & project structure | `{{PATH_TECH_SPEC}}` |
| **Code Quality** | Linting & formatting standards | `{{PATH_CODE_QUALITY}}` |
| **AI Guidelines** | Coding patterns & error handling | `{{PATH_AGENT_GUIDELINES}}` |
| **BRS** | Business requirements context | `{{PATH_BRS}}` |

**Verification Steps:**
1. [ ] Check Section 7 of `{{PATH_TECH_SPEC}}` for the approved code style and testing strategy.
2. [ ] Consult `{{PATH_AGENT_GUIDELINES}}` for specialized AI interaction patterns.

---

## Trigger
Use when: reviewing pull requests, auditing code quality, or providing feedback on implementations.

## Mindset
- **Teach, don't criticize** - explain the "why"
- **Pick battles wisely** - focus on bugs > design > style
- **Approve with trust** - don't block on nitpicks
- **Praise good work** - positive reinforcement matters

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all code reviews and PR audits unless the user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human Reviewer)**: 1-2 hours
- **AI Automated**: 7.5 min
- **User Time**: 5 min (critical issues only)

### Multi-Layer Automated Review

**AI performs parallel checks** (all layers run simultaneously, 5 min):

#### Layer 1: Code Quality (Auto-Fix Enabled)

```python
# AI Auto-Fixes WITHOUT user approval:

# Issue: Inconsistent formatting
- Black formatting violations → Auto-format with Black
- Ruff lint errors → Auto-fix where possible
- Import sorting → Auto-sort with isort

# Issue: Simple refactoring
- Duplicate code blocks → Extract to function
- Magic numbers → Extract to constants
- Long functions (>50 lines) → Suggest split points

# Issue: Type hints missing
- Add type hints to function signatures
- Add return type annotations
```

**Example Auto-Fix**:
```markdown
## 🔧 Auto-Fixed Issues (No Review Needed)

**Fixed 8 issues automatically**:
1. ✅ Formatted 3 files with Black
2. ✅ Fixed 5 {{TECH_STACK_LINTER}} violations (unused imports, line length)
3. ✅ Added type hints to 4 functions
4. ✅ Extracted magic number to constant: `MAX_SESSIONS_PER_DAY = 10`

**Committed**: Auto-fix commit pushed to PR
```

#### Layer 2: Security Vulnerabilities (User Approval Required)

```python
# AI Flags for User Review:

# CRITICAL - Always escalate
- SQL injection vulnerabilities
- Hardcoded secrets/passwords
- Insecure cryptography
- Authentication bypass

# HIGH - Escalate if can't auto-fix
- Missing input validation → AI can auto-add
- Missing authorization checks → User decides placement
- XSS vulnerabilities → AI can auto-escape if obvious

# MEDIUM/LOW - Auto-fix with confidence >0.8
- Missing CSRF protection → AI adds decorator
- Weak password hashing → AI updates to bcrypt
```

**Example Security Finding**:
```markdown
## ⚠️ CRITICAL Security Issue - User Approval Required

**Finding**: Potential SQL Injection in `{{PATH_API_ROUTES}}/members.py:42`

**Current Code**:
```python
def search_members(name: str):
    query = f"SELECT * FROM members WHERE name LIKE '%{name}%'"
    return db.execute(query)
```

**AI Proposed Fix** (Confidence: 0.98):
```python
def search_members(name: str):
    query = "SELECT * FROM members WHERE name LIKE :name"
    return db.execute(query, {"name": f"%{name}%"})
```

**Impact**: Prevents SQL injection attacks
**Action**: Approve auto-fix or modify manually
```

#### Layer 3: Performance Analysis

**AI detects performance issues**:

| Issue | Severity | Auto-Fix | User Decision |
|-------|----------|----------|---------------|
| N+1 queries | HIGH | ✅ Add eager loading | Auto (confidence >0.9) |
| Missing database index | MEDIUM | ✅ Generate migration | User approves new index |
| Inefficient loop | MEDIUM | ✅ Suggest list comprehension | Auto (simple cases) |
| Large payload response | LOW | ⚠️ Suggest pagination | User decides |

**Example Performance Fix**:
```markdown
## 🚀 Performance Optimization - Auto-Fix Available

**Issue**: N+1 query in `get_member_contracts()`

**Problem**: Loading 100 members with contracts = 101 database queries

**Current Code**:
```python
def get_member_contracts():
    members = db.query(Member).all()  # 1 query
    for member in members:
        contracts = member.contracts  # 100 queries (lazy load)
```

**AI Fix** (Confidence: 0.95):
```python
def get_member_contracts():
    members = db.query(Member).options(joinedload(Member.contracts)).all()  # 1 query
```

**Impact**: 101 queries → 1 query (99% reduction)
**Auto-applied**: ✅ (high confidence via {{CAPABILITIES_TEST_RUN_ALL}})
```

#### Layer 4: Best Practices (OWASP, SOLID, DRY)

```markdown
## Best Practice Violations

**OWASP Checks**:
- ✅ Input validation on all endpoints
- ⚠️ Missing rate limiting on `/api/token` (AI can add)
- ✅ Passwords hashed with bcrypt
- ⚠️ CORS allows all origins (AI suggests restriction)

**SOLID Principles**:
- ⚠️ Function `process_payment()` has >3 responsibilities (violates SRP)
  - AI suggests: Split into `validate_payment()`, `charge_card()`, `record_transaction()`
- ✅ Classes follow Open/Closed principle
- ⚠️ Direct database access in API layer (violates DIP)
  - AI suggests: Use repository pattern in {{PATH_INFRASTRUCTURE}}

**DRY Violations**:
- 🔍 Duplicate code detected in 3 places (auth token validation)
  - AI auto-extracted to `validate_token()` helper
```

### Confidence-Based Auto-Approval

**AI auto-fixes without user approval** (confidence ≥0.9):
- Code formatting (Black, Ruff, isort)
- Type hint additions
- Simple refactoring (extract constants, rename variables)
- N+1 query fixes (eager loading)
- Add missing docstrings

**Requires user approval** (confidence <0.9 OR security/breaking change):
- Security vulnerability fixes
- Database schema changes (new indexes)
- API contract changes
- Complex refactoring (split functions, change architecture)

### AI Review Summary

**Example Output**:
```markdown
## AI Code Review Complete - PR #142: Add PT Booking Feature

**Files Changed**: 8 files, +347 lines, -12 lines

### Auto-Fixed Issues ✅ (No Review Needed)
- Formatted 5 files with Black
- Added type hints to 8 functions
- Fixed N+1 query in `booking_service.py`
- Extracted 2 duplicate code blocks
- Added missing docstrings to 4 classes

**Commit**: `fix: apply automated code review suggestions`

---

### Critical Issues ⚠️ (USER REVIEW REQUIRED)

**1. SQL Injection Vulnerability** (CRITICAL)
- File: `{{PATH_PRESENTATION}}/api/members.py:42`
- Fix available (confidence: 0.98)
- [Review Fix](#)

**2. Missing Authorization Check** (HIGH)
- File: `src/api/bookings.py:67`
- AI unsure about permission requirements (confidence: 0.62)
- [Add Manual Review](#)

---

### Recommendations 💡 (Optional Improvements)

**Performance**:
- Add database index on `pt_sessions(trainer_id, schedule_time)` (+15% query speed)
- Implement caching for trainer availability queries

**Architecture**:
- Consider extracting email notification to async task queue (current: blocks API)

**Security**:
- Add rate limiting to `/api/bookings` (prevent booking spam)

---

**Status**: ✅ 2 critical issues need user approval → After approval, PR ready to merge
```

---

## Phase 1: Context Understanding **Skill**: /code-review

1. Before reading code:
   - [ ] What is the purpose of this change?
   - [ ] What are the acceptance criteria?
   - [ ] Are there related issues or tickets?

2. **Standard Alignment Check**:
   - [ ] Does the implementation adhere to the guidelines in `CONTRIBUTING.md`?
   - [ ] Does the PR description follow the `.github/PULL_REQUEST_TEMPLATE.md` format?
   - [ ] Are all "Definition of Done" (DoD) items from the template addressed?

2. **Review Scope & Size Limits**:

   **Quantifiable Limits** (based on research: optimal review effectiveness):
   - [ ] **Line Count**: < 400 lines of code (LOC) per PR
     ```bash
     # Check PR size
     git diff main...HEAD --shortstat
     # If output shows > 400 insertions/deletions, request split
     ```
   - [ ] **Review Time**: Limit to 60 minutes per session
     - Set timer before starting
     - Take 10-min break if approaching limit
   - [ ] **Files Changed**: Ideally < 10 files
     ```bash
     git diff main...HEAD --name-only | wc -l
     ```

   **If PR is too large**:
   ```markdown
   [SUGGESTION] This PR has 850 LOC across 15 files. Consider splitting into:
   1. PR#1: Database migrations + models (200 LOC)
   2. PR#2: Business logic (300 LOC)
   3. PR#3: API endpoints (200 LOC)
   4. PR#4: UI changes (150 LOC)

   Smaller PRs get faster reviews and fewer missed bugs.
   ```

3. **Single Responsibility Check**:
   - [ ] Does this PR address ONE of the following?
     - ✅ Bug fix (one bug)
     - ✅ Feature (one user story)
     - ✅ Refactor (one component)
     - ✅ Documentation update
     - ❌ Multiple unrelated changes (reject - request split)

---

## Phase 1.5: Automated Pre-Checks **Skill**: /code-review

Before manual review, verify CI/CD has passed:

**Required Automated Checks** (block manual review if failed):
// turbo
- [ ] **Linting**: {{CAPABILITIES_CODE_LINT}}/{{CAPABILITIES_CODE_FORMAT}} passing
  ```bash
  # Locally verify
  {{CAPABILITIES_CODE_LINT}} {{PATH_SOURCE_ROOT}}/
  {{CAPABILITIES_CODE_FORMAT}} --check {{PATH_SOURCE_ROOT}}/
  ```
- [ ] **Type Checking**: {{CAPABILITIES_TEST_TYPE_CHECK}} passing
  ```bash
  {{CAPABILITIES_TEST_TYPE_CHECK}}
  ```
- [ ] **Architectural Checks**: Run the consolidated linter
  ```bash
  python .agent/skills/senior-architect/scripts/architecture_checks.py
  ```
- [ ] **Unit Tests**: All tests passing
  ```bash
  pytest tests/unit -v
  ```
- [ ] **Coverage**: ≥ 80% (check CI report)
  - View: `htmlcov/index.html` (generated after `pytest --cov`)

**If CI is red**:
```markdown
[REQUIRED] Please fix failing CI checks before requesting review:
- ❌ {{TECH_STACK_LINTER}}: 3 errors in `{{PATH_API_ROUTES}}/members.py`
- ❌ Tests: `test_create_member` failing

Re-request review after CI is green ✅
```

**Security Scans** (if available):
- [ ] Snyk/Bandit: No high-severity vulnerabilities
- [ ] Dependency check: No known CVEs in new packages

---

## Phase 2: Code Review Checklist **Skill**: /code-review

### Correctness

- [ ] **Functionality Verification**:
  1. Read the acceptance criteria (from linked issue/PR description)
  2. Trace code path for happy path scenario
  3. Ask: "Does this code satisfy AC #1, #2, #3?"

- [ ] **Edge Cases Check**:
  Common edge cases to verify:
  - **Empty inputs**: What if list is empty? String is ""? Dict is {}?
    ```python
    # Bad: crashes on empty list
    first_item = items[0]

    # Good: handles empty
    first_item = items[0] if items else None
    ```
  - **Null/None values**: Is `None` checked before dereferencing?
  - **Boundary conditions**: Off-by-one errors? Max/min values?
  - **Concurrent access**: Thread-safe if accessed concurrently?

- [ ] **Error Handling Check**:
  - [ ] **Try/except blocks present**? (where external calls happen)
  - [ ] **Specific exceptions caught**? (avoid bare `except:`)
    ```python
    # Bad: catches everything, including KeyboardInterrupt
    try:
        result = api_call()
    except:
        pass

    # Good: catches specific errors
    try:
        result = api_call()
    except (TimeoutError, ConnectionError) as e:
        logger.error(f"API call failed: {e}")
        raise ServiceUnavailableError("External service down")
    ```
  - [ ] **Errors logged with context**?

### Security (OWASP Top 10 Checks)

- [ ] **A01: Broken Access Control**
  - [ ] Authorization check before data access?
    ```python
    # Bad: no ownership check
    contract = get_contract(contract_id)
    return contract

    # Good: verify user owns contract
    contract = get_contract(contract_id)
    if contract.member_id != current_user.id and not current_user.is_admin:
        raise ForbiddenError("Cannot access other user's contract")
    ```
  - [ ] **IDOR prevention**? (Can User A access User B's data by changing ID?)

- [ ] **A02: Cryptographic Failures**
  - [ ] No plaintext passwords/tokens in logs?
  - [ ] Secrets in environment variables (not hardcoded)?
    ```python
    # Bad
    API_KEY = "sk_live_abc123"

    # Good
    API_KEY = os.getenv("STRIPE_API_KEY")
    if not API_KEY:
        raise ConfigError("STRIPE_API_KEY not set")
    ```

- [ ] **A03: Injection**
  - [ ] **SQL**: Using parameterized queries (not string interpolation)?
    ```python
    # Bad: SQL injection risk
    query = f"SELECT * FROM users WHERE email = '{email}'"

    # Good: parameterized
    query = "SELECT * FROM users WHERE email = :email"
    result = session.execute(query, {"email": email})
    ```
  - [ ] **Command injection**: Not passing user input to `os.system()`, `subprocess.call()`?

- [ ] **A05: Security Misconfiguration**
  - [ ] Debug mode OFF in production? (`DEBUG=False`)
  - [ ] Default credentials changed?

- [ ] **A07: Identification and Authentication Failures**
  - [ ] Password requirements enforced? (min 8 chars, complexity)
  - [ ] MFA supported where applicable?

- [ ] **A08: Software and Data Integrity Failures**
  - [ ] Dependencies pinned to specific versions? (check `pyproject.toml`)
    ```toml
    # Bad
    fastapi = "*"

    # Good
    fastapi = "^0.115.0"
    ```

- [ ] **A10: Server-Side Request Forgery (SSRF)**
  - [ ] If code makes HTTP requests: URL validated/allowlisted?

### Standardization & Consistency (Gatekeeper)
- [ ] **Project Patterns**:
  - [ ] do API routes match existing conventions? (e.g. `/api/v1/` prefix)
  - [ ] Are file locations consistent with Clean Architecture? (`{{PATH_DOMAIN}}`, `{{PATH_APPLICATION}}`, etc.)
- [ ] **Naming Conventions**:
  - [ ] Do variables/classes follow the project style (snake_case vs CamelCase)?
  - [ ] Are DTOs/Schemas named consistently (e.g., `ContractCreateDetails` vs `CreateContractRequest`)?

### Design
- [ ] Does it follow existing patterns in the codebase?
- [ ] Is the abstraction level appropriate?
- [ ] Are there DRY violations?
- [ ] Is coupling minimized?

### Testing
- [ ] Are tests included?
- [ ] Do tests cover the main scenarios?
- [ ] Are edge cases tested?
- [ ] **Test Quality**: Do tests fail if bug is reintroduced? Are mocks appropriate?
- [ ] Do tests actually assert meaningful things?

### Maintainability
- [ ] Is the code readable without comments?
- [ ] Are names descriptive?
- [ ] Is complexity manageable?
- [ ] Are there magic numbers/strings?

### Performance

- [ ] **Database: N+1 Query Check**
  - Look for loops that make DB queries:
    ```python
    # Bad: N+1 (1 query + N queries in loop)
    for member in members:
        contracts = get_contracts(member.id)  # Query per member!

    # Good: Single query with join or eager loading
    members_with_contracts = session.query(Member).options(
        joinedload(Member.contracts)
    ).all()
    ```
  - **Verification**: Enable SQLAlchemy query logging locally:
    ```python
    # In conftest.py or main.py
    import logging
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    ```
    Run code → count queries in output

- [ ] **Algorithmic Complexity**:
  - [ ] Nested loops on large datasets? (O(n²) or worse)
  - [ ] Could use hash map instead of linear search?
    ```python
    # Bad: O(n) lookup in loop = O(n²)
    for item in items_a:
        if item in items_b_list:  # Linear search!
            ...

    # Good: O(1) lookup = O(n)
    items_b_set = set(items_b_list)
    for item in items_a:
        if item in items_b_set:  # Hash lookup!
            ...
    ```

- [ ] **Memory Efficiency**:
  - [ ] Loading entire dataset into memory? (use pagination/streaming for > 10k records)
  - [ ] Lists duplicated unnecessarily?

- [ ] **Caching Opportunities**:
  - [ ] Expensive computation repeated? (cache result)
  - [ ] Static data fetched repeatedly? (use `@lru_cache` or Redis)

**If performance-critical code**:
```markdown
[SUGGESTION] Consider adding a performance test:
\`\`\`python
def test_get_member_contracts_performance():
    # Setup: 1000 members with 10 contracts each
    ...
    start = time.time()
    result = get_all_member_contracts()
    duration = time.time() - start
    assert duration < 2.0, f"Query too slow: {duration}s"
\`\`\`
```

---

## Phase 3: Feedback Format **Skill**: /code-review

3. Use conventional comment prefixes:

| Prefix | Meaning | Blocking? |
|--------|---------| ----------|
| `[CRITICAL]` | Bug or security issue | Yes |
| `[REQUIRED]` | Must fix before merge | Yes |
| `[SUGGESTION]` | Would improve code | No |
| `[QUESTION]` | Need clarification | Depends |
| `[NITPICK]` | Minor style preference | No |
| `[PRAISE]` | Good work! | No |

4. Example comments:
```
[CRITICAL] This SQL query is vulnerable to injection.
Use parameterized queries instead.

[SUGGESTION] Consider extracting this into a separate function
for reusability.

[PRAISE] Great use of the repository pattern here!
```

---

## Phase 4: Decision **Skill**: /code-review

5. Approval criteria:
   - **Approve**: No critical/required issues, good overall
   - **Request Changes**: Critical issues that must be fixed
   - **Comment**: Questions or non-blocking suggestions only

6. **Post Review Summary** (required for all reviews):

**Template**:
```markdown
## Review Summary

**Decision**: ✅ Approved / ⚠️ Changes Requested / 💬 Comment Only
**Review Time**: [X minutes]
**LOC Reviewed**: [Y lines]

### 🎯 What I Liked
- [Specific positive feedback]
- [Good pattern used]

### 🐛 Critical Issues (Must Fix)
- [CRITICAL] [Issue with line number]

### 💡 Suggestions (Optional)
- [SUGGESTION] [Non-blocking improvement]

### ❓ Questions
- [QUESTION] [Clarification needed]

### ✅ Verification
- [ ] Checked out branch locally? [Yes/No]
- [ ] Ran tests? [Yes/No]
- [ ] Reviewed against linked issue #[N]? [Yes/No]
```

<details>
<summary>📘 Example: Real Review Summary</summary>

## Review Summary

**Decision**: ⚠️ Changes Requested
**Review Time**: 35 minutes
**LOC Reviewed**: 287 lines

### 🎯 What I Liked
- Great use of dependency injection in `MemberService.__init__()` - makes testing easy
- Clear docstrings on all public methods
- Good test coverage (95% for this module)

### 🐛 Critical Issues (Must Fix)
- **[CRITICAL]** `{{PATH_API_ROUTES}}/members.py:42` - SQL injection risk
  ```python
  # Current (vulnerable)
  query = f"SELECT * FROM members WHERE email = '{email}'"

  # Fix: Use parameterized query
  query = "SELECT * FROM members WHERE email = :email"
  session.execute(query, {"email": email})
  ```
- **[REQUIRED]** `{{PATH_SERVICES}}/member_service.py:67` - No error handling for DB connection failure

### 💡 Suggestions (Optional)
- **[SUGGESTION]** `{{PATH_DOMAIN}}/models.py:23` - Consider making `Member.email` a property with validation
- **[NITPICK]** `tests/unit/test_member_service.py:12` - Could use pytest fixture for mock repository

### ❓ Questions
- **[QUESTION]** Why is `status` validation in the service layer instead of the domain model?

### ✅ Verification
- [x] Checked out branch locally
- [x] Ran tests (`pytest`) - all passing
- [x] Reviewed against issue #42
</details>

---

## Time Management & Review Efficiency

**Research-Backed Limits**:
- **Max 400 LOC per review** (defect detection drops after this)
- **Max 60 min per session** (fatigue leads to missed bugs)
- **Max 500 LOC/hour review rate** (slower = better defect detection)

**Recommended Workflow**:
1. **Set timer for 60 minutes**
2. **Review in passes**:
   - **Pass 1** (15 min): Skim entire PR for overall approach
   - **Pass 2** (30 min): Deep dive on logic, security, edge cases
   - **Pass 3** (10 min): Check tests, documentation
   - **Pass 4** (5 min): Write summary comment
3. **If timeout**: Post comment: "Reviewed [X] of [Y] files. Will continue tomorrow."

**Tools to Track Time**:
- Browser extension: "Tab Time Tracker"
- CLI: `time git diff main...HEAD | less` (track how long you spend)

---

## Anti-patterns to Avoid
- ❌ Reviewing for > 1 hour without a break (fatigue leads to missed bugs)
- ❌ Blocking on style issues covered by linters
- ❌ Rewriting in your own style preference
- ❌ Drive-by comments without constructive suggestions
- ❌ Rubber-stamping without actually reading
