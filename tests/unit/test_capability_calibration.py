import pytest
import tempfile
import json
from pathlib import Path
from src.scripts.capability_calibration import (
    load_calibration,
    save_calibration,
    update_calibration_rebuttal,
    get_calibrated_weight
)

def test_load_calibration_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        data = load_calibration(tmp_path)
        assert data == {"schema_version": "1.0", "capabilities": {}}

def test_save_and_load_calibration():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        cal_data = {
            "schema_version": "1.0",
            "capabilities": {
                "BRANCH_ISOLATION": {"tp": 3, "fp": 2, "weight": 1.1}
            }
        }
        save_calibration(cal_data, tmp_path)
        
        loaded = load_calibration(tmp_path)
        assert loaded["capabilities"]["BRANCH_ISOLATION"]["tp"] == 3
        assert loaded["capabilities"]["BRANCH_ISOLATION"]["fp"] == 2
        assert loaded["capabilities"]["BRANCH_ISOLATION"]["weight"] == 1.1

def test_get_calibrated_weight():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Test Default
        w = get_calibrated_weight("BRANCH_ISOLATION", tmp_path)
        assert w == 1.0
        
        # Test saved weight
        cal_data = {
            "schema_version": "1.0",
            "capabilities": {
                "BRANCH_ISOLATION": {"tp": 2, "fp": 1, "weight": 1.3}
            }
        }
        save_calibration(cal_data, tmp_path)
        w = get_calibrated_weight("BRANCH_ISOLATION", tmp_path)
        assert w == 1.3
        
        # Test overrides
        config = {
            "capability_calibration": {
                "enabled": True,
                "overrides": {
                    "BRANCH_ISOLATION": 0.8
                }
            }
        }
        w = get_calibrated_weight("BRANCH_ISOLATION", tmp_path, config)
        assert w == 0.8
        
        # Test disabled
        config_disabled = {
            "capability_calibration": {
                "enabled": False
            }
        }
        w = get_calibrated_weight("BRANCH_ISOLATION", tmp_path, config_disabled)
        assert w == 1.0

def test_update_calibration_rebuttal():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Initial cold start prior (tp=1, fp=1, weight=1.0)
        # Rebuttal accepted -> fp += 1, weight *= 0.9
        update_calibration_rebuttal("TEST_COVERAGE", "REBUTTAL_ACCEPTED", tmp_path)
        data = load_calibration(tmp_path)
        cap = data["capabilities"]["TEST_COVERAGE"]
        assert cap["tp"] == 1
        assert cap["fp"] == 2
        assert pytest.approx(cap["weight"]) == 0.9
        
        # Rebuttal rejected -> tp += 1, weight *= 1.05
        update_calibration_rebuttal("TEST_COVERAGE", "REBUTTAL_REJECTED", tmp_path)
        data = load_calibration(tmp_path)
        cap = data["capabilities"]["TEST_COVERAGE"]
        assert cap["tp"] == 2
        assert cap["fp"] == 2
        assert pytest.approx(cap["weight"]) == 0.945

        # Check clamping lower bound 0.5
        for _ in range(20):
            update_calibration_rebuttal("TEST_COVERAGE", "REBUTTAL_ACCEPTED", tmp_path)
        data = load_calibration(tmp_path)
        assert data["capabilities"]["TEST_COVERAGE"]["weight"] == 0.5


def test_update_calibration_rebuttal_remediated_does_not_pollute_fp():
    """Scenario 4 (HIB-049): REMEDIATED rebuttal type does not treat rebuttal as false positive or reduce weight."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        update_calibration_rebuttal("SECURITY_CHECK", "REBUTTAL_ACCEPTED", tmp_path, rebuttal_type="REMEDIATED")
        data = load_calibration(tmp_path)
        cap = data["capabilities"]["SECURITY_CHECK"]
        assert cap["tp"] == 2
        assert cap["fp"] == 1
        assert pytest.approx(cap["weight"]) == 1.05


        # Check clamping upper bound 1.5
        for _ in range(40):
            update_calibration_rebuttal("TEST_COVERAGE", "REBUTTAL_REJECTED", tmp_path)
        data = load_calibration(tmp_path)
        assert data["capabilities"]["TEST_COVERAGE"]["weight"] == 1.5
