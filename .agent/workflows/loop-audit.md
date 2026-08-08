# Loop Audit Workflow

## Purpose

Determines whether a documented feedback loop actually closes — whether a producer's
claimed output genuinely reaches its consumer, and the consumer genuinely acts on it —
by direct code inspection. This replaces D4a (`SPEC-loop-closure-verification.md`
Tier 4), an automated AST-based orphaned-producer scan that was built, tested against
the real `LOOP_INVENTORY.md`, and retired after flagging 9 of 9 real producer/consumer
pairs as orphaned. The reason: this codebase's actual coupling is almost entirely
file-based (a producer writes a path, a consumer independently reads the same path),
not Python-level imports — the only coupling shape a static scanner can detect. Every
confirmed real defect this project's audits have found (HIB-080, LOOP-001, LOOP-004,
LOOP-013) was file-based or schema-based drift, not a broken import. That category
needs a read, not a scan.

## When to run this

- Before a release, for any loop whose producer or consumer script changed since the
  last audit.
- Whenever a new producer/consumer pair is introduced — add it to `LOOP_INVENTORY.md`
  and audit it the same session, not later.
- On a standing cadence otherwise (recommend: alongside `SPEC-loop-closure-verification.md`
  §9's End-of-Release Tasks, so it happens at least once per release).

## Before starting: identify the loop's shape

`LOOP_INVENTORY.md`'s own taxonomy names six loop shapes, and each needs a different
check — this is the first thing to get right, since collapsing them into one generic
check is itself a source of false confidence (this is precisely the lesson the whole
inventory document opens with):

| Shape | What "closed" actually means | What to check |
|---|---|---|
| Spec-to-test | A spec's claimed outcome has a real test proving it | Does a test assert the *specific* outcome, against the real component, not an adjacent one? |
| Multi-consumer wiring | Shared state reaches every documented consumer | Does each consumer's code genuinely reference the specific field/function claimed, with a real (non-vacuous) value? |
| Session-to-session | A session-close write is read by the next session | Is the read actually mandatory (not just documented as should-happen)? Does the format match? |
| Incident-to-prevention | An incident produces a lasting regression check | Does filing the incident actually gate anything, or does it depend on someone remembering? |
| Self-improvement | A friction signal produces a proposal, and the proposal is usable | Does the producer's output satisfy the consumer's parsing requirements exactly — field names, formats, thresholds? |
| Gate feedback | A FAIL verdict produces a correction that's verified before the next attempt | Is there an artifact confirming the correction happened, or is it agent self-discipline alone? |

## The audit procedure, per loop

1. **Read the producer's actual code.** Not the docstring, not the loop inventory's
   existing summary of it — the real current source. Confirm what it actually writes,
   where, and in what format.
2. **Read the consumer's actual code.** Same standard. Confirm what it actually reads,
   from where, and what format/fields it requires.
3. **Determine the coupling mechanism.** This is the step D4a's failure makes explicit:
   - **Direct code reference** (import, function call) — check if the consumer's code
     literally imports or calls into the producer's module.
   - **File-based** (most common in this codebase) — check whether both scripts
     reference the *same path*, and confirm the file format one writes is exactly
     what the other expects to parse (field names, date formats, schema shape).
     This is where LOOP-001's bug lived: the file existed, the path was shared, but
     one side's format silently didn't satisfy the other's parser.
   - **Schema/contract-based** — check whether both sides agree on a data shape
     (e.g. `DeveloperRebuttal`'s field set in LOOP-016) even without a direct import.
4. **Verify the specific claim, not just "does something happen."** A loop can *run*
   without *closing* — e.g. a producer writing a file nobody reads (LOOP-012), or a
   consumer degrading gracefully to "missing" rather than actually processing real
   data (LOOP-015). Confirm the full path: producer writes → consumer reads → consumer
   acts on what it read, not just that no exception was thrown.
5. **Check for the specific failure classes already found.** Given this project's own
   history, explicitly check for: a hardcoded path in either script that might have
   gone stale since a refactor (LOOP-013's shape); a required field one side writes
   inconsistently with what the other expects (LOOP-001's shape); a documented
   behavior (in a workflow file, spec, or docstring) that doesn't match what the code
   actually does (LOOP-004's shape).
6. **Record the finding in `LOOP_INVENTORY.md`**, using its existing status legend
   (`VERIFIED-WORKING` / `VERIFIED-BROKEN` / `PARTIAL` / `UNVERIFIED` /
   `NOT YET INVESTIGATED`) and its existing per-entry format (Status, Type, Producer,
   Consumer, Finding, with direct citations — file names, function names, line-level
   detail where it matters). Do not mark a loop `VERIFIED-WORKING` without having
   read both sides' actual current code in this session, not from memory of a prior
   audit — code drifts.

## A calibration lesson worth applying here specifically

`LOOP_INVENTORY.md`'s own "Cross-Referenced Findings" section, from triangulating
against an independent audit pass, found: verdicts (is this loop broken or working)
were reliable in 6 of 7 cases checked, but the *specific supporting citations* were
wrong in 2 of the 3 "broken" findings dug into — the right conclusion reached via
the wrong specific fact. Applying that here: trust your own overall verdict, but
before recording a citation (a specific file, function, or line as evidence), confirm
you actually read it this session — don't carry forward a citation from a prior
pass or from what "should" be true given the pattern.

## What this workflow does not do

- It does not attempt to be exhaustive automatically — it runs against whatever loops
  are in `LOOP_INVENTORY.md` at the time, and that document's own completeness is a
  separate, named residual risk (see `SPEC-loop-closure-verification.md` §7).
- It is not a substitute for D1 (contract tests) or D2 (path-staleness scanning) where
  those genuinely apply — this is for the judgment-requiring cases those mechanisms
  can't reach, not a replacement for automation where automation actually works.
- It does not replace `LOOP_INVENTORY.md`'s own "Not Yet Investigated" section — loops
  never yet read at all still need their first pass before a re-audit is meaningful.
