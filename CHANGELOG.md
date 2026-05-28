# Changelog

## [1.1.5] — 2026-05-28

### Theme 1: Gating & Enforcement

#### Structured Rebuttal Protocol (T1-G-06)
- `--rebuttal` mode: adversarial principal-engineer auditor evaluates developer rebuttals against AI review FAILs
- `gate_rebuttal.json` structured input format with `finding_id`, `rebuttal_type` (`FALSE_POSITIVE` / `SPEC_EXCEPTION` / `ACCEPTABLE_RISK`), and evidence fields
- Diff-hash scoping locks rebuttals to the exact staged diff, preventing stale replay
- Per-finding rate limiter blocks repeat rebuttal attempts on already-rejected findings
- `rebuttal_pass.json` one-time hook-bypass token; consumed on next normal review pass
- Token budget integration: rebuttal calls tracked and counted against session budget
- `raw_completion` provider method added to `AnthropicProvider`, `OpenAIProvider`, and `OllamaProvider`
- Dual-vector rebuttal metrics added to `harness_health.py` (`rebuttal_pass_rate`, `rebuttal_avg_latency_ms`)
- 20 new unit tests in `tests/test_ai_review.py` covering all rebuttal paths
- E2E Scenario 25 validates full rebuttal flow end-to-end

#### Token Budget Enforcement
- Session token budget with 80% warning and 100% HALT sentinel
- Atomic structured JSON HALT writes (`.tmp` + `os.replace()`)
- `BYPASS_HALT_REASON` escape hatch with `harness_events.jsonl` audit trail
- Fail-closed enforcement when `session.json` is absent under an active budget

#### Stratified Review Routing
- Large-diff stratified review with high-risk file classification
- Thin-Standard fallback for low-risk oversized diffs (fail-open)
- `repo_map.py` PageRank integration for risk-weighted routing

### Framework Infrastructure
- Bootstrap upgrade/downgrade migration pipeline (v1.1.0 → v1.1.5)
- CRLF-normalized conflict detection; sidecar `.framework-v1.1.5` files for conflicts
- Atomic restore on mid-upgrade exception
- `bootstrap/validate.py` onboarding card and installation verification
- `bootstrap/checksums.py` SHA-256 integrity manifest (629 framework files)
- `bootstrap/generate_checksums.py --verify` for CI integrity checks
- Onboarding baseline snapshot generation

## [1.0.0] — 2026-05-21

### Initial Release
First extraction from GymBase production codebase.
Framework validated across 6 months of active SaaS development.

### Included
- AI adversarial review gate (pre-commit, diff-aware routing)
- PageRank repository map with ADR annotation injection
- Compiled wiki layer (Karpathy pattern, Gemma4 local compilation)
- Dream phase self-improvement loop
- Session lifecycle hooks with outcome inference
- Knowledge base lint pass
- Co-change blast radius estimator
- Governance prohibitions P-01 through P-13
- Universal skills library
- Model tiering configuration (local/cloud)
