# SPEC: Context-Efficient Memory Compression

**Status:** DRAFT v2 — awaiting review/approval before implementation
**Author:** Claude (spec/architecture) — implementation TBD (Gemini/Antigravity per standing workflow)
**Related:** EFC scaling law research, canonical tool inventory parsimony lever
**Changelog:** v2 revises §4 with mechanics confirmed by direct source review of github.com/JuliusBrussee/caveman (cloned, 177 files inspected), and adds two candidate features (§7, §8) found during that pass. v1 was based on marketing copy / search snippets only.

## 1. Problem

Harness users accumulate context overhead every session: `UNIVERSAL_CONTEXT.md`, `AGENTS_PROJECT.md`, `CLAUDE.md`, and per-project memory/spec files are read in full on every session start. As these files grow (spec history, prohibition tables, coupling declarations), fixed per-session token cost grows with them — independent of whether that session touches the relevant content. This is pure overhead: cost paid every session, value realized only when the content is relevant.

This is a distinct problem from gate/audit output verbosity, which must remain precise and is explicitly out of scope here (see §4).

## 2. Goals

- Reduce fixed per-session context-loading token cost for harness memory/context files.
- Preserve 100% of semantic content — no silent loss of constraints, decisions, or nuance.
- Keep the mechanism auditable: a human-readable original must always be recoverable and diffable against the compressed version.
- Fit within existing harness patterns (gate system, audit events, fail-closed defaults) rather than introducing a parallel unaudited pipeline.

## 3. Non-Goals

- Compressing gate output, audit events (`GATE_SKIPPED`, etc.), rebuttal protocol text, or any structured/machine-parsed output. These require full precision for downstream consumers and the Semantic Invariant Registry (T1-G-16); compression risk (point-vs-interval collapse) is exactly the failure mode that registry exists to prevent.
- Compressing code, config, or any non-prose file (`.py`, `.json`, `.yaml`, etc.) — never in scope.
- Runtime/session-level "terse mode" for agent responses. This is a build-time/maintenance-time transform on static context files only.

## 4. Proposed Mechanism

Adapted from `caveman-compress` (source: `skills/caveman-compress/scripts/{compress,validate,detect}.py`), scoped down and integrated into harness conventions. Mechanics below are confirmed from source, not marketing copy.

1. **Scope restriction (source: `detect.py`).** Extension allowlist (`.md .txt .markdown .rst` etc.) / denylist (`.py .js .json .yaml .sql ...`); extensionless files classified by content heuristic (JSON/YAML sniff, then a code-line-pattern ratio >0.4 → code). Harness version should hardcode the allowlist to the specific memory files in scope rather than running content-sniffing on arbitrary files.
2. **Frontmatter carve-out (source: `compress.py: split_frontmatter`).** YAML frontmatter is regex-split off the file *before* the LLM ever sees it, and re-prepended verbatim after. Rationale in their comments: the compression model "has a habit of stripping or rewriting [frontmatter] despite preserve-structure rules in the prompt" — i.e. prompt instructions alone are not reliable; mechanical exclusion is. **Adopt this pattern directly** for any harness metadata block (spec IDs, prohibition-series tags, coupling declaration fields) that must never pass through the compression call at all.
3. **Sensitive-path hard refuse (source: `compress.py: is_sensitive_path`).** Regex denylist on filename/path components (`credentials`, `secret`, `*.pem`, `*.key`, `.ssh/`, `.aws/`, etc.) checked *before any file read*, with no override flag — compression ships file bytes to a third-party API, so the tool refuses outright rather than warn. Given GymBase is multi-tenant, the harness version needs an equivalent refuse-list, extended to cover anything under tenant-data paths, not just credential-shaped filenames.
4. **Compress → validate → bounded fix-loop (source: `compress.py: compress_file`, `validate.py`):**
   - Compress full body (frontmatter excluded per #2) via one LLM call.
   - Reject and abort (no backup written) if output is empty or byte-identical to input — signals refusal or no-op, not success.
   - Write backup, **read it back and byte-compare against the in-memory original**; if mismatch (disk full, AV interference, encoding issue), delete the bad backup and abort before touching the source file at all.
   - Validate structural invariants: heading count/text (error/warning split), fenced code blocks byte-exact (handles nested and variable-length fences), URL set equality, file-path set equality, inline-backtick spans as a multiset (catches *partial* loss, e.g. "lost 2 of 5 occurrences" — not just presence/absence), bullet-count drift >15%.
   - On validation failure: bounded fix-loop (2 retries), and **the fix prompt explicitly forbids recompression** — "ONLY fix the listed errors — leave everything else exactly as-is," with per-error-type repair instructions (e.g. "Code block mismatch: find the exact code block in ORIGINAL, restore it in COMPRESSED"). This is a scoped-remediation pattern, structurally close to the harness's existing rebuttal protocol.
   - Exhausted retries → restore original, delete backup, fail closed. No partially-validated file is ever left in place.
5. **Backup placement (source: `compress.py: backup_dir_for`).** Backups are stored **out-of-tree** (`~/.local/share/caveman-compress/backups/`, not beside the source), because in-tree `.original.md` files were being re-ingested by skill auto-loaders as live context — a real bug they hit and fixed. Harness version should place backups outside any path the harness itself scans for context/spec files, for the same reason.
6. **Harness-specific invariants to add to the validator:** the above validator has no concept of prohibition IDs (H/S/C/G refs), spec IDs, or coupling-declaration fields. These must be added as additional exact-match invariants (errors, not warnings) before this is safe to run over `AGENTS.md` or spec files — the source validator was written for generic markdown, not governance documents.
7. **Audit integration:** compression runs emit a harness audit event (new event type, e.g. `CONTEXT_COMPRESSED`) recording file, timestamp, token delta, and validation result — consistent with existing `GATE_SKIPPED` precedent of making harness-internal transforms visible rather than invisible.
8. **No auto-recompression on every edit.** Compression is an explicit, user- or hook-triggered maintenance action, not a background process silently rewriting files agents rely on for behavior.

### 4.1 Fidelity evidence (source: `tests/caveman-compress/claude-md-project.{md,original.md}`)

Diffed a real before/after pair from their test fixtures: 7,782 → 4,607 bytes (~41% reduction). All file paths, version numbers, and technical facts survived exactly. One defect found: a paragraph describing both an architectural pattern and a directory layout was compressed into *two* separate lists, introducing structure not present in the original (mild content duplication, not loss). This confirms the transform is **interpretive, not mechanical** — supports a conservative-default posture (§5, Q2) and reinforces why harness-specific invariants (#6 above) are necessary rather than optional.

### 4.2 What their eval harness explicitly does NOT measure (source: `evals/README.md`)

Their own docs state the token-delta measurement has no fidelity check: "A skill that replies `k` to everything would score −99% and 'win'." This is an explicit gap in their tooling, not an oversight to inherit. Any harness adoption of this pattern must pair the token-delta measurement with the invariant validator (§4 item 4/6) as a hard gate — token savings alone is not an acceptance criterion.

## 5. Open Questions (for review)

1. Should `CONTEXT_COMPRESSED` be a new audit series entry (H/S/C/G) or a separate lightweight event class, given it's a maintenance action rather than a governance decision?
2. Compression aggressiveness: should this support levels (light trim only vs. more aggressive fragment-style compression), or should the harness ship one conservative default (filler/redundancy removal only, no fragment/abbreviation style) to minimize ambiguity risk in a governance context? (§4.1 fidelity evidence favors conservative-default.)
3. Where does the bounded fix-loop logic live — as a harness-owned script, or should it reuse/wrap the existing three-arm eval harness pattern for measuring compression quality over time?
4. Should this be gated behind the existing enforcement posture model (strict/ratchet/observe), or is it orthogonal since it doesn't affect commit classification?
5. What's the harness-specific invariant list for §4 item 6 — minimally: prohibition IDs, spec IDs, coupling declaration fields, gate names. Confirm/extend before implementation.

## 6. Explicitly Deferred

- Any equivalent of `caveman-code`/`cavemem` (full agent-output compression, cross-session memory stores) — out of scope; the harness's existing audit/rebuttal precision requirements make blanket output compression a poor fit.
- Multi-language / classical-register compression modes — not relevant to harness context files.

---

## 7. Candidate Feature: MCP Tool-Description Compression

**Source:** `src/mcp-servers/caveman-shrink/` — a stdio proxy that sits between the agent and an upstream MCP server, intercepting `tools/list` (and `prompts/list`/`resources/list`) responses and compressing only the `description` field(s). Configurable via `CAVEMAN_SHRINK_FIELDS`.

**Why relevant:** this is a direct, working implementation of the "canonical tool inventory parsimony" EFC lever already identified as a strategic lever. Every session pays the token cost of every connected tool's full description, regardless of whether that tool is used — same fixed-overhead problem as §1, applied to tool catalogs instead of memory files.

**Boundary worth adopting as-is:** their v1 is deliberately conservative — request bodies and `tools/call` *results* pass through completely untouched; only the catalog metadata is compressed. Their stated rationale: they don't want to risk silently mutating the data the upstream returns to the model. This boundary should be non-negotiable in a harness version too — compressing what a tool *returns* is a correctness risk category entirely different from compressing what a tool *is described as*.

**Open question:** does the harness's MCP tool surface (subagent roster, checker invocations) have enough tool-count/description-length to justify this, or is it premature optimization until the tool inventory grows? Recommend deferring to a follow-up spec rather than bundling with §4.

## 8. Candidate Feature: Structured Output Contracts for Review Subagents

**Source:** `skills/cavecrew/SKILL.md` — defines fixed, machine-parseable output grammars for delegated subagents, e.g. investigator output as `path:line — symbol — note`, builder output terminating in one of a fixed token set (`too-big.` / `needs-confirm.` / `ambiguous.` / `regressed.`), reviewer output as `path:line: <severity-emoji> <problem>. <fix>.`

**Why relevant:** their stated rationale is that subagent tool-results get injected into main context *verbatim*, so free-prose subagent output is a recurring context-budget cost per delegation — the same overhead problem as §1, applied to the harness's adversarial review roster's output instead of static files. A contract-constrained reviewer format would likely reduce context cost per review round **and** make findings grep-able for audit purposes, which free prose is not.

**Distinction from §4/caveman-compress:** this is not a compression *pass* over existing output — it's a *format constraint* on how review subagents produce output in the first place. Lower implementation risk than §4 (no LLM-based compress/validate/fix loop needed) but touches the adversarial review roster's core contract, which is a higher-sensitivity surface than memory files.

**Open question:** would a fixed-grammar reviewer format weaken the qualitative rationale the rebuttal protocol currently expects reviewers to provide, or can severity/fix stay one-line while rationale-on-request is preserved (their own "auto-clarity" carve-out drops terse mode for security findings and architectural disagreements)? This likely needs its own spec given it changes reviewer behavior, not just file handling — recommend as a separate follow-up, not folded into §4's implementation.

---
**Per standing protocol:** this spec stops here for review and approval. No code, schema, or script implementation proceeds until sign-off. §7 and §8 are flagged as candidate follow-up specs, not part of this spec's implementation scope.
