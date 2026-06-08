# Security

The security model for AI Delivery Control — what the framework accesses, what it does not, and how to verify it.

---

## What the framework accesses

AI Delivery Control is a local-first governance harness. It runs entirely on your development machine and has access to:

| Resource | How it is used |
|----------|---------------|
| `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` | Sent to the configured LLM provider during gate review calls and spec quality gate Pass 2 calls. Read from environment variables — never written to disk by the framework. |
| Staged diff content | Sent to the LLM provider on every `commit-msg` hook invocation. Includes the full content of every changed file in the commit. |
| Codebase structure | `repo_map.py` generates a PageRank-weighted summary of the repository import graph and injects it into the review context. File paths and import relationships are visible to the reviewing model. |
| `.agent/config.yaml` | Read at session start and gate invocation for routing configuration, architecture rules, and domain constraints. |
| `harness_events.jsonl`, `session_ledger.jsonl` | Read by the dream phase (`distill_dream.py`) to detect recurring failure patterns. These files remain on your local machine and are never transmitted externally. |

---

## What the framework does not do

- Does not transmit data to any endpoint other than the configured AI provider during review calls
- Does not phone home, collect telemetry, or log to external services
- Does not persist credentials — API keys are read from environment variables only
- Does not modify files outside the project directory it is installed into
- Does not require internet access at install time — only during gate review calls

---

## The context injection attack vector

Traditional supply chain security focuses on malicious executable code — backdoors, hidden commands, exfiltration routines. AI governance frameworks introduce a qualitatively different attack vector.

**An attacker who compromises a governance framework does not need to inject malicious code. They need to inject malicious instructions.**

The governance layer — `AGENTS.md`, `governance.md`, workflow files, skill files, the review gate system prompt — consists of natural language that AI agents interpret as instructions. A modified `AGENTS.md` could instruct agents to approve commits that should be blocked, generate code with specific vulnerability patterns, or leak context through review gate API calls. A modified gate system prompt could selectively pass dangerous diffs. None of this requires a single line of malicious Python, and none of it would be detected by `pip-audit`, `bandit`, or `guarddog`.

This risk is highest in automated or "dark factory" deployments where agents run without human session review. The governance layer is trusted implicitly — developers rarely re-read `AGENTS.md` after installation.

---

## Trust model

This framework requires elevated trust relative to a typical developer tool. The correct security posture:

1. **Read the governance files before installing.** At minimum: `.agent/AGENTS.md`, `.agent/governance.md`, and `src/scripts/review_context_universal.md`. These shape the behaviour of every agent session.

2. **Install from the authoritative source.** Forks or third-party distributions cannot be verified to be free of instruction injection.

3. **Verify checksums after installing:**
   ```bash
   python bootstrap/generate_checksums.py --verify
   ```
   This detects modifications to framework-owned files since installation.

4. **Review governance file diffs on every upgrade.** The upgrade report shows which files changed. Read the diffs for `AGENTS.md`, `governance.md`, and workflow files before accepting — even when classified as `OVERWRITE` rather than `CONFLICT`.

---

## What context is injected into agents

Every AI agent session in a framework-installed project receives the following injected context, in order:

1. **`CLAUDE.md` / `GEMINI.md` / `.cursorrules`** — Thin shims that direct the agent to read `.agent/UNIVERSAL_CONTEXT.md` and `.agent/AGENTS.md` as the first action of every session
2. **`.agent/AGENTS.md`** — Mandatory session protocol: startup checklist, named workflows, absolute prohibitions (P-01 to P-17), escalation triggers, session close requirements, and git discipline rules
3. **`.agent/governance.md`** — Absolute prohibitions and escalation rules
4. **`.agent/config.yaml`** — Architecture constraints, layer boundary rules, and domain constraints
5. **`src/scripts/review_context_universal.md`** — Framework-maintained universal review invariants injected into every adversarial gate call
6. **`src/scripts/review_context_project.md`** — Your project-specific review rules
7. **Active skill `SKILL.md`** — Loaded when a named workflow is active

The adversarial gate system prompt is defined in `src/scripts/ai_review.py` in the `_build_system_prompt()` function. It is not obfuscated and is directly readable in the source.

---

## Defences against instruction injection

| Defence | What it addresses |
|---------|------------------|
| Checksum registry (`generate_checksums.py --verify`) | Detects modifications to framework-owned files since installation |
| Structured upgrade report | Shows exactly which files changed — human review point before accepting |
| Unobfuscated gate source | System prompt in `ai_review.py` is directly readable; no hidden instructions |
| `SECURITY.md` visibility baseline | Documents expected content; malicious modifications are harder to hide when the baseline is published |
| Pre-flight installation validation | `bootstrap/validate.py` confirms installation health before each run |

---

## Responsible disclosure

If you discover a security vulnerability in AI Delivery Control, report it via **GitHub Private Vulnerability Reporting**. Do not open a public issue — vulnerabilities are disclosed publicly only after a fix is confirmed and released.

Full disclosure process, supported version table, and contact details: [`SECURITY.md`](../../SECURITY.md) in the repository root.

---

*For the design philosophy behind the gate's independence guarantees, see [Architecture Decisions](Architecture-Decisions).*
