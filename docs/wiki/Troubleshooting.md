# Troubleshooting

Common issues and how to resolve them.

---

## Installation and setup

### Pre-commit hooks not running

**Symptom:** Commits land without any gate output — no PASS, no FAIL, nothing.

**Cause:** Hooks are declared in `.pre-commit-config.yaml` but not activated in `.git/hooks/`.

**Fix:**
```bash
pre-commit install --install-hooks
```

Confirm everything is wired correctly:
```bash
python bootstrap/validate.py --project-path .
```

---

### `ANTHROPIC_API_KEY` not set

**Symptom:** Gate prints `⚠️ AI review skipped (fail-open)` on every commit, or exits immediately with an API authentication error.

**Fix:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Add to your shell profile (`.bashrc`, `.zshrc`, or equivalent) to persist across sessions. The key is read from environment at gate invocation time — it is never written to disk by the framework.

---

### Gate always returns PASS_FAST

**Symptom:** Every commit gets `PASS_FAST` even when you are committing code changes.

**Explanation:** `PASS_FAST` is correct behaviour for commits containing only `.md`, `.txt`, `.yml`, whitespace, or other documentation files — the gate intentionally skips the LLM call in these cases.

If you believe a code commit should trigger a full review, check the policy notes in the gate output. It will say which capabilities were active and which were skipped, with the reason. Verify that the staged files include `.py` or other code files and are not excluded by the architecture check's path patterns.

---

### `session.json` gitignore warning

**Symptom:** A large warning block appears at commit time:
```
⚠️  AI DELIVERY CONTROL — GITIGNORE WARNING  ⚠️
Warning: .agent/state/session.json is NOT ignored by git!
```

**Fix:** Append the operational state block to your `.gitignore`:
```
.agent/state/session.json
.agent/state/HALT
.agent/state/gate_context_current.json
.agent/state/dream_phase_state.json
.agent/wiki_compile_state.json
```

`harness_events.jsonl` must **not** be gitignored — it is the audit trail and must be committed.

---

## Gate behaviour

### How to read a FAIL verdict

See [Gate Verdicts Explained](Gate-Verdicts-Explained.md) for the complete guide to reading `FAIL` output, contesting findings with the rebuttal protocol, and understanding what each capability flag means.

---

### Gate fails closed — API is unavailable

**Symptom:** Commit is blocked with `FAIL CLOSED` even though no LLM review happened.

**Cause:** The AI provider is unreachable and the commit touches a high-risk file — migrations, auth, RBAC, multi-tenant isolation logic. The gate fails closed on these by design regardless of API availability.

**Options:**
1. Wait for the API to recover, then commit
2. Check that `ANTHROPIC_API_KEY` is set and not expired
3. If the commit is genuinely safe: `SKIP_AI_REVIEW=1 SKIP_REASON="factual reason"` — this bypass is logged and appears in the next harness health report

---

### Architecture check failures

**Symptom:** The `architecture-checks` hook fails before the AI gate runs.

**Example output:**
```
❌ [ARCHITECTURE] src/domain/user_service.py imports src.infrastructure.db
   Domain layer cannot depend on infrastructure
```

**Fix:** Move the offending import to the correct layer. If the boundary rule itself is wrong for your project, update `architecture.layers` in `.agent/config.yaml`.

---

### Traceability hook blocking commits

**Symptom:** Commits blocked with a message about missing `SPEC-NNN` reference.

**Explanation:** The traceability hook requires a valid spec ID in the commit message for non-trivial commits. Either:
- Include the spec ID: `SPEC-042: add user authentication endpoint`
- For infrastructure commits with no associated spec: append `--no-trace` to the commit message with a brief reason

`--no-trace` is logged to `harness_events.jsonl`.

---

### HALT file blocking commits

**Symptom:** Every commit is blocked. Output mentions a HALT sentinel.

**Cause:** A previous session wrote `.agent/state/HALT` — from token budget exhaustion, an explicit escalation trigger, or manual intervention.

**Fix:** Read the HALT file to understand why it was written, then remove it:
```bash
cat .agent/state/HALT
rm .agent/state/HALT
```

Do not delete the HALT file without reading it. It contains context about why the previous session stopped and may require follow-up action before continuing work.

---

## Validate.py output

Run the harness validator at any time to check installation health:

```bash
python bootstrap/validate.py --project-path .
```

Common output and what it means:

| Output | Severity | Action |
|--------|----------|--------|
| `Missing tool(s) in system path: pre-commit` | Warning | Activate your virtualenv or install pre-commit |
| `Pre-commit hooks configured but not active in .git/hooks` | Warning | Run `pre-commit install --install-hooks` |
| `Project-specific review context is absent` | Warning | Gate uses universal rules only — safe for getting started; add `review_context_project.md` when ready |
| `UNIVERSAL_CONTEXT.md missing framework version reference` | Warning | Reinstall or restore the framework version comment in the file |
| `HALT state guard is NOT gitignored` | **Error** | Add `.agent/state/HALT` to `.gitignore` immediately — committing it permanently blocks agents on fresh clones |

Errors (printed as `❌`) block gate operation. Warnings (printed as `⚠️`) indicate degraded coverage but do not block commits.

---

## Still stuck

- Run `python bootstrap/validate.py --project-path .` for a full installation health report
- Check `.ai-review-log.jsonl` for recent verdict history — `FAIL_OPEN` entries indicate reviews that did not complete
- Check `harness_events.jsonl` for bypass and error events from previous sessions
- See [Architecture Decisions](Architecture-Decisions.md) for why specific behaviours are designed the way they are
