# SPEC-v1.4.9.1-first-commit-hotfix

**Status**: DRAFT  
**Author**: Gemini (AI execution mode)  
**Feeds into**: Release v1.4.9.1  
**Tracked under**: `T1-K-15` / `T1-B-15` / `T1-B-16` / `HIB-069` / `HIB-070` / `HIB-071` / `HIB-072`

---

## 1. Goal & Context

> A brand-new, empty, pip-based git repository with the harness installed and no optional dependencies present must complete its first commit successfully, or fail only for reasons the user can understand and act on.

This hotfix addresses four critical issues blocking clean onboarding on default Python pip virtual environments:
1. **F1**: `pip run <cmd>` template rendering crash.
2. **F2**: `ai_review.py` and `acceptance_check.py` load crashes due to top-level `pydantic` imports.
3. **F3**: `architecture_checks.py` load crash due to missing `harness_utils` in `sys.path`.
4. **F5**: `_strip_json_fences` NameError runtime regression in providers.

---

## 2. Bounded Scope & Out of Scope

* **Bounded Scope**:
  - Replace hardcoded `[PROJECT_PACKAGE_MANAGER] run` commands in the pre-commit config template with dynamically resolved prefix path placeholders rendered at install time.
  - Relocate Pydantic imports inside target functions or wrap them in dynamic `try...except ImportError` check blocks with fallback stubs in `ai_review.py` and `acceptance_check.py` to prevent NameErrors at load time.
  - Fix parent path insertions and CWD-relative import vulnerability specifically on line 631 of `architecture_checks.py` (the file that blocks the first commit). The remaining 10 vulnerable files identified in the AT-03 inventory (including `repo_map.py`, `init_session.py`, `harness_health.py`, etc.) are deferred to v1.4.11.
  - Re-introduce the regex-based `_strip_json_fences` helper in `providers.py` and cover it with unit tests.
* **Out of Scope**:
  - Upgrading the validator to run dry-run preflights (deferred to v1.4.11).
  - Enforcing merge-time checks or authentication for `--no-trace` (deferred to v1.4.10).

> [!NOTE]
> **Conda Support Scope Decision**: Conda run-prefix rendering is deferred to v1.4.11 (installer/onboarding theme) per Peter's decision 2026-07-19. The hotfix covers pip and poetry prefix rendering only.

> [!NOTE]
> **Pydantic Fallback strategy**: Resolved 2026-07-19. Option A (graceful degradation with dynamic import stub fallback) is selected to avoid first-run installer friction, on the condition that a highly visible warning is printed to stderr on every execution when degraded.

---

## 3. Assumptions

* `[Resolved: The developer has git installed and initialized in their target project root.]`
* `[Resolved: The target virtual environment contains standard Python tools but may not have optional libraries (like Pydantic or PyYAML) pre-installed.]`

---

## 4. Acceptance Criteria

### Scenario 1: Onboarding on a bare pip project
* **Given** a fresh git repository using a basic `pip` layout with an active `.venv`
* **When** `bootstrap/install.py` is executed
* **Then** the rendered `.pre-commit-config.yaml` contains platform-correct relative virtualenv paths to virtualenv tool paths (e.g. `.venv/Scripts/python` on Windows or `.venv/bin/python` on macOS)
* **And** the first git commit completes successfully without raising `ModuleNotFoundError` or `unknown command` errors.

### Scenario 2: Markdown fence stripping executes cleanly
* **Given** the adversarial review gate provider returns a JSON payload wrapped in markdown code fences (` ```json ... ``` `)
* **When** `providers.py` invokes `raw_completion()`
* **Then** the code fences are stripped successfully via regex
* **And** no `NameError: name '_strip_json_fences' is not defined` is raised.

---

## 5. Proposed Changes

### Component: Template & Installer
#### [MODIFY] [pre-commit-config.yaml.template](file:///c:/projects/ai-delivery-control/bootstrap/templates/pre-commit-config.yaml.template)
- Substitute hardcoded package manager run prefixes with `[PROJECT_PYTHON_PREFIX]` and `[PROJECT_MYPY_PREFIX]`.

#### [MODIFY] [install.py](file:///c:/projects/ai-delivery-control/bootstrap/install.py)
- Detect OS layout and virtual environment name to dynamically compute prefix paths at install time (Option A from AT-01).
- **F1 Replacements Integration**: Add `[PROJECT_PYTHON_PREFIX]` and `[PROJECT_MYPY_PREFIX]` (and any other new prefix placeholders introduced) as keys in the `replacements` dict inside `scaffold_configurations()`, computed from the existing `pm_run_prefix` variable (which is already correctly empty-string for pip). Template hooks using `[PROJECT_PACKAGE_MANAGER] run <cmd>` must switch to a prefix placeholder that resolves to `pm_run_prefix` + command.
- **Dead Code Cleanup / Reconciliation**: `scaffold_configurations()` step 6 currently contains a `pc_content.replace('cmd /c ', '')` post-processing step for non-Windows, but the current template contains no `cmd /c` tokens (representing dead code operating on a template that changed underneath it). The F1 fix must either remove this dead stripping step or reconcile it with the new prefix approach.

### Component: Dependency Isolation
#### [MODIFY] [ai_review.py](file:///c:/projects/ai-delivery-control/src/scripts/ai_review.py)
- Wrap top-level `pydantic` imports in a dynamic fallback check block to fail-open gracefully on standard commits if missing (Option 1 from AT-02).
- **Class Load Crash Prevention (Stub Pattern)**: Provide stub fallback definitions for `BaseModel`, `Field`, and `ValidationError` in the `except ImportError:` branch, mirroring the reference pattern in `.agent/scripts/check_spec.py` lines 32–43, to ensure class definitions (e.g. `class ReviewVerdict(BaseModel)`) succeed when Pydantic is absent.
- **Mandatory Visible Warning**: When the stub fallback path is active (Pydantic is absent), the gate must print a highly visible warning to stderr on every execution: `⚠️ [GATE] Running without schema validation — pydantic not installed. Verdict integrity checks are disabled. Install pydantic to restore full gate rigor.`

#### [MODIFY] [acceptance_check.py](file:///c:/projects/ai-delivery-control/.agent/scripts/acceptance_check.py)
- Move Pydantic imports inside functions or use dynamic try/except fallback blocks with the identical BaseModel stub pattern to prevent load crashes on `class AcceptanceVerdict(BaseModel)` when the acceptance hook fires.
- **Mandatory Visible Warning**: When the stub fallback path is active, the hook must print a highly visible warning to stderr on every execution: `⚠️ [GATE] Running without schema validation — pydantic not installed. Verdict integrity checks are disabled. Install pydantic to restore full gate rigor.`

### Component: Path Insertion & Forensics
#### [MODIFY] [architecture_checks.py](file:///c:/projects/ai-delivery-control/.agent/skills/universal/senior-architect/scripts/architecture_checks.py)
- Correct fixed-depth path resolution and fix the CWD-relative import on line 631 (where `sys.path.insert(0, str(Path.cwd() / "src" / "scripts"))` introduces failures when run from subdirectories or with custom source paths).

#### [MODIFY] [providers.py](file:///c:/projects/ai-delivery-control/src/scripts/providers.py)
- **F5 Helper Restoration**: Restore the original regex-based `_strip_json_fences` helper function as a distinct string-returning helper:
  ```python
  def _strip_json_fences(raw: str) -> str:
      """Strip markdown code fences if the model wraps JSON in them."""
      raw = re.sub(r"^```(?:json)?\s*", "", raw)
      raw = re.sub(r"\s*```$", "", raw)
      return raw
  ```
- **Anti-Collision Warning**: Do NOT merge, consolidate, or replace it with the existing `_parse_json_response()` function (line 82) — they serve different call sites with different return contracts (`raw_completion` requires a cleaned string, whereas `review` requires a parsed dict). Keep them separate.

---

## 6. Verification Plan

### Automated Tests
- Run the restored providers unit tests:
  `.venv/bin/python -m pytest tests/test_providers.py -k "test_strip_json_fences"` (macOS/Linux) or `.venv\Scripts\python -m pytest tests/test_providers.py -k "test_strip_json_fences"` (Windows)
- Verify that E2E onboarding scenario executes cleanly:
  `.venv/bin/python tests/e2e/run_e2e_verification.py` (macOS/Linux) or `.venv\Scripts\python tests/e2e/run_e2e_verification.py` (Windows)

---

## 7. Resolved Decisions

* **Pydantic Fallback strategy**: Option A (graceful degradation with dynamic import stub fallback and mandatory per-run warning) — resolved 2026-07-19.
