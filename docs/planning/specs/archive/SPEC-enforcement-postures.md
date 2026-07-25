# SPEC: Gate Enforcement Postures (T1-G-18)

**Status**: APPROVED — multi-persona review reconciled & synchronized
**Author**: Claude (spec/architecture) — implementation Gemini/Antigravity (v1.4.12)
**Tracked under**: T1-G-18
**Related:** T1-G-13 (GateContext) ✅, T1-G-14 (Capability Calibration) ✅, T1-B-12 (CDR ledger — brownfield baseline snapshot precedent) ✅, `outer_loop.mode` (existing posture precedent for spec gates), HIB-053 (phantom completion — informs baseline tamper resistance)
**Changelog:**
- v1.0 initial draft. Informed by direct source review of `architecture_checks.py`, `ai_review.py`, `gate_context.py`, `capability_calibration.py`, `route_decision.py`, `audit_logger.py`, and `config.yaml.template` (2026-07-08).
- v1.1 (Claude, 2026-07-21): Added `Tracked under` field, `Assumptions` section, explicit severity map for `architecture_checks.py`, `TYPE_CHECKING_CAST` tag, and modulation order pipeline clarification.
- v1.2 (Gemini, 2026-07-24): Restructured to satisfy `check_spec.py` Pass 1 criteria (folded goals into `Bounded Scope & Out of Scope`, resolved pending assumptions, added Gherkin Acceptance Criteria, renumbered §5 subsections to §5.1–§5.11, and updated internal cross-references).
- v1.3 (Gemini/Claude, 2026-07-24): Multi-persona review reconciliation & scenario synchronization (canonical JSON hashing, AST entry indexing & fast-path skip condition, shallow-clone lapse fallback, test-only TTY monkeypatching, POSTURE_EXPIRED_WARNING banner copy, H-series session-level conduct scoping, GateContext 1.x schema version compatibility, and verbatim Acceptance Criteria synchronization across all 7 scenarios).

---

## 0. Motivation Gate (context, not blocking)

External feedback (2026-07-08): can the harness be adopted on an existing codebase that was not built under it, or does it overwhelm adopters with every architectural finding at once? Direct evidence says the concern is real: GymBase — the harness's *own* reference implementation, written broadly to its patterns — surfaced 129 architectural violations during checker refinement. A mature brownfield codebase pointed at the current gates will hit a wall of hundreds of blocking findings on day one and reasonably conclude the harness is unusable, when the correct conclusion is that the codebase needs incremental hardening.

This is not a hypothetical adoption problem; it is the primary adoption path for any real organisation. Greenfield-only governance tooling has a market of approximately zero enterprises.

---

## 1. Problem

The harness's enforcement gates are binary: a finding blocks, or the gate is bypassed entirely. Source review confirms four specific defects this creates:

1. **`architecture_checks.py` blocks on `all_errors` regardless of severity.** It already tags each `ArchViolation` `WARN` vs `FAIL` (via fragile substring matching on message text — `"coupling"`/`"lifespan"`/`"nameerror"` → WARN, everything else → FAIL), then ignores that distinction: any error at all → `sys.exit(1)`. The severity model exists but is dead weight at the decision point.
2. **There is no middle state between "everything blocks" and "gate off".** The only relief valve is `SKIP_AI_REVIEW=1` / a `.skip-ai-review` file — advertised in the FAIL message itself — which disables the AI review gate wholesale with no expiry, no config visibility, and no posture semantics. It logs a `GATE_SKIPPED` verdict but is otherwise ungoverned. This is the "parking" failure mode already shipped.
3. **Two gates block independently.** `architecture_checks.py` exits 1 on its own findings before `ai_review.py` ever consumes GateContext. Any brownfield accommodation applied only in the AI review path leaves adopters blocked at the deterministic gate — which is exactly where the violation wall lives.
4. **No mechanism distinguishes pre-existing debt from newly introduced debt.** An agent's change to one file can be blocked by violations in fifty untouched files. The CDR reconciler solved this locally for coupling (T1-B-12: brownfield baseline snapshot, tolerated-vs-accepted status); no equivalent exists for the general gate surface.

---

## 2. Bounded Scope & Out of Scope

### In-Scope (Goals)
- One gate mechanism, configurable to serve three codebase categories: greenfield/compliant (`strict`), brownfield-improving (`ratchet`), and pre-adoption assessment (`observe`).
- Full-strength detection in all postures; only *disposition* (exit code blocking behavior) is modulated. Audit trails remain identical across postures.
- Incremental brownfield hardening: pre-existing violations are mechanically grandfathered in `.agent/baseline.json`; touched files lose their grandfather clause ("you touch it, you own it").
- Governed enforcement state: posture lives in versioned `.agent/config.yaml`, changes are git-visible, assessment mode (`observe`) requires a mandatory expiry date (max 90 days).
- Invariant floor: H-series (hard safety) prohibitions are immune to all posture modulation, calibration weights, or rule overrides.
- Absorb and retire the ungoverned `.skip-ai-review` / `SKIP_AI_REVIEW=1` bypass.

### Out-of-Scope (Non-Goals)
- Weakening detection coverage in any posture (scans always execute at full strength).
- Per-hunk grandfather tracking (file-level scoping only, per resolved decision §7 D2).
- Changing the spec-gate posture system (`outer_loop.mode`); this spec defines only the compatibility matrix (§5.8).
- Runtime or per-commit posture switching by AI agents; posture configuration is managed exclusively by the human operator.
- Migrating consumer projects or GymBase (consumer adoption follows framework delivery).

---

## 3. Assumptions

* `[Resolved: A checker can identify an enclosing function/class body for most violations, making the region-hash grandfather mechanism (§5.2) precise rather than whole-file in the common case. Confirmed false in general — the whole-file fallback (§8) is the accepted degraded path when a checker can't isolate a region.]`
* `[Resolved: .agent/config.yaml remains the single source of truth for enforcement configuration — no per-directory or per-file posture overrides are introduced by this spec. Per-rule overrides (§5.6) are additive to, not a replacement for, the single repo-level posture.]`
* `[Resolved: AGENT_ID is reliably set in the environment whenever an agent is driving execution, enabling baseline.py's human-only guard (§5.2) to reject agent-driven baseline generation.]`
* `[Resolved: GATE_ADVISORY audit-log volume under a busy ratchet posture is tracked under HIB-078 to evaluate batching and rotation requirements if high advisory event volume occurs.]`

---

## 4. Acceptance Criteria

### Scenario 1: Posture Resolution and Fail-Safe Defaults
Given a project executing the pre-commit review gate or architectural checks
When `.agent/config.yaml` is missing, unparseable (YAML syntax error or schema validation failure), or specifies an unknown posture name
Then the posture engine (`src/scripts/posture.py`) resolves to `strict`
And all `FAIL`-severity findings block commit execution with exit code 1.

### Scenario 2: Baseline Grandfathering and File-Edit Lapsing in Ratchet Posture
Given a project configured with `enforcement.posture: ratchet` and a valid `.agent/baseline.json`
When code is committed without modifying any file listed in `.agent/baseline.json` (as determined by `git diff --name-only HEAD`, or `git diff --name-only HEAD^1` for merge commits; if a shallow clone `--depth=1` lacks parent commit history for `HEAD^1`, lapse re-verification is skipped gracefully with a `SHALLOW_CLONE_LAPSE_SKIPPED` advisory event)
Then existing violations in those files disposition to `GRANDFATHERED` and emit `GATE_ADVISORY` events without blocking exit code (with `posture.py` indexing entries into `dict[str, list[BaselineEntry]]` for $O(1)$ lookups and skipping AST parsing for touched files with zero baseline entries)
When code is committed that modifies a file listed in `.agent/baseline.json` (appearing in staged or working-tree changes relative to `HEAD`)
Then region hashes (computed over the innermost enclosing `FunctionDef`/`AsyncFunctionDef`/`ClassDef` AST node via `hashlib.sha256(ast.unparse(node).encode('utf-8'))`, with whole-file fallback for top-level code) for that touched file are re-evaluated against current content, stale hashes lapse, and any remaining `FAIL` findings in the touched file block execution.

### Scenario 3: Baseline Tamper Detection and Fallback
Given an existing `.agent/baseline.json` manifest file containing `header.manifest_sha256`
When `posture.py` computes the SHA-256 hash of the `entries` array using canonical JSON serialization (`json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")`) and compares it to `header.manifest_sha256`
Then if a mismatch is detected, the posture engine logs a `BASELINE_TAMPER_SUSPECTED` audit event in `harness_events.jsonl`
And treats `.agent/baseline.json` as absent, enforcing `strict` blocking dispositions without relying on untracked log history.

### Scenario 4: Human-Only Baseline Generation
Given an environment where `AGENT_ID` is set in environment variables or `sys.stdin.isatty()` is `False`
When `python .agent/scripts/baseline.py init` or `refresh` is executed
Then the script prints an error message ("Baseline generation is human-only") and exits with code 1 without modifying `.agent/baseline.json` (noting `AGENT_ID` + TTY check is a convention-based guard, not an unbypassable security boundary; unit tests in `test_baseline.py` exercise this path using test-only `monkeypatch.setattr(sys.stdin, "isatty", lambda: True)` without adding a public CLI override flag).

### Scenario 5: Observe Posture Disposition Behavior
Given a project configured with `enforcement.posture: observe` and `observe_expires` ISO 8601 UTC date string
When code is committed before the `observe_expires` date boundary
Then all findings disposition to `ADVISORY` and emit `GATE_ADVISORY` events with exit code 0
When `observe_expires` is missing, malformed, or past `datetime.now(timezone.utc)`
Then `posture.py` automatically resolves effective posture to `ratchet` and prints a `POSTURE_EXPIRED_WARNING` banner:
`⚠️  [POSTURE EXPIRED] 'observe' posture expired on <date> UTC. Resolved to 'ratchet'.`
`    👉 Action: Run 'python .agent/scripts/baseline.py init' or update observe_expires in .agent/config.yaml.`

### Scenario 6: Invariant Floor Immunity for Hard Safety Rules
Given a project configured with `enforcement.posture: observe` or `ratchet`
When a diff triggers an H-series prohibition rule (H-01 through H-09 per `AGENTS.md §4.1`)
Then the finding dispositions to `BLOCK` regardless of configured posture, baseline entries, or calibration weights (noting H-series rules represent session-level agent conduct and honesty rules, enforced independently via HALT and escalation protocols; diff-level security capabilities marked invariant are explicitly pinned in `posture.py`'s registry at the capability level).

### Scenario 7: Bypass File Deprecation
Given a repository containing a `.skip-ai-review` file or `SKIP_AI_REVIEW=1` environment variable
When the review gate executes
Then the gate prints a visible deprecation warning pointing to `enforcement.posture: observe`
And logs a `GATE_SKIPPED` event with `deprecated_bypass: true` (preparing full bypass retirement in milestone `v1.5.0`).

---

## 5. Proposed Mechanism

### 5.1 Three postures

Declared in `.agent/config.yaml` under a new `enforcement:` block (§5.7):

| Posture | Semantics | Intended for |
|---|---|---|
| `strict` | Current behaviour, made severity-correct: FAIL-severity findings block; WARN-severity findings warn. **Default** — absence of config, unparseable config, or unknown posture value all resolve to `strict` (fail-safe, not fail-open). | Greenfield and compliant codebases |
| `ratchet` | FAIL findings in **changed files** block. FAIL findings in files matching the baseline manifest (§5.2) are grandfathered → advisory. WARN findings advisory everywhere. | Brownfield codebases under active improvement |
| `observe` | Nothing blocks except the invariant floor (§5.5). All findings emitted as advisory with full detail. **Requires a mandatory `expires` date** (max 90 days ahead); past expiry the posture is invalid config → resolves to `ratchet` and prints a loud renewal instruction. | Pre-adoption assessment |

Session-init and every gate run print a one-line posture banner; under `observe` the banner is prominent and includes the expiry date, so neither human nor agent can forget enforcement is relaxed.

### 5.2 Baseline manifest (`.agent/baseline.json`)

The grandfather record for `ratchet`. **Committed to the repo** — it is a governance record, not session state, so it does not live in `.agent/state/` (which is runtime scratch). Follows the T1-B-12 precedent: a snapshot of tolerated debt, explicitly not laundered into accepted status.

- **Schema (v1):** list of entries `{ rule, file, region_sha256, first_seen, note? }` plus header `{ schema_version, manifest_sha256, generated_at, generated_by, harness_version, posture_at_generation }`.
- **Region hash, not line numbers.** Each entry stores a SHA-256 of the normalised source region containing the violation (the enclosing function/class body where the checker can identify one; whole-file hash as fallback). Line numbers drift; content hashes don't. A finding is grandfathered **only if** rule + file match an entry *and* the current region hash equals the stored hash. Any edit to the region invalidates the grandfather clause — the agent must fix the violation or the human must explicitly re-baseline. This is the strangler-fig mechanism, and it is mechanical rather than judgement-based: agents are never asked to self-assess "was this pre-existing?"
- **File-level scoping (resolved, §7 D2):** if *any* staged change touches a file, all grandfathered entries for that file are re-verified against current hashes; stale entries lapse. "You touched it, you own it."
- **In-memory indexing & AST fast-path:** Upon loading `.agent/baseline.json`, `posture.py` builds an in-memory hash index keyed by file path (`dict[str, list[BaselineEntry]]`), ensuring $O(1)$ lookups per finding. Before attempting AST parsing on a touched file, `posture.py` checks whether the file has any entries in the baseline index; if a touched file has zero baseline entries, AST region extraction is skipped entirely.
- **Generation is human-only, HARD STOP class (resolved, §7 D1).** New CLI: `python .agent/scripts/baseline.py init|refresh|report`. `init`/`refresh` require interactive TTY confirmation (`sys.stdin.isatty()`) and refuse to run when `AGENT_ID` is set in the environment (convention-based defense-in-depth guard, same convention family as existing agent-limit enforcement). Agents may run `report` (read-only diff of current findings vs baseline) and may *recommend* a refresh with prepared analysis — never execute one. Rationale: if agents can write the baseline, the cheapest path past a gate is appending the new violation to it — the manifest-shaped variant of HIB-053.
- **Tamper detection:** `baseline.py init|refresh` computes a SHA-256 checksum over the `entries` array using canonical JSON serialization (`json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")`) and stores it in `header.manifest_sha256`. Gate runs recompute the `entries` SHA-256 hash at execution time; a mismatch against `header.manifest_sha256` → the manifest is treated as absent (nothing grandfathered) and a `BASELINE_TAMPER_SUSPECTED` audit event is logged. Self-contained verification: does not rely on untracked event logs, ensuring deterministic tamper detection across fresh clones and CI runners.

### 5.3 Shared disposition module (`src/scripts/posture.py`)

The single place where "does this finding block?" is answered. Both blocking gates call it at their exit points; neither reimplements the logic.

```
disposition(finding, posture, baseline, overrides, invariants) -> Disposition
  Disposition = { outcome: BLOCK | ADVISORY | GRANDFATHERED,
                  chain: [str],          # human-readable narration of each stage
                  invariant_pinned: bool }
```

- **`architecture_checks.py`** replaces `if all_errors: sys.exit(1)` with: map each error to a `Disposition`; exit 1 iff any `BLOCK`; print advisory/grandfathered findings under clearly separated headings with counts (`12 blocking, 340 advisory` — never one undifferentiated wall).
- **`ai_review.py`** applies disposition to the typed verdict after all existing modulation (§5.4): a `FAIL` verdict whose blocking findings all disposition to advisory exits 0 with the advisory rendering; the persisted verdict records both the model's verdict and the posture outcome.
- **Degradation contract:** if `posture.py` cannot load config or baseline, it returns `strict` dispositions and logs the failure. A broken posture system is a strict posture system.

**Prerequisite fix (in scope):** replace `architecture_checks.py`'s substring-based severity derivation with an explicit rule→severity map (`LAYER_BOUNDARY: FAIL`, `HIGH_COUPLING: WARN`, …) co-located with the existing rule-name mapping. Posture disposition consumes `ArchViolation.severity`; that field must be trustworthy first.

**Regression trap to close before this ships:** `check_type_checking_imports()`'s findings ("Potential NameError risk...") currently have no dedicated `rule` tag in `main()`'s error-parsing loop — they fall through to the generic `ARCHITECTURE_RULE` default and only get WARN today via the `"nameerror"` substring match above. The explicit map has no entry for a bare `ARCHITECTURE_RULE` bucket by design (every other check already has a named rule: `LAYER_BOUNDARY`, `HIGH_COUPLING`, `BRANCH_FILTER`, `AGGREGATE_ROOT`, `INTERFACE_SEGREGATION`, `ASGI_LIFESPAN`, `FORBIDDEN_PATTERN`). Shipping the map without first giving `check_type_checking_imports()` its own rule tag (e.g. `TYPE_CHECKING_CAST: WARN`) would silently reclassify those findings from WARN to FAIL for every brownfield adopter on day one — exactly the kind of surprise this whole spec exists to prevent. This tag must be added as part of the prerequisite fix, not left implicit.

### 5.4 Modulation order contract

Source review found three severity-modulation mechanisms already live: capability calibration (T1-G-14, demotes HIGH→MEDIUM at weight ≤0.9 / promotes at ≥1.1 inside `ai_review.py`), critical-intensity escalation (WARN→FAIL when `review_intensity == "critical"`), and now posture. **These first two stages are `ai_review.py`-specific** — they operate on the LLM verdict's `concern`-tagged issues, which have no equivalent on `ArchViolation` objects (deterministic findings have no `concern` field for calibration to key off, and no `review_intensity` context). The pipeline order is fixed and documented in code, but the pipeline itself is only fully populated for the `ai_review.py` call site:

```
ai_review.py:            detection → calibration (T1-G-14) → intensity escalation → posture disposition → exit code
architecture_checks.py:   detection ────────────────────────────────────────────→ posture disposition → exit code
```

Posture runs **last** in both cases and is authoritative over exit behaviour. For `architecture_checks.py`, calibration and intensity escalation are simply absent stages, not no-ops that need to be invoked and ignored — `disposition()` is called directly on the raw `ArchViolation.severity`. Every stage that changes a finding's effective severity or disposition appends one line to the finding's `chain` (calibration's existing `policy_notes` narration is the pattern). The chain is included in the persisted verdict and in advisory rendering, so "why didn't this block?" / "why did this block?" is answerable from the audit trail without archaeology.

### 5.5 Invariant floor — H-series immune to all modulation

New cross-cutting invariant, enforced in code (assertions), not just documented:

1. A registry of **invariant-pinned capabilities/rules** (the registry is code-level in `posture.py`, not user config). Clarifying scope: H-series rules (H-01 through H-09 per `AGENTS.md §4.1`) represent session-level agent conduct and honesty rules, enforced independently via HALT and escalation protocols. Any diff-level security capabilities marked invariant are explicitly pinned in `posture.py`'s registry at the capability level.
2. `capability_calibration.get_calibrated_weight()` returns exactly `1.0` for pinned capabilities regardless of stored weights or config `overrides` — closing the *existing* gap where rebuttal-driven weights can suppress any capability, including safety-class ones. This is a retroactive fix to T1-G-14.
3. No posture and no per-rule override (§5.6) can downgrade a pinned finding: `strict|ratchet|observe` all `BLOCK`, baseline entries for pinned rules are ignored at load with a logged warning.
4. Existing availability safeguards survive all postures: the high-risk fail-closed path (API unavailable + high-risk patterns → block) and the session-budget halt are **not** enforcement opinions and are unaffected by posture, including `observe`.

Consequence: even in `observe`, the harness still governs *the agent* (integrity, safety, availability) while deferring governance of *the codebase*. The tagline survives brownfield mode.

### 5.6 Per-rule overrides

Within a posture, individual rules/capabilities may be set to `block | warn | off` in config — e.g. a brownfield adopter enables `RBAC` as blocking on day one while `HIGH_COUPLING` stays advisory. Constraints: pinned rules reject any override (config validation error, fail-closed to `block`); `off` still detects and audits — it suppresses *rendering prominence*, never the scan or the event.

### 5.7 Configuration

One consolidated block in `.agent/config.yaml` (and the bootstrap template), adjacent to `outer_loop:` and matching its documentation style:

```yaml
# Gate enforcement posture (T1-G-18)
#
# strict   — (DEFAULT) FAIL findings block everywhere. For greenfield /
#            compliant codebases. Unknown or unparseable posture resolves here.
# ratchet  — FAIL findings block in changed code; pre-existing findings
#            recorded in .agent/baseline.json are advisory until the file is
#            touched. Baseline generation is human-only:
#            python .agent/scripts/baseline.py init
# observe  — assessment mode: nothing blocks except invariant-pinned (H-series)
#            rules and availability safeguards. REQUIRES expires (max 90 days);
#            past expiry resolves to ratchet.
enforcement:
  posture: strict
  observe_expires: null        # ISO date, mandatory when posture: observe
  rule_overrides: {}           # e.g. HIGH_COUPLING: warn   (pinned rules reject overrides)
```

Validated centrally (schema alongside the existing config validation), so calibration config, posture config, and overrides don't accumulate divergent parsing.

### 5.8 `outer_loop.mode` compatibility matrix

Two orthogonal posture systems now exist: `outer_loop.mode` governs *specification* rigour; `enforcement.posture` governs *code-gate* disposition. Valid combinations:

| | `strict` | `ratchet` | `observe` |
|---|---|---|---|
| `discovery` | ✓ | ✓ | ✓ |
| `incremental` | ✓ | ✓ | ✓ |
| `contractual` | ✓ | ✗ invalid | ✗ invalid |

`contractual` promises "maximally strict, no bypass paths"; combining it with relaxed code enforcement is self-contradictory. Config validation rejects the invalid cells at load with an explanatory error.

### 5.9 Bypass absorption — deprecate the skip file

`observe` (with expiry, banner, and audit) is the governed replacement for `SKIP_AI_REVIEW=1` / `.skip-ai-review`. Plan:

- **This release (v1.4.12):** using the env var or skip file prints a deprecation notice pointing at `enforcement.posture: observe`, and the emitted `GATE_SKIPPED` event gains `deprecated_bypass: true`. The FAIL message no longer advertises the bypass; it advertises the rebuttal protocol and, where applicable, posture config.
- **Next minor release (v1.5.0):** the env var and skip file are honoured only when `enforcement.posture != strict` — i.e. they become an emergency valve inside an already-declared relaxed posture, never a silent override of strict.
- **Never removed entirely** without a dedicated decision: a hard-stuck human at 2am needs *some* escape hatch; the goal is that the escape hatch is loud, logged, and posture-consistent, not that it is impossible.

### 5.10 Audit and schema changes

- **New event types** in `harness_events.jsonl` (existing `audit_logger.log_action` conventions): `GATE_ADVISORY` (same payload shape as a blocking finding, plus disposition chain), `BASELINE_GRANDFATHERED` (rule, file, baseline hash), `BASELINE_GENERATED`, `BASELINE_TAMPER_SUSPECTED`, `POSTURE_RESOLVED` (once per gate run: configured posture, effective posture, resolution reason — e.g. "observe expired → ratchet").
- **GateContext v1.1:** add `posture: str`, `dispositions: List[Disposition]`. The loader accepts any `1.x` schema version (`schema_version.startswith("1.")`), defaulting new fields for `1.0` and enabling forward compatibility for future `1.x` minor bumps. Because the degradation contract returns `None` on any parse failure, and consumers treat `None` as "no context", posture data can silently vanish; §5.3's degradation rule (absent context → strict) makes that loss fail-safe. The advisory-count-over-time series derivable from `GATE_ADVISORY` events is the free codebase-health burndown metric — flagged for the promotion track, no implementation in this spec.

### 5.11 Rebuttal interaction

Advisory findings are **not rebuttable** — nothing was blocked, there is nothing to rebut; rebuttal attempts against advisory findings are rejected with an explanatory message (and do not consume the diff-hash rate limit). An agent *claiming* a blocking finding is grandfathered when the baseline hash does not match is a rebuttal-class event: logged, counted against the rate limiter, and surfaced to the human. Calibration counters (T1-G-14 tp/fp) update only from findings that were **blocking** in the effective posture — advisory findings never train the weights, preventing brownfield noise from distorting calibration before enforcement even begins.

---

## 6. What changes where (implementation map)

| Component | Change | New/Modified |
|---|---|---|
| `src/scripts/posture.py` | Disposition engine, invariant registry, posture resolution, baseline verification | New |
| `.agent/scripts/baseline.py` | Human-only init/refresh/report CLI, tamper hash, audit events | New |
| `.agent/skills/universal/senior-architect/scripts/architecture_checks.py` | Explicit rule→severity map; exit logic via disposition; advisory rendering | Modified |
| `src/scripts/ai_review.py` | Posture disposition after calibration/intensity; deprecation notices; verdict persistence gains posture fields | Modified |
| `src/scripts/gate_context.py` | Schema v1.1 (posture, dispositions); loader accepts any 1.x schema version | Modified |
| `src/scripts/capability_calibration.py` | Invariant-pinned capabilities return weight 1.0; advisory findings excluded from counter updates | Modified |
| `src/scripts/rebuttal.py` | Advisory findings non-rebuttable; false-grandfather claims rate-limited | Modified |
| `.agent/config.yaml` + `bootstrap/templates/config.yaml.template` | `enforcement:` block; compatibility validation vs `outer_loop.mode` | Modified |
| `bootstrap/install.py` / `onboarding.py` | Brownfield onboarding path: offer `observe` → `init-baseline` → `ratchet` sequence | Modified |
| Tests | Characterisation tests for disposition matrix (posture × severity × baseline-state × pinned), baseline hash lapse, tamper detection, expiry resolution, config validation, calibration pinning | New |
| Docs | `docs/getting-started.md` brownfield adoption section; `docs/configuration.md` enforcement block | Modified |

Suggested phasing (each phase independently shippable): **P1** severity-map fix + `posture.py` + `architecture_checks` integration (strict/observe only, no baseline). **P2** baseline manifest + CLI + `ratchet`. **P3** `ai_review` integration, calibration pinning, rebuttal rules. **P4** bypass deprecation, onboarding path, docs.

---

## 7. Resolved Design Decisions

1. **D1 — Baseline generation is human-initiated, HARD STOP class.** Agents may analyse and recommend; only the human executes `init`/`refresh`. (Peter, 2026-07-08.)
2. **D2 — File-level grandfather scoping.** Touching a file re-verifies all its baseline entries; hunk-level tracking rejected as complexity without proportionate benefit, and file-level forces opportunistic cleanup. (Peter, 2026-07-08.)
3. **D3 — `observe` is a persistent posture with mandatory expiry**, not a CLI flag. Config is versioned and auditable where flags are not ("enforcement state must itself be governed"); the expiry, fail-safe resolution to `ratchet`, and session banners neutralise the parking risk. (Peter, 2026-07-08.)
4. **D4 — Posture disposition is a shared module called by both gates**, not a GateContext-pipeline-only stage — because `architecture_checks.py` blocks independently before `ai_review.py` runs. (Source review, 2026-07-08.)
5. **D5 — Default-absent resolves to `strict`.** Missing config, parse failure, unknown value, or missing GateContext all yield strict dispositions. Fail-safe over fail-open, consistent with the high-risk fail-closed precedent.
6. **D6 — Detection is never modulated.** All postures scan everything and audit everything; the burndown metric depends on this.

---

## 8. Known Residual Risks

- **Whole-file hash fallback is coarse.** Where a checker can't identify an enclosing region, the fallback whole-file hash means *any* edit to the file lapses *all* its grandfathered entries — stricter than intended, never looser. Acceptable bias; refine region extraction per-rule as follow-up if it proves noisy.
- **Baseline staleness under rebase/format churn.** A repo-wide formatter run lapses most of the baseline at once (every region hash changes), producing a sudden advisory→blocking wave in `ratchet`. Mitigation is procedural: run `baseline.py refresh` (human) immediately after intentional repo-wide mechanical changes; `baseline.py report` previews the blast radius first.
- **`observe`→`ratchet` expiry surprise.** A team ignoring the banners hits blocking behaviour the day after expiry. This is by design, but the renewal instruction printed at resolution must be unmistakable.
- **The escape hatch still exists** (§5.9 end state). A determined human can bypass in non-strict postures. Accepted: the harness governs agents mechanically and humans procedurally; a human bypass that is loud and logged is consistent with "You govern."
- **Two posture systems** (`outer_loop.mode`, `enforcement.posture`) is more cognitive surface than one. Unification was considered and deferred: they modulate different gate families with different lifecycles; forcing them into one enum would create invalid cross-products the matrix in §5.8 handles more honestly.

---

## 9. Explicitly Deferred

- Per-hunk grandfather tracking (rejected for now, §7 D2).
- Automatic burndown reporting/visualisation from `GATE_ADVISORY` events (promotion-track candidate, separate item).
- GymBase adoption of postures (consumer migration follows harness delivery).
- Unifying `outer_loop.mode` and `enforcement.posture` into one lifecycle model.
- Posture-aware behaviour for the PunchCard experiment cells (the 2×2 design predates postures; revisit protocol only if postures ship before execution).

---
**Per standing protocol:** this spec stops here for review and approval. No code, schema, or script implementation proceeds until sign-off. On approval, backlog entry T1-G-18 should be created referencing this document, and the P1–P4 phasing adopted as the delivery sequence.

---

## Post-Delivery Note (2026-07-25)

`SPEC-enforcement-postures.md` was delivered in release `v1.4.12` (commit `5a505c1`).
**Implementation Caveat / Known Defect**: Baseline grandfathering under `ratchet` posture was integrated into `src/scripts/ai_review.py` but **not** into `.agent/skills/universal/senior-architect/scripts/architecture_checks.py` (which evaluates `strict`/`observe` dispositions but omits `baseline` and `touched_files` arguments in its `disposition()` calls). This gap is tracked as **HIB-080** and targeted for remediation in `v1.4.13`.

