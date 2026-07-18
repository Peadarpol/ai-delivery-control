# AT-07 — Framework-File Lint & Formatting Policy

This document analyzes the framework-file linting and formatting collision issue (**F7**) and documents the upstream check results.

## 1. Checksum-Verified, Framework-Owned Path Inventory

The following paths are provisioned by `install.py` (`copy_framework_files()`):
1. **Harness Configs and Metadata** (under `.agent/`):
   - `.agent/scripts/` (containing `check_repo.py`, `check_traceability.py`, `init_session.py`, `check_skills_hygiene.py`, `governance_check.py`, `pm_scaffold.py`)
   - `.agent/workflows/` (workflows directory)
   - `.agent/evals/` (behavior and regression check runners/datasets)
   - `.agent/templates/` (configuration templates)
   - `.agent/skills/` (copied non-destructively: `universal/`, stack packs, etc.)
   - `.agent/governance.md`
   - `.agent/AGENTS.md`
   - `.agent/blocked_commands.md`
2. **Harness Execution Scripts** (under `[PROJECT_SRC_PATH]/scripts/`):
   - `ai_review.py`
   - `providers.py`
   - `roster_builder.py`
   - `review_context_universal.md`
   - `harness_utils.py`
   - `gate_context.py`
   - `capability_calibration.py`
   - `state_persistence.py`
   - `acceptance_hook.py`
   - `context_loader.py`
   - `route_decision.py`
   - `rebuttal.py`

---

## 2. Formatting Mutation Risks

When a target project runs `pre-commit` hooks (like `black` or `ruff --fix`), it automatically formats python files staged in the repository.
- **Risk**: If the project's formatting rules differ from the framework's baseline, the formatters will rewrite parts of the framework-owned files (e.g. quote changes, comma additions, import sorting).
- **Consequence**: This modifies the files and invalidates their checksums. The framework's internal health check (`harness_health.py` or future verify tasks) will flag the files as tampered or corrupt, raising false-positive integrity alerts.
- **Shadowing Collision**: If we resolve this by excluding `[PROJECT_SRC_PATH]/scripts/` entirely in the project's formatter configurations (e.g. `black.exclude` or `ruff.exclude`), the exclusion will also shadow any custom, developer-owned helper scripts that happen to be placed in `src/scripts/`, leaving them unformatted.

---

## 3. Pre-Commit Exclusion Recommendations

We propose configuring the pre-commit configuration template to exclude only the specific framework-owned files rather than the entire scripts directory:

### pyproject.toml / ruff.toml
```toml
[tool.black]
force-exclude = '''
(
  ^\.agent/
  | ^[PROJECT_SRC_PATH]/scripts/ai_review\.py
  | ^[PROJECT_SRC_PATH]/scripts/providers\.py
  | ^[PROJECT_SRC_PATH]/scripts/roster_builder\.py
  | ^[PROJECT_SRC_PATH]/scripts/harness_utils\.py
  | ^[PROJECT_SRC_PATH]/scripts/gate_context\.py
  | ^[PROJECT_SRC_PATH]/scripts/capability_calibration\.py
  | ^[PROJECT_SRC_PATH]/scripts/state_persistence\.py
  | ^[PROJECT_SRC_PATH]/scripts/acceptance_hook\.py
  | ^[PROJECT_SRC_PATH]/scripts/context_loader\.py
  | ^[PROJECT_SRC_PATH]/scripts/route_decision\.py
  | ^[PROJECT_SRC_PATH]/scripts/rebuttal\.py
)
'''

[tool.ruff]
exclude = [
    ".agent",
    "[PROJECT_SRC_PATH]/scripts/ai_review.py",
    "[PROJECT_SRC_PATH]/scripts/providers.py",
    "[PROJECT_SRC_PATH]/scripts/roster_builder.py",
    "[PROJECT_SRC_PATH]/scripts/harness_utils.py",
    "[PROJECT_SRC_PATH]/scripts/gate_context.py",
    "[PROJECT_SRC_PATH]/scripts/capability_calibration.py",
    "[PROJECT_SRC_PATH]/scripts/state_persistence.py",
    "[PROJECT_SRC_PATH]/scripts/acceptance_hook.py",
    "[PROJECT_SRC_PATH]/scripts/context_loader.py",
    "[PROJECT_SRC_PATH]/scripts/route_decision.py",
    "[PROJECT_SRC_PATH]/scripts/rebuttal.py",
]
```

---

## 4. Upstream Hygiene Audit (Ruff Findings)

We ran Ruff check against the harness repo's own `src/` and `.agent/` using GymBase's lint ruleset (`E,F,I,B,TCH` select list, ignoring `B008,E402,B904,E501,E722,TC003`):

### Results Summary
- **Total findings**: 75 errors.
- **Fixable automatically**: 62 errors.

### Per-Rule Statistics
- **`I001` (unsorted-imports)**: 29 instances
- **`F401` (unused-import)**: 25 instances
- **`F841` (unused-variable)**: 6 instances
- **`F541` (f-string-missing-placeholders)**: 4 instances
- **`F821` (undefined-name)**: 4 instances
- **`E731` (lambda-assignment)**: 2 instances
- **`F811` (redefined-while-unused)**: 2 instances
- **`F601` (multi-value-repeated-key-literal)**: 1 instance
- **`F823` (undefined-local)**: 1 instance
- **`TC006` (runtime-cast-value)**: 1 instance

### Classification

#### Real Defects (Bugs)
- **`F821` (Undefined name)**: 4 instances total
  - `src/scripts/providers.py` (Lines 320, 434, 537): call undefined function `_strip_json_fences`. (F5 NameError regression).
  - `.agent/scripts/cdr_ledger_validate.py` (Line 183): references `Path` in the type hint `path: str | Path` without importing it from `pathlib`.
- **`F601` (Repeated dictionary key)**: 1 instance
  - `src/scripts/harness_utils.py` (Line 216): repeats the `"spec_gate"` key literal inside a dictionary.
- **`F823` (Undefined local)**: 1 instance
  - `.agent/scripts/onboarding.py` (Line 59 & 65): accesses `sys` before a local `import sys` occurs on line 74. Due to Python scoping rules, this triggers a fatal `UnboundLocalError` crash.

#### Style / Hygiene Noise
- **`I001` (Import sorting)**: 29 instances.
- **`F401` (Unused import)**: 25 instances.
- **`F841` (Unused local variable)**: 6 instances.
- **`F541` (f-string missing placeholder)**: 4 instances.
- **`E731`, `F811`, `TC006`**: Style and typing warnings.

### Recommendation
Fix the real bugs (4x `F821`, 1x `F601`, 1x `F823`) immediately in the v1.4.10 release. Defer all style/hygiene noise items (`I001`, `F401`, `F841`, etc.) to the backlog as they do not affect gate execution correctness.
