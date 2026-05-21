---
description: Deploy or teardown gym app to any environment with any branding
---

<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Deploy or teardown gym app to any environment with any branding
---

# Deployment Workflow

This workflow deploys the Gym Management System to various targets with configurable branding.

## Available Deployments

| Command | Target | Brand | Architecture |
|---------|--------|-------|--------------|
| `deploy local-momentum` | Local Docker | Momentum Fitness | All-in-one |
| `deploy local-anytime` | Local Docker | Anytime Fitness | All-in-one |
| `deploy local-iron-pumpers` | Local Docker | Iron Pumpers | All-in-one |
| `deploy aws-test-momentum` | AWS TEST | Momentum Fitness | Tiered (Web+API) |

## Configuration Files

- **Brands**: `environments/brands/<brand>.env`
- **Targets**: `environments/targets/<target>.env`
- **Manifest**: `environments/deploy.yaml`

---

## Local Deployment Steps **Skill**: /devops-cicd

1. Read deployment config from `environments/deploy.yaml`

2. Deploy local environment:
// turbo
```bash
{{CAPABILITIES_DEPLOY_RUN}} <deployment-name>
```

3. Verify services are running:
// turbo
```bash
docker ps
```

4. Access the application:
   - Frontend: http://localhost:8501/admin
   - Kiosk: http://localhost:8502
   - API Docs: http://localhost:8000/docs

---

## Local Teardown Steps **Skill**: /devops-cicd

1. Stop and remove containers:
// turbo
```bash
{{CAPABILITIES_DEPLOY_TEARDOWN}} <deployment-name>
```

---

## AWS Deployment Steps **Skill**: /devops-cicd

1. Ensure AWS credentials are configured

2. Deploy with infrastructure provisioning:
```bash
cd c:\projects\Gym_App
python scripts/deploy.py deploy aws-test-momentum --provision
```

3. Wait for Terraform to complete and note the output IPs

4. Access the application via the WEB_PUBLIC_IP

---

## AWS Teardown Steps **Skill**: /devops-cicd

1. Destroy infrastructure:
```bash
cd c:\projects\Gym_App
python scripts/deploy.py teardown aws-test-momentum --destroy
```

---

## Switching Brands **Skill**: /devops-cicd

To switch brands for the same target:
// turbo
```bash
python scripts/deploy.py teardown local-momentum
python scripts/deploy.py deploy local-iron-pumpers
```

---

## Troubleshooting

- **Connection refused**: Check if backend is running with `docker logs gym-backend`
- **Brand not applied**: Verify `.env.active` contains correct BRAND_NAME
- **AWS timeout**: Check security group allows inbound on ports 8501, 8502
