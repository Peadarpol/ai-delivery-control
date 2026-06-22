# Session Close Rules

Before ending any task/session, follow the structured session close protocol:

1. **Review Task Magnitude Auto-Classification** in `session.json`. You **NEVER downgrade** a session from `major` to `micro` without explicit, documented justification in `session.json` (`task_magnitude_override_reason`).
2. **Run Context Compaction** (`python .agent/skills/meta/validate.py`) whenever the rolling spent has passed 80% of its budget ceiling.
3. **Complete Compaction/Handoff Template** `.agent/skills/meta/context-compaction.md` in full prior to close.
4. **Update `.agent/state/active_context.md`** — current task, branch, blockers, immediate next steps.
5. **Update `.agent/state/decisions_log.md`** — document all technical, design, and business decisions made during this session. Archival check: if `decisions_log.md` exceeds 150 lines, archive the oldest entries to `.agent/state/decisions_log_archive.md` before adding new ones.
6. **Update `.agent/state/last_session_summary.md`** — what was done, what's incomplete, decisions deferred.
7. **Append a row to `.agent/state/session_ledger.jsonl` and `.agent/state/session_ledger.md`** — session ID, date, action summary.

## Session Close — Cline-Specific (Outcome Override Write)

Cline has no native Stop hook. Before ending any Cline task, write the following fields to `.agent/state/session.json` in addition to the standard session close steps:

```json
{
  "outcome_override": "success | partial | abandoned | escalated",
  "outcome_override_source": "agent_override",
  "outcome_override_note": "One-sentence summary."
}
```

This is the same pattern as Gemini CLI (HIB-GEMINI-01). It is the only way `infer_and_close_previous_session()` gets the same close fidelity as a Claude session with the Stop hook.
