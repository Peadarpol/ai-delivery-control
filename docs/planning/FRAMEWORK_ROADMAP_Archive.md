# AI Delivery Control — Framework Roadmap Archive

> **Purpose**: This file holds the full, verbatim historical record for milestones that have
> shipped and are no longer actively referenced in day-to-day work. It exists to keep
> `FRAMEWORK_ROADMAP.md` smaller and more current-focused for agent context budgets, without
> discarding any historical detail. Nothing here has been summarised or reworded — content is
> moved, not compressed, per the H-09 principle (dated historical records must not be rewritten).
>
> **Scope of this file**: v1.0.0 through v1.2.0.1 (Foundation through Harness Gitignore
> Enforcements). For v1.3.0 onward, see `FRAMEWORK_ROADMAP.md`.
>
> *Archived 2026-07-24, split from `FRAMEWORK_ROADMAP.md`.*

---

### v1.0.0 — Foundation ✅ SHIPPED (2026-05-21)

**Goal**: Extract the harness from its host project into a standalone installable framework.

**Delivered**:
- Bootstrap install script — under 10 minutes from zero to working harness
- Environment validation script
- Config-driven architecture checks
- Two-layer review context (universal + project)
- Universal + stack-pack skills (22 universal, python-fastapi stack pack)
- Tool supplement generation (CLAUDE.md, GEMINI.md, .cursorrules as thin shims)
- Pre-commit AI adversarial review gate with pre-flight shortcut, diff-aware routing, typed ReviewVerdict, policy notes output
- PageRank repository map injected into review context
- ADR annotation convention and compiled wiki layer (Gemma4 local)
- Dream phase self-improvement loop (session pattern detection, skill proposals, contradiction detection)
- Session lifecycle hooks (outcome inference, startup orientation, retention policy)
- Repository identity guard (P-14)
- Full documentation suite (getting started, configuration reference, customisation guide, AISDLC bootloader)

**Reference implementation**: GymBase (gym management SaaS, currently private). The framework was developed and validated over 6 months of active feature delivery. A public worked example is planned for v1.1.0.

---

### v1.1.0 — Demonstrably Working ✅ SHIPPED (2026-05-23)

**Goal**: Show the framework working in practice. The headline is the self-improvement loop producing real proposals from real sessions — not hygiene items. A developer landing on this project should be able to see the temporal moat in action, understand what makes the gate adversarial, and run the framework without an Anthropic account.

**Success criteria**:
- A public worked example shows a complete commit cycle: diff → routing decision → verdict → policy notes
- Dream phase outputs from real sessions are documented and visible
- The gate works with any LLM provider (Anthropic, OpenAI, Ollama)
- Repository signals a maintained project, not a personal workspace
- Convention vs enforcement is explicitly documented

**Planned items**:

| ID | Item | Category |
|----|------|----------|
| S0-01 | Remove `scratch/` directory | Repository hygiene |
| S0-02 | Narrow README positioning claim to match actual scope | Documentation |
| S0-03 | Add `CONTRIBUTING.md` | Community |
| S0-04 | Add GitHub issue templates | Community |
| S0-05 | Cut v1.0.0 GitHub release with release notes | Release |
| S0-06 | Add CI badge to README | Social proof |
| S0-07 | Document convention vs enforcement explicitly in README | Documentation | ✅ |
| S0-08 | Surface 2-3 representative skills in docs | Documentation |
| S0-09 | Add worked example: complete diff → routing → verdict cycle | Documentation |
| S0-10 | Publish dream phase example: real proposals from real sessions | Documentation |
| S0-11 | Add "What it prevents" section to README | Documentation | ✅ |
| S0-12 | Fix validate.py legacy filename warning | Validation | ✅ |
| S0-20 | Competitive positioning statement — add to README and docs | Documentation | |
| S0-24 | De-GymBase-ify functional code before public promotion | General framework decoupling | |
| T1-E-02 | LLMProvider ABC (AnthropicProvider, OpenAIProvider, OllamaProvider) | Provider portability | ✅ |

> **S0-24 scope note (identified 2026-06-02)**: Three targeted code changes —
> (a) extract `SYSTEM_PROMPT` in `ai_review.py` to a config-loaded template with
> project-neutral defaults (GymBase patterns move to `review_context_project.md`);
> (b) move `DOMAIN_REGISTRY` in `wiki_compile.py` from hardcoded Python to
> `.agent/config.yaml` so projects without GymBase ADR files skip gracefully;
> (c) move hardcoded directory paths in `build_route_decision()` to config.
> Must complete before S0-23 (README pre-Reddit additions) goes live.
| T1-L-06 | Explicit production scope statement in README and docs | Documentation | ✅ |
| T1-L-08 | High-risk commit classification for fail-open behaviour | Gate hardening | ✅ |
| T1-L-09 | Framework self-test suite (60 tests across 6 modules) | Testing | ✅ |
| BUG-01 | commit-msg hook not installed by bootstrap — already present since initial commit | Gate wiring | ✅ |
| BUG-02 | validate.py does not check commit-msg hook — already present | Validation | ✅ |
| BUG-03 | Gate reads empty diff on amend at commit-msg stage — ORIG_HEAD guard + empty tree fallback | Gate fix | ✅ |
| BUG-04 | PASS/PASS_FAST verdicts not written to audit log | Logging | ✅ |
| BUG-05 | ADR domain names not mapping to capability names | Routing fix | ✅ |
| BUG-06 | Gate calibration too aggressive — proportionate calibration + false-positive guard | Gate calibration | ✅ |
| T1-M-01 | Agent operations guide | Documentation | — (human-authored, deferred) |
| T1-M-02 | Spec writing guide | Documentation | — (human-authored, deferred) |
| T1-M-05 | Stack coverage acknowledgment | Documentation | ✅ |

**Note on T1-E-02 placement**: Provider agnosticism is moved from v1.3.0 to v1.1.0. Anthropic vendor lock-in is an immediate evaluation objection from any engineering team with data residency requirements. It should not remain a v1.3.0 problem for a framework positioning itself at governed delivery in constrained environments.

---

### v1.1.5 — Beta Ready ✅ SHIPPED (2026-05-29)

**Goal**: Ship a version that external developers can install, use, and upgrade
without hand-holding — while closing the two sharpest edges the framework
currently has (token surprise, gate false positives). Sits between v1.1.0 and
the Outer Loop milestone; does not pull forward any v1.2.0 outer loop content.

**The gap this addresses**: v1.1.0 delivered a working framework but not yet
an installable product. Beta testers need a clean upgrade path, a governed token
ceiling, and a gate that does not frustrate them with false positives before they
have built any trust in it. A beta tester who hits a $50 session overage or
cannot upgrade without manual file merging will not continue.

**Success criteria**:
- A developer with no prior framework knowledge can install, run the onboarding
  workflow, and make a governed commit in under 30 minutes
- A v1.1.0 installation upgrades to v1.1.5 without manual file merging
  (`upgrade.py --dry-run` completes cleanly)
- A session approaching the token budget ceiling receives a WARN before context
  exhaustion
- A gate FAIL on a false positive has a governed resolution path that does not
  require `SKIP_AI_REVIEW=1`
- Token consumption per session is visible in `session_ledger` by category

---

#### Theme 1 — Beta Installer Experience

| ID | Item | Effort | Status |
|----|------|--------|--------|
| HIB-006 | `bootstrap/upgrade.py` | Medium | ✅ |
| T1-B-03 | Onboarding workflow | Low | ✅ |
| S0-03 | `CONTRIBUTING.md` | Low | ✅ |
| S0-04 | GitHub issue templates | Low | ✅ |
| S0-05 | Cut v1.1.5 GitHub release + tag | Low | ✅ |
| S0-06 | CI badge | Low | ✅ |
| S0-08 | Surface representative skills in docs | Low | ✅ |
| S0-09 | Worked example (diff → routing → verdict cycle) | Low | ✅ |

Human-authored in parallel (no agent session required): T1-M-01 (agent
operations guide), T1-M-02 (spec writing guide), T1-M-04 (team usage guide).

S0-05 must be cut before any beta invitations are sent.

---

#### Theme 2 — Token Measurement & Calibration

| ID | Item | Effort | Status |
|----|------|--------|--------|
| T1-I-02 | Token budget tracking per session | Low | ✅ |
| T1-I-07 | Session token budget with WARN/HALT | Low | ✅ (2026-06-02 pre-sprint) — wiring of ai_review.py → session.json completed 2026-06-02 pre-sprint |
| T1-M-06 | Context compaction template | Low | ✅ |
| T1-G-08 | Diff size review strategy | Low | ✅ |

> **T1-I-07 resolved (2026-06-02 pre-sprint)**: The HALT mechanism, file format,
> and threshold logic existed at v1.1.5 delivery. The missing wiring —
> `ai_review.py` incrementing the session token counter after each review call —
> was completed as a pre-Sprint-1 item. The 80% WARN and 100% HALT thresholds
> now fire correctly during sessions that include review gate calls.

---

#### Theme 3 — Gate Trust & Calibration

| ID | Item | Effort | Status |
|----|------|--------|--------|
| T1-H-08 | Branch-isolated model roster in compiled wiki | Low | ✅ |
| T1-G-07 | Structured SKIP_REASON enforcement | Low | ✅ |
| T1-L-10 | False positive → eval regression pipeline | Low | ✅ |
| T1-G-06 | Structured rebuttal protocol | Medium | ✅ |

---

#### Recommended Sequencing

**Completed**: All items shipped in v1.1.5.2 patch release.

---

### v1.2.0 — Outer Loop ✅ SHIPPED (2026-05-31)

**Goal**: Govern the full delivery lifecycle from requirement to commit, not just from commit to repository.

**The gap this addresses**: The framework currently picks up governance at "an agent starts working." Everything before that — how a business need becomes a requirement, how a requirement becomes a spec good enough to build against — is ungoverned. A perfectly governed commit can implement the wrong thing. This milestone closes that gap.

**The deeper challenge**: The value of the outer loop is not in checking whether required fields are present in a spec file. It is in the institutional knowledge encoded in the `/business-analyst` and `/project-manager` workflows — what makes a requirement specific enough for an agent to act on, what acceptance criteria look like for AI-assisted delivery, how to scope work to avoid context window collapse mid-session. That knowledge is what the workflows need to capture.

**Success criteria**:
- A feature cannot start without an approved spec
- Every commit references the requirement it implements
- An acceptance gate checks intent alignment, not just code correctness
- The `/business-analyst` and `/project-manager` workflows encode actionable institutional knowledge, not just field validation

**Planned items**:

| ID | Item | Description |
|----|------|-------------|
| T1-L-01 | Spec quality gate | Before `/feature-implementation` begins, SPEC-XXX.md must exist and pass quality checks: acceptance criteria present, out-of-scope stated, architectural constraints identified, status APPROVED. Gate refuses to start without an approved spec. *Note: description enhanced with CodeRabbit two-tier check.* | ✅ |
| T1-L-02 | `/business-analyst` workflow | Full state-machine workflow: requirement intake → user story extraction → BDD scenarios → spec drafting → acceptance criteria → traceability matrix → human approval gate. Agent drafts; human approves. *Note: description enhanced with CodeRabbit Phase 0 intake, assumptions, and decisions_log feed.* Agent drafts; human approves. Scope: what to build and why. Effort estimation is T1-L-03's responsibility. | ✅ |
| T1-L-03 | `/project-manager` workflow | How an approved SPEC becomes a prioritised backlog item with effort estimate and dependencies. Sprint planning and dependency resolution. Receives an approved SPEC-XXX.md from T1-L-02. Owns effort estimates, task breakdown, dependency ordering, and sprint assignment. |
| T1-L-04 | Requirement → commit traceability | Pre-commit check: non-trivial commits must reference a requirement ID. Closes the spec-to-code chain. `--no-trace` flag for infrastructure commits with reason logged. |
| T1-L-05 | Acceptance gate | Second AI review call with the spec as context, checking intent alignment not just code correctness. Produces `AcceptanceVerdict`: SATISFIED / PARTIAL / DIVERGED. Runs once per feature branch before PR. |
| T1-L-07 | Incident → backlog pipeline | `incident_to_backlog.py`: structured incident entry with root cause, affected commit SHA, which gate should have caught it, and proposed guard. Closes the production feedback loop. |
| T1-M-03 | Mid-session observability | Lightweight session health check: duration, tool call count, context load estimate, warning patterns. Diagnostic tool for when something feels off mid-session. |

---

### v1.2.0.1 — Harness Gitignore Enforcements ✅ SHIPPED (2026-05-31)

**Goal**: Patch release resolving BUG-10 — bootstrap installations were not adding the required `.gitignore` block for operational state files, causing pre-commit conflict loops on fresh installs.

**The gap this addresses**: On every fresh install and upgrade, the harness creates files in `.agent/state/` that must not be committed (`session.json`, `HALT`, `.lock` files, `config.yaml.migration_backup`, the compiled wiki). Without the `.gitignore` block, these files appear as untracked changes. Developers staging them — inadvertently or deliberately — hit a pre-commit hook that rejects the commit, creating a conflict loop with no clear exit. Beta testers encounter this on their first governed commit.

**Delivered**:
- `bootstrap/install.py` — `update_gitignore()` appends the operational state block to the target project's `.gitignore` on every fresh install (idempotent; block is only appended if absent)
- `bootstrap/migrations/v1_2_0_to_v1_2_0_1.py` — migration module for existing v1.2.0 installations; safe header-anchored downgrade removes only the harness block
- `bootstrap/validate.py` — `validate_gitignored_states()` hardened: HALT absent from `.gitignore` → ERROR; `session.json` absent → WARN (not ERROR); `harness_events.jsonl` excluded (must be committed — it is the audit trail)
- `harness_version.txt`, `upgrade.py`, `downgrade.py` — version targets bumped to `1.2.0.1`
- Full test coverage: 184 tests pass (unit + integration)

| ID | Item | Category | Status |
|----|------|----------|--------|
| BUG-10 | Bootstrap does not write `.gitignore` block — pre-commit conflict loop on fresh installs | Install hardening | ✅ |

---

*End of archived record (v1.0.0 – v1.2.0.1). Continued in `FRAMEWORK_ROADMAP.md` from v1.3.0 onward.*
