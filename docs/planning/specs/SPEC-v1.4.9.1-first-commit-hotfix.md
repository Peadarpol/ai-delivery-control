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
  - Relocate Pydantic imports inside target functions or wrap them in dynamic `try...except ImportError` check blocks in `ai_review.py` and `acceptance_check.py`.
  - Fix parent path insertions and CWD-relative import vulnerability specifically in `architecture_checks.py` (the file that blocks the first commit). The remaining 10 vulnerable files identified in the AT-03 inventory (including `repo_map.py`, `init_session.py`, `harness_health.py`, etc.) are deferred to v1.4.11.
  - Re-introduce the regex-based `_strip_json_fences` helper in `providers.py` and cover it with unit tests.
* **Out of Scope**:
  - Upgrading the validator to run dry-run preflights (deferred to v1.4.11).
  - Enforcing merge-time checks or authentication for `--no-trace` (deferred to v1.4.10).

> [!NOTE]
> **Conda Support Scope Decision**: Conda run-prefix rendering is deferred to v1.4.11 (installer/onboarding theme) per Peter's decision 2026-07-19. The hotfix covers pip and poetry prefix rendering only.

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

### Component: Dependency Isolation
#### [MODIFY] [ai_review.py](file:///c:/projects/ai-delivery-control/src/scripts/ai_review.py)
- Wrap top-level `pydantic` imports in a dynamic fallback check block to fail-open gracefully on standard commits if missing (Option 1 from AT-02).

#### [MODIFY] [acceptance_check.py](file:///c:/projects/ai-delivery-control/.agent/scripts/acceptance_check.py)
- Move Pydantic imports inside functions or use dynamic try/except fallback blocks to prevent load crashes when the acceptance hook fires.

### Component: Path Insertion & Forensics
#### [MODIFY] [architecture_checks.py](file:///c:/projects/ai-delivery-control/.agent/skills/universal/senior-architect/scripts/architecture_checks.py)
- Correct fixed-depth path resolution and fix the CWD-relative import on line 631.

#### [MODIFY] [providers.py](file:///c:/projects/ai-delivery-control/src/scripts/providers.py)
- Restore the original regex-based `_strip_json_fences` helper function:
  ```python
  def _strip_json_fences(raw: str) -> str:
      """Strip markdown code fences if the model wraps JSON in them."""
      raw = re.sub(r"^```(?:json)?\s*", "", raw)
      raw = re.sub(r"\s*```$", "", raw)
      return raw
  ```

---

## 6. Verification Plan

### Automated Tests
- Run the restored providers unit tests:
  `.venv/bin/python -m pytest tests/test_providers.py -k "test_strip_json_fences"` (macOS/Linux) or `.venv\Scripts\python -m pytest tests/test_providers.py -k "test_strip_json_fences"` (Windows)
- Verify that E2E onboarding scenario executes cleanly:
  `.venv/bin/python tests/e2e/run_e2e_verification.py` (macOS/Linux) or `.venv\Scripts\python tests/e2e/run_e2e_verification.py` (Windows)

---

## 7. Resolved Decisions

* **Pydantic Fallback strategy**: Option 1 (Dynamic Import with Graceful Fallback / Degradation) has been approved and selected for implementation.
