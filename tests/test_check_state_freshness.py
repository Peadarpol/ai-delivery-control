"""
Tests for .agent/scripts/check_state_freshness.py — pre-compaction hook.

All cases must exit 0; the hook is non-blocking by contract.
"""

import importlib.util
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = WORKSPACE_ROOT / ".agent" / "scripts" / "check_state_freshness.py"


@pytest.fixture(scope="session")
def freshness_mod():
    """Import check_state_freshness.py as a module."""
    spec = importlib.util.spec_from_file_location("check_state_freshness", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_state_freshness"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestCheckStateFreshness:
    def test_all_fresh_no_warning_exit_0(self, freshness_mod, tmp_path, capsys):
        """All state files recently modified → no warning printed, exits 0."""
        state_files = [
            tmp_path / "active_context.md",
            tmp_path / "last_session_summary.md",
            tmp_path / "decisions_log.md",
        ]
        for f in state_files:
            f.write_text("content", encoding="utf-8")

        patched_files = [str(tmp_path / Path(p).name) for p in freshness_mod.STATE_FILES]

        with patch.object(freshness_mod, "STATE_FILES", patched_files):
            with pytest.raises(SystemExit) as exc_info:
                freshness_mod.main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "WARNING" not in captured.out

    def test_stale_files_print_warning_exit_0(self, freshness_mod, tmp_path, capsys):
        """State files older than threshold → warning printed, still exits 0."""
        stale_file = tmp_path / "active_context.md"
        stale_file.write_text("old content", encoding="utf-8")

        # Backdate mtime to 2 hours ago
        old_mtime = time.time() - 7200
        os.utime(str(stale_file), (old_mtime, old_mtime))

        patched_files = [str(stale_file)]

        with patch.object(freshness_mod, "STATE_FILES", patched_files):
            with pytest.raises(SystemExit) as exc_info:
                freshness_mod.main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "PRE-COMPACTION WARNING" in captured.out
        assert "not updated in" in captured.out

    def test_missing_files_print_warning_exit_0(self, freshness_mod, tmp_path, capsys):
        """State files that do not exist → warning printed, still exits 0."""
        missing = [str(tmp_path / "nonexistent_state.md")]

        with patch.object(freshness_mod, "STATE_FILES", missing):
            with pytest.raises(SystemExit) as exc_info:
                freshness_mod.main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "PRE-COMPACTION WARNING" in captured.out
        assert "not found" in captured.out
