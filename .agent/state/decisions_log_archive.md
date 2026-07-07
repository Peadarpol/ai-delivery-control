# Decisions Log Archive

## Session 2 (Outer Loop)
- **T1-L-12**: Adopted fail-open posture for Pass 2 JSON parsing to ensure spec grader degradation is graceful.
- **T1-L-13**: Evaluated soft-check for ADR annotations; `check_adr_decision_blocks` warns but doesn't block.
- **T1-L-14**: Changed `run_pass1` return type to explicit `Pass1Result` dataclass instead of tuple for better maintainability and extensibility.

## Session 3 (Security & Hardening)
- **T1-K-05a**: Implemented _safe_git_env() as a standalone utility in harness_utils.py rather than patching os.environ globally, ensuring side-effect-free execution for subprocesses in git hooks.
- **T1-K-02 & T1-K-02a**: Documented the quarantine pattern in docs/security/attack-surface-review.md and registered T1-K-07 finding as deferred rather than scope-creeping the v1.4.1 milestone.
- **Verification Protocol**: Adopted strict physical validation for git hooks using temporary .pre-commit-config.yaml scaffolding to prove _safe_git_env() correctly prevents stripped-env crashes on actual commits.

## 2026-06-14: Re-tiered T1-K-07 (Quarantine structural bypass mitigation) from High to Medium
- **Decision**: Formally re-tiered the backlog item T1-K-07 from High to Medium severity.
- **Context**: T1-K-07 addresses validation bypasses on local agent state files (such as dream proposals). An attacker who can write to `.agent/state/` already has a highly privileged position, and the bypass is a defense-in-depth issue rather than a live correctness hole in code delivery enforcement like HIB-055.
- **Consequence**: Ensures backlog prioritization accurately reflects security exposure and correctness enforcement urgency.

## 2026-05-21: Implemented Repository Identity Guard (P-14)
- **Decision**: Added a mandatory `.agent/scripts/check_repo.py` script and integrated it into session startup (Step 0) and the git hooks (`pre-commit` and `pre-push`).
- **Context**: Working across both framework and multiple client repos simultaneously introduces a risk of making accidental commits to the wrong project repository.
- **Consequence**: Pre-commit and pre-push hooks block accidental git operations in the wrong project directory, while `install.py` dynamically customizes the expected repo name for target installations, verified by `validate.py`.

## 2026-05-21: Reordered replacements in template rendering
- **Decision**: Run `extra_replacements` before standard `replacements` in `Installer.render_template`.
- **Context**: Prevent `[PROJECT_NAME_PLACEHOLDER]` key collision where base replacements converted the template key to `# project-name` before the custom framework YAML block replacement could match.
- **Consequence**: Templating behaves robustly and injects version/repo metadata correctly into `config.yaml`.

## 2026-05-21: Config-driven Architecture Checks (T1-A-04)
- **Decision**: Shifted all hardcoded static analysis rules and Clean Architecture invariants from `architecture_checks.py` to declarative blocks in `.agent/config.yaml`.
- **Context**: Portability requires the harness to run on any project (including Node, Go, or Python) without framework code changes to enforce specific architecture boundaries.
- **Consequence**: Custom projects can configure layers, forbidden imports, coupling limits, forbidden regexes, and aggregates. Zero-dependency custom YAML parser handles systems without PyYAML. Absent configurations gracefully bypass checks with an informative skipped state.

## 2026-05-21: Two-layer review_context.md Split (T1-A-05)
- **Decision**: Split the review context into `review_context_universal.md` (framework-owned, generic, overwritten on upgrades) and `review_context_project.md` (developer-maintained, scaffolded on install).
- **Context**: Porting GymBase's specific Unit of Work and multi-tenancy rules directly into general installation templates caused irrelevant and misleading rules to show up in clean projects.
- **Consequence**: Universal standard invariants (secrets, test coverage, repository layer bypass) are enforced globally across all installations. Developers get a clean, generic project template to add their own custom invariants over time, never overwritten on upgrade. Gating logic concatenates project rules after universal rules, and fails-closed if universal guidelines are missing.

## 2026-05-21: Universal + Stack-Pack Skills (T1-A-06)
- **Decision**: Restructured `.agent/skills/` under framework repository into `universal/` and `stack-packs/` subdirectories, and upgraded the installer to copy them flat into the target project using a non-destructive merge copier.
- **Context**: Flat skill sets are highly portable, but technology-specific guidelines (e.g. FastAPI route structures vs. Express controller boundaries) should only be installed when relevant, and re-running the installer on established projects should never destroy custom developer edits or skills.
- **Consequence**: Universal skills are installed globally across all projects. FastAPI or Express-specific guidelines are automatically detected and layered flat directly alongside them, preserving compatibilities with AST routing tools. The merge copier records target skills already present before executing copies, ensuring developer modifications and custom skills are fully preserved on upgrade/re-run scenarios.

## 2026-05-23: Two-layer ADR Domain → Capability Mapping (BUG-05)
- **Decision**: Implemented a two-layer mapping architecture for ADR domains: universal seeds in the framework and project-specific mappings in `.agent/config.yaml`.
- **Context**: Different clients and repositories (like GymBase) define distinct ADR names and structures, making a hardcoded global map brittle and polluting the clean framework repository with client-specific definitions.
- **Consequence**: Universal seeds support out-of-the-box generic concepts (clean architecture, transaction control, isolation), while custom project-specific domains are dynamically parsed from `.agent/config.yaml` and merged at runtime. Normalization ensures mixed-case lookups are completely robust, and project overrides cleanly resolve conflicts.

## 2026-05-23: High-Risk Commit Classification & Fail-Closed Enforcement (T1-L-08)
- **Decision**: Added a dedicated risk classification system using `fnmatch` to match paths, filenames, and ADR domains against hardcoded and project-defined patterns. High-risk commits are configured to fail closed (exit code 1) instead of failing open when the LLM provider is unavailable.
- **Context**: Uniformly failing open when the API is unavailable allows high-risk changes (e.g. database schema migrations, authorization controls, security patches) to bypass the gate silently.
- **Consequence**: Bypassing a high-risk commit using `SKIP_AI_REVIEW=1` requires a documented `SKIP_REASON` env var which is logged as `high_risk_gate_override` to the event trail; otherwise, a warning is printed. High-risk commits are successfully blocked when the gate is unavailable.

## 2026-05-25: Shifted to Role-Based Model Tiering (Budget vs Review)
- **Decision**: Transitioned configuration and token ratio namespaces from topology-specific names ("cloud" and "local") to role-based names ("budget" and "review") under `model_routing` inside `config.yaml`.
- **Context**: Tying routing keys to physical topology constraints presupposed local hosting (Ollama) for the low-cost tier, making cloud-hosted low-cost models (like Claude Haiku or GPT-4o-mini) secondary options.
- **Consequence**: Delivers complete topology independence, allowing developers to route classification and compilation tasks to cheap cloud APIs or local models interchangeably.

## 2026-05-25: Multi-Vector Structured Bypass with Wizard Continuation
- **Decision**: Structured high-risk bypasses execute in B → C → A order at runtime, where Vector C (Interactive TTY Wizard) immediately writes `.skip-ai-reason.json` and continues straight into Vector A (validation, logging, and auto-deletion) without exiting the process. Non-TTY environments safely fail-closed.
- **Context**: Standard bypasses using plain-text are fragile and uninspectable, while prompting developers to write files manually introduces friction that leads to workflow circumvention.
- **Consequence**: Developer friction is minimized through interactive auto-scaffolding, while immediate auto-deletion of the rationale file prevents accidental stale bypass reuse.

## 2026-05-25: Pure Static AST ORM Roster Compiler Sidecar
- **Decision**: Created a shared static AST model compiler `roster_builder.py` that processes model layouts at install/compile time and caches them, bypassing all LLM interaction.
- **Context**: Checking branch-isolation compliance dynamically produced false positives on queries joining branch-isolated models, while routing database inspection to local LLMs introduced latency and cost.
- **Consequence**: Compilation runs statically in <50ms, allowing `ai_review.py` to suppress false-positive join query failures using verified roster sidecar metadata.

## 2026-05-26: Componentized Bidirectional Upgrade & Downgrade Manager
- **Decision**: Developed a highly componentized and isolated upgrade/downgrade system consisting of `manifest.py` (file registry), `migration_base.py` (runtime @runtime_checkable MigrationProtocol contract), `checksums.py` (CRLF-normalized digest registry), `upgrade.py` (atomic upgrade CLI tool), `downgrade.py` (reversion CLI tool), and isolated config migration step modules.
- **Context**: Portability and system safety dictate that framework file registry, version registries, and migration steps remain logically detached from CLI runners. Upgrades must be fully atomic to prevent corruptions during failures, and downgrades must cleanly revert custom modifications.
- **Consequence**: Delivers robust dry-runs, colorized ANSI unified diffs, auto-exits, and timestamped backups. A failure mid-upgrade automatically triggers a complete rollback restore of the original system files (including `.gitignore`).

## 2026-05-26: Automated Diagnostic Onboarding Assistant
- **Decision**: Scaffolded a beautiful first-session onboarding workflow `.agent/workflows/onboarding.md` coupled with a zero-dependency diagnostic onboarding runner `.agent/scripts/onboarding.py`.
- **Context**: Helping developers get up to speed with process configurations, gating tests, reachability checks, and git hooks wiring needs to be smooth and wows-at-first-glance.
- **Consequence**: Automates reachability checks across Ollama/localhost vs cloud models, performs local test suite execution, checks git hook status, and automatically outputs a dated `onboarding_baseline_{YYYY-MM-DD}.md` snapshot for future debugging and regression verification.

## 2026-05-27: Hardened Token Budget Gating & Enforcement (Phase 3)
- **Decision**: Implemented rolling budget tracking summing regular, reasoning, and cache read tokens, coupled with atomic structured JSON HALT writes, interactive TTY/env bypasses, and 80%/100% Warn/Halt warnings.
- **Context**: Invisible reasoning and cache-read tokens were previously untracked, causing budget undercounting, while missing pre-flight priority logic blocked documentation changes in budget-exhausted sessions.
- **Consequence**: Delivers robust spent tracking with clear, high-visibility recovery warnings and complete bypass safety, verified by comprehensive unit and E2E verification suites.

## 2026-05-27: Dynamic Project Root Resolution & Robust Pathing
- **Decision**: Upgraded project root resolution to first check `Path.cwd()` for `.agent` presence before resorting to git/parent directory traversals.
- **Context**: In E2E tests, scripts are run inside a nested project directory (`test_project`) that is not a separate git repository. Using git-based toplevel resolution resolved to the parent repository root, breaking path and config loading.
- **Consequence**: PageRank, ADR, and config loading are dynamically and robustly anchored to the active workspace toplevel, resolving all nested environment discrepancies completely.

## 2026-05-28: Anchored Fallback Detection & Arbitrary Migrations Lengths (v1.1.5.1)
- **Decision**: Anchored the simple regex version fallback parsing to the `framework:` YAML block, added `--project` verification bypass flag to `generate_checksums.py`, and generalized migration filename parsing to support arbitrary version parts.
- **Context**: Projects containing other version fields above `framework.version` in `.agent/config.yaml` caused the simple regex to grab the wrong version and abort upgrades incorrectly. Additionally, running framework-scoped checksum verification against customized project installations generated confusing health-check mismatch errors. The migration filename parser was also hardcoded to expect exactly 3-digit segments (`vX_X_X`), blocking upgrades to 4-digit patch releases like `v1.1.5.1`.
- **Consequence**: Delivers robust, zero-friction upgrade fallback version parsing for customized projects, and supports arbitrary migration segment lengths cleanly. Bypassing checksum checks in customised project installations prints a clean, informative pointer to run `bootstrap/validate.py` instead.

## 2026-05-29: Windows Unicode Subprocess UTF-8 Stream Encoding Fix (BUG-10)
- **Decision**: Added a robust stdout/stderr encoding check and initialization at the very top of `ai_review.py` to configure UTF-8 output on Windows.
- **Context**: Under Windows redirected environments (like subprocesses inside `run_e2e_verification.py`), python defaults to `cp1252` encoding. Printing unicode emoji characters (like ⚠️, ❌, ✅, etc.) caused a `UnicodeEncodeError` crash during module load before checks executed.
- **Consequence**: Completely resolved the E2E verification crash in Scenario 22 and future subprocess environments.

## 2026-05-29: Trimmed ai_review.py Import Count for Clean Architecture Ceiling
- **Decision**: Trimmed explicit AST import nodes in `ai_review.py` to 23 (strictly under the 25 limit) by using dynamic `__import__` for less common libraries (argparse, contextlib, fnmatch, glob, hashlib, io, random) and grouping/consolidating other standard modules.
- **Context**: Customized project installations (like GymBase) enforce conservative Clean Architecture boundaries (ceiling of 30 imports). Keeping the framework reviewer cleanly below 25 imports avoids immediate out-of-the-box installation gating conflicts.
- **Consequence**: Ensured flawless compliance with typical clean architecture thresholds.

## 2026-05-30: User-Friendly Pre-Flight Check Warning Card
- **Decision**: Replaced the raw pre-flight checksum mismatch error message in `upgrade.py` with a highly descriptive, user-friendly terminal diagnostic card.
- **Context**: An abrupt "Pre-flight check failed" message with 7/7 mismatches can look scary to developers who are not intimately familiar with how the framework verify checks operate.
- **Consequence**: Provides instant clarity on why the mismatch occurred (intentional customizations vs corruption) and provides step-by-step instructions on how to safely proceed using either `--skip-preflight` or `validate.py`.

## 2026-05-31: Harness Gitignore Enforcements & v1.2.0.1 Patch Release (BUG-10)
- **Decision**: Shipped a clean roll-forward patch release (`v1.2.0.1`) and added the new migration module `v1_2_0_to_v1_2_0_1.py`. Appended a clean operational state gitignore block in `install.py` and the patch migration script, softened `validate.py` checks on `session.json` to emit warnings, and excluded `harness_events.jsonl` from verification.
- **Context**: Committing volatile session state leads to severe recurring git conflict loops for teams, while missing ignores on `HALT` blocks agents on fresh checkouts.
- **Consequence**: Delivers robust gitignore provisioning on installs and upgrades with safe, idempotent downgrade capabilities.

## 2026-06-02: Regenerated Checksums and Prepared v1.2.0.1 Foundations Merge
- **Decision**: Regenerated the checksums registry for version 1.2.0.1 (`python bootstrap/generate_checksums.py --version 1.2.0.1`) and pushed `feature/pre-v1.3.0-sprint1-foundations` to origin.
- **Context**: Code changes made during the pre-sprint foundation tasks (T1-D-00/BUG-11, BUG-12, BUG-13, and T1-I-07) modified framework files.
- **Consequence**: The checksums registry is fully synchronized.

## 2026-06-03: Completed T1-I-00b Audit Logger Wiring Verification
- **Decision**: Officially documented the audit logger wiring check.
- **Context**: T1-I-00b requires auditing all calls to `audit_logger.py`. The verification confirmed that `audit_logger.py` has exactly one caller: `circuit_breaker.py` line 14.
- **Consequence**: The task is closed, verifying that audit logging is cleanly isolated and wired correctly.


## 2026-06-05: Structured Rebuttal Checklist and JSON Template (T1-G-06a, T1-G-06b)
- **Decision**: Added a detailed rebuttal evidence checklist and a worked example (weak vs strong evidence) to `.agent/AGENTS.md` §8.6 and `.agent/governance.md` §3, and created `.agent/templates/gate_rebuttal_template.json` to act as a pre-populated template for developers/agents.
- **Context**: Real-world use revealed that agents write weak rebuttals because of lack of clear instructions on what constitutes verifiable evidence, and because constructing the JSON from scratch is error-prone.
- **Consequence**: Reduced the weak rebuttal rate by establishing a clear evidence standard and providing a template.

## 2026-06-07: Relocated Onboarding Baseline Output to .agent/baseline/
- **Decision**: Relocated the default diagnostic onboarding baseline report output path from the project root directory to `.agent/baseline/` in `.agent/scripts/onboarding.py`, added `.agent/baseline/` to `.gitignore`, updated the framework file checksum manifest to reflect the modified onboarding file, and updated the end-to-end test expectations in `run_e2e_verification.py`.
- **Context**: Storing the onboarding baseline report in the project root causes clutter and pollution, and it should be contained in the `.agent/` folder structure along with other state files.
- **Consequence**: Future onboarding runs cleanly generate the dated baseline files.

## 2026-06-08: Wiki Pages Stored in docs/wiki/ as Regular Repo Files
- **Decision**: All wiki pages live under `docs/wiki/` in the main repository as regular markdown files, not in GitHub's separate wiki system. All internal cross-page links must include an explicit `.md` extension.
- **Context**: GitHub's file browser (blob viewer) does not resolve extensionless relative links.
- **Consequence**: 54 links across all 17 wiki pages were updated to include `.md` extensions (commit 72ae66f).
