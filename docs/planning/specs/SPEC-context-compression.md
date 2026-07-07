# SPEC: Context-Efficient Memory Compression

**Status:** ON HOLD (v3.2) — §0 ROI gate MEASURED; recommend NOT proceeding with the LLM pipeline for rule-dense files. See §0.1.
**Author:** Claude (spec/architecture) — implementation TBD (Gemini/Antigravity per standing workflow)
**Related:** EFC scaling law research, canonical tool inventory parsimony lever; measurement companion: [SPEC-context-compression-ROI-baseline.md](./SPEC-context-compression-ROI-baseline.md)
**Changelog:**
- v3.2 records the §0 ROI-gate measurement (2026-07-07, Gemini Flash on this repo). Mechanical-only saving ≈ 0% (files already clean); LLM saving ≈ 20% (~3,700 tok/session, ~2–4% of budget); observed governance erosion on non-token lines that the specced validator would NOT catch. Outcome: gate NOT passed for rule-dense files (`AGENTS.md`, `governance.md`); status → ON HOLD. See §0.1.
- v3.1 adds the idempotency rule — a body is never re-compressed as a whole; only content added since the last compression is eligible (§4 item 11) — and clarifies where the tool runs (per-project, on the incorporating project's own context files; §1.1).
- v3 adds a mandatory **§0 ROI gate** (implementation may not proceed until answered), reframes fidelity around *mechanical carve-out of governance lines* rather than post-hoc token validation, and folds in mitigations from an external critical review (Gemini): strict frontmatter parsing (§4.2 mechanism), strict path allowlist + content pre-scan (§4.3), pinned-original backup retention (§4.5 / §5 Q6), line-anchored validation as a secondary net (§4.4), `NO-COMPRESS` fences (§4 item 10), and a content digest in the audit event (§4 item 7). Documents why reasoning-tier escalation was **rejected** in favour of fail-closed abort (§4.4). Records the review disposition in §9.
- v2 revised §4 with mechanics confirmed by direct source review of github.com/JuliusBrussee/caveman (cloned, 177 files inspected), and added two candidate features (§7, §8) found during that pass. v1 was based on marketing copy / search snippets only.

## 0. ROI Gate (BLOCKING — must be answered before any implementation)

This spec proposes an LLM-in-the-loop transform with a non-trivial failure surface (compress → validate → repair → backup → audit). That machinery is only justified if the overhead it removes is materially larger than the risk and complexity it adds. **No code proceeds until the following are measured and recorded here:**

1. **Baseline measurement.** Total token cost of the in-scope static context files (`UNIVERSAL_CONTEXT.md`, `AGENTS_PROJECT.md`, `CLAUDE.md`, `AGENTS.md`, per-project memory/spec files) as loaded at session start, and that figure as a **percentage of the typical session context budget**.
2. **Achievable saving.** Expected reduction from a *conservative* pass (the §5 Q2 default), expressed in tokens and as a percentage of the session budget — not as a percentage of the files themselves. A 41% file reduction on files that are 0.5% of the budget is not worth an LLM pipeline.
3. **Mechanical-alternative comparison.** The saving achievable by a **purely deterministic, non-LLM pass** (strip trailing whitespace, collapse blank-line runs, remove redundant HTML comments, table-whitespace normalisation). If the mechanical pass captures most of the win, it wins by default: it carries none of the fidelity risk this spec spends §4 mitigating.

**Decision rule:** proceed with the LLM mechanism (§4) only if the LLM pass beats the mechanical pass by a margin large enough to justify the added failure surface, *and* the absolute saving is a meaningful fraction of the session budget. Otherwise implement the mechanical pass only, or shelve. This gate exists because neither the original spec nor its external review quantified whether the juice is worth the squeeze.

### 0.1 Gate outcome — MEASURED 2026-07-07 (recommend NOT proceeding for rule-dense files)

The gate was measured against this repo (full data in the [ROI baseline companion](./SPEC-context-compression-ROI-baseline.md), §5). Findings:

1. **Baseline.** The per-session ("Tier A") load is **~18,600 tokens** — `AGENTS.md`, `governance.md`, `AGENT_CAPABILITY_BRIEFING.md`, and small state files. The largest files on disk (`FRAMEWORK_BACKLOG.md` ~61k, `FRAMEWORK_ROADMAP.md` ~19k) are **read on demand, not per session** — compressing them saves ~nothing per session.
2. **Mechanical-alternative saving ≈ 0%.** The in-scope files are already clean (no whitespace/blank-run/scaffolding to strip). There is no free deterministic win to capture.
3. **LLM saving ≈ 20%** (Gemini Flash, conservative prompt), i.e. **~3,700 tokens/session ≈ 2–4%** of a typical 100–200k session budget — not the 41% caveman fixture.
4. **Fidelity failed on rule-dense files.** No negation was inverted, but conservative compression still narrowed a non-negotiable rule's trigger ("more than one file or layer" → "multi-file"), dropped a prohibited action ("compensating actions"), and removed scope qualifiers. **Critically, none of the damaged lines carry a rule-ID token, so the validator specced in §4 (items 4 & 6) would pass all of them as clean** — the protections are mis-targeted for the actual governance prose in these files.

**Decision:** the gate is **NOT passed** for the rule-dense governance files (`AGENTS.md`, `governance.md`). The fidelity-safe saving after carving out governance prose is well below the headline 20%, on a pool worth only ~2–4% of a session — the compress/validate/repair failure surface is not justified, and the validator as designed does not catch the erosion actually observed. **Status → ON HOLD.**

**Not fully closed / possible narrow follow-up:** low-rule-density descriptive files (e.g. parts of `AGENT_CAPABILITY_BRIEFING.md`) may achieve ~20% without touching enforcement text — worth a targeted per-file fidelity check before any adoption.

**Preferred alternative *direction* (not a drop-in change):** the lossless relevance-gating pattern already demonstrated in `src/scripts/context_loader.py` (PA-02 section-selection + budgeted ADR injection) is the safer shape of solution than lossy compression — load only the context relevant to the task instead of rewriting it. **Caveat:** that file governs the *AI-review* prompt, not the session-start agent context (`AGENTS.md`/`governance.md` are read via the `AGENTS.md` convention on a different loading path). So this means *porting the section-gating pattern to the session-start path* — real work, not a one-file edit — with a natural hook in `init_session.py`'s existing task-magnitude gating (it already surfaces `decisions_log.md` only for major tasks). **This alternative must itself pass the §0 ROI gate:** it attacks the same ~2–4%-of-session pool and is non-trivial to build, so the most likely correct action is *no structural change until Tier-A context grows materially*.

## 1. Problem

Harness users accumulate context overhead every session: `UNIVERSAL_CONTEXT.md`, `AGENTS_PROJECT.md`, `CLAUDE.md`, and per-project memory/spec files are read in full on every session start. As these files grow (spec history, prohibition tables, coupling declarations), fixed per-session token cost grows with them — independent of whether that session touches the relevant content. This is pure overhead: cost paid every session, value realized only when the content is relevant.

This is a distinct problem from gate/audit output verbosity, which must remain precise and is explicitly out of scope here (see §3).

### 1.1 Where it runs

The tool ships as part of the harness but operates **per-project, on the incorporating project's own context files** — because the per-session startup tax is paid inside each project, and the in-scope files (`CLAUDE.md`, `UNIVERSAL_CONTEXT.md`, `AGENTS_PROJECT.md`, per-project memory, `.agent/state/decisions_log.md`) live there. The harness's own development repo is simply one such project: a maintainer can point the same tool at the harness repo's `AGENTS.md`/spec files with no separate code path. **Consequence:** the exact-path allowlist (§4 item 1) is therefore *per-project configuration*, not one global hardcoded list — each project declares which of its own files are eligible.

## 2. Goals

- Reduce fixed per-session context-loading token cost for harness memory/context files.
- Preserve 100% of semantic content — no silent loss **or inversion** of constraints, decisions, or nuance.
- Keep the mechanism auditable: a human-readable original must always be recoverable and diffable against the compressed version.
- Fit within existing harness patterns (gate system, audit events, fail-closed defaults) rather than introducing a parallel unaudited pipeline.

## 3. Non-Goals

- Compressing gate output, audit events (`GATE_SKIPPED`, etc.), rebuttal protocol text, or any structured/machine-parsed output. These require full precision for downstream consumers and the Semantic Invariant Registry (T1-G-16); compression risk (point-vs-interval collapse) is exactly the failure mode that registry exists to prevent.
- Compressing code, config, or any non-prose file (`.py`, `.json`, `.yaml`, etc.) — never in scope.
- Runtime/session-level "terse mode" for agent responses. This is a build-time/maintenance-time transform on static context files only.

## 4. Proposed Mechanism

Adapted from `caveman-compress` (source: `skills/caveman-compress/scripts/{compress,validate,detect}.py`), scoped down and integrated into harness conventions. Mechanics below are confirmed from source, not marketing copy.

**Fidelity philosophy (v3):** the spec's own §4 item 2 establishes that *prompt instructions alone are not reliable* for preserving structure — which is why frontmatter is mechanically excluded rather than merely instructed. That principle applies equally to governance rules and their surrounding semantics. Therefore fidelity is achieved primarily by **mechanical carve-out** of anything sensitive (frontmatter, governance-rule lines, fenced blocks) so it never reaches the LLM, and only secondarily by post-hoc validation. Validation is a detection net, not the guarantee.

1. **Scope restriction via strict exact-path allowlist (source: `detect.py`, hardened per review §3).** Do **not** use an "allow any `.md` except denylist" approach. The harness maintains a **hardcoded exact-path allowlist** of known-safe context files (e.g. `AGENTS.md`, `CLAUDE.md`, `docs/planning/FRAMEWORK_BACKLOG.md`, `.agent/state/decisions_log.md`, named memory files). Anything not on the list is out of scope, full stop — no content-sniffing of arbitrary files.
2. **Frontmatter carve-out via strict parser (source: `compress.py: split_frontmatter`, hardened per review §2).** YAML frontmatter is carved off the file *before* the LLM ever sees it, and re-prepended verbatim after. **Use a robust frontmatter parser (e.g. `python-frontmatter`), not a bare regex.** The parser must assert the `---` block is at the absolute start of the file; if the file cannot be cleanly parsed as `frontmatter + body`, **abort and refuse to compress** rather than guess a boundary. Rationale (from caveman comments): the compression model "has a habit of stripping or rewriting [frontmatter] despite preserve-structure rules in the prompt" — prompt instructions are not reliable; mechanical exclusion is.
3. **Sensitive-data hard refuse — path AND content (source: `compress.py: is_sensitive_path`, extended per review §3).** Two layers, both checked *before any LLM call*:
   - **Path layer:** regex denylist on filename/path components (`credentials`, `secret`, `*.pem`, `*.key`, `.ssh/`, `.aws/`, tenant-data paths), with no override flag. Given the strict allowlist in item 1 this is now defence-in-depth rather than the primary control.
   - **Content pre-scan:** a fast pre-flight regex scan of the file body for secret-shaped material (`sk-ant-`, `Bearer `, `-----BEGIN [A-Z ]*PRIVATE KEY`, high-entropy tokens). Any hit → hard refuse. **This is a backstop, not DLP** — it will not catch all PII or tenant data; the allowlist (item 1) remains the real protection. Its purpose is to catch an allowlisted file that has accidentally accreted a secret.
4. **Compress → validate → bounded fix-loop (source: `compress.py: compress_file`, `validate.py`):**
   - Compress full body (frontmatter and `NO-COMPRESS` fences excluded per items 2 and 10) via one LLM call.
   - Reject and abort (no backup written) if output is empty or byte-identical to input — signals refusal or no-op, not success.
   - Write backup, **read it back and byte-compare against the in-memory original**; if mismatch (disk full, AV interference, encoding issue), delete the bad backup and abort before touching the source file at all.
   - Validate structural invariants: heading count/text (error/warning split), fenced code blocks byte-exact (handles nested and variable-length fences), URL set equality, file-path set equality, inline-backtick spans as a multiset (catches *partial* loss, e.g. "lost 2 of 5 occurrences"), bullet-count drift >15%.
   - **Line-anchored governance validation (v3, secondary net per review §1).** For every line in the original containing a protected governance token (see item 6), require that the **entire line survives verbatim** in the compressed output. This defends against *semantic inversion* around tokens (e.g. "Do **not** apply H-01" → "Apply H-01"), which a bare multiset check passes. Note this only protects meaning *on token-bearing lines*; token-free prose remains protected only by the conservative default (§5 Q2) — which is why carve-out (items 2, 10) is preferred for anything that must never change. The general failure mode (meaning inverted around a preserved item) also applies to URLs and paths, not just governance tokens.
   - On validation failure: bounded fix-loop (2 retries), and **the fix prompt explicitly forbids recompression** — "ONLY fix the listed errors — leave everything else exactly as-is," with per-error-type repair instructions. Structurally close to the harness's existing rebuttal protocol.
   - Exhausted retries → restore original, delete backup, fail closed. No partially-validated file is ever left in place.
   - **Repair-tier decision (v3): fail closed, do not escalate.** The external review proposed escalating failed repairs to a reasoning-tier model. **Rejected.** A stronger model lowers the *probability* of over-correction but does not close the actual gap — the validator only inspects a fixed, narrow invariant set, so repair-induced damage to *unvalidated* prose is invisible regardless of model tier. It also contradicts the fast-tier cost rationale (item 9): if reasoning-tier tokens are acceptable on repair, they undercut the case for a fast-tier initial pass. The conservative, spec-consistent choice is to **abort and fail closed** on exhausted retries (the file simply stays uncompressed) rather than throw a more capable model at silently-lossy repair. Escalation may be reconsidered only if the ROI gate (§0) shows the saving is large enough to warrant it.
5. **Backup placement and retention (source: `compress.py: backup_dir_for`, extended per review §5).** Backups are stored **out-of-tree** in project-local `.agent/state/backups/` (Git-ignored, not scanned by context loaders) to prevent in-tree `.original.md` files being re-ingested by skill auto-loaders. Retention is garbage-collected inside `context_compressor.py`: before writing a new backup, prune older backups for the target file. **The very first (pristine, pre-first-compression) backup per file is pinned and never evicted**; a rolling window (e.g. keep the 3 most recent *plus* the pinned original, or delete unpinned backups older than 30 days) applies to the rest. Pinning the original directly counters the "boiled-frog" recoverability decay (§6 risk): a naive "keep 3 most recent" would eventually evict the true original.
6. **Harness-specific invariants (exact-match errors, not warnings):** all occurrences of Coupling Decision Record IDs (`CDR-\d{3}`), spec story/task IDs (`SPEC-\w+-\w+` or `SPEC-\w+`), prohibition rules (`H-\d{2}`, `S-\d{2}`, `C-\d{2}`, `G-\d{2}`), and exact markdown header rule titles must match the original multiset exactly — **and** carry line-anchored validation per item 4.
7. **Audit integration:** compression runs emit a standard lifecycle audit event (`event_type: context_compressed`) to `harness_events.jsonl` recording target file path, timestamp, input/output token sizes, savings delta, validation/repair results, **and a content digest (SHA-256) of both the pre- and post-compression bodies** so the audit trail can later prove exactly what changed (forensic recoverability).
8. **No auto-recompression on every edit.** Compression is an explicit, user- or hook-triggered maintenance action, not a background process silently rewriting files agents rely on for behavior.
9. **Fast-tier model routing.** LLM calls for compression and repair are routed to the configured `fast` tier model (e.g. Gemini Flash) for cost. (See item 4's rejection of reasoning-tier escalation.)
10. **`NO-COMPRESS` fences (v3, per review §6).** Authors may wrap highly-nuanced prose in `<!-- NO-COMPRESS -->` … `<!-- /NO-COMPRESS -->`. The script carves these blocks out alongside frontmatter (item 2) before the LLM call and re-injects them verbatim after. This is opt-in defence-in-depth against boiled-frog flattening of architectural "why". **Limitation:** it protects only what an author remembered to fence; it is not a substitute for the conservative default or the ROI-driven decision not to compress at all.
11. **No re-compression of already-compressed content (v3.1, idempotency).** A body that has already been compressed must never be fed through the LLM again as a whole — repeated passes are the direct cause of the boiled-frog degradation (§6). Mechanism:
    - On a successful compression, the tool stamps the file with a marker recording the compression: a frontmatter field (e.g. `context_compressed: { at: <timestamp>, body_sha256: <hash-of-compressed-body> }`). The marker lives in frontmatter so it is itself carved out (item 2) and never re-processed.
    - On any subsequent run, the tool computes the current body hash and compares it to the stored `body_sha256`. **If unchanged, skip the file entirely** (it is already at its compressed state — no LLM call, no cost).
    - If the body *has* changed since the marker, only the **net-new / edited content** is eligible for compression; previously-compressed regions are treated as carve-outs (like `NO-COMPRESS`, item 10) and passed through verbatim. Determining "net-new" is a diff against the last compressed state.
    - **Fail closed:** if the tool cannot reliably tell which content is new (missing/corrupt marker, ambiguous diff), it does **not** re-compress the whole body — it either compresses nothing or refuses and reports, never silently re-chews old content.
    - This makes compression *convergent*: running the tool repeatedly on an unedited file is a guaranteed no-op, and running it after edits only ever touches the new material.

### 4.1 Fidelity evidence (source: `tests/caveman-compress/claude-md-project.{md,original.md}`)

Diffed a real before/after pair from their test fixtures: 7,782 → 4,607 bytes (~41% reduction). All file paths, version numbers, and technical facts survived exactly. One defect found: a paragraph describing both an architectural pattern and a directory layout was compressed into *two* separate lists, introducing structure not present in the original (mild content duplication, not loss). This confirms the transform is **interpretive, not mechanical** — supporting the carve-out-first fidelity philosophy above and the conservative default (§5, Q2).

### 4.2 What their eval harness explicitly does NOT measure (source: `evals/README.md`)

Their own docs state the token-delta measurement has no fidelity check: "A skill that replies `k` to everything would score −99% and 'win'." Any harness adoption must pair the token-delta measurement with the invariant validator (§4 items 4/6) as a hard gate — token savings alone is not an acceptance criterion.

## 5. Resolved Design Decisions

1. **Audit Event Type**: `CONTEXT_COMPRESSED` is logged as a standard lifecycle event type (`event_type: "context_compressed"`) in `harness_events.jsonl` rather than an H/S/C/G policy verdict.
2. **Compression Aggressiveness**: single conservative default (whitespace/filler/redundancy trimming) while preserving formatting structure, tables, and rules verbatim, avoiding aggressive abbreviation that risks semantic collapse.
3. **Fix-Loop Architecture**: validation checks and bounded repair loop (up to 2 retries) implemented in `.agent/scripts/context_compressor.py`, exposed as an on-demand CLI tool.
4. **Enforcement Gating**: compression runs as an explicit maintenance command, orthogonal to enforcement postures, rolling back automatically to the original backup on any validation failure.
5. **Harness-Specific Invariants**: validator strictly verifies Coupling IDs, Spec IDs, prohibition tags, and rule title headers as an exact multiset **and** line-anchored.
6. **Backup Retention (v3)**: pinned pristine original + rolling window for the rest; GC internal to `context_compressor.py`.
7. **Fidelity mechanism (v3)**: mechanical carve-out (frontmatter, `NO-COMPRESS` fences, governance lines validated verbatim) is the primary fidelity guarantee; post-hoc invariant validation is the secondary net.
8. **Idempotency (v3.1)**: compression is convergent — a marker + body hash ensures already-compressed content is never re-processed; only net-new content since the last run is eligible.
9. **Execution scope (v3.1)**: per-project maintenance action on the incorporating project's own context files (§1.1); the allowlist is per-project config, not a single global list.

## 6. Known Residual Risks (not fully eliminated)

- **Token-free semantic inversion.** Line-anchored validation (§4 item 4) protects meaning only on lines bearing a governance token. Inversion of a constraint expressed in ordinary prose ("do not delete the tenant database") is caught only by the conservative default, not guaranteed. Mitigation: authors fence such content (§4 item 10), or the ROI gate concludes not to LLM-compress at all.
- **Content pre-scan is not DLP.** §4 item 3's regex catches known secret shapes, not arbitrary PII/tenant data. The strict allowlist is the real control.
- **Fenced protection is opt-in.** For any *single* pass, degradation of unfenced nuance is bounded only by the conservative default. Note that the primary boiled-frog driver — *repeated* passes over the same content — is now closed by the idempotency rule (§4 item 11): each region is compressed at most once, so quality cannot ratchet down over many runs.

## 7. Explicitly Deferred

- Any equivalent of `caveman-code`/`cavemem` (full agent-output compression, cross-session memory stores) — out of scope.
- Multi-language / classical-register compression modes — not relevant to harness context files.

---

## 8. Candidate Feature: MCP Tool-Description Compression

**Source:** `src/mcp-servers/caveman-shrink/` — a stdio proxy between agent and upstream MCP server, intercepting `tools/list` (and `prompts/list`/`resources/list`) responses and compressing only `description` field(s). Configurable via `CAVEMAN_SHRINK_FIELDS`.

**Why relevant:** a direct implementation of the "canonical tool inventory parsimony" EFC lever. Every session pays the token cost of every connected tool's full description regardless of use — same fixed-overhead problem as §1, applied to tool catalogs.

**Boundary worth adopting as-is:** their v1 is deliberately conservative — request bodies and `tools/call` *results* pass through untouched; only catalog metadata is compressed. Compressing what a tool *returns* is a different correctness-risk category from compressing what a tool *is described as*. Non-negotiable in a harness version too.

**Open question:** does the harness's MCP tool surface have enough tool-count/description-length to justify this, or is it premature until the inventory grows? Recommend deferring to a follow-up spec.

## 9. Candidate Feature: Structured Output Contracts for Review Subagents

**Source:** `skills/cavecrew/SKILL.md` — fixed machine-parseable output grammars for delegated subagents (investigator `path:line — symbol — note`; builder terminating in a fixed token set `too-big.`/`needs-confirm.`/`ambiguous.`/`regressed.`; reviewer `path:line: <severity-emoji> <problem>. <fix>.`).

**Why relevant:** subagent tool-results are injected into main context *verbatim*, so free-prose subagent output is a recurring per-delegation context cost — the §1 problem applied to the adversarial review roster's output. A contract-constrained reviewer format would reduce per-round cost **and** make findings grep-able for audit.

**Distinction from §4:** this is a *format constraint* on how output is produced, not a compression pass over existing output. Lower implementation risk (no LLM compress/validate/fix loop) but touches the adversarial review roster's core contract — higher-sensitivity surface than memory files.

**Open question:** would a fixed-grammar reviewer format weaken the qualitative rationale the rebuttal protocol expects, or can severity/fix stay one-line with rationale-on-request preserved? Needs its own spec; recommend a separate follow-up, not folded into §4.

---

## 10. External Review Disposition (v3)

An external critical review (Gemini) identified six weaknesses. Disposition:

| # | Weakness | Verdict | Where addressed |
|---|----------|---------|-----------------|
| 1 | Semantic inversion (multiset blind spot) | Accepted — strongest point | §4 item 4 (line-anchored), fidelity philosophy, §6 residual |
| 2 | Frontmatter regex fragility | Accepted (failure mode was somewhat overstated; fix is cheap) | §4 item 2 (strict parser) |
| 3 | Filename-based security insufficient | Accepted | §4 items 1 & 3 (allowlist + content pre-scan) |
| 4 | Fast-tier hallucination fix-loop | Accepted risk; proposed *mitigation* (reasoning-tier escalation) **rejected** in favour of fail-closed | §4 item 4 |
| 5 | Backup proliferation | Accepted (minor) | §4 item 5 (pinned-original retention/GC) |
| 6 | Boiled-frog degradation | Accepted; repeated-pass driver now closed | §4 item 10 (fences) + item 11 (idempotency), §6 residual |

**Not raised by the review, added here:** the §0 ROI gate (is an LLM pass justified at all vs. a mechanical one?), the observation that semantic inversion generalises beyond governance tokens to URLs/paths, and the audit content digest (§4 item 7).

---
**Per standing protocol:** this spec stops here for review and approval. No code, schema, or script implementation proceeds until sign-off — and specifically, not until §0 is answered. §8 and §9 are flagged as candidate follow-up specs, not part of this spec's implementation scope.
