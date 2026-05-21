---
description: CI/CD, deployment, and automation workflows
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: CI/CD, deployment, and automation workflows
---

# /devops - DevOps Engineer Workflow

## Trigger
Use when: setting up CI/CD, deploying applications, automating processes, or managing environments.

## Mindset
- **Idempotency** - running twice should have the same result as once
- **Immutability** - never modify, always replace
- **Observability** - if you can't see it, you can't fix it
- **Rollback first** - plan the undo before the do
- **Structure Authority**: You own the `infrastructure/` directory and deployment configuration layout.
- **Workflow Obedience**: You MUST follow the `{{PATH_GITHUB_OPS}}` guide for all pipeline and deployment triggers.
- **Artifact Alignment**: Always refer to existing `.github/workflows/` before creating new ones.
- **Tech Stack Compliance**: Adhere to the `{{TECH_STACK_LANGUAGE}}` and `{{TECH_STACK_DB_ENGINE}}` specifications from `config.yaml`.

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all CI/CD, deployment, and automation tasks unless the user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human)**: 3 hours
- **AI Automated**: 32 min
- **User Time**: 4 min (approvals only)

### Pre-Deployment Automated Checks

**AI runs all checks in parallel** (2 min):

```bash
# Quality Gates (All must pass)
- ✅ All tests passing (unit, integration, E2E)
- ✅ Security scan clean (Bandit, Snyk)
- ✅ Code coverage ≥80%
- ✅ No high-severity lint errors
- ✅ Performance tests within SLO
- ✅ Database migrations tested on copy
```

**Auto-Fail Conditions** (AI blocks deployment):
- Any test failure
- High/critical security vulnerability
- Coverage <80%
- Database migration fails on test copy

**User Escalation**: AI notifies user if any gate fails, provides fix recommendations

### User Approval Checkpoints

**Always Require User Approval**:
1. **Production Deployment**:
   ```markdown
   ## 🚀 Production Deployment Ready

   **All pre-checks passed**:
   - ✅ Tests: 347/347 passing
   - ✅ Coverage: 86%
   - ✅ Security: No vulnerabilities
   - ✅ Performance: p95 latency 145ms (target <200ms)

   **Deployment Plan**:
   - Blue-green deployment to production
   - Auto-rollback enabled
   - Estimated downtime: 0 seconds

   **Approve to deploy?** (AI will monitor and auto-rollback if issues)
   ```

2. **New AWS Resources**: User must approve terraform changes that create new resources (cost impact)

3. **Manual Rollback Decision**: If auto-rollback fails, AI escalates to user

**Never Require User Approval** (AI handles autonomously):
- Development/staging deployments
- Terraform updates to existing resources
- Auto-rollback execution
- Health check monitoring

### Auto-Rollback Triggers

**AI reverts automatically** (no user intervention):

| Metric | Threshold | Action |
|--------|-----------|--------|
| Health Check | Any endpoint fails | Instant rollback |
| 5xx Error Rate | >1% | Rollback after 30 seconds |
| 4xx Error Rate | >10% | Rollback after 1 minute |
| p95 Latency | >500ms | Rollback after 2 minutes |
| Memory Usage | >90% | Rollback after 1 minute |
| CPU Usage | >85% sustained | Rollback after 3 minutes |

### Immediate Diagnostics Loop (Post-Rollback)
> [!IMPORTANT]
> If rollback occurs, AI must immediately diagnose the cause.

1. **Rollback**: Execute reversion to previous stable commit.
2. **Fetch Logs**: `{{CAPABILITIES_DEVOPS_KUBECTL_LOGS}} -l app={{TECH_STACK_APP_NAME}} --tail=200 > crash.log`
3. **Analyze**: Search for 'Error', 'Exception', 'Panic'.
4. **Report**: Create a "Post-Mortem" markdown file with findings.
5. **Auto-Fix**: If error is trivial (e.g. missing env var), apply fix to dev and re-deploy to staging.

**No Rollback Needed** (AI marks deployment successful):
- All health checks green for 15 minutes
- Error rate <0.1%
- Latency within SLO (p95 <200ms, p99 <500ms)
- Resource usage <70%

---

## 0. Pre-Task Anti-Hallucination Check (MANDATORY)

**CRITICAL**: Before starting any DevOps or infrastructure work, you MUST ensure fresh context from operational guides and existing configurations.

### Required Review Files:

| File | Purpose | Max Age | Action if Stale |
|------|---------|---------|-----------------|
| `{{PATH_GITHUB_OPS}}` | GitHub automation, lifecycle, and troubleshooting | 7 days | Re-read Sections 4 & 5 |
| `{{PATH_CICD_SETUP}}` | Pipeline setup, account configuration, IAM | 14 days | Re-read relevant setup steps |
| `{{PATH_CICD_SPEC}}` | Pipeline architecture & environment strategy | 14 days | Re-read deployment stages |
| `{{PATH_DEPLOY_MANIFEST}}` | Environment & branding combinations | 7 days | Verify target/brand valid |
| `{{PATH_DOCKER_DIR}}` | Docker image & supervisor configuration | 14 days | Check `supervisord.conf` |
| `{{PATH_TERRAFORM_DIR}}` | AWS Infrastructure as Code (RDS, ECS) | 30 days | Verify `ecs.tf` vs `rds.tf` |
| `{{PATH_DR_PLAN}}` | Disaster recovery & database restore procedures | 30 days | Review Section 2 |
| `docs/deployment/DEPLOYMENT.md` | Deployment patterns and infrastructure strategy | 14 days | Re-read relevant strategy |
| `.github/workflows/` | Existing CI/CD pipeline logic | Current Task | Audit relevant YAML files |
| `.agent/state/last_session_summary.md` | Recent changes | Current session | Always read at session start |

### Review Checklist

Before implementing or modifying pipelines:

- [ ] **Read `{{PATH_GITHUB_OPS}}`** - Confirm deployment triggers and troubleshooting steps
- [ ] **Review `{{PATH_CICD_SETUP}}` & `{{PATH_CICD_SPEC}}`** - Align with project architecture
- [ ] **Audit `.github/workflows/`** - Ensure no duplication of logic with `ci.yml` or `cd-test.yml`
- [ ] **Check `docs/deployment/DEPLOYMENT.md`** - Verify environment naming and secret management strategies
- [ ] **Document review date** - Add comment: "Reviewed DevOps operational docs: [DATE]"

---

## Governance: Infrastructure Structure
**Remit**: You are the authority on **operational file organization**.
- **Scope**: `infrastructure/`, `terraform/`, `.github/`, `scripts/`, and root-level config files (`Dockerfile`, `docker-compose.yml`).
- **Responsibility**:
  - Maintain clear separation between IaC (`terraform/`) and container definitions (`docker/`).
  - Ensure CI/CD workflows are discoverable and logical.
  - Keep the root directory clean (move artifacts to subfolders).
- **Fitness**: Adapt the structure for deployment velocity vs. complexity trade-offs (e.g., separating environments).

**Reference Standard**: Consult `docs/deployment/DEPLOYMENT.md` for project patterns and `docs/ci-cd/CICD_Setup_Guide.md` for environment configuration.

---

## Phase 1: Environment Assessment **Skill**: /devops-cicd

// turbo
1. Check current infrastructure state:
```bash
{{CAPABILITIES_DOCKER_PS}} -a
{{CAPABILITIES_DOCKER_COMPOSE_PS}}
```

2. Review existing configuration:
   - [ ] Check `.env` files for environment-specific settings
   - [ ] Review Dockerfile(s) if present
   - [ ] Examine docker-compose.yml or kubernetes manifests
   - [ ] Check CI/CD configuration (.github/workflows/, .gitlab-ci.yml)

---

## Phase 2: Pipeline Design **Skill**: /devops-cicd

3. Define deployment stages:

| Stage | Purpose | Trigger | Rollback |
|-------|---------|---------|----------|
| Build | Compile, test, package | Push to any branch | N/A |
| Test | Integration tests | Push to main | N/A |
| Staging | Deploy to staging | Merge to main | Previous build |
| Production | Deploy to prod | Manual approval | Blue-green swap |

4. Create deployment checklist:
   - [ ] All tests pass
   - [ ] Security scan clean
   - [ ] Database migrations ready
   - [ ] Rollback tested
   - [ ] Monitoring alerts configured
   - [ ] Stakeholders notified

---

## Phase 2.5: Choose Deployment Strategy **Skill**: /devops-cicd

**Decision Matrix**:

| Strategy | Use When | Downtime | Risk | Cost | Rollback Speed |
|----------|----------|----------|------|------|----------------|
| **Rolling** | Standard deployments | Near-zero | Low | $ | Medium (minutes) |
| **Blue-Green** | Zero-downtime required | None | Low | $$$ (2x infra) | Instant (seconds) |
| **Canary** | High-risk changes | None | Very Low | $$ | Instant (redirect traffic) |
| **Recreate** | Dev/test only | Yes (minutes) | High | $ | Slow (redeploy) |

**Recommended Strategy**: Blue-Green for production (gym app)

### Blue-Green Deployment Setup

**Requirements**:
- Two identical environments: "blue" (current) and "green" (new)
- Load balancer to switch traffic
- Database supports both versions concurrently

**Implementation Steps**:
1. Deploy new version to "green" environment (while "blue" serves traffic)
2. Run health checks on "green"
3. Switch load balancer from "blue" to "green"
4. Monitor "green" for 15 minutes
5. Keep "blue" as instant rollback target for 24 hours

**Terraform Example**:
```hcl
resource "aws_lb_target_group" "blue" {
  name     = "gym-app-blue"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path                = "/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group" "green" {
  name     = "gym-app-green"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path                = "/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

# Switch traffic by updating listener rule
resource "aws_lb_listener_rule" "app" {
  listener_arn = var.lb_listener_arn

  action {
    type             = "forward"
    target_group_arn = var.active_target_group  # Toggle blue/green
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }
}
```

**Traffic Switch Command**:
```bash
# Switch to green
{{CAPABILITIES_DEVOPS_AWS_LB_MODIFY}} \
  --listener-arn arn:aws:elasticloadbalancing:{{TECH_STACK_AWS_REGION}}:123:listener/app/... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/{{TECH_STACK_APP_NAME_GREEN}}

# Verify traffic routing
{{CAPABILITIES_DEVOPS_AWS_LB_DESCRIBE}} \
  --target-group-arn arn:aws:elasticloadbalancing:...:targetgroup/{{TECH_STACK_APP_NAME_GREEN}}

# Rollback to blue (if needed)
{{CAPABILITIES_DEVOPS_AWS_LB_MODIFY}} \
  --listener-arn arn:aws:elasticloadbalancing:{{TECH_STACK_AWS_REGION}}:123:listener/app/... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/{{TECH_STACK_APP_NAME_BLUE}}
```

---

## Phase 3: Implementation **Skill**: /devops-cicd

5. Containerization (if needed):
```dockerfile
# Multi-stage build example
FROM python:3.11-slim as builder
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry export -f requirements.txt > requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install -r requirements.txt
COPY {{PATH_SOURCE_ROOT}}/ ./{{PATH_SOURCE_ROOT}}/
CMD ["uvicorn", "{{PATH_ENTRYPOINT_IMPORT}}", "--host", "0.0.0.0", "--port", "8000"]
```

6. CI/CD pipeline structure:
```yaml
# .github/workflows/ci.yml structure
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: poetry run pytest

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
        run: ...
```

7. Secret Management:
   - [ ] Identify new env vars required.
   - [ ] Ensure they are added to CI secrets and Target Environment parameters.

---

## Phase 3.5: Infrastructure as Code (Terraform) **Skill**: /devops-cicd

**For provisioning or modifying AWS infrastructure**:

1. **Project Structure**:
   ```
   terraform/
   ├── main.tf           # Core resources
   ├── variables.tf      # Input variables
   ├── outputs.tf        # Output values
   ├── providers.tf      # AWS provider config
   ├── backend.tf        # S3 remote state
   └── modules/
       ├── vpc/
       ├── ec2/
       └── rds/
   ```

2. **Remote State Setup** (one-time):
   ```bash
   # Create S3 bucket for state
   aws s3 mb s3://gym-app-terraform-state --region us-east-1

   # Enable versioning
   aws s3api put-bucket-versioning \
     --bucket gym-app-terraform-state \
     --versioning-configuration Status=Enabled

   # Create DynamoDB table for state locking
   aws dynamodb create-table \
     --table-name terraform-state-lock \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST
   ```

3. **Terraform Workflow**:

   **A. Initialize**:
   ```bash
   cd terraform/
   terraform init
   ```

   **B. Validate & Format**:
   ```bash
   terraform fmt -check
   terraform validate
   ```

   **C. Plan** (always review before apply):
   ```bash
   terraform plan -out=tfplan

   # Review plan output:
   # - Resources to add (green +)
   # - Resources to change (yellow ~)
   # - Resources to destroy (red -)
   ```

   **D. Security Scan** (before apply):
   ```bash
   # Install tfsec
   brew install tfsec  # or: go install github.com/aquasecurity/tfsec/cmd/tfsec@latest

   # Scan for security issues
   tfsec .

   # Expected: No HIGH or CRITICAL issues
   ```

   **E. Apply** (with approval):
   ```bash
   terraform apply tfplan

   # Confirm: type "yes"
   ```

   **F. Verify Infrastructure**:
   ```bash
   # Check outputs
   terraform output

   # Verify resources created
   aws ec2 describe-instances --filters "Name=tag:Environment,Values=production"
   ```

4. **Terraform Rollback**:
   ```bash
   # List state versions
   aws s3api list-object-versions \
     --bucket gym-app-terraform-state \
     --prefix terraform.tfstate

   # Restore previous version
   aws s3api copy-object \
     --bucket gym-app-terraform-state \
     --copy-source gym-app-terraform-state/terraform.tfstate?versionId=VERSION_ID \
     --key terraform.tfstate

   # Re-apply previous state
   terraform apply
   ```

5. **Best Practices**:
   - [ ] Always run `terraform plan` before `apply`
   - [ ] Use workspaces for multiple environments (dev, staging, prod)
   - [ ] Tag all resources with `Environment`, `ManagedBy=Terraform`
   - [ ] Never commit `.tfstate` files to Git
   - [ ] Use `terraform.tfvars` for environment-specific values (gitignored)
   - [ ] Store secrets in AWS Secrets Manager, reference in Terraform:
     ```hcl
     data "aws_secretsmanager_secret_version" "db_password" {
       secret_id = "gym-app/db-password"
     }
     ```

---

## Phase 4: Deployment Execution **Skill**: /devops-cicd

// turbo
7. Pre-deployment checks:
```bash
{{CAPABILITIES_TEST_RUN_ALL}}
{{CAPABILITIES_CODE_FORMAT}} --check {{PATH_SOURCE_ROOT}}/ {{PATH_TEST_ROOT}}/
{{CAPABILITIES_CODE_LINT}} {{PATH_SOURCE_ROOT}}/ {{PATH_TEST_ROOT}}/
```

8. Execute deployment:
   - [ ] Backup current state
   - [ ] Apply database migrations
   - [ ] Deploy application
   - [ ] Verify health checks
   - [ ] Monitor error rates for 15 minutes

// turbo
9. After pushing to remote, **ALWAYS verify CI/CD status**:
```bash
# Wait 30 seconds for CI to start
sleep 30

# Check GitHub Actions status (Option 1 - if gh CLI available)
gh run list --limit 1

# Check GitHub Actions status (Option 2 - via web)
# Open: https://github.com/{org}/{repo}/actions
```

**CRITICAL:** Do NOT proceed with next tasks until CI pipeline passes:
   - [ ] GitHub Actions workflow completed successfully
   - [ ] All tests passed in CI
   - [ ] No security scan failures
   - [ ] Build artifacts created successfully

**If CI fails:**
   - [ ] Review failed job logs immediately
   - [ ] Fix issues and push corrections
   - [ ] Re-verify CI status before continuing

10. **Post-deployment Verification**:

   **A. Health Endpoint Check**:
   ```bash
   # Basic health check
   curl -f {{URL_APP_PROD}}/health || echo "FAILED"

   # Expected response (200 OK):
   {
     "status": "healthy",
     "database": "connected",
     "version": "1.2.3"
   }
   ```

   **B. Smoke Tests** (critical user flows):
   ```bash
   # Test 1: API authentication
   TOKEN=$(curl -X POST https://gym-app.example.com/api/token \
     -d "username=admin&password=$ADMIN_PASS" | jq -r '.access_token')

   if [ -z "$TOKEN" ]; then
     echo "❌ AUTH FAILED"
     exit 1
   fi
   echo "✅ Auth working"

   # Test 2: Database connectivity
   curl -H "Authorization: Bearer $TOKEN" \
     https://gym-app.example.com/api/members?limit=1 || echo "❌ DB FAILED"

   # Test 3: UI loads
   curl -f https://gym-app.example.com/ | grep -q "Gym Management" || echo "❌ UI FAILED"
   ```

   **C. Monitor Error Rates**:
   ```bash
   # If using CloudWatch
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ApplicationELB \
     --metric-name HTTPCode_Target_5XX_Count \
     --dimensions Name=LoadBalancer,Value=app/gym-app-lb/... \
     --start-time $(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Sum

   # Expected: Sum = 0 (no 5xx errors)
   ```

   **D. Performance Baseline Check**:
   ```bash
   # Response time should be < 500ms
   time curl -s -o /dev/null https://gym-app.example.com/api/members?limit=100

   # Load test (optional, use Apache Bench)
   ab -n 1000 -c 10 https://gym-app.example.com/health
   # Check: 99th percentile < 1000ms
   ```

   **E. Log Verification**:
   ```bash
   # Check application logs for errors (last 5 minutes)
   aws logs tail /aws/ecs/gym-app --since 5m --filter-pattern "ERROR"

   # Expected: No critical errors
   ```

   **Acceptance Criteria** (ALL must pass):
   - [ ] Health endpoint returns 200
   - [ ] No 5xx errors in last 15 minutes
   - [ ] Response time < 500ms (p95)
   - [ ] Critical API endpoints accessible
   - [ ] No ERROR logs in application
   - [ ] Database queries executing successfully

---

## Phase 5: Monitoring and Observability **Skill**: /devops-cicd

**Required Monitoring Setup**:

1. **Application Health Dashboard**:
   - [ ] CloudWatch Dashboard with:
     - ECS CPU/Memory utilization
     - ALB request count & latency
     - RDS connections & query performance
     - 4xx/5xx error rates

   ```bash
   # Create dashboard
   aws cloudwatch put-dashboard \
     --dashboard-name gym-app-production \
     --dashboard-body file://cloudwatch-dashboard.json
   ```

2. **Alerts Configuration**:
   ```bash
   # Alert on high error rate
   aws cloudwatch put-metric-alarm \
     --alarm-name gym-app-high-5xx-errors \
     --metric-name HTTPCode_Target_5XX_Count \
     --namespace AWS/ApplicationELB \
     --statistic Sum \
     --period 300 \
     --threshold 10 \
     --comparison-operator GreaterThanThreshold \
     --evaluation-periods 1 \
     --alarm-actions arn:aws:sns:us-east-1:123:devops-alerts

   # Alert on health check failure
   aws cloudwatch put-metric-alarm \
     --alarm-name gym-app-health-check-failed \
     --metric-name UnHealthyHostCount \
     --namespace AWS/ApplicationELB \
     --statistic Average \
     --period 60 \
     --threshold 1 \
     --comparison-operator GreaterThanOrEqualToThreshold \
     --evaluation-periods 2 \
     --alarm-actions arn:aws:sns:us-east-1:123:devops-alerts
   ```

3. **Log Aggregation**:
   ```bash
   # Stream logs to CloudWatch
   aws logs create-log-group --log-group-name /aws/ecs/gym-app

   # Query logs
   aws logs tail /aws/ecs/gym-app --follow

   # Filter for errors
   aws logs filter-log-events \
     --log-group-name /aws/ecs/gym-app \
     --filter-pattern "ERROR" \
     --start-time $(date -d '1 hour ago' +%s)000
   ```

4. **Performance Metrics to Track**:
   - [ ] API endpoint latency (P50, P95, P99)
   - [ ] Database query time
   - [ ] Cache hit rate (if using Redis)
   - [ ] Concurrent user count
   - [ ] Request throughput (requests/second)

5. **Deployment Tags for Traceability**:
   ```bash
   # Tag Docker image
   docker tag gym-app:latest gym-app:v1.2.3-$(git rev-parse --short HEAD)
   docker tag gym-app:latest gym-app:deployed-$(date +%Y%m%d-%H%M%S)

   # Tag in ECS task definition
   "tags": [
     {"key": "Version", "value": "1.2.3"},
     {"key": "DeployedBy", "value": "CI/CD"},
     {"key": "DeployedAt", "value": "2023-12-13T10:30:00Z"},
     {"key": "GitCommit", "value": "abc123def"}
   ]
   ```

---

## Rollback Procedure **Skill**: /devops-cicd

**Rollback Decision Criteria**:
Initiate rollback immediately if ANY of the following occur:
- ⛔ Health check fails (HTTP 503/500)
- ⛔ 5xx error rate > 1% of requests
- ⛔ P95 response time > 2x baseline
- ⛔ Critical API endpoint down > 2 minutes
- ⛔ Database connection failures

**Automated Rollback** (if using blue-green):
```bash
# 1. Switch traffic back to blue (previous version)
aws elbv2 modify-listener \
  --listener-arn $LISTENER_ARN \
  --default-actions Type=forward,TargetGroupArn=$BLUE_TARGET_GROUP_ARN

# 2. Verify traffic switched
aws elbv2 describe-target-health --target-group-arn $BLUE_TARGET_GROUP_ARN

# 3. Check health
curl -f https://gym-app.example.com/health

# 4. Monitor error rate (should drop to 0)
watch -n 5 'aws cloudwatch get-metric-statistics ...'
```

**Manual Rollback** (Docker/ECS):
```bash
# 1. Identify previous working image
aws ecr describe-images \
  --repository-name gym-app \
  --query 'sort_by(imageDetails,& imagePushedAt)[-2]' \
  --output json

# 2. Update ECS service to previous task definition
aws ecs update-service \
  --cluster gym-app-cluster \
  --service gym-app-service \
  --task-definition gym-app:42  # Previous revision

# 3. Wait for deployment
aws ecs wait services-stable \
  --cluster gym-app-cluster \
  --services gym-app-service

# 4. Verify rollback
curl -f https://gym-app.example.com/health
```

**Database Rollback** (if migrations applied):
```bash
# Database rollback
{{CAPABILITIES_DB_ROLLBACK}}

# Verify downgrade
psql -h prod-db.example.com -U postgres -d gym_app -c "\dt"
```

**Post-Rollback Actions**:
1. [ ] Notify stakeholders (Slack #incidents channel)
   ```bash
   curl -X POST $SLACK_WEBHOOK_URL -H 'Content-type: application/json' \
     --data '{"text":"🚨 Deployment rolled back to previous version due to [REASON]"}'
   ```
2. [ ] Create incident report (`docs/incidents/YYYY-MM-DD-rollback.md`)
3. [ ] Tag failed deployment in Git:
   ```bash
   git tag -a failed-deploy-$(date +%Y%m%d-%H%M) -m "Deployment failed: [reason]"
   git push origin --tags
   ```
4. [ ] Schedule post-mortem within 48 hours
   - Root cause analysis
   - Action items to prevent recurrence
   - Update deployment checklist

**Rollback Testing** (quarterly):
- [ ] Scheduled rollback drill in staging
- [ ] Document time to rollback (target: < 5 minutes)
- [ ] Update procedure if any steps fail

---

## Anti-patterns to Avoid
- ❌ Deploying on Fridays
- ❌ Skipping staging environment
- ❌ Manual deployment steps not documented
- ❌ No rollback plan
- ❌ Secrets in code or logs
