# AT-03 — Skill-Script Import Pathing Audit

This document provides a detailed audit of the import pathing defect (**F3**) across the framework's scripts and skills.

## 1. Directory Script Pathing Inventory

We audited all Python scripts under `.agent/scripts/` and `.agent/skills/` that import `harness_utils` or reference the project's source root scripts.

| Script Path | Path Insertion Code / Strategy | Target Path | Path Invariants & Vulnerabilities |
| :--- | :--- | :--- | :--- |
| `scripts/acceptance_check.py` | `sys.path.insert(0, str(script_dir.parent.parent))` | `.agent` / project root | **Safe**: Resolves relative to own parent directory. |
| `scripts/check_spec.py` | `parent.parent.parent / "src" / "scripts"` | Project root `src/scripts/` | **Vulnerable**: Hardcodes `"src"` source root at lines 22 and 81, crashing at load time before config checks are reached. |
| `scripts/circuit_breaker.py` | `parent.parent.parent / "src" / "scripts"` | Project root `src/scripts/` | **Vulnerable**: Hardcodes `"src"` source root at line 25. |
| `scripts/co_change_core.py` | `parents[2] / "src" / "scripts"` | Project root `src/scripts/` | **Vulnerable**: Hardcodes `"src"` source root at line 15. |
| `scripts/co_change_reconciler.py` | `parent.parent.parent / "src" / "scripts"` | Project root `src/scripts/` | **Vulnerable**: Hardcodes `"src"` source root at line 134. |
| `scripts/init_session.py` | `parent.parent.parent / "src" / "scripts"` | Project root `src/scripts/` | **Vulnerable**: Hardcodes `"src"` source root at line 5 (equivalent to `parents[2]`). |
| `scripts/onboarding.py` | `parent.parent.parent / "src" / "scripts"` | Project root `src/scripts/` | **Vulnerable**: Hardcodes `"src"` source root at line 75. |
| `scripts/pm_scaffold.py` | `sys.path.insert(0, str(script_dir.parent.parent))` | `.agent` / project root | **Safe**: Resolves relative to own parent directory. |
| `scripts/wiki_compile.py` | `parent.parent.parent / "src" / "scripts"` | Project root `src/scripts/` | **Vulnerable**: Hardcodes `"src"` source root at lines 41, 120, and 372. |
| `scripts/wiki_lint.py` | `parent.parent.parent / "src" / "scripts"` | Project root `src/scripts/` | **Vulnerable**: Hardcodes `"src"` source root at lines 58 and 239. |
| `skills/.../repo_map.py` | `parents[5] / "src" / "scripts"` | Project root `src/scripts/` | **Vulnerable**: Hardcodes `"src"` source root (fixed depth/folder) at line 12. |
| `skills/.../architecture_checks.py` | `parents[5] / "src" / "scripts"` & `Path.cwd() / "src" / "scripts"` | Project root `src/scripts/` | **Vulnerable**: Dual vulnerability. Hardcodes `"src"` at line 10 (`parents[5]`) and includes a dynamic CWD-relative hardcode at line 631 (`Path.cwd() / "src" / "scripts"`). |
| `skills/.../validate.py` (api-design) | `PROJECT_ROOT / "src" / "presentation" / "api"` | Project root `src/presentation` | **Vulnerable**: Hardcodes `"src"` source root at line 30. |

---

## 2. GymBase Forensics

To answer whether the Clean Architecture Check hook has ever executed successfully on GymBase (`Gym_App`):
- **Yes**, the gate executes and passes successfully on the GymBase working copy.
- **Why**:
  - GymBase uses the default `"src"` directory name as its source root, meaning the hardcoded path `parents[5] / "src" / "scripts"` resolves to `c:\projects\Gym_App\src\scripts` (which contains `harness_utils.py`).
  - **Correction**: The previous assertion that `architecture_checks.py` did not contain a CWD-relative import vulnerability was wrong. Line 631 explicitly uses `Path.cwd() / "src" / "scripts"`. If run from a subdirectory, this fails-closed due to CWD drift.
- **Gaps**:
  - The check is completely fragile and fails on any project where the source folder is named `"app"` or `"lib"` (such as standard Python project layouts using those conventions).
  - It also fails if the hook is invoked in a context where the parent relative depth of 5 does not align (e.g. global customizations).
  - It remains vulnerable to dynamic execution path drift (running pre-commit from a subdirectory) due to the CWD-relative import on line 631.

### Command Verification Output (GymBase)
We ran the Clean Architecture checks hook against the GymBase working copy manually using pre-commit:

```bash
c:\projects\Gym_App> poetry run pre-commit run architecture-checks --all-files
Clean Architecture Checks................................................Passed
```

This confirms the gate is active and executes successfully on the default `"src"` layout but remains vulnerable to custom layout failures.

---

## 3. Candidate Path Strategies Analysis

We evaluated three candidate solutions for resolving the path-resolution gap:

### Option A: Per-Script dynamic `sys.path` Bootstrap (Precedent-aligned)
Every script implements a lightweight, standalone helper that traverses directories upward to find `.agent/config.yaml`, extracts the `source_path` value using a simple regex (or defaults to `"src"`), and appends `<project_root>/<source_path>/scripts/` to `sys.path`.

- **Pros**:
  - Extremely robust across all package configurations, CWD locations, and custom folder layouts.
  - Zero cross-platform environment dependencies.
  - Aligns with the design of `check_traceability.py` and `circuit_breaker.py`.
- **Cons**:
  - Requires duplicating a small 10-line bootstrapping block at the top of each script.

### Option B: PYTHONPATH in Pre-commit Hook Entry
Set the `PYTHONPATH` environment variable directly in the `.pre-commit-config.yaml` hook definition to point to the correct scripts folder:
`entry: env PYTHONPATH=.venv/lib/python... python .agent/...`

- **Pros**:
  - Keeps the script source code clean.
- **Cons**:
  - Setting environment variables dynamically inside pre-commit entries is highly platform-dependent (fails on Windows Command Prompt/PowerShell without complex shell shims).

### Option C: Duplicate `harness_utils` into `.agent/scripts/`
Maintain a duplicate of `harness_utils.py` in `.agent/scripts/`, which is a framework-owned folder whose relative path is always known.

- **Pros**:
  - Simple relative imports are guaranteed to succeed.
- **Cons**:
  - High risk of checksum drift and duplicate code maintenance.

---

## 4. Recommendation & Rationale

We recommend **Option A (Dynamic Bootstrap Helper)**.
It is the only platform-agnostic, zero-dependency strategy that guarantees successful script execution regardless of whether the user runs from a custom source root (`app/`, `lib/`), an unactivated shell, or a subdirectory.
