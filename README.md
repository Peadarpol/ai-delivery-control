# AI Delivery Control

[![CI Build Status](https://github.com/Peadarpol/ai-delivery-control/actions/workflows/ci.yml/badge.svg)](https://github.com/Peadarpol/ai-delivery-control/actions)

AI Delivery Control is a **lightweight, local-first governance harness**. It operates entirely on your development machine, in your IDE, without server infrastructure. It is designed to establish rigorous guardrails for solo developers and small teams. 


**You govern. Agents deliver.**

Most AI coding frameworks optimise for autonomy — agents run until criteria pass.
AI Delivery Control optimises for accountability — keeping the human architect in the loop at consequential decision points while also enabling agent capability.

**Three checkpoints**

| Checkpoint | When | What it enforces |
|---|---|---|
| **Plan** | Session start | Agent reads context, names the governing workflow, and announces its approach before writing a line of code |
| **Gate** | Pre-commit | AI adversarial review + architecture checks + skill validate scripts must all pass before the commit lands |
| **Record** | Session close | Agent writes a structured audit trail — active task, decisions made, session ledger entry — before the session ends |

---

## What you get

### Governance layer

`AGENTS.md` defines the mandatory session lifecycle every agent follows, across all tools:

**17 absolute prohibitions (P-01–P-17)** enforced by convention and the pre-commit gate — among them:

- No merging to `main` without explicit instruction
- No `git add .` or `git add -A` — always named files only
- No committing without completing local verification first
- No skipping tests for new functionality
- No committing secrets, API keys, or credentials
- No proceeding after a halt sentinel is active

**Workflow-first execution** — 8 named workflows cover multiple task types:

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

### Stack Coverage & Manual Extension

Currently, the framework ships with out-of-the-box templates and invariant checks optimized for:
- **Python (FastAPI)**
- **Node.js (Express)**

Projects utilizing other stacks (e.g., Go, Rust, Java, or Ruby) are fully supported via core universal skills, but require manual customization of architecture boundaries in `.agent/config.yaml` and stack-specific guidelines under `.agent/skills/`.

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

(detailed in /docs/getting-started.md)
```bash
#1. git clone https://github.com/Peadarpol/ai-delivery-control

# 2. python bootstrap/install.py --project-path /path/to/your/project

# 3. Validate the install
python bootstrap/validate.py --project-path /path/to/your/project

# 4. Review and configure
# Edit .agent/config.yaml — set budget_provider, API keys, source paths

# 5. Run onboarding
cd /path/to/your/project
python .agent/scripts/onboarding.py

# 6. Start your first session
python .agent/scripts/init_session.py
```

The installer detects your tech stack, copies framework files, scaffolds configuration
from templates, generates tool supplements, wires pre-commit hooks, and runs the environment
validation suite. Under 10 minutes from zero to working harness.

---

## What it is

A lightweight governance harness for AI-assisted software delivery. Works with Claude Code, Gemini CLI, Cursor, Windsurf, or any LLM-based coding agent. It governs delivery execution — session lifecycle, pre-commit gate, and audit trail — but not production monitoring, incident response, or infrastructure provisioning. See [Out of Scope](#what-is-explicitly-out-of-scope) below.

## What it prevents

By integrating structured guardrails directly at the boundaries of your development workflow, the harness mitigates four critical failure modes of AI-assisted delivery:

1. **Accidental commits to the wrong repository**
   * *The Problem*: Working across multiple project directories introduces the risk of staging or committing framework code to a client repo (or vice versa).
   * *Framework Capability*: **P-14 Repository Guard** dynamically verifies the active folder identity at startup and blocks git operations if it detects a mismatch.

2. **Ungoverned or "hallucinated" correctness**
   * *The Problem*: AI agents tend to resolve failing tests by rewriting test assertions rather than fixing underlying code.
   * *Framework Capability*: The **Pre-Commit AI Review Gate** is structurally adversarial: a fresh, read-only reviewer agent (independent from the writer session) evaluates the diff and enforces custom project rules.

3. **Context window bloat and information loss**
   * *The Problem*: Multi-hour sessions accumulate tool logs and terminal output, causing the model's context window to overflow and drop critical architectural decisions.
   * *Framework Capability*: **Structured Session Lifecycle** maintains active context hot/warm memory tiering and records all key decisions in a durable markdown ledger.

4. **Stale or degraded architectural rules**
   * *The Problem*: Custom development rules written at project start become stale as the codebase evolves, leading to rule-compliance drift.
   * *Framework Capability*: The **Dream Phase** processes your session event logs, detects recurring failure patterns, and automatically proposes updated skills.

---

## Hard Enforcement vs Convention

The pre-commit AI review gate, repository identity guard, and architecture boundary checks are the only fully hard-enforced mechanisms. Every other governance behaviour depends on agent compliance with `AGENTS.md`, `governance.md`, and the workflow protocols.

This is a deliberate design choice. Hard enforcement of every rule would make the framework unusable. The gate is hard because it operates at the commit boundary — the moment where ungoverned code becomes permanent. Everything before the commit is convention reinforced by structured context.

Convention-based governance degrades under pressure. The gate does not.
*Design principle: hard enforcement at the commit boundary, convention everywhere else.*

| Mechanism | Type | Enforcement |
|-----------|------|-------------|
| **Pre-commit AI review gate** | Hard | Blocks commit on `FAIL` verdict |
| **Architecture boundary checks** | Hard | Blocks commit on layer violations |
| **Repository identity guard (P-14)** | Hard | Blocks git operations in wrong repo |
| **Session startup protocol** | Convention | Agent compliance via `AGENTS.md` |
| **Workflow phases** | Convention | Agent compliance via workflow file |
| **Prohibition table (P-01 to P-17)** | Convention | Agent compliance via `AGENTS.md` |
| **ORR checklist before main** | Convention | Required by P-01 (never merge to main) |

---

## What is explicitly Out of Scope

To maintain a lightweight, highly-focused codebase, the following areas are deliberately excluded from the framework:

- **Production Monitoring and Alerting**: Real-time server observability, metrics dashboards, and paging systems are out of scope. The framework’s governance boundary ends at the commit and the Operational Readiness Review (ORR) sign-off.
- **Incident Response**: The framework provides `incident_to_eval.py` to convert escaped defects into permanent regression guards in the eval dataset, but does not participate in active production incident resolution. An incident-to-backlog pipeline is planned (T1-L-07, not yet delivered).
- **Infrastructure Provisioning**: Cloud configuration, Terraform scripting, and cloud environment setups are completely out of scope. The framework governs the code structure that gets deployed, not the infrastructure it runs on.
- **Model Selection and Tuning**: The framework uses LLMs as utility reviewers. It remains agnostic to specific model selection, providing only the tiering configuration (e.g., local tasks vs. cloud reviews).
- **Compliance Control Mappings**: While highly relevant to regulated industries, formal mappings to compliance standards (such as the SOCI Act, ISM, or PSPF) are planned for **v3.0.0** and are not currently active.

---

## What it is not

- **Not** a framework for building custom autonomous AI agents.
- **Not** a fully autonomous software delivery agent.
- **Not** a replacement for human engineering oversight.

---

## Reference Implementation

Built and validated while engineering a multi-tenant SaaS business management platform. The harness governs its own development: all framework changes are developed on feature branches, gated by the same pre-commit AI review, and merged via PR.

---

## Documentation

- [Getting Started Guide](docs/getting-started.md)
- [Configuration Reference](docs/configuration.md)
- [Framework Backlog](docs/planning/FRAMEWORK_BACKLOG.md)

---

## Status

| Tier | Scope | Status | Target Timeline |
|------|-------|--------|-----------------|
| **Tier 1** | Solo developer, multiple projects. No server. Works offline. | **Production-ready** | Current |
| **Tier 2** | Small team, multi-machine. Shared session state. | **In development** | Q3 2026 |
| **Tier 3** | Enterprise / regulated. Full database, compliance. | **Planned** | Q4 2026 |
