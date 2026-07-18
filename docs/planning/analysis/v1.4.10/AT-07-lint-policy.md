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

### Classification

#### Real Defects (Bugs)
- **`F821` (Undefined name)** in `src/scripts/providers.py`:
  - Lines 320, 434, 537 call undefined name `_strip_json_fences`. (Represents the F5 NameError regression).
- **`F601` (Repeated dictionary key)** in `src/scripts/harness_utils.py`:
  - Line 216 repeats key `"spec_gate"` in a dictionary.

#### Style / Hygiene Noise
- **`I001` (Import sorting)**: 62 instances of import blocks needing formatting/sorting.
- **`F401` (Unused import)**: 10 instances of unused imports (e.g. `sys`, `time`, `typing.Optional`).
- **`TC006` (Type cast string representation)**: Cast type expressions needing quotes.
- **`F841` (Unused local variable)**: Line 194 of `state_persistence.py` assigns `token_usage` but does not use it.

### Recommendation
Fix the real bugs (F821, F601) immediately in the v1.4.10 release. Defer the 62 style/hygiene noise items to the backlog as they do not affect gate execution correctness.
