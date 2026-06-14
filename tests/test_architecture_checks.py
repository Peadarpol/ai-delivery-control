import os
import sys
import pytest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_ROOT / ".agent" / "skills" / "universal" / "senior-architect" / "scripts"))

from architecture_checks import check_adr_decision_blocks

def test_check_adr_decision_blocks_advisory_missing(tmp_path):
    docs_dir = tmp_path / "docs" / "adr"
    docs_dir.mkdir(parents=True)
    adr_file = docs_dir / "ADR-001.md"
    adr_file.write_text("## Context\nSome content without decision block.", encoding="utf-8")
    
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        advisories = check_adr_decision_blocks({})
        assert len(advisories) == 1
        assert "Missing or incomplete 'Decision Block' section" in advisories[0]
    finally:
        os.chdir(old_cwd)

def test_check_adr_decision_blocks_advisory_present(tmp_path):
    docs_dir = tmp_path / "docs" / "adr"
    docs_dir.mkdir(parents=True)
    adr_file = docs_dir / "ADR-002.md"
    adr_file.write_text("## Context\n\n## Decision Block\n**Tradeoffs Navigated:**\n**Failure Modes Exposed:**\n", encoding="utf-8")
    
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        advisories = check_adr_decision_blocks({})
        assert len(advisories) == 0
    finally:
        os.chdir(old_cwd)
