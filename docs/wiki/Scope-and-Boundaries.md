# Scope and Boundaries

What the framework guarantees — and what it honestly does not.

---

This page exists because the framework makes specific claims about what it enforces, and those claims have real limits. Naming the limits explicitly is more useful than leaving them for you to discover mid-project.

---

## What the framework guarantees

These are structural guarantees — things the framework enforces by design, not by convention:

- **Every commit passes an adversarial review** by a model that has no access to the writing agent's reasoning. The reviewing model sees only the diff and your project's rules. It cannot rationalise the implementation.
- **Every commit on a governed feature branch traces back to an approved specification.** The traceability gate requires a `SPEC-NNN` reference in the commit message. A commit without a traceable spec is blocked.
- **Every session has a structured audit trail.** Gate verdicts, spec checks, bypass events, and session outcomes are written to `harness_events.jsonl` and `.ai-review-log.jsonl`. You have a record of what was checked and what was decided.
- **The gate improves over time from your project's specific failure patterns.** The dream phase reads your session history and proposes rule additions based on patterns that recur in your project — not generic best practice from somewhere else.

---

## What the framework does not guarantee

Three boundaries are structural — not implementation gaps, but deliberate limits of what a commit-boundary governance framework can provide.

### What happens before the commit

The gate governs what enters the repository. It does not intercept tool calls, API calls, or file operations an agent makes during a session. An agent that damages local state, reads secrets from environment variables, or calls external APIs before committing is outside the framework's enforcement boundary.

Closing this gap requires sandboxing or runtime monitoring — a different architectural component that operates during execution, not at the commit boundary.

The practitioner complement to this boundary is sandboxing: running the agent in a
Docker container or git worktree with filesystem and network isolation constrains
what it can touch before any commit is made. The framework does not require or
configure sandboxing — it is a separate architectural decision — but it is the
correct answer to the runtime enforcement gap for high-stakes delivery work.

### Accumulated drift across many passing commits

The gate checks each commit against your rules. It does not detect when a sequence of individually-passing commits has collectively drifted from the original architectural intent.

Longitudinal coherence — whether the codebase today still reflects the decisions made six months ago — requires periodic architectural fitness functions run against the full codebase, not per-commit gates that see only the diff.

### The gate's own blind spots

The self-improvement loop improves what the gate already notices. It cannot detect systematic gaps in what the gate is configured to look for. A class of violation the gate has never flagged will not generate improvement proposals, because there is no signal in the session history to detect.

External ground truth — production incidents fed back via the incident pipeline, or periodic expert review of the codebase independent of what the gate checks — is the complement the framework cannot provide itself.

---

## Why these boundaries exist

These are deliberate design boundaries, not implementation gaps waiting to be filled. The framework governs the delivery process at the commit boundary — a single, testable enforcement point that is practical, auditable, and composable with any agent tool. Governing the execution environment, detecting longitudinal drift, and red-teaming the gate's own blind spots are each distinct problems requiring distinct approaches. Some are on the roadmap (runtime monitoring, architectural fitness functions). Some are intentionally left to the human architect, because they require judgement that cannot be automated away.

---

*For the full design philosophy behind these choices, see [Architecture Decisions](Architecture-Decisions.md).*

---

## Industry Validation

The harness implements a governance loop that was independently articulated by two
major industry sources in early 2026:

**Sonar AC/DC framework (March 3, 2026)**: Sonar — the global leader in code
verification — introduced the Agent Centric Development Cycle (AC/DC) at Sonar
Summit Austin, defining the same four-stage loop: Guide → Generate → Verify → Solve.
Sonar's positioning: *"At the core of AC/DC is the recognition that agents generating
code need to be supported by strong Guide, Verify, and Solve practices."* The harness's
`UNIVERSAL_CONTEXT.md` + skills injection (Guide), Gemini session (Generate),
`ai_review.py` + `architecture_checks.py` (Verify), and rebuttal protocol + dream phase
(Solve) map directly to these four stages. Sonar's framework was announced after the
harness had been in production use for over a year.

**GitLab AI Accountability Report (June 2026)**: A 1,528-person survey across six
countries found that 92% of respondents report governance challenges with AI-generated
code, and 85% agree the next phase of AI in software will focus less on governing it.
The report defines AI accountability as the ability to answer three questions about any
AI-generated commit: where did it come from, what was it meant to do, and who is responsible
for it in production. The harness answers all three:
session traceability via `session_ledger.jsonl`, spec-to-commit linkage via SPEC-ID
tokens, and the HARD STOP PROTOCOL that keeps the human architect as the responsible
party at every merge gate.

These sources do not change the harness's design — they confirm it.

