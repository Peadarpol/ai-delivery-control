---
name: security-audit
description: Expert security audit agent specialized in identifying vulnerabilities and security risks following OWASP guidelines and Gym App specific requirements.
skill_type: universal
version: 1.0.0
---

# Security Audit (Gym App Edition)

## Purpose

Systematically identify, assess, and mitigate security risks in the Gym App's FastAPI backend and Streamlit frontend. Focuses on data protection (PII), financial integrity (Invoices/Payments), and API security.

## Core Audit Workflow

### 1. Data Protection & Privacy (PII)
**Target**: `Member`, `Staff`, `Contact` entities.
- **Check**: Are emails, phone numbers, and addresses encrypted at rest or properly access-controlled?
- **Action**: Verify `IDOR` prevention (User A cannot access User B's profile by changing the `member_id` in the URL).

### 2. Financial Integrity
**Target**: `Invoice`, `Payment`, `Contract` entities.
- **Check**: Can a member view another's invoice? Can a staff member modify an invoice without proper audit logs?
- **Action**: Audit `Business Logic Flaws` (e.g., negative amounts in payments, overlapping contract dates).

### 3. API Security (FastAPI)
**Target**: `src/application/api/` routes.
- **Check**: Are all endpoints protected by `fastapi.Depends(get_current_user)`?
- **Action**: Conduct `SQL Injection` audit (ensure SQLAlchemy ORM or parameterized queries are used exclusively).

### 4. Input Validation (Poka-Yoke)
**Target**: Pydantic models in `src/application/dtos/`.
- **Check**: Do strings have length limits? Are email formats validated using `EmailStr`?
- **Action**: Ensure `Inconsistent Validation` (e.g., validation in UI but not in API) is eliminated.

---

## 🛡️ Top Vulnerability Checklist (Gym-Specific)

| OWASP | Vulnerability | Gym App Risk | Mitigation |
|-------|---------------|-------------|------------|
| **A01** | Broken Access Control | Member viewing other invoices | Object-level auth check in Service layer |
| **A02** | Cryptographic Failures | Passwords stored in plaintext | Use `passlib` with `bcrypt` / `argon2` |
| **A03** | Injection | SQLi in Staff Search | Parameterized queries (SQLAlchemy) |
| **A04** | Insecure Design | Brute-forcing member login | Rate limiting on `/api/token` |
| **A05** | Misconfiguration | CORS allowing `*` origins | Explicitly allowlist Gym App domains |
| **A07** | Auth Failures | Session Fixation | Regenerate tokens on login |
| **A10** | SSRF | Webhooks targeting internal IPs | URL allowlisting for callbacks |

---

## 📑 Resources

- [Gym_Security_Baseline.md](resources/Gym_Security_Baseline.md): Detailed checklist for Members and Invoices.
- [OWASP Top 10 Reference](https://owasp.org/www-project-top-ten/): Industry standard for web security.

## Remember
- **Assume Breach**: Design for when a component fails.
- **Least Privilege**: Only grant the permissions necessary for the task.
- **Defense in Depth**: Validate at the API, Service, and Repository layers.
