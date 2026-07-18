# AT-04 — Precondition-Dependent Gate Semantics (F4)

This document establishes the semantic rules for pre-commit/pre-push hooks when their target precondition files, directories, or config sections are absent on target consumer projects.

---

## 1. Precondition Audit Table

We audited all hooks defined in [pre-commit-config.yaml.template](file:///c:/projects/ai-delivery-control/bootstrap/templates/pre-commit-config.yaml.template) against their execution prerequisites on a fresh target project installation:

| Hook ID | Precondition | Current Behaviour (Absent) | Observed Exit Code | Proposed Classification | Proposed Resolution |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `check-active-repo` | `.agent/scripts/check_repo.py` exists; valid git repo. | Command fails (file not found). | `1` / `127` | Infrastructure Gap | **Fail-Closed**: Critical repository validation must execute. |
| `mypy` | `mypy` installed; source folder `[PROJECT_SRC_PATH]` exists. | Mypy fails (path does not exist). | `2` | Infrastructure Gap | **Fail-Closed**: Developer-configured path check (verified by dry-run validator). |
| `bandit` | `bandit` installed; `pyproject.toml` config file exists. | Bandit fails due to missing `-c pyproject.toml` config parameter. | `2` | Config Absence | **Skip-With-Advisory**: Re-route config to a local default fallback (e.g. `.agent/config/bandit.toml`) at install time if absent. |
| `pip-audit` | `pip-audit` installed. | Command fails (executable missing). | `1` / `127` | Infrastructure Gap | **Fail-Closed**: Checked by preflight validator. |
| `gitleaks` | `gitleaks` executable installed in environment path. | Pre-commit execution fails. | `1` / `127` | Infrastructure Gap | **Fail-Closed**: Checked by preflight validator. |
| `architecture-quality` | `pytest` installed; `tests/quality/test_exception_standards.py` exists. | Pytest fails with "no tests collected / file not found" error. | `4` | Contextual Absence | **Skip-With-Advisory**: Introduce a local script wrapper to gracefully skip if the test file does not exist. |
| `architecture-checks` | `.agent/config.yaml` exists with `architecture:` block. | Prints warning card and exits cleanly. | `0` | Config Absence | **Safe**: Already implements clean skip. |
| `skills-hygiene` | `.agent/skills/` directory exists. | Prints info card and exits cleanly. | `0` | Config Absence | **Safe**: Already implements clean skip. |
| `behaviour-checks` | `.agent/evals/behaviour_checks.py` exists; summary file exists. | Prints warning card and exits cleanly. | `0` | Contextual Absence | **Safe**: Already exits cleanly on warning issues. |
| `regression-check` | `.agent/evals/golden_dataset.yaml` exists. | Prints warning card and exits cleanly. | `0` | Contextual Absence | **Safe**: Already exits cleanly when dataset is missing. |
| `governance-audit` | `.agent/scripts/governance_check.py` exists. | Logs observation and exits cleanly. | `0` | Contextual Absence | **Safe**: Executed post-commit. |
| `session-heartbeat` | `.agent/scripts/init_session.py` exists. | Exits cleanly. | `0` | Contextual Absence | **Safe**: Executed post-commit. |
| `ai-adversarial-review` | `[PROJECT_SRC_PATH]/scripts/ai_review.py` exists. | Command fails (file not found). | `1` / `127` | Infrastructure Gap | **Fail-Closed**: Core gate script must exist. |
| `commit-traceability` | `.agent/scripts/check_traceability.py` exists. | Command fails (file not found). | `1` / `127` | Infrastructure Gap | **Fail-Closed**: Core gate script must exist. |

---

## 2. Semantic Rules: Infrastructure Gaps vs. Contextual Absences

To protect both developer onboarding velocity and the integrity of the release gate, we establish two distinct resolution semantics:

### A. Infrastructure/Environment Gaps (Fail-Closed)
* **Definition**: A tool executable (e.g. `mypy`, `pip-audit`, `pytest`) is not installed, or a core script (e.g. `ai_review.py`) is missing from the environment.
* **Semantic**: **Fail-Closed**. The commit is blocked.
* **Rationale**: If a validation tool is missing, the security/checks pipeline is broken. Failing open would allow unchecked code to merge.
* **Onboarding Mitigation**: The install-time dry-run validator (`bootstrap/validate.py --dry-run`) must proactively run runnability preflights and warn/fail on installation if the required tooling is absent, ensuring the environment is verified *before* the first commit is attempted.

### B. Contextual/Configurational Absences (Skip-With-Advisory)
* **Definition**: A specific checking configuration or quality asset (such as GymBase-specific exception tests or a project-specific linter config) is missing because the project is in a clean or non-legacy layout.
* **Semantic**: **Skip-With-Advisory**. The hook prints a notice, records the skip, and exits with code `0`.
* **Rationale**: Onboarding or non-GymBase projects should not be blocked by the lack of target-specific test templates.
* **Enforcement & Audit**:
  - The hook prints a clear explanation to `stderr` indicating the missing prerequisite.
  - The hook logs a `gate_precondition_skipped` event to `.agent/state/harness_events.jsonl` containing the `hook_id` and the missing `precondition`.
  - The skip verdict is classified under `SKIPPED-precondition` to unify the gate's classification taxonomy (aligning with `T1-K-14`).

---

## 3. Implementation Design Sketch

### A. Exception Standards Hook Wrapper
We replace the direct `pytest` invocation in the template with a lightweight Python helper script, `[PROJECT_SRC_PATH]/scripts/check_exception_standards.py`, which is provisioned during installation:

```python
# [NEW] .agent/scripts/check_exception_standards.py
import sys
import subprocess
from pathlib import Path
from harness_utils import log_harness_event  # Or direct json write

TEST_PATH = Path("tests/quality/test_exception_standards.py")

def main():
    if not TEST_PATH.exists():
        print(f"⚠️  [PRECONDITION] Exception standards test file not found at {TEST_PATH}. Skipping hook with advisory.")
        # Log to the audit log under the unified taxonomy
        log_harness_event({
            "event_type": "gate_observation",
            "severity": "warning",
            "payload": {
                "hook_id": "architecture-quality",
                "precondition": "tests/quality/test_exception_standards.py",
                "verdict": "SKIPPED-precondition",
                "detail": "Test file absent on non-GymBase target project layout."
            }
        })
        sys.exit(0)
    
    # Run pytest scoped inside the active Python interpreter environment
    res = subprocess.run([sys.executable, "-m", "pytest", "--noconftest", str(TEST_PATH)])
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
```

### B. Bandit Configuration Resolution
During `bootstrap/install.py` execution, the installer checks if `pyproject.toml` exists in the target project root:
- If `pyproject.toml` exists: The pre-commit config renders with `args: ["-c", "pyproject.toml"]`.
- If `pyproject.toml` is absent: The installer copies a default configuration template into `.agent/config/bandit.toml` and renders the pre-commit config with `args: ["-c", ".agent/config/bandit.toml"]`.
This avoids project-root clutter on plain `pip` projects while retaining robust, configuration-backed security checks.
