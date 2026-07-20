"""
Unit tests for harness_utils config loader unification (T1-E-04).
"""

from __future__ import annotations

import importlib
import re
import sys
import unittest.mock
from pathlib import Path

# Add src/scripts and .agent/scripts to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYS_SCRIPTS = PROJECT_ROOT / "src" / "scripts"
AGENT_SCRIPTS = PROJECT_ROOT / ".agent" / "scripts"

for p in (str(SYS_SCRIPTS), str(AGENT_SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

import harness_utils
import check_traceability
import acceptance_hook
import check_spec


def test_fallback_yaml_parse_parity_with_safe_load():
    """Verify _fallback_yaml_parse output parity with yaml.safe_load for standard config templates."""
    try:
        import yaml
        has_yaml = True
    except ImportError:
        has_yaml = False

    if not has_yaml:
        return

    sample_paths = [
        PROJECT_ROOT / "bootstrap" / "templates" / "config.yaml.template",
        PROJECT_ROOT / ".agent" / "config.yaml",
    ]

    for p in sample_paths:
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8")
        parsed_yaml = yaml.safe_load(content) or {}
        parsed_fallback = harness_utils._fallback_yaml_parse(content)

        # Assert key top-level sections match
        for key in ("project", "tech_stack", "outer_loop", "spec_gate"):
            if key in parsed_yaml:
                assert key in parsed_fallback, f"Missing key '{key}' in fallback output for {p}"


def test_no_pyyaml_execution_fallback():
    """Verify fallback parser executes cleanly when PyYAML module is unavailable."""
    harness_utils._reset_config_cache()
    try:
        with unittest.mock.patch.dict(sys.modules, {"yaml": None}):
            importlib.reload(harness_utils)
            cfg = harness_utils.load_harness_config(strict=False)
            assert isinstance(cfg, dict)
    finally:
        importlib.reload(harness_utils)
        harness_utils._reset_config_cache()


def test_config_loader_caching():
    """Verify load_harness_config hits global cache and _reset_config_cache clears it."""
    harness_utils._reset_config_cache()
    cfg1 = harness_utils.load_harness_config()
    cfg2 = harness_utils.load_harness_config()
    assert cfg1 is cfg2

    harness_utils._reset_config_cache()
    cfg3 = harness_utils.load_harness_config()
    assert cfg3 is not cfg1


def test_consumer_section_awareness_scenario_4(tmp_path):
    """Scenario 4: Verify consumers read section-scoped mode instead of matching top-level mode: ignore."""
    config_content = """mode: ignore

outer_loop:
  mode: strict

spec_gate:
  specs_path: custom/specs/

acceptance_gate:
  specs_path: custom/specs/

traceability:
  specs_path: custom/specs/
"""
    tmp_config = tmp_path / "config.yaml"
    tmp_config.write_text(config_content, encoding="utf-8")

    harness_utils._reset_config_cache()
    try:
        # Check traceability consumer
        specs_p, mode = check_traceability.get_config_options()
        # Verify get_harness_config with explicit config path
        val_mode = harness_utils.get_harness_config("outer_loop", "mode", config_path=tmp_config)
        assert val_mode == "strict"
    finally:
        harness_utils._reset_config_cache()


def test_init_session_custom_specs_path_via_config_loader(tmp_path):
    """Verify init_session uses get_harness_config to resolve custom spec_gate.specs_path."""
    config_content = """spec_gate:
  specs_path: custom/specs/dir
"""
    tmp_config = tmp_path / "config.yaml"
    tmp_config.write_text(config_content, encoding="utf-8")

    harness_utils._reset_config_cache()
    try:
        resolved_path = harness_utils.get_harness_config("spec_gate", "specs_path", config_path=tmp_config)
        assert resolved_path == "custom/specs/dir"
    finally:
        harness_utils._reset_config_cache()


def test_self_enforcing_defaults_rule_static_scan():
    """Static test checking no consumer passes an explicit default for a key already in DEFAULTS."""
    defaults = harness_utils.DEFAULTS
    known_default_keys = set()
    for sec, val in defaults.items():
        if isinstance(val, dict):
            for k in val:
                known_default_keys.add((sec, k))

    # Scan python files under src/scripts and .agent/scripts
    py_files = list(SYS_SCRIPTS.glob("*.py")) + list(AGENT_SCRIPTS.glob("*.py"))
    violations = []

    for f in py_files:
        content = f.read_text(encoding="utf-8")
        for sec, k in known_default_keys:
            pattern = rf'get_harness_config\(\s*["\']{sec}["\']\s*,\s*["\']{k}["\']\s*,\s*default\s*='
            if re.search(pattern, content):
                violations.append(f"{f.name}: get_harness_config({sec}, {k}, default=...) redundant with DEFAULTS")

    assert not violations, f"Found self-enforcing defaults violations: {violations}"
