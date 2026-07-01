---
name: security-audit
description: Expert security audit agent specialized in identifying vulnerabilities and security risks following OWASP guidelines.
skill_type: universal
version: 1.0.0
---

# Security Audit

Systematically identify, assess, and mitigate security risks in the application's backend API and frontend presentation layers. Focuses on data protection (PII), financial integrity, and API security.

## Core Audit Workflow

### 1. Data Protection & Privacy (PII)
**Target**: Sensitive entities (e.g., profiles, contact information, personal identifiers).
- **Check**: Are emails, phone numbers, and addresses encrypted at rest or properly access-controlled?
- **Action**: Verify `IDOR` prevention (a client cannot access another client's profile/resources by changing the resource ID in the request parameters).

### 2. Financial Integrity
**Target**: Financial records and transaction entities (e.g., invoices, payments, subscriptions).
- **Check**: Can a client view another client's invoice/payment? Can a staff member modify a transaction without proper audit logs?
- **Action**: Audit `Business Logic Flaws` (e.g., negative amounts in payments, double-spending or double-booking patterns specific to your domain).

### 3. API Security & RBAC Enforcement
**Target**: API routes and endpoints (e.g., in your API route layer).
- **Check**: Are all endpoints protected by appropriate authorization and permission checks?
- **Action**: 
  - Ensure all non-public endpoints require an explicit permission or role dependency.
  - Verify that the `SYSTEM_ADMIN` (or equivalent always-allowed role) short-circuit bypass is preserved cleanly and not bypassed.
  - Ensure role checks use strict enums, not raw strings.
  - Confirm table isolation: staff and members/clients authenticate against distinct tables/entities.

### 4. Input Validation (Poka-Yoke)
**Target**: Payload schemas and models (e.g., in your DTO layer).
- **Check**: Do strings have length limits? Are email formats validated using proper schema validators?
- **Action**: Ensure inconsistent validation (e.g., validation in UI but not in API) is eliminated.

---

## 🛡️ Top Vulnerability Checklist

| OWASP | Vulnerability | Example Risk | Mitigation |
|-------|---------------|-------------|------------|
| **A01** | Broken Access Control | Client viewing other client invoices | Object-level auth check in Service layer |
| **A02** | Cryptographic Failures | Passwords stored in plaintext | Use strong hashing (`bcrypt`, `argon2`) |
| **A03** | Injection | SQLi in Search endpoints | Parameterized queries (SQLAlchemy ORM) |
| **A04** | Insecure Design | Brute-forcing user login | Rate limiting on auth endpoints |
| **A05** | Misconfiguration | CORS allowing `*` origins | Explicitly allowlist application domains |
| **A07** | Auth Failures | Session Fixation | Regenerate tokens on login |
| **A10** | SSRF | Webhooks targeting internal IPs | URL allowlisting for callbacks |

---

## ⚠️ High-Risk Escalation Triggers

> [!WARNING]
> Modifying authentication, authorization, RBAC code, or endpoint protection logic is a **high-risk change**.
> In accordance with `governance.md §2`, any commit that modifies these patterns must trigger an escalation for mandatory human review.

---

## 🚫 Rationalisations to Reject (Anti-Rationalisation)

| Excuse / Rationalisation | Why it fails / Rebuttal |
|--------------------------|-------------------------|
| "This endpoint is only used by the frontend team, so we don't need a permission check." | Endpoints can be called directly by anyone using curl or API tools. Every endpoint must have backend authorization. |
| "SYSTEM_ADMIN is an admin, so we should map it to permissions in the database query." | An admin short-circuit is a system safety invariant that must bypass database matrix queries to prevent lockout when DB maps are corrupted. |
| "I'll do the IDOR check in the next pull request, this is just a quick CRUD setup." | Security controls like IDOR validation must land alongside the creation of the endpoint. |
