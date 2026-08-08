#!/usr/bin/env python3
"""
.agent/scripts/coverage_completeness_check.py — Coverage-Completeness Validator (Tier 4, D4b)

Parses docs/planning/LOOP_INVENTORY.md tolerantly to perform:
- D4b: Coverage-completeness cross-check (VERIFIED-WORKING loops with no co-located test)
- D4a: Retired orphaned-producer scan (retained for historical context; output is retired and replaced by .agent/workflows/loop-audit.md)
"""

from __future__ import annotations

import argparse
import ast
from datetime import date
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

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

PROJECT_ROOT = _find_project_root()
agent_scripts = PROJECT_ROOT / ".agent" / "scripts"
if str(agent_scripts) not in sys.path:
    sys.path.insert(0, str(agent_scripts))

# Reuse wiring_audit_core AST function_call check directly
from wiring_audit_core import check_function_call


def safe_print(*args, **kwargs):
    """Safe print helper preventing UnicodeEncodeError on CP1252 Windows consoles."""
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    file = kwargs.get("file", sys.stdout)
    text = sep.join(str(arg) for arg in args) + end
    encoding = getattr(file, "encoding", "utf-8") or "utf-8"
    file.write(text.encode(encoding, errors="replace").decode(encoding))


@dataclass
class ParsedLoop:
    loop_id: str
    status: str
    producer_raw: str | None
    consumer_raw: str | None
    producer_ident: str | None
    consumer_ident: str | None
    has_producer_none: bool
    has_consumer_none: bool
    is_ambiguous: bool


@dataclass
class D4aFinding:
    loop_id: str
    producer_ident: str | None
    consumer_ident: str | None
    reason: str


@dataclass
class D4bFinding:
    loop_id: str
    producer_ident: str
    consumer_ident: str
    status: str  # "CO-LOCATED-TEST-FOUND" or "NO-COLOCATED-TEST-FOUND"
    co_located_tests: list[Path]


def extract_identifier(text: str | None) -> tuple[str | None, bool, bool]:
    """
    Extract script/module identifier from raw Producer or Consumer text field.
    Returns: (identifier, is_explicit_none, is_unparseable)
    """
    if not text:
        return None, False, True

    cleaned = text.strip()
    
    # Explicit "none found" or "no consumer" signals
    if any(phrase in cleaned.lower() for phrase in [
        "none found", "no consumer", "no automated consumer", "no producer found", "no producer"
    ]):
        return None, True, False

    # Check for backticked path or function name
    bt_match = re.search(r"`([^`]+)`", cleaned)
    if bt_match:
        val = bt_match.group(1).strip()
        # Handle "same file" if matched inside backticks
        if val.lower() == "same file":
            return "same_file", False, False
        # Extract filename / module stem if path-like or extension present
        if "/" in val or "\\" in val or val.endswith((".py", ".md", ".json", ".yaml", ".yml")):
            stem = Path(val).stem
            return stem, False, False
        # If it's a function call like report_rebuttals() or record_decision()
        func_name = val.split("(")[0].strip()
        if func_name:
            return func_name, False, False

    if "same file" in cleaned.lower():
        return "same_file", False, False

    # Cannot confidently parse
    return None, False, True


def parse_loop_inventory(inventory_path: Path) -> list[ParsedLoop]:
    """Parse docs/planning/LOOP_INVENTORY.md tolerantly into ParsedLoop objects."""
    if not inventory_path.exists():
        safe_print(f"ERROR: Inventory file missing at {inventory_path}")
        return []

    content = inventory_path.read_text(encoding="utf-8")
    raw_sections = re.split(r"^##\s+(LOOP-\d+.*?)$", content, flags=re.MULTILINE)

    parsed_loops: list[ParsedLoop] = []

    for i in range(1, len(raw_sections), 2):
        header = raw_sections[i].strip()
        body = raw_sections[i + 1].strip()

        loop_id_m = re.search(r"^(LOOP-\d+)", header)
        loop_id = loop_id_m.group(1) if loop_id_m else "UNKNOWN"

        status_m = re.search(r"\*\*Status\*\*:\s*`?([^`\n\r]+)`?", body)
        status = status_m.group(1).strip() if status_m else "UNKNOWN"

        prod_m = re.search(r"\*\*Producer\*\*:\s*(.*)", body, re.IGNORECASE)
        cons_m = re.search(r"\*\*Consumer\*\*:\s*(.*)", body, re.IGNORECASE)

        prod_raw = prod_m.group(1).strip() if prod_m else None
        cons_raw = cons_m.group(1).strip() if cons_m else None

        prod_ident, prod_none, prod_unparseable = extract_identifier(prod_raw)
        cons_ident, cons_none, cons_unparseable = extract_identifier(cons_raw)

        # Handle "same file" consumer reference
        if cons_ident == "same_file":
            cons_ident = prod_ident
            cons_none = False
            cons_unparseable = False if prod_ident else True

        # Determine if entry is PARSE-AMBIGUOUS
        is_ambiguous = False
        if not prod_none and (prod_unparseable or not prod_ident):
            is_ambiguous = True
        if not cons_none and (cons_unparseable or not cons_ident):
            is_ambiguous = True

        parsed_loops.append(
            ParsedLoop(
                loop_id=loop_id,
                status=status,
                producer_raw=prod_raw,
                consumer_raw=cons_raw,
                producer_ident=prod_ident,
                consumer_ident=cons_ident,
                has_producer_none=prod_none,
                has_consumer_none=cons_none,
                is_ambiguous=is_ambiguous,
            )
        )

    return parsed_loops


def find_workspace_python_files(project_root: Path) -> list[Path]:
    """Find source Python scripts under .agent/scripts/, src/, .agent/skills/."""
    py_files: list[Path] = []
    for sub in [project_root / ".agent" / "scripts", project_root / "src", project_root / ".agent" / "skills"]:
        if sub.exists():
            for p in sub.rglob("*.py"):
                if p.is_file():
                    py_files.append(p)
    return sorted(list(set(py_files)))


def find_test_python_files(project_root: Path) -> list[Path]:
    """Find test Python scripts under tests/, tests/integration/, tests/e2e/."""
    test_files: list[Path] = []
    for sub in ["tests", "tests/integration", "tests/e2e"]:
        tp = project_root / sub
        if tp.exists():
            for p in tp.rglob("*.py"):
                if p.is_file():
                    test_files.append(p)
    return sorted(list(set(test_files)))


def file_references_identifier(file_path: Path, ident: str) -> bool:
    """AST reference search checking if file_path references ident via import, call, attribute, or name."""
    if not ident:
        return False
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return False

    # Reused check_function_call from wiring_audit_core.py
    if check_function_call(tree, ident) == "WIRED":
        return True

    ident_stem = Path(ident).stem
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if ident_stem in alias.name or (alias.asname and ident_stem in alias.asname):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and ident_stem in node.module:
                return True
            for alias in node.names:
                if ident_stem in alias.name or (alias.asname and ident_stem in alias.asname):
                    return True
        elif isinstance(node, ast.Name):
            if node.id == ident_stem:
                return True
        elif isinstance(node, ast.Attribute):
            if node.attr == ident_stem:
                return True

    return False


def run_d4a_orphaned_producer_scan(loops: list[ParsedLoop], project_root: Path) -> list[D4aFinding]:
    """D4a: Identify orphaned producers with no consumer or no external references to consumer."""
    findings: list[D4aFinding] = []
    source_files = find_workspace_python_files(project_root)

    for l in loops:
        if l.is_ambiguous or l.has_producer_none:
            continue

        # Case 1: Explicit consumer: none found
        if l.has_consumer_none:
            findings.append(
                D4aFinding(
                    loop_id=l.loop_id,
                    producer_ident=l.producer_ident,
                    consumer_ident=None,
                    reason="Explicit consumer: none found",
                )
            )
            continue

        # Case 2: Consumer exists but has zero external references in workspace Python scripts
        cons_ident = l.consumer_ident
        prod_ident = l.producer_ident

        if cons_ident:
            external_refs = []
            for sf in source_files:
                if prod_ident and prod_ident in sf.name:
                    continue  # skip producer file itself
                if file_references_identifier(sf, cons_ident):
                    external_refs.append(sf)

            if not external_refs:
                findings.append(
                    D4aFinding(
                        loop_id=l.loop_id,
                        producer_ident=prod_ident,
                        consumer_ident=cons_ident,
                        reason=f"Zero external code references found for consumer '{cons_ident}'",
                    )
                )

    return findings


def run_d4b_coverage_completeness_check(loops: list[ParsedLoop], project_root: Path) -> list[D4bFinding]:
    """D4b: Search test suite for co-located test files referencing both producer and consumer for VERIFIED-WORKING loops."""
    findings: list[D4bFinding] = []
    test_files = find_test_python_files(project_root)

    verified_loops = [l for l in loops if "VERIFIED-WORKING" in l.status and not l.is_ambiguous]

    for l in verified_loops:
        prod_ident = l.producer_ident
        cons_ident = l.consumer_ident

        if not prod_ident or not cons_ident:
            continue

        co_located: list[Path] = []
        for tf in test_files:
            has_prod = file_references_identifier(tf, prod_ident)
            has_cons = file_references_identifier(tf, cons_ident)
            if has_prod and has_cons:
                co_located.append(tf)

        if co_located:
            findings.append(
                D4bFinding(
                    loop_id=l.loop_id,
                    producer_ident=prod_ident,
                    consumer_ident=cons_ident,
                    status="CO-LOCATED-TEST-FOUND",
                    co_located_tests=co_located,
                )
            )
        else:
            findings.append(
                D4bFinding(
                    loop_id=l.loop_id,
                    producer_ident=prod_ident,
                    consumer_ident=cons_ident,
                    status="NO-COLOCATED-TEST-FOUND",
                    co_located_tests=[],
                )
            )

    return findings


def build_phase_d_report_section(
    loops: list[ParsedLoop],
    ambiguous_loops: list[ParsedLoop],
    d4a_findings: list[D4aFinding],
    d4b_findings: list[D4bFinding],
) -> str:
    """Format Phase D section text for .agent/state/loop_closure_report.md."""
    lines = [
        "\n---",
        "\n## Phase D: Producer/Consumer Contracts, Tooling Staleness, and Coverage Completeness",
        f"**Run Date**: {date.today().isoformat()}",
        f"**Summary**: Parsed {len(loops)} loops from LOOP_INVENTORY.md.",
        f"- **PARSE-AMBIGUOUS**: {len(ambiguous_loops)}",
        f"- **D4a Orphaned-Producer Findings (RETIRED)**: {len(d4a_findings)}",
        f"- **D4b Coverage-Completeness Findings**: {len(d4b_findings)}",
        "",
    ]

    if ambiguous_loops:
        lines.append("### ⚠️ PARSE-AMBIGUOUS Inventory Entries")
        for a in ambiguous_loops:
            lines.append(f"- **{a.loop_id}** (`Status: {a.status}`): Unparseable or uninvestigated producer/consumer field")
        lines.append("")

    lines.append("⚠️ D4a RETIRED — DO NOT TREAT AS SIGNAL. The 9 findings below were the empirical evidence that led to D4a's retirement, not confirmed defects. Direct trace confirmed at least LOOP-001 is a false positive — genuinely wired via file-based coupling (Path().glob()) that D4a's AST reference search cannot detect by design. See SPEC-loop-closure-verification.md §7 and v1.17 changelog for the full finding. Retained here as the historical record that motivated retirement, not as a current defect list.\n")
    lines.append("### ❌ D4a Orphaned-Producer Findings")
    for f in d4a_findings:
        prod_str = f"Producer: `{f.producer_ident}`" if f.producer_ident else "No producer"
        cons_str = f"Consumer: `{f.consumer_ident}`" if f.consumer_ident else "Consumer: none found"
        lines.append(f"- **{f.loop_id}** ({prod_str} -> {cons_str}): {f.reason}")
    lines.append("")

    lines.append("### 📊 D4b Coverage-Completeness Results (VERIFIED-WORKING Loops)")
    for b in d4b_findings:
        if b.status == "CO-LOCATED-TEST-FOUND":
            test_list = ", ".join(f"`{t.name}`" for t in b.co_located_tests)
            lines.append(f"- ✅ **{b.loop_id}** (`{b.producer_ident}` <-> `{b.consumer_ident}`): `CO-LOCATED-TEST-FOUND` in {test_list}")
        else:
            lines.append(f"- ❌ **{b.loop_id}** (`{b.producer_ident}` <-> `{b.consumer_ident}`): `NO-COLOCATED-TEST-FOUND` — zero co-located tests found")

    return "\n".join(lines)


def update_loop_closure_report(
    loops: list[ParsedLoop],
    ambiguous_loops: list[ParsedLoop],
    d4a_findings: list[D4aFinding],
    d4b_findings: list[D4bFinding],
    project_root: Path,
):
    """Append or replace Phase D section in .agent/state/loop_closure_report.md."""
    report_path = project_root / ".agent" / "state" / "loop_closure_report.md"
    if not report_path.exists():
        return

    content = report_path.read_text(encoding="utf-8")
    marker = "## Phase D: Producer/Consumer Contracts"

    phase_d_text = build_phase_d_report_section(loops, ambiguous_loops, d4a_findings, d4b_findings)

    if marker in content:
        content = content.split(marker)[0].rstrip() + "\n" + phase_d_text
    else:
        content = content.rstrip() + "\n" + phase_d_text

    report_path.write_text(content, encoding="utf-8")
    safe_print(f"✅ Updated {report_path.relative_to(project_root)} with Phase D findings.")


def main() -> int:
    parser = argparse.ArgumentParser(description="D4 Coverage-Completeness & Orphaned-Producer Validator")
    parser.add_argument("--write-report", action="store_true", help="Update .agent/state/loop_closure_report.md")
    args = parser.parse_args()

    project_root = PROJECT_ROOT
    inventory_path = project_root / "docs" / "planning" / "LOOP_INVENTORY.md"

    loops = parse_loop_inventory(inventory_path)

    ambiguous_loops = [l for l in loops if l.is_ambiguous]
    d4a_findings = run_d4a_orphaned_producer_scan(loops, project_root)
    d4b_findings = run_d4b_coverage_completeness_check(loops, project_root)

    safe_print("=== Tooling D4 Coverage-Completeness Check ===")
    safe_print(f"Total loops parsed: {len(loops)}")
    safe_print(f"PARSE-AMBIGUOUS entries: {len(ambiguous_loops)}")
    safe_print(f"D4a Orphaned-Producer findings: {len(d4a_findings)}")
    safe_print(f"D4b Coverage-Completeness findings: {len(d4b_findings)}")

    if ambiguous_loops:
        safe_print(f"\n⚠️ PARSE-AMBIGUOUS Entries ({len(ambiguous_loops)}):")
        for a in ambiguous_loops:
            safe_print(f"  - {a.loop_id} (Status: {a.status})")

    safe_print(f"\n⚠️ D4a Orphaned-Producer Findings [RETIRED - DO NOT TREAT AS SIGNAL] ({len(d4a_findings)}):")
    for f in d4a_findings:
        safe_print(f"  - {f.loop_id} [Producer: {f.producer_ident}] -> {f.reason}")

    safe_print(f"\n📊 D4b Coverage-Completeness Results ({len(d4b_findings)}):")
    for b in d4b_findings:
        if b.status == "CO-LOCATED-TEST-FOUND":
            rel_tests = [str(t.relative_to(project_root)) for t in b.co_located_tests]
            safe_print(f"  - ✅ {b.loop_id} ({b.producer_ident} <-> {b.consumer_ident}): {b.status} in {rel_tests}")
        else:
            safe_print(f"  - ❌ {b.loop_id} ({b.producer_ident} <-> {b.consumer_ident}): {b.status}")

    if args.write_report:
        update_loop_closure_report(loops, ambiguous_loops, d4a_findings, d4b_findings, project_root)

    return 0


if __name__ == "__main__":
    sys.exit(main())
