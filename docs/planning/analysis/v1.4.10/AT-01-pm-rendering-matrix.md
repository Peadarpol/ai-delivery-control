# AT-01 — Package-Manager & OS Rendering Matrix

This document provides a comprehensive analysis of the package manager rendering bug (**F1**) and the cross-platform virtual environment pathing bug (**F-COLD-2**).

## 1. Package Manager Command Rendering Matrix

This matrix evaluates how the `[PROJECT_PACKAGE_MANAGER]` placeholder and command prefixes render across different package managers when applied to the pre-commit configuration template lines.

### Template Command Lines in Scope
There are 10 hook definition lines in `pre-commit-config.yaml.template` using the `[PROJECT_PACKAGE_MANAGER]` placeholder:
- **C1**: `entry: [PROJECT_PACKAGE_MANAGER] run mypy [PROJECT_SRC_PATH]/` (Mypy type checks)
- **C2**: `entry: [PROJECT_PACKAGE_MANAGER] run pytest --noconftest tests/quality/test_exception_standards.py` (Exception Standards checks)
- **C3**: `entry: [PROJECT_PACKAGE_MANAGER] run python .agent/skills/senior-architect/scripts/architecture_checks.py` (Clean Architecture checks)
- **C4**: `entry: [PROJECT_PACKAGE_MANAGER] run python .agent/scripts/check_skills_hygiene.py` (Skills Hygiene)
- **C5**: `entry: [PROJECT_PACKAGE_MANAGER] run python .agent/evals/behaviour_checks.py` (Agent Behavior Audit)
- **C6**: `entry: [PROJECT_PACKAGE_MANAGER] run python .agent/evals/regression_runner.py --verify-only` (Regression checks)
- **C7**: `entry: [PROJECT_PACKAGE_MANAGER] run python .agent/scripts/governance_check.py` (Governance check)
- **C8**: `entry: [PROJECT_PACKAGE_MANAGER] run python .agent/scripts/init_session.py --post-commit` (Session heartbeat)
- **C9**: `entry: [PROJECT_PACKAGE_MANAGER] run python [PROJECT_SRC_PATH]/scripts/ai_review.py` (AI Adversarial Review)
- **C10**: `entry: [PROJECT_PACKAGE_MANAGER] run python .agent/scripts/check_traceability.py` (Requirement Traceability)

### Rendering Matrix

| PM / Tool | Template Command | Rendered Hook Entry | Valid? | Details / Action Required |
| :--- | :--- | :--- | :--- | :--- |
| **poetry** | C1–C2 | `poetry run <cmd>` | **Yes** | Poetry correctly resolves to its internal virtual env. |
| **poetry** | C3–C10 | `poetry run python <script>` | **Yes** | Standard Poetry execution path. |
| **pipenv** | C1–C2 | `pipenv run <cmd>` | **Yes** | Pipenv correctly resolves execution path. |
| **pipenv** | C3–C10 | `pipenv run python <script>` | **Yes** | Standard Pipenv execution path. |
| **pip** | C1–C2 | `pip run <cmd>` | **No** | **F1 Defect**: `pip` has no `run` command; pre-commit fails with `unknown command "run"`. |
| **pip** | C3–C10 | `pip run python <script>` | **No** | **F1 Defect**: `pip` has no `run` command; pre-commit fails. |
| **npm/pnpm/yarn** | C1–C10 | `<pm> run <cmd>` | **Yes** | Resolves correctly if scripts are defined in the target project's `package.json`. |

> [!NOTE]
> **Uniformity Check**: None of the 7 other python-based hooks (`C4`–`C10`) exhibit special-case command syntax or arguments that would deviate from the standard `[PROJECT_PACKAGE_MANAGER] run python <script>` structure. A blanket placeholder replacement of `[PROJECT_PACKAGE_MANAGER] run python` with a resolved virtual environment prefix is completely safe and robust for all Python invocations.

---

## 2. OS & Virtual Environment Pathing Matrix (F-COLD-2)

This matrix maps how virtual environment paths, script folder names, and python interpreter assumptions vary across OS environments and package manager configurations for pip-based targets.

### Hook Execution Environment Scenarios
- **Scenario A: Activated Shell**: User activates venv manually, then runs `git commit` in the same shell.
- **Scenario B: Non-Activated / GUI Shell**: User commits via an IDE (VS Code, Cursor), GUI git client (Sourcetree, Fork), or fresh shell.

### OS / Environment Compatibility Matrix

| OS | PM / Env | Scenario A (Activated) | Scenario B (Non-Activated) | Resolution Path / Bug Details |
| :--- | :--- | :--- | :--- | :--- |
| **Windows** | poetry | **Valid** (`poetry run`) | **Valid** (`poetry run`) | Poetry resolves env internally; OS invariant. |
| **macOS** | poetry | **Valid** (`poetry run`) | **Valid** (`poetry run`) | Poetry resolves env internally; OS invariant. |
| **Linux** | poetry | **Valid** (`poetry run`) | **Valid** (`poetry run`) | Poetry resolves env internally; OS invariant. |
| **Windows** | pip + `.venv` | **Valid** (`python`) | **Broken** (global python) | **F-COLD-2 Bug**: Global python runs; lacks pydantic/packages. |
| **macOS** | pip + `.venv` | **Valid** (`python`) | **Broken** (global python) | **F-COLD-2 Bug**: Global python runs; lacks pydantic/packages. |
| **Linux** | pip + `.venv` | **Valid** (`python`) | **Broken** (global python) | **F-COLD-2 Bug**: Global python runs; lacks pydantic/packages. |
| **Windows/macOS/Linux** | conda | **Valid** (`python`) | **Broken** (global python) | **Out of Scope**: Conda environment path resolution in Scenario B resides outside the workspace root and requires a named global environment. Conda is treated as an active-only or global environment target for our scope. |

### Conda Environment Support (Design Disposition)
Conda manages python environments in a system-wide user directory (e.g. `C:\Users\username\.conda\envs\` or `/home/user/miniconda3/envs/`) rather than a workspace-local subfolder.
- **Scenario A (Activated)**: Resolves correctly to the active Conda python executable (`python` maps to the conda environment bin path in `PATH`).
- **Scenario B (Non-Activated)**: Pre-commit calls have no way of knowing the named conda environment name or conda root dynamically unless it is hardcoded or resolved via system-wide environment lookups.
- **Decision**: Conda is designated out of scope for workspace-local path resolution. In a non-activated environment (Scenario B), Conda users must either run pre-commit via their activated shells, or configure their IDE/Git GUIs to run git commits with the correct activated environment wrapper.

### Layout Discrepancies
For Scenario B to pass on standard `pip` projects, the hook must target the virtual environment interpreter explicitly:
- **Windows**: `.venv/Scripts/python.exe`
- **macOS/Linux**: `.venv/bin/python`

---

## 3. Design Analysis: Install-time Prefix Rendering vs. Runtime Interpreter Resolution

We compare two strategies for resolving python executable path and package manager prefix inconsistencies:

### Option A: Install-Time Prefix Rendering (Static Templates)
The installer (`bootstrap/install.py`) detects target OS and virtual environment directories (`.venv`, `venv`, `env`), computes the interpreter prefix, and substitutes it into a placeholder (e.g. `[PROJECT_PYTHON_INTERPRETER]` or `[PROJECT_PM_RUN_PREFIX]`).

- **Pros**:
  - Pure declarative pre-commit configuration.
  - Zero performance overhead at commit time.
  - Easy to inspect and debug in target `.pre-commit-config.yaml`.
- **Cons**:
  - Brittle if the virtual environment is recreated with a different name or path after install.

### Option B: Runtime Interpreter Resolution (Dynamic Wrappers)
Use standard `python` or `python3` in the template, but write a lightweight wrapper shell script/batch file that detects `.venv/bin/python` or `.venv/Scripts/python` dynamically and executes python scripts.

- **Pros**:
  - Resilient to virtual environment deletion, recreation, or renaming.
- **Cons**:
  - Pre-commit executes hooks in isolated sub-environments. Calling a wrapper shell script on Windows requires invoking `cmd /c` or having a bash shell present, which introduces additional cross-platform friction.
  - Extra files (shims) must be scaffolded and maintained.

---

## 4. Divergence Analysis

The rendering paths diverged because:
1. In [install.py:374](file:///c:/projects/ai-delivery-control/bootstrap/install.py#L374-L387), `pm_run_prefix` was correctly designed to resolve to an empty string (`""`) for standard `pip` projects.
2. The config placeholders like `[LINT_FORMAT_COMMAND_PLACEHOLDER]` correctly leveraged `pm_run_prefix`.
3. However, `pre-commit-config.yaml.template` bypasses these placeholders and directly hardcodes `[PROJECT_PACKAGE_MANAGER] run mypy` and `[PROJECT_PACKAGE_MANAGER] run python`. This represents a design gap where the template's author assumed `poetry run` or `pipenv run` semantics applied globally to all Python setups.

---

## 5. Blast Radius Analysis

- **Upgrade Process Impact**: `bootstrap/upgrade.py` does not contain any logic for re-rendering `.pre-commit-config.yaml`.
- **Clobbering Risks**: Modifying `pre-commit-config.yaml.template` will only affect:
  1. Brand-new installations.
  2. Manual re-runs of `bootstrap/install.py`.
  Existing installations running `upgrade.py` will not have their `.pre-commit-config.yaml` altered or custom developer hook edits clobbered.
  `install.py` already includes backup behavior (`.pre-commit-config.yaml.bak`), which protects developer customization.

---

## 6. Recommendations & Action Plan

### Recommended Strategy
We recommend **Option A: Install-Time Prefix Rendering** leveraging the installer to resolve both F1 and F-COLD-2. 

### Rationale
Option A keeps the pre-commit configuration declarative and simple. Since the virtual environment name and layout are determined at setup time, the installer can reliably write the correct platform-specific paths.

### Proposed Changes for v1.4.9.1 / v1.4.11 Specs
1. In `bootstrap/install.py`, compute `pm_run_prefix` and introduce a new replacement placeholder:
   ```python
   # Detect virtual environment path and platform layout
   venv_dir = None
   for name in [".venv", "venv", "env"]:
       if (self.project_path / name).is_dir():
           venv_dir = name
           break

   if self.package_manager == "pip" and venv_dir:
       if sys.platform == "win32":
           python_prefix = f"{venv_dir}/Scripts/python"
       else:
           python_prefix = f"{venv_dir}/bin/python"
   else:
       # poetry run python / pipenv run python / global python
       python_prefix = f"{pm_run_prefix}python"
   ```
2. In `pre-commit-config.yaml.template`, replace:
   - `[PROJECT_PACKAGE_MANAGER] run python` ➔ `[PROJECT_PYTHON_PREFIX]`
   - `[PROJECT_PACKAGE_MANAGER] run mypy` ➔ `[PROJECT_PM_RUN_PREFIX]mypy` (or resolve standard placeholders).
