"""
Unit tests for .agent/scripts/log_decision.py CLI wrapper (Phase 6 / HIB-082 / Scenario 9).
"""

import subprocess
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_log_decision_cli_standalone_invocation(tmp_path: Path):
    """Scenario 9 (HIB-082): python .agent/scripts/log_decision.py runs cleanly from project root."""
    log_script = PROJECT_ROOT / ".agent" / "scripts" / "log_decision.py"
    assert log_script.exists()

    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "config.yaml").write_text('version: "1.4.13"\n', encoding="utf-8")
    state_dir = agent_dir / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "decisions_log.md").write_text("# Decisions Log\n\n", encoding="utf-8")

    # Run log_decision.py CLI command with cwd=tmp_path
    cmd = [
        sys.executable,
        str(log_script),
        "Test CLI Decision Title",
        "Test Decision Content",
        "Test Context Motivation",
        "Test Consequence Impact",
        "--date", "2026-07-26",
    ]

    import os
    env = os.environ.copy()
    src_scripts = str(PROJECT_ROOT / "src" / "scripts")
    env["PYTHONPATH"] = f"{src_scripts};{env.get('PYTHONPATH', '')}" if "PYTHONPATH" in env else src_scripts

    res = subprocess.run(cmd, cwd=str(tmp_path), env=env, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Decision logged successfully" in res.stdout

    # Verify entry in tmp_path decisions_log.md
    log_file = state_dir / "decisions_log.md"
    content = log_file.read_text(encoding="utf-8")
    assert "## 2026-07-26: Test CLI Decision Title" in content
    assert "- **Decision**: Test Decision Content" in content
