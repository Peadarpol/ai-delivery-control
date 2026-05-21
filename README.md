# AI Delivery Control

**You govern. Agents deliver.**

Most AI delivery frameworks optimise for autonomy — agents run until 
criteria pass. AI Delivery Control optimises for accountability — 
humans remain responsible for what ships.

Three checkpoints. Not zero. You stay in the loop.
The agents do the work.

Built for teams that need to explain every decision to an auditor,
a client, or a board.

## What it is
A governance harness for AI-assisted software delivery. Covers the
full lifecycle: specification → development → testing → deployment.
Works with Claude Code, Gemini, Cursor, Windsurf, or any 
LLM-based coding agent.

## What it is not
- Not a framework for building AI agents
- Not an autonomous delivery system
- Not a replacement for human judgement

## Quick Install

```bash
git clone https://github.com/Peadarpol/ai-delivery-control
python bootstrap/install.py --project-path /path/to/your/project
```

## How It Works
AI Delivery Control wraps agent execution in standard behavioral and structural constraints:
- **Structural Sanity Gates:** AST-driven static analysis to enforce layer invariants, import rules, and naming standards.
- **Agent Behavioral Monitoring:** Real-time activity auditing, passive session outcome tracing, and rate-limiting limits.
- **Modular Quality Control:** Standardized workflows, evaluations, and genericized skills that compile and execute locally with zero external network leakage.

## Reference Implementation
Built and validated while engineering [GymBase](https://github.com/Peadarpol/gym-management-system) — a multi-tenant SaaS gym management platform.

## Documentation
- [Getting Started Guide](docs/getting-started.md)
- [Configuration and Customisation](docs/configuration.md)
- [Framework Roadmap and Backlog](docs/planning/FRAMEWORK_BACKLOG.md)

## Status
- **Tier 1:** Production-ready for solo developers and small teams.
- **Tier 2:** Multi-machine and team features (active development).
