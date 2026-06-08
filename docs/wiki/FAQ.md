# FAQ

Frequently asked questions about AI Delivery Control.

---

## How it works

### How is this different from having the AI agent review its own code?

The gate uses a completely separate model instance with no access to the writing agent's session context or reasoning. The reviewing model sees only the diff and your project's rules — it cannot rationalise the implementation the way the writing agent would. This is the evaluator-optimizer pattern: one model generates, a separate model evaluates. The two models have different blind spots, and running both over the same output catches what either would miss alone.

### Does the gate run on every commit?

Yes. Every `git commit` triggers the full pre-commit chain. The AI review fires at the `commit-msg` stage. Documentation-only commits (`.md`, `.txt`, whitespace) are detected by the pre-flight check and returned as `PASS_FAST` with zero API calls — the cost is proportionate to what you are committing. See [The Pre-Commit Gate](The-Pre-Commit-Gate.md) for the full hook chain.

### Does it work with Gemini CLI, Cursor, or Windsurf?

Yes. The gate is wired into `git` via pre-commit hooks, not into any specific agent tool. Any agent that runs `git commit` — Claude Code, Gemini CLI, Cursor, Windsurf, or a human at the terminal — passes through the same gate. The hooks run regardless of who or what initiated the commit.

### Is my code sent to a third party?

The staged diff is sent to your configured LLM provider (Anthropic, OpenAI, or a local Ollama instance) during the gate review call. The framework does not phone home, collect telemetry, or transmit data to any other endpoint. See [Security](Security.md) for the full data access model and how to verify it.

---

## Gate behaviour

### What happens if the API is down?

- **Low-risk commits** (docs, config, non-sensitive code): gate fails open — commit proceeds with a warning
- **High-risk commits** (migrations, auth, RBAC, multi-tenant isolation): gate fails closed — commit is blocked until the API is reachable or you explicitly bypass with `SKIP_AI_REVIEW=1 SKIP_REASON="..."`

This asymmetry is intentional. The gate's value collapses if it silently passes high-risk commits during an outage.

### What does FAIL_OPEN mean in the review log?

`FAIL_OPEN` in `.ai-review-log.jsonl` means the gate could not complete a review — API unavailable, timeout, or parse failure — and chose to allow the commit rather than block it. It is distinct from a genuine `PASS`. It means the review did not happen, not that the code is clean.

### Can I bypass the gate?

Two paths exist:

1. **Rebuttal** (preferred): if you believe a `FAIL` finding is wrong, use `--rebuttal` mode. The gate runs a second review against your specific evidence. Confirmed false positives are logged and added to the regression test suite automatically.
2. **Override** (last resort): `SKIP_AI_REVIEW=1 SKIP_REASON="..."` bypasses the gate entirely. The bypass is logged to `harness_events.jsonl` and flagged in the next harness health report. It is not silent.

### Why did the gate flag something that is not a problem?

The most common cause is a missing or incomplete `review_context_project.md`. The gate has no way to know that a particular pattern is intentional in your project unless you tell it. Add a rule to your project context file explaining the pattern. See [Customization](Customization.md).

If you are certain the finding is a false positive, use the rebuttal protocol — this creates a permanent regression guard that prevents the same finding from recurring.

### The gate seems very strict on migration files. Is that intentional?

Yes. Migration files, auth logic, RBAC, and multi-tenant isolation code are classified as high-risk. At elevated review intensity, `WARN` verdicts are escalated to `FAIL`. The gate also fails closed on these files when the API is unavailable. This is the correct tradeoff: the cost of a false positive on a migration is far lower than the cost of a missed violation.

---

## Configuration and setup

### Do I need to re-run the installer when I change `config.yaml`?

No. `config.yaml` is read at runtime — changes take effect on the next commit or session start without reinstalling.

### How do I add project-specific review rules?

Edit `src/scripts/review_context_project.md` in your project. This file is never overwritten on upgrade. See [Customization](Customization.md) for the format and examples.

### Can I use a local model instead of Anthropic?

Yes. Set `model_routing.review_provider: "ollama"` and `model_routing.review_model: "your-model"` in `.agent/config.yaml`. The gate uses the same provider interface regardless of where the model runs. Review quality depends on the model — smaller models may miss subtle architectural violations.

### What is the cost per commit?

A typical feature commit (50–200 changed lines) uses approximately 2,000–4,000 tokens at the review tier. Documentation-only commits use zero tokens. You can track per-session token spend in `.agent/state/session_ledger.jsonl` under `token_usage`.

---

## The outer loop

### What is the outer loop?

The outer loop covers the requirements side of delivery: specification quality checks, requirement traceability, and acceptance checking. It ensures agents implement the right thing, not just that they implement it correctly. See [Workflows Overview](Workflows-Overview.md) for the named workflows that use the outer loop.

### What is a SPEC-NNN reference and why does my commit need one?

When the traceability hook is active, every non-trivial commit must reference an approved specification in the commit message (for example: `SPEC-042: add user authentication endpoint`). This closes the chain from requirement → approved spec → implementation → commit. Infrastructure commits can include `--no-trace` with a brief reason, which is logged.

### What is the dream phase?

The dream phase is the self-improvement loop. It runs periodically (triggered at session start when enough time and data have accumulated) and reads your session history — gate verdicts, bypass events, escalation patterns — to detect recurring failure modes specific to your project. When a pattern meets the threshold, it generates a structured proposal to add or tighten a project skill rule. Proposals require human review before they take effect. See [Dream Phase](Dream-Phase.md) for the full explanation.

---

*For full governance rules and prohibitions, see [Governance Rules](Governance-Rules.md).*
