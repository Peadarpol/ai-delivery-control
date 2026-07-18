# AT-06 — Root-Commit Traceability Exemption

This document analyzes the root-commit traceability exemption defect (**F6**) and evaluates `--no-trace` ergonomics.

## 1. First-Commit Detection Mechanics (Predicate Analysis)

At the `commit-msg` hook stage during the very first commit in a repository, the commit object has not yet been created, and the branch reference `HEAD` does not point to any commit.

### Git Command Probes on Empty Repositories

1. **`git rev-parse HEAD`**
   - *Result*: Exits with non-zero code (`128`).
   - *Output*: `fatal: ambiguous argument 'HEAD': unknown revision or path not in the working tree.`
2. **`git rev-parse HEAD^`**
   - *Result*: Exits with non-zero code (`128`).
   - *Output*: `fatal: ambiguous argument 'HEAD^': unknown revision or path not in the working tree.`
3. **`git log`**
   - *Result*: Exits with non-zero code (`128`).
   - *Output*: `fatal: your current branch 'main' does not have any commits yet`
4. **`git rev-parse --verify HEAD`**
   - *Result*: Exits with non-zero code (`4`).
   - *Output*: `fatal: Needed a single revision` (to stderr).

### Reliable Root-Commit Predicate
To determine if a commit-msg run is evaluating the very first commit of the repository:
```python
def is_root_commit() -> bool:
    """Check if the repository currently contains zero commits (root-commit state)."""
    import subprocess
    res = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True
    )
    # If HEAD does not resolve to a commit, we are making the first commit
    return res.returncode != 0
```
This check is highly deterministic and cross-platform.

---

## 2. Exemption Matrix Across Outer-Loop Modes

We map whether the root-commit traceability exemption should be allowed across the three `outer_loop` governance postures:

| Governance Mode | Exemption Allowed? | Rationale / Argument |
| :--- | :--- | :--- |
| **loose** | **Yes** | Standard developer speed posture; first commit does not require spec tracking. |
| **contractual** | **Yes (Recommended)** | **The Onboarding Paradox**: Every new software project must start with a root commit. Forcing a spec validation check on the first commit creates a catch-22, as the spec validation script (`check_spec.py`) and environment themselves are typically introduced in the root commit. |
| **contractual** | **No** | Strict alignment posture: even the root commit must match a spec defined outside git (e.g. in a parent wiki or task manager). *Cost*: adds substantial friction to bootstrapping. |
| **strict** | **No** | Zero-exception policy. The root commit must contain an approved spec in the staged files that matches the traceability ID. |

---

## 3. `--no-trace` Ergonomics Assessment

We cataloged the developer confusion vectors associated with the `--no-trace` override mechanism:

1. **Syntax Confusion (Git Flag Misconception)**:
   - *Issue*: Developers assume `--no-trace` is a command-line flag for Git (e.g. `git commit --no-trace -m "..."`).
   - *Result*: Git rejects the flag, leading to developer frustration.
   - *Reality*: `--no-trace` is a substring check evaluated *inside* the commit message itself.
2. **Hidden Constraints (10-Character Reason Floor)**:
   - *Issue*: The commit-msg hook rejects messages like `[--no-trace: init]` because the reason text is under 10 characters.
   - *Result*: The user is blocked without prior visibility into the length threshold until the gate rejects it.
3. **Escapes Visibility**:
   - The `--no-trace` syntax is only documented in internal specifications and the hook's rejection output. New developers on a project have no discoverable way to bypass traceability on a trivial change until they fail.

### Backlog Recommendations (Post-v1.4.10)
To improve ergonomics without breaking backward compatibility of existing commit history parsers:
- **R1**: Add detailed syntax help to the rejection message showing correct usage examples:
  `git commit -m "[--no-trace: bootstrapping initial environment] initial files"`
- **R2**: Defer grammar changes to a future release to avoid breaking downstream PR/changelog generators that parse commit history.

---

## 4. Hook Test Cases

To verify this logic in the unit test suite (`tests/test_check_traceability.py`), the following test scenarios must be implemented:

1. **`test_root_commit_passes_without_id`**:
   - Mock `is_root_commit()` to return `True`.
   - Call `check_traceability` with a message lacking any spec ID.
   - Assert it passes (exits `0`).
2. **`test_non_root_commit_fails_without_id`**:
   - Mock `is_root_commit()` to return `False`.
   - Call `check_traceability` with a message lacking any spec ID.
   - Assert it fails (exits non-zero).
3. **`test_root_commit_passes_with_id`**:
   - Mock `is_root_commit()` to return `True`.
   - Call `check_traceability` with a valid spec ID (e.g. `[SPEC-001] message`).
   - Assert it passes (exits `0`).
