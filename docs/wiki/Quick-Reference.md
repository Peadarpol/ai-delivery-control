# Quick Reference

One-page cheat sheet for common tasks and rules.

## Session Startup

```bash
python .agent/scripts/check_halt.py
python .agent/scripts/init_session.py
git log --oneline -5
cat .agent/state/active_context.md
```

## Absolute Prohibitions (P-01–P-15)

| # | Rule |
|---|------|
| P-01 | Merge to `main`/`master` |
| P-02 | Delete migration/schema files |
| P-03 | Disable test assertions |
| P-04 | Skip writing tests for new code |
| P-05 | Install dependencies without approval |
| P-06 | Commit secrets or API keys |
| P-07 | Use unapproved package installers |
| P-08 | Import infrastructure from domain layer |
| P-09 | Access database sessions directly (bypass Repository/UoW) |
| P-10 | Modify `.env` without documenting |
| P-11 | Commit/push without local verification |
| P-12 | Use `git add .` or `git add -A` — named files only |
| P-13 | Stage agent-generated files or logs |
| P-14 | Git operations in wrong repository |
| P-15 | Direct commits to CI/CD branches |

## Escalation Triggers (Stop and Ask)

- Delete or rename >1 file
- Drop/truncate database table
- Modify tenant/multi-tenant isolation
- Modify auth/RBAC code
- Deploy to staging/production
- Modify CI/CD pipelines
- Blocked at same state 2+ times

## Workflows

| Task | Workflow |
|------|----------|
| New feature | `/feature-implementation` |
| Bug | `/bug-fix` |
| Architecture | `/architect` |
| Schema/migration | `/dba` |
| Security | `/security` |
| Performance | `/perf` |
| Tests | `/qa` |
| Release | `/release` |
| Business analysis | `/business-analyst` |
| Spec→tasks | `/project-manager` |

## Gate Verdicts

| Verdict | Meaning |
|---------|----------|
| PASS | Code meets all requirements |
| PASS_FAST | Trivial diff; LLM call skipped |
| WARN | Issues but can ship |
| FAIL | Code cannot ship; fix it |
| FAIL_OPEN | Provider unavailable; proceed |

## Session Close

```bash
vim .agent/state/active_context.md
vim .agent/state/decisions_log.md
vim .agent/state/last_session_summary.md
# Append to session_ledger.jsonl
```

## Customization Surfaces

| What | File |
|------|------|
| Add review rules | `src/scripts/review_context_project.md` |
| Custom skills | `.agent/skills/your-skill/` |
| Architecture | `.agent/config.yaml` → `architecture:` |

## Essential Config Keys

- `tech_stack.language`, `core_framework`, `db_engine`
- `model_routing.review_provider`, `review_model`
- `capabilities.*` (shell commands)
- `paths.*` (project structure)
- `domain_constraints` (inviolable rules)
- `architecture.layers` (layer boundaries)

---

*Full reference: [Glossary](Glossary) · [Governance Rules](Governance-Rules)*