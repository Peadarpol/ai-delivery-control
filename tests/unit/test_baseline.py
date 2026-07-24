#!/usr/bin/env python3
"""
tests/unit/test_baseline.py — Unit tests for baseline CLI and tamper detection (T1-G-18 Phase P2)
"""

import json
import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".agent" / "scripts"))

from baseline import (
    check_human_guard,
    compute_manifest_sha256,
    extract_ast_region_sha256,
    cmd_init,
    cmd_report,
)
from posture import load_baseline


def test_human_guard_blocks_agent(monkeypatch):
    """Verify check_human_guard raises SystemExit when AGENT_ID is present."""
    monkeypatch.setenv("AGENT_ID", "agent-123")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    with pytest.raises(SystemExit) as exc_info:
        check_human_guard()
    assert exc_info.value.code == 1


def test_human_guard_blocks_non_tty(monkeypatch):
    """Verify check_human_guard raises SystemExit when sys.stdin.isatty() is False."""
    monkeypatch.delenv("AGENT_ID", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    with pytest.raises(SystemExit) as exc_info:
        check_human_guard()
    assert exc_info.value.code == 1


def test_human_guard_allows_interactive_human(monkeypatch):
    """Verify check_human_guard passes when AGENT_ID is unset and TTY is True."""
    monkeypatch.delenv("AGENT_ID", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    # Should not raise exception
    check_human_guard()


def test_canonical_manifest_sha256():
    """Verify canonical JSON SHA-256 manifest calculation is key-ordering independent."""
    entries1 = [{"rule": "A", "file": "f1.py"}, {"rule": "B", "file": "f2.py"}]
    entries2 = [{"file": "f1.py", "rule": "A"}, {"file": "f2.py", "rule": "B"}]

    hash1 = compute_manifest_sha256(entries1)
    hash2 = compute_manifest_sha256(entries2)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_load_baseline_tamper_detection(tmp_path, monkeypatch):
    """Verify load_baseline detects header.manifest_sha256 mismatch and returns None."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    baseline_path = agent_dir / "baseline.json"

    entries = [{"rule": "LAYER_BOUNDARY", "file": "src/foo.py", "region_sha256": "123"}]
    correct_hash = compute_manifest_sha256(entries)

    # Write valid baseline
    valid_data = {
        "header": {"manifest_sha256": correct_hash},
        "entries": entries,
    }
    baseline_path.write_text(json.dumps(valid_data), encoding="utf-8")

    loaded = load_baseline(tmp_path)
    assert loaded is not None
    assert "_index" in loaded
    assert "src/foo.py" in loaded["_index"]

    # Tamper with entries without updating header
    tampered_entries = [{"rule": "LAYER_BOUNDARY", "file": "src/foo.py", "region_sha256": "tampered_hash"}]
    tampered_data = {
        "header": {"manifest_sha256": correct_hash},
        "entries": tampered_entries,
    }
    baseline_path.write_text(json.dumps(tampered_data), encoding="utf-8")

    loaded_tampered = load_baseline(tmp_path)
    assert loaded_tampered is None


def test_extract_ast_region_sha256(tmp_path):
    """Verify AST region extraction over enclosing function node."""
    py_file = tmp_path / "example.py"
    py_file.write_text("""
def foo():
    x = 1
    return x

def bar():
    y = 2
    return y
""", encoding="utf-8")

    hash_foo = extract_ast_region_sha256(py_file, line=3)
    hash_bar = extract_ast_region_sha256(py_file, line=7)
    assert hash_foo != ""
    assert hash_bar != ""
    assert hash_foo != hash_bar


def test_scan_current_violations_real_arch_script_path():
    """Verify scan_current_violations finds the real architecture_checks.py script and executes."""
    from baseline import scan_current_violations, PROJECT_ROOT
    arch_script = PROJECT_ROOT / ".agent" / "skills" / "universal" / "senior-architect" / "scripts" / "architecture_checks.py"
    assert arch_script.exists(), f"Architecture script not found at {arch_script}"

    entries = scan_current_violations()
    assert isinstance(entries, list)


def test_scan_current_violations_parses_entries(monkeypatch, tmp_path):
    """Verify scan_current_violations parses architecture_checks.py stdout into baseline entries."""
    from baseline import scan_current_violations
    import subprocess

    dummy_out = "[FAIL] src/foo.py:15: LAYER_BOUNDARY — Prohibited import\n"

    class DummyProc:
        returncode = 1
        stdout = dummy_out
        stderr = ""

    import baseline
    monkeypatch.setattr(baseline.subprocess, "run", lambda *args, **kwargs: DummyProc())

    entries = scan_current_violations()
    assert len(entries) == 1
    assert entries[0]["file"] == "src/foo.py"
    assert entries[0]["line"] == 15
    assert entries[0]["rule"] == "LAYER_BOUNDARY"
    assert "region_sha256" in entries[0]
