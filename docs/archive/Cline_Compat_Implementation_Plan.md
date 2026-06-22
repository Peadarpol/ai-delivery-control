# Cline + Ollama Compatibility — ai-delivery-control Framework

## Revision Note

**Target repository**: `C:\projects\ai-delivery-control` (the harness framework itself).
All changes must land here so every downstream `install.py` run automatically deploys
Cline support to consumer projects (like Gym_App).

**User decisions locked in:**
1. **Hooks — defer entirely.** Do not author hook scripts now. Document the design so it
   can be implemented when Cline ships Windows support. A `docs/CLINE_COMPAT.md` page will
   describe the intended hook architecture for future reference.
2. **Review gate stays Anthropic.** `ai_review.py` continues to call the Anthropic API.
   The Ollama model is Cline's coding inference engine only.
3. **Reuse `session.json` `outcome_override` fields.** No new `cline_session_close.json`.
   The existing `infer_and_close_previous_session()` path already handles this.
4. **Dedicated branch**: `feat/framework-cline-compat` on `ai-delivery-control`.

---

## What Is Already Compatible (No Work Required)

The **git-level enforcement layer is already agent-agnostic**. On any consumer project:
- `pre-commit`, `commit-msg`, `post-commit` hooks fire identically regardless of which
  agent staged the diff — Cline, Gemini, or a human.
- `ai_review.py` calls the Anthropic API directly via urllib; it is not Cline-aware.
- All SKILL.md files in `.agent/skills/` are structurally compatible with Cline's
  Skills tab (modelled on the Anthropic spec).

The gap is entirely in the **agent-instruction layer**:
- No `CLINE.md` template exists → install.py does not emit one for consumer projects.
- No `.clinerules/` template structure exists → Cline has no structured rules on first install.
- `AGENTS.md §6` documents Gemini's `outcome_override` convention but not Cline's (identical pattern).
- `config.yaml.template` has no `cline_provider` model routing entry.

---

## Proposed Changes

### Phase 1 — `bootstrap/templates/CLINE.md.template`

New template, emitted as `CLINE.md` in the consumer project root by `install.py`.
Follows the same thin-shim pattern as `CLAUDE.md.template` and `GEMINI.md.template`:
- Directs Cline to read `.agent/UNIVERSAL_CONTEXT.md` and `.agent/AGENTS.md` first
- Documents that session startup (`init_session.py --agent Cline`) must be run manually
  (hooks deferred — Windows not supported yet)
- Documents the `outcome_override` session-close convention (same as Gemini)
- Points to `.clinerules/` directory for structured per-topic rules
- Notes that the Anthropic gate fires at git commit regardless of which model Cline uses

#### [NEW] [CLINE.md.template](file:///c:/projects/ai-delivery-control/bootstrap/templates/CLINE.md.template)

---

### Phase 2 — `bootstrap/templates/clinerules/` directory (six rule files)

New template subdirectory. `install.py` copies it to `.clinerules/` in the consumer project.
Each file is a standalone markdown rule file loaded by Cline's Rules panel.

```
bootstrap/templates/clinerules/
├── 01-startup.md         Session startup protocol (Steps 0–6 from AGENTS.md §1)
├── 02-workflow-first.md  Workflow selection table (AGENTS.md §2) — verbatim
├── 03-prohibitions.md    P-01 through P-14/P-15 table (AGENTS.md §4) — verbatim
├── 04-session-close.md   Session close + outcome_override instruction
├── 05-git-discipline.md  Staging, verification, push-timing rules (AGENTS.md §9)
└── 06-environment.md     Project-specific env (OS, package manager, test cmd, model note)
```

`04-session-close.md` contains the Cline-specific close instruction, parallel to the
Gemini HIB-GEMINI-01 note in AGENTS.md §6:

```
## Session Close — Cline-Specific

Cline has no native Stop hook. Before ending any Cline task, write the following
fields to .agent/state/session.json in addition to the standard session close steps:

  "outcome_override": "success | partial | abandoned | escalated"
  "outcome_override_source": "agent_override"
  "outcome_override_note": "One-sentence summary."

This is the same pattern as Gemini CLI (HIB-GEMINI-01). It is the only way
infer_and_close_previous_session() gets the same close fidelity as a Claude session
with the Stop hook.
```

`06-environment.md` uses template placeholders (`[PROJECT_PACKAGE_MANAGER]`,
`[TEST_RUN_ALL_COMMAND_PLACEHOLDER]`) so `install.py` renders it per-project.

#### [NEW] `bootstrap/templates/clinerules/01-startup.md`
#### [NEW] `bootstrap/templates/clinerules/02-workflow-first.md`
#### [NEW] `bootstrap/templates/clinerules/03-prohibitions.md`
#### [NEW] `bootstrap/templates/clinerules/04-session-close.md`
#### [NEW] `bootstrap/templates/clinerules/05-git-discipline.md`
#### [NEW] `bootstrap/templates/clinerules/06-environment.md`

---

### Phase 3 — `bootstrap/install.py` updates

Three additions to `Installer`:

**3a. Emit `CLINE.md`** (in `scaffold_configurations()`, alongside CLAUDE.md/GEMINI.md):
```python
("CLINE.md.template", "CLINE.md"),
```
Same skip-if-exists idempotency as the other shims.

**3b. Copy `.clinerules/` template directory** (new helper method `install_clinerules()`
called from `run()`):
- Source: `bootstrap/templates/clinerules/`
- Destination: `<project_path>/.clinerules/`
- Renders placeholder substitutions on each `.md` file (using the same `replacements`
  dict already built in `scaffold_configurations()`)
- Idempotent: skips files that already exist (preserve consumer customisations)

**3c. Update `update_gitignore()`** to add one new entry alongside `gemini_session_close.json`:
```
.clinerules/hooks/   # hook scripts are env-specific, not project history
```
(Hook scripts, when they eventually exist, should not be committed to consumer projects —
they will be generated by `install.py` at that future point.)

#### [MODIFY] [install.py](file:///c:/projects/ai-delivery-control/bootstrap/install.py)

---

### Phase 4 — `bootstrap/templates/config.yaml.template`

Add a `cline` documentation block under `model_routing`:

```yaml
model_routing:
  # ... existing entries (wiki_compile_provider, budget_provider, review_provider) ...

  # Cline (VS Code) — local Ollama-hosted coding agent
  # Set cline_model to the model name pulled in your local Ollama instance.
  # This entry is documentation only — no harness script reads it at runtime.
  # The ai_review.py gate uses review_provider/review_model regardless of cline_model.
  cline_provider: ollama
  cline_model: null                  # e.g. qwen2.5-coder:32b, deepseek-coder-v2
  cline_base_url: http://localhost:11434
```

#### [MODIFY] [config.yaml.template](file:///c:/projects/ai-delivery-control/bootstrap/templates/config.yaml.template)

---

### Phase 5 — `.agent/AGENTS.md` (framework canonical)

Add a `### Cline — explicit outcome write (HIB-CLINE-01)` subsection to **§6 Session
Close**, immediately after the existing Gemini HIB-GEMINI-01 block.

The subsection documents:
- Same `outcome_override` pattern as Gemini (re-uses existing `infer_and_close_previous_session()` path)
- That Cline Hooks (TaskStart/PreToolUse) would be the enforcement upgrade path, but are
  deferred pending Windows support — see `docs/CLINE_COMPAT.md` for the design
- That `outcome_override_source` should be set to `"agent_override"` (same as Gemini)
- The HIB-053 write-before-verify risk applies identically to Cline sessions

Also update the file's first-line scope comment to mention Cline alongside Gemini/Cursor:
```
> **Scope**: Loaded automatically by Gemini CLI, Claude Code, Cursor, Cline, and other editors.
```

#### [MODIFY] [AGENTS.md](file:///c:/projects/ai-delivery-control/.agent/AGENTS.md)

---

### Phase 6 — `docs/CLINE_COMPAT.md` (deferred hooks design)

New documentation file describing the hooks design that will be activated when Cline
ships Windows support. This is the artefact that satisfies "defer but document."

Contents:
- Platform constraint note (macOS/Linux only as of Cline v3.36, checked June 2026)
- Architecture of the three hooks: `TaskStart`, `PreToolUse`, `PostToolUse`
- Full bash script bodies for each hook (not installed, just documented)
- Implementation checklist for when Windows support ships:
  - Create `bootstrap/templates/clinerules/hooks/` directory with the three scripts
  - Update `install_clinerules()` to copy and `chmod +x` the hook scripts
  - Remove the `hooks/` gitignore entry added in Phase 3c
  - Add a note to `CLINE.md.template` instructing users to enable hooks in Cline Features

#### [NEW] [docs/CLINE_COMPAT.md](file:///c:/projects/ai-delivery-control/docs/CLINE_COMPAT.md)

---

## File Summary

| File | Action | Scope |
|------|--------|-------|
| `bootstrap/templates/CLINE.md.template` | NEW | Emitted as `CLINE.md` in consumer projects |
| `bootstrap/templates/clinerules/01-startup.md` | NEW | Emitted as `.clinerules/01-startup.md` |
| `bootstrap/templates/clinerules/02-workflow-first.md` | NEW | Emitted as `.clinerules/02-workflow-first.md` |
| `bootstrap/templates/clinerules/03-prohibitions.md` | NEW | Emitted as `.clinerules/03-prohibitions.md` |
| `bootstrap/templates/clinerules/04-session-close.md` | NEW | Emitted as `.clinerules/04-session-close.md` |
| `bootstrap/templates/clinerules/05-git-discipline.md` | NEW | Emitted as `.clinerules/05-git-discipline.md` |
| `bootstrap/templates/clinerules/06-environment.md` | NEW | Emitted as `.clinerules/06-environment.md` |
| `bootstrap/install.py` | MODIFY | Add CLINE.md shim + `install_clinerules()` + gitignore entry |
| `bootstrap/templates/config.yaml.template` | MODIFY | Add `cline_provider`/`cline_model` block |
| `.agent/AGENTS.md` | MODIFY | Add HIB-CLINE-01 subsection to §6 |
| `docs/CLINE_COMPAT.md` | NEW | Deferred hooks design documentation |

**Total: 8 new files, 3 modified files. No Python dependencies, no tests to update.**

---

## What This Does NOT Change

| Concern | Verdict |
|---------|---------|
| `ai_review.py` gate (Anthropic API) | Unchanged |
| `pre-commit`/`commit-msg`/`post-commit` hooks | Unchanged |
| `init_session.py` (`outcome_override` path) | Unchanged — Cline reuses existing logic |
| Session ledger schema | Unchanged — `"agent": "Cline"` is freeform string, already supported |
| Existing shim templates (`CLAUDE.md`, `GEMINI.md`, `.cursorrules`) | Unchanged |
| `bootstrap/validate.py` | Unchanged — existing validation still applies |
| `bootstrap/upgrade.py` | **Needs awareness check** — see Open Item below |

---

## Open Item — `upgrade.py`

The `upgrade.py` script manages incremental harness upgrades. After this plan is
implemented, confirm that `upgrade.py` correctly handles:
1. Copying new `CLINE.md.template` to consumer projects (skip-if-exists same as install)
2. Copying new `.clinerules/` template files (skip-if-consumer-customised)

This is **not a blocker** for this branch — it is a follow-up task to be logged in
`docs/planning/FRAMEWORK_BACKLOG.md` after execution.

---

## Verification Plan

### Automated

```powershell
# 1. Run the full existing test suite against the framework
python -m pytest tests/ -v

# 2. Smoke-test install.py against a blank temp project
python bootstrap/install.py --project-path .\scratch\test-cline-install --verbose

# 3. Verify CLINE.md was emitted
Test-Path .\scratch\test-cline-install\CLINE.md

# 4. Verify .clinerules/ directory was emitted with all 6 files
Get-ChildItem .\scratch\test-cline-install\.clinerules\ -Filter "*.md"

# 5. Verify config.yaml contains cline_provider
Select-String "cline_provider" .\scratch\test-cline-install\.agent\config.yaml
```

### Manual (requires Cline in VS Code)

1. Install the harness into a scratch project using the updated `install.py`
2. Open the scratch project in VS Code with Cline
3. Confirm `.clinerules/` files appear in Cline's **Rules panel**
4. Start a Cline task — confirm Rules panel loads all six rule files
5. Open Cline's Skills tab — confirm at least one skill is discoverable

---

## Branch

`feat/framework-cline-compat` on `ai-delivery-control` (to be created from `main`).

Branching convention from AGENTS.md §9.5:
`feat/framework-{item-id}-{short-description} → PR → main`

No item ID assigned yet — use `feat/framework-cline-compat` unless you want to assign one.
