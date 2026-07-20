"""
acceptance_hook.py — Spec Acceptance Verification (T1-L-05a)

Invoked as a Claude Code Stop hook (registered in .claude/settings.json via
bootstrap/templates/claude_settings_hooks.json).  Asserts that all specs
referenced by commits on the current branch carry an ACCEPTED status before
the session is closed.

IMPORTANT — Claude Code only:
    This hook is wired exclusively via Claude Code's Stop hook mechanism.
    Gemini CLI has no equivalent Stop hook and will NOT trigger this script
    automatically.  On Gemini-driven feature branches, spec acceptance is
    verified manually or via CI.  Gemini sessions rely on the outcome_override
    convention in session.json (documented in AGENTS.md §6 and GEMINI.md) for
    close-out fidelity — that is separate from acceptance checking.

    If you add Gemini CLI support in the future, call this script from the
    Gemini session-close sequence explicitly (e.g. in the agent_session_close
    write step) rather than relying on a hook event that does not fire.

Usage (invoked automatically by Claude Code):
    python src/scripts/acceptance_hook.py

Exit codes:
    0 — All specs accepted (or no specs found for this branch).
    1 — One or more specs are not yet in ACCEPTED status.
    2 — Hook skipped (not on a feature branch, or acceptance check is disabled).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = PROJECT_ROOT / ".agent" / "state"
CONFIG_PATH = PROJECT_ROOT / ".agent" / "config.yaml"

# Branches where acceptance checking applies
_FEATURE_BRANCH_PATTERNS = [r"^feat/", r"^feature/", r"^release/"]
# Spec files in this dir are scanned for status
_DEFAULT_SPECS_DIR = PROJECT_ROOT / "docs" / "planning" / "specs"


def _get_current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _is_feature_branch(branch: str) -> bool:
    return any(re.match(pat, branch) for pat in _FEATURE_BRANCH_PATTERNS)


def _resolve_specs_dir() -> Path:
    """Read specs_path from config.yaml using get_harness_config if present, otherwise use the default."""
    from harness_utils import get_harness_config
    specs_path = get_harness_config("acceptance_gate", "specs_path", default="docs/planning/specs/")
    return PROJECT_ROOT / Path(specs_path)


def _load_spec_status(specs_dir: Path) -> dict[str, str]:
    """Return {spec_id: status} for all SPEC-*.md files found."""
    statuses: dict[str, str] = {}
    if not specs_dir.exists():
        return statuses

    status_pattern = re.compile(r"^status:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
    id_pattern = re.compile(r"^(SPEC-\d+)", re.IGNORECASE)

    for spec_file in sorted(specs_dir.glob("SPEC-*.md")):
        spec_id_match = id_pattern.match(spec_file.stem.upper())
        if not spec_id_match:
            continue
        spec_id = spec_id_match.group(1)
        try:
            content = spec_file.read_text(encoding="utf-8")
            status_match = status_pattern.search(content)
            statuses[spec_id] = status_match.group(1).strip() if status_match else "UNKNOWN"
        except Exception:
            statuses[spec_id] = "UNREADABLE"

    return statuses


def _get_branch_spec_refs(branch: str, specs_dir: Path) -> list[str]:
    """Return spec IDs referenced in commit messages on this branch since main."""
    try:
        result = subprocess.run(
            ["git", "log", "main..HEAD", "--pretty=%s %b"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []

        found: list[str] = []
        id_pattern = re.compile(r"\b(SPEC-\d+)\b", re.IGNORECASE)
        for line in result.stdout.splitlines():
            for m in id_pattern.finditer(line):
                sid = m.group(1).upper()
                if sid not in found:
                    found.append(sid)
        return found
    except Exception:
        return []


def _sync_accepted_to_db(spec_id: str, status: str) -> None:
    """Best-effort sync to SQLite — never raises."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src" / "scripts"))
        from state_persistence import sync_spec_acceptance_to_db  # type: ignore[import]
        sync_spec_acceptance_to_db(spec_id, status)
    except Exception:
        pass


def main() -> int:
    branch = _get_current_branch()

    if not _is_feature_branch(branch):
        print(
            f"[ACCEPTANCE] Branch '{branch}' is not a feature branch — "
            "acceptance check skipped. (exit 2)"
        )
        return 2

    specs_dir = _resolve_specs_dir()
    all_statuses = _load_spec_status(specs_dir)
    branch_refs = _get_branch_spec_refs(branch, specs_dir)

    if not branch_refs:
        print(
            "[ACCEPTANCE] No SPEC-* references found in branch commit messages — "
            "nothing to verify. (exit 0)"
        )
        return 0

    print(f"[ACCEPTANCE] Checking {len(branch_refs)} spec(s) on branch '{branch}'...")

    not_accepted: list[str] = []
    for spec_id in branch_refs:
        status = all_statuses.get(spec_id, "NOT FOUND")
        _sync_accepted_to_db(spec_id, status)
        symbol = "✓" if status.upper() == "ACCEPTED" else "✗"
        print(f"  {symbol} {spec_id}: {status}")
        if status.upper() != "ACCEPTED":
            not_accepted.append(spec_id)

    if not_accepted:
        print(
            f"\n[ACCEPTANCE] FAIL — {len(not_accepted)} spec(s) not yet ACCEPTED: "
            + ", ".join(not_accepted)
        )
        print(
            "[ACCEPTANCE] Set status: ACCEPTED in the spec file(s) before closing "
            "this branch, or move acceptance to CI if the criteria are not yet met."
        )
        return 1

    print(f"\n[ACCEPTANCE] All {len(branch_refs)} spec(s) are ACCEPTED. ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
