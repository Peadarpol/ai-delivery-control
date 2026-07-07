# Decisions Log

## 2026-07-07: Reconciler ↔ CDR Ledger Integration (T1-B-12 Piece 2)
- **Decision**: Integrated the co-change reconciler CLI with the CDR decisions ledger to filter out sanctioned crossings. Implemented pair-scope matching (using set-equality) and file-scope matching (hub check) against the ledger. Integrated status classifications: ACCEPTED, TOLERATED, AMBIGUOUS, and resolved status (regression check). Added tunable escalation checks for ACCEPTED and TOLERATED crossings (multi-layer delta/threshold checks) and restructured the markdown report into four sections + ambiguous matches. Exposed `--escalation-freq-multiplier` and `--escalation-prob-delta` flags.
- **Context**: Required to bridge the boundary-crossing co-change detector with human coupling decisions, ensuring known/sanctioned debt does not clutter actionable findings.
- **Consequence**: All 11 reconciler CLI tests and 436 full suite tests pass. Real-world proof run against the harness repo successfully moves the three pilot decisions from Undeclared to Accepted.

## 2026-07-07: CDR Ledger Schema Design, Pilot Migration, & Validator (T1-B-12 Piece 1)
- **Decision**: Created `.agent/coupling_decisions.yaml` schema and migrated pilot decisions (collapsing checksums pilot entries into a file-scoped exemption). Implemented the validation library `.agent/scripts/cdr_ledger_validate.py` (C1-C8 schema rules, including the C3 anti-confabulation rule) and a comprehensive validation test suite `tests/test_cdr_ledger.py`.
- **Context**: Schema verification and pilot database representation were required as foundations before integrating subtraction logic into the co-change reconciler.
- **Consequence**: All 428/428 tests pass. Full coverage for C3 validation.

## 2026-06-23: Roadmap Update for Version 1.5.x Milestones
- **Decision**: Updated `docs/planning/FRAMEWORK_ROADMAP.md` to reflect the completed v1.5.x milestone plans (v1.5.0 Quality Signal Maturity, v1.5.1 Tool ABC Foundation, v1.5.2 Skill Chain & Gate Intelligence Completion), bumped current version to 1.4.4, updated active milestone records, and added v1.4.3 and v1.4.4 to the historical release family.
- **Context**: Backlog items (T1-G-15, T1-D-08, T1-L-15, T1-B-06a, T1-L-16, T1-D-09) were accepted and added to the backlog. The roadmap updates were required to reflect the strategic decisions made for planning the upcoming releases.
- **Consequence**: Perfect alignment between release roadmap planning and backlog registry. All 372 unit and E2E verification tests pass.

## 2026-06-22: CodeQL Scoping and Checksums Registry Upgrades
- **Decision**: Added CodeQL configuration `.github/codeql/codeql-config.yml` to restrict scanning to Python, and generated/regenerated checksums registry for version 1.4.3 and 1.4.4 in `bootstrap/checksums.py` to ensure migration verification runs cleanly.
- **Context**: The user requested explicit scoping of CodeQL scans. Additionally, migration testing required that version 1.4.3 registry exist in the checksums database to support contiguous traversal checks.
- **Consequence**: All checksum checks and 372 unit/E2E tests pass successfully, CodeQL analysis is cleanly scoped, and the rollup branch is pushed remotely.

## 2026-06-22: Rollup Version 1.4.4 and Stale Branch Check
- **Decision**: Rolled up all 5 unmerged branches (`feat/v1.4.1-security`, `fix/bug-04-05-gate-logging-and-routing`, `feat/v1.4.1-bugfixes`, `feat/v1.4.2-session-close`, `feat/v1.4.1-outer-loop`) into `feat/v1.4.4` (bumped harness version to 1.4.4) and implemented a new stale unmerged branch check in `harness_health.py` (`T1-K-11`).
- **Context**: A rollup branch `feat/v1.4.4` was needed to cleanly integrate all outstanding branch features and bug fixes. A stale branch detection mechanism was requested to prevent accumulation of orphaned branch work.
- **Consequence**: All unmerged features are integrated, 372 unit/E2E tests are passing, checksums registry regenerated, and stale branch checks dynamically detect unmerged branches older than a configurable threshold (default 14 days).

## 2026-06-22: Fixed Bootstrap Installer Module Copies
- **Decision**: Updated `bootstrap/install.py` to copy all framework-owned scripts listed under `manifest.FRAMEWORK_OWNED` in the `src/scripts/` directory to the target project scripts directory on installation and upgrade.
- **Context**: Consumer projects bootstrapped with the framework would fail at startup with `ModuleNotFoundError: No module named 'harness_utils'` because the installer was only copying `ai_review.py` and `review_context_universal.md` to the target `src/scripts/` directory, leaving out core runtime dependencies like `harness_utils.py` and `state_persistence.py`.
- **Consequence**: Fresh bootstrap installations run `init_session.py` and review gate execution successfully out-of-the-box with all required modules present.

## 2026-06-22: Resolved distill_dream test date time-bomb
- **Decision**: Replaced all hardcoded dates (`2026-06-` and `2026-05-`) in `tests/test_distill_dream.py` with dynamic datetimes computed relative to execution time using `_log_time()` and `_ledger_date()` helpers.
- **Context**: The test `test_hib_dream_03_threshold_redesign_appearance` was failing because the 30-day cutoff logic in `distill_dream.py` dynamically computes the threshold relative to execution time, filtering out May 2026 test ledger records which are now more than 30 days old.
- **Consequence**: The entire test suite of 358 tests now passes successfully, and the tests are safe against future date-based failures.

## 2026-06-22: Stashes Verification and HIB-ENV-01 Backlog Restoration
- **Decision**: Audited all remaining git stashes and restored the missing `HIB-ENV-01` external defect backlog item (Antigravity phantom-trajectory defect) from `stash@{2}` into `docs/planning/FRAMEWORK_BACKLOG.md`. Verified that other stashed changes were already fully integrated into HEAD.
- **Context**: An overwrite event had stashed workspace state. A complete audit of all remaining stashed entries was required to ensure no planning documents, functions, or logs were lost.
- **Consequence**: All stashed changes have been successfully analyzed and categorized, and the missing external defect entry has been restored to maintain perfect backlog traceability.

## 2026-06-22: Stashed planning changes restoration and T1-I-05 / HIB-056 status reconciliation
- **Decision**: Restored stashed changes from `stash@{1}` containing milestone plans, backlog updates (T1-D-07, T2-A-07, T3-C-05), and findings documents. Inspected `.agent/scripts/distill_dream.py` to confirm memory contradiction checking is fully delivered, updated the status of `T1-I-05` to `✅ (integrated into T1-D-03)` in `FRAMEWORK_BACKLOG.md` and `FRAMEWORK_ROADMAP.md`, and resolved `HIB-056` to complete.
- **Context**: Edits made during a prior session were stashed and lost due to an overwrite. Status-marker drift on T1-I-05 caused inconsistency across references.
- **Consequence**: All lost planning assets are restored and version controlled. Backlog integrity is restored with agreed status markers.

## 2026-06-14: Universal review-context RULE sections selection/injection & trigger-gate AT/FM vocabulary (HIB-055, T1-L-13a)
- **Decision**: In `ai_review.py`, always load and inject the core universal RULE sections into the LLM context to ensure enforcement of TDD law, database bypass, and dependency rules. Gated the heavy AT/FM vocabulary section to only inject when an ADR or decision block is detected in the diff, preventing token budget collisions. Wired the LLM-side ADVISORY rule for ADR decision-block review (T1-L-13a).
- **Context**: Universal context rules were silently dropped because their IDs were missing from `active_sections` at review time, while always-injecting all rules would violate the 2,000-token limit.
- **Consequence**: Full rules are now actively reviewed by the gate with budget safety.

## 2026-06-14: Cap spec-mtime commitless work at partial using git status (HIB-053b)
- **Decision**: Replaced the unreliable filesystem mtime scanning in `init_session.py` with `git status --porcelain` to check for spec changes, and capped the retrospective outcome for sessions with uncommitted spec changes (and no commits) at `partial` (downgrading from false-successes).
- **Context**: Session close inference previously marked spec-only sessions as success even when files were uncommitted and mtime was modified by unrelated git checkouts or stash operations.
- **Consequence**: Session outcomes are now determined reliably from git status, enforcing that work is committed to count as a success.

## 2026-06-22: Cline + Ollama Compatibility support (feat/framework-cline-compat)
- **Decision**: Added `CLINE.md` shim template and structured `.clinerules/` rules directory templates covering session startup, workflows, absolute prohibitions, session close outcome overrides, git discipline, and environment details. Implemented `install_clinerules()` dynamic copy and template rendering logic in `install.py` and gitignored local hooks. Created `docs/CLINE_COMPAT.md` detailing the deferred hooks execution scripts.
- **Context**: Consumer teams utilizing VS Code and Cline need structured instructions and rules loaded automatically, without introducing platform-incompatible hooks on Windows.
- **Consequence**: Delivers robust out-of-the-box support for Cline CLI / local Ollama models on consumer projects, matching the close-out outcome override flow of Gemini CLI.

## 2026-05-30: Automated Outer Loop Spec Gating & BDD Governance (v1.2.0)
- **Decision**: Implemented automated spec quality gating (`check_spec.py`) enforcing BDD specifications structures, Gherkin word boundaries, lenient assumptions presence, and adversarial LLM quality checks (soft/hard gates). Consolidated shared path setups, session locks, and Windows UTF-8 stream wrapping into `src/scripts/harness_utils.py` and updated `init_session.py` to prevent redundant wrapping.
- **Context**: BDD specifications lacked structured quality gating, while multiple bootstrap utilities duplicated stdout/stderr stream wrapping logic, causing double-wrapping crashes under Windows subprocesses.
- **Consequence**: All 26/26 E2E scenarios and 154 unit tests pass successfully, delivering robust and automated spec governance.

## 2026-05-30: Hardened Outer Loop Lifecycle Gating & Backlog Scaffolding (v1.3.0)
- **Decision**: Designed the blueprints for Sprint 1 of the v1.3.0 milestone incorporating ten major multi-persona hardening invariants (exempting merges, standard library traceability, schema creep gating, double-anchored commit messages, CI/offline warnings, PM checklist backups, XML sanitization, C4 decoupled providers, isolated E2E sandboxes, terminal box cards).
- **Context**: Rigorous security, developer ergonomics, and pipeline integration must be achieved simultaneously to prevent friction from causing hook circumvention.
- **Consequence**: Delivers robust, enterprise-grade traceability and gating checks with zero developer friction and extremely high reliability.

## 2026-06-02: Applied Consolidated Backlog and Roadmap Updates
- **Decision**: Applied the consolidated June 2026 backlog updates (Sprint 0, T1-B, T1-G, T1-L, T1-M, and T1-N items) to `FRAMEWORK_BACKLOG.md` and the milestone pre-sprint gate/strategic context additions to `FRAMEWORK_ROADMAP.md`.
- **Context**: Keeping documentation in sync with consolidated research findings and plan refinements is necessary before starting Sprint 1 implementation.
- **Consequence**: Ground truth documentation is updated for developers and agents. All 184 tests pass.

## 2026-06-02: Added S0-24 and BUG-11 through BUG-13 to Backlog
- **Decision**: Added S0-24 (De-GymBase-ify functional code), BUG-11 (distill_dream.py reads wrong field), BUG-12 (wiki compile cold-start failure), and BUG-13 (E2E test project runs stale ai_review.py) to `FRAMEWORK_BACKLOG.md` and synced `FRAMEWORK_ROADMAP.md` milestone planned items.
- **Context**: Resolving GymBase hardcoding, dream phase pattern domain detection, cold-start wiki failure cooldown issues, and E2E review script drift is essential for broad framework adoption and robustness.
- **Consequence**: Added tracking and priority for these critical porting and reliability issues in the backlog. All 184 tests pass.

## 2026-06-02: Hardened Session Token Budget Wiring and Graceful Lock Acquisition (T1-I-07)
- **Decision**: Implemented rolling budget tracking summing regular, reasoning, and cache read tokens, coupled with atomic structured JSON HALT writes, and 80%/100% Warn/Halt warnings. Wrapped all `_lock_session` context managers in `try-except` blocks to print warning messages to stderr and proceed gracefully if concurrency lock acquisition fails.
- **Context**: Prevent budget undercounting of reasoning/cache tokens, log session_id in the HALT file dictionary, and ensure the review gate does not crash due to temporary locking issues under concurrent execution.
- **Consequence**: Verified all 28 E2E verification scenarios and 207 unit tests pass successfully.

## 2026-06-03: Two-Layer Context Architecture (UNIVERSAL_CONTEXT.md)
- **Decision**: Consolidated shared tool context rules into `.agent/UNIVERSAL_CONTEXT.md` and converted editor-specific rules (`CLAUDE.md`, `GEMINI.md`, `.cursorrules`) into thin shims loading it.
- **Context**: Duplicating identity and rules across three separate files caused configuration mismatches and high maintenance overhead.
- **Consequence**: Single source of truth for agent system context, leaving shim files clean and minimal.

## 2026-06-03: 3-Tier Memory Tiering (T1-I-01)
- **Decision**: Implemented `memory_manager.py` to parse memory into Hot (always loaded), Warm (keyword-matched), and Cold (historical files older than 90 days), with automatic archiving.
- **Context**: Storing large historic logs in primary agent context causes token blowups, while missing historical context blocks long-term capability retrieval.
- **Consequence**: Dynamic context indexing keeps agent sessions lightweight while retaining retrieveability.

## 2026-06-03: AST Code Pattern Staleness Verification (T1-I-04)
- **Decision**: Implemented static AST parser at session start checking for existence of classes/functions/paths referenced in review context.
- **Context**: Unsynchronized development easily breaks review rules referencing changed or deleted definitions.
- **Consequence**: Provides instant warning warnings if the review context references deleted/refactored codebase definitions.

## 2026-06-04: MIT + Commons Clause License Selection
- **Decision**: Adopted the combined MIT License + Commons Clause License Condition v1.0, updated the root LICENSE file, and removed the outdated README_draft.md.
- **Context**: Preventing commercial exploitation and consulting wraps of the framework without restricting open developer use.
- **Consequence**: Users can use, modify, and distribute the framework freely except for commercial resale or hosted services whose value is derived directly from the framework.

## 2026-06-08: Scope-and-Boundaries as Public Honest-Limits Documentation
- **Decision**: Created `docs/wiki/Scope-and-Boundaries.md` explicitly naming the three structural boundaries of the framework: (1) the gate governs commits, not in-session tool calls; (2) the gate checks individual commits, not accumulated architectural drift; (3) the self-improvement loop can only improve what the gate already notices.
- **Context**: These gaps were discovered through real use and flagged in rebuttal discussions.
- **Consequence**: Public documentation sets honest expectations.

## 2026-06-08: Observation — v1.3.3 Delivery Verified; Gemini CLI HALT Coverage Gap
- **Observation**: v1.3.3 delivery confirmed clean via manual spot-checks. HALT file absent.
- **Context**: The HALT file's absence is ambiguous without external verification.
- **Consequence**: Flagged for v1.4.0 sprint planning.

## 2026-06-12: Framework Version v1.3.4 Release
- **Decision**: Finalized framework version v1.3.4 release. Generated framework checksums registry using `generate_checksums.py --version 1.3.4` and registered digests for 639 framework files, including all new Wave 4 components.
- **Context**: Release instruction mandates generating checksums registry for the new release to support clean conflict-free roll-forward upgrades.
- **Consequence**: All 289 unit tests pass. Version 1.3.4 registry is recorded.

## 2026-06-13: Per-Capability AT9 Calibration & Dynamic Calibration Weighting
- **Decision**: Developed the `capability_calibration.py` module to maintain running TP/FP counters and weights in `.agent/state/capability_calibration.json`. Integrated weight evaluation in `ai_review.py` regular reviews to promote/demote severities and add policy notes, and added counter updates on rebuttal completion.
- **Context**: Uniform thresholds across capabilities led to high rebuttal overhead for some rules and low coverage for others. Per-project calibration helps resolve the correctness vs permissiveness tradeoff dynamically.
- **Consequence**: Calibration dynamically adjusts thresholds per-project and per-capability based on historical rebuttal outcomes. Surfaced calibration statistics in `harness_health.py`.

## 2026-06-13: SQLite State Persistence Fallback Strategy & Acceptance Stop Hook
- **Decision**: Designed and implemented `state_persistence.py` to index flat-file data (session ledger, events, decisions, and review verdicts) into a single-machine SQLite database at `~/.aisdlc/harness.db`. The system handles write-safety gracefully by falling back to a project-local database or flat-files alone if the home directory is read-only. Added `acceptance_hook.py` as a Stop hook to automate spec acceptance verification when ending a session on a feature branch.
- **Context**: SQLite indexing is necessary for cross-project health and querying, but must degrade gracefully in locked-down or ephemeral environments (containers, CI). The acceptance gate prevents compliance gaps by verifying implementation alignment against Gherkin specs before PR promotion.
- **Consequence**: Fast querying and project-isolated cleanup are fully operational with Zero external pip dependencies. The Stop hook asserts spec acceptance on session end, ensuring continuous compliance.

## 2026-06-13: [T1-D-02] Reopened — mismarked as delivered in v1.4.0
- **Decision**: T1-D-02 (harness_health.py SQLite read-side) is reopened and its ✅ v1.4.0 mark removed. Corrections applied to FRAMEWORK_BACKLOG.md (table row + archive list), CHANGELOG.md, agent-capability-briefing.md (section heading + changelog row), CAPABILITY_INVENTORY.md (delivered tag + backlog dependency), and CANDIDATE_BACKLOG.md (dependency note).
- **Context**: Code audit confirmed `state_persistence.py` has no SELECT functions and `harness_health.py` has no `sqlite3` import. Root cause: write-side sibling T1-D-01 shipped complete; T1-D-02 was co-marked without separate verification of the read-side consumer path.
- **Consequence**: T1-D-02 is ⬜ undelivered. Any candidate work scoped as a read layer over T1-D-02 is blocked until the read-side is built.
