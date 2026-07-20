"""
Unit tests for route_decision.py classification and config override mechanics (T1-L-21).
"""

from __future__ import annotations

import sys
import unittest.mock
from pathlib import Path

# Add src/scripts to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYS_SCRIPTS = PROJECT_ROOT / "src" / "scripts"

if str(SYS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SYS_SCRIPTS))

import route_decision


def test_get_active_ai_review():
    """Verify _get_active_ai_review returns None or module wrapper cleanly."""
    res = route_decision._get_active_ai_review()
    # When running under pytest without ai_review active in stack, returns sys.modules entry or None
    assert res is None or hasattr(res, "__getattr__") or hasattr(res, "PROJECT_ROOT")


def test_load_high_risk_patterns_override_defaults():
    """Verify _load_high_risk_patterns respects override_defaults flag."""
    hrp_dict = {
        "override_defaults": True,
        "paths": ["*/custom_secret/*"],
        "filenames": ["secret.py"],
        "adr_domains": ["custom_domain"],
    }
    with unittest.mock.patch("route_decision.get_harness_config", return_value=hrp_dict):
        cfg = route_decision._load_high_risk_patterns()
        assert cfg["override_defaults"] is True
        assert "*/custom_secret/*" in cfg["paths"]
        assert "secret.py" in cfg["filenames"]


def test_classify_commit_risk_override_defaults_empty_fails_closed(caplog):
    """Verify override_defaults=True with empty pattern set fails closed to elevated review."""
    mock_config = {
        "override_defaults": True,
        "paths": [],
        "filenames": [],
        "adr_domains": [],
    }
    with unittest.mock.patch("route_decision._load_high_risk_patterns", return_value=mock_config):
        is_high, patterns = route_decision.classify_commit_risk(["src/normal.py"], [])
        assert is_high is True
        assert "CRITICAL_WARNING_ZERO_HIGH_RISK_PATTERNS" in patterns
