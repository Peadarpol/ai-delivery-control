# Workflow-First Rules

Before any task involving code changes across more than one file or layer:

1. **Name the governing workflow** from `.agent/workflows/`. If none fits, say so and ask.
2. **Announce it** — e.g. "This is a `/feature-implementation` task, starting at Phase 2.5."
3. Follow the workflow phases in order. Direct user instructions do not override workflow phases.

**Quick-task exception**: Single-file fixes, docs edits, config tweaks — proceed directly.
**Ambiguous scope**: Ask before starting, not after three files have changed.

| Task type | Governing workflow |
|---|---|
| New feature or requirement | `/feature-implementation` |
| Production bug | `/bug-fix` |
| Architecture decision | `/architect` |
| Schema / migration change | `/dba` |
| Security concern | `/security` |
| Performance issue | `/perf` |
| Tests only | `/qa` or `/test-engineer` |
| Release / changelog | `/release` |
