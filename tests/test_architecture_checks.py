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


# ---------------------------------------------------------------------------
# T1-K-08: fail-loud guards in main()
# ---------------------------------------------------------------------------

from architecture_checks import main as arch_main


def _run_main_in(tmp_path):
    """Change to tmp_path, call arch_main(), restore cwd.  Returns the SystemExit code."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with pytest.raises(SystemExit) as exc_info:
            arch_main()
        return exc_info.value.code
    finally:
        os.chdir(old_cwd)


def test_main_fails_loud_when_no_config(tmp_path):
    """T1-K-08: missing .agent/config.yaml must exit(1), not exit(0)."""
    # tmp_path has no .agent directory at all
    code = _run_main_in(tmp_path)
    assert code == 1, "Expected exit(1) when config.yaml is absent"


def test_main_exits_zero_when_no_architecture_block(tmp_path):
    """T1-K-08: config.yaml without an 'architecture:' key is a conscious opt-out — exit(0)."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    (agent_dir / "config.yaml").write_text("paths:\n  source_root: src\n", encoding="utf-8")
    code = _run_main_in(tmp_path)
    assert code == 0, "Expected exit(0) when architecture block is absent (opt-out)"


def test_main_fails_loud_when_all_layer_paths_missing(tmp_path):
    """T1-K-08: layers configured but every path is non-existent → exit(1), not exit(0)."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    config_content = (
        "architecture:\n"
        "  layers:\n"
        "    - name: domain\n"
        "      path: src/domain\n"
        "      forbidden_imports: []\n"
    )
    (agent_dir / "config.yaml").write_text(config_content, encoding="utf-8")
    # src/domain does NOT exist in tmp_path — zero files will be scanned
    code = _run_main_in(tmp_path)
    assert code == 1, "Expected exit(1) when configured layer paths exist in config but not on disk"


def test_main_passes_when_layers_contain_python_files(tmp_path):
    """T1-K-08: layers configured and path exists with .py files → no spurious FAIL."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    src_dir = tmp_path / "src" / "domain"
    src_dir.mkdir(parents=True)
    (src_dir / "model.py").write_text("class Foo:\n    pass\n", encoding="utf-8")

    config_content = (
        "architecture:\n"
        "  layers:\n"
        "    - name: domain\n"
        "      path: src/domain\n"
        "      forbidden_imports: []\n"
    )
    (agent_dir / "config.yaml").write_text(config_content, encoding="utf-8")
    code = _run_main_in(tmp_path)
    # Should pass (0) — one file found, no violations
    assert code == 0, "Expected exit(0) when layers exist and contain Python files"

