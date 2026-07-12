# Gemini CLI Developer Guidelines

This document outlines guidelines specific to developers using the Gemini CLI.

---

## Post-Session Close Protocol
At session end, write `.agent/state/agent_session_close.json` following the schema in `.agent/templates/agent_session_close.md`. This file is read at the start of the next session and merged into the session ledger, equivalent to the Claude Code Stop hook outcome recording.
