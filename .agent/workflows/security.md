<!-- NOTE: This file uses universal placeholders (e.g., {{PLACEHOLDER}}). Refer to .agent/config.yaml for project-specific values. -->
---
description: Security audit, vulnerability assessment, and hardening
---

# /security - Security Engineer Workflow

## 0. Pre-Task Anti-Hallucination Check
Before auditing or hardening, you **MUST** verify the security baseline:

| Artifact | Purpose | Placeholder |
| :--- | :--- | :--- |
| **RBAC Matrix** | Role permissions truth | `{{PATH_RBAC_MATRIX}}` |
| **Security Ops** | Secret rotation & audit policies | `{{PATH_SECURITY_OPS}}` |
| **Technical Spec** | Security architecture (Section 6) | `{{PATH_TECH_SPEC}}` |
| **API Docs** | Auth endpoints & public access | `{{PATH_API_DOCS}}` |

**Verification Steps:**
1. [ ] Check `{{PATH_RBAC_MATRIX}}` before modifying permissions.
2. [ ] Review Section 6 of `{{PATH_TECH_SPEC}}` to align with the existing auth flow.
3. [ ] If rotating secrets, follow the procedure in `{{PATH_SECURITY_OPS}}`.

## 0.1 Related Skills

> [!TIP]
> Load the following skill for enhanced security audit capabilities.

| Skill | Path | Use Case |
|-------|------|----------|
| **Security Audit** | `.agent/skills/security-audit/SKILL.md` | OWASP Top 10, vulnerability detection |

**Available Scripts:**
- `security_scan.py` - Run Bandit + Safety + custom secret checks
- `owasp_checklist.py` - Interactive OWASP Top 10 compliance checklist

**Example:**
```bash
# Run comprehensive security scan
poetry run python .agent/skills/security-audit/scripts/security_scan.py

# Run OWASP checklist (interactive)
poetry run python .agent/skills/security-audit/scripts/owasp_checklist.py
```

---

## Trigger
Use when: reviewing authentication, auditing for vulnerabilities, implementing security controls, or responding to incidents.

## Mindset
- **Assume breach** - design for when, not if
- **Defense in depth** - multiple layers, no single point of failure
- **Least privilege** - minimum access required
- **Validate everything** - never trust input

---

## AI EXECUTION MODE (Default)

**When to Use**: Default for all security audits, vulnerability assessments, and hardening tasks unless the user explicitly requests manual mode.

**Time Comparison**:
- **Manual (Human Security Engineer)**: 4-5 hours
- **AI Automated**: 37 min
- **User Time**: 10 min (review high/critical)

### Parallel Scan Execution

**AI runs all scans simultaneously** (15 min):

```bash
# All scans execute in parallel, no sequential waiting

# Scan 1: {{TECH_STACK_LINTER}} (SAST) - 2 min
{{CAPABILITIES_SECURITY_SCAN_SAST}} -f json -o bandit_report.json &

# Scan 2: Snyk (Dependencies + Containers) - 3 min
snyk test --severity-threshold=low --json > snyk_report.json &
snyk container test gym-app:latest --json > snyk_container.json &

# Scan 3: OWASP ZAP (Web App Scan) - 15 min
docker run zaproxy/zap-stable zap-full-scan.py \
  -t {{URL_BACKEND_LOCAL}} \
  -r zap_report.html &

# Scan 4: SQLmap (SQL Injection) - 10 min
sqlmap -u "{{URL_BACKEND_LOCAL}}/api/members?id=1" \
  --batch --level=3 --risk=2 \
  --output-dir=sqlmap_results &

# Wait for all scans to complete
wait
```

**AI Correlation Engine** (2 min):
- Deduplicates findings across tools
- Correlates related vulnerabilities
- Prioritizes by CVSS score and exploitability

### Auto-Remediation by Severity

**LOW/MEDIUM Severity** (AI fixes automatically, no user approval):

| Vulnerability | Auto-Fix | Example |
|---------------|----------|---------|
| Outdated dependency | Update to latest secure version | `requests==2.25.0` → `requests==2.31.0` |
| Missing input validation | Add Pydantic validation | Add `EmailStr`, `constr(min_length=1)` |
| SQL injection (obvious) | Parameterized queries | `f"SELECT * WHERE id={id}"` → `"SELECT * WHERE id=:id"` |
| XSS vulnerability | Auto-escape output | Add `escape()` to template variables |
| Missing security headers | Add to middleware | Add `Strict-Transport-Security`, `X-Content-Type-Options` |
| Weak password hashing | Upgrade to bcrypt | `hashlib.md5()` → `bcrypt.hashpw()` |
| Hardcoded secrets | Environment variables | Move to `.env` + add to `.gitignore` |

**Example Auto-Fix Report**:
```markdown
## 🔧 Auto-Fixed Security Issues (No Review Needed)

**Fixed 12 vulnerabilities automatically**:

### Dependency Updates (6 issues)
1. ✅ Updated `requests` 2.25.0 → 2.31.0 (CVE-2023-32681)
2. ✅ Updated `pillow` 9.0.0 → 10.1.0 (CVE-2023-44271)
3. ✅ Updated `sqlalchemy` 1.4.0 → 2.0.23 (CVE-2023-XX)
...

### Code Fixes (4 issues)
7. ✅ Added input validation to `/api/members` (email format)
8. ✅ Parameterized SQL query in `member_repository.py:42`
9. ✅ Added XSS escaping to member notes display
10. ✅ Replaced MD5 password hashing with bcrypt

### Configuration (2 issues)
11. ✅ Added security headers to FastAPI middleware
12. ✅ Moved API keys from code to environment variables

**Commits**:
- `fix(security): update dependencies with known vulnerabilities`
- `fix(security): add input validation and parameterized queries`
- `fix(security): improve password hashing and add security headers`
```

**HIGH/CRITICAL Severity** (User approval required):

```markdown
## ⚠️ CRITICAL Security Vulnerabilities - USER APPROVAL REQUIRED

### Finding 1: Authentication Bypass (CRITICAL)

**CVSS Score**: 9.8 (Critical)
**OWASP Category**: A07: Identification and Authentication Failures
**File**: `{{PATH_API_ROUTES}}/auth.py:67`

**Vulnerability**:
```python
def verify_token(token: str):
    # Missing signature verification!
    payload = jwt.decode(token, options={"verify_signature": False})
    return payload["user_id"]
```

**AI Proposed Fix** (Confidence: 0.98):
```python
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Impact**: Currently allows token forgery - any user can impersonate any other user
**Exploit Difficulty**: Trivial (requires only JWT library)
**Action**: [Approve Fix] [Manual Review] [Accept Risk]

---

### Finding 2: SQL Injection in Search (HIGH)

**CVSS Score**: 8.1 (High)
**OWASP Category**: A03: Injection
**File**: `{{PATH_API_ROUTES}}/members.py:91`

**Vulnerability**:
```python
def search_members(query: str):
    sql = f"SELECT * FROM members WHERE name LIKE '%{query}%'"
    return db.execute(sql)
```

**AI Proposed Fix** (Confidence: 0.95):
```python
def search_members(query: str):
    sql = "SELECT * FROM members WHERE name LIKE :query"
    return db.execute(sql, {"query": f"%{query}%"})
```

**Impact**: Allows database access/modification/deletion
**Exploit Difficulty**: Easy (common attack pattern)
**Action**: [Approve Fix] [Manual Review]
```

### Penetration Testing Automation

**AI Automated Penetration Tests** (no user intervention):

```bash
# OWASP Top 10 Automated Tests

# A01: Broken Access Control
# Test horizontal privilege escalation
curl -H "Authorization: Bearer <TOKEN>" \
  {{URL_BACKEND_LOCAL}}/api/members/user_B_id
# Expected: 403 Forbidden ✅

# A03: Injection - SQL Injection
sqlmap -u "{{URL_BACKEND_LOCAL}}/api/members?name=test" --batch
# Expected: No injection vectors found ✅

# A03: Injection - XSS
curl -X POST {{URL_BACKEND_LOCAL}}/api/members \
  -d '{"name": "<script>alert(1)</script>"}'
# Expected: Script escaped in output ✅

# A07: Authentication Failures
# Test brute force protection
for i in {1..20}; do
  curl -X POST {{URL_BACKEND_LOCAL}}/api/token \
    -d "username=admin&password=wrong$i"
done
# Expected: 429 Too Many Requests after ~10 attempts ✅

# A10: SSRF
curl -X POST {{URL_BACKEND_LOCAL}}/api/webhooks \
  -d '{"url": "http://169.254.169.254/latest/meta-data/"}'
# Expected: URL validation rejects internal IPs ✅
```

### Confidence-Based Escalation

**AI Auto-Fixes** (confidence ≥0.90 AND severity ≤MEDIUM):
- Dependency updates
- Input validation additions
- SQL parameterization (simple cases)
- XSS output escaping
- Security header configuration

**User Approval Required** (confidence <0.90 OR severity >MEDIUM):
- Authentication/authorization logic changes
- Cryptography changes
- Complex SQL injection fixes
- API contract modifications

---

## Phase 1: Threat Modeling **Skill**: /security-audit

1. Identify assets and threat actors:

| Asset | Sensitivity | Threat Actor | Attack Vector |
|-------|-------------|--------------|---------------|
| User credentials | Critical | External attacker | Credential stuffing |
| Member data | High | Insider | Data exfiltration |
| Session tokens | High | External attacker | XSS, session hijacking |

2. **OWASP Top 10 Validation** (2021):

#### A01: Broken Access Control

**Test for Horizontal Privilege Escalation (IDOR)**:
```bash
# Login as User A (ID=1)
TOKEN_A=$(curl -X POST {{URL_BACKEND_LOCAL}}/api/token \
  -d "username=user_a&password=pass" | jq -r '.access_token')

# Attempt to access User B's data (ID=2)
curl -H "Authorization: Bearer $TOKEN_A" \
  {{URL_BACKEND_LOCAL}}/api/members/2

# Expected: 403 Forbidden (not User A's data)
# Vulnerability: 200 OK with User B's data
```

**Test for Vertical Privilege Escalation**:
```bash
# Login as regular user
TOKEN_USER=$(curl -X POST {{URL_BACKEND_LOCAL}}/api/token \
  -d "username=member&password=pass" | jq -r '.access_token')

# Attempt to access admin endpoint
curl -H "Authorization: Bearer $TOKEN_USER" \
  {{URL_BACKEND_LOCAL}}/api/admin/users

# Expected: 403 Forbidden
# Vulnerability: 200 OK (regular user accessing admin function)
```

---

#### A02: Cryptographic Failures

**Test for Sensitive Data Over HTTP**:
```bash
# Use proxy to intercept traffic
# If using Burp Suite or OWASP ZAP:
# 1. Configure proxy (localhost:8080)
# 2. Attempt login over HTTP
curl -v http://localhost:8000/api/token \
  -d "username=admin&password=secret"

# Check response: Should redirect to HTTPS or refuse connection
# Vulnerability: Credentials transmitted in plaintext
```

**Test Password Storage**:
```python
# Connect to database and check password hashing
import psycopg2
conn = psycopg2.connect("dbname={{TECH_STACK_DB_NAME}}")
cursor = conn.execute("SELECT password_hash FROM staff LIMIT 1")
hash_value = cursor.fetchone()[0]

# Good: bcrypt/argon2 hash (starts with $2b$ or $argon2)
# Bad: MD5 (32 hex chars), SHA1 (40 hex chars), plaintext
print(f"Hash algorithm: {hash_value[:10]}")
```

---

#### A03: Injection

**Test for SQL Injection**:
```bash
# Test in search/filter endpoints
curl "http://localhost:8000/api/members?name=test' OR '1'='1"

# Test with UNION attack
curl "http://localhost:8000/api/members?id=1 UNION SELECT password_hash FROM staff--"

# Expected: Parameterized queries prevent injection
# Vulnerability: Error messages revealing SQL syntax or data leak
```

**Test for XSS (Cross-Site Scripting)**:
```bash
# Stored XSS test
curl -X POST http://localhost:8000/api/members \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "first_name": "<script>alert(document.cookie)</script>",
    "last_name": "Test",
    "email": "test@example.com"
  }'

# Retrieve and check if script executes
# Expected: Data sanitized, script rendered as text
# Vulnerability: Script executes in browser
```

---

#### A04: Insecure Design

**Test for Rate Limiting**:
```bash
# Brute-force attempt on login endpoint
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/token \
    -d "username=admin&password=wrong$i" &
done
wait

# Expected: 429 Too Many Requests after ~5-10 attempts
# Vulnerability: All 100 requests succeed
```

**Test for Business Logic Flaws**:
```bash
# Example: Apply same discount code multiple times
curl -X POST http://localhost:8000/api/transactions \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"amount": 100, "discount_code": "SAVE20"}'

# Repeat same request
curl -X POST http://localhost:8000/api/transactions \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"amount": 100, "discount_code": "SAVE20"}'

# Expected: Discount code marked as used, second request rejected
# Vulnerability: Discount applied twice
```

---

#### A05: Security Misconfiguration

**Test for Debug Mode in Production**:
```bash
# Trigger error and check response
curl http://localhost:8000/api/nonexistent

# Vulnerability: Stack trace, file paths, framework version exposed
# Expected: Generic error message
```

**Test Security Headers**:
```bash
curl -I https://gym-app.example.com

# Check for:
# - Strict-Transport-Security: max-age=31536000
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: DENY
# - Content-Security-Policy: default-src 'self'
```

---

#### A06: Vulnerable and Outdated Components

- [ ] Maintain component inventory (see Phase 2, step 6)
- [ ] Cross-reference with CVE databases
- [ ] Remove unused dependencies
- [ ] Regular patching schedule

---

#### A07: Identification and Authentication Failures

**Test for Weak Password Policy**:
```bash
# Attempt to create account with weak password
curl -X POST http://localhost:8000/api/register \
  -d '{"username": "test", "password": "123"}'

# Expected: 400 Bad Request (password too weak)
# Vulnerability: Account created successfully
```

**Test for Session Fixation**:
```bash
# Get session ID before login
SESSION_1=$(curl -c - http://localhost:8000/ | grep session_id | awk '{print $7}')

# Login with session ID
curl -b "session_id=$SESSION_1" -X POST http://localhost:8000/api/token \
  -d "username=admin&password=pass"

# Get new session ID after login
SESSION_2=$(curl -b "session_id=$SESSION_1" -c - http://localhost:8000/api/profile | grep session_id)

# Expected: New session ID issued after login
# Vulnerability: Same session ID before and after login
```

---

#### A08: Software and Data Integrity Failures

- [ ] Verify software update mechanism uses digital signatures
- [ ] Test for insecure deserialization
- [ ] Check CI/CD pipeline security
- [ ] Validate repository vetting

---

#### A09: Security Logging and Monitoring Failures

- [ ] Review log contents (login attempts, access failures, errors)
- [ ] Test for missing logging (perform attacks, check if logged)
- [ ] Assess monitoring and alerting
- [ ] Check log retention and protection

---

#### A10: Server-Side Request Forgery (SSRF)

**Test for Internal IP Access**:
```bash
# If app has URL input (e.g., webhook, image URL)
curl -X POST http://localhost:8000/api/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"callback_url": "http://127.0.0.1:8000/admin"}'

# Expected: URL validation rejects internal IPs
# Vulnerability: Request sent to internal endpoint
```

**Test for Cloud Metadata Access**:
```bash
# On AWS EC2
curl -X POST http://localhost:8000/api/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"callback_url": "http://169.254.169.254/latest/meta-data/"}'

# Expected: Blocked
# Vulnerability: Metadata endpoint accessible
```

---

## Phase 2: Code Audit **Skill**: /security-audit

3. Authentication review:
   - [ ] Password hashing (bcrypt, argon2, not MD5/SHA1)
   - [ ] Session management (secure cookies, expiration)
   - [ ] Token handling (JWT validation, refresh tokens)
   - [ ] MFA implementation if applicable

4. Authorization review:
   - [ ] Role-based access control (RBAC) implemented
   - [ ] Object-level authorization (can user X access resource Y?)
   - [ ] Function-level authorization (can user X perform action Z?)

5. Input validation:
   - [ ] All user input sanitized
   - [ ] Parameterized queries (no SQL injection)
   - [ ] Output encoding (XSS prevention)
   - [ ] File upload restrictions
   - [ ] **License Check**: Ensure no GPL/copyleft libraries in proprietary code.

// turbo
6. **Automated Security Scanning**:

**A. Bandit (Python SAST)**:
```bash
# Basic scan with JSON output
{{CAPABILITIES_SECURITY_SCAN_SAST}} -f json -o security_report.json

# Filter by severity (only High)
{{CAPABILITIES_SECURITY_SCAN_SAST}} --severity-level high

# Exclude specific paths
{{CAPABILITIES_SECURITY_SCAN_SAST}} --exclude {{PATH_TEST_ROOT}}/,{{PATH_SCRIPTS}}/

# CI/CD integration (fail on High severity)
{{CAPABILITIES_SECURITY_SCAN_SAST}} -ll -ii || exit 1  # Exit code 1 if issues found

# Generate HTML report
{{CAPABILITIES_SECURITY_SCAN_SAST}} -f html -o security_report.html
```

**B. Snyk (Dependency & Container Scanning)**:
```bash
# Install Snyk CLI
npm install -g snyk

# Authenticate (set SNYK_TOKEN env var in CI)
snyk auth

# Test dependencies for vulnerabilities
snyk test --severity-threshold=high

# Monitor project (continuous scanning)
snyk monitor

# Test Docker image
docker build -t gym-app:latest .
snyk container test gym-app:latest

# Test Infrastructure as Code (Terraform/Kubernetes)
snyk iac test terraform/

# Generate JSON report
snyk test --json > snyk_report.json
```

**C. Safety (Python Dependency Vulnerability Check)**:
```bash
# Check dependencies against CVE database
{{CAPABILITIES_SECURITY_SCAN_DEPS}}

# Output as JSON
{{CAPABILITIES_SECURITY_SCAN_DEPS}} --json

# Fail build on vulnerabilities
{{CAPABILITIES_SECURITY_SCAN_DEPS}} --exit-code 1
```

**D. CI/CD GitHub Actions Example**:
```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r src/ -ll -ii -f json -o bandit_report.json

      - uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

      - name: Upload Security Reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-reports
          path: |
            bandit_report.json
            snyk_report.json
```

---

## Phase 3: Configuration Audit **Skill**: /security-audit

7. Environment security:
   - [ ] Secrets not in code (use env vars or vault)
   - [ ] Debug mode disabled in production
   - [ ] HTTPS enforced
   - [ ] CORS properly configured
   - [ ] Security headers present (CSP, HSTS, X-Frame-Options)
   - [ ] **Container Hardening**: Run as non-root? Minimal base image?

8. Dependency audit:
   - [ ] No known vulnerabilities in dependencies
   - [ ] Dependencies pinned to specific versions
   - [ ] Regular update schedule defined

---

## Phase 4: Security Testing **Skill**: /security-audit

9. **Penetration Testing Checklist**:

**Recommended Tools**:
- **OWASP ZAP** (Web Application Scanner)
- **Burp Suite Community** (Proxy & Scanner)
- **SQLmap** (SQL Injection)
- **Nikto** (Web Server Scanner)

#### A. Automated Scanning with OWASP ZAP

```bash
# Install OWASP ZAP
docker pull zaproxy/zap-stable

# Baseline scan (passive)
docker run -v $(pwd):/zap/wrk/:rw -t zaproxy/zap-stable \
  zap-baseline.py -t http://localhost:8000 \
  -r zap_baseline_report.html

# Full scan (active, more aggressive)
docker run -v $(pwd):/zap/wrk/:rw -t zaproxy/zap-stable \
  zap-full-scan.py -t http://localhost:8000 \
  -r zap_full_report.html

# API scan
docker run -v $(pwd):/zap/wrk/:rw -t zaproxy/zap-stable \
  zap-api-scan.py -t http://localhost:8000/openapi.json \
  -f openapi -r zap_api_report.html
```

#### B. SQL Injection Testing with SQLmap

```bash
# Install SQLmap
git clone https://github.com/sqlmapproject/sqlmap.git

# Test specific parameter
python3 sqlmap/sqlmap.py -u "http://localhost:8000/api/members?id=1" \
  --cookie="session_id=abc123" \
  --level=3 --risk=2

# Test all parameters
python3 sqlmap/sqlmap.py -u "http://localhost:8000/api/members" \
  --forms --batch

# Dump database (if vulnerable)
python3 sqlmap/sqlmap.py -u "http://localhost:8000/api/members?id=1" \
  --dump -T members
```

#### C. Manual Testing Checklist

| Test | Tool | Command/Steps | Expected Result |
|------|------|---------------|-----------------|
| SQL Injection | cURL | `curl "http://localhost:8000/api/members?name=test' OR '1'='1"` | Parameterized query prevents injection |
| XSS | Browser | Input `<script>alert(1)</script>` in form fields | Script escaped/sanitized |
| CSRF | Burp Suite | Remove/modify CSRF token in POST request | Request rejected |
| Session Fixation | cURL | Reuse session ID after logout | Session invalidated |
| Path Traversal | cURL | `curl "http://localhost:8000/api/files?path=../../etc/passwd"` | Access denied |
| HTTP Verb Tampering | cURL | `curl -X DELETE http://localhost:8000/api/members/1` (without auth) | 401 Unauthorized |

10. **Security Findings Report Template**:

Create `docs/security/findings-YYYY-MM-DD.md`:

```markdown
## Security Assessment Report

**Date**: 2023-12-15
**Assessor**: [Name]
**Scope**: Gym Management System v1.2.0
**Methodology**: OWASP Top 10, Automated Scanning (Bandit, Snyk, OWASP ZAP), Manual Penetration Testing

### Executive Summary
- **Total Findings**: 8
- **Critical**: 1
- **High**: 2
- **Medium**: 3
- **Low**: 2
- **Risk Score**: 7.2/10 (High Risk)

---

### Detailed Findings

| ID | Finding | Severity | CVSS | OWASP | Affected Component | Status |
|----|---------|----------|------|-------|-------------------|--------|
| SEC-001 | SQL Injection in member search | Critical | 9.8 | A03 | `{{PATH_API_ROUTES}}/members.py:42` | Open |
| SEC-002 | Weak password policy | High | 7.5 | A07 | `{{PATH_DOMAIN}}/schemas.py` | Open |
| SEC-003 | Missing rate limiting | High | 7.0 | A04 | `/api/token` endpoint | Open |

---

### SEC-001: SQL Injection in Member Search (CRITICAL)

**CVSS Score**: 9.8 (Critical)
**OWASP Category**: A03: Injection
**CWE**: CWE-89

**Description**:
The member search endpoint (`GET /api/members?name=...`) is vulnerable to SQL injection. User input is directly interpolated into the SQL query without parameterization.

**Proof of Concept**:
```bash
curl "http://localhost:8000/api/members?name=test' UNION SELECT password_hash FROM staff--"
```

**Impact**:
- Unauthorized data access (entire database)
- Data modification/deletion
- Potential remote code execution

**Affected Code** (`{{PATH_API_ROUTES}}/members.py:42`):
```python
# Vulnerable code
query = f"SELECT * FROM members WHERE name LIKE '%{name}%'"
```

**Remediation**:
```python
# Fixed code (parameterized query)
query = "SELECT * FROM members WHERE name LIKE :name"
result = session.execute(query, {"name": f"%{name}%"})
```

**Timeline**:
- Discovered: 2023-12-10
- Reported: 2023-12-10
- Target Fix: 2023-12-12 (48 hours - CRITICAL)

**Verification**:
```bash
# After fix, re-test
curl "http://localhost:8000/api/members?name=test' OR '1'='1"
# Expected: No SQL injection, error or empty result
```
```

---

## Phase 5: Hardening **Skill**: /security-audit

11. Implement security controls:
    - [ ] Rate limiting on auth endpoints
    - [ ] Account lockout after failed attempts
    - [ ] Security logging and monitoring
    - [ ] Incident response procedures

12. Documentation:
    - [ ] Security policy document
    - [ ] Incident response runbook
    - [ ] Security contact information

---

## Anti-patterns to Avoid
- ❌ Security through obscurity
- ❌ Rolling your own crypto
- ❌ Storing passwords in plaintext or reversible encryption
- ❌ Trusting client-side validation
- ❌ Logging sensitive data

---

## Phase 6: Issue Lifecycle & Project Board **Skill**: /project-manager

**Goal**: Ensure security findings are tracked and closed properly on the Project Board.

13. **Finding to Issue**:
    - When a finding is confirmed, ensure a GitHub Issue exists.
    - Label: `security`, `priority:critical|high|medium|low`.

14. **Start Remediation**:
    - Move Issue to "In Progress".
    - `{{CAPABILITIES_GITHUB_ISSUE_MANAGER}}` update-phase --issue <ID> --phase implementation

15. **Technical Review**:
    - Create PR with fix.
    - Move to "Technical Review".
    - `{{CAPABILITIES_GITHUB_ISSUE_MANAGER}}` add-tech-review --issue <ID> --pr <PR#>

16. **Troubleshooting**:
    - If card status fails to update, refer to `.github/GITHUB_OPERATIONS.md`.
