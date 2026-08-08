"""
tests/integration/test_coverage_completeness.py — Integration test for coverage_completeness_check.py (Tier 4, D4)
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
agent_scripts = PROJECT_ROOT / ".agent" / "scripts"
if str(agent_scripts) not in sys.path:
    sys.path.insert(0, str(agent_scripts))

from coverage_completeness_check import (
    parse_loop_inventory,
    run_d4a_orphaned_producer_scan,
    run_d4b_coverage_completeness_check,
)


def test_d4a_self_test_known_cases():
    """Verify D4a self-test cases: LOOP-003, LOOP-012, LOOP-018 flagged; LOOP-015 not flagged."""
    inventory_path = PROJECT_ROOT / "docs" / "planning" / "LOOP_INVENTORY.md"
    loops = parse_loop_inventory(inventory_path)
    assert len(loops) > 0, "No loops parsed from inventory"

    d4a_findings = run_d4a_orphaned_producer_scan(loops, PROJECT_ROOT)
    orphaned_ids = {f.loop_id for f in d4a_findings}

    # LOOP-003, LOOP-012, LOOP-018 MUST be flagged
    assert "LOOP-003" in orphaned_ids, "LOOP-003 was not flagged as ORPHANED-PRODUCER"
    assert "LOOP-012" in orphaned_ids, "LOOP-012 was not flagged as ORPHANED-PRODUCER"
    assert "LOOP-018" in orphaned_ids, "LOOP-018 was not flagged as ORPHANED-PRODUCER"

    # LOOP-015 MUST NOT be flagged as ORPHANED-PRODUCER (consumer-only loop)
    assert "LOOP-015" not in orphaned_ids, "LOOP-015 was incorrectly flagged as ORPHANED-PRODUCER"


def test_d4b_self_test_verified_working_cases():
    """Verify D4b self-test cases against VERIFIED-WORKING loops (LOOP-002, LOOP-016, LOOP-017)."""
    inventory_path = PROJECT_ROOT / "docs" / "planning" / "LOOP_INVENTORY.md"
    loops = parse_loop_inventory(inventory_path)

    d4b_findings = run_d4b_coverage_completeness_check(loops, PROJECT_ROOT)
    d4b_map = {f.loop_id: f for f in d4b_findings}

    assert "LOOP-002" in d4b_map, "LOOP-002 missing from D4b findings"
    assert "LOOP-016" in d4b_map, "LOOP-016 missing from D4b findings"
    assert "LOOP-017" in d4b_map, "LOOP-017 missing from D4b findings"

    # LOOP-017 MUST report NO-COLOCATED-TEST-FOUND (true negative)
    assert d4b_map["LOOP-017"].status == "NO-COLOCATED-TEST-FOUND"
