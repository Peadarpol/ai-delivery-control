# Subprocess-Import Bug Sweep

**Summary:** Total files checked: 93 | Total clean: 90 | Total confirmed instances: 3 | Total ambiguous: 0

## Methodology
Searched all `.py` files across `.agent/scripts/`, `src/scripts/`, `bootstrap/`, and `.agent/skills/` (recursive) for `subprocess.run` or `subprocess.Popen` invocations. 
For each invocation, the file was checked for a top-level `import subprocess` or a local `import subprocess` preceding the call within the same scope. 

## Confirmed Instances (3)
These files suffer from the identical pattern: `subprocess.run` is called inside a `try` block, no `import subprocess` is present (either globally or locally), and the resulting `NameError` is silently swallowed by a broad `except Exception:` block, forcing a silent fallback.

1. `.agent/scripts/co_change_reconciler.py`
   - Unimported call site: `line 19`
   - Swallowing except block: `line 22`

2. `.agent/scripts/wiki_compile.py` (Nested inside `load_domain_registry()`)
   - Unimported call site: `line 60`
   - Swallowing except block: `line 63`

3. `.agent/scripts/wiki_lint.py`
   - Unimported call site: `line 53`
   - Swallowing except block: `line 56`

## Clean Files (90)
- **53 files** do not use `subprocess` at all.
- **33 files** properly import `subprocess` globally at the top level, ensuring all functions in the module have safe access.
- **4 files** (`src/scripts/posture.py`, `src/scripts/state_persistence.py`, `.agent/skills/universal/senior-architect/scripts/architecture_checks.py`, `.agent/scripts/pm_scaffold.py`) use a local `import subprocess` inside the `try` block immediately preceding the `subprocess.run()` calls, correctly binding the module to the local scope without raising a `NameError`.

## Ambiguous (0)
No files were flagged as ambiguous. All `subprocess` references were definitively traceable to either a safe import or a confirmed swallowing bug.
