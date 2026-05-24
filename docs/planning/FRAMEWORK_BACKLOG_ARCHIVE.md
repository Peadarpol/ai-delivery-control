# AISDLC Harness — Delivered Items Archive

Sections moved here from `FRAMEWORK_BACKLOG.md` once fully delivered.
Each section retains its original description detail for audit and reference.
The main backlog carries a one-line pointer back to this file.

---

## T1-A: Harness Extraction & Portability ✅ Complete (2026-05-21)

| ID | Item | Description | Effort | Status |
|----|------|-------------|--------|--------|
| T1-A-01 | **Standalone harness repository** | Extract the framework layer from Gym App into its own repository. Gym App becomes the first "project using the harness." Separates generic framework from project-specific config. | Medium | ✅ |
| T1-A-02 | **Bootstrap install script** | `bootstrap/install.py` — detects tech stack, copies framework files into target project, scaffolds project config from templates, wires pre-commit hooks, runs validation. Target: under 10 minutes from zero to working harness. | Medium | ✅ |
| T1-A-03 | **Environment validation script** | `bootstrap/validate.py` — confirms all required tools are installed, pre-commit hooks are wired, validate.py scripts pass, regression runner returns clean. Run at install time and on-demand. | Low | ✅ |
| T1-A-04 | **Config-driven architecture checks** | Replace hardcoded Python/Clean Architecture rules in `architecture_checks.py` with a config-driven rule set read from `.agent/config.yaml`. Any project can define its own layer boundaries and forbidden patterns without code changes. | Medium | ✅ |
| T1-A-05 | **Two-layer review_context.md** | Split `review_context.md` into a universal base layer (framework-owned, generic invariants) and a project layer (user-maintained, project-specific patterns). `ai_review.py` loads and concatenates both. New users get working AI review immediately; it improves as they fill in project context. | Low | ✅ |
| T1-A-06 | **Universal + stack-pack skills** | Split skills into universal (language-agnostic: systematic-debugging, code-review, security-audit, architect, dba) and stack packs (python-fastapi, python-django, node-express). Install script deploys universal skills always, stack pack based on detected tech. | Medium | ✅ |
| T1-A-07 | **Tool supplement generation** | Install script generates `CLAUDE.md`, `GEMINI.md`, `.cursorrules` from templates rather than requiring manual creation. Each is a thin shim pointing at `.agent/UNIVERSAL_CONTEXT.md`. | Low | ✅ |

---

## T1-F: Documentation & Shareability ✅ Complete (2026-05-21)

| ID | Item | Description | Effort | Status |
|----|------|-------------|--------|--------|
| T1-F-01 | **Getting-started guide** | `docs/getting-started.md` — install to first AI review gate firing in under 10 minutes. Written for someone who didn't build the harness. | Low | ✅ |
| T1-F-02 | **Configuration reference** | `docs/configuration.md` — every config.yaml field documented with type, default, and example. | Low | ✅ |
| T1-F-03 | **Customisation guide** | `docs/customisation.md` — how to add project-specific invariants to review_context.md, create custom skills, configure architecture checks. | Low | ✅ |
| T1-F-04 | **Refined AISDLC bootloader** | Update the bootloader document (written for a friend's fresh install) to reference the new standalone harness repository. The bootloader becomes the agent-readable setup guide for the framework. | Low | ✅ (`docs/aisdlc-bootloader.md`) |
| T1-F-05 | **Harness README** | Repository-level README with: what this is, 5-minute install, the "8 interruptions → 3 checkpoints" value proposition, link to docs. | Low | ✅ (delivered in T1-A-07) |
