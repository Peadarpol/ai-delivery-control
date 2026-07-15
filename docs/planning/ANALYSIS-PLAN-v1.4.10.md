# ANALYSIS PLAN — First-Commit Defects (v1.4.9.1 / v1.4.10 split)

**Status**: DRAFT v2 — pending human approval
**Author**: Claude (adversarial review agent), on behalf of Peter Long
**Executing agent**: Gemini (analysis only — see Ground Rules)
**Feeds into**: `SPEC-v1.4.9.1-first-commit-hotfix.md` + inputs to the existing
v1.4.10 Governance Hardening milestone
**Baseline**: v1.4.9 (`3ecc771`, Release/v1.4.9)

---

## 0. Scope Reconciliation with FRAMEWORK_ROADMAP (v2 revision)

`FRAMEWORK_ROADMAP.md` already defines **v1.4.10 — Governance Hardening** (T1-K-12,
T1-K-13, T1-K-14+HIB-068, HIB-063, T1-L-20, HIB-ENV-02, T1-I-08, HIB-059, HIB-061),
assembled deliberately from the v1.4.9 incident cluster. This plan therefore does
NOT claim the v1.4.10 number for a defect release. Proposed shape (**[DECISION
REQUIRED — release shape]**):

- **v1.4.9.1 (hotfix, pre-demo critical path)**: F1, F2 (import relocation +
  doc correction; dependency disposition may be interim), F3, F5. All are
  root-cause-confirmed and need no new design vocabulary.
- **v1.4.10 (Governance Hardening, as planned)** absorbs:
  - F4 / AT-04 → **into T1-K-14's verdict taxonomy** (PASS / FAIL_OPEN /
    INCOMPLETE / SKIPPED-precondition must be ONE vocabulary, not two).
  - F2's infrastructure-failure-vs-verdict finding → T1-K-14 audit evidence.
  - F6 / AT-06 → coordinated `check_traceability.py` change set alongside
    T1-K-13 and HIB-061 (same file, one review).
  - AT-05's meta-governance finding (did the fence-strip deletion pass the
    gate?) → T1-K-14 audit evidence.
  - HIB-061 is partially discharged by this plan's fresh-project reproduction —
    AT-06 must fold its observations into that ticket.
- **v1.4.11 / v1.5 (installer & onboarding theme)**: F7 (lint policy), F8
  (validator dry-run), genesis mode spec. Parked together deliberately.

**Roadmap inconsistency to resolve regardless of shape**: T1-K-12 is BLOCKED on
T1-L-21, which is absent from the v1.4.10 planned list. Either add T1-L-21 to the
milestone or move T1-K-12 out. **[DECISION REQUIRED]**

Analysis tasks below are unchanged in content but their outputs now route to two
spec destinations per the split above; AT-09 is updated accordingly.

---

## 1. Purpose

An independent ground-up assessment (fresh empty pip-based project, harness installed
via `bootstrap/install.py`, first commit attempted) surfaced **six independent
first-commit failures plus one live runtime regression** in v1.4.9. This plan
enumerates the analysis Gemini must perform to (a) confirm root causes, (b) size blast
radius, (c) surface the decision points reserved for the human, and (d) produce the
evidence base from which the v1.4.10 specification will be written.

**Release acceptance sentence** (to be carried verbatim into the hotfix spec):
> A brand-new, empty, pip-based git repository with the harness installed and no
> optional dependencies present must complete its first commit successfully, or fail
> only for reasons the user can understand and act on.

## 2. Ground Rules (HARD STOP conditions)

1. **Analysis only.** No production code changes, no template changes, no fixes —
   however trivial they appear. Findings 1–7 below already have candidate fixes
   sketched; implementing them is out of scope until the spec is APPROVED.
2. Failing tests MAY be written where a task explicitly calls for them (test-first
   evidence). They must be committed skipped/xfail so the suite stays green.
3. All output artefacts go under `docs/planning/analysis/v1.4.10/` (create it).
4. Each analysis task commits under its assigned HIB/backlog ID (see AT-00).
   No `--no-trace` commits in this workstream.
5. Every completion claim must cite the file/line or command output that proves it
   (verification-before-completion applies to analysis too).
6. If any task uncovers a NEW defect not listed here, STOP that thread, record it in
   `docs/planning/analysis/v1.4.10/NEW-FINDINGS.md`, and continue other tasks.

## 3. Reproduction Baseline (context for all tasks)

Observed failure stack on first commit (fresh project, pip, no poetry, no pydantic):

| # | Failure | Layer |
|---|---------|-------|
| F1 | `pip run <cmd>` → `ERROR: unknown command "run"` across ~8 `language: system` hooks | Installer/template |
| F2 | `ai_review.py` → `ModuleNotFoundError: pydantic` — import-time crash, bypasses fail-open | Gate runtime |
| F3 | `architecture_checks.py` → `ModuleNotFoundError: harness_utils` | Hook wiring |
| F4 | Exception Standards hook targets `tests/quality/test_exception_standards.py` — absent on all non-GymBase projects | Template (GymBase leak) |
| F5 | `providers.raw_completion()` → `NameError: _strip_json_fences` (all three providers) — breaks `pm_scaffold.py`, `acceptance_check.py`, `rebuttal.py` | Runtime regression |
| F6 | Traceability gate rejects the root commit (no spec exists yet; `--no-trace` ergonomics confusing) | Gate design |
| F7 | black/ruff mutate framework-owned scripts (62 ruff findings in framework files); checksum drift risk | Template policy |
| F8 | `bootstrap/validate.py` reports "0 errors" immediately before F1–F6 manifest — presence checks, not runnability checks | Validator design |

---

## 4. Analysis Tasks

### AT-00 — Incident filing and ID allocation
**Objective**: Establish traceability anchors before any analysis commits.
**Method**:
- File HIB entries (next free IDs, cross-file ID discipline applies) for: F5
  (runtime regression, unambiguous), F1 and F2 (install-defect incidents), F3
  (dead-gate incident — pending AT-03 outcome may split into two HIBs).
- F4, F6, F7, F8 are design defects, not incidents: file as backlog items
  (T1 series) in `FRAMEWORK_BACKLOG.md`.
- Run `incident_to_eval.py` against the F5 HIB once AT-05 produces the failing test.
**Output**: HIB entries + backlog rows + an ID map table at the top of
`docs/planning/analysis/v1.4.10/ID-MAP.md`.
**Human decision**: none. Mechanical.

### AT-01 — Package-manager rendering matrix (F1)
**Objective**: Enumerate every placeholder rendering across templates and package
managers; confirm the defect class is confined to the pre-commit template.
**Method**:
- `grep -rn "PROJECT_PACKAGE_MANAGER" bootstrap/templates/ bootstrap/install.py`.
- Build a matrix: {pip, poetry, pipenv, npm, pnpm, yarn} × every template line using
  the placeholder → rendered command → valid? (Y/N, with the reason).
- Contrast with the `pm_run_prefix` logic at `bootstrap/install.py:374` (already
  correct for config.yaml rendering) — document why the two rendering paths diverged.
- Blast radius: does `bootstrap/upgrade.py` re-render `.pre-commit-config.yaml` on
  existing installs? Would a corrected template clobber user-edited hook entries?
  Check backup behaviour (`.pre-commit-config.yaml.bak` path in install.py).
**Output**: `AT-01-pm-rendering-matrix.md` with the matrix, divergence analysis,
and TWO candidate fix strategies costed: (a) installer passes computed
`pm_run_prefix` into the template (single source of truth), (b) conditional
template blocks. Include a recommendation with rationale.
**Human decision**: fix strategy (a) vs (b).

### AT-02 — Pydantic dependency disposition (F2)
**Objective**: Determine how load-bearing pydantic is to gate integrity, so the human
can choose between fallback, declared prerequisite, or vendored shim.
**Method**:
- Inventory every pydantic usage in `src/scripts/ai_review.py` (BaseModel, Field,
  ValidationError): list each model class, the fields validated, and what happens
  today when the reviewing model returns malformed JSON (trace the code path).
- Answer explicitly: *if verdict validation were reduced to hand-rolled dict/key
  checks, what specific rejection behaviours would be lost?* Enumerate them.
- Confirm the structural defect: the import sits above the fail-open try/except.
  Identify the exact guarded region boundaries and what a missing-dependency event
  SHOULD map to under existing semantics (fail-open for normal commits, fail-closed
  for high-risk patterns — cite `handle unavailability` path, ai_review.py ~line 790).
- Check whether any OTHER harness script imports pydantic (grep the tree).
- Reconcile with docs: list every place that claims "stdlib only"
  (`docs/getting-started.md`, README, wiki pages).
**Output**: `AT-02-pydantic-disposition.md` with the usage inventory, the three
options (fallback / prerequisite / vendored shim) costed against gate-integrity
impact, and the doc-correction list.
**Human decision**: option selection. (Note the structural import-placement fix is
required under ALL options and is not itself a decision.)

### AT-03 — Skill-script import pathing audit (F3)
**Objective**: Establish that F3 is a defect *class*, enumerate all instances, and
answer the uncomfortable question: has this gate ever run on GymBase?
**Method**:
- Inventory every script under `.agent/skills/**/scripts/` and `.agent/scripts/`
  that imports `harness_utils` or any module living in `src/scripts/` — list each
  with its import style and whether it self-bootstraps `sys.path` (compare the
  working pattern in `check_traceability.py`, which bootstraps for `audit_logger`).
- **GymBase forensics** (read-only, against the GymBase working copy): run the
  Clean Architecture Checks hook exactly as pre-commit invokes it. Does it execute,
  or has it been failing/erroring silently? Pull the last N pre-commit run results
  or reproduce manually. If the gate has been dead in production, record it as a
  separate HIB (silent dead gate — governance-relevant).
- Enumerate candidate path strategies: per-script sys.path bootstrap (existing
  precedent) / PYTHONPATH in hook entry / duplicate `harness_utils` into
  `.agent/scripts/`. Cost each against the upgrade path (checksummed files).
**Output**: `AT-03-import-pathing-audit.md` + possible new HIB.
**Human decision**: path strategy (recommendation expected: per-script bootstrap,
matching precedent).

### AT-04 — Precondition-dependent gate semantics (F4, feeds genesis mode)
**Objective**: Define the general rule for gates whose precondition artefact does not
exist, using Exception Standards as the concrete instance.
**Method**:
- Enumerate every hook in the pre-commit template whose precondition can be absent
  on a fresh project (exception-standards test file, architecture rules in
  config.yaml, pyproject.toml for bandit `-c`, dependency manifest for pip-audit,
  test suites for behaviour/regression pre-push hooks). Produce the precondition
  table: hook → precondition → current behaviour when absent → observed exit code.
- Draft the semantic options: hard fail (current) / silent skip / **skip-with-advisory
  + audit event** (expected recommendation — aligns with fail-closed classification
  audit item and GATE_SKIPPED precedent from v1.4.5).
- Design sketch only (no code): does the precondition check live in a wrapper per
  hook, or a shared `gate_preflight` helper? Note reuse by the future genesis-mode
  spec so v1.4.10 doesn't paint v1.5 into a corner.
**Output**: `AT-04-gate-precondition-semantics.md` with the precondition table and a
one-page semantic rule proposal.
**Human decision**: adopt skip-with-advisory as the standing rule? (This is a
governance-policy decision, not an implementation detail.)

### AT-05 — `_strip_json_fences` regression forensics (F5)
**Objective**: Root-cause the regression, close the test gap that let it ship, and
produce the failing test that will anchor the fix.
**Method**:
- `git log -S "_strip_json_fences" --oneline --all` — identify where the definition
  lived, which commit/refactor removed it (hypothesis: v1.4.6 `ai_review.py`
  decomposition), and whether the removal was flagged by any gate at the time.
  If the removing commit PASSED the adversarial review gate, record what the gate
  saw and why the deletion of a referenced symbol wasn't caught — this is
  meta-governance evidence.
- Confirm the return contract expected by all three call sites
  (`providers.py` AnthropicProvider/OpenAIProvider/OllamaProvider `raw_completion`)
  and by the three consumers (`pm_scaffold.py`, `acceptance_check.py`,
  `rebuttal.py`) — is fence-stripping the only transformation, or was there trailing
  behaviour (whitespace, partial-fence tolerance)? Recover the original function
  body from git history verbatim.
- Test-gap audit: read `tests/test_providers.py` and `tests/unit/*` — document the
  mocking level that masked the method body. Write the failing test: stubbed HTTP
  layer, real `raw_completion` body, fenced-JSON response → assert stripped output.
  Commit as xfail with the F5 HIB ID.
- Run `incident_to_eval.py` to generate the regression eval from the HIB.
**Output**: `AT-05-fence-strip-forensics.md`, recovered function body (quoted from
history, not reinstated), xfail test, regression eval entry.
**Human decision**: none — restoration is mechanical once evidence is assembled.

### AT-06 — Root-commit traceability exemption (F6)
**Objective**: Confirm detection mechanics and surface the governance decision.
**Method**:
- Verify detection: behaviour of `git rev-parse HEAD^` / commit-count probes in a
  repo with zero commits, at the commit-msg hook stage (the commit object does not
  yet exist — confirm what IS observable at that stage). Document the reliable
  root-commit predicate.
- Map the exemption against all three `outer_loop` modes. Draft the argument matrix
  for allowing the exemption in `contractual` mode (every project has a first
  commit) vs. requiring a pre-existing spec even then.
- `--no-trace` ergonomics: catalogue confusion vectors (reads as a git flag; resides
  inside the message; 10-char reason minimum invisible until failure). Propose
  alternatives WITHOUT recommending a grammar change in v1.4.10 — note migration
  implications for anything parsing commit history, and park it as a candidate
  backlog item.
**Output**: `AT-06-root-commit-exemption.md` + test cases list for the gate's suite.
**Human decision**: does the exemption apply in `contractual` mode? Ergonomics
change deferred to backlog: yes/no.

### AT-07 — Framework-file lint policy (F7)
**Objective**: Separate policy (are framework-owned files subject to project
formatters?) from hygiene (the 62 findings themselves).
**Method**:
- Enumerate the exact file set installed by `copy_framework_files()` (install.py
  ~219–346) → these are the checksum-verified, framework-owned paths.
- Confirm the mutation risk concretely: which of those files did black/ruff modify
  in the reproduction run, and what would `harness_health.py` / checksum
  verification report afterwards?
- Draft exclude patterns for black/ruff/mypy in the pre-commit template covering
  `.agent/` and framework scripts under `[PROJECT_SRC_PATH]/scripts/`; verify the
  patterns cannot shadow plausible user code paths (e.g., a user's own
  `src/scripts/` utilities — flag this collision honestly).
- Upstream hygiene: run ruff against the harness repo's own `src/` and `.agent/`
  with the TEMPLATE's rule set (not the harness repo's), diff the two rule sets,
  and document the inconsistency. Classify the 62 findings: real bugs (the F821s
  are F5), style noise, auto-fixable. Fixing them is v1.4.10 work only if
  classified as bugs; style-only items go to backlog.
**Output**: `AT-07-lint-policy.md` with exclude-pattern proposal, rule-set diff,
findings classification.
**Human decision**: adopt "framework files exempt from project formatters" as
policy (with upstream hygiene as the compensating control)?

### AT-08 — Validator dry-run design study (F8, mini-spec input)
**Objective**: Produce the design study for upgrading `bootstrap/validate.py` from
presence-checking to runnability-checking. This is the systemic fix and gets the
deepest analysis.
**Method**:
- Side-effect audit: determine a guaranteed-clean sequence for exercising hooks
  without creating commit objects or firing post-commit hooks. Candidates to
  evaluate: `pre-commit run --all-files` on a scratch stage; `pre-commit run
  --hook-stage commit-msg` with a synthetic message file; full `git commit` in a
  throwaway clone. For each: what executes, what mutates, what's restorable.
- Pass-criterion taxonomy: define the distinction between *infrastructure error*
  (hook could not execute: missing interpreter, missing module, unknown command —
  install defect, validator FAILS) and *content finding* (hook ran and rejected the
  content — validator PASSES). Enumerate exit-code/output heuristics per hook to
  classify reliably.
- Runtime budget: measure first-run pre-commit environment installation cost;
  propose default-on vs opt-out flag with warning.
- e2e matrix feasibility: cost a CI matrix {pip, poetry} × {bare venv, full deps}
  against current `tests/e2e/run_e2e_verification.py`. Identify the minimum matrix
  that would have caught F1 and F2 (hypothesis: pip × bare venv alone catches both).
**Output**: `AT-08-validator-dryrun-design.md` — this document becomes a section of
the v1.4.10 spec (or is split to v1.5 if runtime findings make it heavy; present
the evidence either way).
**Human decision**: v1.4.10 scope inclusion vs deferral to v1.5; default-on vs
opt-out.

### AT-09 — Consolidation and spec skeleton (two destinations)
**Objective**: Assemble AT-01…AT-08 outputs per the §0 release split.
**Method**:
- Produce `SPEC-v1.4.9.1-first-commit-hotfix.md` in DRAFT covering F1, F2
  (structural fix + interim dependency disposition), F3, F5: the acceptance
  sentence (§1) as umbrella Gherkin scenario, one section per finding referencing
  its analysis artefact, `[DECISION REQUIRED]` blocks, and the AT-05 xfail tests
  as the test plan anchor.
- Produce `docs/planning/analysis/v1.4.10/GOVERNANCE-HARDENING-INPUTS.md`
  packaging the AT-04 precondition taxonomy, AT-05 meta-governance evidence,
  AT-06 root-commit analysis, and the fresh-project observations discharging
  part of HIB-061 — addressed to the existing v1.4.10 milestone items
  (T1-K-13, T1-K-14, HIB-061), NOT as a competing spec.
- Update `FRAMEWORK_ROADMAP.md` DRAFT edit: insert v1.4.9.1 milestone entry;
  record the T1-K-12/T1-L-21 dependency resolution once decided.
- Explicitly list what is parked with pointers: genesis mode + F7 + F8
  (v1.4.11/v1.5 installer & onboarding theme), `--no-trace` grammar change
  (backlog), enforcement postures implementation (T1-G-18, unchanged),
  style-only lint findings (backlog).
**Output**: DRAFT hotfix spec + governance-hardening input package + roadmap edit.
**Human decision**: all `[DECISION REQUIRED]` blocks, then spec APPROVED status.

---

## 5. Sequencing and Effort

- **Parallel-safe**: AT-01, AT-02, AT-03, AT-05, AT-06, AT-07 are independent.
- **Ordered**: AT-00 first (IDs); AT-04 benefits from AT-01's hook inventory;
  AT-08 last of the analyses (uses reproduction infrastructure insights from all);
  AT-09 strictly last.
- **Pre-demo critical path** (guest session): AT-01, AT-02, AT-05 analyses are
  sufficient to write targeted hotfix notes even before the full spec — flag to
  human when those three are complete.
- Estimated effort: AT-05 and AT-08 are the deep ones; the rest are 1–2 focused
  sessions each.

## 6. Exit Criteria

This plan is complete when:
1. Every AT output artefact exists under `docs/planning/analysis/v1.4.10/` with
   evidence citations.
2. All HIBs/backlog IDs filed; F5 regression eval generated.
3. The DRAFT spec exists with all decision points enumerated and no code changed.
4. Claude has adversarially reviewed the spec; Peter has resolved decisions and
   set Status: APPROVED. Implementation begins only after that gate.
