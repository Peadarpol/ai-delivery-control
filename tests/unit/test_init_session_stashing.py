"""
Unit tests for init_session stashing safety and cleanup (HIB-ENV-02, T1-I-08).
"""

from __future__ import annotations

import io
import sys
import unittest.mock
from pathlib import Path

# Add .agent/scripts and src/scripts to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_SCRIPTS = PROJECT_ROOT / ".agent" / "scripts"
SYS_SCRIPTS = PROJECT_ROOT / "src" / "scripts"

for p in (str(AGENT_SCRIPTS), str(SYS_SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

import init_session


def test_create_session_checkpoint_clean_tree_skips():
    """Verify _create_session_checkpoint does nothing if working tree is clean."""
    with unittest.mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = ""
        mock_run.return_value.returncode = 0
        init_session._create_session_checkpoint("test-sess-clean")
        # Ensure stash push was not called
        assert not any("stash" in call.args[0] and "push" in call.args[0] for call in mock_run.call_args_list)


def test_create_session_checkpoint_interactive_tty_accept():
    """Verify interactive TTY prompt creates stash on Y response."""
    status_output = " M file.py\n"
    with unittest.mock.patch("subprocess.run") as mock_run, \
         unittest.mock.patch("sys.stdin", io.StringIO("y\n")) as mock_stdin:
        mock_stdin.isatty = lambda: True
        mock_run.side_effect = [
            unittest.mock.Mock(stdout=status_output, returncode=0),  # status check
            unittest.mock.Mock(stdout="Saved working directory", returncode=0),  # stash push
        ]
        init_session._create_session_checkpoint("test-sess-tty-y")
        assert mock_run.call_count == 2


def test_create_session_checkpoint_interactive_tty_decline():
    """Verify interactive TTY prompt skips stash on N response."""
    status_output = " M file.py\n"
    with unittest.mock.patch("subprocess.run") as mock_run, \
         unittest.mock.patch("sys.stdin", io.StringIO("n\n")) as mock_stdin:
        mock_stdin.isatty = lambda: True
        mock_run.side_effect = [
            unittest.mock.Mock(stdout=status_output, returncode=0),  # status check
        ]
        init_session._create_session_checkpoint("test-sess-tty-n")
        assert mock_run.call_count == 1  # Only status run, no stash push


def test_drop_session_checkpoint_stash_on_clean_close():
    """Verify _drop_session_checkpoint_stash drops matching stash on clean close."""
    stash_list_output = "stash@{0}: AUTO: session-start checkpoint [sess-1234567]\n"
    with unittest.mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            unittest.mock.Mock(stdout=stash_list_output, returncode=0),  # stash list
            unittest.mock.Mock(stdout="Dropped stash@{0}", returncode=0),  # stash drop
        ]
        init_session._drop_session_checkpoint_stash("sess-123456789abc")
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[1].args[0] == ["git", "stash", "drop", "stash@{0}"]
