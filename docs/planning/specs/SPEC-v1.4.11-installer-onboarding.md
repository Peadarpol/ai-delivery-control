# SPEC-v1.4.11-installer-onboarding

**Status**: Approved  
**Author**: Gemini (AI execution mode)  
**Feeds into**: Release v1.4.11  
**Tracked under**: `F7` / `F8` / `T1-K-17` / `F-COLD-1` / `F-COLD-2` / `F-COLD-3` / `F-COLD-5`
**Changelog:**
- v1.0 initial draft (Gemini).
- v1.1 (Claude, adversarial review, 2026-07-21): resolved an internal contradiction between §2/§4 and §5 over whether the F-COLD-1 wrong-target check lives in `install.py` or `validate.py` — confirmed via source review that placing it only in `validate.py` cannot satisfy Scenario 1's "halts immediately" criterion, since `run_validation()` is the last step of `Installer.run()` and `detect_stack()` (an earlier step) already mutates the target directory. Re-scoped F-COLD-1 to `install.py` as primary enforcement, `validate.py` as secondary re-verification. Also flagged the undocumented `--skip-validation` flag implied by §7's resolved decision, and reconciled the F-COLD-5 Python floor (3.10) against the installer's existing hard floor (3.9).
- v1.2 (Claude, multi-persona review synthesis, 2026-07-21): **fixed a real bug found in the course of this review** — `validate.py`'s `validate_wiki_state()` imported `datetime.UTC` (Python 3.11+ only) and used the `X | None` type-hint syntax (3.10+) with no `from __future__ import annotations`, meaning the validator itself could not run end-to-end below 3.11 regardless of what floor this spec declared. Patched to `from datetime import datetime, timezone` / `timezone.utc` and added `from __future__ import annotations`; the 3.9 hard floor / 3.10 soft-recommend split below is now actually true rather than aspirational. Also folded in a critical multi-persona review (Principal Architect, DevOps/Cross-Platform, Security, DX, QA personas): added missing acceptance criteria for F7, F-COLD-2/F-COLD-5, and `--skip-validation`; added Windows `rmtree`-on-readonly-git-objects handling, `CONDA_PREFIX` cross-verification, credential redaction + explicit timeout on preflight calls, sandbox orphan-cleanup semantics, and CI mock-provider testability requirements. Identified the concrete F7 gap: `black`/`ruff` hooks in `pre-commit-config.yaml.template` have no `exclude:` field (unlike the adjacent `bandit` hook, which already excludes `^tests/|^[PROJECT_SRC_PATH]/scripts/|^.agent/`), so project-level formatter runs can currently rewrite framework-owned files.
- v1.3 (Claude, final consistency pass, 2026-07-21): four residual gaps closed. (1) §2 Bounded Scope now explicitly lists `--skip-validation` and the timeout/redaction/`CONDA_PREFIX` requirements as committed scope, matching what §4/§5 already required — previously these existed only in the Acceptance Criteria and Proposed Changes, with no top-level scope line covering them. (2) §2's `mypy` exclude-pattern commitment was downgraded to match §5's existing hedge ("include if trivial") — the two sections previously disagreed on whether mypy exclusion was committed or optional. (3) §3's network-availability assumption was in tension with the new Scenario 2 timeout requirement (an assumption of availability sits oddly next to a requirement to handle unavailability gracefully) — reworded to state the assumption is the common case, not a guarantee. (4) The Python floor split was demoted from `§7 Resolved Decisions` (which contains two items Peter already approved) to a new `§7a Proposed Resolution — Pending Peter's Confirmation`, since that item was resolved by Claude during review, not by Peter, and shouldn't sit at the same authority level as the two decisions he's already signed off on.
- v1.4 (Claude, second multi-persona review synthesis, 2026-07-21): folded in a second persona review (Technical Writer, Performance/Resource, Kaizen/Refactoring, Python Toolchain, C4 Architect personas). Verified two claims directly against source before accepting: confirmed `install.py`'s `update_gitignore()` `required_entries` list genuinely omits `.agent/scratch/` (the sandbox's own directory isn't gitignored, so a crash mid-dry-run can leave untracked files visible in the target project's `git status`); confirmed no shared helper module exists between `install.py` and `validate.py` today, so the F-COLD-1 wrong-target check (primary + secondary) is genuine inline duplication risk. Added: shallow (`--depth 1`) sandbox clone (pushed back on the reviewer's paired `--no-hardlinks` recommendation, which cuts against its own stated disk-savings goal — hardlinking is what makes local clones cheap; kept as a documented trade-off rather than disabled by default); `bootstrap/common.py` shared-helper refactor (`is_harness_repo()`, `resolve_venv_python()`); mandatory `try/finally` (or context-manager) sandbox teardown so `Ctrl+C`/`SIGINT` mid-dry-run still cleans up, distinct from the existing orphan-recovery requirement (that covered a *previous* crashed run; this covers *this* run being interrupted); regex-escaping of the substituted path segment in F7's `exclude:` pattern (unescaped substitution of a source-root name containing regex metacharacters would silently weaken the exclusion rather than error); per-call timeout on the three tool-version subprocess checks; standardized `--skip-validation` help text and canonical Python-floor diagnostic strings; explicit `.agent/scratch/` gitignore entry.

---

## 1. Goal & Context

This release focuses on hardening the harness installation and onboarding experience. It ensures that the first pre-commit hook runs reliably on every supported platform (macOS, Windows, Linux) across diverse virtualenv managers (pip, poetry, conda), validates live API credentials before onboarding completes, prevents accidental installations inside the harness folder itself, and protects framework-owned files from project-level formatter mutations.

---

## 2. Bounded Scope & Out of Scope

* **Bounded Scope**:
  - Implement a temporary git-sandbox dry-run validator in `bootstrap/validate.py` that exercises hook execution and catches tool/interpreter errors before the first commit (delivering `F8`). The sandbox is a shallow (`--depth 1`) clone, interrupt-safe (`try/finally`/context-manager teardown), and orphan-safe across runs.
  - Add wrong-install-target checking as the **first step** of `bootstrap/install.py`'s `Installer.run()` — before `detect_stack()` and any filesystem mutation — so the halt in Scenario 1 is actually reachable (delivering `F-COLD-1`). `bootstrap/validate.py` independently re-checks the same condition as a post-install sanity net, but is not the primary enforcement point. Both call a new shared `bootstrap/common.py` helper (`is_harness_repo()`) rather than duplicating the check inline.
  - Add connection-preflight checks for configured API keys, bounded by an explicit timeout and with credential values excluded from all diagnostic output (delivering `F-COLD-3`).
  - Implement venv path layout resolution and Python version checks (delivering `F-COLD-2`, `F-COLD-5`), via a second shared `bootstrap/common.py` helper (`resolve_venv_python()`) used by both scripts.
  - Add Conda run-prefix rendering (`conda run -n {env_name}`) via `CONDA_DEFAULT_ENV` detection, cross-verified against `CONDA_PREFIX` (deferred from v1.4.9.1 hotfix).
  - Add template exclude patterns for `black` and `ruff` configurations, with the substituted path segment regex-escaped, to shield framework-owned folders (delivering `F7`); the same exclusion for `mypy` is a stretch item within F7, included only if trivial (see §5) — not a committed deliverable.
  - Add a `--skip-validation` CLI flag (on both `install.py` and `validate.py`, with standardized help text) to bypass the sandbox dry-run specifically, per the Default-On resolved decision in §7.
  - Add `.agent/scratch/` to `install.py`'s `.gitignore` scaffolding so the sandbox directory itself is never visible in the target project's `git status`.
* **Out of Scope**:
  - Retrofitting existing non-governed repositories (F-COLD-4).

---

## 3. Assumptions

* `[Resolved: The host environment supports subprocess execution of standard git and python commands.]`
* `[Amended in v1.2: Network access during validate.py execution is expected but not assumed reliable. Preflight API calls must degrade gracefully — bounded by an explicit timeout (Scenario 2) — rather than assuming the network is always reachable. The original assumption ("network access is available") is retained as the common case; the timeout requirement exists precisely because that assumption can be wrong in practice (corporate firewalls, offline onboarding, etc.).]`

---

## 4. Acceptance Criteria

### Scenario 1: Installer blocks wrong target directory (F-COLD-1)
* **Given** the resolved `project_path` (the target directory, defaulting to cwd via `--project-path`) contains the framework file `harness_version.txt`
* **When** `bootstrap/install.py` is executed
* **Then** `Installer.run()` halts execution immediately, before `detect_stack()` runs and before any directory creation, `git init`, or file copy occurs
* **And** prints a warning instructing the user to run the script against an unrelated project.
* **And** this check is independently re-verified by `bootstrap/validate.py` post-install, so a target that somehow bypasses the install.py guard (e.g. a direct call into installer internals) is still caught before the harness is declared functional.

### Scenario 2: Onboarding validation fails on unreachable API key (F-COLD-3)
* **Given** an invalid, absent, or unreachable credentials configuration for the active LLM provider (e.g., `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` when cloud routing is selected, or local connection failures when Ollama is selected)
* **When** `bootstrap/validate.py` executes preflight connection tests
* **Then** the validator fails the runnability check within a bounded time (hard socket/HTTP timeout, e.g. 5.0s — a blocked corporate firewall or unresponsive endpoint must not hang the installer indefinitely)
* **And** outputs precise key location and authorization troubleshooting cards
* **And** the raw key value, any authorization header, and any partial key fragment are never printed to stdout/stderr or written to any log — diagnostic cards reference the key by its environment variable name only (e.g. "`ANTHROPIC_API_KEY` not found" or "`ANTHROPIC_API_KEY` rejected: 401"), never its value.

### Scenario 3: Temporary sandbox dry-run execution catches tool missing errors
* **Given** the target environment lacks a required executable or interpreter for a configured hook (e.g., the `gitleaks` executable, which results in exit code `127`)
* **When** `bootstrap/validate.py` executes the dry-run check (invoking pre-commit via python -m pre_commit or .venv/bin/pre-commit / .venv\Scripts\pre-commit)
* **Then** the validator identifies the non-zero exit code as an **Infrastructure Error** rather than a Content Violation
* **And** fails the environment runnability validation cleanly
* **And** the sandbox is created as a shallow clone (`git clone --depth 1 file://<project_path> <sandbox_path>`), not a full clone — a full clone of a large repo can take several seconds and hundreds of MB, which is disproportionate for a check that only needs the current working tree and hook config, not history. (Local clones hardlink shared objects by default, which is what keeps this fast and cheap; that default is retained deliberately, not disabled, since the dry-run never rewrites existing git objects.)
* **And**, on any exit path (success, failure, or exception), the ephemeral sandbox under `.agent/scratch/validate_sandbox/` is fully removed — including on Windows, where `git clone` marks internal object files read-only and a bare `shutil.rmtree()` raises `PermissionError: [WinError 5]`
* **And** cleanup also runs if the operator interrupts the dry-run mid-execution (`Ctrl+C` / `SIGINT`) — sandbox creation, hook invocation, and teardown are wrapped in `try/finally` (or an equivalent context manager) so an interrupted run doesn't skip cleanup. This is distinct from the next criterion: this one covers *this* run being interrupted; the next covers a *previous* run having already crashed.
* **And** a sandbox left over from a prior crashed run (orphaned directory) does not corrupt or get silently reused by the next validation run — each run gets a fresh, uniquely-named or atomically-recreated sandbox directory.
* **And** `.agent/scratch/` is present in the target project's `.gitignore` *before* the sandbox is ever created — `install.py`'s `update_gitignore()` (which already runs before `run_validation()` in `Installer.run()`'s sequence) must include `.agent/scratch/` in its `required_entries` list (today it does not: the list covers `.agent/state/*`, `.agent/wiki/`, and a few others, but not `.agent/scratch/`), so a crash mid-dry-run can't leave untracked sandbox files visible in the target repo's `git status`.

### Scenario 4: Framework-owned files are shielded from formatter mutation (F7)
* **Given** a project has `black` and `ruff` configured as pre-commit hooks via the harness-scaffolded `.pre-commit-config.yaml`
* **When** a commit stages changes anywhere in the repository, including inside `.agent/` or `[PROJECT_SRC_PATH]/scripts/` (the framework-owned scripts copied in by `install.py`: `ai_review.py`, `gate_context.py`, `capability_calibration.py`, etc.)
* **Then** the `black` and `ruff` pre-commit hooks do not reformat or rewrite any file under `.agent/` or `[PROJECT_SRC_PATH]/scripts/`
* **And** this is enforced the same way the adjacent `bandit` hook already shields those paths (via an `exclude:` regex on the hook entry), not via a separate mechanism
* **And** when `[PROJECT_SRC_PATH]` (a user-controlled value derived from the target project's directory/package name) is substituted into the `exclude:` regex, any regex metacharacters in that value (e.g. a literal `.` in a source-root name) are escaped first — a naive string substitution would silently produce a *weaker* regex (a stray `.` matches any character) rather than an error, which defeats the exclusion this scenario exists to guarantee, without ever surfacing as a visible failure.

### Scenario 5: Venv path layout and Python currency check (F-COLD-2, F-COLD-5)
* **Given** a target project has an active virtual environment (pip, poetry, or conda) whose interpreter is below the declared soft-recommend floor, or whose `Scripts/`/`bin/` layout doesn't match the detected platform
* **When** `bootstrap/validate.py` runs its Python Currency & Tooling check
* **Then** the validator does not fail the run (this is advisory, not blocking) but prints a loud warning distinguishing "Harness Minimum Floor: 3.9" (hard, enforced by `install.py`'s `check_python_version()`) from "Recommended Currency: 3.10+" (soft, this check) — a user on 3.9 must never see a pass from `install.py` followed by an unexplained contradictory warning from `validate.py` with no framing
* **And**, separately, `.pre-commit-config.yaml` is rendered with the platform-correct venv path (`Scripts\` on Windows, `bin/` on macOS/Linux) rather than a hardcoded separator
* **And**, when a Conda environment is detected via `CONDA_DEFAULT_ENV`, the validator cross-verifies `CONDA_PREFIX` actually points at that same named environment before rendering the `conda run -n {env_name}` prefix (two similarly-named environments must not be conflated).

### Scenario 6: `--skip-validation` bypasses the sandbox dry-run (Resolved Decision, §7)
* **Given** an operator runs `bootstrap/install.py --skip-validation` (which forwards the flag into its post-install validation call), or runs `bootstrap/validate.py --skip-validation` directly against an already-installed project
* **When** validation executes
* **Then** the git-sandbox dry-run (Scenario 3's mechanism) is skipped entirely, while all other non-sandbox validation checks (directory layout, core files, config parseability, gitignore state) still run
* **And** the validator's summary output clearly states that dry-run validation was explicitly skipped, so this is never silently indistinguishable from a real pass
* **And** absence of the flag is the default — the dry-run runs unless explicitly opted out.

---

## 5. Proposed Changes

### Component: Shared Helpers (new — DRY refactor, supports F-COLD-1, F-COLD-2)
#### [NEW] [common.py](file:///c:/projects/ai-delivery-control/bootstrap/common.py)
- No shared module currently exists between `bootstrap/install.py` and `bootstrap/validate.py` — confirmed by source review. The wrong-target check now lives in both scripts (primary in `install.py`, secondary re-verification in `validate.py`); writing that condition inline twice is exactly the kind of duplication that drifts silently over time (one copy gets updated, the other doesn't).
- `is_harness_repo(path: Path) -> bool`: encapsulates the `harness_version.txt`-at-root check used by both `Installer.run()`'s primary halt and `Validator.validate_repo_guard()`'s secondary re-check.
- `resolve_venv_python(project_path: Path) -> Path`: encapsulates venv interpreter/layout resolution (`Scripts/` vs `bin/`), used by both `install.py`'s `.pre-commit-config.yaml` rendering (F-COLD-2) and `validate.py`'s Python Currency check (F-COLD-5) — today these are two independent implementations of the same platform-detection logic.
- Both `install.py` and `validate.py` import from this module rather than reimplementing the checks locally.

### Component: Installer (F-COLD-1, F-COLD-2, F7)
#### [MODIFY] [install.py](file:///c:/projects/ai-delivery-control/bootstrap/install.py)
- **Wrong install target check (F-COLD-1) — primary enforcement point.** Add as the first statement inside `Installer.run()`, before `self.check_python_version()`, calling `common.is_harness_repo(self.project_path)`. If present, print the warning and `sys.exit(1)` immediately. This must run before `detect_stack()`, since `detect_stack()` is what currently creates the target directory and runs `git init` — any check placed after it is too late to prevent mutation.
- Update platform-specific prefix rendering path to map `Scripts/` vs `bin/` virtualenv folders (via `common.resolve_venv_python()`), rendering them into `.pre-commit-config.yaml`.
- Add Conda run-prefix rendering (`conda run -n {env_name}`) detected via `CONDA_DEFAULT_ENV` environment variable (deferred from v1.4.9.1), **cross-verified against `CONDA_PREFIX`** so the rendered `conda run -n {env_name}` prefix targets the environment that's actually active, not just similarly named.
- Add `--skip-validation` as a CLI flag on `install.py`'s own `argparse` (in addition to `validate.py`'s copy — see below), forwarded into `Installer.run_validation()` to suppress the sandbox dry-run specifically while leaving the rest of post-install validation intact. **Help text (standardized across both scripts):** `help="Skip post-install git-sandbox dry-run validation (non-sandbox checks still run)."`
- **`.agent/scratch/` gitignore entry:** add `.agent/scratch/` to `update_gitignore()`'s `required_entries` list (currently: `.agent/state/session.json`, `.agent/state/HALT`, `.agent/state/*.lock`, `.agent/config.yaml.migration_backup`, `.agent/wiki/`, `.agent/state/agent_session_close.json`, `.clinerules/hooks/` — `.agent/scratch/` is absent). `update_gitignore()` already runs before `run_validation()` in `Installer.run()`'s sequence, so ordering is already correct; only the entry itself is missing.

#### [MODIFY] [pre-commit-config.yaml.template](file:///c:/projects/ai-delivery-control/bootstrap/templates/pre-commit-config.yaml.template)
- **F7, concrete change:** add `exclude: ^\.agent/|^[PROJECT_SRC_PATH]/scripts/` to the `black` hook and the `ruff` hook entries — mirroring the pattern the adjacent `bandit` hook already uses (`exclude: ^tests/|^[PROJECT_SRC_PATH]/scripts/|^.agent/`). Today neither hook has an `exclude:` field, so a project-level formatter run can rewrite framework-owned files copied in by `copy_framework_files()`. `[PROJECT_SRC_PATH]` is substituted the same way it already is elsewhere in this template, **with the substituted value regex-escaped** (e.g. `re.escape(self.src_path)`) before insertion — a literal string replacement into a regex-context field would silently weaken the exclusion if the source-root name contains regex metacharacters.
- Consider the same exclusion for the local `mypy` hook — it doesn't mutate files, but running project mypy strictness settings against framework-owned scripts can produce noisy failures unrelated to the project's own code; lower priority than the black/ruff mutation risk, include if trivial.

### Component: Onboarding (F8, F-COLD-3, F-COLD-5)
#### [MODIFY] [validate.py](file:///c:/projects/ai-delivery-control/bootstrap/validate.py)
- Refactor check runner to initialize a temporary git clone sandbox under `.agent/scratch/validate_sandbox/` (Option C from AT-08), created as a **shallow clone** (`git clone --depth 1 file://<project_path> <sandbox_path>`) rather than a full clone — a full clone of a large repo's history is disproportionate for a check that only exercises hook execution against the current working tree, and can cost seconds and hundreds of MB unnecessarily. Local clones hardlink shared objects by default, which is what keeps this cheap; that default is retained rather than disabled (`--no-hardlinks` would trade the disk-savings goal away for isolation the dry-run doesn't need, since it never rewrites existing git objects).
  - **Sandbox Invocation Safety**: The sandbox must invoke pre-commit via `python -m pre_commit` (or interpreter-relative `.venv/bin/pre-commit` / `.venv\Scripts\pre-commit`) rather than bare `pre-commit` (Rationale: the validator must not contain the same unverified-PATH assumption class (F1) it is designed to detect).
  - **Windows sandbox teardown:** `git clone` marks internal `.git/objects/**` files read-only on Windows; a bare `shutil.rmtree()` on cleanup raises `PermissionError: [WinError 5]`. Teardown must use a custom `onexc`/`onerror` handler that clears the read-only bit (`os.chmod(path, stat.S_IWRITE)`) and retries the removal before re-raising.
  - **Interrupt safety:** sandbox creation, hook invocation, and teardown must be wrapped in `try/finally` (or a context manager, e.g. an `EphemeralSandbox` class) so that a `Ctrl+C`/`SIGINT` mid-dry-run still triggers cleanup rather than abandoning the sandbox mid-flight.
  - **Orphan sandbox handling:** use `tempfile.TemporaryDirectory()` semantics (or an equivalent atomic recreate-if-exists step at sandbox start) so a directory left behind by a prior crashed run is never silently reused or allowed to corrupt the next run's result. (This is distinct from interrupt safety above: that covers *this* run being interrupted; this covers a *previous* run having already crashed.)
- **Wrong install target check — secondary/post-install re-verification.** `validate.py` calls the same `common.is_harness_repo()` helper as a sanity net (it already resolves `project_path` the same way for `validate_repo_guard`). This is defense-in-depth, not the primary halt described in Scenario 1 — see the Installer component above for that.
- Add `--skip-validation` CLI flag to `validate.py`'s own `argparse` setup (Resolved Decision, Default-On per §7), using the **same standardized help text** as `install.py`'s copy: `help="Skip post-install git-sandbox dry-run validation (non-sandbox checks still run)."` Absence of the flag is the default (dry-run runs). When set, the summary output must explicitly state that dry-run validation was skipped rather than silently omitting it, so a skipped run is never visually indistinguishable from a clean pass.
- Implement live API preflight key validation using a mock low-token query.
  - **Timeout:** every preflight network call carries an explicit timeout (e.g. `timeout=5.0` seconds) at the socket/HTTP client level. No preflight call may block indefinitely.
  - **Credential redaction:** raw key values, authorization headers, and partial key fragments are never included in stdout/stderr output or written to any log file. Failure messages reference the environment variable name and outcome only (e.g. "`ANTHROPIC_API_KEY`: 401 Unauthorized"), never the value. This applies to exception messages too — a caught `HTTPError` or similar must be sanitized before being printed, not passed through with the raw request/response attached.
- **Python Currency & Tooling check (F-COLD-5)**:
  - Detect the active virtual environment Python version (via `common.resolve_venv_python()`) and compare against system interpreters and a declared floor. **Reconciliation with existing floor:** `install.py`'s `check_python_version()` already hard-blocks below Python 3.9 for the *installer's own interpreter*. This check is a separate, softer warning for the *target project's venv* interpreter, with its own floor (>= 3.10). Now that `validate.py` itself has been patched to actually run on 3.9+ (see Changelog v1.2 — it previously depended on `datetime.UTC`, a 3.11+-only symbol), the 3.9-hard / 3.10-soft split is a real, honest distinction rather than aspirational. **Standardized diagnostic strings** (both scripts use the same phrasing so the two floors never read as contradictory):
    - Hard floor met: `[SUCCESS] Harness system floor met: Python {version} (minimum required: 3.9)`
    - Soft floor not met: `[WARN] Target project Python {version} is below recommended currency (3.10+). Upgrade recommended for best hook compatibility.`
  - Warn loudly before dependency installation if the interpreter is downlevel.
  - Execute and parse tool version CLI checks (`black --version`, `ruff --version`, `mypy --version`) and report their resolved versions in the validator output. **Each subprocess call is individually bounded by an explicit timeout (e.g. 1.0s)** so a slow or hung tool invocation (e.g. a broken `mypy` shim) doesn't stall the rest of validation; sequential execution is acceptable given the small per-call cost once bounded — parallelizing these three calls is a nice-to-have, not required for this release.

---

## 6. Verification Plan

### Automated Tests
- Run validation suite:
  `.venv/bin/python -m pytest tests/test_validate.py` (macOS/Linux) or `.venv\Scripts\python -m pytest tests/test_validate.py` (Windows)
- Run installer scaffold tests:
  `.venv/bin/python -m pytest tests/test_install.py` (macOS/Linux) or `.venv\Scripts\python -m pytest tests/test_install.py` (Windows)
- **New coverage required for this revision:**
  - `test_install.py`: wrong-target halt fires before `detect_stack()` (assert no directory/git-init side effects occur when `harness_version.txt` is present at the target); F7 exclude patterns present and correct in rendered `.pre-commit-config.yaml`, including a case where `PROJECT_SRC_PATH` contains a regex metacharacter (e.g. a source root name with a literal `.`), asserting the rendered `exclude:` pattern still matches only the intended literal path; `.agent/scratch/` present in the rendered `.gitignore`.
  - `test_validate.py`: Windows-only test (skipped elsewhere) asserting sandbox teardown succeeds against a read-only git-objects tree; orphaned-sandbox-from-prior-run does not corrupt a fresh run; a simulated `SIGINT`/`KeyboardInterrupt` mid-dry-run still results in the sandbox directory being removed; the sandbox clone uses `--depth 1` (assert on the constructed git command, or on wall-clock/disk-footprint bounds against a fixture repo with non-trivial history); `--skip-validation` skips the sandbox dry-run only, not the rest of validation, and says so in the summary; each tool-version subprocess call respects its individual timeout (a hung/slow mock tool doesn't stall the others).
  - `test_common.py` (new, for `bootstrap/common.py`): `is_harness_repo()` and `resolve_venv_python()` covered directly, and both `test_install.py`/`test_validate.py` assert their respective callers actually invoke the shared helper rather than reimplementing the logic (guards against the duplication regressing back in later).
  - **API preflight tests must run deterministically offline in CI.** Introduce a mock-provider mode (e.g. `HARNESS_MOCK_API_PREFLIGHT=1` env var, or `monkeypatch` on the provider's HTTP call) so `tests/test_validate.py` never makes a real network call. Assert the timeout and redaction behavior directly against the mocked failure path (e.g. a mocked 401 response must not leak the fixture's fake key into captured stdout).

---

## 7. Resolved Decisions

* **Default-On Dry-Run**: Option A (Default-On with a `--skip-validation` flag) has been approved and selected for implementation.
* **Dry-Run Sandbox Strategy**: Option C (ephemeral git sandbox clone) has been selected in accordance with the AT-08 recommendation.

## 7a. Proposed Resolution — Pending Peter's Confirmation

Unlike the two items above, the following was resolved by Claude during spec review rather than by Peter, and should be explicitly confirmed (or overridden) at approval rather than treated as co-equal with §7:

* **Python floor split**: retain the existing 3.9 hard floor (`install.py`) and add a 3.10 soft-recommend (`validate.py`), now that `validate.py`'s own 3.11-only dependency has been patched out (Changelog v1.2). This was flagged as TBC in v1.1. The engineering blocker that motivated reconsidering the floor (the validator being unable to run at all below 3.11) is gone, so there's no longer a *technical* reason to force the question — but whether 3.9 vs 3.10 is the right product floor for the harness is a judgement call about supported environments, not something the code fix settles by itself. Recommend: confirm at approval, or explicitly defer to a follow-up decision if you want more data on the installed base first.
