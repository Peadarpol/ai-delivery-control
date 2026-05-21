---
description: Comprehensive workflow for diagnosing, fixing, and verifying bugs
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Comprehensive workflow for diagnosing, fixing, and verifying bugs
---

# /bug-fix - Bug Fix Workflow

## 0. Pre-Task Anti-Hallucination Check
Before diagnosing, you **MUST** verify the system baseline and known issues:

| Artifact | Purpose | Placeholder |
| :--- | :--- | :--- |
| **Troubleshooting** | Known issues & resolutions | `docs/runbooks/TROUBLESHOOTING.md` |
| **Technical Spec** | Component boundaries & logic | `{{PATH_TECH_SPEC}}` |
| **Business Rules** | Expected behavior truth | `{{PATH_BUSINESS_RULES}}` |
| **GitHub Ops** | Troubleshooting project board | `{{PATH_GITHUB_OPS}}` |

**Verification Steps:**
1. [ ] Check `docs/runbooks/TROUBLESHOOTING.md` to see if this is a recurring issue.
2. [ ] Review Section 2 of `{{PATH_TECH_SPEC}}` to identify the responsible layer.
3. [ ] If the card fails to move, refer to `{{PATH_GITHUB_OPS}}`.

---

## Trigger
Use when: a bug is reported (`[BUG]`), assigning an issue with `label:bug`, or troubleshooting a production incident.

## Mindset
- **Reproduction First** - If you can't reproduce it, you can't fix it.
- **Test-Driven Fixes** - Write a failing test before changing code.
- **Root Cause Analysis** - Fix the disease, not just the symptom.
- **Regression Prevention** - Ensure the fix sticks.

---

## Phase 1: Reproduction & Diagnosis **Skill**: /systematic-debugging

**Goal**: Confirm the bug exists and create a minimal reproduction case.

1. **Analyze the Issue**:
   - [ ] Read "Steps to Reproduce" in the GitHub Issue.
   - [ ] Check logs/screenshots.
   - [ ] Identify the environment (Dev, Test, Prod).

2. **Move Issue to "In Progress"**:
   ```bash
   python scripts/github/issue_manager.py update-phase --issue <ID> --phase implementation
   ```
   > **Note**: If the card fails to move, see `.github/GITHUB_OPERATIONS.md`.

3. **Create Reproduction Script** (The "Red" Test):
   - **Unit Level**: Create a test case in `{{PATH_TEST_ROOT}}/unit/` that asserts the *correct* behavior (but fails currently).
   - **Integration Level**: Create a script in `reproduce_issue.py` or `{{PATH_TEST_ROOT}}/integration/` that triggers the bug.

   *Example Reproduction Script (`reproduce_issue_123.py`)*:
   ```python
   # Minimal script to trigger the bug
   from src.services import member_service

   try:
       # Trigger the bug
       member_service.create_member(email=None)
       print("❌ Failed to reproduce: Operation succeeded unexpectedly")
   except TypeError as e:
       print(f"✅ Reproduced: Caught expected TypeError: {e}")
   except Exception as e:
       print(f"❓ Unexpected error: {e}")
   ```

4. **Confirm Failure**:
   - Run the test/script.
   - **Outcome**: It MUST fail. If it passes, you haven't reproduced the bug.

---

## Phase 2: Implementation (The Fix) **Skill**: /test-driven-development

**Goal**: Implement the fix using TDD.

5. **Implement the Fix**:
   - Check input validation.
   - Handle edge cases.
   - Fix logic errors.

6. **Verify Failure is Gone** (The "Green" Test):
   - Run the reproduction test again.
   - **Outcome**: It MUST pass.

7. **Run Relevant Suite**:
   - Ensure you haven't broken surrounding code.
   - `{{CAPABILITIES_TEST_RUN_ALL}} {{PATH_TEST_ROOT}}/unit/test_related_module.py`

---

## Phase 3: Regression Testing **Skill**: /test-engineer

**Goal**: Ensure this specific bug never returns.

8. **Permanent Test Case**:
   - Convert the reproduction script into a permanent regression test.
   - Place in `{{PATH_TEST_ROOT}}/regression/` or `{{PATH_TEST_ROOT}}/unit/`.
   - Naming convention: `test_bug_<issue_id>_<description>`

   ```python
   def test_bug_123_create_member_null_email_validation():
       """Regression test for Issue #123"""
       with pytest.raises(ValidationError):
           member_service.create_member(email=None)
   ```

9. **Full Suite Check**:
   - `{{CAPABILITIES_TEST_RUN_ALL}}` (All tests must pass)

---

## Phase 4: Closure & Technical Review **Skill**: /project-manager

**Goal**: Merge fix and close issue.

10. **Submit PR**:
    - Commit changes with message: `fix(auth): handle null email (fixes #123)`
    - Create PR linking to the issue.

11. **Technical Review**:
    - Move card to "Technical Review".
    - `python scripts/github/issue_manager.py add-tech-review --issue <ID> --pr <PR#>`

12. **Stakeholder UAT (if visible bug)**:
    - If UI/Behavior change: Move to "Stakeholder Review".
    - Provide "How to Verify" instructions.

13. **Close Issue**:
    - Once merged and verified.
    - `gh issue close <ID>`

14. **Post-Mortem: Golden Dataset Update** (Mandatory):
    - [ ] Run `python .agent/evals/incident_to_eval.py` to register the regression.
    - [ ] Verify with `python .agent/evals/regression_runner.py --verify-only`.

---

## Troubleshooting
- **Can't Reproduce?**: Ask reporter for more info. Do NOT simply close.
- **Flaky?**: Check race conditions or data pollution.
- **Project Board Stuck?**: See `.github/GITHUB_OPERATIONS.md`.
