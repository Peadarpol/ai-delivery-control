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
