# SPEC: Loop Closure Verification (T1-K-19)

**Status**: APPROVED
**Author**: Claude (drafting)
**Tracked under**: T1-K-19
**Target Release**: v1.4.14
**Related**: T1-K-09 (consistency gate — "gates actually gate," binary precedent this generalizes), HIB-080 (direct evidence case), HIB-081 (supporting evidence case, do not develop independently), SPEC-enforcement-postures.md (the spec whose cross-gate claim HIB-080 silently violated), T1-L-18 (Gherkin scenario coverage for outer-loop docs — a sibling concern at the spec-completeness layer rather than the test-coverage layer)
**Changelog**:
- v1.0 (2026-07-25, Claude): Initial draft, motivated by two incidents in one session (HIB-080; a pre-merge schema-exemption regression) that a fully green 550/550 test suite did not catch.

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
- **Phase B — Static wiring audit.** For each shared artifact with more than one documented consumer (starting with `GateContext`, `.agent/baseline.json`, `session.json`, `capability_calibration.json`), an AST-based script confirming each claimed consumer's source actually references the specific fields/functions the producing spec attributes to it. Mirrors exactly the manual check that found HIB-080 (confirming `architecture_checks.py`'s `disposition()` call includes `baseline=`), generalized and automated.
- **Phase C — E2E scenario classification and outcome-equivalence tests.** Audit `tests/e2e/run_e2e_verification.py`'s existing 29 scenarios, tagging each as single-gate or genuinely cross-gate. Add outcome-equivalence tests at cross-gate seams currently covered only by single-gate scenarios. Add a general outcome-equivalence test pattern (load a real project fixture's operational config/data, run the check, assert zero-diff vs. a pinned baseline) for any future refactor claiming behavior-preservation.

### Out-of-Scope (Non-Goals)
- Making Phase A or B a **blocking** pre-commit or pre-merge gate in this spec. Both ship as reporting/advisory tools first (see §7 Known Residual Risks) — converting either to blocking is a follow-up decision after they've run against the existing spec/test corpus and produced a manageable, accurate signal.
- Retroactively writing missing tests for every gap Phase A/B surfaces. This spec delivers the *detection* mechanism; the resulting backlog of specific gaps is triaged and closed as separate, normal work — the equivalent of `harness_health.py` surfacing a signal rather than this spec being scoped to close every instance of it.
- General mutation testing or property-based testing infrastructure — a different (and reasonable) approach to the same underlying "test suite gives false confidence" problem, but distinct tooling and out of scope here.
- Replacing boundary-mocked unit tests generally. Mocking remains correct for the majority of the suite; this spec targets specifically the seams between components with documented multi-party contracts.

---

## 3. Assumptions

- `[Resolved: APPROVED specs under docs/planning/specs/ (including archive/) are the authoritative source of cross-component outcome claims for Phase A. Specs without Gherkin Scenario blocks predate T1-L-01's formalization and are out of scope for retroactive scenario extraction — Phase A operates only on specs already in the required format.]`
- `[Resolved: Phase B's "documented consumer" list is seeded manually from each artifact's producing spec (e.g. SPEC-enforcement-postures.md §5.3 names both ai_review.py and architecture_checks.py as GateContext/posture consumers) rather than auto-discovered — auto-discovery of "who should consume this" is not a well-posed static analysis problem; auto-discovery of "does a named consumer actually reference it" is.]`
- `[Resolved: Phase C's outcome-equivalence pattern requires a real project fixture (a minimal but representative schema/config, not GymBase's live data) checked into tests/data/ or equivalent, so the test is hermetic and does not depend on GymBase's actual repository state.]`
- `[Pending: whether Phase A/B reports integrate into harness_health.py's existing output (as a new section, consistent with how schema-hardening trend and dream-proposal staleness already surface) or ship as standalone CLI scripts initially, promoted to harness_health.py once stable. Recommend standalone-first, matching the precedent set by T1-K-09's tests/test_framework_consistency.py, which the T1-K-19 audit tooling closely resembles in spirit.]`

---

## 4. Acceptance Criteria

### Scenario 1: Spec-scenario cross-reference detects an unimplemented outcome assertion (Phase A)
Given an APPROVED spec containing a Gherkin scenario naming a specific component and a specific disposition outcome
When the cross-reference script runs against the current test suite
Then a scenario whose `Then` outcome is not asserted anywhere against that component's real entry point is reported as `UNVERIFIED`, distinct from scenarios with a matching test.

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
- Output: `.agent/state/loop_closure_report.md`, modeled on `wiki_lint_findings.md`'s existing format

**Phase B — Static wiring audit**
- Seed the consumer list manually for the four named artifacts (§2)
- AST-based reference check per consumer file
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
| New: `.agent/scripts/wiring_audit.py` | AST-based multi-consumer reference checker | B |
| `.agent/config/wiring_consumers.yaml` (new) | Seeded list of shared artifacts → documented consumers, per §3 assumption | B |
| `tests/e2e/run_e2e_verification.py` | Add `# gate-scope: single \| cross` tag per scenario | C |
| New: `tests/helpers/outcome_equivalence.py` | Reusable fixture-based outcome-equivalence test pattern | C |
| New: `tests/data/schema_hardening_fixture/` | Hermetic fixture project for Scenario 6 | C |
| `.agent/state/loop_closure_report.md` (new artifact) | Combined Phase A/B report output | A, B |

---

## 7. Known Residual Risks

- **Phase A's matching heuristic will have false positives/negatives initially.** Natural-language proximity matching between a Gherkin scenario and a test assertion is not a solved problem; treat v1's report as directional, not authoritative, and expect to refine the heuristic against real spec/test pairs before trusting a clean report as proof of coverage.
- **Phase B's manually-seeded consumer list can itself drift** — if a spec adds a new consumer of a shared artifact and `wiring_consumers.yaml` isn't updated, that consumer is invisible to the audit. This is a smaller, more contained version of the exact problem this spec addresses; mitigate by adding "update wiring_consumers.yaml" as a checklist item in the spec-authoring workflow when a spec introduces a new shared-artifact consumer.
- **None of this replaces human review.** These are detection aids that make a specific class of gap cheap to find mechanically; the schema-exemption regression was still caught by a human reading a diff, not a script. Phase C's outcome-equivalence pattern is the one mechanism here that could have caught it automatically, and only for the specific case someone thought to write a fixture for.
- **Advisory-first is a deliberate choice, not a placeholder.** Converting Phase A/B to blocking gates before they've proven low-false-positive-rate risks recreating the exact "gate cries wolf, gets bypassed" dynamic the harness's own `HIB-045` (bypass rate as a proactive health metric) already tracks as a known failure mode elsewhere.

---

## 8. Explicitly Deferred

- Converting Phase A/B from advisory report to blocking pre-commit/pre-merge gate — revisit after the report has run against the existing corpus and demonstrated an accurate, low-noise signal.
- Retroactively writing every test Phase A/B's first run surfaces as missing — triaged and closed as normal backlog work, not bundled into this spec's delivery.
- General mutation testing / property-based testing adoption — related problem, different tooling, separate consideration.
- Auto-discovery of "who *should* consume a shared artifact" (as opposed to auditing named consumers) — not a well-posed static analysis problem as scoped here.

---

**Per standing protocol:** this spec stops here for review and approval. No code, schema, or script implementation proceeds until sign-off.
