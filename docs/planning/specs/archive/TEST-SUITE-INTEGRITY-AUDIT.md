# Test-Suite Integrity Audit — Working Findings

**Status**: COMPLETE — not a SPEC, no APPROVED/DRAFT lifecycle applies. All 59 test
files in scope (`tests/` top-level, `tests/unit/`, `tests/e2e/`) have been checked.
This remains a working findings log rather than a formal document, so future
sessions can extend it if Peter opens a new audit scope (e.g. `tests/data/`, or a
re-check after `SPEC-loop-closure-verification.md` ships).
**Started**: 2026-08-02
**Origin**: Item (5) of Peter's original loop-effectiveness plan — "assess whether the
test suite tests the loops correctly, or has it been jury-rigged to pass by an agent
looking for expediency." Distinct from and complementary to `LOOP_INVENTORY.md`
(which audits producer/consumer loops) and `SPEC-loop-closure-verification.md`
(which builds general tooling for that). This audit is specifically about **test
integrity** — not "does the mechanism work" but "does the test suite honestly verify
that it does, or has a test been weakened/left incomplete in a way that masks a
defect."

**Related parallel work**: a separate, narrower task was delegated independently —
a mechanical sweep for the specific `subprocess`-not-imported bug pattern (confirmed
three times already: `co_change_reconciler.py`, `wiki_lint.py`, `wiki_compile.py`)
across `.agent/scripts/`, `src/scripts/`, `bootstrap/`, and `.agent/skills/**/scripts/`.
Results recorded separately in `docs/planning/specs/archive/SUBPROCESS-IMPORT-SWEEP.md` — check
that file before re-deriving anything about this bug pattern from scratch here.

**Two Gemini tasks dispatched 2026-08-04 — both RESOLVED and independently
verified**: (1) `test_ai_review.py`'s `test_token_write_fails_gracefully` — traced
real stderr-warning behavior in `ai_review.py` first (confirmed genuine, not a
docstring mismatch), then completed the assertion; (2) all three remaining
tautological tests — `test_validate.py`'s `test_warnings_only_passes`/
`test_errors_fail`, and `test_phase3_enforcement.py`'s
`test_count_diff_lines_exactly_at_threshold_uses_standard_strategy` — all now
genuinely invoke the real production code path rather than re-asserting a hand-set
value. Every specific claim in both reports was independently verified against the
actual source before being accepted — see "Findings by file" below for detail.

---

## Methodology

No shell/git access on the user's machine through available tools — this audit is
**static analysis of current test file content**, not git-history diffing. It cannot
detect a test that was weakened *and then the weakening was itself later reverted*;
it can only detect what's in the file today. Two things are being watched for,
kept deliberately distinct because they carry different implications:

1. **Genuine H-03 gaming signatures** (per `governance.md` §3.3's rationalization
   table): commented-out assertions, `assert True`, bare `except: pass` swallowing a
   real test failure, `skip`/`xfail` markers without a documented reason, `sys.exit(0)`
   in hooks. This would be a process violation if found.
2. **Coverage gaps and incomplete assertions** — not gaming, but the same practical
   danger: a green suite that doesn't actually verify the thing it looks like it
   verifies. This is the more common finding so far, and each instance is graded
   into one of three shapes (see Taxonomy below).

## Taxonomy of findings (four shapes identified so far)

| Shape | Description | Danger level |
|---|---|---|
| **Coverage gap** | Nobody wrote a test for X; the rest of the suite is honest | Low — straightforward backlog item |
| **Masking-resistant blind spot** | The code's own error handling (a bare `except`) hides a defect behind a working fallback, so no black-box behavioral test — however well-designed — could catch it without specifically testing implementation internals | Medium — structurally invisible, not anyone's fault, but needs a deliberately different test design to close |
| **Incomplete assertion with self-aware residue** | Test *looks* complete (right mocks, plausible docstring) but a promised assertion was never written; author's own uncertainty is left as dangling comments in place of the check | Highest of the three — closest in spirit to what H-03 warns about, even though nothing was deliberately weakened |
| **Tautological / self-fulfilling test** | Test hand-sets a value, then asserts that same value, without ever invoking the production code path the docstring claims to verify | Silent — no residue, no exception; an assertion that can never fail regardless of whether the real logic works |

No genuine H-03 gaming signature (category 1 above) has been found in any file
checked so far. One finding (`test_phase3_enforcement.py` Finding B) sat right at
the boundary of that category and has since been fixed and independently verified
— see Progress Summary and Recommendation section below. All tautological-test
findings (category 4) and the incomplete-assertion finding (category 3) are now
resolved as well.

---

## Progress Summary (update this each session)

**Milestone: all 58 files across `tests/` top-level (31) and `tests/unit/` (27) are
now fully checked.** Only `tests/e2e/` (one main script plus a fixture project
directory) remains within this audit's scope. `tests/data/` is fixture data only
(a CSV and a fixture-cases directory) — not tests to audit for gaming, though
`false_positive_cases.csv` might be worth a glance later for its own data-quality
reasons, unrelated to this audit's purpose.

**Overall verdict, 58 files complete**: this is a fundamentally honest test suite.
No true H-03 gaming signature (deliberately weakened assertion) found in any file
checked. Multiple genuinely exemplary files across both tiers: `test_check_spec.py`'s
fail-open/fail-closed partitioning, `test_co_change_core.py`'s exact-probability
characterization testing, `test_install.py`'s F-COLD-1 halt verification,
`test_framework_consistency.py`'s working documentation-consistency gate,
`test_rebuttal.py`'s real-git cross-module hash verification and live tamper
injection, `test_downgrade.py`'s deliberate mid-flight corruption-and-rollback test,
`test_prompt.py`'s prompt-regression guard, `test_posture.py`'s direct HIB-080
mechanism testing, and `test_state_persistence.py`'s real-SQLite multi-tenant
safety test. This is a well-built suite overall — the handful of genuine findings
are exceptions against a strong baseline, not a pattern.

**Nine numbered findings, seven resolved, two open representing two distinct
underlying issues (since #5 completes #1)**:
1. `test_distill_dream.py` — coverage gap (never checks for the `Generated:` field). Open — fix is bundled in `SPEC-loop-closure-verification.md` v1.4, not yet implemented.
2. `test_wiki_compile.py` / `test_co_change_reconciler.py` — masking-resistant blind
   spot (subprocess bug structurally invisible to black-box testing). Open — fix bundled in v1.6/v1.7 Scenario 4p, not yet implemented.
3. `test_ai_review.py` — one incomplete assertion. **RESOLVED 2026-08-04**, independently verified.
4. `test_validate.py` — two tautological tests. **RESOLVED 2026-08-04**, independently verified.
5. `test_harness_health.py` — **completes finding #1**: the consumer-side tests
   also hand-craft the field the producer never writes, confirming the
   producer/consumer contract was never tested from either side. Open, same issue as #1, not a distinct one.
6. `test_framework_consistency.py` — soft `ImportError`-swallowing pattern.
   **RESOLVED 2026-08-04**, independently verified.
7. `test_phase3_enforcement.py` — Finding A (tautological) **RESOLVED 2026-08-04**;
   Finding B (the most serious finding of the audit) **RESOLVED 2026-08-04**, both
   independently verified. See Recommendation section for full detail on both.
8. `tests/unit/test_context_loader.py` — the one test for `get_adr_context()`
   monkeypatches around the exact `DOMAIN_REGISTRY` dependency that's confirmed
   broken in production (connects directly to LOOP-014's fourth finding). Not
   gaming — legitimate isolation practice — but means this test provides zero
   signal that the real wiring is broken. Open by design; naturally resolved once
   LOOP-014's `architecture_checks.DOMAIN_REGISTRY` gap is addressed, not via a
   test change.
9. `tests/unit/test_upgrade_units.py` — `test_yaml_rename_skips_comment_line` and
   two sibling tests had incomplete assertions or parallel regex copies instead of
   exercising the real migrator. **RESOLVED 2026-08-04**, independently verified.

---

## Findings by file

### `tests/test_distill_dream.py` — Coverage gap
All 8 tests are well-constructed (real fixtures, dedicated HIB-DREAM-03 threshold
regression tests). **None check for a `Generated:` field** in the proposal card
output — the exact producer whose missing schema field is being fixed in
`SPEC-loop-closure-verification.md` v1.4. The suite is 8/8 green while never having
asserted the one thing that turned out to be broken. Not gaming — nobody was
thinking about the consumer's parsing requirements when writing the producer's tests.

### `tests/test_wiki_compile.py` — Masking-resistant blind spot
Docstring documents a real, deliberate architecture change: *"Change 2 (S0-24):
DOMAIN_REGISTRY is now loaded from `.agent/config.yaml` instead of being hardcoded."*
Six tests thoroughly verify that config-driven loading mechanism (empty config,
explicit empty, missing sources, happy path, absent config, partial sources) — no
gaming, genuinely good design.

However: every one of these six tests calls `load_domain_registry()`, which
internally, unconditionally, calls a nested `_find_project_root()` containing the
unimported-`subprocess` bug (see `SPEC-loop-closure-verification.md` v1.6/v1.7).
Every test run triggers the masked `NameError`, silently falls through to the safe
fallback, and passes — because the fallback still resolves correctly. **This test
suite provides zero signal on whether that bug exists or not.** It cannot
distinguish "the git-rev-parse path ran successfully" from "it silently failed and
fell through to the fallback." This is exactly why v1.6/v1.7 specified a *new*,
dedicated test (Scenario 4p) rather than assuming existing coverage would catch a
regression here — it wouldn't have.

### `tests/test_co_change_reconciler.py` — Same masking-resistant blind spot, confirmed via CLI subprocess execution
This file runs `co_change_reconciler.py` as a real subprocess
(`subprocess.run([sys.executable, str(_RECONCILER_PATH), ...])`) rather than via
import/mock — a genuinely strong testing approach for CDR ledger status
classification (accepted/tolerated/resolved/escalated/ambiguous, malformed-ledger
fail-loud, missing-ledger graceful degradation — all well covered, no gaming).

But `co_change_reconciler.py`'s `PROJECT_ROOT = _find_project_root()` executes at
**module level**, before `main()` even parses `--project-root` — meaning every single
one of the 11+ subprocess invocations in this test file triggers the identical
subprocess bug on load, every time, silently masked the same way. Same conclusion as
above: a fully green, well-designed suite with zero signal on this specific defect.

### `tests/test_ai_review.py` (101KB, the harness's largest and most safety-critical test file) — Read in full. Overall: **high quality, no gaming found.**
Real regression tests tied to specific bug/incident IDs (BUG-03/04/05, SE-01/02,
HIB-047/048, HIB-068 oversized-diff matrix). Explicit fail-closed testing on JSON
parse errors for both low- and high-risk commits. An honest self-governance test
(`TestAiReviewImportCount`) enforcing a ratchet ceiling on its own import count, with
a documented plan to lower it further after a named refactor (T1-E-01) — the kind of
technical debt tracking that's the *opposite* of gaming.

**One incomplete-assertion finding, RESOLVED 2026-08-04** — `test_token_write_fails_gracefully`:
docstring promised *"the gate logs a warning but continues,"* the test set up
`patch("sys.stderr.write") as mock_stderr_write` clearly intending to verify that,
but only asserted `exit_code == 0`. Where the stderr assertion should have been, the
test instead contained the author's own unresolved reasoning, left in as comments.
**Fixed and independently verified**: traced the real `_run_review()` lock-failure
path in `src/scripts/ai_review.py` first (confirmed the code genuinely does print
`f"⚠️  [GATE WARNING] Failed to lock session file for update: {e}"` to stderr on a
lock exception — this was a real behavior, not a docstring/code mismatch), then
completed the assertion to check the actual captured message. Confirmed the fixed
test file on disk matches exactly.

### `tests/test_check_spec.py` (27.81 KB) — Clean
Genuinely strong. Config-vs-availability failure partitioning is well-designed security
logic, correctly tested: network timeout/connection error → fail-open (legitimate
degraded-mode signal); auth failure or missing credentials → fail-closed
(configuration neglect, not transient). Bypass safety tests correctly reject
empty/short reasons, only succeed with a real explanation, and confirm the event is
logged. Mode-conditional behavior (discovery/incremental/contractual) thoroughly
tested, including contractual mode correctly rejecting local bypasses other modes
allow. No gaming signatures found.

### `tests/test_init_session.py` (21.62 KB) — Clean
Covers HIB-053/HIB-053b write-before-verify guards (an `outcome_override` or
`agent_session_close.json` claiming "success" with no actual commits is correctly
downgraded to "partial"), session_kind asymmetric handling (analysis-kind sessions
can legitimately succeed without commits; code-kind sessions cannot), and agent-close
file consumption/session-ID-mismatch handling. No gaming found. One trivial
observation: `test_silent_on_missing_session_id` has zero assertions — it only
verifies the function doesn't raise on empty input. Docstring ("Non-fatal execution
test") doesn't overclaim what's being checked, so this isn't a finding, just the
thinnest test seen so far.

### `tests/test_install.py` (14.02 KB) — Clean
BUG-01 regression coverage for hook wiring (all three hook types — pre-commit,
commit-msg, pre-push — verified installed, not just one). Idempotency correctly
tested for both Claude Code hook installation and `.gitignore` provisioning.
`test_blocked_commands_idempotent` correctly verifies a customized destination file
is NOT overwritten by a source file, not just that copying works. The F-COLD-1 halt
test (`test_installer_halts_on_harness_target`) verifies `detect_stack` was never
called via mock assertion, not just that the exit code was 1 — confirming the halt
genuinely short-circuits rather than continuing and happening to fail later.
`test_precommit_template_exclude_and_regex_escaping` includes a good negative
assertion (explicitly checks the *unescaped*, wrong regex output is absent, not just
that the correct one is present). No gaming.

### `tests/test_upgrade.py` (19.25 KB) — Clean
Thorough integration coverage of the upgrade/downgrade machinery: atomic rollback
verified by literal byte-content comparison of `config.yaml` after a simulated
mid-migration failure, stale-backup blocking without `--force`, conflict/sidecar
preservation of a developer's custom edit to a framework-owned file,
checksum-preflight mismatch threshold behavior, migration-chain fork resolution
(picking the correct branch when two migrations share a `from_version`), and
idempotency (repeat-run `.gitignore` entries not duplicated). No gaming.

### `tests/test_co_change_core.py` (17.57 KB) — Clean, exemplary
Deterministic characterization testing: builds a real temporary git repo with a
hand-designed, hardcoded commit sequence, then asserts **exact** computed
co-change probabilities (e.g. `P(b|a) = 2/3`) to `1e-9` precision — not just "above
the floor." The file's own docstring states its purpose bluntly: *"The test MUST
fail if any computed probability changes. That is its entire purpose."* This is the
model pattern for regression-proofing a probabilistic/heuristic component. No gaming.

### `tests/test_validate.py` (16.69 KB) — Mostly clean, one tautological-test finding
Strong overall — notably the API-preflight test, which verifies a raw API key, a
`Bearer <key>` header, and a bare key fragment are all independently redacted from
stderr output on a simulated failure; sandbox-removal postcondition testing
correctly handles read-only files; subprocess timeouts are enforced and checked, not
just assumed.

**Finding, RESOLVED 2026-08-04**: `TestOverallResult.test_warnings_only_passes` and
`test_errors_fail` were tautological. The first set `v.warnings = 3; v.errors = 0`
and then asserted `v.errors == 0` — a value the test itself just assigned two lines
earlier — despite a comment reading `# Validator run() returns exit code`
immediately above; `run()` was never called and no actual exit code was ever
checked. `test_errors_fail` did the mirror version. **Fixed and independently
verified**: both now call the real `Validator.run_all()` (with `run_check` patched
out to isolate the aggregation logic), and the fix correctly adds `(tmp_path /
".agent").mkdir()` first — necessary because `run_all()` has its own "is harness
installed" guard clause ahead of the errors/warnings branch being tested. Confirmed
against the actual `run_all()` source: `if errors > 0: return 1; elif warnings > 0:
return 0; else: return 0` — the new tests genuinely exercise this real logic path.

### `tests/test_harness_health.py` (10.89 KB) — Clean overall, but completes the picture on finding #1
State-file size thresholds, capability-calibration precision math (0.67 / 0.10 / 0.83,
hand-verified against tp/fp inputs), and unmerged-branch staleness detection are all
correctly and thoroughly tested. No gaming.

**Important completion of the `test_distill_dream.py` finding**: all three
dream-proposal staleness tests (`test_staleness_clean/_warn/_critical`) construct
their fixture files by hand, writing the `Generated:` field themselves
(`recent_prop.write_text(f"Generated: {today_str}\n", ...)`) rather than generating
the file via `distill_dream.py`'s real code path. These tests correctly verify the
*consumer's* parsing boundaries (clean/warn/critical day thresholds) — but they
silently assume the `Generated:` field exists, because the test itself put it there.
Combined with `test_distill_dream.py` (which tests the producer's routing logic but
never checks for this field either), **the schema contract between these two files
was split across two test suites, and neither one actually tests the contract
itself.** Each side correctly tests its own half in isolation, with the other
half's precondition quietly assumed rather than verified. This is now direct,
two-sided evidence for why `SPEC-loop-closure-verification.md` Scenario 4q
specifically requires a dedicated producer-output-vs-consumer-parser contract test
for this pair — not an inference from one file, but confirmed from both.

### `tests/test_uninstall.py` (10.46 KB) — Clean
Good safety-gating tests: developer spec-file content correctly triggers a
confirmation prompt before uninstall proceeds; dry-run correctly takes precedence
over `--force`. `test_uninstall_state_file_removed_last` verifies removal *ordering*
via a tracking wrapper around the real `_remove` method, not just checking the final
state — a stronger test design than asserting end-state alone. No gaming.

### `tests/test_framework_consistency.py` (10.40 KB) — Clean, and itself a positive counter-example. Soft spot RESOLVED 2026-08-04
T1-K-09's consistency gate genuinely works: verifies every workflow slug in
`AGENTS.md` §2 resolves to a real file in `.agent/workflows/`, includes explicit
regression guards for two previously-dead slugs (`/perf`, `/qa`), and checks
section-label consistency (H/S/C/G vs. legacy P-series). This is the same *category*
of documentation/code consistency check `wiki_lint.py`'s orphaned-rules-check was
supposed to provide (LOOP-013) — and this one actually works. Worth citing alongside
`test_check_spec.py` and `test_co_change_core.py` as a model example.

**Finding, RESOLVED**: `test_no_explicit_default_for_known_config_keys` and
`test_harness_config_distinguishes_none_from_missing` previously silently `return`ed
(no assertion, no failure) on `ImportError` from `harness_utils` — meaning any
unrelated breakage in `harness_utils.py`'s import chain would have made these tests
silently pass forever without ever actually checking anything. **Fixed and
independently verified**: both `try/except ImportError: return` guards removed
entirely; `harness_utils` is now imported directly and unguarded, matching how
every other test file in this suite imports it. Confirmed the underlying test
assertions are otherwise unchanged — since `harness_utils.py` is a permanent core
file always present in a valid environment, this closes the blind spot without
altering any tested behavior. Test count (9 in the file) verified by direct count,
matching Gemini's report exactly.

### `tests/test_harness_config.py` (10.14 KB) — Clean
Precise boundary-matching tests against this repo's own real `config.yaml` (not a
fixture). `test_partial_prefix_does_not_match` is a good specific edge case: verifies
`"bootstrapper.py"` does NOT wrongly match a `"bootstrap/"` prefix boundary. No
gaming.

### `tests/test_check_traceability.py` (10.01 KB) — Clean
Good bypass-path coverage (merge commits, docs-only, `--no-trace` with a length
threshold, contractual-mode rejection of `--no-trace`). `test_hib_076_self_ratification_prevented`
verifies against the *committed* `HEAD` state of a backlog file via `git show`, not
the working directory — correctly preventing a commit from inventing its own
traceability reference by editing the backlog in the same commit. No gaming.

### `tests/test_providers.py` (9.40 KB) — Clean
`test_unavailable_provider_raises` is explicitly labeled SEC-02 ("must raise, not
silently skip") — good security-relevant test. Retry logic and a JSON-fence-stripping
regression (`Anthropic` provider) both verified concretely, not just smoke-tested.
No gaming.

### `tests/test_phase3_enforcement.py` (9.39 KB) — Two findings, both RESOLVED 2026-08-04
Most of the file is solid: task-magnitude classification (hotfix/rfc/docs branch
heuristics), HALT escape-hatch behavior with and without a bypass reason, and a
concrete reasoning-token budget-summation check (350 = 100+50+200, hand-verified).
No gaming in those.

**Finding A — tautological test, RESOLVED**: `test_count_diff_lines_exactly_at_threshold_uses_standard_strategy`
claimed to test boundary behavior "at exactly threshold lines," but its entire
assertion was `assert threshold == 400 or isinstance(threshold, int)` — trivially
true regardless of the actual value. **Fixed and independently verified**: now
constructs a real diff of exactly `threshold` lines, calls the actual
`count_diff_lines()`, and asserts `counted == threshold` plus the real
strategy-boundary comparison (`is_large_diff = counted > threshold`, matching
`ai_review.py`'s actual `if diff_lines > large_diff_threshold` logic). Confirmed
against `count_diff_lines()`'s real implementation that this assertion holds.

**Finding B — the most concerning pattern found this session, RESOLVED 2026-08-04**:
`test_missing_session_json_budget_assumes_zero_spent` originally wrapped
`_run_review()` in three separate try/except blocks, each shaped like:
```python
try:
    _run_review()
except SystemExit as exc:
    assert exc.code != 1 or "budget" not in str(exc).lower()
except Exception:
    pass
```
If `_run_review()` raised **any** exception other than `SystemExit` — a broken
mock, a genuine regression, anything — it was silently swallowed and the test
passed. This was not application code masking a bug via a bare `except`; it was the
**test itself** authored with an escape hatch that hid failure. This was the
closest instance found all session to genuine H-03 territory. **Fixed and
independently verified against the live source — full detail in the Recommendation
section below.** The root cause turned out to be even more fundamental than the
weak assertion alone: the original test's `get_changed_files=[]` mock caused an
*earlier* unrelated early-return, meaning the test never even reached the code path
it was named for.

### `tests/test_cdr_ledger.py` (9.01 KB) — Clean
`TestLedgerFileValid` tests the actual real `coupling_decisions.yaml` file against
the schema (not just a mock). `TestConstraintLogic` covers all eight constraints
(C1–C8) with precise positive/negative cases, including a good anti-confabulation
check (C3: a "tolerated/unevaluated" decision must NOT carry a rationale). No
gaming.

### `conftest.py` (8.41 KB) — Fixtures only, nothing to evaluate
No test assertions in this file (as expected for a conftest). `_get_git_v110_file`'s
graceful fallback to mock content on a `git show` failure is reasonable fixture
setup, not a gaming concern.

### `tests/test_acceptance_check.py` (7.92 KB) — Clean
Good coverage of the `HIGH_RISK_SCHEMA_CHANGE` flag (blocked without it, allowed
with it), explicit fail-open vs. fail-closed offline modes (`--fail-closed` flag
tested both ways), strict-mode rejection of partial verdicts. A code comment shows
deliberate awareness of avoiding a flaky real-LLM-call fallback in tests. No gaming.

### `tests/test_architecture_checks.py` (7.71 KB) — Clean, directly tests the incident that started this whole effort
`test_ratchet_posture_grandfathers_untouched_violation` and
`test_ratchet_posture_blocks_on_touched_file_violation` directly reproduce the
HIB-080 scenario (the ratchet-posture grandfathering bug that motivated
`SPEC-loop-closure-verification.md` in the first place), using a real baseline
manifest with SHA256 verification — distinguishing "grandfathered in untouched
file" (exit 0) from "blocks on touched file" (exit 1). Also covers T1-K-08's
fail-loud guards (missing config → exit 1; no `architecture:` block → conscious
exit 0; all layer paths missing → exit 1; layers with real files → exit 0) — the
same discipline flagged as a positive counter-example in LOOP-011. No gaming.

### `tests/test_session_health.py` (6.21 KB) — Clean
Real string-level assertions on formatted console output (`"1,000 in / 500 out"`,
truncated session ID `"test_ses…"`), specific detection-logic testing (same file
read 3+ times, a repeated error message appearing 2x), and two separate
missing-file graceful-degradation scenarios (missing events file, missing review
log) each independently verified. No gaming.

### `tests/test_rebuttal.py` (5.61 KB) — Clean, exemplary
Strong integration testing against a *real* git repository, not mocks:
`test_hash_alignment_real_git_repo` confirms `ai_review.py` and `rebuttal.py`'s
independent hash functions produce byte-identical 40-char git write-tree hashes for
the same staged state — directly verifying a cross-module consistency claim, not
just each module in isolation. `test_tamper_detection_unreviewed_staged_file` goes
further: stages an actual second file mid-test and confirms the hash changes,
genuinely proving the tamper-detection property rather than asserting it should
work. No gaming.

### `tests/test_migration_v1_3_0_to_v1_3_3.py` (5.39 KB) — Clean
Idempotency explicitly checked (`migrate()` run twice, asserts the version string
appears exactly once, not zero or two times), field-preservation, missing-file
error handling, and full end-to-end `UpgradeManager`/`DowngradeManager` integration.
No gaming.

### `tests/test_downgrade.py` (4.75 KB) — Clean, exemplary
`test_atomic_rollback_on_downgrade_failure` deliberately injects a migration that
corrupts `config.yaml` mid-flight then raises, and verifies **byte-for-byte**
restoration to the pre-downgrade state — plus confirms the backup file itself is
cleaned up afterward, not just that data was restored. Dry-run verified via exact
before/after content equality (zero writes actually occurred, not assumed). No
gaming.

### `tests/test_pm_scaffold.py` (4.59 KB) — Clean
`test_pm_scaffold_offline_success` wraps `main()` in `except SystemExit` only
(not a bare `except Exception`) — this is a materially different and safe pattern
from the Finding B case in `test_phase3_enforcement.py`: any exception other than a
clean `SystemExit` would still propagate and fail the test normally. Backup-before-
overwrite behavior correctly verified (`.bak` file created, original content
preserved, not just presence-checked). No gaming.

### `tests/unit/test_decisions_log.py` — Clean, and confirms a forward-looking gap
13 tests covering `record_decision()`/`archive_old_decisions()`: append ordering,
empty-field rejection, invalid-date rejection, file-creation-with-header,
extra-fields support, backdated-entry rejection, same-date entries allowed, archival
no-op under threshold, FIFO archival of oldest entries first (built with 29 real
entries, not a trivial case), a deliberately adversarial test that hand-constructs a
disordered log file directly to verify the ascending-order guard fires, a
never-empty-the-log invariant test at `threshold_lines=1`, and a specific BUG-19
regression test (tab characters stripped without corrupting a legitimately
leading-"t" word). No gaming — genuinely thorough.

**Forward-looking gap, not a current defect**: none of these 13 tests pass or check
an `impact` parameter anywhere. Correct and expected —
`SPEC-loop-closure-verification.md` v1.3 (required `impact` classification,
age-weighted retention) is still an unimplemented draft, and this file faithfully
tests the current, pre-v1.3 code. Confirms: once v1.3 ships, this file needs the
four new tests already specified there (Scenarios 4d–4g) — none exist yet, because
nothing to test exists yet either.

### `tests/unit/test_log_decision_cli.py` — Clean, same forward-looking note
One test, genuine real subprocess execution (`subprocess.run()` against the actual
CLI script, not mocked), verifying the current 4-positional-argument invocation plus
`--date` produces a correctly-formatted log entry. No gaming.

**Same forward-looking gap**: `log_decision.py` genuinely has no `--impact` flag
today — confirmed both here and independently during this session's earlier v1.3
spec-drafting work. This test correctly covers only what currently exists; it will
need updating once v1.3's Implementation Map item (adding the `--impact` flag) is
actually built.

### `tests/integration/test_acceptance_check_pydantic_fallback.py` — Clean, genuinely distinct from the top-level file of the same stem
Tests the pydantic-fallback-stub mechanism specifically (different concern from the
top-level `test_acceptance_check.py`, which tests `HIGH_RISK_SCHEMA_CHANGE`
flags/fail-open-closed modes). Genuinely removes `pydantic` from `sys.modules` and
reloads the module to trigger the real fallback path — not just mocking a flag —
then verifies the stub class works, CI fail-closed enforcement (`exit 1`), local
audit-log + visual-warning behavior both with and without the silence flag, and
correctly restores original module state in a `finally` block. No gaming.

### `tests/integration/test_acceptance_hook.py` — Clean
Thorough parametrized branch classification (`_is_feature_branch`), spec-status
parsing across five scenarios including a real edge case (a non-spec file like
`README.md` containing a `status:` line is correctly excluded, not accidentally
matched), branch spec-ref extraction with dedup and empty/failure handling, and
seven distinct `main()` integration scenarios correctly distinguishing exit codes
0 (nothing to check)/1 (spec not accepted)/2 (non-feature branch skip). No gaming.

### `tests/integration/test_ai_review_failopen.py` — Clean, and directly relevant to this session's own findings
`test_ai_review_route_decision_integration_namespace_safety` is a direct regression
guard against exactly the bug class this whole session has been hunting — it
verifies `route_decision` genuinely has access to `get_harness_config` at runtime
without a `NameError`, not merely that an import statement exists in the source.
Also covers `_handle_api_unavailable`'s fail-open persistence directly, and
oversized-diff fail-open logging for the line-ceiling and char-ceiling paths
separately (not conflated into one test). No gaming.

### `tests/integration/test_ai_review_context_selection.py` — Clean, third genuinely distinct file sharing this stem
(Initially skipped by mistake — see correction note above; now checked.) Covers
`load_review_context()`'s section-selection logic: verifies secrets/TDD rule
sections are always included, while vocabulary and ADR-decision-block sections are
only injected when an ADR trigger is actually present in the diff — tested both
ways (present/absent), not just the positive case. Also includes a fallback-stub
test that **honestly documents a known limitation** rather than concealing it: when
Pydantic is absent, the stub `ArchViolation` model accepts an invalid `Literal`
severity value (`"CRITICAL"`) without validation, and the test explicitly asserts
and comments on this being current, accepted behavior rather than silently passing
over it. A `skip_paths` merge/dedup test across two config sources (JSON +
`config.yaml`) with a real overlapping-entry case. No gaming — the
honest-limitation-documentation pattern is worth citing as a positive example
alongside `TestAiReviewImportCount`'s ratchet-ceiling approach in the top-level file.

### `tests/integration/test_baseline.py` — Clean
Real tamper-detection test: `test_load_baseline_tamper_detection` actually modifies
baseline entries without updating the manifest hash, and confirms `load_baseline()`
correctly returns `None` — a genuine security-invariant check, not an assumption.
AST region-hash extraction verified to produce different hashes for two distinct
functions in the same file (not just "a hash was returned"). Incidentally
reconfirms `architecture_checks.py`'s current correct location under `universal/`
(`test_scan_current_violations_real_arch_script_path` asserts the real path exists).
No gaming.

### `tests/integration/test_capability_calibration.py` — Clean, directly confirms LOOP-002
The same loop this session's `LOOP_INVENTORY.md` identified as "genuinely closed
and working" — now confirmed with hand-computed precision: weight `0.9` after one
accepted rebuttal, `0.945` after a subsequent rejection (`0.9×1.05`, verified via
`pytest.approx`), correct clamping at both the `0.5` floor (20 more accepted
rebuttals) and `1.5` ceiling (40 rejected). A HIB-049 regression test verifies
`REMEDIATED` rebuttals don't pollute the false-positive counter — the same
anti-confabulation discipline as `test_cdr_ledger.py`'s C3 check. No gaming.

### `tests/integration/test_check_spec_pass1_parsing.py` — Clean, genuinely distinct from the top-level file of the same stem
Tests Pass 1's structural parsing specifically (different concern from the
top-level file's fail-open/fail-closed config-availability and bypass-safety
testing): nested-subheading section-boundary detection, old/new spec-convention
alias matching, custom alias-override config, error messages that list every
attempted alias on a missing concept, and Gherkin/assumptions format validation
failures. `test_pass1_smoke_all_three_specs` runs Pass 1 against **real archived
spec files** in the repo (not synthetic fixtures) and asserts at least 3 were
actually checked, guarding against the paths silently resolving to nothing. No
gaming.

### `tests/unit/test_check_traceability_hardening.py` — Clean
Precise regex-matching tests distinguishing versioned (`SPEC-v1.4.10-governance-hardening`)
from legacy numeric (`SPEC-001`) spec-ID formats, plus a correct negative case
confirming an unrelated tag (`FID-1`) does not false-positive-match. An exact
truncation check: a 300-character `--ack-no-trace` reason is confirmed truncated to
precisely 250 characters in the logged event, not just "shorter than before."
`test_merge_trace_gate_blocks_without_ack` verifies the actual recovery-command hint
text appears verbatim in captured stderr, not merely that an error occurred. Both
archived and non-archived spec-file-path resolution tested. No gaming.

### `tests/unit/test_config_loader.py` — Clean
Fallback YAML parser tested for parity against real, actual config templates in the
repo (not synthetic fixtures). Config-cache tested via true object identity
(`cfg1 is cfg2`, not just equal values). Section-scoped mode override correctly
verified not to leak from a deliberately conflicting top-level `mode: ignore`. A
second, independent static-scan test enforces the same "no redundant `default=`"
rule as `test_framework_consistency.py`'s finding #6 — genuine double coverage of
that invariant from two different files. No gaming.

### `tests/unit/test_constraint01_budget.py` — Clean, small but genuinely meaningful
Calls `load_review_context()` **without mocking** the context files — measures real
estimated token cost against this repo's actual live `review_context_universal.md`/
`project.md` content, with a hard ceiling assertion (2000) that includes the real
production caps (`+600`/`+400`, matching `ai_review.py`'s actual `repo_map`/
`adr_context` character caps). A genuine regression guard against context bloat
creeping up over time, not a synthetic check. No gaming.

### `tests/unit/test_context_loader.py` — One test, no gaming, but a concrete finding about signal loss
`test_get_adr_context_non_root_cwd` correctly verifies `get_adr_context()`'s
domain-matching logic works when `DOMAIN_REGISTRY` is populated — by directly
monkeypatching `context_loader.DOMAIN_REGISTRY` to `{"TRANSACTIONAL_INTEGRITY"}`
before the call. Legitimate unit-testing practice in isolation, not gaming.

**Finding, connects to LOOP-014**: recall this session's earlier investigation —
`context_loader.py`'s real `DOMAIN_REGISTRY` comes from `from architecture_checks
import DOMAIN_REGISTRY`, which always fails (confirmed: `architecture_checks.py`
never defines it) and silently falls back to an empty `set()`. In actual
production, this domain-matching path never fires for any real commit. This test —
the only one covering this function — sidesteps that broken dependency entirely by
injecting a working value directly, meaning it provides **zero signal that the real
wiring is broken**. Same practical danger as the masking-resistant blind-spot
findings elsewhere in this audit (`wiki_compile.py`, `co_change_reconciler.py`), via
a different mechanism: a deliberate mock around a known-broken dependency rather
than a swallowed exception. Independent confirmation that the LOOP-014 bug has
persisted invisibly — even this function's dedicated unit test never exercises the
real, currently-broken production path.

### `tests/unit/test_exception_standards_wrapper.py` — Clean
Precondition-skip behavior verified via actual captured output text (`"SKIPPED-precondition"`),
not just exit code. A real manifest-consistency check confirms the wrapper script
is correctly registered as framework-owned in `bootstrap.manifest`. No gaming.

### `tests/unit/test_gate_context.py` — Clean, exemplary
Schema v1.0 backward-compatibility loading, a real write-then-load round-trip test,
schema-version-mismatch degradation confirmed to return `None` (not silently
accept), a precise TODO/FIXME delta calculation across mixed add/remove lines, and
a deterministic-findings-section renderer test matching exact expected string
fragments. `test_session_id_lifecycle_regression` is a standout: confirms events
logged *before* session initialization get specifically `"pre-session-init"` (not
`"unknown"` or `None`), and events logged after get the correct session UUID —
exactly the precision this whole audit values in fallback-value handling. No gaming.

### `tests/unit/test_harness_utils.py` — Clean, small, security-relevant
Confirms `_safe_git_env()` correctly excludes secret API keys (`ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`) and `PYTHONPATH` (a legitimate subprocess-injection precaution),
while preserving `PATH` and `GIT_*`-prefixed variables. Precise positive/negative
checks throughout. No gaming.

### `tests/unit/test_init_session_stashing.py` — Clean
Precise subprocess call-count assertions distinguishing the clean-tree-skip,
TTY-accept, and TTY-decline paths (0/2/1 calls respectively — not just "behavior
differs"). `test_drop_session_checkpoint_stash_on_clean_close` verifies the exact
subprocess args list to confirm the correct stash entry is matched and dropped by
session ID, not just that some stash was dropped. No gaming.

### `tests/unit/test_migration_v1_4_10_to_v1_4_11.py`, `test_migration_v1_4_11_to_v1_4_12.py`, `test_migration_v1_4_12_to_v1_4_13.py`, `test_migration_v1_4_9_to_v1_4_10.py` — All clean
Consistent with the migration-test pattern already established elsewhere in this
audit: migrate/downgrade round-trips, missing-file and missing-version-key error
handling. The v1.4.12→v1.4.13 migration stands out: real AST/regex literal
extraction from actual sample source files (not synthetic strings), and —
notably — `test_schema_hardening_config_readers` verifies that
`enforce_hardened_schemas.py` and `analyze_schema.py` both correctly *read back*
the config-driven exemptions this migration writes, closing the full
producer→consumer loop for this migration rather than only testing the write side.
No gaming in any of the four.

### `tests/unit/test_posture.py` — Clean, exemplary
Direct unit test for the posture-disposition engine — the exact mechanism HIB-080's
call-site bug flowed into. Precise coverage: invariant-floor pinning confirmed
unoverridable even with an explicit override attempt, observe-posture expiry (past
date → ratchet, future → stays observe), and the three-way baseline-grandfathering
matrix — matching file/hash/untouched → `GRANDFATHERED`, touched file → `BLOCK`
even with a matching hash, hash mismatch → `BLOCK`. No gaming.

### `tests/unit/test_route_decision.py` — Clean
`test_classify_commit_risk_override_defaults_empty_fails_closed` is a genuinely
valuable fail-safe test: confirms that a misconfiguration (`override_defaults=True`
with empty pattern lists, which would silently disable *all* high-risk
classification) correctly fails closed by treating everything as high-risk rather
than nothing — same defensive-design family as `architecture_checks.py`'s
zero-files-scanned guard. No gaming.

### `tests/unit/test_snapshot_logs.py` — Clean
Real file-content preservation verified after snapshotting, and a correct negative
test confirming zero-byte files are genuinely skipped (snapshot files not created),
not just "behavior differs." No gaming.

### `tests/unit/test_sqlite_schema_drift.py` — Clean
Genuine real-database test: creates an actual in-memory SQLite table with a legacy,
drifted schema (missing columns), runs the real migration function, and verifies
via `PRAGMA table_info` that columns were actually added while the existing one was
preserved. Idempotency confirmed by running twice. No gaming.

### `tests/unit/test_state_persistence.py` — Clean, one of the most thorough files this session
Real SQLite tests throughout, not mocked except deliberately for error-simulation.
Upsert behavior confirmed by exact row counts, WAL mode confirmed via a real
`PRAGMA` query, idempotent schema creation confirmed via exact `schema_version` row
count, a real rebuild-from-JSONL test with `ON CONFLICT DO NOTHING` idempotency
confirmed by running twice, and — notably — a genuine multi-tenant safety test:
`test_cleanup_project_rows_only_removes_target_project` confirms deleting one
project's rows leaves another project's rows in the shared DB completely untouched.
No gaming.

### `tests/unit/test_stdio_consolidation.py` — Clean
Genuine AST-based static-analysis test scanning every real file in
`.agent/scripts/` for forbidden stdio-wrapping patterns (real cross-file
enforcement, not a synthetic fixture), plus a real subprocess execution test that
actually simulates a non-UTF-8 Windows console encoding (`cp1252`) and confirms
`session_health.py` doesn't crash under it. No gaming.

### `tests/unit/test_upgrade_units.py` — Mostly clean, one new finding
Solid real coverage overall: filename-parsing regex, correct multi-step and
fork-resolution chain-building logic (real greedy-selection semantics verified), a
real CRLF-normalization test comparing actual SHA-256 hashes on temp files, and a
genuine `Protocol`/`runtime_checkable` test correctly distinguishing a malformed
migration (missing `downgrade`) from a valid one.

**Finding, RESOLVED 2026-08-04**: `test_yaml_rename_skips_comment_line` (and its two sibling tests `test_yaml_rename_preserves_trailing_comment` and `test_yaml_rename_skips_mid_value_occurrence`) originally had incomplete assertions or used parallel regex copies instead of exercising the real migrator. **Fixed and independently verified**: all three tests now pass real v1.1.0 `config.yaml` temp files into `MigrationV1_1_0_to_V1_1_5().migrate()` and perform concrete before/after assertions on the resulting file content. Unused setup code in `test_chain_resolves_single_step` cleaned up.

### `tests/e2e/run_e2e_verification.py` — Clean, the strongest single test artifact in the audit
29 real end-to-end scenarios, almost nothing mocked except the external LLM
provider (and even that's done by writing a real Python file consumed by the
actual subprocess, not `unittest.mock` — the rest is genuine subprocess execution
against a freshly-scaffolded, real git repository each time). Standouts:
Scenario 10 writes an actual crashing migration module to disk and confirms real
atomic rollback; Scenario 19 uses a genuinely closed port (`54321`) to simulate an
unreachable service rather than mocking the network call; Scenario 22 writes a
real over-budget `session.json`, runs the real `ai_review.py`, and confirms an
actual `HALT` file is written and cleared on reset; Scenario 24 correctly
distinguishes fail-open (low-risk, API down) from fail-closed (high-risk, API down)
using real git-staged files with real line counts to trigger the real threshold
logic; Scenario 29 runs a fully independent temp git repo through the real
spec→scaffold→traceability→acceptance pipeline end to end. `has_v110_tag()`
correctly fails loud with a clear message if a required git tag is missing, rather
than skipping silently — the same discipline valued elsewhere in this audit. No
gaming anywhere in this file.

`tests/e2e/test_project/` was confirmed to be live, run-regenerated
working-directory state matching `setup_fresh_v110_project()`'s output exactly —
not a separate static fixture with its own content requiring audit.

---

## Not Yet Checked

**Nothing remains within this audit's scope.** All 31 top-level `tests/` files, all
27 `tests/unit/` files, and `tests/e2e/run_e2e_verification.py` are checked — 59
test files total. `tests/e2e/test_project/` is confirmed to be live,
run-regenerated working-directory state (matches `setup_fresh_v110_project()`'s
output exactly), not a static fixture with its own content to audit.

**`tests/data/`** remains deliberately out of scope: fixture data only
(`false_positive_cases.csv`, `fp_cases/`), not test files. `false_positive_cases.csv`
may be worth a glance later for its own data-quality reasons, unrelated to this
audit's gaming/coverage-gap purpose.

---

## Recommendation once this audit is more complete

Each finding above should eventually become either (a) a backlog item (coverage
gaps — low priority, normal triage), or (b) folded into
`SPEC-loop-closure-verification.md` as additional acceptance scenarios where it's
the same producer/consumer pair already being fixed there (as with the two
masking-resistant blind spots, which directly support Scenarios 4p and its
`wiki_compile.py`/`co_change_reconciler.py` analogues). The
`test_token_write_fails_gracefully` case (originally slated for path (c), a
standalone fix) is **RESOLVED 2026-08-04**: traced real stderr warning behavior in
`src/scripts/ai_review.py` (`"Failed to lock session file for update: {e}"`) and
completed the `mock_stderr_write` assertion — see "Findings by file" above.

**One finding from `tests/unit/` follows the same triage model, resolved
differently from the other**: `test_context_loader.py`'s finding will resolve
naturally once LOOP-014's `architecture_checks.DOMAIN_REGISTRY` gap is fixed
(path (b) — no standalone test fix needed, since the test itself is correctly
designed; only the production dependency is broken). `test_upgrade_units.py`'s
three affected tests are already **RESOLVED 2026-08-04** — path (c), a standalone
fix, independently verified against the real migrator (see "Findings by file"
above).

**Priority action — RESOLVED (2026-08-04)**: Fixed by Gemini per the dispatched brief,
independently verified against the actual code. `tests/test_phase3_enforcement.py`'s
Finding B (`test_missing_session_json_budget_assumes_zero_spent`) was the most
serious finding of this entire audit — a test-authored escape hatch that could
silently swallow a genuine regression in the exact behavior it claimed to protect.

**Root cause, confirmed independently**: the old test mocked `get_changed_files` to
return `[]`, which triggers `_run_review()`'s `if not changed_files: return 0`
check — an *earlier* early-return than the session/budget logic the test claimed to
exercise. The old test never actually reached the code path it was named for; the
`except Exception: pass` blocks were catching nothing because nothing ever got far
enough to raise.

**Fix, confirmed independently against the live source**: the test now mocks a real
file change and exercises three genuinely distinct behavioral paths in `ai_review.py`:
1. Non-CI + budget configured + missing `session.json` → fail-closed, `SystemExit(1)`,
   exact banner text `"!!! EXECUTION BLOCKED: MISSING SESSION STATE !!!"` verified
   present in captured output.
2. CI + budget configured + missing `session.json` → budget enforcement skipped,
   `spent` assumed 0, review proceeds; exact skip message verified in output.
3. No budget configured + missing `session.json` → no enforcement block reached at
   all; verified the missing-session banner does NOT appear.

The bare `except Exception: pass` is completely removed — confirmed by reading the
full test function on disk. Test count (16 in the file) verified by direct count,
matching Gemini's report exactly. Sanity-check methodology (temporarily reverting
`sys.exit(1)`→`pass` in `ai_review.py`, confirming the test then fails with
`DID NOT RAISE SystemExit`, then reverting) is consistent with the code structure,
though not re-executed independently in this pass (no shell/pytest execution
available via the tools used for this audit). This is the cleanest, most rigorous
piece of delegated work of the whole session — genuine root-cause tracing from the
source rather than guessing from the test alone, exactly as the brief required.

Finding A (the tautological `test_count_diff_lines_exactly_at_threshold_uses_standard_strategy`
in the same file) is also resolved — see "Findings by file" above for detail. All
tautological findings from this audit (`test_validate.py`'s two, plus this one) are
now closed out.

*Last updated: 2026-08-04. Milestone: the entire audit is complete — all 59 test
files across `tests/` top-level (31), `tests/unit/` (27), and `tests/e2e/` (1) have
been checked. Eight findings resolved and independently verified (Finding B,
Finding A, the `test_ai_review.py` incomplete assertion, both `test_validate.py`
tautologies, `test_framework_consistency.py`'s soft `ImportError`-swallowing
pattern, and the three `test_upgrade_units.py` tests). Two coverage-gap findings
(#1/#5 dream-proposal schema, #2 subprocess masking) remain open, with fixes
already bundled into `SPEC-loop-closure-verification.md` v1.4/v1.6/v1.7 pending
Peter's sign-off. One finding (`test_context_loader.py`) remains open by design —
it will resolve naturally once LOOP-014's production fix ships, not via a test
change. No H-03 gaming signature found in any of the 59 files. If resuming from a
new session: this audit's scope is complete; any further work is either (a) the
pending spec sign-off, or (b) a fresh audit scope Peter defines.*
