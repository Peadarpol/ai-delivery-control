# Specification: SPEC-XXX — [Feature Title]

**Source Issue**: [GitHub/Jira/Linear URL or #number]
**Date**: YYYY-MM-DD
**Author**: [Your Name / Role]

---

## 1. Goal & Context
Provide a brief, high-level description of what the feature accomplishes, why it is needed, and any business context or user needs driving this work.

---

## 2. Bounded Scope & Out of Scope
Clearly demarcate the boundaries of this feature to prevent scope creep.

### In Scope
- Item 1
- Item 2

### Out of Scope
- Item 1 (e.g. Mobile app support, offline synchronization, etc.)

---

## 3. Assumptions
All unstated assumptions surfaced during requirements intake must be resolved and prefixed. 
*Note: Any entry left in `[Pending]` state blocks the final APPROVED status.*

### Format Rule
Each non-empty assumption line must be a bullet point starting with either `[Resolved: ...]` or `[Pending: ...]`. Any bullet point lacking these prefixes represents a floating assumption and will fail Pass 1 static checks.

- [Resolved: Auth handled by existing middleware] User must be logged in.
- [Resolved: promoted to criterion #1] Session timeout must be configured.
- [Resolved: declared out of scope] Offline mode.

---

## 4. Acceptance Criteria (BDD / Gherkin format)
All functional requirements must be expressed as concrete, testable Gherkin scenarios. 
*Note: Each scenario must contain at least one occurrence of **each** of the three essential keywords: Given, When, and Then.*

```gherkin
Scenario: [Successful scenario description]
  Given [initial state or preconditions]
  And [additional preconditions]
  When [an event or action occurs]
  Then [expected outcome or postconditions]
  And [additional postconditions]
```

---

## 5. Architectural Constraints
Identify any architectural invariants, layer boundaries, or system constraints this feature must adhere to.

- [HIGH_RISK_SCHEMA_CHANGE] (Include this exact tag if this specification proposes database schema modifications, migration sequences, or transaction isolation alterations to elevate the Pass 2 LLM scrutiny).

### 5.1 Cross-Boundary Coupling Declaration
*Advisory (not gate-enforced). Vocabulary is defined in `.agent/governance.md` §8.*

State whether this feature introduces or strengthens a dependency that crosses a declared architectural boundary (layer, module, service, or bounded context). If it does not, write `[NO_NEW_COUPLING]` and move on.

For each new or strengthened cross-boundary dependency, add one `[COUPLING]` block:

- [COUPLING]
  - **Boundary crossed**: [e.g. Booking module → Entitlement module]
  - **Strength**: [intrusive | functional | model | contract] (governance.md §8.1)
  - **Distance**: [same-module | cross-module | cross-service | cross-team] (§8.2)
  - **Volatility**: [low | medium | high] — how often the shared thing is expected to change (§8.3)
  - **Rationale**: Why this strength is acceptable at this distance for this volatility. If strength is high AND distance is long AND volatility is not low, justify explicitly or redesign.

---

## 6. Decisions (ADRs referenced)
List any active Architectural Decision Records (ADRs) this feature implements or relates to (e.g., `branch_isolation`, `repository_pattern`). If a `[COUPLING]` block in §5.1 represents a deliberate, standing exception, reference its Coupling Decision Record ID here once that mechanism exists (e.g. `CDR-004`).

---

## 7. Status & Sign-off
Consistent parse target for the specification quality gate. Set status to `APPROVED` only when all assumptions are resolved and the spec is ready for development.

**Status**: DRAFT
**Signed-off by**: [Human Architect Name]
**Sign-off Date**: YYYY-MM-DD

