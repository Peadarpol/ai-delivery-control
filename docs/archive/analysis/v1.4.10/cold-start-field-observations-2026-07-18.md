# Cold-Start Field Observations — 2026-07-18

**Status**: INPUT DOCUMENT — five findings; evidence for AT-01, AT-02, AT-08, and a new proposed workstream
**Source**: Live observation, ~90 minutes, Peter guiding a first-time user through
installing `ai-delivery-control` v1.4.9 into their own project
**Author**: Claude, on behalf of Peter Long
**Destination**: `docs/planning/analysis/v1.4.10/` (to be committed by Gemini
alongside `hib-collision-map-2026-07.md` and `incident-chain-2026-07-15.md`)
**Relationship to existing plan**: These findings feed the parked "installer &
onboarding" theme (v1.4.11/v1.5) identified in `ANALYSIS-PLAN-v1.4.10.md` §0, and
directly extend AT-01, AT-02, and AT-08. One finding (F-COLD-4) proposes new scope
not yet in the plan and is flagged for a human decision before adoption.

**Why this document matters**: every fresh-project defect found so far (F1–F8)
was discovered by Claude running a synthetic reproduction. These findings were
discovered by watching an actual first-time user, unassisted by anyone who
understands the harness's internals, hit the real cold-start experience. They are
a different — and arguably stronger — category of evidence, because they surface
problems a scripted reproduction can't: wrong mental models, missing signposting,
and the fact that the harness currently assumes a knowledgeable operator (Peter)
is present to translate its instructions. That assumption is false for essentially
every future user.

---

## Finding 1 — Distribution model: users don't know what to clone, or where

**Observation**: The user cloned `ai-delivery-control`'s repository into a folder and expected it to function
as an independent entity to their project - not quite understanding the install path. They had no model of "harness repo, cloned once, used to install
into an unrelated target project" versus "this repo IS my project." Peter had to
intervene manually and redirect them to have their Gemini instance run the
installer *against* their actual development project.

**Root cause**: Nothing in the README's first screen establishes the two-repo
mental model before commands appear. A user reads "clone this repo" and could clone it
where they're standing — inside the folder they think of as their project — or they could clone it correctly but never run the installation command against their target project.

**Severity**: This is upstream of every other finding. If this doesn't land, no
downstream fix matters — the user never reaches a pre-commit hook, a `pip run`
error, or an API key prompt, because they're not operating on a real target
project at all.

**Proposed remediation**:
- Add an unmissable "you are here" diagram or callout as the *first* thing in
  `docs/getting-started.md` and the README, before any command: two labeled boxes
  — "ai-delivery-control (this repo — clone once, don't work inside it)" and
  "your project (where you run the installer, where you'll actually code)" —
  with an arrow showing the installer runs *from* the first *into* the second.
- Add an installer self-check (extends AT-08's validator work): on startup,
  detect whether the current working directory (or `--project-path` target) *is*
  the `ai-delivery-control` repo itself (e.g., check for `bootstrap/install.py`
  and `harness_version.txt` matching the framework's own signature at the
  target path) and, if so, hard-stop with an explicit message: "This looks like
  the harness's own repository, not a target project. Clone this repo elsewhere,
  then re-run the installer with `--project-path` pointing at your actual
  project." This single check would have caught the observed failure in under
  a second, with no human translator needed.
- **Feeds AT-08** directly: this is exactly the class of "infrastructure problem
  the validator should catch before the user reaches a git hook" that AT-08 is
  already scoped to design.

---

## Finding 2 — Cross-platform path/interpreter assumptions (extends F1, new axis)

**Observation**: On macOS, several harness scripts needed manual editing so
commands were prefixed with `.venv/bin/...` (the macOS/Linux venv layout) rather
than whatever the templates assumed. Peter guided Gemini to make these corrections,
in real time, during the session.

**Relationship to existing findings**: F1 (the `pip run` template bug, AT-01)
established that package-manager placeholder rendering is broken for at least
one package manager. This is a **second, independent axis of the same defect
class**: command-invocation assumptions baked into templates that don't account
for platform-specific venv layouts (`Scripts/` on Windows vs. `bin/` on
macOS/Linux) or, worse, that hardcode a path prefix that assumes a specific venv
tool or location entirely.

**Root cause (hypothesis, needs AT-01 confirmation)**: the templates likely
assume a fixed relative invocation path rather than either (a) resolving the
active interpreter via `sys.executable` / `shutil.which()` at hook-run time, or
(b) rendering a platform-appropriate prefix at install time the way the
`pm_run_prefix` logic already does for `config.yaml`.

**Severity**: High for adoption — this is not a rare edge case. macOS is a
majority platform for individual developers, the exact audience this harness
targets ("solo architect," "1-3 person team"). Every macOS user who isn't Peter
will hit this blind.

**Proposed remediation**:
- **Extend AT-01's rendering matrix with a second dimension.** The matrix
  should not just be {pip, poetry, pipenv, npm...} × template lines — it needs
  {Windows, macOS, Linux} × {venv, poetry, pipenv, conda, none} crossed against
  every template that invokes a script or tool. Two escaped bugs (F1 and this
  one) from the same untested-dimension pattern — no macOS case and no venv-path
  case existed in the e2e matrix — is strong evidence the matrix itself, not
  just the templates, needs to widen.
- Prefer runtime resolution over install-time hardcoding where feasible:
  hooks that need "the active interpreter" should resolve it live
  (`sys.executable` from within a Python hook, or a small shell shim that
  checks for `.venv/bin/python` then `.venv/Scripts/python.exe` then falls back
  to `python3` / `python` on PATH) rather than baking one assumption into a
  template at install time. This is more robust to venvs being moved, renamed,
  or recreated after install — a design question for AT-01 to weigh explicitly.
- **Feeds AT-01** directly as an additional matrix dimension and design question.

---

## Finding 3 — Adversarial-review API key setup has no discoverable path

**Observation**: The user had no idea they needed to configure an API key for
the adversarial AI review gate to function. Peter had to manually prompt them to
ask their Gemini instance to set one up. Nothing in the installer flow, the
getting-started doc, or the tool's own error output (as experienced by the user)
surfaced this requirement proactively.

**Relationship to existing findings**: This intersects both AT-02 (pydantic /
provider dependency disposition — a missing key plausibly manifests as one of
the raw, confusing failures already catalogued under F2) and AT-08 (validator
dry-run design). It's a third instance of the same underlying pattern as
Findings 1 and 2: **a hard prerequisite that the harness assumes but never
checks or explains before the user hits a wall.**

**Severity**: High — without a working API key, the adversarial review gate is
either silently degraded (fail-open, giving a false sense of governance) or
crashes with a raw error the user can't interpret, depending on how F2's
disposition is ultimately resolved.

**Proposed remediation**:
- Add an explicit, interactive API-key setup step to the installer itself
  (or a documented, one-command follow-up: e.g. `python bootstrap/install.py
  --check-provider` or similar) that: (a) checks for an existing key via the
  expected environment variable or config path, (b) if absent, prints the exact
  provider-specific instructions (where to get a key, what environment variable
  or config field to set it in), and (c) offers to write a placeholder/example
  entry into the project's `.env.example` or equivalent so the requirement is
  visible in version control even if the actual key isn't.
- **Extend AT-08's validator dry-run** to explicitly test that a configured key
  is present AND reachable (a trivial API call, not just an env-var presence
  check) before reporting the harness "ready" — a key that's set but invalid
  (typo, expired, wrong provider) should fail the same dry-run that would catch
  F1–F3's install defects, for the same reason: "0 errors, 0 warnings" should
  mean the first commit will actually work, not just that files exist.
- **Feeds AT-02 and AT-08** as an additional precondition both should account for.

---

## Finding 4 (proposed new workstream) — No guided path from "vibe-coded prototype" to SDLC-compliant project

**Observation, and the most structurally significant of the session**: this user
arrived with something quite different from a "fresh empty project." They had
already vibe-coded a working prototype — a web front end, backend code, and a
database — through open-ended conversation with Gemini, with **no recorded
requirements, no architecture documentation, and no roadmap or backlog.** Peter
personally talked them through creating their first spec, by hand, in real time.

**Why this matters more than it first appears**: this is very likely the
*modal* real-world entry point for the harness, not the edge case. Someone who
already has disciplined requirements, an architecture doc, and a backlog before
they've written a line of code is someone who probably doesn't need convincing
to adopt a governance harness — they're already halfway to inventing one
themselves. The person who benefits *most* from adopting `ai-delivery-control` is
precisely the person who vibe-coded first and has no formal artifacts yet — and
the harness currently has no answer for them beyond "here's a human who happens
to already understand this stuff, sitting next to you."

**The gap in harness terms**: this is a *third* posture the harness doesn't yet
model, adjacent to but distinct from the brownfield `strict`/`ratchet`/`observe`
work (T1-G-18) and the greenfield/genesis-mode discussion from earlier in this
arc. Call it, provisionally, **retrofit mode**: a project with real, working
code but no governance artifacts at all. It's not brownfield in the T1-G-18
sense — there's no mature architecture to ratchet enforcement against, no
existing test suite, no prior spec history. It's not greenfield either — there's
already a codebase with real behavior, real data models, and real user-facing
surfaces that a fresh spec-first process would otherwise assume don't exist yet.

**What "gently guide someone through it" would need, concretely**:
1. **A detection step.** The installer or onboarding flow could ask (or infer
   from repo contents — existing non-trivial source files, a working `git log`
   with substantive commits, absence of any `docs/planning/` or `docs/architecture/`
   directory) whether this looks like a retrofit case, and branch its guidance
   accordingly rather than assuming either brownfield or greenfield.
2. **A reverse-engineering-first workflow**, not a spec-first one. The existing
   `/architect` or `/ba` workflows (per T1-L-02, T1-L-13) assume you write the
   spec *before* the code exists. A retrofit user needs the inverse: a guided
   session where the agent reads the existing code and *proposes* a first-draft
   architecture document and an initial backlog *from what's already there*,
   which the human then reviews and corrects — rather than starting from a
   blank spec template. This is closer to what Peter did by hand this session:
   look at what exists, extract the shape of it, write it down, then move
   forward spec-first from that point on.
3. **An explicit "baseline" artifact**, distinct from a spec: something like a
   `RETROFIT_BASELINE.md` capturing "this is what existed before governance
   started, as best as we can reconstruct it, on this date" — so the harness's
   traceability gate has something to point to for the pre-existing code
   without requiring (impossible, retroactive) formal specs for work already
   shipped. This is the retrofit-mode equivalent of a brownfield architectural
   boundary snapshot (which T1-B-12's CDR ledger already does for coupling) —
   the same pattern, applied one level up, to requirements and architecture
   rather than just coupling debt.
4. **A staged ratchet**, matching the existing posture vocabulary: `observe`
   from day one (behavioral rules on, nothing blocks), moving to `ratchet` once
   the baseline and first real spec exist, with the same explicit
   human-approved promotion already designed for brownfield/genesis.

**Sizing note — this is bigger than F1–F3**: those are defects with clear fixes.
This is a genuine new workflow requiring design, a new artifact type, and
probably a new guided session type. It does not belong in v1.4.9.1 or even
v1.4.10, and probably deserves its own spec rather than being folded into the
existing genesis-mode discussion — genesis mode is "how do gates behave for a
truly empty project," retrofit mode is "how does the harness retroactively
adopt an already-partially-built one," and conflating the two would produce a
confused spec serving neither well.

**[DECISION REQUIRED]**: whether retrofit mode becomes a named item on the
roadmap now (even if unscheduled — a placeholder with this write-up as its
seed) or waits for a second observed instance before being formalized. Given
the argument above that this may be the modal case rather than the edge case,
there's a reasonable argument for adding it to `FRAMEWORK_ROADMAP.md` as an
explicitly unscheduled, backlog-recorded item now, purely so the insight isn't
lost the way HIB-ENV-02-adjacent findings nearly were this week.

---

## Finding 5 — Stale venv Python silently downgrades enforcement tooling

**Observation**: The user's machine had two Python installations — a current 3.14
on the system path, and a 3.9 inside an existing `.venv` they hadn't touched in
some time. The installer detected and used the `.venv` without checking its
currency. Pip then resolved `black`/`ruff`/`mypy`/etc. to whichever older versions
still supported 3.9. Nothing failed or errored — the harness installed
"successfully" and reported clean. Recovery required manually asking Gemini to
upgrade the venv's Python, reinstall the harness, and update every dependency,
costing significant session time.

**Why this is worse than F1–F3**: those failed loudly. This failed silently — the
user would have no way to know their formatter, linter, and type checker were
years stale and enforcing a different rule set than the harness's config assumes,
until something that should have been caught wasn't, or a version-specific rule
simply didn't exist yet in the installed tool. A governance harness whose
enforcement tools are silently downlevel is a credibility problem as much as a
technical one.

**Root cause (hypothesis)**: the installer selects an existing `.venv` if present,
with no check of the venv's Python version against either (a) the system's
currently available interpreters, or (b) a minimum-version floor the harness
itself requires for its dependency set to resolve to current tool versions.

**Proposed remediation**:
- Extend AT-08's validator dry-run with a **Python currency check**: detect the
  venv's Python version, compare against the system's available interpreters
  (and/or a harness-declared minimum), and warn — loudly, before dependency
  install — if the venv is meaningfully behind. Offer to recreate the venv
  against a newer interpreter as part of the installer flow, rather than
  requiring the user to diagnose and fix it manually afterward.
- Separately, the validator's existing "0 errors, 0 warnings" success report
  should include resolved tool versions (`black --version`, `ruff --version`,
  etc.) so even without the proactive check, the information needed to notice
  staleness is visible rather than buried.
- **Feeds AT-08** as a third precondition class, alongside the
  wrong-install-target check (F-COLD-1) and the API-key reachability check
  (F-COLD-3): all three share the same shape — a silent prerequisite failure
  that "presence-only" validation can't see, but a slightly deeper dry-run
  check can.

---

## Summary — routing table

| Finding | Feeds | Type | Ready to ship now? |
|---|---|---|---|
| F-COLD-1: distribution model / wrong clone target | AT-08 (validator self-check) + docs | Doc fix + small installer check | Doc fix: yes, today. Installer check: needs AT-08 design. |
| F-COLD-2: macOS/venv path assumptions | AT-01 (extends matrix to platform × venv-tool axis) | Template/design fix | No — needs AT-01 analysis first (root cause hypothesis stated, not confirmed) |
| F-COLD-3: API key setup undiscoverable | AT-02 + AT-08 | Installer feature + validator extension | No — needs AT-02's disposition decision first |
| F-COLD-4: no retrofit-mode guidance | New workstream (proposed) | Design + new workflow + new artifact type | No — needs scoping decision, likely its own spec |
| F-COLD-5: stale venv Python silently downgrades enforcement | AT-08 (validator extension) | Validator dry-run feature | No — needs AT-08 design and analysis first |

**Immediate, no-analysis-needed action**: the "you are here" diagram/callout for
Finding 1 needs no design decision and no code change — it's a documentation
edit. This can ship independent of and ahead of v1.4.9.1 if desired.

**Recommended handling**: file F-COLD-1, F-COLD-2, F-COLD-3, and F-COLD-5 as
backlog items cross-referencing AT-01/AT-02/AT-08 as routed above (mechanical,
AT-00-style filing). Bring F-COLD-4 to Peter as a `[DECISION REQUIRED]` before
filing anything beyond this write-up — it's a scoping call, not a mechanical one.
