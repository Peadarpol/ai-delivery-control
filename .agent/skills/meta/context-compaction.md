# Context Compaction Meta-Skill

This meta-skill provides instructions on compacting the active context when the session token budget is exhausted or near ceiling (>= 80%).

## Target Structure

Compaction MUST produce an updated handoff template containing:

### 1. Completed Tasks
- Summarize all completed work with exact details and files modified.
- Include verification outputs or links to automated test results.

### 2. Verification Findings (mandatory — ALL severities)
- List **every** finding produced by any verification tool run this session: gate
  verdicts, `ai_review` findings, test failures, and `bandit` / `gitleaks` /
  `pip-audit` / lint / type warnings — **including non-blocking WARN and
  MEDIUM-severity items**.
- For each finding record: source tool, severity, a one-line description, and
  resolution status (fixed / accepted / deferred â†’ where tracked).
- **If verification produced no findings, you MUST write
  `None — verification ran clean` explicitly.** An absent or empty section is a
  defect, not a pass — the reviewer cannot distinguish "nothing to report" from
  "forgot to report" unless you state it.
- **Why this section exists:** it is the structural enforcement of prohibition
  H-04 (selective summary). Findings cannot be silently dropped from a handoff
  when the handoff has a required slot for them — omission shows up here as a
  missing required field, rather than depending on the author remembering not to
  omit at the moment of writing.

### 3. Architectural Decisions
- Document all core technical and business decisions made during this session.
- Record any new database schemas, capability route mappings, or security invariants.

### 4. Failed Experiments
- Detail any approaches that were attempted but rejected.
- Explain the precise technical reasoning behind the rejection to avoid regression loops.

### 5. Remaining Tasks
- Outline the concrete next steps required to achieve the milestones.
- Specify the exact files to target and the proposed implementation.

### 6. Open Questions
- Detail any blocking issues or design choices that require feedback from the human developer.

---

## Handoff Summary — 2026-07-07 (Session Close)

> _Authored under the prior five-section template (before the mandatory
> **Verification Findings** slot was added 2026-07-08). Its section numbering
> reflects that earlier structure._

### 1. Completed Tasks
- **Reconciler â†” CDR Ledger Integration (T1-B-12 Piece 2)**:
  - Added `load_ledger` helper to `.agent/scripts/cdr_ledger_validate.py`.
  - Updated arguments in `.agent/scripts/co_change_reconciler.py` to expose tunable escalation parameters.
  - Implemented ledger loading, schema validation, pair-scope matching (using set-equality), and file-scope matching (hub check).
  - Categorized crossings into Undeclared, Escalated, Tolerated, Accepted, and Ambiguous sections, writing a restructured Markdown report.
  - Added 9 E2E and unit tests in `tests/test_co_change_reconciler.py` covering all integration requirements.
  - Ran pytest suite with all tests (436/436) passing successfully.
  - Verified primary proof run (defaults) and secondary proof run (low threshold) against the harness repository.

### 2. Architectural Decisions
- Restructured report format to isolate accepted/tolerated crossings from undeclared ones and highlight escalated crossings where metrics worsen.
- Used set comparison `{files[0], files[1]} == {file_a, file_b}` to handle pair-scope exemptions order-independently.
- Utilized `--escalation-freq-multiplier` (default 1.5) and `--escalation-prob-delta` (default 0.15) parameters to classify escalated entries.

### 3. Failed Experiments
- None.

### 4. Remaining Tasks
- Brownfield baseline bulk-population tool (Piece 3).

### 5. Open Questions
- None.




## Handoff Summary — 2026-07-07 (Session Close)
### 1. Completed Tasks
- Swept HIB items and updated tracking files.
- Fixed HIB-060 in co_change_core.py.
### 2. Verification Findings
- None — verification ran clean.
### 3. Architectural Decisions
- HIB ghost items archived to main backlog.
### 4. Failed Experiments
- None.
### 5. Remaining Tasks
- T1-E-04, T1-E-03, T1-B-11.
### 6. Open Questions
- None.
