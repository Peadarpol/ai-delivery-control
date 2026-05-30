# AI Delivery Control

[![CI Build Status](https://github.com/Peadarpol/ai-delivery-control/actions/workflows/ci.yml/badge.svg)](https://github.com/Peadarpol/ai-delivery-control/actions)

AI coding tools are capable. They will also happily commit broken code, implement
something adjacent to what you asked for, or quietly lose track of decisions made
three hours earlier — unless you give them structure.

This framework gives them structure.

**You govern. Agents deliver.**

It works with Claude Code, Gemini CLI, Cursor, Windsurf, or any LLM-based coding
agent. It is free, runs entirely on your machine, and requires no server infrastructure.

---

## Why this exists

Most AI coding guidance focuses on getting agents to do more. Less attention goes to
what happens when they do the wrong thing — and how you find out before it matters.

A few things go wrong regularly in AI-assisted development:

- The agent implements what it thinks you meant, not what you meant
- The agent resolves a failing test by rewriting the test rather than fixing the code
- The agent in a long session loses context and starts improvising
- There is no record of what was decided, or why

If you are working alone or in a small team without years of professional engineering
experience behind you, these problems are easy to miss until they compound. The habits
this framework enforces are the ones that experienced engineers carry in their heads.
This makes them explicit and, where it counts, automatic.

---

## What it does

Four things, at four points in your workflow:

**Before implementation begins** — a specification must exist and pass quality checks.
The spec gate verifies that acceptance criteria, scope boundaries, and a human
sign-off are present before a single line of code is written.

**Before the agent starts coding** — it reads your project context, names the workflow
it will follow, and states its approach. No freestyle.

**Before each commit lands** — every commit passes through an AI adversarial review.
A separate model, independent from the one that wrote the code, checks the diff against
your project's rules. `FAIL` blocks the commit. This is the only mechanism in the
framework that actually prevents something.

**At the end of each session** — the agent writes a structured record of what it did,
what decisions it made, and what is still open. You have an audit trail.

---

## The gate

The pre-commit AI review is the core of the framework. It is adversarial in a specific
sense: the reviewing model has no access to the writing agent's reasoning — only the
diff and your project's rules. It cannot rationalise the implementation.

It checks against two layers:
- **Universal rules** — shipped with the framework, covers common failure modes
- **Your project's rules** — defined in `.agent/config.yaml`, no code required

Verdicts are `PASS`, `WARN`, or `FAIL`. `FAIL` blocks the commit. All verdicts are
logged to `.ai-review-log.jsonl` so you can see patterns over time.

If the gate flags something you believe is wrong, there is a governed path to contest
it — a structured rebuttal protocol that logs the argument and gets a second opinion,
rather than a blunt bypass.

---

## Session structure

`AGENTS.md` defines how every agent session runs: what to check at startup, which
workflow applies to the task at hand, and when to stop and ask rather than improvise.

**15 absolute prohibitions (P-01–P-15)** cover the most common ways agent sessions go wrong:

- No committing to `main` without explicit instruction
- No `git add .` — always named files only
- No committing without running local verification first
- No skipping tests for new code
- No committing secrets or API keys

**Named workflows** cover the main task types. The agent names the workflow
it is following at the start of every session.

| Workflow | Use for |
|---|---|
| `/feature-implementation` | New features |
| `/business-analyst` | Requirement → approved specification |
| `/bug-fix` | Production bugs |
| `/architect` | Architecture decisions |
| `/dba` | Schema and migration changes |
| `/security` | Security concerns |
| `/perf` | Performance issues |
| `/qa` | Tests only |
| `/release` | Releases and changelogs |

**Escalation triggers** define the conditions where the agent must stop and ask rather
than make a decision: destructive scope, auth or access control changes, infrastructure,
or being stuck at the same point more than twice.

---

## Skills

22 universal skills ship with the framework. Each describes how to approach a specific
type of work and includes a `validate.py` script the agent must run before declaring
the task complete.

`api-design` · `c4-architect` · `code-migration` · `code-review` · `database-design` ·
`debugging` · `devops-cicd` · `kaizen` · `performance-optimization` · `playwright-skill` ·
`python-async` · `python-automation` · `python-fastapi` · `python-testing` · `refactoring` ·
`security-audit` · `senior-architect` · `systematic-debugging` · `test-driven-development` ·
`test-writing` · `testing-patterns` · `verification-before-completion`

Stack-specific skills layer on top when the installer detects a matching stack.
Currently ships with full support for **Python / FastAPI** and a stub for
**Node.js / Express**. Other stacks work through the universal skills with manual
configuration. Skills you customise are never overwritten on re-install.

---

## Hard enforcement vs convention

The pre-commit gate, the repository identity guard, and the architecture boundary
checks are the only mechanisms that actually block anything. Everything else —
session lifecycle, workflow phases, the prohibition table — depends on the agent
following instructions.

This is deliberate. Hard enforcement at every point would make the framework
unusable. The gate is hard because it operates at the commit boundary, where
ungoverned code becomes permanent. Everything before that is convention reinforced
by structure.

Convention degrades under pressure. The gate does not.

| Mechanism | Enforcement |
|---|---|
| Pre-commit AI review gate | Blocks commit on FAIL |
| Architecture boundary checks | Blocks commit on violations |
| Repository identity guard (P-14) | Blocks git operations in wrong repo |
| Session startup protocol | Convention — agent compliance |
| Workflow phases | Convention — agent compliance |
| Prohibition table (P-01–P-15) | Convention — agent compliance |

---

## Install

```bash
# Always pull the latest framework before installing or upgrading
git clone https://github.com/Peadarpol/ai-delivery-control
# or, from an existing clone: git pull

# Install into your project
python bootstrap/install.py --project-path /path/to/your/project

# Validate
python bootstrap/validate.py --project-path /path/to/your/project
```

Full setup: [docs/getting-started.md](docs/getting-started.md)

The installer detects your stack, copies framework files, wires pre-commit hooks,
and runs the environment validation suite. Under ten minutes from zero to working.

---

## Security

**Authoritative source only**: `https://github.com/Peadarpol/ai-delivery-control`

Forks or third-party distributions cannot be guaranteed to be free of malicious code.

Before running `install.py`, read `.agent/AGENTS.md` and `.agent/governance.md`.
This framework injects context into every AI agent session in your project. You
should understand what it instructs agents to do before granting it that access.
That is not a courtesy suggestion — it is the correct security posture for any
governance layer you did not author.

**What the framework accesses**: your API key via environment variables, the content
of every commit diff reviewed by the gate, your codebase structure via the repo map,
and `.agent/config.yaml`. It does not send data anywhere beyond what your configured
LLM provider receives during review calls.

Verify the framework clone is unmodified before installing:
```bash
# Run from inside the ai-delivery-control clone directory
python bootstrap/generate_checksums.py --verify
```

Full security model and responsible disclosure: [`SECURITY.md`](SECURITY.md)

---

## What it does not do

- Not a replacement for engineering judgement
- Not production monitoring or alerting
- Not infrastructure provisioning
- Not an autonomous delivery agent — you are still making the decisions
- Not compliance-mapped to regulatory standards (planned for v3.0.0)

---

## Reference implementation

Built and validated while developing a multi-tenant SaaS platform. The framework
governs its own development: all changes are made on feature branches, gated by the
same pre-commit AI review, and merged via PR.

---

## Status

| Tier | Scope | Status |
|---|---|---|
| **Tier 1** | Solo developer or small team. Local only. No server required. | Production-ready |
| **Tier 2** | Small team, multi-machine, shared session state | Roadmap — v2.0.0 |
| **Tier 3** | Enterprise, compliance, regulated industries | Roadmap — v3.0.0 |

---

## Documentation

- [Getting Started](docs/getting-started.md)
- [Configuration Reference](docs/configuration.md)
- [Framework Backlog](docs/planning/FRAMEWORK_BACKLOG.md)
- [Changelog](CHANGELOG.md)
