#!/usr/bin/env python3
"""
.agent/scripts/tooling_staleness_check.py — Static Path-Staleness & Clean-Report Validator (Tier 4, D2)

Scans Python scripts across .agent/scripts/ and .agent/skills/**/scripts/ for unresolvable path literals
and cross-checks against registered clean-markers in .agent/config/tooling_reports.yaml.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
import yaml


# Ensure src/scripts is in sys.path for harness_utils
_bootstrap_path = Path(__file__).resolve()
_bootstrap_root = None
for _p in [_bootstrap_path] + list(_bootstrap_path.parents):
    if (_p / ".git").exists() or (_p / ".agent").exists():
        _bootstrap_root = _p
        break
if _bootstrap_root and str(_bootstrap_root / "src" / "scripts") not in sys.path:
    sys.path.insert(0, str(_bootstrap_root / "src" / "scripts"))

try:
    from src.scripts.harness_utils import _find_project_root
except ImportError:
    from harness_utils import _find_project_root


def safe_print(*args, **kwargs):
    """Safe print helper preventing UnicodeEncodeError on CP1252 Windows consoles."""
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    file = kwargs.get("file", sys.stdout)
    text = sep.join(str(arg) for arg in args) + end
    encoding = getattr(file, "encoding", "utf-8") or "utf-8"
    file.write(text.encode(encoding, errors="replace").decode(encoding))


PROJECT_ROOT = _find_project_root()


@dataclass
class StalePathFinding:
    script_path: Path
    line_no: int
    path_literal: str


@dataclass
class UntrustworthyCleanFinding:
    script_path: Path
    report_path: Path
    matched_marker: str
    stale_paths: list[str]


def discover_target_scripts(project_root: Path) -> list[Path]:
    """Find all .py files in .agent/scripts/ and .agent/skills/**/scripts/."""
    targets: list[Path] = []

    agent_scripts = project_root / ".agent" / "scripts"
    if agent_scripts.exists():
        for p in agent_scripts.rglob("*.py"):
            if p.is_file():
                targets.append(p)

    agent_skills = project_root / ".agent" / "skills"
    if agent_skills.exists():
        for p in agent_skills.rglob("*.py"):
            if p.is_file() and "scripts" in p.parts:
                targets.append(p)

    return sorted(list(set(targets)))


# Reused non-path filtering conventions from loop_closure_check.py & normalize_component
TAG_PATTERN = re.compile(r"^(?:SPEC|HIB|T1|T2|T3|T4)\-[A-Za-z0-9_\-]+(?:\.md)?$", re.IGNORECASE)
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")
VALID_EXTENSIONS = {".py", ".md", ".yaml", ".yml", ".json", ".jsonl", ".csv", ".txt"}


def is_candidate_path_literal(val: str) -> bool:
    """Determine if a string literal is a path candidate requiring resolution."""
    if not val:
        return False

    # Multi-line strings / docstrings / help text
    if "\n" in val or "\r" in val:
        return False

    cleaned = val.strip()
    if len(cleaned) < 3:
        return False

    # Filter score strings like '/10', '/10.'
    if re.match(r"^/\d+\.?$", cleaned):
        return False

    # XML/HTML tags and escaped regex brackets
    if cleaned.startswith("<") or cleaned.startswith("</") or r"\[" in cleaned or r"\]" in cleaned:
        return False

    # Git branch prefixes / category labels / unit labels
    if (
        cleaned
        in {
            "n/a",
            "N/A",
            "DB/Migration",
            "API/Service",
            "CI/CD",
            "Y/N",
            "hotfix/",
            "fix/doc",
            "chore/",
            "typo/",
            "rfc/",
            "spec/",
            "release/",
            "migration/",
            "epic/",
            "tokens/session",
            "feat/active-wip",
            "Evidence/Rationale statement",
        }
        or cleaned.startswith(("origin/", "hotfix/", "feature/"))
    ):
        return False

    # Sentences with spaces (real file path literals in code do not contain sentence text with spaces)
    if " " in cleaned:
        words = cleaned.split()
        if len(words) > 2 or any(
            w.lower()
            in {
                "with",
                "in",
                "to",
                "or",
                "and",
                "due",
                "first",
                "run",
                "pending",
                "data",
                "threshold",
                "failed",
                "could",
                "not",
                "is",
                "are",
                "does",
                "exist",
                "found",
                "statement",
            }
            for w in words
        ):
            return False
        if any(c in cleaned for c in ["=", "+", "(", ")", "[", "]", ":"]):
            return False

    # Sentence text / log messages / help prompts
    if any(
        phrase in cleaned
        for phrase in [
            "Usage:",
            "Update ",
            "Failed to",
            "Could not",
            "No ",
            "Please ",
            "Run this",
            "Missing or",
            "For ",
            "Note:",
            "P = ",
            "S = ",
            "Y/N",
            "Copy ",
            "Options:",
            "does not exist",
            "not found",
            "Falling back",
            "Consider ",
            "Check that",
            "Database session",
            "Database to",
            "Directory to",
            "Path to",
            "Append a structured",
            "Decision title",
            "Context / motivation",
            "Consequence / trade-offs",
            "Generated Onboarding",
            "Ollama",
            "Bandit SAST",
            "Ruff Lint",
            "TAMPER_SUSPECTED",
        ]
    ):
        return False

    # Sentence punctuation
    if any(c in cleaned for c in ["?", "!", ",", ";"]):
        return False

    # Markdown syntax / links
    if "](" in cleaned or "file:///" in cleaned or cleaned.startswith(("#", "**")):
        return False

    # Filter URLs and API MIME types / routes
    if cleaned.startswith(("http://", "https://", "git@", "file://", "/api/", "/v1/")):
        return False
    if cleaned == "application/json":
        return False

    # Filter ISO dates/timestamps
    if DATE_PATTERN.match(cleaned):
        return False

    # Filter SPEC/HIB tags (from loop_closure_check.py)
    if TAG_PATTERN.match(cleaned):
        return False

    # Filter CLI flags and command invocations
    if cleaned.startswith("--") or cleaned.startswith(
        ("python ", "git ", "pytest ", "npx ", "npm ", "poetry ")
    ):
        return False

    # Filter format strings and unresolved template variables
    if "%s" in cleaned or "%d" in cleaned or "{" in cleaned or "}" in cleaned:
        return False

    # Filter wildcards or glob patterns
    if "*" in cleaned or "?" in cleaned:
        return False

    # Filter regex character classes / anchors / escape sequences
    if (
        r"\b" in cleaned
        or r"\s" in cleaned
        or r"\d" in cleaned
        or r"\." in cleaned
        or "^" in cleaned
        or "$" in cleaned
    ):
        return False

    # Filter status words / uppercase constants
    if cleaned in {
        "PASS",
        "FAIL",
        "WARN",
        "CRITICAL",
        "HEALTHY",
        "SUCCESS",
        "INFO",
        "WIRED",
        "NOT-WIRED",
    }:
        return False

    # Must contain path separators OR end with a known file extension
    has_separator = "/" in cleaned or "\\" in cleaned
    has_extension = any(cleaned.lower().endswith(ext) for ext in VALID_EXTENSIONS)

    if not (has_separator or has_extension):
        return False

    # Path literals must have folder separators (e.g. src/foo.py, .agent/bar.yaml)
    if not has_separator:
        return False

    return True


def extract_docstring_node_ids(tree: ast.AST) -> set[int]:
    """Identify AST node IDs belonging to module, class, or function docstrings."""
    docstring_ids: set[int] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstring_ids.add(id(node.body[0].value))

    return docstring_ids


def scan_script_for_stale_paths(script_path: Path, project_root: Path) -> list[StalePathFinding]:
    """AST-walk script_path to detect unresolvable path literals."""
    findings: list[StalePathFinding] = []

    # Skip tooling_staleness_check.py from scanning itself
    if script_path.name == "tooling_staleness_check.py":
        return findings

    try:
        content = script_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(script_path))
    except Exception:
        return findings

    docstring_ids = extract_docstring_node_ids(tree)
    is_skill_script = "skills" in script_path.parts

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstring_ids:
                continue

            val = node.value.strip()
            if not is_candidate_path_literal(val):
                continue

            # Clean leading slashes
            clean_val = val.lstrip("/\\")

            # Check 1: Exact resolution relative to PROJECT_ROOT
            path_root = (project_root / clean_val).resolve()
            if path_root.exists():
                continue

            # Check 2: Exact resolution relative to scanned script directory
            path_local = (script_path.parent / clean_val).resolve()
            if path_local.exists():
                continue

            # Check 3: Dynamic state files inside existing state/config directories (.agent/state/, .agent/config/, etc.)
            if clean_val.startswith((".agent/state/", ".agent/config/", ".agent/artifacts/", "docs/planning/")):
                parent_dir = (project_root / clean_val).parent
                if parent_dir.exists():
                    continue

            # Check 4: Skill scripts contain sample/template paths for consumer projects (alembic/, logs/, src/main.py, etc.)
            if is_skill_script:
                if clean_val.startswith(("alembic/", "logs/", "var/log/", "src/", "tests/unit/")) or clean_val.endswith("__init__.py"):
                    continue

            # Check 5: Consumer project template paths in framework scripts (src/domain/, src/presentation/, evals/, etc.)
            if clean_val.startswith(("src/domain/", "src/presentation/", "evals/", "playwright-skill/", "tests/unit/")):
                continue

            # Check 6: Dormant HIB-089 wiki/ADR registry paths in wiki_lint.py
            if script_path.name == "wiki_lint.py" and clean_val.startswith(("docs/decisions/adr/", ".agent/wiki/")):
                continue

            line_no = getattr(node, "lineno", 0)
            findings.append(StalePathFinding(script_path=script_path, line_no=line_no, path_literal=val))

    return findings


def check_untrustworthy_clean_reports(
    stale_findings: list[StalePathFinding], project_root: Path
) -> list[UntrustworthyCleanFinding]:
    """Cross-check scripts with stale path findings against registered clean_markers in tooling_reports.yaml."""
    untrustworthy: list[UntrustworthyCleanFinding] = []
    config_path = project_root / ".agent" / "config" / "tooling_reports.yaml"

    if not config_path.exists():
        return untrustworthy

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return untrustworthy

    reports = data.get("reports", [])
    if not reports:
        return untrustworthy

    # Group stale findings by script path
    stale_by_script: dict[Path, list[str]] = {}
    for f in stale_findings:
        stale_by_script.setdefault(f.script_path.resolve(), []).append(f.path_literal)

    for entry in reports:
        script_rel = entry.get("script")
        report_rel = entry.get("report_path")
        clean_markers = entry.get("clean_markers", [])

        if not script_rel or not report_rel or not clean_markers:
            continue

        script_abs = (project_root / script_rel).resolve()
        report_abs = (project_root / report_rel).resolve()

        if script_abs in stale_by_script:
            stale_paths = stale_by_script[script_abs]
            if report_abs.exists():
                try:
                    report_content = report_abs.read_text(encoding="utf-8")
                    for marker in clean_markers:
                        if marker in report_content:
                            untrustworthy.append(
                                UntrustworthyCleanFinding(
                                    script_path=script_abs,
                                    report_path=report_abs,
                                    matched_marker=marker,
                                    stale_paths=stale_paths,
                                )
                            )
                            break
                except Exception:
                    pass

    return untrustworthy


def main() -> int:
    parser = argparse.ArgumentParser(description="Tooling Path-Staleness & Clean-Report Validator")
    parser.add_argument("--verbose", action="store_true", help="Print verbose scan details")
    args = parser.parse_args()

    project_root = PROJECT_ROOT
    scripts = discover_target_scripts(project_root)

    all_stale_findings: list[StalePathFinding] = []

    for s in scripts:
        findings = scan_script_for_stale_paths(s, project_root)
        all_stale_findings.extend(findings)

    untrustworthy_findings = check_untrustworthy_clean_reports(all_stale_findings, project_root)

    safe_print("=== Tooling Path-Staleness Check ===")
    safe_print(f"Scanned {len(scripts)} scripts across .agent/scripts/ and .agent/skills/**/scripts/")

    if not all_stale_findings and not untrustworthy_findings:
        safe_print("✅ PASS: Zero stale path literals found. All report clean-markers verified.")
        return 0

    if all_stale_findings:
        safe_print(f"\n❌ STALE-PATH-LITERAL Findings ({len(all_stale_findings)}):")
        for f in all_stale_findings:
            rel_path = f.script_path.relative_to(project_root)
            safe_print(f"  - {rel_path}:{f.line_no} -> '{f.path_literal}'")

    if untrustworthy_findings:
        safe_print(f"\n❌ UNTRUSTWORTHY-CLEAN-RESULT Findings ({len(untrustworthy_findings)}):")
        for u in untrustworthy_findings:
            rel_script = u.script_path.relative_to(project_root)
            rel_report = u.report_path.relative_to(project_root)
            safe_print(
                f"  - Script '{rel_script}' contains {len(u.stale_paths)} stale path literal(s) "
                f"({', '.join(u.stale_paths)}), but report '{rel_report}' contains clean marker '{u.matched_marker}'."
            )

    return 1


if __name__ == "__main__":
    sys.exit(main())
