# Absolute Prohibitions

| # | Never do this |
|---|---|
| P-01 | Merge to `main`/`master` |
| P-02 | Delete migration/schema files |
| P-03 | Disable or weaken test assertions to make tests pass |
| P-04 | Skip writing tests for new functionality (TDD Iron Law) |
| P-05 | Install new dependencies without listing them for user approval |
| P-06 | Commit secrets, API keys, or credentials |
| P-07 | Use unapproved package installers (always use project-specific package manager) |
| P-08 | Import infrastructure layer from domain/business layers |
| P-09 | Access database sessions directly, bypassing Repository/UoW (where pattern is active) |
| P-10 | Modify `.env` files without documenting the change |
| P-11 | Commit or push without completing local verification first — **CI is not a substitute for local verification. If you cannot verify locally, stop and say so. Do not commit and push hoping CI will catch it.** |
| P-12 | Use `git add .` or `git add -A` — always stage named files only |
| P-13 | Stage agent-generated files or log files (`AGENTS.md`, `harness_events.jsonl`, `session_ledger.jsonl`, `dream_phase_state.json`, brain files, session logs, etc.) in git commits |
| P-14 | Perform any git add, commit, merge, or push without verifying the active repository matches the intended project. |
| P-15 | Direct commits to deployment/devops branches for CI/CD fixes: Create a short-lived branch, merge to devops, then merge back to active feature branch |
