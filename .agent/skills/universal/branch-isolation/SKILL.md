---
name: branch-isolation
description: Expert review of multi-tenant and branch isolation safety, ensuring no query data leaks or cross-tenant access.
skill_type: universal
version: 1.0.0
---

# Multi-Tenant & Branch Isolation

Expert guidelines to check that database queries and API routing enforce tenancy isolation. Every multi-tenant resource check-in, search, transaction, or update must be correctly scoped.

## 🛡️ Isolation Rules

- **Query Isolation Filtering**: All queries against tenant-scoped tables must explicitly filter by tenant ID / branch ID. Queries missing this scope pose a severe data-leakage risk.
- **Middleware Validation**: Tenancy identifiers passed via request headers or session cookies must be validated by middleware early in the request lifecycle. Avoid trusting a tenant identifier supplied in the body parameter of a request without validation.
- **Fail-Closed Queries**: In database helper functions and base repositories, assume isolation by default. Unscoped queries should be disallowed unless they match explicitly documented global exemptions.

## ⚠️ High-Risk Escalation Triggers

> [!WARNING]
> Modifying multi-tenant isolation logic, tenant resolving middleware, or global scope bypass rules are **high-risk changes**.
> In accordance with `governance.md §2`, any commit that modifies these patterns must trigger an escalation for mandatory human review.

## 🚫 Rationalisations to Reject (Anti-Rationalisation)

| Excuse / Rationalisation | Why it fails / Rebuttal |
|--------------------------|-------------------------|
| "We filter by tenant ID in the UI, so the API query doesn't need to duplicate it." | UI filters can be easily bypassed by direct API calls. All backend queries must enforce isolation. |
| "This is a super-admin operation, so we can ignore multi-tenant filters here." | Super-admins must still route queries through explicit system boundaries or validated admin endpoints. |
| "I'll add the database filter in the service layer next time, let's merge the repository change first." | Never allow unscoped database queries to enter the repository layer, even temporarily. |
