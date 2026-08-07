# Independent Loop-Closure Audit Findings

This document enumerates the feedback loops found across `.agent/scripts/`, `src/scripts/`, `.agent/evals/`, and `.agent/workflows/*.md`, independently verifying if producers and consumers genuinely connect via code.

## 1. Gate Rebuttal Evaluation (`gate_rebuttal.json`)

- **Producer**: A human or agent, scaffolded by `src/scripts/ai_review.py` (lines 1390-1400) which emits a template containing `original_fail_session_id`, `original_fail_timestamp`, `normalized_diff_hash`, and `findings`.
- **Consumer**: `src/scripts/rebuttal.py` (`DeveloperRebuttal` schema).
- **Condition for Closure**: The fields in the generated JSON must exactly match the required fields in the `DeveloperRebuttal` Pydantic model (`original_fail_session_id`, `original_fail_timestamp`, `normalized_diff_hash`).
- **Status Verdict**: **Working**. The scaffold printed by `ai_review.py` correctly populates the mandatory `timestamp` and `diff_hash` fields expected by `rebuttal.py`.
- **Pressure Test (Verification)**: To assert this stays working, a test should execute `ai_review.py` to trigger a simulated failure, capture the stdout scaffold, write it directly to `.agent/state/gate_rebuttal.json` (filling in dummy evidence), and invoke `python src/scripts/ai_review.py --rebuttal`. The assertion must verify `_run_rebuttal` returns 0 (or appropriately evaluates the findings without raising a `ValidationError`).

## 2. Spec Grade Card (`spec_grade_{SPEC_ID}.md`)

- **Producer**: `.agent/scripts/check_spec.py` (`write_spec_grade_card` function).
- **Consumer**: None found. `FRAMEWORK_BACKLOG.md` mentions that a `/ba` workflow Phase 3 should read this, but there is no `/ba` workflow or any script referencing this file.
- **Condition for Closure**: A workflow or script must read `.agent/state/spec_grade_{SPEC_ID}.md` and utilize the `Verdict` and `Clarity Score` to guide agent actions.
- **Status Verdict**: **Broken / Partial (Orphaned)**. The producer reliably generates the grade card, but the feedback is never consumed.
- **Pressure Test (Verification)**: N/A until a consumer is built. Once built, a test should verify that a spec failing a criterion (e.g., scoring < 10) causes the consumer to loop back for a revision rather than proceeding.

## 3. Co-Change Reconciliation Report (`co_change_reconciliation_report.md`)

- **Producer**: `.agent/scripts/co_change_reconciler.py` (writes to `.agent/state/co_change_reconciliation_report.md`).
- **Consumer**: None found.
- **Condition for Closure**: A script or human must be prompted to read the report and reconcile the out-of-sync files.
- **Status Verdict**: **Broken / Orphaned**. The producer writes the report, but no automated mechanism reads it. 
- **Pressure Test (Verification)**: N/A until a consumer is established.

## 4. Golden Dataset Regression (`golden_dataset.yaml`)

- **Producer**: `.agent/evals/incident_to_eval.py` (interactive wizard that appends an entry with `id` and `test_reference`).
- **Consumer**: `.agent/evals/regression_runner.py` (loads `golden_dataset.yaml`, maps over `entries`, and calls pytest on `test_reference`).
- **Condition for Closure**: The dictionary structure `{ "entries": [ { "id": "...", "test_reference": "..." } ] }` must be consistent between both scripts.
- **Status Verdict**: **Working**. `incident_to_eval.py` writes `test_reference`, and `regression_runner.py` retrieves it exactly (via `entry.get("test_reference", "")`).
- **Pressure Test (Verification)**: An automated test should invoke `incident_to_eval.py` (mocking stdin) to create a dummy entry pointing to an intentionally failing mock test, then run `regression_runner.py --run`, asserting that it exits non-zero and flags the precise `id` added.

## 5. Dream Proposals Analysis (`dream_proposals/`)

- **Producer**: `.agent/scripts/distill_dream.py` (generates proposals based on ledger/harness events).
- **Consumer**: `.agent/scripts/harness_health.py` (parses the proposals for staleness checks).
- **Condition for Closure**: The producer must write the metadata fields expected by the consumer.
- **Status Verdict**: **Working (Restored by v1.4)**. The loop was previously broken because `distill_dream.py` failed to write the `Generated:` field required by `harness_health.py` for staleness parsing, masking proposals from detection. (Documented in v1.4 fix).
- **Pressure Test (Verification)**: A test should generate a mock proposal via `distill_dream.py` forcing a date > N days ago, and assert that `harness_health.py` outputs a staleness warning for that specific proposal.

## 6. Wiki Domain Compilation (`.agent/wiki/*.md`)

- **Producer**: `.agent/scripts/wiki_compile.py` (compiles knowledge into `.agent/wiki/{domain_name}.md` and supposedly exposes `DOMAIN_REGISTRY`).
- **Consumer**: Supposedly `src/scripts/ai_review.py` (the docstring in `wiki_compile.py` claims: `ai_review.py does: from wiki_compile import DOMAIN_REGISTRY`).
- **Condition for Closure**: `ai_review.py` must import `DOMAIN_REGISTRY` or read `.agent/wiki/*.md` files.
- **Status Verdict**: **Broken**. `ai_review.py` does not contain `DOMAIN_REGISTRY` nor does it import `wiki_compile.py`. The wiki files are generated but ignored by the review gate.
- **Pressure Test (Verification)**: N/A until the consumer actually imports the registry and leverages the wiki contexts in its LLM prompts.

## 7. Session Ledger Retention (`session_ledger.jsonl`)

- **Producer**: `src/scripts/init_session.py` (and state persistence routines) appending JSONL objects with a `date` field.
- **Consumer**: `.agent/scripts/retention_cleanup.py` (archives old sessions).
- **Condition for Closure**: The archival target definition `{"file": STATE_DIR / "session_ledger.jsonl", "date_field": "date"}` must map to a field that actually exists in the producer's JSON structure.
- **Status Verdict**: **Working**. The JSON appended to the ledger correctly includes the `date` key, and `retention_cleanup.py` extracts it correctly.
- **Pressure Test (Verification)**: Create a mock `session_ledger.jsonl` with one entry dated today and one dated 100 days ago. Run `retention_cleanup.py` with `session_ledger_retention_days` = 90. Assert that the resulting `session_ledger.jsonl` contains exactly 1 line (today's) and the archive directory receives the older entry.
