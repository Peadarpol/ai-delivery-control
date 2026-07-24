#!/usr/bin/env python3
"""
API Design Skill — Validation Script

Validates that API changes meet quality standards:
1. FastAPI application starts and OpenAPI schema generates without error.
2. mypy type-checks the API routes layer.
3. Ruff lint is clean on the API routes directory.
4. If a schema snapshot exists at .agent/artifacts/openapi_snapshot.json,
   checks for breaking changes (removed paths or changed methods).

Usage:
    poetry run python .agent/skills/api-design/scripts/validate.py

Exit Codes:
    0  — PASS: API design gates satisfied.
    1  — FAIL: Schema generation failed, type errors, lint errors, or breaking changes.
"""

import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def _find_project_root() -> Path:
    try:
        res = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        if res.returncode == 0 and res.stdout.strip():
            return Path(res.stdout.strip())
    except Exception:
        pass
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".git").exists() or (parent / ".agent").exists():
            return parent
    return p.parents[2] if len(p.parents) > 2 else p.parent

PROJECT_ROOT = _find_project_root()
_src_scripts = PROJECT_ROOT / "src" / "scripts"
if _src_scripts.exists() and str(_src_scripts) not in sys.path:
    sys.path.insert(0, str(_src_scripts))

API_ROUTES_DIR = PROJECT_ROOT / "src" / "presentation" / "api"
SNAPSHOT_PATH = PROJECT_ROOT / ".agent" / "artifacts" / "openapi_snapshot.json"
SCHEMA_EXPORT_SCRIPT = """
import json
import sys
sys.path.insert(0, 'src')
try:
    from main import app
    schema = app.openapi()
    print(json.dumps(schema))
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
"""


def run_cmd(cmd: list[str], label: str) -> tuple[int, str]:
    print(f"\n{'=' * 60}")
    print(f"  VALIDATE: {label}")
    print(f"  Command:  {' '.join(cmd)}")
    print(f"{'=' * 60}\n")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    output = result.stdout + result.stderr
    print(output[-3000:] if len(output) > 3000 else output)
    return result.returncode, output


def generate_openapi_schema() -> tuple[bool, dict | None]:
    """Generate the OpenAPI schema by importing the FastAPI app."""
    result = subprocess.run(
        ["poetry", "run", "python", "-c", SCHEMA_EXPORT_SCRIPT],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print(f"\n❌ Schema generation failed:\n{result.stderr}")
        return False, None
    try:
        schema = json.loads(result.stdout)
        return True, schema
    except json.JSONDecodeError as e:
        print(f"\n❌ Schema JSON parse error: {e}\nOutput: {result.stdout[:500]}")
        return False, None


def check_breaking_changes(
    current_schema: dict, snapshot: dict
) -> tuple[bool, list[str]]:
    """Detect removed paths or changed HTTP methods vs snapshot."""
    breaking: list[str] = []
    snapshot_paths = snapshot.get("paths", {})
    current_paths = current_schema.get("paths", {})

    for path, methods in snapshot_paths.items():
        if path not in current_paths:
            breaking.append(f"REMOVED path: {path}")
        else:
            for method in methods:
                if method not in current_paths[path]:
                    breaking.append(f"REMOVED method: {method.upper()} {path}")

    return len(breaking) == 0, breaking


def main() -> int:
    results: list[tuple[str, bool]] = []

    # Check 1: OpenAPI schema generates without error
    print(f"\n{'=' * 60}")
    print("  VALIDATE: OpenAPI Schema Generation")
    print(f"{'=' * 60}\n")
    schema_ok, current_schema = generate_openapi_schema()
    results.append(("OpenAPI Schema Generates", schema_ok))
    if schema_ok:
        path_count = len(current_schema.get("paths", {}))
        print(f"  ✅ Schema generated successfully ({path_count} paths)")

    # Check 2: mypy on API routes
    if API_ROUTES_DIR.exists():
        exit_code, _ = run_cmd(
            ["poetry", "run", "mypy", str(API_ROUTES_DIR)],
            "mypy — API Routes Type Safety",
        )
        results.append(("mypy API Routes", exit_code == 0))
        if exit_code != 0:
            print("\n❌ FAIL: Type errors in API routes layer.")
    else:
        print(
            f"\n⚠️  API routes dir not found at {API_ROUTES_DIR} — skipping mypy check."
        )

    # Check 3: Ruff lint on API routes
    if API_ROUTES_DIR.exists():
        exit_code, _ = run_cmd(
            ["poetry", "run", "ruff", "check", str(API_ROUTES_DIR)],
            "Ruff Lint — API Routes",
        )
        results.append(("Ruff Lint API Routes", exit_code == 0))
        if exit_code != 0:
            print("\n❌ FAIL: Lint violations in API routes.")

    # Check 4: Breaking change detection vs snapshot
    if SNAPSHOT_PATH.exists() and schema_ok and current_schema:
        try:
            with open(SNAPSHOT_PATH) as f:
                snapshot = json.load(f)
            no_breaking, breaking_changes = check_breaking_changes(
                current_schema, snapshot
            )
            results.append(("No Breaking API Changes", no_breaking))
            if not no_breaking:
                print(
                    f"\n❌ FAIL: Breaking API changes detected ({len(breaking_changes)}):"
                )
                for change in breaking_changes:
                    print(f"   - {change}")
                print("\n   If intentional, update the snapshot:")
                print(f'   python -c "..." > {SNAPSHOT_PATH}')
            else:
                print(f"\n  ✅ No breaking changes vs snapshot ({SNAPSHOT_PATH.name})")
        except (json.JSONDecodeError, KeyError) as e:
            print(
                f"\n⚠️  Could not read snapshot: {e} — skipping breaking change check."
            )
    else:
        if not SNAPSHOT_PATH.exists():
            print(f"\n  ℹ️  No snapshot at {SNAPSHOT_PATH}. To create one:")
            print(
                "     poetry run python -c '<export script>' > .agent/artifacts/openapi_snapshot.json"
            )

    # Summary
    print(f"\n{'=' * 60}")
    print("  API DESIGN VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    all_passed = True
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  ✅ PASS — API design gates satisfied.")
        return 0
    else:
        print("\n  ❌ FAIL — See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
