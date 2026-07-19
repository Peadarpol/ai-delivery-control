# SPEC-v1.4.11-installer-onboarding

**Status**: DRAFT  
**Author**: Gemini (AI execution mode)  
**Feeds into**: Release v1.4.11  
**Tracked under**: `F7` / `F8` / `T1-K-17` / `F-COLD-1` / `F-COLD-2` / `F-COLD-3` / `F-COLD-5`

---

## 1. Goal & Context

This release focuses on hardening the harness installation and onboarding experience. It ensures that the first pre-commit hook runs reliably on every supported platform (macOS, Windows, Linux) across diverse virtualenv managers (pip, poetry, conda), validates live API credentials before onboarding completes, prevents accidental installations inside the harness folder itself, and protects framework-owned files from project-level formatter mutations.

---

## 2. Bounded Scope & Out of Scope

* **Bounded Scope**:
  - Implement a temporary git-sandbox dry-run validator in `bootstrap/validate.py` that exercises hook execution and catches tool/interpreter errors before the first commit (delivering `F8`).
  - Add wrong-install-target checking to `bootstrap/install.py` (delivering `F-COLD-1`).
  - Add connection-preflight checks for configured API keys (delivering `F-COLD-3`).
  - Implement venv path layout resolution and Python version checks (delivering `F-COLD-2`, `F-COLD-5`).
  - Add Conda run-prefix rendering (`conda run -n {env_name}`) via `CONDA_DEFAULT_ENV` detection (deferred from v1.4.9.1 hotfix).
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
* **Given** the target environment lacks a required executable or interpreter for a configured hook (e.g., the `gitleaks` executable, which results in exit code `127`)
* **When** `bootstrap/validate.py` executes the dry-run check (invoking pre-commit via python -m pre_commit or .venv/bin/pre-commit / .venv\Scripts\pre-commit)
* **Then** the validator identifies the non-zero exit code as an **Infrastructure Error** rather than a Content Violation
* **And** fails the environment runnability validation cleanly.

---

## 5. Proposed Changes

### Component: Onboarding (F8, F-COLD-1, F-COLD-3, F-COLD-5)
#### [MODIFY] [validate.py](file:///c:/projects/ai-delivery-control/bootstrap/validate.py)
- Refactor check runner to initialize a temporary git clone sandbox under `.agent/scratch/validate_sandbox/` (Option C from AT-08). 
  - **Sandbox Invocation Safety**: The sandbox must invoke pre-commit via `python -m pre_commit` (or interpreter-relative `.venv/bin/pre-commit` / `.venv\Scripts\pre-commit`) rather than bare `pre-commit` (Rationale: the validator must not contain the same unverified-PATH assumption class (F1) it is designed to detect).
- Implement wrong install target check at startup.
- Implement live API preflight key validation using a mock low-token query.
- **Python Currency & Tooling check (F-COLD-5)**:
  - Detect the active virtual environment Python version and compare against system interpreters and a declared floor (minimum Python >= 3.10).
  - Warn loudly before dependency installation if the interpreter is downlevel.
  - Execute and parse tool version CLI checks (`black --version`, `ruff --version`, `mypy --version`) and report their resolved versions in the validator output.

### Component: Installer (F-COLD-2)
#### [MODIFY] [install.py](file:///c:/projects/ai-delivery-control/bootstrap/install.py)
- Update platform-specific prefix rendering path to map `Scripts/` vs `bin/` virtualenv folders, rendering them into `.pre-commit-config.yaml`.
- Add Conda run-prefix rendering (`conda run -n {env_name}`) detected via `CONDA_DEFAULT_ENV` environment variable (deferred from v1.4.9.1).

---

## 6. Verification Plan

### Automated Tests
- Run validation suite:
  `.venv/bin/python -m pytest tests/test_validate.py` (macOS/Linux) or `.venv\Scripts\python -m pytest tests/test_validate.py` (Windows)
- Run installer scaffold tests:
  `.venv/bin/python -m pytest tests/test_install.py` (macOS/Linux) or `.venv\Scripts\python -m pytest tests/test_install.py` (Windows)

---

## 7. Resolved Decisions

* **Default-On Dry-Run**: Option A (Default-On with a `--skip-validation` flag) has been approved and selected for implementation.
* **Dry-Run Sandbox Strategy**: Option C (ephemeral git sandbox clone) has been selected in accordance with the AT-08 recommendation.
