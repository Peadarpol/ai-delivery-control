"""
Unit tests for check_exception_standards.py wrapper script and distribution manifest (T1-K-15, AT-04).
"""

from __future__ import annotations

import sys
import unittest.mock
from pathlib import Path

# Add src/scripts and bootstrap to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYS_SCRIPTS = PROJECT_ROOT / "src" / "scripts"
BOOTSTRAP_DIR = PROJECT_ROOT / "bootstrap"

for p in (str(SYS_SCRIPTS), str(BOOTSTRAP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import check_exception_standards
import manifest


def test_check_exception_standards_precondition_skip(capsys):
    """Verify check_exception_standards exits 0 with SKIPPED-precondition when tests/unit/test_exception_standards.py is absent."""
    with unittest.mock.patch("pathlib.Path.exists", return_value=False):
        code = check_exception_standards.check_exception_standards()
        assert code == 0
        captured = capsys.readouterr()
        assert "SKIPPED-precondition" in captured.out


def test_manifest_includes_check_exception_standards():
    """Verify bootstrap manifest lists check_exception_standards.py as framework-owned."""
    assert "src/scripts/check_exception_standards.py" in manifest.FRAMEWORK_OWNED
