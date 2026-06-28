# Known Risks and Pre-Sprint Checks

This file documents known risks, compatibility assumptions, and pre-sprint verification
items that must be confirmed before starting delivery on a new release milestone.

---

## RISK-001: Antigravity CLI Hook Compatibility (Pre-v1.5.0 Check)

**Status**: Unverified  
**Added**: 2026-06-28  
**Priority**: Must verify before first v1.5.0 delivery session

### Context

Google transitioned Gemini CLI to Antigravity CLI (closed-source Go binary) in June
2026. The harness's Gemini delivery integration depends on the following conventions
that were designed for Gemini CLI:

- `GEMINI.md` shim file — loaded as agent-specific context by the session
- `TaskStart` hook — fires at session start, triggers `init_session.py`
- `gemini_session_close.json` flow — outcome metadata written at session end
- `outcome_override` field in `session.json` — read by `infer_and_close_previous_session()`

### Risk

If Antigravity CLI changes the semantics, file names, or hook events for any of the
above, the session traceability and outcome-recording chain will break silently. The
most likely failure mode is HIB-GEMINI-01 (phantom completion) recurring because the
Stop hook equivalent no longer fires.

### Pre-Sprint Verification (complete before first v1.5.0 Gemini session)

Run a minimal test session in Antigravity IDE and confirm:

1. `GEMINI.md` is loaded at session start (Gemini references project-specific context)
2. `init_session.py` runs at session start (session_id appears in `session.json`)
3. `gemini_session_close.json` can be written at session end without error
4. `outcome_override` written to `session.json` is read correctly by the next
   `init_session.py` call's `infer_and_close_previous_session()`

**If any step fails**: raise a backlog item before starting v1.5.0 delivery and
assess whether a `GEMINI.md` update or hook rewiring is required.

### Owner

Human operator (you) — this is a manual verification task, not agent-deliverable.
