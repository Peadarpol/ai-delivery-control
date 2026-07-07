# SPEC: Reconciler ↔ CDR Ledger Integration (T1-B-12 Piece 2)

**Task ID**: T1-B-12 Piece 2 (depends on T1-B-09 ✅ and T1-B-12 Piece 1 ✅, both delivered)
**Type**: Logic change to the working reconciler CLI. Touches a real pipeline, not transcription.
**Status**: DRAFT — awaiting Peter's approval before implementation
**Implementer**: a strong-reasoning model (Pro or equivalent) — NOT Flash. This is matching/
filtering logic against the existing reconciler, not mechanical transcription.
**Reviewer**: Peter — verified by tests + a proof run comparing before/after report output
**Explicitly NOT in scope**: brownfield baseline bulk-population tooling (separate, future
Piece 3); any change to the CDR ledger schema or `cdr_ledger_validate.py`'s contract (Piece 1
is fixed); any change to the reconciler's core detection/ranking algorithm (§2.2 steps 1–7 of
the original reconciler spec are untouched).

---

## 0. What this closes

Right now the reconciler (T1-B-09) and the CDR ledger (T1-B-12 Piece 1) are **two independent
artifacts**. The reconciler still flags CDR-001/002/003's crossings as raw undeclared findings
— it has never read the ledger. This piece wires them together: the reconciler becomes a
**filter**, not just a detector, using the ledger's recorded decisions to distinguish genuinely
new/undeclared crossings from ones a human has already judged.

## 1. Inputs (already built, do not modify)

- The reconciler's existing pipeline (`.agent/scripts/co_change_reconciler.py`) up through
  ranking (steps 1–7 of its spec): produces a list of crossings, each with
  `(file_a, boundary_a, file_b, boundary_b, co_changes, p_max)`.
- `.agent/scripts/cdr_ledger_validate.py`: exposes `validate_ledger(data) -> list[str]`.
  **This piece will need the loader too** — confirm whether a `load_ledger(path) -> dict` (or
  similar) already exists in that module. If not, add one (thin: `yaml.safe_load` + return the
  parsed dict; call `validate_ledger` on it and raise/warn on any violations before use — do not
  silently proceed with a ledger that fails its own constraints).
- `.agent/coupling_decisions.yaml`: the ledger, 3 entries as of Piece 1.

## 2. New logic

### 2.1 Load and validate the ledger

At startup (after boundary loading, before/alongside co-change computation):
- Look for `.agent/coupling_decisions.yaml` (or `--project-root`-relative equivalent, matching
  the reconciler's existing `--project-root` convention).
- **If absent**: proceed as if there are zero decisions — every crossing is "undeclared." Do
  NOT error; an adopter with no ledger yet should get the current (Piece-1-era) behaviour, not a
  crash. Print an informational note in the report ("no CDR ledger found — all crossings shown
  as undeclared").
- **If present**: load via the ledger module, run `validate_ledger` on it. If violations are
  returned, **halt with a clear error listing the violations** — do not proceed with a
  malformed ledger silently ignoring bad entries. This mirrors the harness's fail-closed
  philosophy elsewhere.

### 2.2 Match each crossing against the ledger

For each ranked crossing `(file_a, file_b, co_changes, p_max)`, check every ledger entry:

- **`scope: pair`** matches iff `{entry.files[0], entry.files[1]} == {file_a, file_b}`
  (set-equality; do not assume the ledger's sort order or the crossing's order agree).
- **`scope: file`** matches iff `entry.file == file_a OR entry.file == file_b`.

A crossing may match **at most one entry** in the current ledger (Piece 1's 3 entries don't
overlap, but don't assume that always holds) — if a crossing matches more than one entry,
**flag it as an ambiguous-match warning** in the report rather than silently picking one. This
is a real data-integrity signal (the ledger has redundant/conflicting entries) and should be
visible, not swallowed.

### 2.3 Classify each crossing

Given the match result and the matched entry's `status` (if any):

| Match? | Entry status | Classification |
|---|---|---|
| No match | — | **UNDECLARED** (the actionable list — this is what Piece-1-era behaviour showed for everything) |
| Matched | `accepted` | **ACCEPTED** (sanctioned, informational) |
| Matched | `tolerated` | **TOLERATED** (known debt, visible, not urgent) |
| Matched | `resolved` | **UNDECLARED + flagged "previously resolved — regression?"** (a resolved coupling reappearing is itself worth surfacing) |
| Matched >1 entry | any | **AMBIGUOUS** (data-integrity warning, list separately) |

### 2.4 Escalation check (for ACCEPTED and TOLERATED matches only)

Compare the crossing's **current** `co_changes` and `p_max` against the matched entry's
`observed` snapshot:
- If current `co_changes >= observed.co_changes * 1.5` **OR** current `p_max` exceeds
  `observed.p_max` by more than `0.15` absolute — mark the entry **ESCALATED** in addition to
  its status (e.g. "ACCEPTED — ESCALATED").
- These two thresholds (`1.5x` frequency, `+0.15` probability) are defaults; expose as CLI
  flags `--escalation-freq-multiplier` and `--escalation-prob-delta` so they're tunable once
  you see real escalation behaviour (same "make it a flag, don't guess the right constant"
  philosophy as the original reconciler's gate/floor defaults).
- An escalated entry should be **visually distinct** in the report (its own subsection or a
  clear marker) — the whole point is that a sanctioned coupling getting worse shouldn't hide
  silently inside "accepted, nothing to see here."

## 3. Report format changes (`.agent/state/co_change_reconciliation_report.md`)

Replace the single flat table with four sections, in this order:

```markdown
# Co-Change Reconciliation Report

**Generated**: <ISO datetime>  **Ledger**: <path, or "none found">
**Target**: <project root>  **Window / gate / floor**: <as before>

## 1. Undeclared boundary-crossing co-change (<count>)
[same table format as before — this is the actionable list]
[if any are "previously resolved" regressions, mark them: "⚠ RESOLVED-REGRESSION" in a Notes column]

## 2. Escalated (sanctioned couplings that have gotten worse) (<count>)
| Rank | File A | File B | CDR ID | Status | Observed (at decision) | Current | Δ |
[only entries where §2.4 flagged escalation — empty section is fine and expected initially]

## 3. Tolerated — known coupling debt (<count>)
[matched, status=tolerated, not escalated — visible backlog, not urgent]
| File A | File B | CDR ID | Reason | Note |

## 4. Accepted — sanctioned, informational (<count>)
[matched, status=accepted, not escalated — collapse to a compact list, not full detail,
since these require no action]
| File A | File B | CDR ID | Archetype |

## Ambiguous matches (data integrity — should normally be empty)
[only if any crossing matched >1 ledger entry]

## Notes
[as before, plus: note if no ledger was found]
```

If §1 (Undeclared) is empty, still write the report saying so explicitly (unchanged principle
from the original spec).

## 4. Tests — extend `tests/test_co_change_reconciler.py` (or new file, implementer's choice
   consistent with existing test organisation)

Using the existing fixture-repo pattern (temp git repo + temp `architecture.layers` config),
ADD a temp `coupling_decisions.yaml` to the fixture and assert:

1. A crossing matching a `scope: pair, status: accepted` entry lands in section 4, not section 1.
2. A crossing matching a `scope: file, status: accepted` entry (hub case) — matches regardless
   of partner — lands in section 4.
3. A crossing matching NO entry lands in section 1 (unchanged Piece-1-era behaviour).
4. A crossing matching a `status: tolerated` entry lands in section 3, not section 1 or 4.
5. A crossing matching a `status: resolved` entry lands in section 1 WITH the
   regression-warning marker.
6. A crossing whose current co_changes/p_max exceed the matched entry's `observed` values past
   the threshold lands in section 2 (escalated), not section 4.
7. A crossing matching TWO ledger entries (construct a deliberately-overlapping fixture) is
   reported under "Ambiguous matches", not silently resolved.
8. **No ledger file present**: reconciler runs exactly as Piece-1-era (everything in section 1),
   with the "no ledger found" note. No crash.
9. **Malformed ledger** (fixture with a constraint violation, e.g. accepted-without-rationale):
   reconciler halts with a clear error listing the violation(s). No silent pass-through.

## 5. Proof run (the acceptance criterion that matters most)

Run the reconciler against the harness's own repo (which now has a real 3-entry ledger) with
default settings:

- **Expected**: CDR-001, CDR-002, CDR-003's crossings should now appear under section 4
  (Accepted) — NOT section 1 (Undeclared). This is the visible, human-checkable proof that the
  integration works: the exact three findings from the original proof run should have
  "disappeared" from the actionable list and reappeared, correctly labelled, in the accepted
  section.
- If any of the three still show up in section 1, the matching logic has a bug — stop and
  diagnose before accepting.
- Also worth running with the low `--min-commits 1` setting again (as in the original proof
  run) to confirm the 665-crossing case still works sensibly with the ledger applied — the
  three known entries should be pulled into their sections regardless of gate level, since
  matching happens per-crossing, not per-report-section.

## 6. Acceptance criteria

- [ ] Ledger loaded and validated at startup; absent ledger handled gracefully; malformed
      ledger halts with clear errors (not silently ignored).
- [ ] Matching logic implements pair-scope and file-scope correctly (§2.2).
- [ ] Four-way classification (§2.3) + ambiguous-match handling implemented.
- [ ] Escalation check (§2.4) implemented with tunable CLI flags.
- [ ] Report restructured into the four sections (§3).
- [ ] All 9 new test cases (§4) pass.
- [ ] Full `pytest tests/ -q` green, no regressions.
- [ ] **Proof run**: CDR-001/002/003 move from "Undeclared" to "Accepted" in the real report
      against the harness repo. This is checked by reading the actual report file, not by
      trusting a summary.
- [ ] No changes to `cdr_ledger_validate.py`'s public contract, no changes to the reconciler's
      core detection/ranking steps 1–7.

## 7. Reviewer notes (Peter)

- The proof run in §5 is the whole point — if you only check tests-pass, you haven't confirmed
  the integration actually filters real findings. Read the actual report file.
- Escalation thresholds (1.5x, +0.15) are guesses tuned for "not too sensitive." Expect to
  revisit once real escalation data exists — same philosophy as the reconciler's original
  gate/floor defaults.
- The "resolved → regression flag" behaviour (§2.3) has never been exercised on real data
  (nothing's been marked `resolved` yet) — it's speculative until a real resolved-then-recurring
  case happens. Keep it, but don't over-invest in polishing an untested path.
- Ambiguous-match handling is defensive programming against a scenario that shouldn't occur
  with 3 well-formed entries — it's there for when the ledger grows and entries might overlap
  by mistake.
