# Test-Suite Integrity Audit — Working Findings

**Status**: IN PROGRESS — not a SPEC, no APPROVED/DRAFT lifecycle applies. This is a
working findings log so investigation can resume without reconstruction if this
session is interrupted.
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
Results recorded separately in `docs/planning/specs/SUBPROCESS-IMPORT-SWEEP.md` — check
that file before re-deriving anything about this bug pattern from scratch here.

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
checked so far, though one finding (`test_phase3_enforcement.py`, below) sits right
at the boundary of that category — see Progress Summary.

---

## Progress Summary (update this each session)

**Files fully read**: 17 of ~31 top-level files in `tests/` (roughly 55%).
`tests/unit/`, `tests/e2e/`, `tests/data/` not yet touched at all.

**Overall verdict so far**: this is a fundamentally honest test suite, with one
notable exception found this pass. No true H-03 gaming signature (deliberately
weakened assertion) found anywhere. Several files are genuinely exemplary
(`test_check_spec.py`'s fail-open/fail-closed partitioning, `test_co_change_core.py`'s
exact-probability characterization testing, `test_install.py`'s F-COLD-1 halt
verification via mock assertion, `test_framework_consistency.py`'s working
documentation-consistency gate, `test_harness_config.py`'s boundary-matching edge
cases).

**Seven concrete findings, six non-malicious, one borderline**:
1. `test_distill_dream.py` — coverage gap (never checks for the `Generated:` field)
2. `test_wiki_compile.py` / `test_co_change_reconciler.py` — masking-resistant blind
   spot (subprocess bug structurally invisible to black-box testing)
3. `test_ai_review.py` — one incomplete assertion, author's own doubt left as
   dangling comments instead of a finished check
4. `test_validate.py` — two tautological tests asserting a value they just hand-set
5. `test_harness_health.py` — **completes finding #1**: the consumer-side tests
   also hand-craft the field the producer never writes, confirming the
   producer/consumer contract was never tested from either side
6. `test_framework_consistency.py` — minor: two tests silently skip (no assertion)
   on `ImportError`, a soft masking-resistant variant
7. `test_phase3_enforcement.py` — **the most serious finding of the audit**: one
   tautological test (same shape as #4), and one test
   (`test_missing_session_json_budget_assumes_zero_spent`) whose own `except
   Exception: pass` blocks would silently swallow a genuine regression in exactly
   the behavior it claims to verify. This is the closest instance found to true
   H-03 territory — not a weakened assertion, but a structurally permissive test
   that was, as far as can be told from static reading, authored this way rather
   than weakened from a stricter prior version.

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

**One incomplete-assertion finding** — `test_token_write_fails_gracefully`:
docstring promises *"the gate logs a warning but continues,"* the test sets up
`patch("sys.stderr.write") as mock_stderr_write` clearly intending to verify that,
but only asserts `exit_code == 0`. Where the stderr assertion should be, the test
instead contains the author's own unresolved reasoning, left in as comments:
```python
# Stderr should receive a warning warning of the lock failure
# Wait, in the code:
# except Exception: pass
# We want to print a WARNING to stderr on Lock Failure!
# Let's verify if our code prints a WARNING to stderr on Exception in the update block.
```
Not a weakened assertion (nothing was removed) — an assertion that was never
finished, with the gap in reasoning preserved in place rather than resolved. This is
the first finding all session that isn't clearly benign, and the closest in shape to
what H-03 actually warns about.

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

**Finding**: `TestOverallResult.test_warnings_only_passes` and `test_errors_fail`
are tautological. The first sets `v.warnings = 3; v.errors = 0` and then asserts
`v.errors == 0` — a value the test itself just assigned two lines earlier — despite
a comment reading `# Validator run() returns exit code` immediately above, `run()`
is never called and no actual exit code is ever checked. `test_errors_fail` does the
mirror version. Both pass unconditionally regardless of whether the Validator's real
exit-code logic works. New taxonomy category — see above.

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

### `tests/test_framework_consistency.py` (10.40 KB) — Clean, and itself a positive counter-example
T1-K-09's consistency gate genuinely works: verifies every workflow slug in
`AGENTS.md` §2 resolves to a real file in `.agent/workflows/`, includes explicit
regression guards for two previously-dead slugs (`/perf`, `/qa`), and checks
section-label consistency (H/S/C/G vs. legacy P-series). This is the same *category*
of documentation/code consistency check `wiki_lint.py`'s orphaned-rules-check was
supposed to provide (LOOP-013) — and this one actually works. Worth citing alongside
`test_check_spec.py` and `test_co_change_core.py` as a model example.

**Minor soft spot, not a full finding**: `test_no_explicit_default_for_known_config_keys`
and `test_harness_config_distinguishes_none_from_missing` both silently `return`
(no assertion, no failure) on `ImportError` from `harness_utils` — a deliberate
"skip if not ready" pattern, reasonable for install-time tolerance. But it means any
unrelated breakage in `harness_utils.py`'s import chain would make these tests
silently pass forever without ever actually checking anything, with no signal that
this is happening. Same shape as the masking-resistant blind-spot category, via
`ImportError` rather than a swallowed runtime exception.

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

### `tests/test_phase3_enforcement.py` (9.39 KB) — Two findings, one is the most serious of the session
Most of the file is solid: task-magnitude classification (hotfix/rfc/docs branch
heuristics), HALT escape-hatch behavior with and without a bypass reason, and a
concrete reasoning-token budget-summation check (350 = 100+50+200, hand-verified).
No gaming in those.

**Finding A — tautological test**: `test_count_diff_lines_exactly_at_threshold_uses_standard_strategy`
claims to test boundary behavior "at exactly threshold lines," but its entire
assertion is `assert threshold == 400 or isinstance(threshold, int)` — trivially
true regardless of the actual value, since `threshold` is always an `int` by
construction. Verifies nothing about the claimed behavior. Same category as the
`test_validate.py` finding.

**Finding B — the most concerning pattern found this session**:
`test_missing_session_json_budget_assumes_zero_spent` wraps `_run_review()` in three
separate try/except blocks, each shaped like:
```python
try:
    _run_review()
except SystemExit as exc:
    assert exc.code != 1 or "budget" not in str(exc).lower()
except Exception:
    pass
```
If `_run_review()` raises **any** exception other than `SystemExit` — a broken
mock, a genuine regression, anything — it is silently swallowed and the test
passes. This is not application code masking a bug via a bare `except`; it is the
**test itself** authored with an escape hatch that hides failure. Even where
`SystemExit` is caught, the assertion is weak (`exc.code != 1 or "budget" not in
...`) — an unrelated exit code 1 whose message doesn't happen to mention "budget"
still passes. This is the closest instance found all session to genuine H-03
territory — not a weakened assertion, but a test structurally built so that an
unexpected failure in exactly the scenario it claims to protect (a broken
session-budget fallback) would never be caught.

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

---

## Not Yet Checked

Remaining files in `tests/`, in descending size order (resume here):
`test_session_health.py` (6.21 KB),
`test_rebuttal.py` (5.61 KB), `test_migration_v1_3_0_to_v1_3_3.py` (5.39 KB),
`test_downgrade.py` (4.75 KB), `test_pm_scaffold.py` (4.59 KB),
`test_check_state_freshness.py` (3.07 KB), `test_prompt.py` (3.01 KB),
`test_common.py` (1.67 KB), `test_migration_v1_2_0_1_to_v1_3_0.py` (1.63 KB).

Also not yet touched: `tests/unit/`, `tests/e2e/`, `tests/data/` subdirectories —
not even listed yet.

---

## Recommendation once this audit is more complete

Each finding above should eventually become either (a) a backlog item (coverage
gaps — low priority, normal triage), (b) folded into `SPEC-loop-closure-verification.md`
as additional acceptance scenarios where it's the same producer/consumer pair already
being fixed there (as with the two masking-resistant blind spots, which directly
support Scenarios 4p and its `wiki_compile.py`/`co_change_reconciler.py` analogues),
or (c) — for the `test_token_write_fails_gracefully` case specifically — a small,
standalone fix: complete the missing assertion, since the underlying behavior it's
supposed to verify (a warning printed on lock timeout) may or may not actually exist
in `ai_review.py` and hasn't been confirmed either way yet.

**Priority action, not yet covered above**: `tests/test_phase3_enforcement.py`'s
Finding B (`test_missing_session_json_budget_assumes_zero_spent`) is the most
serious finding of this entire audit and currently has no corresponding action item.
Unlike every other finding here, this one is a **test-authored escape hatch**, not a
producer/consumer gap or a masked application-code exception — the test itself
swallows any exception other than `SystemExit` via a bare `except: pass`, meaning a
genuine regression in the exact behavior it claims to protect (session-budget
fallback when `session.json` is absent) would pass silently. This needs a decision
from Peter directly, not a default triage path: (1) whether this reflects an
intentional, if loosely-worded, design choice that should just be commented
explicitly, or (2) whether it should be tightened to fail on any unexpected
exception — and either way, this is close enough to true H-03 territory that it
probably shouldn't be batched anonymously into a general backlog cleanup. The
tautological test in the same file (Finding A) can follow the same low-priority path
as the `test_validate.py` tautology above.

*Last updated: 2026-08-02, mid-session. If resuming from a new session, read this
file first, then continue from the "Not Yet Checked" list above.*
