---
name: security-audit
description: Expert security audit agent specialized in identifying vulnerabilities and security risks following OWASP guidelines.
skill_type: universal
version: 1.0.0
---

# Security Audit

## Purpose

Systematically identify, assess, and mitigate security risks in the application's FastAPI backend and frontend. Focuses on data protection (PII), financial integrity (Invoices/Payments), and API security.

## Core Audit Workflow

### 1. Data Protection & Privacy (PII)
**Target**: `User`, `Staff`, `Contact` entities.
- **Check**: Are emails, phone numbers, and addresses encrypted at rest or properly access-controlled?
- **Action**: Verify `IDOR` prevention (User A cannot access User B's profile by changing the `user_id` in the URL).

### 2. Financial Integrity
**Target**: `Invoice`, `Payment`, `Contract` entities.
- **Check**: Can a user view another's invoice? Can a staff member modify an invoice without proper audit logs?
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

## 🛡️ Top Vulnerability Checklist

| OWASP | Vulnerability | Example Risk | Mitigation |
|-------|---------------|-------------|------------|
| **A01** | Broken Access Control | User viewing other invoices | Object-level auth check in Service layer |
| **A02** | Cryptographic Failures | Passwords stored in plaintext | Use `passlib` with `bcrypt` / `argon2` |
| **A03** | Injection | SQLi in Staff Search | Parameterized queries (SQLAlchemy) |
| **A04** | Insecure Design | Brute-forcing user login | Rate limiting on `/api/token` |
| **A05** | Misconfiguration | CORS allowing `*` origins | Explicitly allowlist application domains |
| **A07** | Auth Failures | Session Fixation | Regenerate tokens on login |
| **A10** | SSRF | Webhooks targeting internal IPs | URL allowlisting for callbacks |

---

## 📑 Resources

- [OWASP Top 10 Reference](https://owasp.org/www-project-top-ten/): Industry standard for web security.

## Remember
- **Assume Breach**: Design for when a component fails.
- **Least Privilege**: Only grant the permissions necessary for the task.
- **Defense in Depth**: Validate at the API, Service, and Repository layers.
