# SPEC: Loop Closure Verification (T1-K-19)

**Status**: DRAFT
**Author**: Claude (drafting)
**Tracked under**: T1-K-19
**Target Release**: v1.4.15
**Related**: T1-K-09 (consistency gate — "gates actually gate," binary precedent this generalizes), HIB-080 (direct evidence case), HIB-081 (supporting evidence case, do not develop independently), SPEC-enforcement-postures.md (the spec whose cross-gate claim HIB-080 silently violated), T1-L-18 (Gherkin scenario coverage for outer-loop docs — a sibling concern at the spec-completeness layer rather than the test-coverage layer)
**Changelog**:
- v1.0 (2026-07-25, Claude): Initial draft, motivated by two incidents in one session (HIB-080; a pre-merge schema-exemption regression) that a fully green 550/550 test suite did not catch.
- v1.1 (2026-07-26, Claude): Retagged Target Release from v1.4.14 to v1.4.15 — resequenced behind SPEC-v1.4.14-punchcard-preparation.md at Peter's direction. The two releases are independent; this spec's HIB-080 precondition is satisfied by v1.4.13 regardless of ship order. See decisions_log.md for the resequencing rationale.
- v1.2 (2026-08-02, Gemini): Reopened for adversarial review — addresses four gaps found in post-approval review: Scenario 2 mechanism gap, Phase B vacuous-argument gap, Phase A calibration gap, wiring_consumers.yaml validation gap. See decisions_log.md.
- v1.3 (2026-08-02, Gemini): Extends Phase B with decisions_log.md as a fourth named shared artifact — impact-weighted retention replacing pure-FIFO archival. Adds the impact-classification rubric as a required schema element, not separate guidance. See decisions_log.md.
- v1.4 (2026-08-02, Gemini): Fixes a live schema mismatch found during the loop-inventory audit — distill_dream.py's proposal-card template never wrote the Generated: field harness_health.py's staleness parser requires, silently hiding every proposal from staleness detection since the mechanism's inception. Backfills the one existing stale proposal. See decisions_log.md.
- v1.5 (2026-08-02, Gemini): Fixes a second live discrepancy found during the loop-inventory audit — .agent/workflows/eval-pipeline.md documents that an empty golden dataset must escalate to a human ("gate is hollow"), but regression_runner.py's actual code exits 0 (success) on empty. Reconciles code to match the documented escalation trigger. See decisions_log.md.
- v1.6 (2026-08-02, Gemini): Fixes a third live discrepancy found during the loop-inventory audit — wiki_lint.py's orphaned-rules and staleness checks have been silently no-op since a file/directory refactor left two hardcoded paths (review_context.md, .agent/skills/senior-architect/...) pointing at locations that no longer exist. Also fixes an unimported subprocess reference masked by a bare except. Establishes a post-fix baseline run. See decisions_log.md.
- v1.7 (2026-08-02, Gemini): Revises v1.6's wiki_lint.py fix after cross-checking against Gym_App (an installed project under the harness). Replaces hardcoded CONTEXT_FILE/ARCH_CHECKS_FILE paths with dynamic resolution mirroring context_loader.py's own logic, so the fix generalizes to any installed project rather than encoding this repo's specific file layout. Adds a new check for legacy review-context files that exist but aren't actually loaded — the exact failure mode found live in Gym_App, where review_context.md still claims canonical status but has been silently superseded since 2026-07-01, hiding two entire rule blocks (BUSINESS-RULES, FINANCIAL-PRECISION) from every prior audit. See decisions_log.md.

---

## 0. Motivation Gate (context, not blocking)

The framework's test suite is comprehensive by conventional measures (550/550 passing, unit coverage across gates, migrations, and bootstrap). It is not, by design, answering the question that actually matters for a governance harness: *does the outcome a spec promises actually hold when components are exercised together, through their real call sites, with real state?*

Two incidents in a single session demonstrated the gap concretely:

1. **HIB-080**: `SPEC-enforcement-postures.md` claims `ratchet` posture's baseline-grandfathering applies across both `ai_review.py` and `architecture_checks.py`. `ai_review.py`'s call site is correct and tested. `architecture_checks.py`'s call site silently omits the required parameters, defeating grandfathering for that gate entirely — the exact gate the spec's own motivation section names as the reason `ratchet` exists. Full suite green throughout.
2. **A schema-hardening exemption regression** (caught by manual review before merge, not by the suite): a refactor intended to genericize framework source deleted GymBase's operational exemption data. 550/550 tests passed, because no test asserted the specific data survived — only that the code still ran.

Both are the same failure shape: a cross-component or cross-refactor *claim* is made, and the suite verifies the claim's individual mechanical parts without ever verifying the claim itself. Most of the suite mocks at component boundaries — correct for isolating unit behavior, but it structurally guarantees the suite cannot notice a caller failing to actually reach across a boundary it claims to use.

---

## 1. Problem

Three distinct verification gaps, previously uncovered by any single mechanism:

1. **Spec-to-test traceability is one-directional and incomplete.** `check_spec.py` enforces that specs contain Gherkin acceptance criteria before APPROVED status. Nothing enforces the inverse: that a test exists asserting each scenario's specific `Then` outcome against the actual component named in the `Given`/`When`, rather than merely touching the same file.
2. **Multi-consumer artifacts have no wiring audit.** Shared state — `GateContext`, `.agent/baseline.json`, `session.json` fields, `capability_calibration.json` — is documented as consumed by multiple named components. Nothing statically confirms every claimed consumer actually references the fields/functions in question. `T1-K-09` catches "does this gate block on a seeded violation" (binary); it does not catch "does this specific consumer actually read this specific shared field."
3. **Refactors claiming behavior-preservation have no outcome-equivalence check.** A change that says "this preserves existing behavior for project X" is verified only by "the code still executes without error" — never by "the specific data/config X depends on is unchanged," which is the actual claim being made.

---

## 2. Bounded Scope & Out of Scope

### In-Scope (Goals)
- **Phase A — Spec-scenario cross-reference.** A script that parses every APPROVED spec under `docs/planning/specs/` (including `archive/`) for `### Scenario:` blocks, extracts the named component(s) and claimed outcome from each `Given`/`When`/`Then`, and cross-references against the test suite for an assertion that (a) exercises that named component's real entry point (not a mock of it) and (b) asserts the specific `Then` outcome. Scenarios with no matching test are flagged, not auto-failed — this is a coverage report, not a new blocking gate, at least initially (see §7).
- **Phase B — Static wiring audit.** For each shared artifact with more than one documented consumer (starting with `GateContext`, `.agent/baseline.json`, `session.json`, `capability_calibration.json`), an AST-based script confirming each claimed consumer's source actually references the specific fields/functions the producing spec attributes to it and that the reference is not a vacuous/default pass-through (e.g. `baseline=None` literal) — a present-but-empty argument must still be flagged. Mirrors exactly the manual check that found HIB-080 (confirming `architecture_checks.py`'s `disposition()` call includes `baseline=`), generalized and automated. A fourth artifact, `decisions_log.md`, extends this audit differently: its "documented consumers" are every agent session at mandatory startup (AGENTS.md §1), and the claim under audit is retention integrity — that the archival sweep does not silently evict a decision classified as load-bearing before a future session can read it. This is a structural produce/consume claim in the same spirit as the other three artifacts, verified mechanically rather than by judging whether any given session actually acted on a retained entry — that latter question is not statically verifiable and is explicitly out of scope (see §2 Out-of-Scope addition below). A fifth case surfaced during the loop-inventory audit, distinct in shape from the first four: `dream_proposals/*__open.md`'s implicit schema contract between `distill_dream.py` (producer) and `harness_health.py`'s staleness parser (consumer). The producer's card template never wrote the `Generated: YYYY-MM-DD` field the consumer's regex requires — every proposal ever generated has silently evaded staleness detection. This is fixed directly here as a diagnosed bug, not built out as new general tooling — Phase B's AST-based wiring audit checks whether consumer code references a producer's claimed fields; this bug is the inverse shape (a producer's serialized text output failing to satisfy a consumer's parser), which Phase B as scoped does not generically cover. See §7 for the resulting scope note. A sixth case, also surfaced during the loop-inventory audit, is narrower in shape than the first five — not a producer/consumer wiring gap but a direct contradiction between a documented escalation trigger and its implementing code. `.agent/workflows/eval-pipeline.md`'s Escalation Triggers section states an empty golden dataset must escalate to a human ("gate is hollow"); `regression_runner.py`'s `main()` instead prints a warning and calls `sys.exit(0)` — a success code — on the same condition. Fixed directly here, same treatment as the fifth case: a diagnosed bug, not new general tooling. Whether other documented escalation triggers across `.agent/workflows/*.md` have similarly drifted from their implementing code is explicitly not audited by this fix — see §7/§8. A seventh case, surfaced during the loop-inventory audit, is the most consequential found so far: `wiki_lint.py`'s `run_orphaned_rules_check()` and `run_staleness_check()` both depend on `CONTEXT_FILE` (hardcoded to `src/scripts/review_context.md`, which does not exist — the file was split into `review_context_universal.md` and `review_context_project.md` at some point after this script was written) and, for the orphaned-rules check specifically, `ARCH_CHECKS_FILE` (hardcoded to `.agent/skills/senior-architect/scripts/architecture_checks.py`, which does not exist — the real file lives under `.agent/skills/universal/senior-architect/scripts/`). Revision (v1.7): the v1.6 fix as originally scoped corrected this repo's specific stale paths, but cross-checking against Gym_App (an installed project under this harness) surfaced that a hardcoded path — of any kind — is the wrong fix shape, because it re-creates the identical failure class the moment a project's layout differs, which Gym_App already does on two counts: it still uses the flat `.agent/skills/senior-architect/scripts/` layout (not this repo's `universal/`-nested one), and it retains a legacy `review_context.md` that its own `context_loader.py` no longer loads — confirmed by reading `context_loader.py` directly, which resolves only `review_context_universal.md` and `review_context_project.md`, treating the universal file's absence as install-corruption-fatal. That legacy file's banner still falsely claims "single source of truth... injected verbatim on every commit," and two entire rule blocks added to the real live file since 2026-07-01 (`[RULE:BUSINESS-RULES]`, `[RULE:FINANCIAL-PRECISION]` — eleven and three invariants respectively, several HIGH severity) have never been checked for orphaned-enforcement status as a result. The corrected fix must therefore not hardcode any path; it must ask the project's own `context_loader.py` and `harness_utils.py` what they actually resolve, so the audit tracks the real loader instead of encoding a second, driftable opinion of it. A second, smaller bug in the same file — a `_find_project_root()` calling `subprocess.run()` without importing `subprocess`, masked by a bare `except` — is fixed as part of the same touch, since it's in the same function being corrected. An identical bug in a different file (`co_change_reconciler.py`) is explicitly NOT fixed here — see §8.
- **Phase C — E2E scenario classification and outcome-equivalence tests.** Audit `tests/e2e/run_e2e_verification.py`'s existing 29 scenarios, tagging each as single-gate or genuinely cross-gate. Add outcome-equivalence tests at cross-gate seams currently covered only by single-gate scenarios. Add a general outcome-equivalence test pattern (load a real project fixture's operational config/data, run the check, assert zero-diff vs. a pinned baseline) for any future refactor claiming behavior-preservation.

### Out-of-Scope (Non-Goals)
- Making Phase A or B a **blocking** pre-commit or pre-merge gate in this spec. Both ship as reporting/advisory tools first (see §7 Known Residual Risks) — converting either to blocking is a follow-up decision after they've run against the existing spec/test corpus and produced a manageable, accurate signal.
- Retroactively writing missing tests for every gap Phase A/B surfaces. This spec delivers the *detection* mechanism; the resulting backlog of specific gaps is triaged and closed as separate, normal work — the equivalent of `harness_health.py` surfacing a signal rather than this spec being scoped to close every instance of it.
- General mutation testing or property-based testing infrastructure — a different (and reasonable) approach to the same underlying "test suite gives false confidence" problem, but distinct tooling and out of scope here.
- Replacing boundary-mocked unit tests generally. Mocking remains correct for the majority of the suite; this spec targets specifically the seams between components with documented multi-party contracts.
- Verifying that a retained decision was actually read and acted on by a subsequent agent session — this is a behavioral/eval question, not a mechanical audit, and is explicitly not claimed by this spec.

---

## 3. Assumptions

- `[Resolved: APPROVED specs under docs/planning/specs/ (including archive/) are the authoritative source of cross-component outcome claims for Phase A. Specs without Gherkin Scenario blocks predate T1-L-01's formalization and are out of scope for retroactive scenario extraction — Phase A operates only on specs already in the required format. The parser must handle multi-clause scenarios (And continuations, multiple Then clauses per scenario) — verify against this spec's own Scenarios 3–6 as a self-test fixture before running against the full corpus.]`
- `[Resolved: Phase B's "documented consumer" list is seeded manually from each artifact's producing spec (e.g. SPEC-enforcement-postures.md §5.3 names both ai_review.py and architecture_checks.py as GateContext/posture consumers) rather than auto-discovered — auto-discovery of "who should consume this" is not a well-posed static analysis problem; auto-discovery of "does a named consumer actually reference it" is.]`
- `[Resolved: Decision log-worthiness is classified at write time via a required impact parameter to record_decision(), one of {high, medium, low}, with no auto-classification from prose attempted — mirroring Phase B's existing manually-seeded consumer-list philosophy (auto-discovery of "how important is this" is no better posed than auto-discovery of "who should consume this"). Rubric: HIGH — establishes/changes an architectural invariant or pattern; sets precedent from an incident generalizing beyond the single case; changes release/spec sequencing or scope; resolves a previously contested tradeoff with lasting effect; supersedes a prior log entry. MEDIUM — routine architectural/business decisions with limited future constraint (the default classification for decisions not meeting the HIGH bar). LOW — narrow, session-local decisions recorded for audit-trail completeness only.]`
- `[Resolved: making impact a required parameter applies only to record_decision() calls made after this spec ships. Existing entries in decisions_log.md predating this change lack the field and are treated as medium by archive_old_decisions() for eviction purposes — no retroactive backfill/reclassification of historical entries is required as a precondition.]`
- `[Resolved: Phase C's outcome-equivalence pattern requires a real project fixture (a minimal but representative schema/config, not GymBase's live data) checked into tests/data/ or equivalent, so the test is hermetic and does not depend on GymBase's actual repository state.]`
- `[Pending: whether Phase A/B reports integrate into harness_health.py's existing output (as a new section, consistent with how schema-hardening trend and dream-proposal staleness already surface) or ship as standalone CLI scripts initially, promoted to harness_health.py once stable. Recommend standalone-first, matching the precedent set by T1-K-09's tests/test_framework_consistency.py, which the T1-K-19 audit tooling closely resembles in spirit.]`

---

## 4. Acceptance Criteria

### Scenario 1: Spec-scenario cross-reference detects an unimplemented outcome assertion (Phase A)
Given an APPROVED spec containing a Gherkin scenario naming a specific component and a specific disposition outcome
When the cross-reference script runs against the current test suite
Then a scenario whose `Then` outcome is not asserted anywhere against that component's real entry point is reported as `UNVERIFIED`, distinct from scenarios with a matching test.

### Scenario 1b: Cross-reference heuristic is calibrated before its report is trusted
Given Phase A's first run against the full existing spec/test corpus
When the resulting UNVERIFIED/VERIFIED report is produced
Then at least 10 flagged results (a mix of UNVERIFIED and VERIFIED) are manually spot-checked against human judgment, and the false-positive/false-negative rate is recorded in the report's own output before Phase A's findings are treated as directional signal rather than noise.

### Scenario 2: Cross-reference does not false-positive on genuinely covered scenarios
Given a scenario whose `Then` outcome is asserted in a test that exercises the real component (not a mock of it)
When the cross-reference script runs
Then that scenario is reported as `VERIFIED`, and the report distinguishes "verified against real entry point" from "verified against a mock of the entry point" as two different confidence levels.

### Scenario 3: Wiring audit reproduces the HIB-080 finding retroactively
Given `SPEC-enforcement-postures.md`'s documented consumer list for the baseline/posture disposition mechanism (`ai_review.py`, `architecture_checks.py`)
When the Phase B wiring-audit script runs against the pre-HIB-080-fix state of the codebase
Then it reports `architecture_checks.py` as a claimed consumer that does not reference `baseline=`/`touched_files=` in its `disposition()` call, without requiring a human to have manually diffed the two call sites.

### Scenario 4: Wiring audit passes cleanly post-HIB-080-fix
Given the same consumer list, evaluated after HIB-080's fix lands
When the Phase B script runs
Then both consumers are reported as correctly wired, with no false positives introduced by the audit's own AST parsing (e.g. correctly handling keyword-vs-positional argument passing, `**kwargs` forwarding).

### Scenario 4b: Wiring audit flags a vacuous argument as a partial-wiring defect
Given a consumer's call site references `baseline=` but passes a hardcoded `None` or literal default rather than a value sourced from the actual baseline data
When the Phase B script runs
Then it reports this consumer as `PARTIALLY-WIRED` (a third status distinct from `WIRED`/`NOT-WIRED`), flagging that presence-of-reference alone was insufficient.

### Scenario 4c: Malformed or empty consumer manifest fails loud, not silent
Given `wiring_consumers.yaml` is missing, empty, or has a malformed entry for an artifact
When the Phase B script runs
Then it exits with a clear validation error rather than silently treating the artifact as having zero consumers to check — a silent-pass here would recreate this spec's own motivating failure mode in miniature.

### Scenario 4d: record_decision() rejects an unclassified impact value
Given a call to `record_decision()` with `impact` missing, empty, or not one of `{high, medium, low}`
When the function executes
Then it raises `ValueError` before writing any content to `decisions_log.md`, applying the same fail-loud validation already used for title/decision/context/consequence.

### Scenario 4e: archive_old_decisions() retains high-impact entries across the line-count threshold
Given `decisions_log.md` exceeds 150 lines and contains a mix of high/medium/low-impact entries, including a high-impact entry older than several medium/low entries
When the archival sweep runs
Then the high-impact entry remains in `decisions_log.md` regardless of age, and eviction proceeds only among medium/low entries.

### Scenario 4f: Eviction priority correctly orders mixed medium/low entries by age-weighted score, not recency alone
Given multiple medium and low-impact entries of varying ages, including at least one pair where naive oldest-first ordering would evict a medium entry before an older low entry
When eviction priority is computed as `age_in_days / impact_weight` (low=1, medium=2) for each candidate
Then entries are evicted in descending priority order (oldest, lowest-impact first), verified against that hand-computed pair.

### Scenario 4g: A log exceeding threshold entirely from high-impact entries fails loud rather than silently evicting a pinned entry
Given `decisions_log.md` exceeds 150 lines and every entry present is tagged high
When the archival sweep runs
Then it archives zero entries and reports that the threshold is exceeded with no eligible non-high entries to evict, rather than silently archiving a pinned entry to force compliance.

### Scenario 4h: Reproducing the staleness blind spot before the fix
Given the current, unfixed `distill_dream.py` template and the existing open proposal card (`verification-before-completion__state_anomaly__open.md`)
When `report_dream_proposal_staleness()` runs against it
Then the proposal is silently skipped by the regex match failure — reproducing the diagnosed bug exactly, as a pre-fix baseline.

### Scenario 4i: Fix — proposal template emits a Generated field the existing parser can consume
Given the fixed `distill_dream.py` template
When a new proposal card is written, or an existing one is updated via the de-duplication/merge path
Then it includes a `Generated: YYYY-MM-DD` line whose date is derived from the earliest evidence timestamp in the occurrence list, not the file's disk mtime — mtime is unsuitable because the merge path rewrites the file without changing when the underlying pattern was first detected, which would silently reset the staleness clock on every merge.

### Scenario 4j: Backfill closes the loop for the existing proposal, not just future ones
Given the one currently-open proposal, predating this fix, whose earliest evidence entry is dated `2026-06-13`
When the one-time backfill runs
Then the proposal is updated with `Generated: 2026-06-13`, and `report_dream_proposal_staleness()` immediately reports it as `WARN` (46 days old, past the 30-day threshold) — demonstrating the fix closes the loop for existing state, not merely prevents new instances of the bug.

### Scenario 4k: Reproducing the hollow-gate discrepancy before the fix
Given `golden_dataset.yaml` contains zero entries
When `regression_runner.py` is run with `--verify-only` or `--run`
Then the current, unfixed code exits with code 0, contradicting `eval-pipeline.md`'s documented requirement to escalate — reproducing the discrepancy exactly, as a pre-fix baseline.

### Scenario 4l: Fix — empty dataset exits non-zero and states the escalation reason
Given `golden_dataset.yaml` contains zero entries
When the fixed `regression_runner.py` runs
Then it prints a message stating the gate is hollow and requires human escalation, and exits with a non-zero code — matching `eval-pipeline.md`'s documented trigger and making the condition CI-visible rather than silently green.

### Scenario 4m: Fix does not break the legitimate "no regressions yet" case
Given a freshly-scaffolded project where no incidents have occurred yet and `golden_dataset.yaml` has deliberately never been created
When `regression_runner.py` runs during initial onboarding
Then the exit-non-zero behavior from Scenario 4l is confirmed to be the intended signal even in this legitimate case — an empty dataset is always worth a human's attention (either "nothing has gone wrong yet" or "someone forgot to wire this up"), not a special-cased exception. This must be explicitly confirmed against onboarding workflows so the fix doesn't get treated as a false-positive nuisance and quietly reverted later.

### Scenario 4n: Reproducing the stale-path blind spot before the fix
Given the current, unfixed `wiki_lint.py` and the real `review_context_universal.md`/`review_context_project.md` files (which contain `[RULE:...]`/`[PATTERN:...]` annotations)
When `run_orphaned_rules_check()` and `run_staleness_check()` run
Then both return empty results because `CONTEXT_FILE.exists()` is False — reproducing the diagnosed blind spot exactly, as a pre-fix baseline, distinct from "no orphaned rules exist" which would be a legitimate empty result.

### Scenario 4o (revised): Fix resolves context files by asking the real loader, not a hardcoded guess
Given a target project has `context_loader.py` present (as this repo and Gym_App both do)
When the fixed `wiki_lint.py` determines which review-context files are live
Then it imports and calls `context_loader.py`'s own file-resolution logic (`UNIVERSAL_CONTEXT_FILE`, `PROJECT_CONTEXT_FILE` module-level paths, or equivalent) rather than hardcoding `review_context.md` or any specific filename — so a future rename or restructure of the live context files is automatically reflected without requiring a matching change in `wiki_lint.py`.

### Scenario 4o-b: Fix resolves architecture_checks.py by reusing the harness's own dual-path resolution
Given `harness_utils.py`'s `_setup_sys_path()` already checks both `.agent/skills/universal/senior-architect/scripts` and `.agent/skills/senior-architect/scripts` (nested vs. flat layouts)
When the fixed `wiki_lint.py` resolves `ARCH_CHECKS_FILE`
Then it reuses this same dual-path check (import the logic or replicate the identical two-path fallback) rather than hardcoding one layout — verified against both this repo (nested) and Gym_App (flat) resolving correctly with the same code.

### Scenario 4p: Fix does not mask the subprocess NameError with a different silent failure
Given the fixed `_find_project_root()` with `subprocess` properly imported
When the function runs in a normal repo context
Then the git-rooted resolution path executes and succeeds, rather than silently falling through to the directory-walk fallback as it has been doing — and if it fails for a genuine reason (not a `NameError`), the fallback still applies, but the bare `except Exception` no longer conceals an import error indefinitely.

### Scenario 4q: Post-fix baseline run establishes real findings, not asserted zero
Given the fixed script run once against the actual current state of `review_context_universal.md`, `review_context_project.md`, and `architecture_checks.py`
When `wiki_lint.py` runs its full check
Then `.agent/state/wiki_lint_findings.md` is regenerated and reviewed by a human — its content is not asserted in this scenario, since the real result is unknown until the fix runs; what's asserted is that the report changes from its current "0 issues" state to a report reflecting genuine analysis, and any findings surfaced are logged as new backlog items rather than silently absorbed into this spec's delivery (mirrors the existing Out-of-Scope precedent: "Retroactively writing missing tests for every gap Phase A/B surfaces... triaged and closed as separate, normal work").

### Scenario 4r: Fix detects a legacy, unloaded context file as its own finding
Given a project has both a `review_context.md` and a `review_context_universal.md`/`review_context_project.md` split (Gym_App's actual current state)
When the fixed `wiki_lint.py` runs
Then it reports the legacy file as a distinct finding — e.g. `LEGACY-CONTEXT-FILE: 'review_context.md' exists but is not loaded by context_loader.py; content here is not part of the live AI review context` — rather than silently scanning it as if it were current, so a project carrying a stale duplicate is surfaced rather than confidently misread.

### Scenario 4s: Fix works correctly against Gym_App without any Gym_App-specific code
Given the fixed `wiki_lint.py`, unmodified, copied into Gym_App via the normal harness upgrade process (not specially adapted for it)
When it runs there
Then it correctly resolves Gym_App's flat `architecture_checks.py` path, its two live context files, flags `review_context.md` as legacy per Scenario 4r, and surfaces real orphaned-rule findings for `BUSINESS-RULES`/`FINANCIAL-PRECISION` that have been invisible since 2026-07-01 — confirming the fix is generic, not a special case bundled for this repo alone.

### Scenario 5: E2E scenario classification produces an accurate single-gate/cross-gate tally
Given the 29 existing scenarios in `tests/e2e/run_e2e_verification.py`
When the Phase C classification runs
Then each scenario is tagged `single-gate` or `cross-gate`, and the count is manually spot-checked against at least 5 scenarios to confirm the automated classification matches human judgment before the tally is treated as reliable.

### Scenario 6: Outcome-equivalence test catches a data-deletion regression
Given a project fixture with known operational config values (schema exemptions, analogous to GymBase's real values but fixture-only)
When a refactor is applied that claims to preserve those values while changing their storage mechanism
Then an outcome-equivalence test asserting the specific values are unchanged fails if the refactor silently drops or empties them — reproducing, in a hermetic fixture, the class of regression caught manually in the schema-hardening cleanup.

---

## 5. Proposed Phasing

**Phase A — Spec-scenario cross-reference** (highest leverage, lowest effort — static parsing of already-structured Gherkin blocks)
- Parser for `### Scenario:` blocks across `docs/planning/specs/**/*.md`
- Matching heuristic against test file contents (component name + outcome keyword proximity, refined iteratively — expect false positives/negatives in v1, treat as a coverage report not a source of truth on day one)
  - Mock/real-entry-point detection: parse the test file's AST for the target component's import and call site; classify as mocked if the call site is wrapped by or substitutes a `unittest.mock.patch`/`MagicMock`/`monkeypatch` target matching the component name, else real. This classification feeds Scenario 2's two-tier confidence output directly — it is not a separate concern from the proximity matcher.
- Output: `.agent/state/loop_closure_report.md`, modeled on `wiki_lint_findings.md`'s existing format

**Phase B — Static wiring audit**
- Seed the consumer list manually for the four named artifacts (§2)
- AST-based reference check per consumer file
- Impact-weighted decision log retention in `harness_utils.py` replacing pure-FIFO archival
- Direct bug fix: `distill_dream.py` template update emitting `Generated: {date}` matching `harness_health.py` regex, plus backfill of `verification-before-completion__state_anomaly__open.md`
- Direct bug fix: `regression_runner.py` main() exit code reconciliation for empty dataset to match `eval-pipeline.md` escalation trigger
- Direct bug fix: `wiki_lint.py` dynamic resolution for live context files via `context_loader.py` and `architecture_checks.py` via `harness_utils.py` dual-path lookup; legacy context file detection; `subprocess` import added to `_find_project_root()`; duplicate definition removed
- Output: same report, separate section

**Phase C — E2E classification + outcome-equivalence tests**
- Classify existing 29 E2E scenarios
- Add outcome-equivalence tests at under-covered cross-gate seams
- Add the fixture-based outcome-equivalence pattern as a documented, reusable test helper (`tests/helpers/outcome_equivalence.py` or similar) so future refactors touching operational data have a ready-made pattern to write against, not just a principle to remember

Each phase is independently shippable. Phase A alone would have flagged HIB-080's underlying spec-claim gap; Phase B would have flagged the specific wiring defect; Phase C's pattern would have flagged the schema-exemption regression. None depend on the others completing first.

---

## 6. What Changes Where (Implementation Map)

| Component | Change | Phase |
|---|---|---|
| New: `.agent/scripts/loop_closure_check.py` | Gherkin scenario parser + test cross-reference matcher | A |
| `.agent/scripts/loop_closure_check.py` (same file, new function) | Mock-vs-real classifier per above | A |
| New: `.agent/scripts/wiring_audit.py` | AST-based multi-consumer reference checker | B |
| `.agent/scripts/wiring_audit.py` (same file, new function) | Schema/sanity validation of `wiring_consumers.yaml` on load — reject empty consumer lists, malformed entries; fail loud, not silent-pass | B |
| `.agent/config/wiring_consumers.yaml` (new) | Seeded list of shared artifacts → documented consumers, per §3 assumption | B |
| `src/scripts/harness_utils.py` — `record_decision()` | Add required `impact`: `'high'\|'medium'\|'low'` parameter; fail-loud validation matching existing field checks | B |
| `src/scripts/harness_utils.py` — `archive_old_decisions()` | Replace pure-FIFO eviction with: pin high entries; compute `age_in_days / impact_weight` for medium/low candidates; evict in descending priority order; fail loud (0 archived, warning) if only high entries remain over threshold | B |
| `.agent/scripts/log_decision.py` | Update CLI wrapper to accept and pass required `impact` parameter to `record_decision()` | B |
| `.agent/scripts/distill_dream.py` | Add `Generated: {date}` line to both new-card and merged-card templates; date sourced from earliest evidence timestamp, not `datetime.now()` or file mtime | B |
| `.agent/state/dream_proposals/verification-before-completion__state_anomaly__open.md` | One-time backfill: add `Generated: 2026-06-13`, derived from its earliest evidence entry | B |
| `tests/` (new or existing dream-phase test file) | Add a regression test asserting `distill_dream.py`'s actual template output satisfies `harness_health.py`'s regex — a direct producer-output-vs-consumer-parser contract test, so this specific pair cannot silently drift apart again | B |
| `.agent/evals/regression_runner.py` — `main()` | Replace the empty-dataset `print(warning); sys.exit(0)` path with a message stating the gate is hollow and requires escalation, exiting non-zero | B |
| `.agent/scripts/wiki_lint.py` — context-file resolution | Replace hardcoded `CONTEXT_FILE` with dynamic resolution via `context_loader.py`'s own `UNIVERSAL_CONTEXT_FILE`/`PROJECT_CONTEXT_FILE` (import if present; fall back to a single `review_context.md` only if `context_loader.py` itself doesn't exist in the target project — i.e. an older/pre-split installation) | B |
| `.agent/scripts/wiki_lint.py` — `ARCH_CHECKS_FILE` resolution | Replace hardcoded path with the same nested-then-flat dual-path check `harness_utils.py`'s `_setup_sys_path()` already uses | B |
| `.agent/scripts/wiki_lint.py` — new legacy-file check | Add detection: if a `review_context.md` exists in a project alongside a resolved universal/project split, emit a `LEGACY-CONTEXT-FILE` finding rather than scanning it as current | B |
| `.agent/scripts/wiki_lint.py` — `_find_project_root()` | Add missing `import subprocess`; remove duplicate/shadowing definition | B |
| N/A (operational step, not a code change) | Run `wiki_lint.py` once post-fix and route resulting findings, if any, to the harness improvement backlog for triage | B |
| `tests/e2e/run_e2e_verification.py` | Add `# gate-scope: single \| cross` tag per scenario | C |
| New: `tests/helpers/outcome_equivalence.py` | Reusable fixture-based outcome-equivalence test pattern | C |
| New: `tests/data/schema_hardening_fixture/` | Hermetic fixture project for Scenario 6 | C |
| `.agent/state/loop_closure_report.md` (new artifact) | Combined Phase A/B report output | A, B |

---

## 7. Known Residual Risks

- **Phase A's matching heuristic will have false positives/negatives initially.** Natural-language proximity matching between a Gherkin scenario and a test assertion is not a solved problem; treat v1's report as directional, not authoritative. Per Scenario 1b, the false-positive/false-negative rate must be calibrated against at least 10 spot-checked results and recorded in the report before findings are treated as signal.
- **Phase B's manually-seeded consumer list can itself drift** — if a spec adds a new consumer of a shared artifact and `wiring_consumers.yaml` isn't updated, that consumer is invisible to the audit. This is a smaller, more contained version of the exact problem this spec addresses; mitigate by adding "update wiring_consumers.yaml" as a checklist item in the spec-authoring workflow when a spec introduces a new shared-artifact consumer.
- **Vacuous argument pass-throughs are caught explicitly.** Presence of keyword arguments alone (e.g., `baseline=None`) previously posed a false-negative risk; Phase B addresses this structurally by evaluating argument values and classifying default/literal pass-throughs as `PARTIALLY-WIRED` (Scenario 4b).
- **Pinning high entries has no automatic release valve.** If high-impact entries alone push the log over threshold indefinitely, the mechanism deliberately refuses to auto-evict one (Scenario 4g) — this requires a human to explicitly move an entry to archive manually, the same deliberate-transition pattern used for spec DELIVERED status. This is a design choice, not an oversight: silently evicting a pinned entry to satisfy a line-count would defeat the entire point of pinning.
- **Impact classification remains a human/agent authoring judgment, not a verified fact.** Nothing in Phase B checks whether a high tag was correctly assigned against the rubric — only that the retention mechanism honors whatever tag was given. A miscategorized medium entry that should have been high is a classification error outside this spec's mechanical scope, same as Phase B's existing wiring audit doesn't judge whether a design is correct, only whether the wiring matches what was claimed.
- **This fix addresses one instance, not the general class.** The underlying shape — a producer's serialized text output silently failing to satisfy a consumer's parser expectations — is structurally different from Phase B's AST-based wiring audit and is not claimed to be covered by Phase B elsewhere. Whether other producer/consumer text-artifact pairs in the harness have the same latent risk is an open question, explicitly deferred (see §8), not assumed solved by this fix.
- **This fix addresses one documented-trigger/code mismatch, not a sweep of all of them.** `.agent/workflows/*.md` contains many other escalation triggers (stale unmerged branches, deterministic-failure flakiness, others) whose implementing code has not been checked for the same class of drift. This fix resolves the one instance found; a systematic cross-check of documented triggers against their code is separate future work.
- **Exiting non-zero on empty dataset may surface during legitimate early-project onboarding (Scenario 4m)** — this is intended behavior, not a regression to quietly patch around if a fresh project's CI starts failing here. Document this clearly in the fix's commit message so it isn't mistaken for a bug during a future onboarding session.
- **This fix will very likely surface a backlog of real orphaned-rule and stale-identifier findings that have been invisible for an unknown period.** That backlog is expected and is not itself a defect introduced by this fix — see Scenario 4q and the Out-of-Scope precedent already established for Phase A/B. Do not treat a non-zero post-fix findings count as a regression.
- **This fix was validated against two real installations (this repo and Gym_App), not just this repo alone** — the original v1.6 scope would have passed this repo's own tests while remaining broken for Gym_App's different layout. Any future spec touching installed-project-facing scripts should check at least one other installed project before treating a fix as generalized, not just as a matter of good practice but because this specific spec already got that wrong once.
- **The legacy-file detection (Scenario 4r) is a new, narrow check, not a general "detect all stale documentation" mechanism.** It specifically targets the review-context file case because it's now confirmed live in a real project; it does not attempt to detect analogous drift in other document types.
- **Gym_App itself is not touched by this spec.** The fix ships in the harness; Gym_App receives it only via its own next harness upgrade cycle, at which point the real orphaned-rule findings this fix will surface (BUSINESS-RULES, FINANCIAL-PRECISION) become that project's own backlog item, triaged separately — not bundled into this harness-side spec's delivery.
- **The identical subprocess-import bug in co_change_reconciler.py is not fixed by this version.** Confirmed present via the same audit; deliberately scoped out here since it's a different file with a different producer/consumer relationship — see §8.
- **Two files sharing an identical, specific bug shape suggests a common template origin.** A broader sweep for a third instance has not been done; this fix addresses the two diagnosed instances only (one now, distill_dream.py unaffected, co_change_reconciler.py deferred).
- **None of this replaces human review.** These are detection aids that make a specific class of gap cheap to find mechanically; the schema-exemption regression was still caught by a human reading a diff, not a script. Phase C's outcome-equivalence pattern is the one mechanism here that could have caught it automatically, and only for the specific case someone thought to write a fixture for.
- **Advisory-first is a deliberate choice, not a placeholder.** Converting Phase A/B to blocking gates before they've proven low-false-positive-rate risks recreating the exact "gate cries wolf, gets bypassed" dynamic the harness's own `HIB-045` (bypass rate as a proactive health metric) already tracks as a known failure mode elsewhere.

---

## 8. Explicitly Deferred

- Converting Phase A/B from advisory report to blocking pre-commit/pre-merge gate — revisit after the report has run against the existing corpus and demonstrated an accurate, low-noise signal.
- Retroactively writing every test Phase A/B's first run surfaces as missing — triaged and closed as normal backlog work, not bundled into this spec's delivery.
- Generalizing a "producer output satisfies consumer parser" contract-test pattern across other text-artifact pairs in the harness — this fix resolves the one diagnosed instance; a systematic sweep for other instances is separate future work.
- Systematically cross-checking every documented escalation trigger in `.agent/workflows/*.md` against its implementing code for the same class of doc/code drift — this fix resolves the one diagnosed instance found this session; a full sweep is separate future work.
- Retiring or correcting Gym_App's `review_context.md` banner and content — that's Gym_App-side cleanup, to happen after its next harness upgrade surfaces the `LEGACY-CONTEXT-FILE` finding there; not part of this spec.
- Triaging the specific orphaned-rule findings this fix will surface in Gym_App once upgraded (`BUSINESS-RULES`, `FINANCIAL-PRECISION`, and any from `review_context_universal.md`'s six rule tags) — separate backlog work for that project, not this spec's delivery.
- Fixing the identical subprocess-not-imported bug in `co_change_reconciler.py` — diagnosed, deferred to separate work, same treatment as other cross-file generalizations in this spec.
- Building an automated consumer for `co_change_reconciliation_report.md` (LOOP-012) — the reconciler itself works; nothing currently surfaces its output automatically. Separate design question, not part of this fix.
- Sweeping for a third file sharing the same `_find_project_root()`/`subprocess` bug pattern — this version fixes the one instance touched by this file's other changes; a dedicated sweep is separate future work.
- General mutation testing / property-based testing adoption — related problem, different tooling, separate consideration.
- Auto-discovery of "who *should* consume a shared artifact" (as opposed to auditing named consumers) — not a well-posed static analysis problem as scoped here.

---

**Per standing protocol:** this spec stops here for review and approval. No code, schema, or script implementation proceeds until sign-off.
