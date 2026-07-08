import pytest
from pathlib import Path
from src.scripts.harness_utils import (
    load_harness_config,
    get_harness_config,
    DEFAULTS,
    _fallback_yaml_parse
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def test_config_loader_drift_assertions():
    """
    Ensure every section and key in DEFAULTS is physically present in the 
    template config file. This prevents drift where a default is provided for 
    a key that no longer exists or was moved to another section.
    """
    template_path = PROJECT_ROOT / "bootstrap" / "templates" / "config.yaml.template"
    assert template_path.exists(), "config.yaml.template not found"
    
    # Load template content
    content = template_path.read_text(encoding="utf-8")
    
    pytest.importorskip('yaml')
    import yaml
    template_dict = yaml.safe_load(content)
    
    def check_keys(d, template_d, path=""):
        for k, v in d.items():
            assert k in template_d, f"Key '{k}' from DEFAULTS missing in template at {path}!"
            if isinstance(v, dict):
                check_keys(v, template_d[k], path=f"{path}.{k}" if path else k)
                
    check_keys(DEFAULTS, template_dict)

def test_fallback_yaml_parse():
    """Test our simple indentation-aware parser."""
    yaml_content = '''
project:
  name: "ai-delivery-control"
  type: "Governance Harness"
outer_loop:
  mode: "incremental"
    '''
    parsed = _fallback_yaml_parse(yaml_content)
    assert parsed["project"]["name"] == "ai-delivery-control"
    assert parsed["outer_loop"]["mode"] == "incremental"

def test_get_harness_config_resolution_order(tmp_path):
    """
    Test resolution order: config value -> DEFAULTS table -> explicit arg -> None
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text('''
memory:
  retention_days: 90
traceability:
  other_key: true
    ''', encoding="utf-8")
    
    # 1. Config value wins
    assert get_harness_config("memory", "retention_days", config_path=config_file) == 90
    
    # 2. DEFAULTS table wins if not in config
    assert get_harness_config("traceability", "specs_path", config_path=config_file) == "docs/planning/specs/"
    
    # 3. Explicit arg wins if not in config and not in DEFAULTS
    assert get_harness_config("traceability", "other_key_not_in_defaults", default="fallback", config_path=config_file) == "fallback"
    
    # 4. None if not provided
    assert get_harness_config("traceability", "not_exist", config_path=config_file) is None

def test_get_harness_config_falsy_values(tmp_path):
    """
    Test that falsy config values (0, False, empty string) are correctly returned
    and do not fall through to defaults. (Regression test for FID-1)
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text('''
model_routing:
  max_tokens: 0
memory:
  retention_days: false
  other_val: ""
    ''', encoding="utf-8")
    
    assert get_harness_config("model_routing", "max_tokens", config_path=config_file) == 0
    assert get_harness_config("memory", "retention_days", config_path=config_file) is False
    assert get_harness_config("memory", "other_val", config_path=config_file) == ""
