# AI Delivery Control Wiki

Welcome to the AI Delivery Control framework wiki. This is the central hub for exploring, learning, and referencing the framework.

## Quick Navigation

**Getting started?** → Start with [Installation & Setup](Installation-&-Setup)

**Need a quick lookup?** → Check the [Glossary](Glossary) or [Quick Reference](Quick-Reference)

**Exploring workflows?** → Browse [Workflows & Tasks](Workflows-&-Tasks)

**Understanding gates?** → Read [The Pre-Commit Gate](The-Pre-Commit-Gate)

---

## What is AI Delivery Control?

AI Delivery Control is a governance harness that sits between you and AI coding agents. It doesn't make agents more capable—it makes them **more accountable**.

The framework enforces structure at four points:

1. **Before implementation** — specs must pass quality checks
2. **Before the agent starts** — it reads context and names its workflow
3. **Before each commit** — the AI review gate validates against project rules
4. **At session end** — structured record of what was decided

**Core principle:** Hard enforcement at the commit boundary. Convention everywhere else.

---

## The Framework at a Glance

| Component | Purpose |
|-----------|---------|
| **Pre-commit AI review gate** | Independent model reviews every diff against project rules — `FAIL` blocks commit |
| **Session lifecycle** | UUID-tracked sessions with context carryover across developer sessions |
| **Named workflows** | 18 state machines covering feature delivery, bug fixes, architecture decisions, etc. |
| **Universal skills** | 22 reusable task guides covering debugging, testing, refactoring, security, performance, etc. |
| **Outer loop** | Requirement → spec → approval → tasks → commits → acceptance gate → PR |
| **Dream phase** | Self-improvement: recurring failure patterns feed back into project-specific rules |
| **Custom domains** | Project-specific review rules and architectural constraints, never overwritten on upgrade |

---

## Core Concepts

### The Gate

Every `git commit` triggers an independent AI review. The gate reads:
- Your diff
- Universal review rules (shipped with framework)
- Project-specific rules (you define these)

Verdict: `PASS`, `WARN`, `FAIL`, or `FAIL_OPEN`. Only `FAIL` blocks.

### Workflows

Named task types that enforce sequence. Before any substantive code change, the agent announces which workflow it's following:
- `/feature-implementation` — new features
- `/bug-fix` — production bugs
- `/architect` — architecture decisions
- `/security` — security concerns
- ... and 14 others

Each workflow has phases, escalation triggers, and validation checkpoints.

### Skills

Portable, executable policy documents. Each skill:
- Describes how to approach a task type
- Includes a `validate.py` that must exit 0 before task completion
- Covers the "how" so agents don't freestyle

Universal skills ship with the framework. Add custom skills to your project—they're never overwritten on upgrade.

### Session State

Four markdown files carry context across sessions:
- `active_context.md` — current work, blockers, next steps
- `decisions_log.md` — all technical and business decisions made
- `last_session_summary.md` — what was completed, what's incomplete
- `session_ledger.jsonl` — timestamped session inventory

---

## Wiki Structure

- **[Installation & Setup](Installation-&-Setup)** — Get running in <10 minutes
- **[Glossary](Glossary)** — Define key terms
- **[Quick Reference](Quick-Reference)** — One-page cheat sheet
- **[Configuration](Configuration)** — `.agent/config.yaml` reference
- **[Workflows & Tasks](Workflows-&-Tasks)** — Detailed guides for each named workflow
- **[Skills](Skills)** — The 22 universal skills, plus how to create custom skills
- **[Governance Rules](Governance-Rules)** — Prohibitions (P-01–P-15) and escalation triggers
- **[Customization](Customization)** — How to add project-specific rules without modifying framework files
- **[Troubleshooting](Troubleshooting)** — Common issues and solutions
- **[Gate Verdicts Explained](Gate-Verdicts-Explained)** — What `PASS`, `WARN`, `FAIL` mean and how to contest them
- **[Architecture Decisions](Architecture-Decisions)** — Why the framework is designed this way
- **[FAQ](FAQ)** — Common questions

---

## Key Files

| File | What it is |
|------|-----------|
| `.agent/AGENTS.md` | Mandatory agent protocol (do not edit manually—auto-generated) |
| `.agent/governance.md` | Prohibitions, escalation rules, full rationale |
| `.agent/config.yaml` | Project config: tech stack, capabilities, paths, constraints, architecture |
| `.agent/skills/` | 22 universal skills + your custom skills |
| `.agent/workflows/` | 18 named workflows |
| `src/scripts/review_context_universal.md` | Framework-maintained review rules (do not edit) |
| `src/scripts/review_context_project.md` | **Your** custom review rules (edit freely) |

---

## Common Tasks

**I want to...** | **See**
---|---
...get the framework running | [Installation & Setup](Installation-&-Setup)
...understand what a workflow is | [Workflows & Tasks](Workflows-&-Tasks)
...add a custom review rule | [Customization](Customization)
...create a project-specific skill | [Skills](Skills)
...understand why I got a `FAIL` verdict | [Gate Verdicts Explained](Gate-Verdicts-Explained)
...see what the prohibitions are | [Governance Rules](Governance-Rules)
...configure my tech stack | [Configuration](Configuration)
...troubleshoot a pre-commit hook | [Troubleshooting](Troubleshooting)
...understand the design philosophy | [Architecture Decisions](Architecture-Decisions)

---

## Quick Stats

- **22 universal skills** covering debugging, testing, refactoring, security, DevOps, etc.
- **18 named workflows** for every major task type
- **15 absolute prohibitions** (P-01–P-15) that encode minimal-footprint engineering
- **2 stack-packs** (Python/FastAPI, Node/Express) with language-specific rules
- **100% local** — no server, no cloud dependency
- **Upgrade-safe** — your customizations never overwritten

---

## For Developers

If you're installing this framework into your project, start here:
1. Read [Installation & Setup](Installation-&-Setup)
2. Understand [Governance Rules](Governance-Rules)
3. Explore the [Quick Reference](Quick-Reference)
4. Run your first session and check the [Troubleshooting](Troubleshooting) guide if needed

For questions on specific tasks, navigate to [Workflows & Tasks](Workflows-&-Tasks) or [Skills](Skills).

---

## For Maintainers

If you're contributing to the framework:
- All governance is in `.agent/AGENTS.md`, `.agent/governance.md`, and `.agent/config.yaml`
- Skills live in `.agent/skills/` — each has a `SKILL.md` and optional `validate.py`
- Workflows live in `.agent/workflows/` — each is a state machine
- The gate logic is in `src/scripts/ai_review.py` and related modules

See [Architecture Decisions](Architecture-Decisions) for the design philosophy.

---

*Last updated: 2026-06-04*
