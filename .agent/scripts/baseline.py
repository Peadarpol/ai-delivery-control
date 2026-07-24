#!/usr/bin/env python3
"""
.agent/scripts/baseline.py — Human-Only Baseline Manifest CLI (T1-G-18 Phase P2)

Manages the grandfathered technical debt manifest (.agent/baseline.json).

Subcommands:
  init    : Collect all pre-existing violations into .agent/baseline.json (Human-only).
  refresh : Re-scan current codebase and update .agent/baseline.json (Human-only).
  report  : Output a read-only report comparing current findings vs baseline.json.
"""

from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Bootstrap harness path
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

try:
    from harness_utils import _safe_git_env, log_harness_event
except ImportError:
    def _safe_git_env() -> dict:
        return dict(os.environ)
    def log_harness_event(evt: dict) -> None:
        pass

BASELINE_PATH = PROJECT_ROOT / ".agent" / "baseline.json"
SCHEMA_VERSION = "1.0"


def compute_manifest_sha256(entries: List[Dict[str, Any]]) -> str:
    """Compute SHA-256 over entries array using canonical JSON serialization."""
    canonical_bytes = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def extract_ast_region_sha256(file_path: Path, line: int) -> str:
    """Compute SHA-256 hash over the innermost enclosing AST node (FunctionDef, AsyncFunctionDef, ClassDef).
    Fallback to whole-file SHA-256 if AST parsing fails or line is top-level.
    """
    if not file_path.exists():
        return ""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        best_node = None
        best_size = float("inf")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if hasattr(node, "lineno") and hasattr(node, "end_lineno") and node.lineno is not None and node.end_lineno is not None:
                    if node.lineno <= line <= node.end_lineno:
                        size = node.end_lineno - node.lineno
                        if size < best_size:
                            best_size = size
                            best_node = node

        if best_node is not None:
            region_str = ast.unparse(best_node)
            return hashlib.sha256(region_str.encode("utf-8")).hexdigest()

        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    except Exception:
        try:
            return hashlib.sha256(file_path.read_bytes()).hexdigest()
        except Exception:
            return ""


def check_human_guard() -> None:
    """Refuse baseline modification when executed by an AI agent or non-interactively."""
    if os.environ.get("AGENT_ID") or not sys.stdin.isatty():
        print("❌ Baseline generation is human-only.", file=sys.stderr)
        print("   Agent executions and non-interactive scripts cannot create or refresh baseline.json.", file=sys.stderr)
        sys.exit(1)


def scan_current_violations() -> List[Dict[str, Any]]:
    """Scan current codebase for architectural and quality violations."""
    arch_script = PROJECT_ROOT / ".agent" / "skills" / "universal" / "senior-architect" / "scripts" / "architecture_checks.py"
    entries: List[Dict[str, Any]] = []

    if arch_script.exists():
        try:
            res = subprocess.run(
                [sys.executable, str(arch_script)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(PROJECT_ROOT),
                env=_safe_git_env(),
            )
            out = res.stdout + "\n" + res.stderr
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

            for line_str in out.splitlines():
                if "  - " in line_str or "[FAIL]" in line_str or "[ADVISORY]" in line_str:
                    clean = line_str.strip().lstrip("-").strip()
                    for tag in ("[FAIL]", "[ADVISORY]", "[WARN]", "[OK]"):
                        if clean.startswith(tag):
                            clean = clean[len(tag):].strip()

                    parts = clean.split(":", 2)
                    if len(parts) >= 3 and parts[1].strip().isdigit():
                        rel_file = parts[0].strip().replace("\\", "/")
                        line_no = int(parts[1].strip())
                        msg = parts[2].strip()

                        # Determine rule
                        rule = "ARCHITECTURE_RULE"
                        msg_lower = msg.lower()
                        if "layer" in msg_lower:
                            rule = "LAYER_BOUNDARY"
                        elif "coupling" in msg_lower:
                            rule = "HIGH_COUPLING"
                        elif "conditional branch filter" in msg_lower:
                            rule = "BRANCH_FILTER"
                        elif "aggregate root" in msg_lower:
                            rule = "AGGREGATE_ROOT"
                        elif "concrete infrastructure" in msg_lower:
                            rule = "INTERFACE_SEGREGATION"
                        elif "lifespan" in msg_lower:
                            rule = "ASGI_LIFESPAN"
                        elif "forbidden pattern" in msg_lower:
                            rule = "FORBIDDEN_PATTERN"
                        elif "nameerror" in msg_lower or "type checking" in msg_lower:
                            rule = "TYPE_CHECKING_CAST"

                        abs_file = PROJECT_ROOT / rel_file
                        region_hash = extract_ast_region_sha256(abs_file, line_no)

                        entries.append({
                            "rule": rule,
                            "file": rel_file,
                            "line": line_no,
                            "region_sha256": region_hash,
                            "first_seen": now_iso,
                            "note": msg,
                        })
        except Exception as e:
            print(f"⚠️  Warning: Scannner execution failed: {e}", file=sys.stderr)

    return entries


def cmd_init() -> int:
    """Initialize .agent/baseline.json manifest."""
    check_human_guard()
    print("🔍 Scanning codebase to initialize baseline manifest...")
    entries = scan_current_violations()

    harness_ver = "unknown"
    harness_ver_file = PROJECT_ROOT / "harness_version.txt"
    if harness_ver_file.exists():
        try:
            harness_ver = harness_ver_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    manifest_hash = compute_manifest_sha256(entries)
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    manifest = {
        "header": {
            "schema_version": SCHEMA_VERSION,
            "manifest_sha256": manifest_hash,
            "generated_at": now_utc,
            "generated_by": os.environ.get("USER") or os.environ.get("USERNAME") or "human",
            "harness_version": harness_ver,
            "posture_at_generation": "ratchet",
        },
        "entries": entries,
    }

    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"✅ Baseline successfully initialized at {BASELINE_PATH.name} ({len(entries)} entries grandfathered).")
    print(f"   Manifest SHA-256: {manifest_hash[:12]}...")
    return 0


def cmd_refresh() -> int:
    """Refresh .agent/baseline.json manifest."""
    check_human_guard()
    return cmd_init()


def cmd_report() -> int:
    """Print read-only report comparing current findings vs baseline."""
    if not BASELINE_PATH.exists():
        print(f"⚠️  No baseline manifest found at {BASELINE_PATH.name}.")
        print("   Run 'python .agent/scripts/baseline.py init' to create one.")
        return 0

    try:
        raw_text = BASELINE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        header = data.get("header", {})
        entries = data.get("entries", [])
        stored_hash = header.get("manifest_sha256", "")

        computed_hash = compute_manifest_sha256(entries)
        tampered = stored_hash != computed_hash

        print("==================================================")
        print("AI Delivery Control — Baseline Grandfather Report")
        print("==================================================")
        print(f"Manifest File  : {BASELINE_PATH.name}")
        print(f"Generated At   : {header.get('generated_at', 'unknown')}")
        print(f"Generated By   : {header.get('generated_by', 'unknown')}")
        print(f"Entries Count  : {len(entries)}")
        print(f"Tamper Status  : {'🚨 TAMPER SUSPECTED (hash mismatch)' if tampered else '✅ VALID'}")
        print("==================================================\n")

        current_violations = scan_current_violations()

        grandfathered = []
        new_violations = []

        baseline_map = {(e["rule"], e["file"]): e for e in entries}

        for v in current_violations:
            key = (v["rule"], v["file"])
            if key in baseline_map:
                stored = baseline_map[key]
                if v["region_sha256"] == stored.get("region_sha256"):
                    grandfathered.append(v)
                else:
                    new_violations.append((v, "region hash changed"))
            else:
                new_violations.append((v, "new finding"))

        print(f"Grandfathered tolerated findings : {len(grandfathered)}")
        print(f"New blocking findings             : {len(new_violations)}")

        if new_violations:
            print("\n🔴 New Blocking Findings:")
            for v, reason in new_violations:
                print(f"  - [{v['rule']}] {v['file']}:{v['line']} — {v['note']} ({reason})")

        return 0
    except Exception as e:
        print(f"❌ Error reading baseline manifest: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Human-Only Baseline Manifest CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize .agent/baseline.json manifest (Human-only)")
    subparsers.add_parser("refresh", help="Refresh .agent/baseline.json manifest (Human-only)")
    subparsers.add_parser("report", help="Read-only report of baseline status")

    args = parser.parse_args()

    if args.command == "init":
        return cmd_init()
    elif args.command == "refresh":
        return cmd_refresh()
    elif args.command == "report":
        return cmd_report()

    return 0


if __name__ == "__main__":
    sys.exit(main())
