# AT-02 — Pydantic Dependency Disposition

This document provides a detailed analysis of the Pydantic import-time crash defect (**F2**) and the API key reachability discovery issue (**F-COLD-3**).

## 1. Pydantic Usage Inventory

Pydantic is imported in the following files across the repository:

1. **[src/scripts/ai_review.py](file:///c:/projects/ai-delivery-control/src/scripts/ai_review.py#L33)**:
   - Imports: `BaseModel`, `Field`, `ValidationError` (unprotected top-level import).
   - Usage: Inherited by `ReviewVerdict` and `PlanOutput`.
2. **[src/scripts/route_decision.py](file:///c:/projects/ai-delivery-control/src/scripts/route_decision.py#L12)**:
   - Imports: `BaseModel`, `Field` (unprotected top-level import).
   - Usage: Inherited by `RouteDecision`.
3. **[src/scripts/rebuttal.py](file:///c:/projects/ai-delivery-control/src/scripts/rebuttal.py#L18)**:
   - Imports: `BaseModel`, `Field`, `ValidationError` (unprotected top-level import).
   - Usage: Inherited by rebuttal schemas.
4. **[src/scripts/gate_context.py](file:///c:/projects/ai-delivery-control/src/scripts/gate_context.py#L17)**:
   - Imports: `BaseModel`, `Field` (unprotected top-level import).
5. **[.agent/scripts/acceptance_check.py](file:///c:/projects/ai-delivery-control/.agent/scripts/acceptance_check.py#L14)**:
   - Imports: `BaseModel` (unprotected top-level import).
   - Usage: Inherited by `AcceptanceVerdict`.
6. **[.agent/scripts/check_spec.py](file:///c:/projects/ai-delivery-control/.agent/scripts/check_spec.py#L33)**:
   - Imports: `BaseModel`, `Field` (protected dynamic import).
   - Usage: Wrapped in `try...except ImportError` with a zero-dependency fallback class block.

### Defect Class Propagation (F2)
The import-time crash defect is NOT unique to `ai_review.py`.
- **`check_spec.py`** is guarded correctly. If Pydantic is missing, it falls back to a clean mock class block and runs successfully.
- **`acceptance_check.py`** has the exact same top-level unprotected import pattern and shares the F2 crash risk. If Pydantic is not installed, the AI-driven acceptance gate crashes at load time, blocking commits on pre-push/post-commit. A robust v1.4.9.1 hotfix must fix the import layout in BOTH `ai_review.py` and `acceptance_check.py`.

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

## 4. Malformed LLM Response Path Tracing

We traced the behavior of the review gate when the LLM call succeeds but returns an invalid or schema-mismatched response:

### Path A: Completely Malformed JSON (`json.JSONDecodeError`)
If the model returns a response that cannot be parsed as valid JSON (even after brace-extraction in `_parse_json_response`):
1. `_parse_json_response()` raises a `json.JSONDecodeError`.
2. This is caught by the `except json.JSONDecodeError` block in `_run_review()`.
3. It calls `_handle_parse_failure()`, logs `json_parse_failure` to `harness_events.jsonl`, writes the parse failure reason to `verdict.json`, and **uniformly fails closed** by returning exit code `1`.
4. **Behavior**: Always blocks the commit, regardless of risk level.

### Path B: Valid JSON but Schema Mismatch (`ValidationError`)
If the model returns valid JSON, but the fields fail to validate against the `ReviewVerdict` model schema (e.g. missing `verdict` or invalid Literal value):
1. Instantiation of `ReviewVerdict(**raw_review_dict)` raises a Pydantic `ValidationError`.
2. This is caught by `except ValidationError as exc` at the bottom of the parsing block in `_run_review()`.
3. It sets `fail_reason = f"ReviewVerdict validation failed: {exc}"` and delegates to `_handle_api_unavailable()`.
4. **Behavior**:
   - **Low-Risk Commit**: Fails open, logs the event, and allows the commit (exit code `0`).
   - **High-Risk Commit**: Fails closed, logs the event, and blocks the commit (exit code `1`).

### Summary of Path Divergences
The gate treats a Pydantic validation failure as a transient provider error (failing open for low-risk commits), while treating raw JSON parse errors as complete engine failures (always failing closed). This represents an intentional safety posture choice, but should be documented clearly.

---

## 5. Documentation Reconciliation ("Stdlib Only" Claims)

The framework documentation frequently claims "stdlib only" or "zero external dependencies" for the gate scripts:
- **[getting-started.md](file:///c:/projects/ai-delivery-control/docs/getting-started.md#L11)**: "Python stdlib is required to run the harness regardless of your project's language."
- **[CAPABILITY_INVENTORY.md](file:///c:/projects/ai-delivery-control/docs/planning/CAPABILITY_INVENTORY.md#L642)**: "`.agent/scripts/check_traceability.py` — stdlib-only commit-msg hook (zero external dependencies)"
- **[sprint_1_implementation_plan.md](file:///c:/projects/ai-delivery-control/docs/archive/sprint_1_implementation_plan.md#L247)**: "Zero-Dependency Lightness: stdlib only"
These statements are technically inaccurate as long as `ai_review.py` and `acceptance_check.py` force top-level imports of `pydantic`.

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
