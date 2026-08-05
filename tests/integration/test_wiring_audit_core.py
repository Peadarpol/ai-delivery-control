import ast
import os
import sys
import pytest
from pathlib import Path

# Add .agent/scripts to sys.path to import wiring_audit_core
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_SCRIPTS_DIR = PROJECT_ROOT / ".agent" / "scripts"
if str(AGENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_SCRIPTS_DIR))

from wiring_audit_core import (
    check_keyword_arg,
    check_dict_key_access,
    validate_manifest
)

FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "wiring_audit"

def get_ast(fixture_name: str) -> ast.AST:
    fixture_path = FIXTURES_DIR / fixture_name
    with open(fixture_path, "r", encoding="utf-8") as f:
        return ast.parse(f.read(), filename=str(fixture_path))

class TestWiringAuditCore:
    def test_pre_hib_080_reconstruction_is_not_wired(self):
        """Scenario 3: Retroactive test confirming pre-HIB-080 missing kwargs are NOT-WIRED."""
        tree = get_ast("synthetic_pre_hib_080.py")
        result_baseline = check_keyword_arg(tree, "disposition", "baseline")
        result_touched_files = check_keyword_arg(tree, "disposition", "touched_files")
        
        assert result_baseline == "NOT-WIRED"
        assert result_touched_files == "NOT-WIRED"

    def test_vacuous_keyword_fixture_is_partially_wired(self):
        """Scenario 4b: Vacuous keyword arguments correctly flag as PARTIALLY-WIRED."""
        tree = get_ast("synthetic_vacuous_fixture.py")
        result_baseline = check_keyword_arg(tree, "disposition", "baseline")
        result_touched_files = check_keyword_arg(tree, "disposition", "touched_files")
        
        assert result_baseline == "PARTIALLY-WIRED"
        assert result_touched_files == "PARTIALLY-WIRED"

    def test_vacuous_dict_fixture_is_partially_wired(self):
        """Scenario 4b (Dict): Dict key access missing a non-vacuous write flags as PARTIALLY-WIRED."""
        tree = get_ast("synthetic_vacuous_dict.py")
        result = check_dict_key_access(tree, "sdata", "token_usage")
        
        assert result == "PARTIALLY-WIRED"

    def test_malformed_manifest_raises_system_exit(self, capsys):
        """Scenario 4c: A manifest declaring an empty consumers list fails loud and aborts."""
        manifest_path = FIXTURES_DIR / "wiring_consumers_malformed.yaml"
        
        with pytest.raises(SystemExit) as excinfo:
            validate_manifest(str(manifest_path))
            
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "ERROR: Artifact 'baseline.json' has zero consumers." in captured.out
