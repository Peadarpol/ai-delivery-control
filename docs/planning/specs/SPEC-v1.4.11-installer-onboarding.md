# SPEC-v1.4.11-installer-onboarding

**Status**: APPROVED (Option A Selected)  
**Author**: Gemini (AI execution mode)  
**Feeds into**: Release v1.4.11  
**Tracked under**: `F7` / `F8` / `T1-K-17` / `F-COLD-1` / `F-COLD-2` / `F-COLD-3` / `F-COLD-5`

---

## 1. Goal & Context

This release focuses on hardening the harness installation and onboarding onboarding experience. It ensures that the first pre-commit hook runs reliably on every supported platform (macOS, Windows, Linux) across diverse virtualenv managers (pip, poetry, conda), validates live API credentials before onboarding completes, prevents accidental installations inside the harness folder itself, and protects framework-owned files from project-level formatter mutations.

---

## 2. Bounded Scope & Out of Scope

* **Bounded Scope**:
  - Implement a temporary git-sandbox dry-run validator in `bootstrap/validate.py` that exercises hook execution and catches tool/interpreter errors before the first commit (delivering `F8`).
  - Add wrong-install-target checking to `bootstrap/install.py` (delivering `F-COLD-1`).
  - Add connection-preflight checks for configured API keys (delivering `F-COLD-3`).
  - Implement venv path layout resolution and Python version checks (delivering `F-COLD-2`, `F-COLD-5`).
  - Add template exclude patterns for `black`, `ruff`, and `mypy` configurations to shield framework-owned folders (delivering `F7`).
* **Out of Scope**:
  - Retrofitting existing non-governed repositories (F-COLD-4).

---

## 3. Assumptions

* `[Resolved: The host environment supports subprocess execution of standard git and python commands.]`
* `[Resolved: Network access is available during validate.py execution to perform preflight API calls.]`

---

## 4. Acceptance Criteria

### Scenario 1: Installer blocks wrong target directory (F-COLD-1)
* **Given** the current working directory contains the framework file `harness_version.txt`
* **When** `bootstrap/install.py` is executed
* **Then** the installer halts execution immediately
* **And** prints a warning instructing the user to run the script against an unrelated project.

### Scenario 2: Onboarding validation fails on unreachable API key (F-COLD-3)
* **Given** an invalid, absent, or unreachable credentials configuration for the active LLM provider (e.g., `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` when cloud routing is selected, or local connection failures when Ollama is selected)
* **When** `bootstrap/validate.py` executes preflight connection tests
* **Then** the validator fails the runnability check
* **And** outputs precise key location and authorization troubleshooting cards.

### Scenario 3: Temporary sandbox dry-run execution catches tool missing errors
* **Given** the target environment lacks the `gitleaks` tool in its path
* **When** `bootstrap/validate.py` is executed with dry-run check enabled
* **Then** the sandbox execution fails on the gitleaks hook
* **And** flags the exit code `127` as an infrastructure error, failing the validator.

---

## 5. Proposed Changes

### Component: Onboarding (F8, F-COLD-1, F-COLD-3, F-COLD-5)
#### [MODIFY] [validate.py](file:///c:/projects/ai-delivery-control/bootstrap/validate.py)
- Refactor check runner to initialize a temporary git clone sandbox under `.agent/scratch/validate_sandbox/` (Option C from AT-08).
- Implement wrong install target check at startup.
- Implement live API preflight key validation using a mock low-token query.
- Add version-checking metadata to compile black/ruff/python version currency reports.

### Component: Installer (F-COLD-2)
#### [MODIFY] [install.py](file:///c:/projects/ai-delivery-control/bootstrap/install.py)
- Update platform-specific prefix rendering path to map `Scripts/` vs `bin/` virtualenv folders, rendering them into `.pre-commit-config.yaml`.

---

## 6. Verification Plan

### Automated Tests
- Run validation suite:
  `poetry run pytest tests/test_validate.py`
- Run installer scaffold tests:
  `poetry run pytest tests/test_install.py`

### Resolved Decisions
* **Default-On Dry-Run**: Resolved 2026-07-18. Option A (Default-On with a `--skip-validation` flag) has been approved and selected for implementation.
