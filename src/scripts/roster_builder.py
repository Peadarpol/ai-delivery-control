#!/usr/bin/env python3
"""
roster_builder.py — Shared AST Roster Builder

Statically parses ORM model and mixin class definitions across typical Python
projects to build a deterministic branch-isolated model roster sidecar JSON file.
"""

from __future__ import annotations

import ast
import glob
import json
import os
from pathlib import Path
from typing import Any, Dict, List


def log_harness_event(event_dict: Dict[str, Any], project_root: Path) -> None:
    """Log a harness event to .agent/state/harness_events.jsonl for auditing."""
    try:
        log_dir = project_root / ".agent" / "state"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "harness_events.jsonl"
        
        import datetime
        session_id = None
        session_file = project_root / ".agent" / "state" / "session.json"
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    session_id = json.load(f).get("session_id")
            except Exception:
                pass
                
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        
        record = {
            "schema_version": "1.0",
            "event_type": event_dict.get("event_type"),
            "timestamp_utc": now_utc,
            "session_id": session_id,
            "commit_sha": None,
            "agent": "roster_builder",
            "severity": event_dict.get("severity", "INFO"),
            "payload": event_dict.get("payload", {}),
        }
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


def _extract_fk_and_nullable(node: ast.AST) -> tuple[bool, str | None]:
    """Helper to parse ForeignKey and nullable keyword arguments from an AST node."""
    nullable = True  # SQL Alchemy default is nullable=True
    fk_target = None

    # Helper function to inspect a Call node (like Column() or mapped_column())
    def inspect_call(call_node: ast.Call):
        nonlocal nullable, fk_target
        # Check keyword arguments for nullable
        for kw in call_node.keywords:
            if kw.arg == "nullable":
                if isinstance(kw.value, ast.Constant):
                    nullable = bool(kw.value.value)
                elif isinstance(kw.value, ast.NameConstant):  # Python < 3.8 compat
                    nullable = bool(kw.value.value)

        # Check args and keywords for ForeignKey call
        def check_for_fk(arg_node: ast.AST):
            nonlocal fk_target
            if isinstance(arg_node, ast.Call):
                func_name = ""
                if isinstance(arg_node.func, ast.Name):
                    func_name = arg_node.func.id
                elif isinstance(arg_node.func, ast.Attribute):
                    func_name = arg_node.func.attr

                if func_name == "ForeignKey":
                    # Get target string argument
                    if arg_node.args and isinstance(arg_node.args[0], ast.Constant):
                        fk_target = str(arg_node.args[0].value)
                    elif arg_node.args and isinstance(arg_node.args[0], ast.Str):  # Python < 3.8
                        fk_target = str(arg_node.args[0].s)

        for arg in call_node.args:
            check_for_fk(arg)
        for kw in call_node.keywords:
            check_for_fk(kw.value)

    # Walk targets/right-hand values
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
        inspect_call(node.value)
    elif isinstance(node, ast.AnnAssign) and node.value and isinstance(node.value, ast.Call):
        inspect_call(node.value)
        # Also check annotation for Nullable types (e.g. Mapped[Optional[int]] or int | None)
        annotation_str = ast.unparse(node.annotation) if hasattr(ast, "unparse") else ""
        if "Optional" in annotation_str or "None" in annotation_str or "mapped_column" in annotation_str:
            nullable = True

    return nullable, fk_target


def build_branch_isolation_roster(
    patterns: list[str],
    base_classes: list[str],
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Parse model definitions in matching pattern paths and build the branch isolation roster.

    If no files are found matching the patterns, logs a warning and returns an empty roster.
    """
    if project_root is None:
        project_root = Path.cwd()

    matched_files: list[Path] = []
    for pat in patterns:
        # Resolve pattern relative to project_root
        search_pattern = str(project_root / pat)
        # Handle globbing with standard python glob
        for match in glob.glob(search_pattern, recursive=True):
            p = Path(match)
            if p.is_file() and p.suffix == ".py":
                matched_files.append(p)

    if not matched_files:
        msg = f"No model files matched branch_isolation.model_file_patterns: {patterns} — BRANCH_ISOLATION suppression inactive. Update config.yaml to fix."
        print(f"⚠️  [ROSTER] {msg}")
        log_harness_event({
            "event_type": "branch_isolation_roster_warning",
            "severity": "WARNING",
            "payload": {
                "message": msg,
                "patterns": patterns,
            }
        }, project_root)
        return {}

    roster: dict[str, Any] = {}

    for filepath in matched_files:
        try:
            content = filepath.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(filepath))
        except Exception as e:
            print(f"⚠️  [ROSTER] Failed to parse AST for {filepath.name}: {e}")
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            class_name = node.name
            is_isolated = False
            has_branch_id_col = False
            nullable = True
            fk = "branches.id"

            # 1. Resolve Class Base Names
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                    bases.append(f"{base.value.id}.{base.attr}")

            if any(b in bases for b in base_classes):
                is_isolated = True

            # 2. Walk Class Body to Find Explicit branch_id Declarations
            for stmt in node.body:
                # Check for assignments like: branch_id = Column(...) or branch_id: Mapped[int] = mapped_column(...)
                is_assign = False
                target_node = None

                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "branch_id":
                            is_assign = True
                            target_node = stmt
                            break
                elif isinstance(stmt, ast.AnnAssign):
                    if isinstance(stmt.target, ast.Name) and stmt.target.id == "branch_id":
                        is_assign = True
                        target_node = stmt

                if is_assign and target_node:
                    has_branch_id_col = True
                    is_isolated = True
                    # Extract nullable and fk from argument calls
                    parsed_nullable, parsed_fk = _extract_fk_and_nullable(target_node)
                    nullable = parsed_nullable
                    if parsed_fk:
                        fk = parsed_fk

            if is_isolated:
                roster[class_name] = {
                    "branch_isolated": True,
                    "column": "branch_id",
                    "nullable": nullable,
                    "fk": fk,
                }

    return roster
