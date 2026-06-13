# The Pre-Commit Gate

How the AI adversarial review gate works — what fires, when, and in what order.

---

## Overview

Every `git commit` in a framework-installed project triggers a chain of automated checks. The AI adversarial review gate is the final hook in that chain, firing at the `commit-msg` stage after all formatting, linting, type-checking, and architecture checks have passed.

---

## The Hook Chain

Hooks fire in this order on every commit:

### Pre-commit stage

These run first, before the commit message is written:

| Hook | What it checks |
|------|---------------|
| `check-active-repo` | Confirms the commit targets the expected repository (P-14 guard) |
| `trailing-whitespace`, `end-of-file-fixer`, `check-yaml` | Standard file hygiene |
| `black` | Code formatting |
| `ruff` | Lint and style |
| `mypy` | Static type checking |
| `bandit` | Static application security analysis |
| `pip-audit` | Dependency vulnerability scan |
| `gitleaks` | Secret scanning |
| `architecture-checks` | Layer boundary enforcement — AST-based, no LLM call |
| `skills-hygiene` | Validates skill file structure and metadata |

### Commit-msg stage

These run when the commit message is supplied — after all pre-commit hooks pass:

| Hook | What it checks |
|------|---------------|
| **`ai-adversarial-review`** | The AI gate — an independent model reviews the full diff against your project rules |
| `commit-traceability` | Verifies the commit message references an approved `SPEC-NNN` ID |

### Post-commit stage

These run after the commit lands:

| Hook | What it does |
|------|-------------|
| `governance-audit` | Writes a governance event record to `harness_events.jsonl` |
| `session-heartbeat` | Updates the active session record in `session.json` |

### Pre-push stage

These run before `git push`:

| Hook | What it checks |
|------|---------------|
| `behaviour-checks` | Agent behaviour regression against the golden eval dataset |
| `regression-check` | Golden dataset regression guard |

---

## How the AI Review Decides

The gate does not send the diff blindly to the LLM. It routes first.

### Pre-flight check (PASS_FAST)

If the diff contains only documentation files (`.md`, `.rst`, `.txt`), whitespace changes, or configuration files, the gate returns `PASS_FAST` immediately with zero LLM calls. This keeps the gate fast and cheap for trivial commits.

### Diff-aware routing

For code changes, the gate builds a `RouteDecision` before calling the LLM:

1. **File-path routing** — changed files are matched against capability patterns. Migration files activate `TRANSACTIONAL_INTEGRITY`. Auth and permission files activate `BRANCH_ISOLATION`. Files with no high-risk match use the default capability set.

2. **PageRank intensity** — the codebase import graph assigns structural importance scores to each file. Changes to files in the top 10 by PageRank score escalate review intensity to `elevated`; top 3 escalates to `critical`, where `WARN` verdicts are treated as `FAIL`.

3. **ADR annotations** — `# ADR: domain_name` comments in source files activate the corresponding review capability regardless of file path. The domain key maps to a compiled wiki page injected into the review context.

The `RouteDecision` is printed alongside every verdict, so you can see exactly which capabilities were active and which were skipped.

### Context assembly

Before the LLM call, the gate assembles a context bundle (total budget ≤2,000 tokens):

| Source | Budget | Content |
|--------|--------|---------|
| `review_context_universal.md` | ≤800 tokens | Framework-maintained universal review rules |
| `review_context_project.md` | included above | Your project-specific rules |
| Repo map | ≤600 tokens | PageRank-weighted structural summary of the codebase |
| ADR wiki pages | ≤400 tokens | Compiled domain summaries for activated capabilities |
| Co-change warnings | ≤200 tokens | Files that co-change historically with the changed files, classified by confidence tier: `EXTRACTED` (git history + import link) and `INFERRED` (history only) are injected here; `AMBIGUOUS` (import only) appears in routing policy notes instead |
| Evidence signals | — | `pytest` collection status and TODO count delta, gathered before the LLM call and included as additional context signals |

### The LLM call

The reviewing model has no access to the writing agent's session context or reasoning. It sees only the diff, the assembled context, and the active capability list. It produces a typed `ReviewVerdict` with a verdict, specific findings, and the active route decision.

---

## Fail-Open vs Fail-Closed

If the configured AI provider is unavailable:

- **Low-risk commits** (docs, config, non-sensitive code): gate fails open — commit proceeds with a warning printed to the terminal
- **High-risk commits** (migrations, auth, RBAC, multi-tenant isolation files): gate fails closed — the commit is blocked even without an LLM call

High-risk file patterns include anything matching `*/migrations/*`, `*/auth/*`, `*/rbac/*`, `*/permissions/*`, or files annotated `# ADR: branch_isolation`. Override requires `SKIP_AI_REVIEW=1 SKIP_REASON="..."`.

---

## Capability Calibration

The gate tracks false-positive history per review capability (e.g. `BRANCH_ISOLATION`, `CLEAN_ARCH`). Each accepted rebuttal nudges that capability's weight down slightly; rejected rebuttals and uncontested findings nudge it up.

Over time, a capability that repeatedly generates accepted rebuttals will have its HIGH-severity findings automatically softened — reducing the chance of a blocking `FAIL` on a known-noisy check without disabling the check entirely. The weight is clamped: it can dampen a capability but never silence it. You can also lock a capability's weight manually in `.agent/config.yaml` under `capability_calibration.overrides`.

The practical effect: the gate gets less confrontational about things your project genuinely doesn't care about, and stays firm on everything else.

---

## Bypass Options

| Method | When to use | What is logged |
|--------|-------------|----------------|
| `--rebuttal` mode | Gate `FAIL` on a finding you believe is a false positive | Full rebuttal review written to `.ai-review-log.jsonl`; confirmed false positives added to the regression suite |
| `SKIP_AI_REVIEW=1 SKIP_REASON="..."` | Last resort — infrastructure commit with no governance risk | Bypass event written to `harness_events.jsonl`; flagged in next harness health report |

`SKIP_AI_REVIEW=1` is not silent. It is logged and appears in the harness health report as a named bypass event.

---

*For what the verdicts mean and what to do about them, see [Gate Verdicts Explained](Gate-Verdicts-Explained.md).*
