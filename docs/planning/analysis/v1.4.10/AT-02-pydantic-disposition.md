# AT-02 — Pydantic Dependency Disposition

This document provides a detailed analysis of the Pydantic import-time crash defect (**F2**) and the API key reachability discovery issue (**F-COLD-3**).

## 1. Pydantic Usage Inventory

Pydantic is imported at the top-level of [src/scripts/ai_review.py](file:///c:/projects/ai-delivery-control/src/scripts/ai_review.py#L33):
`from pydantic import BaseModel, Field, ValidationError`

It is also used in three sub-modules: [route_decision.py](file:///c:/projects/ai-delivery-control/src/scripts/route_decision.py), [rebuttal.py](file:///c:/projects/ai-delivery-control/src/scripts/rebuttal.py), and [gate_context.py](file:///c:/projects/ai-delivery-control/src/scripts/gate_context.py).

### Pydantic Models & Fields Injected

1. **`ReviewVerdict`** (Line 464 in `ai_review.py`):
   - `verdict`: `Literal["PASS", "WARN", "FAIL", "FAIL_OPEN", "PASS_FAST"]` (Checks that the response classification is recognized).
   - `blocking_concern`: `Optional[str]`
   - `concerns`: `List[str]` (Default: `[]`)
   - `route_decision`: `Optional[RouteDecision]` (Validates dynamic tool-routing results).
   - `planner_note`: `Optional[str]`
   - `fail_open_reason`: `Optional[str]`
   - `model`: `str`
   - `token_usage`: `Dict[str, int]` (Default: `{}`)
   - `verdict_tier`: `Literal["cloud", "local", "review", "budget", "preflight"]`
   - `session_id`: `Optional[str]`
   - `strategy`: `Optional[str]`
   - `context_snapshot`: `Optional[str]`
   - `intent_alignment`: `Optional[str]`
   - `summary`: `Optional[str]`
   - `issues`: `List[Dict[str, Any]]` (Default: `[]`)

2. **`PlanOutput`** (Line 493 in `ai_review.py`):
   - `requires_review`: `bool`
   - `direct_pass_allowed`: `bool`
   - `planner_note`: `str`

3. **Fallback Models** (Line 153 in `ai_review.py`):
   - If `rebuttal` or `route_decision` modules fail to load, duplicate fallback Pydantic models are instantiated locally: `RouteDecision`, `RebuttedFinding`, `RebuttedVerdict`, `DeveloperRebuttalFinding`, and `DeveloperRebuttal`.

---

## 2. Hand-Rolled Validation Trade-offs

If verdict validation were reduced to pure Python dict/key checks (to remove Pydantic as a dependency entirely), the following specific validation behaviors and safeguards would be lost:

1. **Nested Dict Validation**: `route_decision` validates recursively against the `RouteDecision` model schema. Doing this in standard dictionary loops requires deep nested checks.
2. **Value Literal Validation**: Direct validation of type restrictions (e.g. verifying `verdict` is one of the five specific string choices) would require custom check loops.
3. **Type Coercion & Default Assignment**: Assigning empty list objects to missing values like `concerns` or `issues` would require verbose initialization checks.
4. **Structured Error Handling**: Pydantic's `ValidationError` collects all schema mismatch issues into a single object (`exc.errors()`), providing precise feedback on exactly what fields were malformed.

---

## 3. Structural Import Placement Defect

Today, the top-level import of `pydantic` sits above the fail-open protection block of the script:
- If Pydantic is not present in the target project virtual environment (common in standard pip setups upon first install), the script raises a `ModuleNotFoundError` during load.
- This bypasses the `try...except` block in `main()`, returning an exit code 1 to `pre-commit` and blocking all commits indiscriminately.

### Guarded Region Boundaries & Correct Mapping
- **Normal Commits (Low Risk)**: A missing dependency crash should fail open, print a warning, and allow the commit (return exit code `0`).
- **High-Risk Commits**: A missing dependency crash must fail closed, log `high_risk_gate_closed` event to `harness_events.jsonl`, and block the commit (return exit code `1` via `_handle_api_unavailable` path).

---

## 4. API Key Discovery & Unavailability Semantics (F-COLD-3)

We analyzed the current behavior of the review gate when the API provider key is:
- **(a) Absent**:
  - `providers.get_provider()` calls `is_available()`, which returns `False` because the environment variable `ANTHROPIC_API_KEY` (or equivalent) is empty.
  - This raises a `RuntimeError` which is caught in `_run_review`'s try-catch and routes to `_handle_api_unavailable()`.
  - For normal commits: fails open with a warning.
  - For high-risk commits: fails closed and blocks.
- **(b) Present but Unreachable/Invalid** (e.g. invalid key or network issue):
  - `is_available()` returns `True` since the variable is set.
  - The network request in `call_api_with_retry` fails and throws `HTTPError` (e.g., 401 Unauthorized or 403 Forbidden).
  - This is also caught and routes to `_handle_api_unavailable()`, behaving identically to (a).

### User Experience Gap
In the field session, the user attempted their first commit and faced a failure/warning because the key requirement was undiscoverable.
- There is no check during the onboarding phase (`bootstrap/install.py`) or the validation phase (`bootstrap/validate.py`) checking if the keys are defined or valid.
- The user is only notified of the missing key at commit time.
- Preflight key verification should be added to the installer/validator to improve onboarding ergonomics.

---

## 5. Documentation Reconciliation ("Stdlib Only" Claims)

The framework documentation frequently claims "stdlib only" or "zero external dependencies" for the gate scripts:
- **[getting-started.md](file:///c:/projects/ai-delivery-control/docs/getting-started.md#L11)**: "Python stdlib is required to run the harness regardless of your project's language."
- **[CAPABILITY_INVENTORY.md](file:///c:/projects/ai-delivery-control/docs/planning/CAPABILITY_INVENTORY.md#L642)**: "`.agent/scripts/check_traceability.py` — stdlib-only commit-msg hook (zero external dependencies)"
- **[sprint_1_implementation_plan.md](file:///c:/projects/ai-delivery-control/docs/archive/sprint_1_implementation_plan.md#L247)**: "Zero-Dependency Lightness: stdlib only"
These statements are technically inaccurate as long as `ai_review.py` forces a top-level import of `pydantic`.

---

## 6. Options & Cost Analysis

We evaluate three strategies for resolving the dependency conflict:

### Option 1: Dynamic Import with Graceful Degradation (Recommended)
Move all Pydantic imports inside the specific functions/classes that require them, or wrap them in a `try...except ImportError` block that delegates validation to helper wrapper scripts. If Pydantic is absent, the gate treats it as a provider-unavailability event (failing open for low-risk commits, failing closed for high-risk commits).
- **Pros**:
  - Preserves the "stdlib-only" contract for normal commits (zero setup friction).
  - Maintains strict type validation when Pydantic is installed.
  - Resolves the import-time crash completely.
- **Cons**:
  - Slight runtime overhead of dynamic imports (negligible).

### Option 2: Mandatory Prerequisite
Declare `pydantic` as a mandatory dependency in the target project's environment and update the installer to fail if it cannot install it.
- **Pros**:
  - Ensures type-checked validation is always active.
- **Cons**:
  - Breaks the zero-dependency value proposition of the framework.
  - Adds install-time setup friction.

### Option 3: Vendored Shim
Include a lightweight, hand-rolled mini-Pydantic or a third-party single-file validation library inside the harness.
- **Pros**:
  - True zero-dependency while maintaining type safety checks.
- **Cons**:
  - High maintenance cost and added file footprint.

---

## 7. Action Plan

We propose implementing **Option 1 (Dynamic Import with Graceful Degradation)**:
1. Relocate the Pydantic imports below the `try...except` fail-open boundary in `ai_review.py`.
2. Wrap imports in `try...except ImportError` and handle missing-pydantic errors as a custom `PROVIDER_ERROR` within the fail-open/fail-closed framework of `_handle_api_unavailable`.
3. Add API key reachability checks to `bootstrap/validate.py` (F-COLD-3/T1-B-16) to verify that provider keys are set and reachable before the user attempts their first commit.
