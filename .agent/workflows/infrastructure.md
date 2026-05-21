---
description: Cloud setup, scaling, networking, and reliability
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Cloud setup, scaling, networking, and reliability
---

# /infra - Infrastructure Engineer Workflow

## Trigger
Use when: provisioning cloud resources, designing network topology, optimizing costs, or setting up disaster recovery.

## Mindset
- **Reliability** - design for failure; assume everything breaks
- **Scalability** - build systems that grow without redesign
- **Security** - least privilege, network isolation by default
- **Cost-Aware** - efficient resource usage, no zombie resources

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all cloud provisioning, network design, and infrastructure optimization tasks unless the user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human)**: ~9 hours
- **AI Automated**: ~15 min
- **User Time**: 5 min (approvals only)

### Automated Infrastructure Audits

**AI runs full audit in parallel** (2 min):

```bash
# Automated Compliance Checks
- ✅ VPC Layout audit (Subnets, Route Tables, IGW)
- ✅ Security Group "Least Privilege" scan (No open 0.0.0.0/0 on SSH)
- ✅ IAM Role Policy check (No AdministratorAccess on instances)
- ✅ S3 Bucket Public Access check
- ✅ Unused Resource Identification (Zombie volumes/IPs)
```

**Auto-Fix Recommendations**:
- "Found open SSH port 22 on SG `sg-12345`. **Action**: Restrict to `10.0.0.0/16` (VPN)?"
- "Found unattached EBS volume `vol-67890`. **Action**: Snapshot and delete to save $15/mo?"

### User Approval Checkpoints

**Always Require User Approval**:
1.  **Destructive Actions**:
    ```markdown
    ## ⚠️ Destructive Change Detected

    **Action**: Destroy RDS Database `gym-db-prod`
    **Reason**: Terraform state mismatch / Refactor

    **Are you SURE?** (Requires manual "YES" confirm)
    ```

2.  **Cost Implications**:
    - "New ASG configuration involves `m5.large` instances. Estimated increase: +$45/mo. Approve?"

3.  **Network Changes**:
    - "Modifying Route Tables for Production VPC. Approve?"

**Never Require User Approval** (AI handles autonomously):
- Security group tightening (non-destructive)
- Tagging resources for cost allocation
- Log group retention updates
- Backup schedule creation

### Automated Optimization Triggers

**AI optimizes automatically when**:

| Trigger | Threshold | AI Action |
|---------|-----------|-----------|
| CPU Usage (EC2) | < 5% for 7 days | Recommend downsizing (e.g., t3.medium -> t3.micro) |
| EBS Throughput | < 10% provisioned | Switch IO1 -> GP3 to save cost |
| S3 Object Age | > 90 days | Move to Glacier Instant Retrieval |
| Lambda Duration | < 50% timeout | Tighten timeout setting |

### Confidence Scoring for IaC

**AI Confidence levels**:
- **0.99 (High)**: Tag updates, non-breaking security fixes. *Auto-apply enabled.*
- **0.80 (Medium)**: Instance type changes, scaling policy updates. *User review recommended.*
- **0.50 (Low)**: VPC peering, complex routing, data store replacements. *User review MANDATORY.*

---

## Phase 1: Infrastructure Assessment **Skill**: /senior-architect

// turbo
1. Audit current resources:
```bash
# List all running EC2 instances
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" --query "Reservations[*].Instances[*].{ID:InstanceId,Type:InstanceType,State:State.Name,Name:Tags[?Key=='Name']|[0].Value}" --output table

# Check RDS instances
aws rds describe-db-instances --query "DBInstances[*].{ID:DBInstanceIdentifier,Class:DBInstanceClass,Status:DBInstanceStatus,Engine:Engine}" --output table
```

2. Review Configuration:
   - [ ] VPC topology (subnets, route tables, IGW/NAT)
   - [ ] Security Groups (ingress/egress rules)
   - [ ] IAM Roles and Policies
   - [ ] Cost Explorer trends

---

## Phase 2: Design & Planning **Skill**: /senior-architect

3. Define Requirements:
   - **Compute**: CPU/RAM needs, scaling triggers (CPU > 70%?)
   - **Storage**: IOPS requirements, retention policies, backup frequency
   - **Network**: Public vs Private subnets, Load Balancer needs
   - **Recovery**: RTO (Time) and RPO (Point) targets

4. Selection Matrix:

| Feature | Option A (Simple) | Option B (Robust) | Option C (Serverless) |
|---------|-------------------|-------------------|-----------------------|
| **Compute** | EC2 (Single) | EC2 ASG + ALB | Fargate / Lambda |
| **DB** | RDS (Dev) | RDS Multi-AZ | Aurora Serverless |
| **Static** | S3 Public | S3 + CloudFront | S3 + CloudFront + WAF |
| **Cost** | Low | High | Variable |

**Recommendation for Gym App**: Option B (EC2 ASG + ALB + RDS) for production reliability.

---

## Phase 3: Implementation (Terraform) **Skill**: /devops-cicd

5. Infrastructure as Code Structure:
   ```hcl
   # main.tf - centralized definitions
   module "vpc" {
     source = "./modules/vpc"
     cidr_block = "10.0.0.0/16"
   }

   module "compute" {
     source = "./modules/compute"
     instance_type = var.instance_type
     vpc_id = module.vpc.vpc_id
   }
   ```

6. Provisioning Steps:
   - [ ] `terraform plan` - Verify proposed changes
   - [ ] Security Scan (tfsec/checkov)
   - [ ] `terraform apply` - Execute changes
   - [ ] Verify resource existence in AWS Console

---

## Phase 4: Reliability & Monitoring **Skill**: /devops-cicd

7. Health Checks:
   - Configuring ALB Health Checks (`/health` endpoint)
   - Setting up Route53 Failover routing

8. Disaster Recovery Setup:
   - [ ] Automate RDS snapshots (daily + retention)
   - [ ] Enable S3 Versioning & Cross-Region Replication (if critical)
   - [ ] Document recovery procedure in `docs/dr/recovery_playbook.md`

9. Cost Optimization & Sustainability:
   - [ ] Implement AWS Savings Plans/Reserved Instances for baseline load
   - [ ] Use Spot Instances for fault-tolerant workloads (e.g. CI runners)
   - [ ] Enable S3 Lifecycle Policies (Infrequent Access/Glacier)
   - [ ] Right-size instances based on CloudWatch metrics

10. Security Hardening (AWS Well-Architected):
    - [ ] Enable GuardDuty for threat detection
    - [ ] Use IAM Access Analyzer to verify least privilege
    - [ ] Rotate KMS keys annually
    - [ ] Enable WAF on ALB for public-facing endpoints

---

## Phase 5: Verification **Skill**: /devops-cicd

11. Observability Check:
    - [ ] X-Ray tracing enabled for API latency analysis
    - [ ] CloudWatch Alarms for 5xx errors > 1%
    - [ ] Log aggregation to CloudWatch Logs

12. Final Sign-off:
    - Infrastructure matches architecture diagram?
    - Security groups minimized?
    - Backups confirmed accessible?

---

## Phase 6: Issue Lifecycle & Project Board **Skill**: /project-manager

**Goal**: Keep the GitHub Project Board verified and up-to-date.

13. **Start Work**:
    - Move Issue to "In Progress".
    - `{{CAPABILITIES_GITHUB_ISSUE_MANAGER}}` update-phase --issue <ID> --phase implementation

14. **Technical Review**:
    - If Terraform changes involved:
    - Create PR.
    - Move to "Technical Review".
    - `{{CAPABILITIES_GITHUB_ISSUE_MANAGER}}` add-tech-review --issue <ID> --pr <PR#>`

15. **Troubleshooting**:
    - If card status fails to update, see `.github/GITHUB_OPERATIONS.md`.
