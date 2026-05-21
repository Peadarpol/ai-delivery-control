---
description: Versioning, release notes, and deployment coordination
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Versioning, release notes, and deployment coordination
---

# /release - Release Manager Workflow

## Trigger
Use when: cutting a new version, preparing release notes, or coordinating a deployment to production.

## Mindset
- **Stability** - Gatekeeper of production quality
- **Communication** - Ensure all stakeholders know what/when/why
- **Compliance** - Audit trail of changes and approvals
- **Safety** - Always have a backout plan

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all versioning, release coordination, and deployment tasks unless the user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human)**: ~3-4 hours
- **AI Automated**: ~20 min
- **User Time**: 7 min (approvals only)

### Automated Pre-Flight Checks

**AI validates release readiness** (2 min):

```bash
# Release Readiness Listing
- ✅ Git Branch: `release/vX.Y.Z` matches `main`
- ✅ CI Status: All workflows GREEN
- ✅ Database: Migration compatibility verified (dry-run)
- ✅ Security: Dependabot/Snyk clean
- ✅ Documentation: Swagger/OpenAPI updated
- ✅ Jira/Ticket Status: All included tickets in "Done"
```

**Auto-Block Conditions**:
- "Blocking Release: Critical bug #123 linked to this version is OPEN."
- "Blocking Release: Migration `v45_users` is missing rollback script."

### User Approval Checkpoints

**Always Require User Approval**:
1.  **Production Canary Promotion**:
    ```markdown
    ## 🐤 Canary Healthy

    **Metrics (10% Traffic)**:
    - Error Rate: 0.00%
    - Latency: 120ms (vs Baseline 118ms)

    **Action**: Promote to 100% traffic?
    ```

2.  **Major Version Releases (Breaking Changes)**:
    - "This release (v2.0.0) introduces breaking API changes. Confirm API consumers notified?"

**Never Require User Approval** (AI handles autonomously):
- Deploying to Staging/QA environments
- Generating and committing Changelog drafts
- Tagging Git commits
- Uploading build artifacts to registry

### Data-Driven Rollback Decisions

**AI monitors real-time metrics for 15m post-release**:

| Metric | Condition | AI Action |
|--------|-----------|-----------|
| HTTP 500s | > 10 / min | **Instant Rollback** + Alert User |
| Latency (p99) | > 2x Baseline | Hold (do not promote canary) |
| Login Failures | > 5% increase | **Instant Rollback** + Alert Security |
| Customer Support | Ticket surge | Flag for review |

### Automated Communication

**AI generates and sends release notes**:
- **To Engineering**: Detailed changelog with commit links.
- **To Product/Stakeholders**: High-level feature summary ("What's New").
- **To Users (Draft)**: "We've improved performance and added X..."

---

## Phase 1: Planning & Scope **Skill**: /release

1. Identify Release Scope:
   - List features ready for release (Merges to `main`)
   - Check `CHANGELOG.md` for unreleased entries
   - Review pending bugfixes

2. Determine Version Number (Semantic Versioning):
   - **Major** (x.0.0): Breaking changes
   - **Minor** (1.x.0): New features (backward compatible)
   - **Patch** (1.0.x): Bug fixes (backward compatible)

   *Current version check:*
   ```bash
   grep -m 1 "version" pyproject.toml
   ```

---

## Phase 2: Preparation **Skill**: /release

3. Update Documentation:
   - [ ] Generate release notes via GitHub (Auto-generated from PRs)
   - [ ] Update version in `pyproject.toml` or `package.json`
   - [ ] Verify `README.md` is current

4. Generate Release Artifacts:
   - [ ] Create release branch (e.g., `release/v2.1.0`)
   - [ ] Dry-run build/packaging
   - [ ] Verify test suite passes on release branch
   - [ ] **Database Migration Plan**: Verify `{{CAPABILITIES_DB_MIGRATE}}` and `{{CAPABILITIES_DB_ROLLBACK}} -1` scripts

---

## Phase 3: The Release **Skill**: /release

5. Pre-Flight Approvals & Gates:
   - [ ] QA Sign-off (Test Report)
   - [ ] Product Owner Approval
   - [ ] Security Audit Clear
   - [ ] **Canary/Feature Flag Check**: Ensure riskier features are behind toggles

## Step 5.1: Operational Readiness Review (BLOCKING)
1. Open {{ path_uat_orr }} (from config.yaml)
2. Complete every checklist item (audit AI logs, verify migrations, check DLQ).
3. Save the signed-off checklist with date and reviewer name filled in.
4. **git add docs/ci-cd/UAT_OR_CHECKLIST.md**
5. **Include in the release commit** — not as a separate commit.
6. **PR title format**: `[RELEASE vX.Y.Z] ORR signed off — YYYY-MM-DD`

> [!WARNING]
> **DO NOT open the PR to main** until step 4 is complete.
> This step cannot be skipped. `SKIP_AI_REVIEW=1` does not apply here.

6. Execution (via DevOps):
   > "Initiating deployment of v2.1.0 to Production."

   - Trigger CI/CD deployment pipeline (GitHub Actions)
   - Monitor Deployment Metrics:
     - Error Rates (5xx)
     - Latency (p95)
     - Health Check Status

7. Rollback Strategy (If metrics degrade):
   - **Automated**: CI/CD pipeline auto-reverts on failed health check
   - **Manual**: `aws ecs update-service --task-definition <prev-revision>`
   - **Database**: `{{CAPABILITIES_DB_ROLLBACK}} -1` (Only if safe/non-destructive)

7. Git Tagging:
   ```bash
   git tag -a v2.1.0 -m "Release v2.1.0: Feature X and Bug fix Y"
   git push origin v2.1.0
   ```

---

## Phase 4: Post-Release **Skill**: /release

8. Notification:
   - Slack/Email to stakeholders
   - "Release v2.1.0 is successful. New features include..."

9. GitHub Release:
   - Create Release on GitHub from tag
   - Paste contents of Changlog entry

10. Retrospective (if issues occurred):
    - Document what went wrong
    - Plan mitigations for next cycle

> **Note**: If the Project Board "Done" column update fails, see `.github/GITHUB_OPERATIONS.md` for manual correction.
