# Git Discipline

## Staging rules
- **Always stage named files only.** `git add .` and `git add -A` are prohibited (G-02).
- **Never stage files outside the repository root.**
- **Never stage agent-generated files** (§9.1 git discipline): `AGENTS.md`, brain files, session logs, `active_context.md`, `decisions_log.md`, `last_session_summary.md`, `session_ledger.md`.
- **Documentation commits with code.** All documentation updates (walkthrough, task files, harness logs) must be committed in the same commit as the code they describe — never a follow-up commit. Prepare everything locally first, then commit once.

## Verification before commit
- **Verification is mandatory before every commit and push. It is never optional and never skipped to save time.**
- Verification must be run against a **clean state** — not an already-seeded or in-progress local database.
- If you cannot run the verification suite (environment broken, tests hanging, tool unavailable), **stop and report**. Do not commit. Do not push. Do not defer to CI.
- CI failure is not a substitute for local verification. A commit or push made without completing local verification is a governance breach.

## Push timing
Before any `git push` to the devops/main branch, check if the deployment pipeline is already in progress from another push. Stage your changes locally and coordinate to prevent conflicts.

## Branch Strategy for CI Fixes
When a CI/CD pipeline fails after a push:
1. Create a short-lived fix branch: `git checkout -b fix/ci-description`
2. Implement the fix
3. Merge to the build branch
4. Merge back to the active feature branch to prevent divergence
5. Delete the fix branch

**Exception**: Trivial one-line typo fixes may be made directly with a warning acknowledged in the commit message: `[direct-devops: trivial]`

## Branching Conventions
All framework work must develop on dedicated feature branches before merging via Pull Request:
`feat/framework-{item-id}-{short-description} → PR → main`

## Gate Governance Escalation Hierarchy
When the AI review gate returns a `FAIL` verdict, agents and developers MUST adhere to the following escalation hierarchy:
1. **Fix the actual problem** (First Priority): Always attempt to resolve the underlying code quality, security, or architectural issue directly.
2. **Structured Rebuttal** (Governed Contest): If a finding is believed to be a false positive or is specifically required, create `.agent/state/gate_rebuttal.json`. 
   - **Agent Mandate**: **Agents MUST NOT self-execute the `--rebuttal` command.** Writing the rebuttal file and presenting the argument to the human operator is the agent's sole action. The human reviews the argument and explicitly runs: `python src/scripts/ai_review.py --rebuttal`.
   - **Rebuttal Evidence Checklist**: Assertions without verifiable facts will be rejected. Every rebuttal entry must satisfy this checklist:
     1. Quote the actual commit message verbatim.
     2. State the spec ID and its current status (e.g., SPEC-123, status APPROVED).
     3. Cite the specific acceptance criteria the diff implements.
     4. Describe what the diff actually contains — including file names, line count, and the exact nature of the change.
3. **Structured SKIP_REASON bypass** (Acknowledged Override): Only as a last resort in emergencies, use `SKIP_AI_REVIEW=1` with a structured bypass JSON to step aside.
