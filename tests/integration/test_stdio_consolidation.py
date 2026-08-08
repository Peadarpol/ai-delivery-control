"""
Unit tests for UTF-8 stdio consolidation and HIB-083 regression guards (Phase 3 / Scenarios 10 & 11).
"""

import ast
import os
import subprocess
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_scenario_10_no_script_duplicates_stdio_wrap():
    """Scenario 10 (HIB-083): Assert no script in .agent/scripts/ contains a local TextIOWrapper / reconfigure stdio wrap."""
    agent_scripts_dir = PROJECT_ROOT / ".agent" / "scripts"
    assert agent_scripts_dir.exists()

    forbidden_patterns = ["TextIOWrapper", "reconfigure"]
    violations = []

    for py_file in agent_scripts_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("reconfigure", "TextIOWrapper"):
                violations.append(f"{py_file.name}:{node.lineno} -> {node.attr}")
            elif isinstance(node, ast.Name) and node.id == "TextIOWrapper":
                violations.append(f"{py_file.name}:{node.lineno} -> TextIOWrapper")

    assert not violations, f"Local stdio wrap duplication found in .agent/scripts/: {violations}"


def test_scenario_11_session_health_cp1252_execution(tmp_path: Path):
    """Scenario 11 (HIB-083): session_health.py executes cleanly under non-UTF-8 console without UnicodeEncodeError."""
    session_health_script = PROJECT_ROOT / ".agent" / "scripts" / "session_health.py"
    assert session_health_script.exists()

    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "config.yaml").write_text('version: "1.4.13"\n', encoding="utf-8")
    state_dir = agent_dir / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "session.json").write_text(
        '{"schema_version": "1.0", "session_id": "test", "status": "ACTIVE", "task_magnitude": "micro"}\n',
        encoding="utf-8"
    )

    # Environment simulating Windows non-UTF-8 codepage (cp1252)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252:replace"
    src_scripts = str(PROJECT_ROOT / "src" / "scripts")
    env["PYTHONPATH"] = f"{src_scripts};{env.get('PYTHONPATH', '')}" if "PYTHONPATH" in env else src_scripts

    res = subprocess.run(
        [sys.executable, str(session_health_script)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        encoding="cp1252",
        errors="replace",
    )

    assert res.returncode == 0, f"session_health.py failed: stderr={res.stderr}, stdout={res.stdout}"
    assert "Session Health Report" in res.stdout
