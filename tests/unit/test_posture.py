#!/usr/bin/env python3
"""
tests/unit/test_posture.py — Characterization tests for posture engine (T1-G-18 Phase P1)
"""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "scripts"))
import pytest

from posture import (
    Disposition,
    INVARIANT_FLOOR_REGISTRY,
    Outcome,
    disposition,
    is_invariant_pinned,
    load_enforcement_config,
)


def test_is_invariant_pinned():
    """Verify invariant floor rule identification."""
    assert is_invariant_pinned("H-01") is True
    assert is_invariant_pinned("h-05") is True
    assert is_invariant_pinned("H-09") is True
    assert is_invariant_pinned("H_SERIES") is True
    assert is_invariant_pinned("LAYER_BOUNDARY") is False
    assert is_invariant_pinned("HIGH_COUPLING") is False


def test_load_enforcement_config_defaults(tmp_path):
    """Verify default strict posture resolution when config is missing."""
    cfg = load_enforcement_config(tmp_path)
    assert cfg["posture"] == "strict"
    assert cfg["effective_posture"] == "strict"
    assert cfg["expired"] is False


def test_load_enforcement_config_observe_expired(tmp_path):
    """Verify observe posture with past expiry date resolves to ratchet."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    config_file = agent_dir / "config.yaml"
    config_file.write_text("""
enforcement:
  posture: observe
  observe_expires: "2020-01-01T00:00:00Z"
""", encoding="utf-8")

    cfg = load_enforcement_config(tmp_path)
    assert cfg["posture"] == "observe"
    assert cfg["effective_posture"] == "ratchet"
    assert cfg["expired"] is True


def test_load_enforcement_config_observe_valid(tmp_path):
    """Verify observe posture with future expiry date remains observe."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    config_file = agent_dir / "config.yaml"
    future_date = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).isoformat()
    config_file.write_text(f"""
enforcement:
  posture: observe
  observe_expires: "{future_date}"
""", encoding="utf-8")

    cfg = load_enforcement_config(tmp_path)
    assert cfg["posture"] == "observe"
    assert cfg["effective_posture"] == "observe"
    assert cfg["expired"] is False


def test_disposition_invariant_floor_blocks_always():
    """Verify invariant floor rules BLOCK under observe and ratchet postures."""
    # Observe posture
    disp = disposition("H-03", "FAIL", posture="observe")
    assert disp.outcome == Outcome.BLOCK
    assert disp.invariant_pinned is True

    # Ratchet posture
    disp_ratchet = disposition("H-07", "FAIL", posture="ratchet")
    assert disp_ratchet.outcome == Outcome.BLOCK
    assert disp_ratchet.invariant_pinned is True

    # Override attempt on pinned rule
    disp_override = disposition("H-01", "FAIL", posture="observe", rule_overrides={"H-01": "off"})
    assert disp_override.outcome == Outcome.BLOCK
    assert disp_override.invariant_pinned is True


def test_disposition_strict_posture():
    """Verify strict posture disposition rules."""
    # FAIL severity -> BLOCK
    disp_fail = disposition("LAYER_BOUNDARY", "FAIL", posture="strict")
    assert disp_fail.outcome == Outcome.BLOCK

    # WARN severity -> ADVISORY
    disp_warn = disposition("HIGH_COUPLING", "WARN", posture="strict")
    assert disp_warn.outcome == Outcome.ADVISORY


def test_disposition_observe_posture():
    """Verify observe posture downgrades non-pinned FAIL findings to ADVISORY."""
    disp = disposition("LAYER_BOUNDARY", "FAIL", posture="observe")
    assert disp.outcome == Outcome.ADVISORY
    assert "observe posture: downgraded to ADVISORY" in disp.chain[-1]


def test_disposition_rule_overrides():
    """Verify per-rule config overrides."""
    overrides = {"HIGH_COUPLING": "block", "LAYER_BOUNDARY": "warn"}
    
    # Non-pinned rule upgraded to BLOCK via override
    disp_up = disposition("HIGH_COUPLING", "WARN", posture="strict", rule_overrides=overrides)
    assert disp_up.outcome == Outcome.BLOCK

    # Non-pinned rule downgraded to ADVISORY via override
    disp_down = disposition("LAYER_BOUNDARY", "FAIL", posture="strict", rule_overrides=overrides)
    assert disp_down.outcome == Outcome.ADVISORY


def test_disposition_ratchet_baseline_grandfathering():
    """Verify baseline grandfathering in ratchet posture."""
    baseline = {
        "entries": [
            {
                "rule": "LAYER_BOUNDARY",
                "file": "src/legacy/old_module.py",
                "region_sha256": "abc123hash"
            }
        ]
    }

    # Matching file, rule, and hash -> GRANDFATHERED
    disp = disposition(
        rule="LAYER_BOUNDARY",
        severity="FAIL",
        file_path="src/legacy/old_module.py",
        region_sha256="abc123hash",
        posture="ratchet",
        baseline=baseline,
        touched_files=set()
    )
    assert disp.outcome == Outcome.GRANDFATHERED

    # Touched file -> BLOCK (lapse condition)
    disp_touched = disposition(
        rule="LAYER_BOUNDARY",
        severity="FAIL",
        file_path="src/legacy/old_module.py",
        region_sha256="abc123hash",
        posture="ratchet",
        baseline=baseline,
        touched_files={"src/legacy/old_module.py"}
    )
    assert disp_touched.outcome == Outcome.BLOCK

    # Hash mismatch -> BLOCK (content edited)
    disp_hash_mismatch = disposition(
        rule="LAYER_BOUNDARY",
        severity="FAIL",
        file_path="src/legacy/old_module.py",
        region_sha256="different_hash",
        posture="ratchet",
        baseline=baseline,
        touched_files=set()
    )
    assert disp_hash_mismatch.outcome == Outcome.BLOCK
