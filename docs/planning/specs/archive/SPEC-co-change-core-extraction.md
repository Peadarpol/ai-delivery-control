# SPEC: Co-Change Core Extraction (Behaviour-Preserving Refactor)

**Task ID**: T1-G-17 (proposed — confirm against FRAMEWORK_BACKLOG.md before filing)
**Type**: Refactor / structural extraction. **No behaviour change.**
**Status**: DRAFT — awaiting Peter's approval before implementation
**Implementer**: Qwen (local, via Cline) under harness governance
**Reviewer**: Peter (human) — verification is by running tests, not by reading judgement
**Prerequisite**: none. Independent of boundary-declaration and reconciler work.

---

## 1. Purpose

Extract the git-history-parsing and co-change-probability logic currently
private inside `.agent/scripts/co_change_check.py` into a shared, parameterised
core module so a future periodic reconciler can reuse it without duplicating the
parsing logic.

This is a **pure structural refactor**. The observable behaviour of the existing
pre-commit co-change advisor (`run_co_change_estimator`) must remain
**byte-for-byte identical**. Success is defined as: a characterization test,
written against the *current* code before any change, passes unchanged after the
extraction.

## 2. Why this is safe to do now (context for the implementer)

`run_co_change_estimator` is live in the pre-commit gate. Its output is consumed
by `src/scripts/ai_review.py` in three places, which destructure these exact
dict keys: `staged`, `unstaged`, `confidence`, `reason`. The `confidence` value
must remain one of `EXTRACTED`, `INFERRED`, `AMBIGUOUS`.

**The extraction seam sits BELOW that contract.** We are moving the internal
helper `get_git_co_changes` (and its supporting cache/refactor-keyword helpers)
into a shared module. `run_co_change_estimator` stays in
`co_change_check.py`, keeps its signature, keeps its output shape, and keeps
calling the moved function. Nothing `ai_review.py` sees changes.

**There are currently NO tests exercising the real behaviour** of any function
in `co_change_check.py`. Every existing reference mocks
`run_co_change_estimator` to return `[]`. This means the characterization test in
§4 is not optional — it is the only thing that makes the refactor verifiable.
Write it first, against the unmodified code.

## 3. Scope

### 3.1 In scope
- New module: `.agent/scripts/co_change_core.py`
- Move into it, unchanged in logic: `get_git_co_changes`, `check_refactor_keyword`,
  `build_co_change_map`, `load_co_change_map`, `get_ast_imports`, and the module
  constants they depend on (`CACHE_PATH`, `REPO_CACHE_PATH`, `PROJECT_ROOT`
  resolution, `_safe_git_env` import).
- Parameterise `get_git_co_changes` (see §3.3) — defaults preserve current behaviour exactly.
- Update `co_change_check.py` to import the moved functions from `co_change_core`
  and call `get_git_co_changes` with **explicit arguments equal to the current
  hardcoded values**, so behaviour is provably unchanged.
- Characterization test (§4), written FIRST.

### 3.2 Out of scope (do NOT touch)
- `run_co_change_estimator` — its body, signature, thresholds (`0.1`, `0.2`),
  confidence tiers, AST-link logic, and output dict shape stay exactly as they are.
- `ai_review.py` — not one line changes.
- The `src/`-only and `.py`-only file filters' *default* behaviour.
- Any threshold value, probability floor, or commit window's *default*.
- `.agent/config.yaml` (does not exist in the harness repo; leave it that way).
- Boundary declaration, CDR ledger, reconciler — all later work.

### 3.3 Parameterisation (defaults MUST preserve current behaviour)

`get_git_co_changes` currently hardcodes three values. Lift them to parameters
with defaults equal to today's constants:

| Parameter | Default (= current behaviour) | Purpose (future reconciler) |
|---|---|---|
| `commit_window: int` | `200` (current `-n 200`) | reconciler will pass a larger window |
| `file_filter: Callable[[str], bool]` | a predicate equal to `lambda f: f.endswith(".py") and f.startswith("src/")` | reconciler will widen beyond `src/` |
| `prob_floor: float` | `0.05` (current conditional-probability floor) | reconciler may use a different floor |

The caller in `co_change_check.py` MUST pass these explicitly at their current
values, e.g. `get_git_co_changes(commit_window=200, file_filter=_default_src_py_filter, prob_floor=0.05)`,
so that a reader can see behaviour is unchanged and the characterization test proves it.

Do **not** add any other parameters. Do **not** "improve" the algorithm.

## 4. Characterization test (WRITE THIS FIRST, before any extraction)

Create `tests/test_co_change_core.py`.

**Step 1 — pin current behaviour against a fixture git history.**
- Build a temporary git repo in `tmp_path` with a known, small sequence of commits
  touching a controlled set of `src/*.py` files (and at least one non-`src/`,
  non-`.py` file to prove the filter excludes them).
- Call the CURRENT `co_change_check.get_git_co_changes()` (before extraction)
  against that repo and record the exact returned probability dict as the
  expected fixture value in the test.
- Assert the structure: keys are file paths, values are dicts of
  `{other_file: probability}`, probabilities are floats, and the `0.05` floor is
  respected (no entry below 0.05).
- Include at least one assertion proving the `src/`-only filter excludes a
  non-`src/` file, and one proving the `.py`-only filter excludes a non-`.py` file.

**Step 2 — pin the caller's output contract.**
- Add a test calling `run_co_change_estimator(changed_files)` against the same
  fixture repo and assert every returned dict has keys
  `{staged, unstaged, confidence, reason, probability}` and that `confidence` is
  always one of `EXTRACTED`, `INFERRED`, `AMBIGUOUS`. This locks the contract
  `ai_review.py` depends on.

**Step 3 — run it against the UNMODIFIED code and confirm it passes.**
This is the baseline. Commit it (or at least record the green run) before extracting.

## 5. Extraction steps (only after §4 is green)

1. Create `.agent/scripts/co_change_core.py`. Move the functions listed in §3.1
   verbatim, applying only the §3.3 parameterisation to `get_git_co_changes`.
   Preserve the `harness_utils` import fallback pattern exactly as it appears in
   the current `co_change_check.py` (the `try/except ImportError` with the
   `src/scripts` path insert).
2. In `co_change_check.py`, replace the moved function bodies with imports from
   `co_change_core`, and update the single call site to pass the §3.3 defaults
   explicitly.
3. Run `tests/test_co_change_core.py`. It MUST pass with identical expected
   values — no fixture numbers changed. If any probability differs, the
   extraction altered behaviour: STOP and report, do not adjust the test to match.
4. Run the full existing suite (`pytest tests/`). Nothing should change,
   especially `tests/test_ai_review.py` (which mocks the estimator and must stay green).

## 6. Acceptance criteria (all must hold)

- [ ] `tests/test_co_change_core.py` exists, was written before the extraction,
      and pins both `get_git_co_changes` output and `run_co_change_estimator`'s
      contract.
- [ ] `co_change_core.py` exists and contains the moved logic.
- [ ] `co_change_check.py` imports from it and calls with explicit current-value args.
- [ ] `run_co_change_estimator`'s body and output shape are unchanged (diff shows
      only the moved-out functions replaced by imports + explicit call args).
- [ ] `ai_review.py` is untouched (zero lines changed).
- [ ] Full `pytest tests/` passes, identical to pre-change results.
- [ ] The characterization fixture numbers are identical before and after.

## 7. Verification protocol for Peter (how to check Qwen's work)

Because the co-change engine had no prior test coverage, do not verify by reading
the implementation for correctness — verify by running:

1. Confirm `tests/test_co_change_core.py` was committed/recorded green **before**
   `co_change_core.py` existed (check commit order or ask Qwen to show the baseline run).
2. `git diff` on `co_change_check.py` — confirm it shows only: functions removed,
   imports added, one call site gaining explicit args. Nothing else.
3. `git diff` on `ai_review.py` — confirm it is empty.
4. Run `pytest tests/` — confirm green, same count as before.
5. Apply HIB-GEMINI-01 discipline: treat Qwen's "done" as a hypothesis; the
   passing characterization test against unchanged fixture numbers is the evidence.

## 8. Notes / findings surfaced during design (not part of this task)

- **Coverage gap (backlog candidate)**: the co-change engine
  (`get_git_co_changes` / `run_co_change_estimator`) had zero real test coverage
  before this task. This spec incidentally fixes that. Worth a note that the new
  test is now a guard for the live pre-commit advisor, not just scaffolding.
- **Open design question for the reconciler (defer)**: where harness *self*-boundaries
  get declared — a minimal `architecture.layers`-only `config.yaml`, or a dedicated
  boundary file. Not decided here; belongs to the reconciler spec.
