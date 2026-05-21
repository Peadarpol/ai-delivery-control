# AI Delivery Control

**You govern. Agents deliver.**

Most AI coding frameworks optimise for autonomy — agents run until criteria pass.
AI Delivery Control optimises for accountability — humans remain in the loop at
every consequential decision point.

Three checkpoints. Not zero.

| Checkpoint | When | What it enforces |
|---|---|---|
| **Plan** | Session start | Agent reads context, names the governing workflow, and announces its approach before writing a line of code |
| **Gate** | Pre-commit | AI adversarial review + architecture checks + skill validate scripts must all pass before the commit lands |
| **Record** | Session close | Agent writes a structured audit trail — active task, decisions made, session ledger entry — before the session ends |

---

## What you get

### Governance layer

`AGENTS.md` defines the mandatory session lifecycle every agent follows, across all tools:

**14 absolute prohibitions** enforced by convention and the pre-commit gate — among them:

- No merging to `main` without explicit instruction
- No `git add .` or `git add -A` — always named files only
- No committing without completing local verification first
- No skipping tests for new functionality
- No committing secrets, API keys, or credentials
- No proceeding after a halt sentinel is active

**Workflow-first execution** — 8 named workflows cover every task type:

| Workflow | Use for |
|---|---|
| `/feature-implementation` | New features or requirements |
| `/bug-fix` | Production bugs |
| `/architect` | Architecture decisions |
| `/dba` | Schema and migration changes |
| `/security` | Security concerns |
| `/perf` | Performance issues |
| `/qa` | Tests only |
| `/release` | Releases and changelogs |

**Escalation triggers** — defined conditions where the agent must stop and ask rather than improvise: destructive scope, domain safety (auth, RBAC, multi-tenant isolation), infrastructure changes, or being blocked at the same state more than twice.

---

### Pre-commit AI review gate

Every commit passes through an AI adversarial review before it lands. The gate:

- Reviews the diff against a **universal invariants layer** (framework-owned) and a **project-specific rules layer** (developer-maintained)
- Produces a structured `PASS` / `WARN` / `FAIL` verdict — `FAIL` blocks the commit
- Logs all verdicts to `.ai-review-log.jsonl` for session history and trend analysis

Architecture checks run in the same gate: layer boundaries, import rules, and naming conventions are read from `.agent/config.yaml` — any project can define its own rules without touching code.

---

### Skills

22 universal skills ship with the harness, each with a `validate.py` script the agent must
run before declaring a task complete:

`api-design` · `c4-architect` · `code-migration` · `code-review` · `database-design` ·
`debugging` · `devops-cicd` · `kaizen` · `performance-optimization` · `playwright-skill` ·
`python-async` · `python-automation` · `python-fastapi` · `python-testing` · `refactoring` ·
`security-audit` · `senior-architect` · `systematic-debugging` · `test-driven-development` ·
`test-writing` · `testing-patterns` · `verification-before-completion`

Stack-pack skills layer framework-specific rules on top. Installed automatically when the
installer detects a matching stack:

- **`python-fastapi`** — mass assignment protection, async session management, Alembic migrations, pytest-asyncio patterns
- **`node-express`** — Node.js delivery conventions (stub, extensible)

Skills installed by the framework are never overwritten on re-run — developer customisations are preserved.

---

### Tool supplements

After install, four files sit in or near the project root — one canonical source, three thin shims:

```
.agent/UNIVERSAL_CONTEXT.md   ← project identity, harness version, key file locations
CLAUDE.md                     ← shim for Claude Code  (skip if exists)
GEMINI.md                     ← shim for Gemini CLI   (skip if exists)
.cursorrules                  ← shim for Cursor        (skip if exists)
```

Each shim tells its tool to read `UNIVERSAL_CONTEXT.md` first. Re-running the installer
refreshes `UNIVERSAL_CONTEXT.md` with the current version and date while leaving any
developer customisations in the shim files untouched.

---

## Quick Install

```bash
git clone https://github.com/Peadarpol/ai-delivery-control
python bootstrap/install.py --project-path /path/to/your/project
```

The installer detects your tech stack, copies framework files, scaffolds configuration
from templates, generates tool supplements, wires pre-commit hooks, and runs the environment
validation suite. Under 10 minutes from zero to working harness.

---

## What it is

A governance harness for AI-assisted software delivery. Works with Claude Code, Gemini CLI,
Cursor, Windsurf, or any LLM-based coding agent. Covers the full delivery lifecycle:
specification → development → testing → deployment.

## What it is not

- Not a framework for building AI agents
- Not an autonomous delivery system
- Not a replacement for human judgement

---

## Reference Implementation

Built and validated while engineering a multi-tenant SaaS business management platform. The harness governs its own development: all
framework changes are developed on feature branches, gated by the same pre-commit AI review,
and merged via PR.

---

## Documentation

- [Getting Started Guide](docs/getting-started.md)
- [Configuration Reference](docs/configuration.md)
- [Framework Backlog](docs/planning/FRAMEWORK_BACKLOG.md)

---

## Status

| Tier | Scope | Status |
|------|-------|--------|
| **Tier 1** | Solo developer, multiple projects. No server infrastructure. Works offline. | Production-ready |
| **Tier 2** | Small team, multi-machine. Shared session state and skill registry. | In development |
| **Tier 3** | Enterprise / regulated. Full database backend, RBAC, compliance reporting. | Planned |
