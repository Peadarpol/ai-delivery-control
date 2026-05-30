# Security Policy

## Responsible Disclosure

If you discover a security vulnerability in AI Delivery Control, please report it via **GitHub Private Vulnerability Reporting**:

1. Go to [Security → Report a vulnerability](https://github.com/Peadarpol/ai-delivery-control/security/advisories/new)
2. Describe the vulnerability, affected versions, and reproduction steps
3. Allow up to 14 days for an initial response

Please do not open a public issue for security vulnerabilities. Once a fix is confirmed and released, the vulnerability will be disclosed publicly via a GitHub Security Advisory.

---

## Security Model

### What This Framework Has Access To

AI Delivery Control is a **local-first** governance harness. It runs entirely on your development machine and has access to:

| Resource | How it is used |
|----------|---------------|
| `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`) | Sent to the configured LLM provider during pre-commit gate review calls and spec quality gate Pass 2 calls. Keys are read from environment variables; never written to disk by the framework. |
| Git diff content | The staged diff is sent to the LLM provider on every `commit-msg` hook invocation. This includes the full content of every changed file in the commit. |
| Codebase structure | `repo_map.py` generates a PageRank-weighted summary of the repository structure and injects it into the review gate context. File paths and import relationships are visible. |
| `.agent/config.yaml` | Read at session start and gate invocation for routing configuration. Contains architecture rules, domain constraints, and model configuration. |
| `harness_events.jsonl`, `session_ledger.jsonl` | Read by the dream phase (`distill_dream.py`) to detect recurring failure patterns. These files remain on your local machine and are never transmitted externally. |

### What This Framework Does Not Do

- Does not exfiltrate data beyond what the configured LLM provider receives during review calls.
- Does not phone home, collect telemetry, or transmit data to any endpoint other than the configured AI provider.
- Does not persist credentials. API keys are read from environment variables only.
- Does not modify files outside the project directory it is installed into.
- Does not require internet access during install (only during gate review calls).

### What Context Is Injected Into Agents

Every AI agent session in a framework-installed project receives the following injected context, in order:

1. **`CLAUDE.md` / `GEMINI.md` / `.cursorrules`** — Thin shims that direct the agent to read `.agent/UNIVERSAL_CONTEXT.md` and `.agent/AGENTS.md` as the first action of every session.
2. **`.agent/AGENTS.md`** — The mandatory session protocol: startup checklist, workflow-first discipline, absolute prohibitions (P-01 to P-17), escalation triggers, session close requirements, git discipline rules. This is the primary governance document. **Read this before installing the framework.**
3. **`.agent/governance.md`** — Absolute prohibitions and escalation rules. Rarely changes; high trust document.
4. **`.agent/config.yaml`** — Architecture constraints, layer boundary rules, domain constraints injected into the AI review gate system prompt via `governance_check.py`.
5. **`src/scripts/review_context_universal.md`** — Framework-owned universal review invariants injected into every adversarial gate call.
6. **`src/scripts/review_context_project.md`** — Developer-maintained project-specific review rules injected alongside the universal layer.
7. **Active skill `SKILL.md`** — The relevant skill file is loaded when a workflow is active.

The adversarial gate's system prompt is defined in `src/scripts/ai_review.py` in the `_build_system_prompt()` function. It is not obfuscated and is directly readable in the source.

### Trust Model

This framework requires **elevated trust** relative to a typical developer tool:

- It shapes the behaviour of every AI agent session in your project through context injection.
- It has access to your API keys and commit content.
- The governance layer (AGENTS.md, governance.md, workflow files, skill files) consists of natural language that AI agents interpret as instructions — not executable code that can be scanned by traditional security tools.

The correct security posture:
1. **Read the governance files before installing.** Specifically: `.agent/AGENTS.md`, `.agent/governance.md`, and `src/scripts/review_context_universal.md`.
2. **Install from the authoritative source**: `https://github.com/Peadarpol/ai-delivery-control`. Forks or third-party distributions cannot be guaranteed to be free of malicious code.
3. **Verify checksums after installing**: `python bootstrap/generate_checksums.py --verify`.
4. **Review governance file diffs on every upgrade.** The upgrade report shows which files changed. Read the diffs for AGENTS.md, governance.md, and workflow files before accepting.

---

## The Context-Injection Attack Vector

Traditional supply chain security focuses on malicious executable code — backdoors, exfiltration routines, hidden commands. AI governance frameworks introduce a qualitatively different attack vector.

**An attacker who compromises a governance framework does not need to inject malicious code. They need to inject malicious instructions.**

A modified `AGENTS.md` could instruct agents to generate code with specific vulnerability patterns, approve commits that should be blocked, or leak context through the review gate's API calls. A modified review gate system prompt could selectively pass dangerous diffs. A modified workflow file could redirect agent behaviour at critical decision points. None of this requires a single line of malicious Python — and none of it would be detected by `pip-audit`, `bandit`, or `guarddog`.

This attack vector is particularly dangerous in automated or "dark factory" deployments where agents run without human review of session output. The governance layer is trusted implicitly. Developers rarely re-read AGENTS.md after installation.

**Current defences in this framework:**

| Defence | What it addresses |
|---------|------------------|
| Checksum registry (`checksums.py`) | Detects modifications to framework-owned files; `--verify` surfaces any drift |
| Pre-flight check (`--skip-preflight` required to bypass) | Validates installation health before running migrations |
| Structured upgrade report | Shows exactly which files changed; human review point |
| Adversarial gate source is unobfuscated | System prompt in `ai_review.py` is directly readable |
| `SECURITY.md` (this document) | Creates a visibility baseline; malicious modifications are harder to hide when the expected content is documented |

**Planned defences (v1.3.0+):**

- GPG-signed releases — signed tags verifiable against a published public key, independent of distribution channel
- `validate.py --security` mode — hashes and displays system prompts and key governance files interactively for user verification without reading source code
- `docs/security/` directory — documents every context injection point as a formal baseline; deviations from the baseline are detectable

A formal security review of the framework's own attack surface as a context-injection vector is planned and will be published before broad community distribution.

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| v1.2.0 (current) | ✅ Active |
| v1.1.5.x | ⚠️ Security fixes only — upgrade recommended |
| v1.1.0 and earlier | ❌ Unsupported |
