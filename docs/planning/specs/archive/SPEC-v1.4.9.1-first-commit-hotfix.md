# SPEC-v1.4.9.1-first-commit-hotfix

**Status**: DELIVERED  
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
- **F1 PM Detection & Prefix Scaffolding (Unified Routine)**: Refactor stack detection into a single ordered evaluation sequence in `scaffold_configurations()` to compute OS-correct relative virtualenv tool path prefixes:
  1. If Poetry is active -> use `poetry run python` and `poetry run mypy`.
  2. If Pipenv is active -> use `pipenv run python` and `pipenv run mypy`.
  3. Otherwise (standard pip), scan the project root directory for `.venv`, `venv`, or `env` (in that exact order).
     * If found: compute the resolved path to the python interpreter per OS (e.g. `.venv/Scripts/python` / `.venv/Scripts/mypy` on Windows, `.venv/bin/python` / `.venv/bin/mypy` on macOS/Linux).
     * If none found: fall back to system `python` / `mypy` and log a prominent install-time onboarding warning.
- **Replacements Integration**: Add `[PROJECT_PYTHON_PREFIX]` and `[PROJECT_MYPY_PREFIX]` as replacements in `scaffold_configurations()`, matching the computed values from the unified routine.
- **Dead Code Cleanup**: Remove the legacy non-Windows post-processing step (`pc_content.replace('cmd /c ', '')`) as it is no longer required under the dynamic prefix rendering design.

### Component: Dependency Isolation & Auditing
#### [MODIFY] [ai_review.py](file:///c:/projects/ai-delivery-control/src/scripts/ai_review.py) and [acceptance_check.py](file:///c:/projects/ai-delivery-control/.agent/scripts/acceptance_check.py)
- Move Pydantic imports inside functions or use dynamic try/except fallback blocks with identical BaseModel/Field/ValidationError stub patterns to prevent load crashes when Pydantic is absent.
- **CI-Check / Audit-Log / Silence-Flag Precedence Rule**: Implement the following execution precedence when Pydantic is absent:
  1. **CI Enforcement (Unconditional Check)**: Check if `CI` environment variable is set (`CI=true` or `CI=1`). If so, the gate must fail-closed (print a fatal error and exit with code `1`), regardless of any config flags. The silence flag must never override CI gate enforcement.
  2. **Audit Logging (Unconditional Log)**: If not in CI, write a `schema_validation_disabled` observation to the local audit log (`harness_events.jsonl`) unconditionally. This audit trail entry is mandatory and cannot be suppressed by config flags.
  3. **Visual stderr Warning (Conditional Print)**: Check the `.agent/config.yaml` configuration for `silence_pydantic_warning` under the tech_stack or general config. If `silence_pydantic_warning: true` is set, suppress printing the warning banner to stderr. Otherwise, print a highly visible warning block.
- **Dynamic PM Remediation Wording**: When printing the warning banner to `stderr` or logging it, read the persisted package manager from `.agent/config.yaml` (`tech_stack.package_manager`) and suggest the correct command dynamically:
  * For `poetry` -> suggest `poetry add pydantic --group dev`
  * For `pipenv` -> suggest `pipenv install --dev pydantic`
  * For `pip` -> suggest `pip install pydantic`

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
- Add a new unit test in `tests/unit/test_ai_review.py` and `tests/unit/test_acceptance_hook.py` that mocks `import pydantic` to raise `ImportError` and verifies:
  1. Successful class instantiation of the stubs.
  2. Fallback execution exits with code `1` under `CI=true`.
  3. Fallback execution logs a `schema_validation_disabled` event to `harness_events.jsonl` under local development.
  4. The warning banner is printed to stderr when `silence_pydantic_warning` is false/absent, and is silenced when the flag is true.

---

## 7. Resolved Decisions

* **Pydantic Fallback strategy**: Option A (graceful degradation with dynamic import stub fallback and mandatory per-run warning) — resolved 2026-07-19.
* **Precedence Rule & CI Posture**: Resolved 2026-07-19. Fail-closed posture is enforced under CI environments unconditionally. Audit logs are written unconditionally. The config flag `silence_pydantic_warning` only silences terminal stdout/stderr warnings.
* **Dynamic Remediation Wording**: Resolved 2026-07-19. Dynamic package manager commands are suggested based on tech_stack.package_manager configuration.
* **Staged Diff Inclusion in Spec Acceptance Gate**: Resolved 2026-07-19. To close a coverage gap where staged, uncommitted migration files were bypassed by the spec acceptance gate checks, `acceptance_check.py`'s `get_git_diff()` is updated to evaluate both branch diffs and staged index changes (`git diff --cached`).
