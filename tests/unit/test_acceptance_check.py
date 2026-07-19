import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure .agent/scripts is in path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".agent" / "scripts"))
import acceptance_check

def test_acceptance_check_pydantic_fallback(tmp_path, monkeypatch):
    # Temporarily remove pydantic from sys.modules
    original_pydantic = sys.modules.get("pydantic")
    monkeypatch.setitem(sys.modules, "pydantic", None)

    # Reload acceptance_check module to trigger fallback
    try:
        importlib.reload(acceptance_check)
    except Exception as e:
        pytest.fail(f"Failed to import acceptance_check with Pydantic missing: {e}")

    assert not acceptance_check._pydantic_installed

    # Verify AcceptanceVerdict stub works
    verdict = acceptance_check.AcceptanceVerdict(
        verdict="SATISFIED",
        satisfied_scenarios=[],
        partial_scenarios=[],
        unimplemented_scenarios=[],
        scope_creep_findings=[],
        remediation_steps=[],
        rationale="stub"
    )
    assert verdict.verdict == "SATISFIED"
    assert verdict.model_dump()["verdict"] == "SATISFIED"

    # Test CI enforcement (fail-closed)
    monkeypatch.setenv("CI", "true")
    with patch("sys.stdout", new_callable=MagicMock), \
         patch("sys.stderr", new_callable=MagicMock):
        with pytest.raises(SystemExit) as excinfo:
            acceptance_check.main()
        assert excinfo.value.code == 1

    # Test local run (audit logging + visual warning)
    monkeypatch.delenv("CI", raising=False)

    logged_actions = []
    def mock_log_action(**kwargs):
        logged_actions.append(kwargs)
    monkeypatch.setattr(acceptance_check, "log_action", mock_log_action)

    # Create a config file to test Stage 3 Warning printing (not silenced)
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / ".agent"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yaml"
    config_file.write_text("silence_pydantic_warning: false\npackage_manager: pip\n", encoding="utf-8")

    mock_args = MagicMock()
    mock_args.spec = "SPEC-001"
    mock_args.base = None
    mock_args.strict = False
    mock_args.fail_closed = False

    with patch("sys.stdout", new_callable=MagicMock), \
         patch("sys.stderr", new_callable=MagicMock) as mock_stderr, \
         patch("argparse.ArgumentParser.parse_args", return_value=mock_args), \
         patch("acceptance_check.resolve_spec_id", side_effect=ValueError("stop")):
        with pytest.raises(SystemExit) as excinfo:
            acceptance_check.main()
        assert excinfo.value.code == 1

        # Assert Stage 2 Audit Log was written
        assert len(logged_actions) == 1
        assert logged_actions[0]["action_type"] == "spec_acceptance_gate"
        assert logged_actions[0]["status"] == "fail"

        # Assert Stage 3 Visual warning was printed to stderr
        stderr_output = "".join(call[0][0] for call in mock_stderr.write.call_args_list)
        assert "⚠️  [ACCEPTANCE_GATE WARNING] Running without schema validation" in stderr_output
        assert "pip install pydantic" in stderr_output

    # Test silence warning flag
    config_file.write_text("silence_pydantic_warning: true\npackage_manager: pip\n", encoding="utf-8")
    with patch("sys.stdout", new_callable=MagicMock), \
         patch("sys.stderr", new_callable=MagicMock) as mock_stderr, \
         patch("argparse.ArgumentParser.parse_args", return_value=mock_args), \
         patch("acceptance_check.resolve_spec_id", side_effect=ValueError("stop")):
        with pytest.raises(SystemExit) as excinfo:
            acceptance_check.main()
        assert excinfo.value.code == 1
        stderr_output = "".join(call[0][0] for call in mock_stderr.write.call_args_list)
        assert "⚠️  [ACCEPTANCE_GATE WARNING] Running without schema validation" not in stderr_output

    # Clean up and restore original pydantic status
    if original_pydantic:
        sys.modules["pydantic"] = original_pydantic
    else:
        sys.modules.pop("pydantic", None)
    importlib.reload(acceptance_check)
