#!/usr/bin/env python3
"""
gate_context.py — Shared Gate Context Model and Utilities
Defines the GateContext schema and provides atomic read/write functions.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
try:
    from pydantic import BaseModel, Field
    _pydantic_installed = True
except ImportError:
    _pydantic_installed = False
    class FieldStub:
        def __init__(self, default=None, default_factory=None, **kwargs):
            self.default = default
            self.default_factory = default_factory
    def Field(default=None, default_factory=None, **kwargs):
        return FieldStub(default, default_factory, **kwargs)
    class BaseModel:
        """NOTE: fallback stub does not validate Literal/type constraints — values are accepted as-is when Pydantic is absent."""
        def __init__(self, **kwargs):
            fields = {}
            for cls in self.__class__.__mro__:
                if hasattr(cls, "__annotations__"):
                    for field_name in cls.__annotations__:
                        if not field_name.startswith("_") and field_name not in fields:
                            val = getattr(self.__class__, field_name, None)
                            fields[field_name] = val
            for k, val in fields.items():
                if val is not None:
                    if isinstance(val, FieldStub):
                        if val.default_factory:
                            setattr(self, k, val.default_factory())
                        else:
                            setattr(self, k, val.default)
                    else:
                        setattr(self, k, val)
                else:
                    setattr(self, k, None)
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self) -> Dict[str, Any]:
            res = {}
            for k, v in self.__dict__.items():
                if isinstance(v, BaseModel):
                    res[k] = v.model_dump()
                elif isinstance(v, list):
                    res[k] = [item.model_dump() if isinstance(item, BaseModel) else item for item in v]
                else:
                    res[k] = v
            return res
        def dict(self) -> Dict[str, Any]:
            return self.model_dump()
from src.scripts.harness_utils import PROJECT_ROOT

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
    schema_version: str = "1.1"
    generated_at: Optional[str] = None
    diff_text: str = ""
    diff_hash: str = ""
    changed_files: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    posture: str = "strict"
    dispositions: List[Dict[str, Any]] = Field(default_factory=list)

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
    from src.scripts.harness_utils import PROJECT_ROOT
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
        # Check schema version — accept any 1.x schema version
        ver = str(data.get("schema_version", ""))
        if not ver.startswith("1."):
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


def gather_pytest_evidence(changed_files: List[str]) -> Dict[str, Any]:
    """Gather pytest collect evidence.
    For each changed python file, look for a corresponding test file and collect its tests.
    """
    evidence = {}
    for f in changed_files:
        if not f.endswith(".py") or f.startswith("tests/"):
            continue
        path = Path(f)
        basename = path.name
        test_name = f"test_{basename}"
        found_tests = list(PROJECT_ROOT.glob(f"**/tests/**/{test_name}")) + list(PROJECT_ROOT.glob(f"**/tests/{test_name}"))
        if found_tests:
            test_file = found_tests[0]
            try:
                res = subprocess.run(
                    [sys.executable, "-m", "pytest", "--collect-only", "-q", str(test_file)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=str(PROJECT_ROOT),
                    timeout=60
                )
                if res.returncode == 0:
                    tests = [line.strip() for line in res.stdout.splitlines() if line.strip() and "::" in line]
                    evidence[f] = {
                        "test_file": str(test_file.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "collected_tests": tests
                    }
                else:
                    evidence[f] = {
                        "test_file": str(test_file.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "error": f"pytest returned {res.returncode}"
                    }
            except subprocess.TimeoutExpired:
                evidence[f] = {
                    "test_file": str(test_file.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "error": "pytest collection timed out after 60s"
                }
            except Exception as e:
                evidence[f] = {
                    "test_file": str(test_file.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "error": str(e)
                }
        else:
            evidence[f] = {
                "test_file": None,
                "collected_tests": []
            }
    return evidence


def calculate_todo_delta(diff: str) -> int:
    added_todos = 0
    removed_todos = 0
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            if "TODO" in line.upper() or "FIXME" in line.upper():
                added_todos += 1
        elif line.startswith("-") and not line.startswith("---"):
            if "TODO" in line.upper() or "FIXME" in line.upper():
                removed_todos += 1
    return added_todos - removed_todos


def get_recent_file_churn(diff: str) -> str:
    """Check if any changed files have been modified >3 times in the last week."""
    # Extract filenames from diff headers
    files = re.findall(r"^\+\+\+ b/(.+)$", diff, re.MULTILINE)
    churn_warnings = []
    for filepath in files[:20]:  # Limit to avoid slowness
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--oneline",
                    "--since=7 days ago",
                    "--follow",
                    "--",
                    filepath,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(PROJECT_ROOT),
            )
            commit_count = len(result.stdout.strip().splitlines())
            if commit_count >= 3:
                churn_warnings.append(
                    f"  {filepath} has been modified {commit_count} times in the last 7 days"
                )
        except Exception:
            pass
    return "\n".join(churn_warnings) if churn_warnings else ""
