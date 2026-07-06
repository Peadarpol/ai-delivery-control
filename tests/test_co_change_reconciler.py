"""
tests/test_co_change_reconciler.py — verification tests for co_change_reconciler.py

Asserts:
  - boundary_of resolves paths correctly with longest-prefix wins and leading-dot.
  - CLI execution against a temporary repository identifies and ranks qualifying crossings.
  - Zero-layers config exits cleanly and prints expected message.
  - The markdown report is correctly generated with correct headers/table rows.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import pytest
import yaml

# Add harness scripts directory to path for imports
_HARNESS_ROOT = Path(__file__).resolve().parents[1]
_RECONCILER_PATH = _HARNESS_ROOT / ".agent" / "scripts" / "co_change_reconciler.py"
sys.path.insert(0, str(_HARNESS_ROOT / ".agent" / "scripts"))

import co_change_reconciler  # noqa: PLC0415


def _create_test_git_repo(base_dir: Path, declare_layers: bool = True) -> Path:
    """Create a temporary git repository with mock layers and commit history.

    Boundaries (when declare_layers is True):
      - layer1: src/layer1
      - layer2: src/layer2
      - gov_scripts: .agent/scripts

    Commits:
      - Commit 1 to 5: co-change:
        - src/layer1/a.py & src/layer2/b.py (cross-boundary, 5 times)
        - src/layer1/a.py & .agent/scripts/x.py (cross-boundary, spans leading-dot, 5 times)
        - src/layer1/c.py & src/layer1/d.py (within-boundary, 5 times)
        - src/layer1/a.py & src/layer2/e.py (cross-boundary, 3 times - under gate)
      - Commit 6:
        - src/layer1/c.py & src/layer1/d.py (within-boundary, total 6 times)
    """
    repo = base_dir / "test_reconciler_repo"
    repo.mkdir(parents=True, exist_ok=True)

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            cwd=str(repo)
        )

    git("init")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test User")

    # Write config.yaml
    agent_dir = repo / ".agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    config_file = agent_dir / "config.yaml"

    if declare_layers:
        config_content = {
            "project": {"name": "test-project", "type": "mock"},
            "framework": {"version": "1.0.0"},
            "architecture": {
                "layers": [
                    {"name": "layer1", "path": "src/layer1"},
                    {"name": "layer2", "path": "src/layer2"},
                    {"name": "gov_scripts", "path": ".agent/scripts"}
                ]
            }
        }
        config_file.write_text(yaml.dump(config_content), encoding="utf-8")
    else:
        config_content = {
            "project": {"name": "test-project", "type": "mock"},
            "framework": {"version": "1.0.0"}
        }
        config_file.write_text(yaml.dump(config_content), encoding="utf-8")

    git("add", ".agent/config.yaml")
    git("commit", "-m", "add config")

    def make_commit(files: dict[str, str], msg: str):
        for path, content in files.items():
            filepath = repo / path
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
        git("add", ".")
        git("commit", "-m", msg)

    # Commits 1 to 3: touch a, b, x
    for i in range(1, 4):
        make_commit({
            "src/layer1/a.py": f"print('a{i}')",
            "src/layer2/b.py": f"print('b{i}')",
            ".agent/scripts/x.py": f"print('x{i}')"
        }, f"commit_1_3_{i}")

    # Commits 4 to 5: touch a, b
    for i in range(4, 6):
        make_commit({
            "src/layer1/a.py": f"print('a{i}')",
            "src/layer2/b.py": f"print('b{i}')"
        }, f"commit_4_5_{i}")

    # Commits 6 to 7: touch a, x
    for i in range(6, 8):
        make_commit({
            "src/layer1/a.py": f"print('a{i}')",
            ".agent/scripts/x.py": f"print('x{i}')"
        }, f"commit_6_7_{i}")

    # Commits 8 to 13 (6 commits): touch c, d (within-boundary)
    for i in range(8, 14):
        make_commit({
            "src/layer1/c.py": f"print('c{i}')",
            "src/layer1/d.py": f"print('d{i}')"
        }, f"commit_8_13_{i}")

    # Commits 14 to 16 (3 commits): touch a, e (under-gate crossing)
    for i in range(14, 17):
        make_commit({
            "src/layer1/a.py": f"print('a{i}')",
            "src/layer2/e.py": f"print('e{i}')"
        }, f"commit_14_16_{i}")

    return repo


class TestBoundaryOfResolution:
    """Validate boundary_of resolves file paths correctly (longest-prefix, None)."""

    def test_boundary_of_resolves_correctly(self):
        layers = {
            "layer1": "src/layer1",
            "layer2": "src/layer2",
            "layer2_sub": "src/layer2/sub",
            "gov_scripts": ".agent/scripts"
        }

        # Exact boundary or prefix
        assert co_change_reconciler.boundary_of("src/layer1/a.py", layers) == "layer1"
        assert co_change_reconciler.boundary_of("src/layer2/b.py", layers) == "layer2"

        # Longest prefix wins
        assert co_change_reconciler.boundary_of("src/layer2/sub/c.py", layers) == "layer2_sub"

        # Leading-dot path
        assert co_change_reconciler.boundary_of(".agent/scripts/x.py", layers) == "gov_scripts"

        # Unmatched files
        assert co_change_reconciler.boundary_of("docs/index.md", layers) is None
        assert co_change_reconciler.boundary_of("src/layer3/a.py", layers) is None


class TestCoChangeReconcilerCLI:
    """Validate E2E execution of reconciler CLI against temporary repository."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self.repo = _create_test_git_repo(tmp_path, declare_layers=True)
        self.empty_repo = _create_test_git_repo(tmp_path / "empty", declare_layers=False)

    def test_run_identifies_cross_boundary_crossings(self):
        """Assert CLI correctly identifies qualifying crossings, excludes others, and writes report."""
        report_path = self.tmp_path / "report.md"
        res = subprocess.run([
            sys.executable,
            str(_RECONCILER_PATH),
            "--project-root",
            str(self.repo),
            "--min-commits",
            "5",
            "--out",
            str(report_path)
        ], capture_output=True, text=True, encoding="utf-8")

        assert res.returncode == 0
        assert "Reconciliation complete" in res.stdout
        assert "2 crossings found" in res.stdout

        # Assert report file was created
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")

        # Must have the header and target root
        assert "# Co-Change Reconciliation Report" in content
        assert "**Min-commits gate**: 5" in content
        assert "gov_scripts, layer1, layer2" in content

        # Check cross-boundary pair 1: layer1/a.py & layer2/b.py (5 co-changes)
        assert "src/layer1/a.py" in content
        assert "src/layer2/b.py" in content
        assert "layer1" in content
        assert "layer2" in content

        # Check cross-boundary pair 2 (spans leading-dot): layer1/a.py & gov_scripts/x.py (5 co-changes)
        assert ".agent/scripts/x.py" in content
        assert "gov_scripts" in content

        # Check that within-boundary pair (c.py & d.py) is absent (Clarification 1 & 2)
        assert "src/layer1/c.py" not in content
        assert "src/layer1/d.py" not in content

        # Check that under-gate pair (a.py & e.py, 3 co-changes) is absent
        assert "src/layer2/e.py" not in content

    def test_no_layers_exit_gracefully(self):
        """Assert CLI exits with 0 and prints 'nothing to reconcile' when layers config is missing."""
        res = subprocess.run([
            sys.executable,
            str(_RECONCILER_PATH),
            "--project-root",
            str(self.empty_repo)
        ], capture_output=True, text=True, encoding="utf-8")

        assert res.returncode == 0
        assert "no architecture.layers declared; nothing to reconcile" in res.stdout
