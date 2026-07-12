# Companion: ROI Baseline & Measurement Kit for SPEC-context-compression

**Status:** Measurement artifact — supports the §0 ROI Gate in [SPEC-context-compression.md](./SPEC-context-compression.md)
**Purpose:** Answer the blocking question before any implementation: *is an LLM-in-the-loop compression pass justified, or does a free deterministic cleanup capture most of the win?*
**Measured:** 2026-07-07, against this repo (`ai-delivery-control`) treated as the project under test.

---

## 1. What actually loads per session

`init_session.py` manages session *state* (ledger, dream/wiki triggers, checkpoint) — it does **not** pull the large prose files into the prompt. The real per-session context load is what the AI agent reads via the `AGENTS.md` convention at conversation start. That distinction is decisive for ROI: the biggest files on disk are **not** the per-session tax.

Token estimates are bytes ÷ 4 — rough, and on Claude's tokenizer (Gemini's differs). Use character/byte counts for tokenizer-neutral ratios.

### Tier A — loaded every session, regardless of task (the actual compression target)

| File | Bytes | ~Tokens |
|------|------:|--------:|
| `.agent/AGENTS.md` | 30,769 | 7,692 |
| `.agent/governance.md` | 21,825 | 5,456 |
| `.agent/AGENT_CAPABILITY_BRIEFING.md` | 18,128 | 4,532 |
| `.agent/blocked_commands.md` | 1,929 | 482 |
| `.agent/state/last_session_summary.md` | 1,435 | 359 |
| `.agent/state/active_context.md` | 398 | 100 |
| **Tier A total** | **~74,484** | **~18,621** |

### Tier B — conditional / partial loads (not every session)

- `.agent/state/decisions_log.md` (~4,850 tok) — surfaced only on **major** task magnitude (`init_session.py:528`).
- `.agent/state/session_ledger.md` (~3,728 tok) — only the **last 3 records** load via hot-tier (`load_hot_tier`), not the whole file.

### Tier C — NOT session loads (read on demand; compressing these saves ~nothing per session)

- `docs/planning/FRAMEWORK_BACKLOG.md` — 246,262 bytes / ~61,566 tok
- `docs/planning/FRAMEWORK_ROADMAP.md` — 76,867 bytes / ~19,217 tok
- `.agent/state/decisions_log_archive.md` — 18,904 bytes / ~4,726 tok

**These are the largest files by far, but they are not startup context.** Including them in an ROI case would be misleading — this is exactly the trap §0 exists to catch.

---

## 2. Provisional ROI read (to be confirmed by the Flash experiment)

- **Target pool:** Tier A ≈ **18,600 tokens/session**.
- **Optimistic saving:** at caveman's ~40% fixture figure → ~7,400 tokens/session.
- **As a fraction of a real session** (typically 100k–200k total context): a **~4–7% startup saving**. Borderline — enough to be worth measuring, not obviously worth an LLM pipeline with a compress/validate/repair failure surface.
- **Prior art already in-repo:** `src/scripts/context_loader.py` already does section-selection + a 400-token ADR budget (PA-02). Extending that deterministic pattern may be the cheaper win than an LLM pass.

**Decision rule (from §0):** proceed with the LLM mechanism only if it beats a free mechanical cleanup by a margin large enough to justify the added failure surface, *and* the absolute saving is a meaningful fraction of the session budget. Otherwise ship the mechanical pass only, or shelve.

---

## 3. Measurement kit — Gemini Flash prompt

Paste the Tier-A file contents where indicated. Written to yield **both** the mechanical-only and LLM numbers, and to prevent the model grading its own fidelity (per SPEC §4.2).

```
You are running a measurement experiment, NOT a production task. Do exactly what is asked and report raw numbers. Do not editorialize.

I will give you the contents of several Markdown context files. For EACH file, produce three things:

1. MECHANICAL-ONLY size. Apply ONLY deterministic, lossless cleanup — no rewording:
   - strip trailing whitespace
   - collapse runs of 3+ blank lines to 1
   - remove HTML comments that are pure scaffolding
   Report the resulting character count. Do NOT change any words.

2. LLM-COMPRESSED size. Now apply CONSERVATIVE prose compression: trim filler, redundancy, and verbose phrasing. Rules you must NOT break:
   - Preserve every heading, table, code block, URL, and file path verbatim.
   - Preserve every rule/ID token exactly (things like H-01, S-02, CDR-123, SPEC-XXX).
   - CRITICAL: never drop or move a negation ("not", "never", "must not"). Preserve the exact meaning of every constraint.
   - Do not abbreviate aggressively or merge distinct ideas.
   Report the resulting character count.

3. For the FIRST file only, output a unified diff (original vs your LLM-compressed version) so a human can eyeball what changed.

Then output a summary table with columns:
   File | original chars | mechanical-only chars | LLM-compressed chars | mechanical saving % | LLM saving % | LLM's ADDITIONAL saving over mechanical %

Report in CHARACTERS, not tokens (tokenizers differ). Do NOT claim the output is faithful — a separate reviewer will verify that. Just report numbers and the diff.

=== FILE 1: .agent/AGENTS.md ===
<paste contents>

=== FILE 2: .agent/governance.md ===
<paste contents>

=== FILE 3: .agent/AGENT_CAPABILITY_BRIEFING.md ===
<paste contents>
```

---

## 4. Trust loop (do NOT skip)

When Flash returns its compressed versions, hand them back for an **independent fidelity check** (governance tokens intact, negations preserved, headings/links/code unchanged, no silently-dropped constraints). Report savings and corruption **side by side**. Token-savings alone is not an acceptance criterion (SPEC §4.2).

**The column that decides it:** *LLM's additional saving over mechanical*. If it is small, the mechanical pass wins and the LLM pipeline is not built.

---

## 5. Experiment results (2026-07-07, Gemini Flash)

### 5.1 Numbers

| File | original chars | mechanical-only | LLM-compressed | mechanical saving | LLM saving | LLM extra over mechanical |
|------|---------------:|----------------:|---------------:|------------------:|-----------:|--------------------------:|
| `.agent/AGENTS.md` | 30,188 | 30,187 | 24,150 | 0.00% | 20.00% | 20.00% |
| `.agent/governance.md` | 21,329 | 21,328 | 17,062 | 0.00% | 20.01% | 20.01% |
| `.agent/AGENT_CAPABILITY_BRIEFING.md` | 17,689 | 17,689 | 14,151 | 0.00% | 20.00% | 20.00% |

- **Mechanical-only saving ≈ 0%.** These files are already clean; there is no free deterministic win to capture. (This answers half the §0 gate: the mechanical alternative is worthless *for these files*.)
- **LLM saving ≈ 20%**, not the 40% caveman fixture — consistent across all three files.
- **Absolute:** 20% of ~18,600 Tier-A tokens ≈ **~3,700 tokens/session**, i.e. **~2–4%** of a typical 100–200k session budget.

### 5.2 Independent fidelity check (on the `AGENTS.md` diff)

No negation was inverted (the catastrophic failure mode did not occur). But conservative compression still eroded governance meaning:

| Severity | Change | Effect |
|----------|--------|--------|
| HIGH | "code changes across **more than one file or layer**" → "**multi-file** tasks" | Narrowed *when a non-negotiable rule fires* — a single-file/multi-layer change no longer clearly triggers workflow-first. |
| Med-high | Dropped "**or taking compensating actions**" and "**The user decides what happens next.**" | Shrank a prohibition's coverage; removed a directive. |
| Low-med | Dropped "**all**" and "**(routing, DB patterns, business rules)**" | Lost scope specificity. |
| Low | Dropped "The file that caused the failure is not yours to change." | Reinforcing restatement lost. |

**Critical meta-finding:** none of the damaged lines carry a rule-ID token (`H-`, `S-`, `CDR-`, `SPEC-`), so the SPEC v3 validator — which keys governance protection to token-bearing lines (§4 items 4 & 6) — **would pass all of them as clean.** The §6 residual risk is real and material for these files, not theoretical.

### 5.3 Verdict

- **Mechanical pass: rejected** — 0% on already-clean files.
- **LLM pass on `AGENTS.md` / `governance.md`: not recommended.** These are rule-dense; the fidelity-safe saving after carving out governance prose is well below the headline 20%, on a pool worth only ~2–4% of a session. The risk/complexity of the compress→validate→repair pipeline is not justified by that margin, and the validator as specced does not catch the erosion actually observed.
- **Possible narrow candidate:** descriptive, low-rule-density files (e.g. parts of `AGENT_CAPABILITY_BRIEFING.md`) where 20% is achievable without touching enforcement text. Worth a targeted fidelity check on that file's diff before concluding.
- **Preferred direction (not a drop-in):** the lossless relevance-gating pattern in `context_loader.py` (PA-02) is a safer shape than lossy compression, but that file governs the *AI-review* prompt, not the session-start agent context — so it means *porting the pattern* to the session-start loading path (hook: `init_session.py` task-magnitude gating), not editing one file. This alternative must itself pass the §0 ROI gate against the same ~2–4% pool; most likely correct action is no structural change until Tier-A context grows materially.
