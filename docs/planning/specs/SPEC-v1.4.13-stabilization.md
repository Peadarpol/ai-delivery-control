# SPEC: v1.4.13 — Stabilization Release (Posture Enforcement Fix, Pre-v1.5.x Data Integrity, Rebuttal Protocol Cluster, Framework Decoupling)

**Status**: DRAFT — awaiting review and approval
**Author**: Claude / Gemini (planning & spec refinement) — source analysis: Claude Opus 4.6 / Gemini 3.6
**Tracked under**: HIB-080 (new), BUG-19, BUG-11, HIB-047, HIB-048, HIB-049, HIB-050, HIB-051
**Related**: T1-G-18 (enforcement postures — HIB-080 is a direct follow-on defect against this capability), SPEC-enforcement-postures.md, T1-D-07/T1-D-09/T1-L-15/T1-L-16 (v1.5.0 items whose foundations this spec protects)
**Changelog**:
- v1.0 (2026-07-25, Claude): Initial draft.
- v1.1 (2026-07-25, Gemini/Peter): Reconciled with v1.4.12 delivery evidence. Removed HIB-073, HIB-074, HIB-076, HIB-077 from scope (all confirmed delivered in v1.4.12). Refocused v1.4.13 strictly on HIB-080 (Phase 0), data integrity (BUG-19, HIB-049), rebuttal freeze (HIB-047/048), test infrastructure (BUG-11), and documentation housekeeping.
- v1.2 (2026-07-25, Gemini/Peter): Added Phase 5 (GymBase-specific residue cleanups) with config-driven exemptions (`.agent/config.yaml`), preserved GymBase legacy exemptions at project configuration level, and explicit decision pinning `ai_review.py` import ceiling at 32 via internal import consolidation.
- v1.3 (2026-07-25, Gemini/Peter): Extended Phase 5 to mandate upgrade-path migration (`bootstrap/migrations/v1_4_12_to_v1_4_13.py`). Migration script extracts installed `WHITELIST` and `exempt_tables` literals from target project files before overwrite, writes them forward into `.agent/config.yaml` under `schema_hardening`, and prints an explicit confirmation banner naming auto-migrated items. Added Scenario 8 acceptance criterion.
- v1.4 (2026-07-25, Gemini/Peter): Multi-persona review refinements folded: AST parse-failure fallback clarification for HIB-080 (`extract_ast_region_sha256()`), defensive type coercion in `get_harness_config()`, AST+Regex extraction with additive set union in `v1_4_12_to_v1_4_13.py`, and un-mocked entry point assertions for Scenarios 1 & 2.

---

## 0. Motivation Gate (context, not blocking)

Release **v1.4.13** is a targeted stabilization pass following the v1.4.12 release, addressing critical integrity gaps before v1.5.0 (Quality Signal Maturity) begins and before GymBase adopts v1.4.12:

1. **HIB-080** (Phase 0): Auditing v1.4.12 ahead of GymBase's upgrade revealed that `ratchet` posture's baseline-grandfathering was integrated into `ai_review.py` but omitted from `architecture_checks.py` — the exact gate whose 129-violation wall motivated T1-G-18 in the first place (`SPEC-enforcement-postures.md` §0). GymBase adopting `ratchet` today would get silent `strict`-equivalent blocking from `architecture_checks.py`.
2. **Data & Rebuttal Integrity** (Phases 1–3): Fixes for `decisions_log.md` tab corruption (`BUG-19`), the `REMEDIATED` rebuttal type (`HIB-049`), rebuttal finding surfacing & freezing (`HIB-047`/`HIB-048`), and pytest stdout wrapping (`BUG-11`).
3. **Framework Decoupling & Safe Upgrade Migration** (Phase 5): De-coupling remaining GymBase domain artifacts from scripts and skill tools (`harness_health.py` title banner, `enforce_hardened_schemas.py`, `analyze_schema.py`, internal test paths). Hardcoded GymBase domain exemptions are extracted into project-level `.agent/config.yaml` (`schema_hardening`). Crucially, `bootstrap/upgrade.py` and its migration unit (`v1_4_12_to_v1_4_13.py`) auto-extract legacy Python literals from upgrading targets before file overwrite, writing them forward into `.agent/config.yaml` and emitting a mandatory operator confirmation banner.

Starting v1.5.0 without these fixes means building new capabilities (recidivism tracking, driver counters, memory retention) on top of known-corrupt or uncalibrated base data.

---

## 1. Verification Note

Every item in this spec's scope was verified against current filesystem and git state (`5a505c1`):
- **Delivered in v1.4.12**: HIB-073 (pathing), HIB-074 (provider errors), HIB-076 (traceability self-ratification), HIB-077 (SQLite schema drift) were verified present in git history and excluded from v1.4.13 code scope.
- **Confirmed Open**:
  - `HIB-080`: `architecture_checks.py` posture evaluation block calls `posture.disposition(...)` without `baseline=` or `touched_files=`.
  - `BUG-19`: Unvalidated free-text writes in `record_decision()` replacing leading 't' with a tab character.
  - `BUG-11`: Pytest stdout capture wrapper overwritten by `sys.stdout` re-wrapping in `harness_utils.py`.
  - `HIB-047`/`HIB-048`/`HIB-049`/`HIB-050`/`HIB-051`: Rebuttal protocol findings freeze and `REMEDIATED` classification missing.
  - **GymBase Residue & Decoupling**: `harness_health.py` title banner, hardcoded `WHITELIST` in `enforce_hardened_schemas.py`, hardcoded `exempt_tables` in `analyze_schema.py`.
  - **Upgrade Blind Spot**: Stock v1.4.12 `enforce_hardened_schemas.py` and `analyze_schema.py` in target projects match the shipped baseline checksums and would be silently overwritten by `upgrade.py` without AST/literal extraction into `.agent/config.yaml`.

---

## 2. Bounded Scope & Out of Scope

### In-Scope (Goals)
- **Phase 0 (blocking for GymBase adoption of v1.4.12):** HIB-080 — Wire `.agent/baseline.json` and touched-file lapsing into `architecture_checks.py`'s posture disposition call, matching `ai_review.py`'s pattern.
- **Phase 1 (data integrity):** BUG-19 (decisions_log tab-corruption), HIB-049 (REMEDIATED rebuttal type — prevents false-positive calibration pollution).
- **Phase 2 (gate integrity):** HIB-047 + HIB-048 (rebuttal finding surfacing + freeze using `.agent/state/gate_findings_{session_id}.json`).
- **Phase 3 (test infrastructure):** BUG-11 (pytest stdout wrapping interference).
- **Phase 4 (housekeeping):** Verification pass over documentation status markers and release ledger.
- **Phase 5 (framework decoupling & safe upgrade migration):**
  - Refactor `enforce_hardened_schemas.py` and `analyze_schema.py` to read `schema_hardening.whitelist` and `schema_hardening.exempt_tables` from `.agent/config.yaml` via `get_harness_config()`. Default fallback for greenfield projects is empty whitelist and standard system migration tables (`alembic_version`, `schema_migrations`, `sqlite_sequence`).
  - Build `bootstrap/migrations/v1_4_12_to_v1_4_13.py` migration script: auto-extract `WHITELIST` and `exempt_tables` literals from target project files before file overwrite and append them into target's `.agent/config.yaml` under `schema_hardening`.
  - Emit an explicit operator confirmation banner in `upgrade.py` naming all auto-migrated schema exemptions.
  - Update `harness_health.py` banner to project-neutral string.
  - Fix internal test fallback paths in `.agent/tests/*.py`.
  - Consolidate duplicate imports in `ai_review.py` to preserve import ceiling at 32 without raising test thresholds.

### Out-of-Scope (Non-Goals)
- `HIB-073`, `HIB-074`, `HIB-076`, `HIB-077` (already shipped in v1.4.12).
- T1-G-15 (complexity gate) or other v1.5.0 features.
- Raising `test_ai_review.py`'s import ceiling threshold above 32 (prohibited — consolidation required instead).
- Silent overwriting of target project schema exemptions during upgrade (prohibited — migration unit extraction mandatory).
- HIB-066, HIB-053c (trigger-gated).

---

## 3. Assumptions & Design Decisions

- `[Resolved: HIB-080's fix is scoped to architecture_checks.py's disposition call site only — posture.py's disposition() signature already accepts baseline, touched_files, and region_sha256 as optional parameters. Note that extract_ast_region_sha256() (reused from baseline.py) already degrades gracefully on AST parse failure via whole-file SHA-256 fallback — no new fallback logic is required in architecture_checks.py's posture-evaluation block.]`
- `[Resolved: BUG-19's fix requires input sanitization / string formatting guards in record_decision() and decisions_log.md write helpers.]`
- `[Resolved: HIB-047/048 creates .agent/state/gate_findings_{session_id}.json at gate fail time and consumes it during --rebuttal.]`
- `[Resolved: Config-Driven Schema Hardening Exemptions — enforce_hardened_schemas.py and analyze_schema.py will read schema_hardening configuration from .agent/config.yaml via get_harness_config(). New greenfield projects default to empty whitelist and standard system migration tables (alembic_version, schema_migrations, sqlite_sequence). Existing GymBase exemptions are explicitly configured in GymBase's .agent/config.yaml to guarantee zero regression. get_harness_config() parsing defensively coerces whitelist and exempt_tables values to set(), filtering out None or non-string elements.]`
- `[Resolved: Upgrade Path Safety — Stock v1.4.12 target files will checksum-match upgrade.py's baseline. To prevent silent loss of load-bearing exemptions on GymBase (or any v1.4.12 project), v1_4_12_to_v1_4_13.py must extract installed WHITELIST and exempt_tables literals before file replacement, write them additively to .agent/config.yaml under schema_hardening, and display an explicit operator confirmation banner. AST parsing is attempted first for literal extraction, falling back to regex set-literal matching if AST parsing fails. Extracted sets are additively merged with existing .agent/config.yaml entries (existing_config | extracted_set).]`
- `[Resolved: Import Ceiling Maintenance — ai_review.py contains a duplicate import (from gate_context import write_gate_context at lines 2040 and 2399). Consolidating write_gate_context import removes the duplicate AST node added during v1.4.12 posture integration, bringing top-level AST import count back to 32. The test ceiling in test_ai_review.py MUST NOT be increased.]`

---

## 4. Acceptance Criteria

### Scenario 1: Ratchet posture grandfathers pre-existing architecture_checks.py violations (HIB-080)
Given a project configured with `enforcement.posture: ratchet` and a valid `.agent/baseline.json` containing an entry for a `FAIL`-severity `LAYER_BOUNDARY` violation in an untouched file
When `architecture_checks.py` runs its posture-evaluation block
Then `posture.load_baseline()` and `posture.get_touched_files()` are invoked before any `disposition()` call
And the matching violation dispositions to `GRANDFATHERED` with exit code 0, not `BLOCK`.
*(Note: Verified via end-to-end function invocation without mocking posture.disposition().)*

### Scenario 2: Ratchet posture still blocks on touched-file violations (HIB-080 regression guard)
Given the same baseline as Scenario 1
When the diff modifies the file containing the baseline-matched violation
Then the region hash is re-evaluated and, if changed, the finding dispositions to `BLOCK`.
*(Note: Verified via end-to-end function invocation without mocking posture.disposition().)*

### Scenario 3: decisions_log.md rejects corrupting writes (BUG-19)
Given the `record_decision()` helper
When a decision entry containing a leading `t` character is written
Then the persisted entry contains the literal character, not a tab, verified via regression unit test.

### Scenario 4: REMEDIATED rebuttal type is available and does not pollute calibration (HIB-049)
Given a developer has fixed a genuine gate-flagged issue
When they file a rebuttal
Then `REMEDIATED` is a valid `rebuttal_type` requiring no `spec_reference`, and `capability_calibration.py` does not treat a `REMEDIATED` rebuttal as evidence of a false positive.

### Scenario 5: Gate findings are surfaced and frozen at rebuttal time (HIB-047 + HIB-048)
Given a gate `FAIL` verdict
When the finding is first evaluated
Then it is written verbatim to `.agent/state/gate_findings_{session_id}.json`
And when `--rebuttal` is invoked, the developer sees the original frozen finding text before writing evidence.

### Scenario 6: Config-driven schema hardening exemptions preserve GymBase behavior while keeping framework source clean (Phase 5)
Given `enforce_hardened_schemas.py` and `analyze_schema.py`
When executed on a project with `schema_hardening` options defined in `.agent/config.yaml`
Then `enforce_hardened_schemas.py` reads `schema_hardening.whitelist` and `analyze_schema.py` reads `schema_hardening.exempt_tables` from config
And when executed on a project with no `schema_hardening` config block, `enforce_hardened_schemas.py` defaults to an empty whitelist and `analyze_schema.py` defaults strictly to standard migration tables (`alembic_version`, `schema_migrations`, `sqlite_sequence`).

### Scenario 7: Import ceiling in test_ai_review.py remains strictly pinned at 32 (Phase 5)
Given `src/scripts/ai_review.py`
When `test_import_count_does_not_exceed_ceiling` executes in `tests/test_ai_review.py`
Then `ast.walk` counts `<= 32` imports without modifying the test ceiling threshold.

### Scenario 8: Upgrade preserves existing schema-hardening exemptions (Phase 5)
Given a project on v1.4.12 with hardcoded `WHITELIST`/`exempt_tables` values in its installed `enforce_hardened_schemas.py`/`analyze_schema.py`
When `bootstrap/upgrade.py` migrates it to v1.4.13
Then `v1_4_12_to_v1_4_13.py` extracts those values via AST/Regex and additively merges them (`existing_config | extracted_set`) into the project's `.agent/config.yaml` under `schema_hardening`, printing an explicit confirmation banner naming what was migrated before the old files are overwritten.

---

## 5. Proposed Phasing

- **Phase 0 — Posture Enforcement Integrity**: HIB-080 (`architecture_checks.py` baseline/touched-files wiring).
- **Phase 1 — Data Integrity**: BUG-19 (decisions_log tab-corruption sanitization), HIB-049 (`REMEDIATED` rebuttal type).
- **Phase 2 — Gate Integrity**: HIB-047 + HIB-048 (rebuttal findings freeze artifact).
- **Phase 3 — Test Infrastructure**: BUG-11 (pytest stdout wrapping fix in `harness_utils.py`).
- **Phase 4 — Housekeeping**: Verification pass over documentation status markers and release ledger.
- **Phase 5 — Framework Decoupling & Upgrade Migration**:
  - Implement `schema_hardening` config reader in `enforce_hardened_schemas.py` and `analyze_schema.py`.
  - Author migration unit `bootstrap/migrations/v1_4_12_to_v1_4_13.py` for AST/literal extraction into target `.agent/config.yaml` and operator confirmation banner.
  - Update `harness_health.py` banner to project-neutral string.
  - Consolidate duplicate `write_gate_context` import in `ai_review.py` to maintain import ceiling at 32.
  - Update `.agent/tests/*.py` fallback paths.

---

## 6. What Changes Where (Implementation Map)

| Component | Change | Phase |
|---|---|---|
| `.agent/skills/universal/senior-architect/scripts/architecture_checks.py` | Load baseline + touched files; pass into `disposition()`; compute `region_sha256` per violation | 0 |
| `.agent/scripts/baseline.py` | Expose `extract_ast_region_sha256()` for reuse by the live gate | 0 |
| `tests/unit/test_posture.py` / `tests/test_architecture_checks.py` | Seeded-violation ratchet/grandfather regression test (unmocked disposition) | 0 |
| `record_decision()` helper / `harness_utils.py` | Input sanitization at write boundary for decisions_log | 1 |
| `src/scripts/rebuttal.py`, `gate_rebuttal_template.json`, `AGENTS.md §8.6` | Add `REMEDIATED` rebuttal type | 1 |
| `src/scripts/capability_calibration.py` | Exclude `REMEDIATED` from false-positive weight adjustments | 1 |
| `.agent/state/gate_findings_{session_id}.json` (new artifact), `src/scripts/rebuttal.py` | Freeze findings on fail; load frozen text during `--rebuttal` | 2 |
| `src/scripts/harness_utils.py` | Conditional UTF-8 stdout wrapping logic (detect pytest capture) | 3 |
| `.agent/scripts/harness_health.py` | Update banner string to project-neutral name | 5 |
| `.agent/scripts/enforce_hardened_schemas.py` | Config-driven whitelist (`schema_hardening.whitelist`), default empty `set()` | 5 |
| `.agent/skills/universal/database-design/scripts/analyze_schema.py` | Config-driven table exemptions (`schema_hardening.exempt_tables`), default migration tables | 5 |
| `bootstrap/migrations/v1_4_12_to_v1_4_13.py` (new) | Parse target files for `WHITELIST` and `exempt_tables` via AST/Regex, additively merge (`existing | extracted`) forward to target `.agent/config.yaml`, emit confirmation banner | 5 |
| `tests/test_upgrade.py` / `tests/unit/test_migration_v1_4_12_to_v1_4_13.py` | Migration unit tests verifying literal extraction, additive `.agent/config.yaml` merge, and banner | 5 |
| `.agent/config.yaml` (and templates) | Define `schema_hardening` section preserving GymBase operational exemptions | 5 |
| `src/scripts/ai_review.py` | Consolidate duplicate `write_gate_context` import (keep AST import count <= 32) | 5 |
| `.agent/tests/*.py` | Replace hardcoded fallback path `c:/projects/Gym_App` with `_find_project_root()` | 5 |

---

**Per standing protocol:** this spec stops here for review and approval. No code, schema, or script implementation proceeds until sign-off.
