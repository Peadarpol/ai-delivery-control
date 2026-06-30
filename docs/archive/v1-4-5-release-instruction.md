# v1.4.5 Release Instruction
**Repository**: `C:\projects\ai-delivery-control`
**Current branch**: `fix/code-review-hallucination-checks`
**Starting point**: Commit `c78b7a9a` (hallucination checks added to code-review SKILL.md)
**Target**: Merge branch `fix/code-review-hallucination-checks` into `main` as release v1.4.5

---

## Standing documentation rule (applies to every commit in this instruction)

After each themed commit below, update the relevant planning documents
**in the same commit** (not a separate docs commit):

- `docs/planning/FRAMEWORK_BACKLOG.md` — mark completed HIB/S0/T1 items as `✅ (v1.4.5)`
- `docs/planning/FRAMEWORK_ROADMAP.md` — add v1.4.5 milestone section (see Commit 5)
- `docs/planning/CAPABILITY_INVENTORY.md` — update relevant capability cards to reflect
  changes (Last reviewed date, Current limitations sections, backlog dependency markers)

Do not leave any of these documents in a state that claims an item is `⬜` when it has
just been completed. The documentation must be accurate after each commit, not just at
the end of the release.

---

## Prerequisites

Confirm the repository is in a clean state:

```powershell
cd C:\projects\ai-delivery-control
git status
git log --oneline -5
```

Expected: `fix/code-review-hallucination-checks` is the current branch, working tree is
clean, `c78b7a9a` is the HEAD commit.

---

## COMMIT 1 — Gate trustworthiness: GATE_SKIPPED event + commit message fix

**Theme**: Two gate reliability bugs that have been open since v1.0.0 — silent gate bypass
and the commit message not being read at the `commit-msg` stage.

**Files to modify**:
- `src/scripts/ai_review.py`

---

### Fix A — HIB-014/017: Write GATE_SKIPPED to audit log when gate does not fire

When `ai_review.py` exits early for any reason other than a legitimate PASS/WARN/FAIL
verdict (e.g. missing API key, empty diff with no pre-flight, wrong hook stage detection,
exception before the LLM call), it currently exits silently with no log entry.

Find the earliest exit paths in `ai_review.py` — specifically:
- The path where the diff is empty AND pre-flight shortcut is not applicable
- The path where the provider raises an auth/config error before any LLM call
- The top-level `except` handler that exits with a non-verdict code

In each of these early-exit paths, before `sys.exit()`, write a `GATE_SKIPPED` entry to
`.ai-review-log.jsonl` using the same append pattern already used by `_persist_verdict()`.
The entry must include:

```json
{
  "timestamp": "<ISO UTC>",
  "session_id": "<from session.json or 'unknown'>",
  "verdict": "GATE_SKIPPED",
  "skip_reason": "<one of: EMPTY_DIFF | PROVIDER_ERROR | EXCEPTION | DIFF_TOO_LARGE_FAILOPEN>",
  "diff_hash": "<hash of staged diff or 'none'>",
  "harness_version": "<from harness_version.txt>"
}
```

Also write a `gate_skipped` event to `.agent/state/harness_events.jsonl` using the
existing event-writing pattern in `ai_review.py`.

Note: `DIFF_TOO_LARGE_FAILOPEN` already has a log path — verify it is writing a
`GATE_SKIPPED` (or equivalent) record and update it to match the new schema if not.
The pre-flight PASS_FAST path is NOT a skip — leave that unchanged.

---

### Fix B — HIB-021 (BUG-09): Read commit message from sys.argv[1] at commit-msg stage

At the `commit-msg` hook stage, Git passes the path to the commit message file as
`sys.argv[1]`. The current `ai_review.py` does not read from this path — it either
ignores the commit message or reads from a hardcoded location.

Find where the commit message is read (or should be read) in `ai_review.py`. Update the
code to:

1. Check if `len(sys.argv) > 1` and `sys.argv[1]` is a readable file path
2. If so, read the commit message from `Path(sys.argv[1]).read_text(encoding="utf-8")`
3. Make the commit message available to the review context (injected as a field in the
   prompt or as part of the `GateContext`) so the reviewer can evaluate intent alignment

If the commit message is already injected into the review context via a different
mechanism (check the code), verify it is being read correctly from `sys.argv[1]` and
update any hardcoded or fallback path.

---

### Documentation updates for Commit 1

In the same commit, update:

**`docs/planning/FRAMEWORK_BACKLOG.md`**:
- Mark `HIB-014` as `✅ (v1.4.5)` with note: "GATE_SKIPPED event written on all early-exit paths"
- Mark `HIB-017` as `✅ (v1.4.5)` with note: "GATE_SKIPPED entry written to .ai-review-log.jsonl and harness_events.jsonl"
- Mark `HIB-021` / `BUG-09` as `✅ (v1.4.5)` with note: "sys.argv[1] read at commit-msg stage"

**`docs/planning/CAPABILITY_INVENTORY.md`**:
- In the AI Adversarial Review Gate card, remove or update any "Current limitations"
  bullet that described the commit message gap or silent gate bypass
- Update "Backlog dependencies" section to mark these resolved

---

### Commit 1 message

```
git add src/scripts/ai_review.py docs/planning/FRAMEWORK_BACKLOG.md docs/planning/CAPABILITY_INVENTORY.md
git commit --no-verify -m "fix(gate): GATE_SKIPPED audit event + commit message from sys.argv[1]

HIB-014/017: Write GATE_SKIPPED entry to .ai-review-log.jsonl and
harness_events.jsonl on all early-exit paths (EMPTY_DIFF, PROVIDER_ERROR,
EXCEPTION, DIFF_TOO_LARGE_FAILOPEN). Silent gate absence was worse than a
loud failure — an uninstrumented bypass is invisible to the audit trail.

HIB-021/BUG-09: Read commit message from sys.argv[1] at commit-msg hook
stage. Git passes the COMMIT_EDITMSG path as the first argument to the
hook; the previous implementation did not read from this path, causing
'no commit message provided' errors even when a message existed.

Docs: FRAMEWORK_BACKLOG.md and CAPABILITY_INVENTORY.md updated."
```

---

## COMMIT 2 — Cross-platform portability: remove Windows-only cmd /c from hooks

**Theme**: HIB-042 — every local hook in the pre-commit template uses `cmd /c` which
is Windows shell syntax and breaks silently on Linux/macOS.

**File to modify**:
- `bootstrap/templates/pre-commit-config.yaml.template`

---

### The fix

In `bootstrap/templates/pre-commit-config.yaml.template`, find every local hook entry
that uses the pattern:

```yaml
entry: cmd /c [PROJECT_PACKAGE_MANAGER] run python ...
```

Replace each with the cross-platform equivalent:

```yaml
entry: [PROJECT_PACKAGE_MANAGER] run python ...
```

The `[PROJECT_PACKAGE_MANAGER]` placeholder is already substituted by `install.py` at
install time with the detected package manager (`poetry`, `uv`, or `pip`). Removing
`cmd /c` allows the hook entry to be invoked directly by pre-commit's `language: system`
runner on any platform.

After making the substitution, verify:
1. Every local hook in the template that previously had `cmd /c` now has the package
   manager invocation directly
2. No hook entries use `cmd /c` or any other Windows-shell-specific prefix
3. The hook entries remain syntactically valid YAML

Also check `bootstrap/install.py` to confirm the `[PROJECT_PACKAGE_MANAGER]` substitution
logic handles `language: system` hooks correctly and does not reintroduce `cmd /c` during
installation.

If `docs/getting-started.md` contains Windows-specific hook installation instructions
that don't mention Linux/macOS equivalents, add a brief cross-platform note.

---

### Documentation updates for Commit 2

**`docs/planning/FRAMEWORK_BACKLOG.md`**:
- Mark `HIB-042` as `✅ (v1.4.5)` with note: "cmd /c removed from all local hook entries in pre-commit-config.yaml.template"

**`docs/planning/CAPABILITY_INVENTORY.md`**:
- If there is a Bootstrap / Install card, update it to note cross-platform hook portability is resolved

---

### Commit 2 message

```
git add bootstrap/templates/pre-commit-config.yaml.template bootstrap/install.py docs/planning/FRAMEWORK_BACKLOG.md docs/planning/CAPABILITY_INVENTORY.md
git commit --no-verify -m "fix(bootstrap): remove Windows-only cmd /c from pre-commit hook template

HIB-042: All local hooks in pre-commit-config.yaml.template used
'cmd /c [PKG_MGR] run python ...' — Windows cmd shell syntax that fails
silently on Linux/macOS. pre-commit's language: system invokes the entry
string directly; cmd is not present on non-Windows platforms.

Replaced with '[PKG_MGR] run python ...' — the package manager binary
handles subprocess creation cross-platform. The [PROJECT_PACKAGE_MANAGER]
placeholder is still substituted by install.py at install time.

Impact: any non-Windows installation previously had hooks that appeared
wired (present in .git/hooks/) but never executed — the AI review gate,
architecture checks, and session heartbeat all silently failed to run.

Docs: FRAMEWORK_BACKLOG.md and CAPABILITY_INVENTORY.md updated."
```

---

## COMMIT 3 — Governance language audit + model diversification + validate.py visual fix

**Theme**: Three small documentation and polish items that improve day-one experience.

**Files to modify**:
- `.agent/AGENTS.md`
- `docs/configuration.md`
- `bootstrap/validate.py`

---

### Fix A — HIB-025: AGENTS.md governance language audit

Read `.agent/AGENTS.md` in full. Identify every governance-critical instruction that uses
weak language: "should", "consider", "it is recommended", "you may", "try to".

Replace with imperative language in sections that govern behaviour the harness requires:
- "should run" → "must run"
- "consider escalating" → "escalate"
- "it is recommended to" → (delete the preamble, state the instruction directly)
- "you may want to" → "you must" (where the action is non-optional)

**Do not change** the conversational sections (skill descriptions, rationale explanations,
context sections). The target is governance-critical sections only: session startup
protocol, prohibited commands, escalation triggers, commit discipline, and
outcome_override conditions.

The prohibition table already uses correct imperative language — do not modify it.

After the audit, verify that no governance-critical instruction uses weak language.
Non-governance sections (e.g. agent conduct, spirit of the rules, rationale paragraphs)
may retain conversational tone.

---

### Fix B — HIB-043: Model diversification guidance in docs/configuration.md

In `docs/configuration.md`, find the section documenting `model_routing:` configuration
(or wherever `review_provider` and `review_model` are documented).

Add a "Cross-family review recommendation" note immediately after the `review_model`
documentation:

```markdown
**Cross-family review recommendation**: For maximum gate effectiveness, configure
`review_provider` to use a *different model family* from your primary writing agent
where possible (e.g. if writing with Claude Code, configure the review gate to use
OpenAI or an Ollama model; if writing with GPT-4, configure the review gate to use
Anthropic or Ollama).

Same-model review catches structural violations, format errors, and most semantic errors,
but creates correlated blind spots — both the writing agent and the reviewing model share
the same training-time failure modes. Cross-family review eliminates this correlation.
Same-model review is still significantly better than no gate.
```

---

### Fix C — T1-B-08: validate.py warning visual representation

In `bootstrap/validate.py`, find the `run_check()` method (or equivalent runner that
prints the ✅ / ❌ / ⚠️ symbols).

The current bug: when a check function returns `(True, details)` but has already
incremented `self.warnings` internally (e.g. `validate_tools` when pre-commit is missing
from PATH), the runner prints `✅` because the return value is `True`. This is misleading
— a warning state should display `⚠️`.

Fix: the check function should signal warning state through the return value, not a
side-effect. Options:
1. Return a third value: `(True, details, is_warning)` — the runner uses `⚠️` if
   `is_warning` is True
2. Return a special sentinel that the runner maps to `⚠️`
3. Have the check function return `(False, details)` for warnings and have the runner
   distinguish between ERROR and WARN based on a separate accumulator

Choose the approach that requires the least invasive change to the existing `run_check()`
callers. The goal is: any check that increments `self.warnings` but does not increment
`self.errors` should display `⚠️` not `✅` in the terminal output.

Apply the fix and verify all existing check functions still produce correct visual output.

---

### Documentation updates for Commit 3

**`docs/planning/FRAMEWORK_BACKLOG.md`**:
- Mark `HIB-025` as `✅ (v1.4.5)` with note: "AGENTS.md governance sections audited; must/always/never language applied to all non-negotiable instructions"
- Mark `HIB-043` as `✅ (v1.4.5)` with note: "Cross-family review recommendation added to docs/configuration.md"
- Mark `T1-B-08` as `✅ (v1.4.5)` with note: "validate.py check runner updated to display ⚠️ for warning states rather than ✅"

**`docs/planning/CAPABILITY_INVENTORY.md`**:
- In the Bootstrap / Validate card (if present), note that the warning visual representation is corrected

---

### Commit 3 message

```
git add .agent/AGENTS.md docs/configuration.md bootstrap/validate.py docs/planning/FRAMEWORK_BACKLOG.md docs/planning/CAPABILITY_INVENTORY.md
git commit --no-verify -m "fix(governance): AGENTS.md language audit, model diversity guidance, validate.py warning display

HIB-025: Audit AGENTS.md governance-critical sections. Replace weak
language (should/consider/recommended) with imperative (must/always/never)
in: session startup protocol, escalation triggers, commit discipline,
prohibited command sections, and outcome_override conditions. Non-governance
sections retain conversational tone.

HIB-043: Add cross-family review recommendation to docs/configuration.md
under model_routing. Correlated blind spots in same-model review eliminated
by using a different LLM family for the review gate vs the writing agent.
Same-model review is still better than no gate — this is an optimisation,
not a requirement.

T1-B-08: Fix validate.py check runner — warning states now display ⚠️
rather than ✅. Previously, checks that returned True but incremented
self.warnings were visually indistinguishable from clean passes.

Docs: FRAMEWORK_BACKLOG.md and CAPABILITY_INVENTORY.md updated."
```

---

## COMMIT 4 — S0-13 GitHub topics (documentation only)

**Theme**: Two GitHub topic tags. Zero code. Claimed as ⬜ since v1.1.0.

**File to modify**:
- `README.md` (one sentence addition only)

Note: GitHub topic tags themselves must be set manually by you via the GitHub web UI
after this commit merges — they cannot be set from within a commit. This commit adds
the topic names to the README as a visible record of intent and improves discoverability
for users who browse the README.

---

### The change

In `README.md`, find the section that describes the repository's positioning or the
footer/metadata area. Add one sentence that names the topics:

```markdown
**GitHub topics**: `ai-delivery-control` · `agent-harness` · `harness-engineering` ·
`agentic-sdlc` · `governance` · `llm-governance`
```

Place this where it is visible but not intrusive — the existing badges line or the end
of the introduction paragraph is appropriate.

---

### Documentation updates for Commit 4

**`docs/planning/FRAMEWORK_BACKLOG.md`**:
- Mark `S0-13` as `✅ (v1.4.5)` with note: "Topics named in README; set via GitHub UI after merge"

---

### Commit 4 message

```
git add README.md docs/planning/FRAMEWORK_BACKLOG.md
git commit --no-verify -m "docs(readme): add GitHub topic names for discoverability

S0-13: Name the repository's GitHub topics in README (agent-harness,
harness-engineering, agentic-sdlc, governance, llm-governance).
Topics must be set manually via GitHub web UI after merge — this commit
records the intent and improves README discoverability.

Docs: FRAMEWORK_BACKLOG.md updated."
```

---

## COMMIT 5 — Release infrastructure: migration module, checksums, version bump

**Theme**: The release mechanics — everything needed for the v1.4.5 checksum-verified
release to be installable and upgradeable.

**Files to create/modify**:
- `bootstrap/migrations/v1_4_4_to_v1_4_5.py` (CREATE)
- `harness_version.txt` (MODIFY)
- `bootstrap/checksums.py` (MODIFY — via generate_checksums.py)
- `docs/planning/FRAMEWORK_ROADMAP.md` (MODIFY — add v1.4.5 milestone)
- `docs/planning/FRAMEWORK_BACKLOG.md` (MODIFY — any remaining status updates)
- `CHANGELOG.md` (MODIFY — add v1.4.5 entry)

---

### Step 5.1 — Create migration module v1_4_4_to_v1_4_5.py

Create `bootstrap/migrations/v1_4_4_to_v1_4_5.py` using the same structure as
the most recent migration module (`v1_4_3_to_v1_4_4.py`). Read that file first to
understand the exact template.

The v1.4.5 migration has:
- No config schema changes (no new keys in `.agent/config.yaml`)
- Framework-owned file updates only (SKILL.md updated, ai_review.py updated,
  pre-commit template updated, AGENTS.md updated, validate.py updated)

The migration module must:
1. Define `FROM_VERSION = "1.4.4"` and `TO_VERSION = "1.4.5"`
2. Define `MIGRATION_TYPE = "patch"`
3. Copy the updated framework-owned files to the target installation:
   - `.agent/skills/universal/code-review/SKILL.md` (hallucination checks added)
   - `src/scripts/ai_review.py` (GATE_SKIPPED + sys.argv[1] fixes)
   - `bootstrap/templates/pre-commit-config.yaml.template` (cmd /c removed)
   - `.agent/AGENTS.md` (governance language audit)
   - `bootstrap/validate.py` (warning display fix)
4. Include the standard pre-migration backup and post-migration verification steps
   matching the pattern in the existing migration modules

Do not add config mutations — this release has no config schema changes.

---

### Step 5.2 — Bump harness_version.txt

```
echo 1.4.5 > harness_version.txt
```

Verify the file contains exactly `1.4.5` with no trailing whitespace.

---

### Step 5.3 — Generate checksums for v1.4.5

```powershell
python bootstrap/generate_checksums.py --version 1.4.5 --framework-root .
```

This regenerates `bootstrap/checksums.py` with a `V1_4_5` dictionary containing
SHA-256 hashes of all framework-owned files in their v1.4.5 state.

After running, verify `bootstrap/checksums.py` contains a `V1_4_5 = { ... }` dict
with entries (not an empty dict).

Then run the checksum verifier:

```powershell
python bootstrap/generate_checksums.py --verify --framework-root .
```

Expected: "Verification SUCCESSFUL: N files checked cleanly."

If verification fails, stop and report the mismatch before proceeding.

---

### Step 5.4 — Add v1.4.5 milestone to FRAMEWORK_ROADMAP.md

In `docs/planning/FRAMEWORK_ROADMAP.md`, find the section immediately after the
v1.4.4 milestone entry and before the v1.5.0 milestone entry.

Insert the following v1.4.5 milestone section:

```markdown
### v1.4.5 — Gate Reliability, Cross-Platform Portability & Polish ✅ SHIPPED (2026-06-30)

**Goal**: Close a cluster of low-effort, high-value reliability and portability gaps
that have been open since v1.0.0. Keeps v1.5.0 scoped to its Quality Signal Maturity
theme without bundling unrelated polish work into it.

**The gap this addresses**: Three categories of day-one friction for new users and
existing installations: (1) silent gate bypasses leaving no audit trail, (2) pre-commit
hooks that appear wired but never execute on Linux/macOS, and (3) AGENTS.md governance
language that was advisory rather than imperative — violating the Osmani "curse of
instructions" principle the framework itself cites.

**Delivered**:

| ID | Item | Category | Status |
|----|------|----------|--------|
| HIB-014/017 | GATE_SKIPPED audit event on all early-exit paths | Gate reliability | ✅ |
| HIB-021/BUG-09 | Commit message read from sys.argv[1] at commit-msg stage | Gate reliability | ✅ |
| HIB-042 | Remove Windows-only cmd /c from pre-commit hook template | Cross-platform portability | ✅ |
| HIB-025 | AGENTS.md governance language audit (must/always/never) | Governance compliance | ✅ |
| HIB-043 | Cross-family review model recommendation in docs/configuration.md | Documentation | ✅ |
| T1-B-08 | validate.py warning states display ⚠️ not ✅ | UX polish | ✅ |
| S0-13 | GitHub topics named in README | Discoverability | ✅ |
| (skill) | AI hallucination detection checks added to code-review SKILL.md | Skill quality | ✅ |

**Migration**: `bootstrap/migrations/v1_4_4_to_v1_4_5.py` — patch migration, no config
schema changes. Copies updated framework-owned files to the target installation.

**Test suite**: Run `pytest` from the framework root and confirm all tests pass before
tagging.
```

Also update the **Current Sprint Status** section at the bottom of the roadmap:
- Change `**Current Version**: 1.4.4` to `**Current Version**: 1.4.5`
- Update the v1.4.x family line to include `v1.4.5 ✅`

---

### Step 5.5 — Add v1.4.5 entry to CHANGELOG.md

Add a new entry at the top of `CHANGELOG.md` following the existing format:

```markdown
## [1.4.5] — 2026-06-30

### Gate Reliability
- **GATE_SKIPPED audit event** (HIB-014/017): All early-exit paths in `ai_review.py`
  now write a `GATE_SKIPPED` entry to `.ai-review-log.jsonl` and `harness_events.jsonl`
  with a typed `skip_reason`. Silent gate absence is no longer invisible to the audit trail.
- **Commit message read correctly** (HIB-021/BUG-09): At the `commit-msg` hook stage,
  the gate now reads the commit message from `sys.argv[1]` (the path Git passes to the
  hook), resolving "no commit message provided" errors.

### Cross-Platform Portability
- **Pre-commit hook template** (HIB-042): Removed Windows-only `cmd /c` prefix from all
  local hook entries in `bootstrap/templates/pre-commit-config.yaml.template`. Hooks now
  invoke the package manager directly, working correctly on Linux/macOS. Previously, all
  hooks silently failed to execute on non-Windows platforms despite appearing wired.

### Governance & Skill Quality
- **AGENTS.md language audit** (HIB-025): Governance-critical sections updated to use
  imperative language (must/always/never) rather than advisory language
  (should/consider/recommended). Complies with the Osmani "curse of instructions"
  principle — imperative commands produce materially better agent compliance than
  polite suggestions.
- **AI hallucination detection checks** added to `universal/code-review/SKILL.md`:
  four new passes targeting API hallucinations (non-existent method calls), latent race
  conditions (correct synchronous, broken concurrent), implicit security vulnerabilities
  (f-string SQL, unsafe deserialization, auth token exposure), and architectural technical
  debt (locally correct, globally inconsistent). Source: FractalDevelop AI-Powered
  Developer Manifest (June 2026), §2.3.

### Documentation & UX
- **Model diversification guidance** (HIB-043): Cross-family review recommendation added
  to `docs/configuration.md` — configure review gate on a different model family from the
  writing agent to eliminate correlated blind spots.
- **validate.py warning display** (T1-B-08): Warning states now correctly display ⚠️
  rather than ✅ in validation output.
- **GitHub topics** (S0-13): Repository topics named in README (`agent-harness`,
  `harness-engineering`, `agentic-sdlc`, `governance`, `llm-governance`).
```

---

### Step 5.6 — Run the full test suite

```powershell
pytest
```

Expected: all tests pass (the two known failing `test_harness_health.py` timezone tests
are pre-existing and unrelated to v1.4.5 changes — note them but do not block on them
if they were failing before this work began).

If any test fails that was not failing before this work, stop and report before committing.

---

### Commit 5 message

```
git add bootstrap/migrations/v1_4_4_to_v1_4_5.py harness_version.txt bootstrap/checksums.py docs/planning/FRAMEWORK_ROADMAP.md docs/planning/FRAMEWORK_BACKLOG.md CHANGELOG.md
git commit --no-verify -m "release: v1.4.5 — gate reliability, cross-platform portability, skill quality

Release infrastructure for v1.4.5:
- bootstrap/migrations/v1_4_4_to_v1_4_5.py: patch migration module
  (no config schema changes; copies updated framework-owned files)
- harness_version.txt: 1.4.4 → 1.4.5
- bootstrap/checksums.py: V1_4_5 checksum registry generated for all
  framework-owned files
- docs/planning/FRAMEWORK_ROADMAP.md: v1.4.5 milestone added; current
  version updated to 1.4.5
- CHANGELOG.md: v1.4.5 entry added

All 8 items delivered:
HIB-014/017 (GATE_SKIPPED event), HIB-021/BUG-09 (sys.argv[1]),
HIB-042 (cross-platform hooks), HIB-025 (AGENTS.md language),
HIB-043 (model diversity docs), T1-B-08 (validate.py visual),
S0-13 (GitHub topics), code-review SKILL.md (hallucination checks)"
```

---

## Final verification

After all 5 commits:

```powershell
git log --oneline -8
```

Confirm 5 commits on `fix/code-review-hallucination-checks` above the original
`c78b7a9a` base commit.

```powershell
python bootstrap/generate_checksums.py --verify --framework-root .
```

Expected: "Verification SUCCESSFUL"

```powershell
python bootstrap/validate.py --project-path .
```

Expected: 0 errors, ≤ 2 warnings (known pre-existing).

```powershell
pytest --tb=short -q 2>&1 | tail -5
```

Expected: pass count matches pre-work baseline (note any new failures).

```powershell
python -c "from bootstrap import checksums; print('V1_4_5' in dir(checksums), len(checksums.V1_4_5))"
```

Expected: `True <N>` where N > 0.

---

## After all verifications pass — stop

Do NOT push. Do NOT raise a PR. Stop after the 5 commits and verifications, and report:

1. All 5 commit SHAs
2. The checksum verification output
3. The validate.py output
4. The pytest pass/fail summary
5. Confirm `V1_4_5` is present in `bootstrap/checksums.py` with the file count

The PR to main and the git tag `v1.4.5` will be raised by the human architect after
reviewing the branch.

---

## Post-merge actions (human, not Gemini)

After reviewing and merging the PR:

1. `git tag -s v1.4.5 -m "v1.4.5 — gate reliability, cross-platform portability, skill quality"`
2. `git push origin v1.4.5`
3. Set GitHub topics on the repository: `agent-harness`, `harness-engineering`,
   `agentic-sdlc`, `governance`, `llm-governance` (via GitHub web UI → repository settings)
4. Update GymBase to pull the v1.4.5 harness and copy the updated code-review SKILL.md
   into `C:\projects\Gym_App\.agent\skills\code-review\SKILL.md`
