# SPEC: CDR Ledger — Schema & Pilot Migration (T1-B-12, Piece 1)

**Task ID**: T1-B-12 (Piece 1 of the CDR ledger work)
**Type**: New data file + migration of five existing decisions + validation test. No logic changes.
**Status**: Approved
**Implementer**: Gemini Flash (mechanical transcription against this fixed schema — no design latitude)
**Reviewer**: Peter — verification by reading the migrated ledger + running the parse test
**Design authority**: schema settled in design session (four decisions locked, recorded in §1)
**Deferred to later pieces**: reconciler integration (subtraction logic — Piece 2, needs a
strong model), brownfield baseline bulk-population tool (Piece 3).

---

## 1. Settled design decisions (context — do not revisit)

1. **Unified entry model with `scope`**: one entry type; `scope: pair` matches its exact file
   pair, `scope: file` matches ANY crossing involving that file. The hub-exemption is just a
   file-scoped entry — no special hub machinery. (Extensible later with `scope: pattern`.)
2. **Three-status model with mechanical anti-confabulation**: `accepted` requires `rationale`;
   `tolerated` requires `reason` (`deferred` | `unevaluated`); `tolerated/unevaluated` MUST NOT
   have a `rationale` (you cannot have a rationale for something unjudged); `resolved` keeps the
   entry with a `resolved_by` note (history survives).
3. **Observed-metrics snapshot**: every entry records the co-change count, P(max), and date at
   decision time, so future escalation ("has this gotten worse since we tolerated it?") is
   detectable.
4. **Baseline = population strategy, not a separate artifact**: one ledger file; a brownfield
   baseline is a bulk insert of `tolerated/unevaluated` entries into the same file. The
   tolerated-debt view is a filter, not a second data source.

## 2. The file

**Location**: `.agent/coupling_decisions.yaml` (repo-tracked, version-controlled — these are
decisions, not local state; they belong in git, unlike `.agent/state/*`).

**Top-level structure**:

```yaml
# Coupling Decision Records (CDR) ledger.
# Consumed by the co-change reconciler (T1-B-09) to distinguish sanctioned crossings
# from undeclared ones. Schema: docs/planning/specs/SPEC-cdr-ledger.md (this spec).
version: 1
decisions:
  - id: CDR-001
    ...
```

`version: 1` at the top so future schema evolution is detectable.

## 3. Entry schema

Every entry under `decisions:` has these fields:

| Field | Required? | Values / format |
|---|---|---|
| `id` | always | `CDR-NNN`, zero-padded 3 digits, sequential, never reused |
| `scope` | always | `pair` \| `file` |
| `files` | if scope=pair | list of exactly 2 repo-relative paths, **sorted lexicographically** |
| `file` | if scope=file | single repo-relative path |
| `status` | always | `accepted` \| `tolerated` \| `resolved` |
| `reason` | if status=tolerated | `deferred` \| `unevaluated` |
| `archetype` | required if status=accepted; optional otherwise | `derived` \| `model` \| `functional` |
| `rationale` | required if accepted; FORBIDDEN if tolerated/unevaluated; optional for tolerated/deferred and resolved | free text (folded scalar `>` fine) |
| `observed` | always (except resolved may omit) | map: `co_changes: int`, `p_max: float`, `as_of: YYYY-MM-DD` |
| `follow_up` | optional | free text; for accepted-with-improvement-path entries. Reference backlog IDs where they exist |
| `note` | optional | free text; e.g. tolerated/deferred's "why not now" |
| `resolved_by` | required if status=resolved | free text describing what resolved it |
| `sdv` | optional | map with any of `strength` (`intrusive`\|`functional`\|`model`\|`contract`), `distance`, `volatility` (`low`\|`medium`\|`high`) — vocabulary per governance.md §8 |
| `boundaries` | optional but populate when known | list of the boundary names the crossing spans (from `architecture.layers`) |

**Constraint rules (the validation test in §5 enforces these):**
- C1: `accepted` ⇒ `rationale` present and non-empty.
- C2: `tolerated` ⇒ `reason` present and one of the enum.
- C3: `tolerated` + `reason: unevaluated` ⇒ `rationale` ABSENT.
- C4: `accepted` ⇒ `archetype` present.
- C5: `scope: pair` ⇒ `files` has exactly 2 entries, sorted.
- C6: `scope: file` ⇒ `file` present, `files` absent (and vice versa).
- C7: `id` values unique, format `CDR-\d{3}`.
- C8: `resolved` ⇒ `resolved_by` present.

## 4. The migration — exact content

Migrate the five pilot decisions (source: `docs/planning/CDR-pilot-entries.md`, or wherever
Peter saved the pilot doc) into the ledger. **The three checksums entries collapse into ONE
file-scoped entry** — that collapse is the point of the scope model. Resulting ledger has
**three** decisions:

```yaml
version: 1
decisions:
  - id: CDR-001
    scope: file
    file: bootstrap/checksums.py
    status: accepted
    archetype: derived
    rationale: >
      Checksum manifest regenerated whenever tracked files change; co-changes with its
      inputs by construction. Derived coupling with no independent behaviour that can
      drift. Exempt all crossings involving this file. (Subsumes the three pair-level
      findings from the first reconciler run: providers.py, init_session.py, ai_review.py.)
    observed:
      co_changes: 6        # highest of the three subsumed pairs
      p_max: 0.71          # highest of the three subsumed pairs
      as_of: 2026-07-08
    boundaries: [bootstrap, review_engine, governance_scripts]

  - id: CDR-002
    scope: pair
    files: [.agent/scripts/init_session.py, src/scripts/ai_review.py]
    status: accepted
    archetype: model
    rationale: >
      Producer/consumer coupling over the session.json state schema: init_session.py
      creates the session and sets token-budget allocations; ai_review.py reads remaining
      budget and writes back spent fields. They also share session-locking utilities and
      the event trail. Co-change is the expected consequence of the shared session-state
      model evolving (verified by commit analysis: 4 of 6 co-changes were genuine
      shared-abstraction/state changes; no direct import).
    follow_up: >
      Make the session.json contract explicit — extract schema into a shared typed
      definition both sides import (filed as T1-E-03, low priority).
    observed:
      co_changes: 6
      p_max: 0.60
      as_of: 2026-07-08
    boundaries: [governance_scripts, review_engine]
    sdv:
      strength: model
      distance: cross-boundary
      volatility: low

  - id: CDR-003
    scope: pair
    files: [bootstrap/validate.py, src/scripts/ai_review.py]
    status: accepted
    archetype: functional
    rationale: >
      Validator-to-validated coupling: validate.py checks install integrity of structures
      ai_review.py depends on (outer_loop.mode config key, session.json gitignore
      invariant, review_context file split). A validator is supposed to be coupled to what
      it validates; low coupling here would be a defect (stale validator silently passing
      broken installs). Verified by commit analysis: 3 of 6 co-changes were genuine
      validator-tracks-validated changes; 3 were release-rollup bundling noise; no direct
      import. No improvement path — the coupling is correct by design.
    observed:
      co_changes: 6
      p_max: 0.46
      as_of: 2026-07-08
    boundaries: [bootstrap, review_engine]
    sdv:
      strength: functional
      distance: cross-boundary
      volatility: low
```

**Note on ID renumbering**: the pilot doc used CDR-001..005 for five pair-level drafts. The
ledger renumbers: the checksums hub (pilot 001/002/005) becomes ledger CDR-001; pilot CDR-003
(session.json) becomes ledger CDR-002; pilot CDR-004 (validate) becomes ledger CDR-003. The
implementer should add a one-line mapping comment at the top of the decisions list so the pilot
doc's numbering remains traceable:
```yaml
# Migrated from CDR pilot 2026-07: pilot 001/002/005 -> CDR-001 (hub-collapsed);
# pilot 003 -> CDR-002; pilot 004 -> CDR-003.
```

## 5. Validation test — `tests/test_cdr_ledger.py`

Two test classes:

**TestLedgerFileValid** — loads `.agent/coupling_decisions.yaml` via `yaml.safe_load` and
asserts, against the ACTUAL ledger file:
1. `version == 1`; `decisions` is a non-empty list.
2. Every constraint C1–C8 from §3 holds for every entry.
3. Exactly 3 decisions exist post-migration; CDR-001 is file-scoped on
   `bootstrap/checksums.py`; CDR-002 and CDR-003 are the expected pairs (sorted).

**TestConstraintLogic** — tests the constraint checks themselves against in-memory fixtures
(not the real file): an accepted-without-rationale entry fails C1; a tolerated/unevaluated
WITH a rationale fails C3; an unsorted pair fails C5; a duplicate id fails C7; etc. Implement
the constraint checks as a small importable function (e.g. `validate_ledger(data) -> list[str]`
returning violation messages) inside the test module OR as a tiny
`.agent/scripts/cdr_ledger_validate.py` — implementer's choice, but if a script, it must be
import-only-no-side-effects so the reconciler can reuse `validate_ledger` in Piece 2.
Recommendation: the small script, since Piece 2 will want to import the loader/validator.

## 6. Acceptance criteria

- [ ] `.agent/coupling_decisions.yaml` exists, `version: 1`, exactly 3 decisions, content
      matching §4 (rationale wording may be lightly edited for YAML formatting but must not
      change meaning; observed metrics and statuses exactly as specified).
- [ ] Pilot-to-ledger ID mapping comment present.
- [ ] `tests/test_cdr_ledger.py` passes: real-file validation + constraint-logic fixtures.
- [ ] Full `pytest tests/ -q` green (no regressions).
- [ ] No existing file modified except the two new files (+ optional small validator script).
- [ ] The reconciler is NOT touched in this piece.

## 7. Reviewer notes (Peter)

- The one judgment already made for you: the checksums hub-collapse (3 pilot entries → 1
  file-scoped entry). Verify the collapse reads correctly in the migrated file — it's the
  schema's key feature being exercised.
- Constraint C3 (unevaluated forbids rationale) is the anti-confabulation guard made
  mechanical. The fixture test for it matters more than it looks: it's what will later stop an
  agent bulk-inserting baseline entries WITH invented rationales.
- Flash has zero design latitude here by intent. If it asks a design question or deviates from
  §4's content, that's a stop-and-check, not a judgment call for it to make.
