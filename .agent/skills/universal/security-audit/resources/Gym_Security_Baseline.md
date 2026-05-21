# Gym App Security Baseline

This document defines the baseline security requirements for handling sensitive data within the Gym App.

## 1. Member PII (Personally Identifiable Information)

**Requirement**: Absolute isolation of member data.
- **Access Control**: Every service method that accepts a `member_id` must verify that the `current_user` has permission to access that specific member (Self or Admin/Staff).
- **Audit Logging**: Any update to member profiles (`email`, `phone`, `emergency_contact`) must be logged with the timestamp and the identity of the modifier.
- **Sanitization**: All member-provided strings (notes, biographies) must be sanitized to prevent Stored XSS.

## 2. Invoice & Payment Integrity

**Requirement**: Immutability of financial records.
- **State Guarantee**: Once an invoice is marked as `PAID`, its `amount`, `member_id`, and `date` should be immutable at the database layer (if possible) or strictly protected in the Service layer.
- **Refund Policy**: Refunds must be processed as separate `CreditNote` or `Refund` entities, never by modifying the original `Invoice` amount.
- **IDOR Check**: Accessing `GET /invoices/{id}` MUST verify ownership.

## 3. Staff & Role Security

**Requirement**: Strict RBAC enforcement.
- **Role Hierarchy**:
    - `Member`: Can only access their own data.
    - `Staff`: Can access all members but cannot modify `SystemSettings` or delete `Invoices`.
    - `Admin`: Full access.
- **Elevation**: Changing a user's role to `Admin` must require confirmation or be logged as a critical security event.

## 4. API Hardening (Technical)

- **SQLAlchemy**: Use ORM relationships and avoids raw SQL strings for dynamic filters.
- **Pydantic**: Use `PositiveInt` and `PositiveFloat` for all financial and count fields.
- **Exceptions**: Use `DomainException` to avoid leaking stack traces in API responses.
