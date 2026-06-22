# Session Startup Rules

Always run the manual session startup sequence before any other actions:

## Step 0 — Verify Active Repository (mandatory)
Run `python .agent/scripts/check_repo.py` before reading any files or taking any actions. If the check fails, stop the session immediately and switch to the correct project in your IDE.

0. Run: `python .agent/scripts/check_halt.py`. If exit code 2: STOP. Do not proceed. Read the `.agent/state/HALT` file contents and report to the user.
   Run: `python .agent/scripts/init_session.py --agent Cline` to establish session traceability.
1. Run `git log --oneline -5` and `git branch` — establish ground truth on branch and recent work.
2. Read `.agent/state/active_context.md` — verify against git log; the file is often stale.
3. Read `.agent/state/decisions_log.md` — understand architectural/business decisions for the project.
4. Read `.agent/state/last_session_summary.md` — treat as hints, not facts if stale.
5. State in one sentence: current branch, what the last session did, what the current task is.
6. Identify the governing workflow before writing a single line of code.
