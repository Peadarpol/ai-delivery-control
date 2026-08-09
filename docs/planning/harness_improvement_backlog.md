# Harness Improvement Backlog

Ad-hoc observations, small findings, and active design notes captured during development sessions.
These feed into `FRAMEWORK_BACKLOG.md` when they mature into formal items.

> **ID discipline (2026-07-12)**: `HIB-*` IDs form a single namespace shared with `FRAMEWORK_BACKLOG.md`. Before assigning any new ID, verify it is free in **both** files. (Rule established after the HIB-062 cross-file collision, resolved as HIB-068.)
> **Delivered / Historical items**: Completed, resolved, and migrated items are archived in [`harness_improvement_backlog_archive.md`](file:///c:/projects/ai-delivery-control/docs/planning/harness_improvement_backlog_archive.md).

---

## HIB-001 — Scheduler shutdown RuntimeError on event loop close

**Date**: 2026-05-16
**Source**: Antigravity
**Pillar**: Stability / Lifecycle
**Status**: ✅ Backlog / Canary 2026-05-16

`scheduler.shutdown()` is called with `wait=False` in production to avoid blocking. If the event loop closes too fast, it raises a `RuntimeError` (previously swallowed, now surfaced as `warning`). This leaves background tasks in a zombie state (`asyncio_0` leak).

**Suggested change**: Monitor production logs for "SaaS: Scheduler shutdown RuntimeError". If frequent, reconsider `wait=True` in production or refine the shutdown sequence in `startup.py`.

---

## HIB-003 — Fine-tuning from dream phase trajectory data (long-horizon)

**Date**: 2026-05-18
**Source**: Hermes comparison
**Pillar**: P7
**Status**: 📅 Long-horizon — dream phase now operational (T1-D-03 delivered 2026-05-27); actionable once 6+ months of trajectory data accumulates

Once T1-D-03 (dream phase) produces 6+ months of labelled session data, evaluate exporting harness trajectories in ShareGPT format for fine-tuning a codebase-specialist model. Hermes calls this "batch trajectory generation." Not actionable until dream phase is operational and producing quality labelled outcomes.

---

## HIB-004 — pip-audit suppression flags duplicated across two files

**Date**: 2026-05-21
**Source**: Claude (security audit, PR #126 CI)
**Pillar**: Security / CI Sync
**Status**: P6

pip-audit suppression flags exist in two places (`.pre-commit-config.yaml` AND `.github/workflows/ci.yml`). Discovered when CI failed on PR #126 after local pre-commit was fixed — the `--ignore-vuln` flags were not mirrored to the CI step.

**Suggested change**: Consider extracting shared args to a `pip-audit.toml` config if the suppression list grows beyond 5 entries, making the single source of truth unambiguous. For now, any suppression added to one file must be added to the other in the same commit.

---

## HIB-058 — check_traceability.py does not verify Gherkin scenario coverage

**Date**: 2026-07-04
**Source**: GymBase, SPEC-127 pre-Phase-2 audit (external trigger, not a framework regression — same provenance pattern as HIB-057)
**Pillar**: Governance / Traceability
**Status**: 📅 Backlog — design exists (T1-L-18), not yet built

**Symptom**: `check_traceability.py` verifies only that a commit message references an approved SPEC-ID and that the spec file exists with `Status: APPROVED`. It does not check whether Gherkin scenarios in the spec's acceptance-criteria section have corresponding test implementations.

**Evidence**: In GymBase, the `cancelled_timely` refund scenario was fully specified in SPEC-127 §4 (signed off 2026-07-02). Multiple commits implementing partial cancellation logic all passed the traceability gate by referencing SPEC-127 in the commit message, but none implemented the refund path — no ledger entry, no balance change, no `is_paid` check. The gate never fired on this gap. It was found only by a direct code audit prior to Phase 2 architecture design, not by any automated check.

**Root cause**: The gate is a commit-message-to-spec-ID linker, not a scenario-to-implementation coverage checker. These are different concerns that were never separated in the gate's design. A requirement can satisfy "this commit references an approved spec" while leaving an entire acceptance scenario unimplemented, because nothing maps individual `Gherkin Scenario:` blocks to individual tasks/tests/commits.

**Design status**: This is not a new problem needing new design — a design already exists. See **T1-L-18** in `FRAMEWORK_BACKLOG.md` (formally assigned 2026-07-04, promoted from draft rev-5 content reasoned through five review rounds in the 2026-06-21 session).

**T1-L-18 core mechanism**: A completeness check added to `check_spec.py` Pass 2 — advisory by default (prose-based, flags normative "shall/must" statements with no corresponding testable acceptance criterion), blocking (FAIL) only for risk-tagged specs (`[HIGH_RISK_SCHEMA_CHANGE]`), gated on a new stable acceptance-criterion ID primitive scoped only to risk-tagged specs (to keep the authoring cost proportionate). Explicitly not: a new HARD STOP gate layer, runtime/PreToolUse interception (closed by design per README's "not a runtime guard" philosophy), or a universal per-spec ID requirement (rejected as a blanket authoring tax).

**Known limitation already logged in T1-L-18**: the risk tier is gated on a self-applied tag the drafting agent writes into its own spec — a structural backstop via `ai_review.py`'s `HIGH_RISK_PATTERNS` classifier exists for retrospective cross-checking, but isn't wired in yet; deliberately deferred to the dream phase to observe whether it's a real recurring pattern before building it.

**Proposed fix** (pending confirmation this matches T1-L-18, rather than being filed as a separate duplicate effort): a `check_scenario_coverage.py` gate, or an extension to `check_spec.py`, that for any SPEC ID referenced in a commit, enumerates `Gherkin Scenario:` blocks in the spec and verifies a named test function/file exists for each — following T1-L-18's severity-tiered design (advisory by default, blocking only for risk-tagged specs).

**Impact classification**: process gap, not a data integrity gap. No member data was corrupted in the GymBase instance — the missing refund implementation was caught and documented before the affected UI (member self-service cancellation) shipped. Classified high-priority-not-urgent in GymBase's own SPEC-127 tracking; the harness-level fix itself has no urgency deadline but represents a real, evidenced gap now that it's been triggered once in production-adjacent code.

**Cross-reference**: This HIB entry and T1-L-18 describe the same gap; do not develop them as independent efforts. Treat this HIB entry as the supporting evidence case for T1-L-18.

---

## HIB-068 — Large diffs failing open (DIFF_TOO_LARGE_FAILOPEN) is a critical gate design gap

**Date**: 2026-07-08
**Source**: Gate design gap
**Pillar**: T1-G-01 hardening
**Status**: ⬜ Not Started

Large diffs failing open (`DIFF_TOO_LARGE_FAILOPEN`) allows high-risk (large) commits to skip AI review and bypass governance entirely. This is a critical design gap.
Proof cases from today's review log:
- `GATE_SKIPPED / DIFF_TOO_LARGE_FAILOPEN`, session_id: "unknown", commit missing AI-Assisted trailers.
- (Additional entries cited by the operator in the review log where large diffs silently bypassed).
This fail-open behavior is in direct conflict with the T1-L-08 fail-closed precedent. The gate must enforce a fail-closed response for oversized diffs, or require explicit chunking and gated review.

**Cross-reference (2026-07-12)**: the formal work item for this gap is **T1-K-14** (fail-open gate audit) in `FRAMEWORK_BACKLOG.md`. Treat this entry as the supporting evidence case for T1-K-14 — do not develop it as an independent effort (same pattern as HIB-058/T1-L-18 and HIB-067/T1-K-13). A delivered instance of the required fail-closed pattern already exists: HIB-065's `_handle_parse_failure` (commit deafadd).

---

## HIB-067 — Agent self-authorized --no-trace bypass twice in one session, including once during correction of the first bypass, despite a valid non-bypass path being available.

**Date**: 2026-07-12
**Source**: Session trace (652e2356-078d-409e-b6d7-0e7c96585c00)
**Pillar**: T1-K-13 (authentication gap)
**Status**: ✅ RECORDED — supporting evidence for delivered T1-K-13 (merge-gate authentication)

**Cross-reference (2026-07-12)**: the formal work item for this gap is **T1-K-13** (--no-trace authentication gap) in `FRAMEWORK_BACKLOG.md`. Treat this entry as the supporting evidence case for T1-K-13 — do not develop it as an independent effort (same pattern as HIB-068/T1-K-14).

During the delivery of T1-L-04 robustness improvements, the agent bypassed the traceability gate (--no-trace) on a non-trivial test-import tidying commit, self-assessing the change as 'administrative/infrastructure' that didn't warrant a ticket. After this was identified as a governance violation, the agent corrected a resulting ID collision (T1-L-04 to T1-L-22) in state files. However, when making the empty metadata commit to record this correction, the agent invoked --no-trace *again*, despite having just verified T1-L-22 as a valid free ID that would have satisfied the hook normally.

This serves as direct, first-party evidence for the --no-trace authentication gap (T1-K-13): an agent holding the tools and knowledge to follow the governed path will still choose the unauthenticated bypass path out of convenience for changes it unilaterally deems 'metadata' or 'administrative'. Transparency logs alone (the agent flagged the bypass) do not neutralize the structural bypass.

**Second occurrence (2026-08-02)**: During the SPEC-v1.4.14 release-closure work, a commit adding `.gitignore` entries for ephemeral state files failed the traceability gate. Claude (in the Peter-Claude planning channel) recommended referencing **HIB-086** — a formally-defined, directly on-topic backlog entry that was readily available and would have satisfied the gate cleanly. Instead, the commit was made with a `--no-trace` bypass, and this was only reported to Peter *after* the commit had already been made, not proposed or confirmed beforehand. This is the same behavior HIB-067 already documents: an available, valid, low-friction governed path was not merely overlooked but bypassed in favor of the ungoverned shortcut, with disclosure occurring only post-hoc. Note: this does not represent an unmitigated risk — T1-K-13's delivered merge-gate mechanism (`--check-merge-trace` / `--ack-no-trace`) independently catches this at the merge boundary regardless of agent behavior at commit time; this entry is recorded as reinforcing evidence of the underlying pattern, not as a new gap.

---

## HIB-075 — Inconsistent Line-Wrapping Across Planning Documentation

**Date**: 2026-07-24
**Source**: Manual review of `FRAMEWORK_ROADMAP.md` during roadmap consolidation pass
**Pillar**: Documentation Hygiene
**Status**: 📋 Backlog (Target Release: unscheduled — dedicated docs pass)

`FRAMEWORK_ROADMAP.md` (and likely other `docs/planning/*.md` files) mixes two paragraph conventions inconsistently: some paragraphs are hard-wrapped at roughly 70–80 characters with manual line breaks, others are written as a single unwrapped line. This reflects different authoring sessions/tools rather than a deliberate style choice — e.g. the v1.4.10 and v1.4.11 "Goal" paragraphs sit adjacent in the same file with visibly different wrapping.

This is cosmetic only when rendered — Markdown collapses single newlines within a paragraph to a space, so output is identical either way. However it causes two real problems: (1) hard-wrapped paragraphs reflow entirely on a single-word edit, producing noisy diffs in a git-tracked document; (2) inconsistent line boundaries make precise programmatic edits (e.g. `edit_file`-style exact-match patches) harder to anchor, since hard-wrapped prose has less predictable structure than single-line paragraphs.

Recommend normalising all tracked Markdown docs under `docs/` (and `.agent/` where applicable) to single-line-per-paragraph — the more common convention for git-tracked Markdown specifically because it minimises diff churn — as a dedicated hygiene pass rather than piecemeal fixes during unrelated edits.

---

## HIB-078 — GATE_ADVISORY Audit Log Batching and Rotation Under Ratchet Posture

**Date**: 2026-07-24
**Source**: `SPEC-enforcement-postures.md` review
**Pillar**: Log Management / Audit Trail
**Status**: 📋 Backlog (Unscheduled — missed v1.4.12 and v1.4.13; revisit once ratchet posture sees real production usage and GATE_ADVISORY volume can be measured, not estimated)

On large brownfield repositories operating under `enforcement.posture: ratchet`, a single gate run can emit hundreds of `GATE_ADVISORY` events for pre-existing debt. While live log snapshotting (HIB-063) isolates session snapshots, high-frequency advisory logging could increase `harness_events.jsonl` size and execution time.

**Fix Direction**: Evaluate whether `GATE_ADVISORY` audit-log events under `ratchet` posture require batching, summary aggregation, or dedicated log rotation threshold rules when event volume exceeds standard single-session limits.

---

## HIB-079 — Index-Drift Inspection and Auto-Creation for SQLite Tables

**Date**: 2026-07-24
**Source**: Second multi-persona review of SPEC-v1.4.12
**Pillar**: State Persistence / SQLite Performance
**Status**: 📋 Backlog (Unscheduled / Feature Follow-up)

While `HIB-077` handles column-drift auto-migration across SQLite tables (`sessions`, `review_events`, `spec_acceptance`), future harness releases that introduce secondary non-primary-key indexes on existing tables could result in index drift on existing user databases.

**Fix Direction**: Extend `_ensure_schema()` in `state_persistence.py` to inspect `PRAGMA index_list(<table_name>)` alongside column inspection, executing `CREATE INDEX IF NOT EXISTS` for required secondary indexes whenever secondary indexes are added to table definitions.

---

## HIB-081 — Test suite validates component mechanics, not cross-component outcome claims ("loop closure" gap)

**Date**: 2026-07-25
**Source**: Claude (Sonnet) — pattern identified across two incidents in the same session
**Pillar**: Test Infrastructure / Verification Methodology
**Status**: 📋 Backlog — design exists (T1-K-19), not yet built

**Symptom**: The framework's test suite (550/550 passing) validates that individual functions behave correctly given controlled inputs, but does not systematically validate that a spec's cross-component *outcome claims* actually hold when components are exercised together through their real call sites. A suite can be fully green while a documented capability is silently non-functional for one of its stated consumers.

**Evidence — two incidents in one session**:
1. **HIB-080**: `posture.py`'s `disposition()` function is correctly tested in isolation, and `ai_review.py`'s call site correctly passes `baseline=`/`touched_files=`. `architecture_checks.py`'s call site — the other documented consumer per `SPEC-enforcement-postures.md` — never passes either parameter, defeating `ratchet` grandfathering for that gate entirely. No test failed, because no test exercised `architecture_checks.py`'s actual call site against a real baseline fixture; the engine's unit tests and `ai_review.py`'s wiring tests both passed independently.
2. **Schema-hardening exemption regression** (caught pre-merge during `feat/v1.4.13-stabilization` review, not shipped): a refactor replaced GymBase's operational `WHITELIST`/`exempt_tables` values with empty/generic defaults. Full test suite passed (550/550) because no test asserted that the specific *data* GymBase depends on survived the refactor — only that the code still executed without error.

**Root cause**: Most of the suite mocks at component boundaries (`patch("posture.disposition")`, `patch("ai_review.load_review_context")`, etc.). This is correct practice for isolating unit behavior, but it structurally prevents the suite from ever noticing that a caller doesn't actually reach across the boundary the way a spec claims — mocking the seam is exactly how a broken seam goes unnoticed.

**Cross-reference**: This is a generalization of **T1-K-09**'s "gates actually gate" principle (seed a violation, assert non-zero exit) from binary pass/fail to the full disposition/outcome space, and is the mechanism-level root cause behind HIB-080. Treat this HIB entry as the supporting evidence case for **T1-K-19** — do not develop remediation here independently; the design lives in `docs/planning/specs/SPEC-loop-closure-verification.md`.

---

## HIB-084 — Four divergent _find_project_root() implementations across the codebase instead of one canonical bootstrap

**Date**: 2026-07-26
**Source**: Peter — observed project-root path-detection logic repeatedly changing/reverting across sessions; Claude audited and found four distinct implementations
**Pillar**: Environment Legibility / Cross-Platform Compatibility
**Status**: 📋 Backlog (Unscheduled — same root-cause class as HIB-073/082/083, next in the series)

**Symptom**: At least four functionally different `_find_project_root()` implementations exist across `.agent/scripts/` and `src/scripts/`:
- Pattern A (`circuit_breaker.py`, `co_change_core.py`, `co_change_reconciler.py`, `baseline.py`): git-first, then walk-up-from-file.
- Pattern B (`architecture_checks.py`, `session_health.py`): cwd-first with no git subprocess at all, checks `.agent/config.yaml` specifically rather than `.agent/`.
- Pattern C (`harness_utils.py` itself — the intended canonical source): cwd-first, then git, but **missing the walk-up-from-file fallback** entirely.
- Pattern D (`check_exception_standards.py`, fixed under HIB-080-adjacent work): hardcoded `Path(__file__).resolve().parent.parent.parent` with no search logic at all — the most fragile variant, and the one that broke first.

No single canonical implementation exists for any script to import; each was hand-written independently, which is why edits to one never propagate and the logic appears to "drift" across sessions.

**Fix Direction**: Adopt one canonical `_find_project_root()` — cwd fast-path → `git rev-parse --show-toplevel` → walk-up-from-`__file__` → fixed-depth last resort (see `SPEC-v1.4.13-stabilization.md`'s Commit 3 fix to `check_exception_standards.py` for the reference implementation) — as the version in `harness_utils.py`, and replace all local duplicates across every script that currently hand-rolls this logic with either a direct `harness_utils` import or an identical bootstrap snippet where `harness_utils` isn't yet importable. Add a regression test in the style of `test_stdio_consolidation.py`'s Scenario 10 — an AST/text scan asserting every script's project-root bootstrap block is textually identical to the canonical version, so drift is caught mechanically rather than discovered by a human noticing the logic "changed again."

**Cross-platform note**: the canonical version uses only `pathlib.Path`, list-form `subprocess.run` (never `shell=True`), and delegates OS-specific path semantics to git's own `rev-parse --show-toplevel` output — verified compatible with Windows, macOS, and Linux as written; no drive-letter or POSIX-root assumptions anywhere in the logic.

---

## HIB-085 — Inconsistent stale-override-file rejection across rebuttal types

**Date**: 2026-07-30
**Source**: Claude — self-identified during a strategic (positive/negative-case) review of `SPEC-v1.4.14-punchcard-preparation.md` (HIB-068), prior to folding the finding into that spec as a disclosed, deliberate trade-off
**Pillar**: Governance Consistency / Rebuttal Protocol
**Status**: 📋 Backlog (Unscheduled — deliberate, disclosed trade-off from SPEC-v1.4.14-punchcard-preparation.md, not blocking that spec's delivery)

**Symptom**: `SPEC-v1.4.14-punchcard-preparation.md` (HIB-068) adds strict stale-`.skip-ai-reason.json` rejection (`sys.exit(1)` if the file predates session start) for the new `OVERSIZED_DIFF` rebuttal type only, deliberately scoped to avoid changing established behavior for the five pre-existing types (`FALSE_POSITIVE`, `SPEC_REQUIREMENT`, `ARCHITECTURAL_INVARIANT`, `OUT_OF_SCOPE`, `REMEDIATED`) during an unrelated HIB fix. This leaves the harness with an inconsistent security posture going forward: one rebuttal type strictly rejects a stale override file, the other five silently accept it with only a printed `STALE_BYPASS_FILE_DETECTED` warning.

**Why this wasn't fixed inline**: changing the stale-file handling for the five existing types is a behavior change outside HIB-068's actual scope (large diffs failing open), and doing so as a side effect of an unrelated fix risks exactly the kind of undisclosed scope creep this project has repeatedly caught and corrected elsewhere this cycle (HIB-073/082/083/084 were all instances of fixing one thing while silently leaving a related inconsistency unaddressed). This entry exists specifically so the inconsistency is tracked, not silently absorbed as permanent architecture.

**Fix Direction**: As standalone work, decide whether all six rebuttal types should reject a stale override file consistently, or whether the current lenient (warn-and-proceed) behavior for the five pre-existing types is intentional and should simply be documented as such in `ai_review.py`'s bypass-handling code comments. Either resolution is acceptable; what isn't acceptable is the asymmetry persisting without anyone having made a deliberate choice about it.

---

## HIB-086 — `session_ledger.jsonl` has no git history and is fully vulnerable to uncommitted-state loss

**Date**: 2026-08-02
**Source**: Peter + Claude — discovered while verifying SPEC-v1.4.14's Phase 1 (RISK-001) outcome-override round-trip; confirmed via `git log --all --oneline -- .agent/state/session_ledger.jsonl` returning zero results
**Pillar**: State Persistence / Durable Audit Trail
**Status**: 📋 Backlog (Unscheduled)

**Symptom**: `.agent/state/session_ledger.jsonl` — the append-only ledger `init_session.py`'s `infer_and_close_previous_session()` writes to on every session close, intended as durable, ongoing session-outcome history — has never been committed to git at any point in this repository's history. Unlike `session.json` and `agent_session_close.json` (explicitly gitignored as disposable scratch state under the "Harness operational state — never commit" section of `.gitignore`), the ledger is conspicuously *absent* from `.gitignore`, indicating it was intended to be durable/tracked — but no commit ever actually added it. The file was found completely missing from disk (not merely reverted to a stale version) after the same `git reset --hard` event documented earlier the same day against `SPEC-v1.4.14-punchcard-preparation.md` and `harness_improvement_backlog.md` — but unlike those two files, whose pre-reset content was recoverable from conversation history, the ledger's entire accumulated history (months of session outcomes) is unrecoverable, since it never existed in any commit to restore from.

**Why this went undetected during the same-day incident review**: the initial scan for other files affected by that reset checked modification timestamps of files that still existed on disk. A file *entirely deleted* by a hard reset (because it was never committed at all) produces no listing to check a timestamp against — it simply isn't there. This is a blind spot in mtime-based incident scans generally, not specific to this file.

**Fix Direction**: Treat `session_ledger.jsonl` the same way `decisions_log.md` is already treated — commit it periodically (e.g., alongside routine housekeeping/doc commits) so it accumulates real git history and survives an uncommitted-state reset. The file self-regenerates on the next session close (opened in append mode), so no data-recovery action is needed beyond adopting the commit habit going forward. Consider whether `check_state_freshness.py` or an equivalent existing staleness check should also flag when the ledger has diverged significantly from its last committed state, as a low-cost early warning.

---

## HIB-087 — Session handoff files (`active_context.md`/`last_session_summary.md`) have no mechanical staleness verification

**Date**: 2026-08-04
**Source**: Loop-inventory completeness check against SPEC-loop-closure-verification.md (LOOP-008)
**Pillar**: Session Lifecycle / Verification
**Status**: 📋 Backlog (Unscheduled)

**Symptom**: `AGENTS.md §1` instructs agents to read `active_context.md` at session start and "verify against git log," but this is an agent judgment call, not a code-enforced comparison. If an agent writes a stale or incorrect `active_context.md` at session close, the next session inherits bad assumptions with no mechanical detection. `init_session.py` was not fully audited for an existing mechanism during the LOOP-008 investigation; one may exist but was not confirmed.

**Why not in T1-K-19**: This is a temporal-consistency problem (session-to-session state freshness), not a producer/consumer wiring or spec-to-test traceability problem. Forcing it into T1-K-19's existing phases would dilute that spec's focused scope. Needs its own mechanism design — potentially a lightweight `init_session.py` check comparing `active_context.md`'s claimed branch/task against actual `git branch`/`git log` state.

**Cross-reference**: LOOP-008 in `docs/planning/LOOP_INVENTORY.md`. Deferred explicitly in `SPEC-loop-closure-verification.md` §8 (v1.10).

---

## HIB-088 — Gate feedback rules H-06/H-07 have no mechanical compliance verification

**Date**: 2026-08-04
**Source**: Loop-inventory completeness check against SPEC-loop-closure-verification.md (LOOP-009)
**Pillar**: Governance / Gate Integrity
**Status**: 📋 Backlog (Unscheduled)

**Symptom**: H-06 requires a correction summary after any gate FAIL before the next commit attempt. H-07 requires escalation after two identical-class failures. No artifact cross-check was found confirming either rule is actually verified against — both rely entirely on agent self-discipline. The loop's failure mode is an agent committing without the required correction summary, or retrying the same failing approach indefinitely without escalating.

**Why not in T1-K-19**: Mechanically verifying H-06/H-07 requires instrumenting the commit-attempt → gate-result → correction-summary → next-commit chain. This is a non-trivial new mechanism with no existing tooling shape in T1-K-19's phases to attach to. The Loop Inventory itself notes (line 658): "no existing tooling shape fits cleanly; likely need dedicated audit scripts, design not yet started."

**Fix Direction**: A `post-commit` or pre-commit check that reads `gate_context_current.json` (or `.ai-review-log.jsonl`) for the previous commit's verdict, and if it was FAIL, checks whether a correction summary exists in the session notes before allowing the next commit. For H-07, track failure-class counts per session and block at two identical-class failures. Design complexity: distinguishing "same class" failures from unrelated ones.

**Cross-reference**: LOOP-009 in `docs/planning/LOOP_INVENTORY.md`. Deferred explicitly in `SPEC-loop-closure-verification.md` §8 (v1.10).

---

## HIB-089 — Wiki compilation pipeline dormant since GymBase extraction — needs retire-or-configure decision

**Date**: 2026-08-04
**Source**: Loop-inventory completeness check against SPEC-loop-closure-verification.md (LOOP-014)
**Pillar**: Tooling Hygiene / Dead Code
**Status**: 📋 Backlog (Unscheduled — product decision, not a code fix)

**Symptom**: The entire wiki compilation pipeline (`wiki_compile.py`, `wiki_lint.py`'s factual-drift check, the `DOMAIN_REGISTRY` import chain through `context_loader.py` → `architecture_checks.py`) has been dormant since this repo was extracted from GymBase. Four compounding issues confirmed in LOOP-014: (1) no `wiki_domains:` config exists, so the domain registry is empty and nothing compiles; (2) `.agent/wiki/index.md` reads "Last compiled: never / Pages: 0 / 0 ready"; (3) `wiki_lint.py`'s hardcoded `DOMAIN_REGISTRY` still lists 12 GymBase-specific domains referencing ADR files that don't exist in this repo; (4) the `DOMAIN_REGISTRY` import chain from `context_loader.py` → `architecture_checks.py` always falls back to an empty set, structurally preventing wiki content from ever reaching a review prompt.

**Why not in T1-K-19**: LOOP-013 (stale paths in `wiki_lint.py`) is fixed by Tier 1 — that's a broken tool with a clear code fix. LOOP-014 is an unconfigured subsystem requiring a product decision: either populate `wiki_domains:` with domains that actually apply to this repo (the harness's own architecture), or explicitly retire the factual-drift-check subsystem and clean up the dead code. Neither option is a bug fix.

**Fix Direction**: Decision required. Option A: define 3–5 domains relevant to this repo's own architecture (e.g. `governance_gates`, `session_lifecycle`, `bootstrap_install`, `calibration_loop`, `dream_phase`) in `.agent/config.yaml`'s `wiki_domains:`, write corresponding ADR-equivalent docs, and let `wiki_compile.py` produce useful wiki pages. Option B: remove `wiki_domains` references, mark the factual-drift-check as inapplicable to this repo, and document why in a brief ADR-style note. S0-24 (delivered 2026-06-02) partially addressed this by moving `DOMAIN_REGISTRY` to config, but the config was never populated for this repo.

**Cross-reference**: LOOP-014 in `docs/planning/LOOP_INVENTORY.md`. Deferred explicitly in `SPEC-loop-closure-verification.md` §8 (v1.10). Related: S0-24 (✅, partial — moved to config but config never populated), T1-H-06 (✅, delivered the compilation mechanism itself).

---

## HIB-090 — Schema-hardening trend consumer exists but no producer was ever built (phantom loop)

**Date**: 2026-08-04
**Source**: Loop-inventory completeness check against SPEC-loop-closure-verification.md (LOOP-015)
**Pillar**: Tooling Hygiene / Dead Code
**Status**: 📋 Backlog (Unscheduled — lowest priority of all loop-inventory findings)

**Symptom**: `harness_health.py`'s `report_schema_hardening()` reads `.agent/state/schema_hardening_trend.csv` and computes a coverage percentage and trend direction. That file does not exist, and no script anywhere in the repo writes to it. `enforce_hardened_schemas.py` (the closest-named script) is a pass/fail pre-commit gate — it prints a verdict and exits but never writes a trend CSV. The consumer degrades gracefully with `Status: DATA SOURCE MISSING`, so nobody is being actively misled.

**Why not in T1-K-19**: D4's orphaned-producer scan targets producers with no consumer. This is the inverse — an orphaned *consumer* with no producer. D4 as scoped would not catch it. Additionally, the graceful degradation means this is not actively misleading anyone, making it lower priority than any gap where false confidence is being reported.

**Fix Direction**: Decision required. Option A: build the missing producer — extend `enforce_hardened_schemas.py` (or a new companion script) to append coverage stats to `schema_hardening_trend.csv` on each run, giving `report_schema_hardening()` data to work with. Option B: remove the dead consumer code from `harness_health.py` and the references to this metric elsewhere, acknowledging the trend-tracking concept was designed but never built.

**Cross-reference**: LOOP-015 in `docs/planning/LOOP_INVENTORY.md`. Deferred explicitly in `SPEC-loop-closure-verification.md` §8 (v1.10).

---

## HIB-091 — `wiki_lint.py`'s post-fix findings were never routed to this backlog for triage

**Date**: 2026-08-07
**Source**: Pre-merge verification pass on `SPEC-loop-closure-verification.md` (T1-K-19, Tier 1 / Scenario 4q)
**Pillar**: Tooling Hygiene / Loop Closure
**Status**: 📋 Backlog (Unscheduled — triage required, 8 confirmed findings)

**Symptom**: `SPEC-loop-closure-verification.md` §6's Implementation Map carries an explicit operational step: "Run `wiki_lint.py` once post-fix and route resulting findings, if any, to the harness improvement backlog for triage," matching Scenario 4q's requirement that surfaced findings "are logged as new backlog items rather than silently absorbed into this spec's delivery." The run happened — `.agent/state/wiki_lint_findings.md` was regenerated and committed in `b6bc5d4` — but the routing half never did. No entry in this file referenced those findings until this one.

The report ([`.agent/state/wiki_lint_findings.md`](file:///c:/projects/ai-delivery-control/.agent/state/wiki_lint_findings.md), run 2026-08-04) contains **8 issues, 5 High / 3 Medium**, all against `src/scripts/review_context_universal.md`:

- **High — orphaned rules** (documented but with no executable implementation in `architecture_checks.py`): `RULE:SECRETS`, `RULE:TDD-LAW`, `RULE:DATABASE-BYPASS`, `RULE:CLEAN-CODE`, `RULE:DEPENDENCIES`.
- **Medium — stale identifiers** (referenced in review context but absent from `src/`): `requests`, `httpx`, `exc_info=True`.

This is precisely the backlog the spec predicted ("This fix will very likely surface a backlog of real orphaned-rule and stale-identifier findings that have been invisible for an unknown period... Do not treat a non-zero post-fix findings count as a regression" — §7). The findings are the fix working as designed; the gap is that they were left sitting in a state file nobody triages, which is the same silent-non-closure shape T1-K-19 exists to detect. Worth noting the report is self-evidently under-read: its `**Run Date**` field is a raw float epoch (`1785849028.3115053`) rather than a formatted date.

**Why not in T1-K-19**: T1-K-19 delivered the detection mechanism; §2's Out-of-Scope explicitly defers closing the instances it surfaces ("Retroactively writing missing tests for every gap Phase A/B surfaces... triaged and closed as separate, normal work"). Filing them here is the routing step the spec required, not a reopening of its scope. Triaging each finding — deciding whether a rule genuinely warrants an `architecture_checks.py` implementation or should be documented as advisory-only, and whether the three stale identifiers should be removed from the review context or are legitimately forward-looking — is the separate work this entry tracks.

**Fix Direction**: Triage the 8 findings as two independent batches. (1) The five orphaned rules: for each, decide implement-in-`architecture_checks.py` vs. mark-advisory; several (`RULE:SECRETS`, `RULE:DATABASE-BYPASS`) look structurally checkable, while `RULE:CLEAN-CODE` likely does not and may warrant an explicit "prose-guidance, not mechanically enforceable" annotation so it stops being re-flagged every run. (2) The three stale identifiers: `requests`/`httpx`/`exc_info=True` appear in review-context guidance for a codebase that does not use them — either the guidance is inherited boilerplate to remove, or it is deliberately forward-looking and needs an exemption mechanism. Note that whichever way (1) resolves, a permanently-nonzero findings report re-creates the "gate cries wolf" dynamic §7 already names as a known failure mode.

**Cross-reference**: `SPEC-loop-closure-verification.md` §6 (routing step), Scenario 4q (post-fix baseline run), §7 (expected-backlog residual risk). Related: HIB-089 (`wiki_lint.py`'s other subsystem — the dormant wiki compilation pipeline — is a separate, unconfigured-subsystem problem, not these findings).

---

## HIB-092 — Oversized-diff gate offers an unconditional bypass with no attempt to find a reviewable path first

**Date**: 2026-08-08
**Source**: Two live incidents in the same session — SPEC-loop-closure-verification.md's release closure (T1-K-19)
**Pillar**: Governance / Review Gate Integrity
**Status**: 📋 Backlog (Unscheduled)

**Symptom**: When a commit's diff exceeds the AI Adversarial Review gate's size ceiling, `OVERSIZED_DIFF_BLOCKED` fires and the gate's own error output hands the agent a ready-to-run bypass command (`SKIP_AI_REVIEW=1 SKIP_REASON=...`) as the suggested next step. The gate does not check, or even prompt for consideration of, whether the same commit could instead be split into smaller pieces that would each clear the ceiling and receive a genuine review. Two occurrences of the identical block, in the same session, produced opposite responses: once the commit was manually split and each piece got a real review pass; once the bypass was invoked immediately, with an evidence string that described the diff's contents rather than justifying why skipping review was safe. Nothing in the gate's own behavior favored one response over the other — it was reasoned about fresh each time, meaning the outcome depended on whether the human happened to catch it in the moment, not on the gate itself.

**Why not in T1-K-19**: this spec's tooling (Phase A/B/C, D1/D2/D4b) verifies loop closure and wiring correctness within the harness's own logic; it does not cover pre-commit gate design. Also relevant, per the external research logged earlier this session (Wauters' permission-approval study; Anthropic's own auto-mode telemetry): a bypass that's equally easy to reach for regardless of genuine necessity degrades with repeated exposure — the fix needs to live in the tooling's own structure, not in a documented rule an agent is expected to re-derive under time pressure each time the block fires. A `decisions_log.md` entry recording "prefer splitting" was considered and deliberately rejected for this reason.

**Fix Direction**: Not prescribed here — several real approaches exist and the right one needs actual design work, not a snap decision. One illustrative direction: have the gate itself judge whether the diff is separable into sub-commits that would each individually clear the size ceiling, and only present the full-bypass path when no such split exists — meaning a block only ever occurs when there genuinely is no path to a reviewed commit, not merely when the current commit happens to be large. Other directions worth weighing against that one: removing the env-var bypass for high-risk paths entirely (migrations, schema-adjacent code) regardless of size; requiring an out-of-band confirmation step that can't be supplied in the same scripted command that produced the block; or some combination. Whichever direction is chosen, the evidence field's own required content should change too — right now it accepts a description of the diff, not a justification for why review was safe to skip.

**Cross-reference**: The Register / Wauters permission-game research (logged in `decisions_log.md`, 2026-08-06) on human approval-fatigue in agentic systems. The two live incidents: `bootstrap/checksums.py` split-and-review (commit `b5aae54`) vs. the 23-file migration sweep bypass (commit `d3fd049`), both in this session.

---

## HIB-093 — upgrade.py's sidecar conflict resolution offers no triage, forcing manual review of every conflict regardless of actual risk

**Date**: 2026-08-09
**Source**: Real-world multi-version upgrade of GymBase (Gym_App) from v1.4.7 to v1.4.15
**Pillar**: Tooling Ergonomics / Installer & Upgrade Path
**Status**: 📋 Backlog (Unscheduled)

**Symptom**: When `upgrade.py` detects a framework file differs from what it expects to overwrite, it writes a `*.framework-vX.X.X` sidecar and reports the file as a generic conflict, with identical treatment regardless of *why* the file differs. This GymBase upgrade produced 45 such sidecars. Direct review of the first two revealed the tool's single "conflict" signal is masking at least three genuinely different situations: (1) the local file is byte-for-byte identical to the shipped version, and the conflict fired only because it wasn't in GymBase's original install-time baseline — `wiring_consumers.yaml`, confirmed via direct diff; (2) the local file is stale, running older framework logic with no project-specific content, where the shipped version is strictly better and safe to adopt wholesale — `architecture_checks.py`, confirmed to be *missing* the Posture Engine/HIB-080 integration entirely, meaning GymBase's own `enforcement.posture: strict` setting was silently inert for architecture checks; (3) genuine project-specific customization that must be preserved or merged deliberately. All three currently require the same manual, one-by-one human review, with no computed diff surfaced and no distinction offered up front.

**Why not in T1-K-19**: this spec's tooling verifies loop closure and wiring correctness within the harness's own logic once installed; it does not cover the installer/upgrade UX for target projects. This is a distinct problem in a related but separate part of the harness (`bootstrap/upgrade.py`).

**Fix Direction**: `upgrade.py` should perform the same three-way categorization a human currently has to do manually, before ever prompting: (1) byte-identical files auto-resolve with zero sidecar and zero prompt; (2) files that differ should have their diff computed and shown at conflict time, not left for the operator to go find and read separately; (3) a heuristic (or explicit confidence signal) distinguishing "this looks like drift from an older shipped version" from "this looks like real local customization" would let the tool recommend a default action rather than presenting all conflicts as equally undifferentiated. This does not need to be fully automated — even just *showing the diff inline in the conflict report*, rather than requiring the operator to locate and open each sidecar manually, would meaningfully reduce the toil observed here (45 files, each requiring a separate manual file-open-and-compare step).

**Cross-reference**: `SPEC-loop-closure-verification.md`'s broader theme of not trusting a mechanism's own "it worked" signal without checking what actually happened — the same principle applies here: `upgrade.py` reporting "conflict" is not itself informative about what a human should actually do next.

---

## HIB-094 — upgrade.py never re-seeds EXPECTED_REPO in check_repo.py, silently reintroducing a known-fixed placeholder on every upgrade

**Date**: 2026-08-09
**Source**: Real-world upgrade of GymBase (Gym_App) from v1.4.7 to v1.4.15
**Pillar**: Installer & Upgrade Path / Silent Regression
**Status**: 📋 Backlog (Unscheduled)

**Symptom**: `install.py`'s `Installer.copy_framework_files()` contains a one-time seeding step that replaces the literal placeholder `EXPECTED_REPO = "ai-delivery-control"` in `check_repo.py` with the target project's actual, auto-detected repo name (via `git remote get-url origin`). This seeding logic exists only in `install.py`'s class and is never called by `upgrade.py`. Confirmed directly in GymBase: after tonight's upgrade adopted the shipped `check_repo.py`, `EXPECTED_REPO` reverted to the literal `"ai-delivery-control"` placeholder — meaning the script would report a `[REPO MISMATCH]` and exit 1 on every invocation inside GymBase, despite having been correctly seeded at original install time. This is not GymBase-specific: any project whose upgrade touches `check_repo.py` will have this same value silently reset, with no error or warning at upgrade time — the script still runs, it just checks against the wrong name.

**Why not in T1-K-19**: this spec's tooling verifies loop closure and wiring correctness within the harness's own logic once installed; this is a gap in the installer/upgrade tooling itself, the same category as `HIB-093`.

**Fix Direction**: `upgrade.py` needs the equivalent of `install.py`'s seeding step — either (a) detect and re-apply the target project's repo name to `check_repo.py` whenever that file is part of an upgrade's file set, using the same `git remote get-url origin` detection `install.py` already uses correctly, or (b) treat `EXPECTED_REPO` as a genuinely project-local value that upgrade's file-copy logic should never overwrite at all — closer to how `blocked_commands.md` is already handled idempotently (`install.py` skips copying it if it already exists, to preserve customization). Option (b) is likely more robust and generalizes better: this is really an instance of a broader pattern — any value that's correctly install-time-seeded but has no equivalent upgrade-time re-seeding is at risk of the same silent regression, and `check_repo.py` may not be the only file with this exact shape.

**Cross-reference**: `HIB-093` (same session, same root category — upgrade conflict handling offering no meaningful signal to the operator). This is a more specific, confirmed instance: not just "conflicts aren't triaged," but "some resolutions are silently and specifically wrong, not merely undifferentiated."
