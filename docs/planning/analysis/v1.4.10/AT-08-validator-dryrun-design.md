# AT-08 — Validator Dry-Run Design Study (F8)

This document presents the technical design study for upgrading [bootstrap/validate.py](file:///c:/projects/ai-delivery-control/bootstrap/validate.py) from static file presence checking to automated runnability verification.

---

## 1. Dry-Run Sandbox Strategy & Side-Effect Audit

To safely exercise git commit hooks during onboarding validation without modifying the developer's working directory or polluting git history, we evaluated three sandbox models:

| Strategy | Mutates Project? | Fires Post-Commit Hooks? | Executable Hooks Covered | Disk/Time Overhead | Rationale / Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A. Live `pre-commit run --all-files`** | **Yes** (if formatters fix) | No | All | None | **Rejected**: Formatters/linters will modify active source files directly, violating validator read-only contract. |
| **B. Mock Hook Execution Shims** | No | No | Only mocked scripts | Complex mock logic | **Rejected**: Fails to catch actual package/interpreter missing errors since execution is simulated. |
| **C. Throwaway Git Clone Sandbox** | **No** (isolated directory) | **No** (post-commit bypassed) | All | Copying ~10–50KB files (<200ms) | **Recommended**: Clone the project into a temp folder under `.agent/scratch/validate_sandbox/`, run `pre-commit run --all-files --config [temp_config]` in that folder, and discard. |

### Temporary Clone Dry-Run Procedure:
1. Create an ephemeral sandbox directory at `.agent/scratch/validate_sandbox/`.
2. Copy the project's source tree (excluding `.git`, `node_modules`, `.venv`, and `venv`) to the sandbox.
3. Initialize an isolated git repository in the sandbox directory (`git init -b main`).
4. Stage all copied files and perform a dry-run test commit within the sandbox:
   ```bash
   git add .
   # Run pre-commit hooks in validation mode against sandbox files
   pre-commit run --all-files --config .pre-commit-config.yaml
   ```
5. Retrieve hook exit codes and logs, then clean up the sandbox directory.

---

## 2. Pass-Criterion Taxonomy

When executing hooks in the validation sandbox, we distinguish between **Content Violations** (where a hook successfully ran and rejected code syntax/errors) and **Infrastructure Errors** (where a hook could not load due to environment faults):

| Failure Category | Examples | Exit Code | Validator Result | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Infrastructure / Onboarding Error** | `ModuleNotFoundError: pydantic`, `command not found`, `ImportError`, Python version mismatch. | `1` / `127` / `9009` | **FAIL** | Represents a broken verification pipeline. The harness is not ready to govern. |
| **Content Violation** | `mypy` type error, `black` formatting check fail, failed unit tests in pytest. | Target linter exit code (typically `1` or `2`) | **PASS** | The check executed successfully and caught a coding issue. The pipeline is functional. |
| **Skipped Precondition** | Exception Standards test file absent. | `0` (with advisory) | **PASS** | Precondition skipped gracefully as designed (verdict: `SKIPPED-precondition`). |

---

## 3. Onboarding Preflight Checks (F-COLD-1/3/5)

We design three mandatory preflight checks to detect silent environment gaps prior to hook execution:

### 1. Wrong-Install-Target Detection (F-COLD-1)
* **Goal**: Prevent developers from running `install.py` inside the framework's own directory instead of their target project.
* **Mechanism**:
  - Check the project root directory for the presence of `harness_version.txt` and `bootstrap/install.py`.
  - Check git remote origin URL: `git config --get remote.origin.url`. If it maps to `ai-delivery-control.git` and the user is executing an installation, halt with:
    `❌ [ERROR] Target directory is the framework repository. Run the installer with --project-path pointing to your development project.`

### 2. Live API Key Preflight (F-COLD-3)
* **Goal**: Confirm the configured LLM API key is present and actually has network reachability to the provider endpoint.
* **Mechanism**:
  - Retrieve the budget/review keys and providers from `.agent/config.yaml`.
  - Run a cheap, low-token (e.g. `max_tokens=1`) connection test call to the provider endpoint.
  - Catch `401 Unauthorized` (auth/key error) or connection timeouts, formatting a clear remediation guide:
    `❌ [ERROR] Anthropic API Key is unreachable or invalid (status: 401). Verify ANTHROPIC_API_KEY environment variable.`

### 3. venv Python Currency & Tooling Report (F-COLD-5)
* **Goal**: Detect downlevel Python interpreters or outdated formatters in the local virtualenv.
* **Mechanism**:
  - Verify that the active Python interpreter matches a minimum version floor (e.g., Python >= 3.10).
  - Run executable version checks (`black --version`, `ruff --version`, `mypy --version`) and write their output into the validator's onboarding health report, confirming path correctness.

---

## 4. End-to-End CI Matrix Feasibility

To prevent onboarding regressions from reaching production releases, we map a minimal CI verification matrix:

* **Current E2E Harness**: `tests/e2e/run_e2e_verification.py` executes 21 scenarios but runs in a single pre-configured developer environment (Poetry on host OS). It missed both `F1` (pip template crash) and `F2` (pydantic missing on raw pip).
* **Proposed CI Matrix**:
  - **Runner OS**: Windows, macOS, Linux (cross-platform path checks).
  - **Tooling Tiers**:
    1. `pip` + bare virtualenv (no global dependencies pre-installed) ➔ *Guarantees F1 and F2 are caught*.
    2. `poetry` + virtualenv.
  - **E2E Trigger**: Run `run_e2e_verification.py` inside the bare `pip` environment on every release PR.

---

## 5. Human Decision & Recommendation

### Default-On vs. Opt-Out
* **Options**:
  - **Option A (Default-On)**: `install.py` runs validation dry-run automatically. Installer exits with `1` if preflight checks fail.
  - **Option B (Opt-Out)**: Validator runs only when `--validate` is passed.
* **Recommendation**: **Option A (Default-On)** with a `--skip-validation` flag for headless/container installations. Ensuring environment validity on installation prevents developers from encountering confusing pre-commit blockages on their very first commit.
