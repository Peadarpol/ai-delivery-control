# T1-E-04 `config.yaml` Parser Unification

This plan addresses the technical debt where `config.yaml` is parsed across ~20 different files using multiple incompatible strategies (hand-rolled regex, line parsers, and `yaml.safe_load`). This fixes the latent defect (HIB-061) in `check_traceability.py` and provides a single, robust contract for configuration access across the governance harness.

## Resolved Decisions

The design previously required user review regarding fallback parser complexity. This is now fully resolved:
- The fallback parser will be an indentation-aware parser that explicitly supports block scalars (`|` or `>`), extending the logic already proven in `bootstrap/migration_base.py:validate_yaml_config`.
- It will fail gracefully per-key with a warning logged via `log_harness_event` and `stderr` (which avoids circular imports since `log_harness_event` lives in `harness_utils.py`), never defaulting the whole file silently.
- A strict parity test will assert that the fallback parser and `yaml.safe_load` produce identical AST representations of both `bootstrap/templates/config.yaml.template` and `.agent/config.yaml`.
- Precedence: The central `DEFAULTS` table strictly wins over caller-provided `default=` arguments. The resolution chain is: User Config Value → `DEFAULTS` Table → Caller explicit `default=` argument → `None`.

## Proposed Changes

### 1. Core Configuration Utility (Commit 1)

#### [MODIFY] `src/scripts/harness_utils.py`
- **[NEW] DEFAULTS Table**: Define a single dictionary of all harness configuration defaults (e.g., `specs_path: docs/planning/specs`). Call sites will never redefine defaults.
- **Lazy Imports**: The `import yaml` statement MUST be lazy and try/except guarded *inside* the loading functions (not module top-level), otherwise the monkeypatch for testing fails and the fallback is never reached in a clean environment.
- **Generic YAML Loader**: Implement `load_yaml_with_fallback(path: Path | str) -> dict`. This attempts lazy `yaml.safe_load` and falls back to `_fallback_yaml_parse`. It has no caching and no defaults, making it safe for generic YAML consumers (e.g. `coupling_decisions.yaml`).
- **Config Loader**: Implement `load_harness_config(config_path: Path | str | None = None) -> dict`. This uses `load_yaml_with_fallback` under the hood.
- **Caching Semantics**: Implement a module-level `_config_cache` dict, keyed by resolved path, to parse the config exactly once per process. Add a `_reset_config_cache()` hook for test isolation.
- **Section-Aware Fetcher**: Implement `get_harness_config(section: str | None = None, key: str | None = None, default: Any = None) -> Any`. Adheres to the strict precedence chain: User Config → DEFAULTS table → Explicit argument.

### 2. Refactoring Regex-Based Parsers (Commit 1)

The following files will be refactored to replace their custom regex blocks with thin calls to `harness_utils.get_harness_config()`:

#### [MODIFY] `src/scripts/acceptance_hook.py`
- Replace regex `mode` and `specs_path` extraction with `get_harness_config()`.

#### [MODIFY] `.agent/scripts/check_traceability.py`
- **Import Fix**: Add the `_setup_sys_path` bootstrap pattern (from `check_spec.py:21-23`) so it can successfully import `src.scripts.harness_utils`.
- **Logic Fix (HIB-061)**: Use `get_harness_config` to resolve `traceability.specs_path`, falling back to `spec_gate.specs_path`, and finally the default from `harness_utils` (mandatory precedence chain). Read `mode` explicitly from the `outer_loop` section.

#### [MODIFY] `.agent/scripts/acceptance_check.py`
- Replace hand-rolled config reading regex loop with `get_harness_config()`.

#### [MODIFY] `.agent/scripts/pm_scaffold.py`
- Replace `get_specs_path()` regex logic with `get_harness_config()`.

#### [MODIFY] `.agent/scripts/check_spec.py`
- Replace regex blocks inside `_load_outer_loop_mode` and main logic with `get_harness_config()`.

#### [MODIFY] `.agent/scripts/init_session.py`
- Replace regex loop parsing with `get_harness_config()`.

#### [MODIFY] `src/scripts/route_decision.py`
- Replace `_load_adr_capability_mappings()` regex loop with `get_harness_config()`.

### 3. Refactoring yaml.safe_load Callers (Commit 2)

#### [MODIFY] Remaining Scripts (Bulk Update)
- Audit the remaining 11 target files (`ai_review.py`, `wiki_compile.py`, `retention_cleanup.py`, `circuit_breaker.py`, `harness_health.py`, `session_health.py`, `onboarding.py`, `providers.py`, `roster_builder.py`, `co_change_reconciler.py`, `wiki_lint.py`) to classify which YAML they actually parse.
- **For `config.yaml` consumers**: Replace their manual `yaml.safe_load` calls with `get_harness_config()` or `load_harness_config()`.
- **For other-YAML consumers** (like `coupling_decisions.yaml` in `co_change_reconciler.py`): Replace their manual `yaml.safe_load` calls with `harness_utils.load_yaml_with_fallback()`.

## Verification Plan

### Automated Tests
#### [NEW] `tests/unit/test_config_loader.py`
1. **Fallback Parity Test**: Parse `bootstrap/templates/config.yaml.template` and `.agent/config.yaml` using both `yaml.safe_load` and the fallback parser. Assert the resulting dictionaries are identical.
2. **No-PyYAML Execution**: Monkeypatch `sys.modules["yaml"] = None` during test setup to explicitly verify the lazy import triggers `ImportError` and the fallback parser executes successfully in a clean environment.
3. **Caching**: Verify `load_harness_config` hits the cache, is correctly keyed by path, and `_reset_config_cache` clears it.
4. **Consumer Section Awareness (HIB-061)**: Provide a config where an unrelated top-level `mode: ignore` exists above the `outer_loop: {mode: strict}` block. **Test consumer behavior directly**: Call the actual mode-resolution functions exported by `check_traceability.py`, `acceptance_hook.py`, and `check_spec.py` and verify they return `strict`.
5. **[NEW] Self-Enforcing Defaults Rule**: Add a static grep-style test ensuring no consumer calls `get_harness_config(..., default=X)` for a key that already exists in the `DEFAULTS` table, making AC1 self-enforcing.

### Manual Verification
- Dry-run `python .agent/scripts/check_traceability.py` and `python .agent/scripts/check_spec.py` locally to ensure the import paths and parsers work without raising exceptions.

## Commit Strategy
- **Commit 1**: Implement core loader + tests + Regex parser replacements (Sections 1 & 2).
- **Commit 2**: Implement the bulk swap of `yaml.safe_load` based on YAML target classification for the 11 remaining files (Section 3).
