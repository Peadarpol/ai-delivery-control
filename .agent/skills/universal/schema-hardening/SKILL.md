---
name: schema-hardening
description: Expert review of Pydantic and data transfer schema validation constraints to prevent mass assignment vulnerabilities.
skill_type: universal
version: 1.0.0
---

# Schema Hardening & Input Validation

Expert guidelines to check input schemas (Pydantic models, JSON schemas) and prevent mass-assignment (CWE-915) or field-injection vulnerabilities.

## 🛡️ Hardening Rules

- **Mass Assignment Prevention (CWE-915)**: All public request-facing schemas must prevent extra/unexpected payload attributes. In Pydantic v2, declare `model_config = ConfigDict(extra="forbid")` or inherit from a project-wide hardened base class.
- **Strict Validation**: Always validate datatypes strictly (e.g. use specific types like `EmailStr`, `PositiveInt`, `Field(max_length=...)` instead of raw `str` or `int` attributes).
- **Safe Fallbacks**: Enum fields must validate against actual enum classes, preventing bypass of custom fallback logic in schemas.

## 🚫 Rationalisations to Reject (Anti-Rationalisation)

| Excuse / Rationalisation | Why it fails / Rebuttal |
|--------------------------|-------------------------|
| "Pydantic ignores extra parameters by default, so we don't need extra='forbid'." | Ignoring parameters allows clients to send unvalidated inputs that could silently bind to backend models or logic. Hard-failing is the safe poka-yoke design. |
| "I will add validation logic directly inside the repository layer later." | Input schemas at the boundary must validate payloads first before they reach any service or database layer. |
