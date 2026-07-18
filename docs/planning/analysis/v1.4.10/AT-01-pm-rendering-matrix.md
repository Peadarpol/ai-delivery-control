# AT-01 — Package-Manager & OS Rendering Matrix

This document provides a comprehensive analysis of the package manager rendering bug (**F1**) and the cross-platform virtual environment pathing bug (**F-COLD-2**).

## 1. Package Manager Command Rendering Matrix

This matrix evaluates how the `[PROJECT_PACKAGE_MANAGER]` placeholder and command prefixes render across different package managers when applied to the pre-commit configuration template lines.

### Template Command Lines in Scope
- **C1**: `entry: [PROJECT_PACKAGE_MANAGER] run mypy [PROJECT_SRC_PATH]/`
- **C2**: `entry: [PROJECT_PACKAGE_MANAGER] run pytest --noconftest tests/quality/test_exception_standards.py`
- **C3**: `entry: [PROJECT_PACKAGE_MANAGER] run python .agent/skills/senior-architect/scripts/architecture_checks.py`

### Rendering Matrix

| PM / Tool | Template Command | Rendered Hook Entry | Valid? | Details / Action Required |
| :--- | :--- | :--- | :--- | :--- |
| **poetry** | C1 | `poetry run mypy src/` | **Yes** | Poetry correctly resolves to its internal virtual env. |
| **poetry** | C2 | `poetry run pytest ...` | **Yes** | Standard Poetry execution path. |
| **poetry** | C3 | `poetry run python ...` | **Yes** | Standard Poetry execution path. |
| **pipenv** | C1 | `pipenv run mypy src/` | **Yes** | Pipenv correctly resolves execution path. |
| **pipenv** | C2 | `pipenv run pytest ...` | **Yes** | Standard Pipenv execution path. |
| **pipenv** | C3 | `pipenv run python ...` | **Yes** | Standard Pipenv execution path. |
| **pip** | C1 | `pip run mypy src/` | **No** | **F1 Defect**: `pip` has no `run` command; pre-commit fails. |
| **pip** | C2 | `pip run pytest ...` | **No** | **F1 Defect**: `pip` has no `run` command; pre-commit fails. |
| **pip** | C3 | `pip run python ...` | **No** | **F1 Defect**: `pip` has no `run` command; pre-commit fails. |
| **npm** | C1 | `npm run mypy src/` | **Yes** | Resolves if a `mypy` script is defined in `package.json`. |
| **pnpm** | C1 | `pnpm run mypy src/` | **Yes** | Resolves if a `mypy` script is defined in `package.json`. |
| **yarn** | C1 | `yarn run mypy src/` | **Yes** | Resolves if a `mypy` script is defined in `package.json`. |

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
