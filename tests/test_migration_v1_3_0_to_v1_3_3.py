"""
Tests for bootstrap/migrations/v1_3_0_to_v1_3_3.py

Covers:
- migrate(): version field bumped from 1.3.0 to 1.3.3
- downgrade(): version field reverted from 1.3.3 to 1.3.0
- UpgradeManager integration: end-to-end from a v1.3.0 project
"""

import json
import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_ROOT))

from bootstrap import upgrade, downgrade
from bootstrap.migrations import v1_3_0_to_v1_3_3 as migration_mod


# ── Config template ───────────────────────────────────────────────────────────

_V1_3_0_CONFIG = """\
# AI Delivery Control - Config v1.3.0
framework:
  version: "1.3.0"
  repo: "https://github.com/Peadarpol/ai-delivery-control"
  installed_at: "2026-01-01"

project:
  name: "TestProject"

model_routing:
  budget_provider: "anthropic"
  budget_model: "claude-haiku"
  review_provider: "anthropic"
  review_model: "claude-sonnet"

domain_constraints:
  - "Tenant Isolation"
"""


@pytest.fixture
def v130_config(tmp_path) -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(_V1_3_0_CONFIG, encoding="utf-8")
    return config


@pytest.fixture
def v130_project(tmp_path) -> Path:
    """Minimal v1.3.0 project layout for UpgradeManager."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "scripts").mkdir()
    (agent_dir / "workflows").mkdir()
    (agent_dir / "skills").mkdir()
    (agent_dir / "config").mkdir()
    (agent_dir / "state").mkdir()

    (agent_dir / "config.yaml").write_text(_V1_3_0_CONFIG, encoding="utf-8")
    (tmp_path / ".gitignore").write_text("/node_modules/\n", encoding="utf-8")

    state_data = {"current_version": "1.3.0", "applied_migrations": [], "last_upgraded": "2026-01-01T00:00:00"}
    (agent_dir / ".framework_migration_state").write_text(json.dumps(state_data), encoding="utf-8")

    return tmp_path


# ── Unit: migrate ─────────────────────────────────────────────────────────────

def test_migrate_bumps_version(v130_config):
    migration_mod.migrate(v130_config)
    content = v130_config.read_text(encoding="utf-8")
    assert 'version: "1.3.3"' in content
    assert 'version: "1.3.0"' not in content


def test_migrate_preserves_other_fields(v130_config):
    migration_mod.migrate(v130_config)
    content = v130_config.read_text(encoding="utf-8")
    assert "TestProject" in content
    assert "Tenant Isolation" in content
    assert "claude-sonnet" in content


def test_migrate_is_idempotent(v130_config):
    migration_mod.migrate(v130_config)
    migration_mod.migrate(v130_config)
    content = v130_config.read_text(encoding="utf-8")
    assert content.count('version: "1.3.3"') == 1


# ── Unit: downgrade ───────────────────────────────────────────────────────────

def test_downgrade_reverts_version(v130_config):
    migration_mod.migrate(v130_config)
    migration_mod.downgrade(v130_config)
    content = v130_config.read_text(encoding="utf-8")
    assert 'version: "1.3.0"' in content
    assert 'version: "1.3.3"' not in content


def test_downgrade_preserves_other_fields(v130_config):
    migration_mod.migrate(v130_config)
    migration_mod.downgrade(v130_config)
    content = v130_config.read_text(encoding="utf-8")
    assert "TestProject" in content
    assert "Tenant Isolation" in content


def test_migrate_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        migration_mod.migrate(tmp_path / "nonexistent.yaml")


def test_downgrade_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        migration_mod.downgrade(tmp_path / "nonexistent.yaml")


# ── Integration: UpgradeManager from v1.3.0 ──────────────────────────────────

def test_upgrade_manager_from_v130_to_v133(v130_project):
    """UpgradeManager discovers and applies the v1.3.0→v1.3.3 migration."""
    manager = upgrade.UpgradeManager(
        v130_project,
        dry_run=False,
        force=True,
        target_version="1.3.3",
    )
    manager.run_upgrade(skip_preflight=True)

    config = (v130_project / ".agent" / "config.yaml").read_text(encoding="utf-8")
    assert 'version: "1.3.3"' in config

    state_file = v130_project / ".agent" / ".framework_migration_state"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["current_version"] == "1.3.3"


def test_downgrade_manager_from_v133_to_v130(v130_project):
    """DowngradeManager reverts v1.3.3 back to v1.3.0 cleanly."""
    mgr_up = upgrade.UpgradeManager(v130_project, dry_run=False, force=True, target_version="1.3.3")
    mgr_up.run_upgrade(skip_preflight=True)

    mgr_down = downgrade.DowngradeManager(v130_project, dry_run=False, force=True, to_version="1.3.0")
    mgr_down.run_downgrade()

    config = (v130_project / ".agent" / "config.yaml").read_text(encoding="utf-8")
    assert 'version: "1.3.0"' in config

    state_file = v130_project / ".agent" / ".framework_migration_state"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["current_version"] == "1.3.0"
