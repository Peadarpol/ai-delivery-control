"""
tests/integration/test_tooling_staleness.py — Integration test for tooling_staleness_check.py (Tier 4, D2)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
agent_scripts = PROJECT_ROOT / ".agent" / "scripts"
if str(agent_scripts) not in sys.path:
    sys.path.insert(0, str(agent_scripts))

from tooling_staleness_check import (
    discover_target_scripts,
    scan_script_for_stale_paths,
    check_untrustworthy_clean_reports,
    main as scanner_main,
)


def test_tooling_staleness_check_clean_baseline():
    """Verify that current codebase passes tooling_staleness_check cleanly."""
    scripts = discover_target_scripts(PROJECT_ROOT)
    assert len(scripts) > 0, "No target scripts discovered"

    all_stale = []
    for s in scripts:
        all_stale.extend(scan_script_for_stale_paths(s, PROJECT_ROOT))

    untrustworthy = check_untrustworthy_clean_reports(all_stale, PROJECT_ROOT)

    assert len(all_stale) == 0, f"Unexpected stale path findings in clean codebase: {all_stale}"
    assert len(untrustworthy) == 0, f"Unexpected untrustworthy clean findings: {untrustworthy}"
