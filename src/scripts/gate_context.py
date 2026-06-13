#!/usr/bin/env python3
"""
gate_context.py — Shared Gate Context Model and Utilities
Defines the GateContext schema and provides atomic read/write functions.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class ArchViolation(BaseModel):
    file: str
    line: int
    rule: str
    severity: str

class CoChangeWarning(BaseModel):
    file: str
    confidence: str  # EXTRACTED, INFERRED, or AMBIGUOUS (T1-H-10)
    reason: str

class GateContext(BaseModel):
    schema_version: str = "1.0"
    generated_at: Optional[str] = None
    diff_text: str = ""
    diff_hash: str = ""
    changed_files: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None

    # Populated by architecture_checks.py
    arch_violations: List[ArchViolation] = Field(default_factory=list)
    adr_domains: List[str] = Field(default_factory=list)

    # Populated by repo_map.py
    pagerank_scores: Dict[str, float] = Field(default_factory=dict)
    review_intensity: Literal["standard", "elevated", "critical"] = "standard"
    repo_map_text: str = ""

    # Populated by co_change_check.py
    co_change_warnings: List[CoChangeWarning] = Field(default_factory=list)

    # Populated and read by ai_review.py
    route_decision: Optional[Dict[str, Any]] = None
    verdict: Optional[Dict[str, Any]] = None

    # Evidence fields (T1-G-11)
    pytest_collect_status: Optional[str] = None
    todo_delta: Optional[int] = None

def get_context_path(project_root: Optional[Path] = None) -> Path:
    from harness_utils import PROJECT_ROOT
    root = project_root or PROJECT_ROOT
    return root / ".agent" / "state" / "gate_context_current.json"

def load_gate_context(path: Optional[Path] = None) -> Optional[GateContext]:
    if path is None:
        path = get_context_path()
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        # Check schema version
        if data.get("schema_version") != "1.0":
            return None
        return GateContext(**data)
    except Exception:
        # Degradation contract: return None on validation/parse error
        return None

def write_gate_context(context: GateContext, path: Optional[Path] = None) -> None:
    if path is None:
        path = get_context_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(context.model_dump(), f, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise e
