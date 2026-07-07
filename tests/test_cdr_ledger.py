"""
tests/test_cdr_ledger.py — validation and constraint tests for the CDR ledger.
"""

from __future__ import annotations
import copy
import sys
from pathlib import Path
import pytest
import yaml

# Add harness scripts directory to path for imports
_HARNESS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_HARNESS_ROOT / ".agent" / "scripts"))

from cdr_ledger_validate import validate_ledger


class TestLedgerFileValid:
    """Asserts that the actual tracked ledger file is valid and matches SPEC requirements."""

    def test_actual_ledger_file_is_valid(self):
        ledger_path = _HARNESS_ROOT / ".agent" / "coupling_decisions.yaml"
        assert ledger_path.exists(), f"Ledger file not found at {ledger_path}"

        with open(ledger_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data is not None
        assert data.get("version") == 1
        decisions = data.get("decisions")
        assert isinstance(decisions, list)
        assert len(decisions) > 0

        # Assert no validation errors
        errors = validate_ledger(data)
        assert not errors, f"Ledger validation failed with errors: {errors}"

        # Assert exact structure for the migrated ledger
        assert len(decisions) == 3, f"Expected exactly 3 decisions, got {len(decisions)}"

        d1 = decisions[0]
        assert d1["id"] == "CDR-001"
        assert d1["scope"] == "file"
        assert d1["file"] == "bootstrap/checksums.py"
        assert d1["status"] == "accepted"
        assert d1["archetype"] == "derived"

        d2 = decisions[1]
        assert d2["id"] == "CDR-002"
        assert d2["scope"] == "pair"
        assert d2["files"] == [".agent/scripts/init_session.py", "src/scripts/ai_review.py"]
        assert d2["status"] == "accepted"
        assert d2["archetype"] == "model"

        d3 = decisions[2]
        assert d3["id"] == "CDR-003"
        assert d3["scope"] == "pair"
        assert d3["files"] == ["bootstrap/validate.py", "src/scripts/ai_review.py"]
        assert d3["status"] == "accepted"
        assert d3["archetype"] == "functional"


class TestConstraintLogic:
    """Tests individual constraints (C1-C8) against mock/fixture data."""

    @pytest.fixture
    def base_valid_ledger(self) -> dict:
        return {
            "version": 1,
            "decisions": [
                {
                    "id": "CDR-001",
                    "scope": "file",
                    "file": "some/file.py",
                    "status": "accepted",
                    "archetype": "derived",
                    "rationale": "Valid rationale",
                    "observed": {
                        "co_changes": 3,
                        "p_max": 0.5,
                        "as_of": "2026-07-08"
                    }
                }
            ]
        }

    def test_valid_ledger_passes(self, base_valid_ledger):
        errors = validate_ledger(base_valid_ledger)
        assert not errors

    def test_c1_accepted_requires_rationale(self, base_valid_ledger):
        # Missing rationale
        ledger = copy.deepcopy(base_valid_ledger)
        del ledger["decisions"][0]["rationale"]
        errors = validate_ledger(ledger)
        assert any("missing rationale" in e for e in errors), errors

        # Empty rationale
        ledger = copy.deepcopy(base_valid_ledger)
        ledger["decisions"][0]["rationale"] = "   "
        errors = validate_ledger(ledger)
        assert any("missing rationale" in e for e in errors), errors

    def test_c2_tolerated_requires_valid_reason(self, base_valid_ledger):
        ledger = copy.deepcopy(base_valid_ledger)
        ledger["decisions"][0]["status"] = "tolerated"
        # missing reason
        errors = validate_ledger(ledger)
        assert any("missing reason" in e for e in errors), errors

        # invalid reason
        ledger["decisions"][0]["reason"] = "invalid_reason"
        errors = validate_ledger(ledger)
        assert any("invalid reason" in e for e in errors), errors

        # valid deferred
        ledger["decisions"][0]["reason"] = "deferred"
        errors = validate_ledger(ledger)
        assert not errors

        # valid unevaluated
        ledger["decisions"][0]["reason"] = "unevaluated"
        del ledger["decisions"][0]["rationale"]
        errors = validate_ledger(ledger)
        assert not errors

    def test_c3_tolerated_unevaluated_forbids_rationale(self, base_valid_ledger):
        """C3 check: tolerated/unevaluated MUST NOT have a rationale (anti-confabulation)."""
        ledger = copy.deepcopy(base_valid_ledger)
        ledger["decisions"][0]["status"] = "tolerated"
        ledger["decisions"][0]["reason"] = "unevaluated"
        # Rationale is present
        ledger["decisions"][0]["rationale"] = "Some custom rationale that should not be here"
        
        errors = validate_ledger(ledger)
        assert any("reason 'unevaluated', so 'rationale' must be absent" in e for e in errors), errors

    def test_c4_accepted_requires_archetype(self, base_valid_ledger):
        # Missing archetype
        ledger = copy.deepcopy(base_valid_ledger)
        del ledger["decisions"][0]["archetype"]
        errors = validate_ledger(ledger)
        assert any("missing archetype" in e for e in errors), errors

        # Invalid archetype
        ledger = copy.deepcopy(base_valid_ledger)
        ledger["decisions"][0]["archetype"] = "invalid_archetype"
        errors = validate_ledger(ledger)
        assert any("invalid archetype" in e for e in errors), errors

    def test_c5_pair_scope_files_constraints(self, base_valid_ledger):
        ledger = copy.deepcopy(base_valid_ledger)
        ledger["decisions"][0]["scope"] = "pair"
        del ledger["decisions"][0]["file"]

        # Missing files
        errors = validate_ledger(ledger)
        assert any("files' list is missing" in e for e in errors), errors

        # Wrong number of files (1)
        ledger["decisions"][0]["files"] = ["a.py"]
        errors = validate_ledger(ledger)
        assert any("files' list must have exactly 2 entries" in e for e in errors), errors

        # Wrong type
        ledger["decisions"][0]["files"] = "not a list"
        errors = validate_ledger(ledger)
        assert any("files' must be a list" in e for e in errors), errors

        # Unsorted files
        ledger["decisions"][0]["files"] = ["b.py", "a.py"]
        errors = validate_ledger(ledger)
        assert any("files' must be sorted lexicographically" in e for e in errors), errors

        # Equal files (duplicate)
        ledger["decisions"][0]["files"] = ["a.py", "a.py"]
        errors = validate_ledger(ledger)
        assert any("files' must be sorted lexicographically" in e for e in errors), errors

        # Correct sorted files
        ledger["decisions"][0]["files"] = ["a.py", "b.py"]
        errors = validate_ledger(ledger)
        assert not errors

    def test_c6_scope_mismatch_mutual_exclusion(self, base_valid_ledger):
        # scope: file with files list present
        ledger = copy.deepcopy(base_valid_ledger)
        ledger["decisions"][0]["files"] = ["a.py", "b.py"]
        errors = validate_ledger(ledger)
        assert any("files' list is present" in e for e in errors), errors

        # scope: pair with file path present
        ledger = copy.deepcopy(base_valid_ledger)
        ledger["decisions"][0]["scope"] = "pair"
        ledger["decisions"][0]["files"] = ["a.py", "b.py"]
        # file remains present
        errors = validate_ledger(ledger)
        assert any("file' path is present" in e for e in errors), errors

    def test_c7_id_uniqueness_and_format(self, base_valid_ledger):
        # Duplicate ID
        ledger = {
            "version": 1,
            "decisions": [
                copy.deepcopy(base_valid_ledger["decisions"][0]),
                copy.deepcopy(base_valid_ledger["decisions"][0])
            ]
        }
        errors = validate_ledger(ledger)
        assert any("Duplicate decision ID" in e for e in errors), errors

        # Invalid ID format
        ledger = copy.deepcopy(base_valid_ledger)
        ledger["decisions"][0]["id"] = "CDR-1"
        errors = validate_ledger(ledger)
        assert any("does not match format CDR-\\d{3}" in e for e in errors), errors

        ledger["decisions"][0]["id"] = "ABC-001"
        errors = validate_ledger(ledger)
        assert any("does not match format CDR-\\d{3}" in e for e in errors), errors

    def test_c8_resolved_requires_resolved_by(self, base_valid_ledger):
        ledger = copy.deepcopy(base_valid_ledger)
        ledger["decisions"][0]["status"] = "resolved"
        
        # missing resolved_by
        errors = validate_ledger(ledger)
        assert any("missing 'resolved_by'" in e for e in errors), errors

        # present resolved_by
        ledger["decisions"][0]["resolved_by"] = "Fixed in commit 1234"
        errors = validate_ledger(ledger)
        assert not errors
