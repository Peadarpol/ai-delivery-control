import pytest
from pathlib import Path
from unittest.mock import patch
from src.scripts import ai_review

def test_select_context_sections_always_includes_rule_sections(tmp_path):
    universal = tmp_path / "review_context_universal.md"
    content = """# Universal Guidelines
---
## [RULE:SECRETS]
<!-- SECTION:secrets -->
AWS_SECRET_ACCESS_KEY must not be committed.
---
## [RULE:TDD]
<!-- SECTION:tdd_law -->
Always write tests.
---
## [APPENDIX:VOCABULARY]
<!-- SECTION:vocabulary -->
AT1, FM1
"""
    universal.write_text(content, encoding="utf-8")
    
    # Diff containing a secret pattern (this might be a secret-bearing diff, but we ensure rule sections appear)
    diff = "+ AWS_SECRET_ACCESS_KEY = 'secret'"
    
    with patch.object(ai_review, "UNIVERSAL_CONTEXT_FILE", universal), \
         patch.object(ai_review, "PROJECT_CONTEXT_FILE", tmp_path / "project_context.md"):
        result = ai_review.load_review_context(diff)
        
    assert "AWS_SECRET_ACCESS_KEY" in result
    assert "Always write tests" in result
    assert "VOCABULARY" not in result


def test_select_context_sections_excludes_vocabulary_without_adr(tmp_path):
    universal = tmp_path / "review_context_universal.md"
    content = """# Universal Guidelines
---
## [RULE:SECRETS]
<!-- SECTION:secrets -->
AWS_SECRET_ACCESS_KEY must not be committed.
---
## [RULE:TDD]
<!-- SECTION:tdd_law -->
Always write tests.
---
## [APPENDIX:VOCABULARY]
<!-- SECTION:vocabulary -->
AT1, FM1
"""
    universal.write_text(content, encoding="utf-8")
    
    # Plain code diff
    diff = "+ x = 1"
    
    with patch.object(ai_review, "UNIVERSAL_CONTEXT_FILE", universal), \
         patch.object(ai_review, "PROJECT_CONTEXT_FILE", tmp_path / "project_context.md"):
        result = ai_review.load_review_context(diff)
        
    assert "AWS_SECRET_ACCESS_KEY" in result
    assert "Always write tests" in result
    assert "VOCABULARY" not in result


def test_adr_diff_injects_vocabulary(tmp_path):
    universal = tmp_path / "review_context_universal.md"
    content = """# Universal Guidelines
---
## [RULE:SECRETS]
<!-- SECTION:secrets -->
AWS_SECRET_ACCESS_KEY must not be committed.
---
## [RULE:TDD]
<!-- SECTION:tdd_law -->
Always write tests.
---
## [APPENDIX:VOCABULARY]
<!-- SECTION:vocabulary -->
AT1, FM1
"""
    universal.write_text(content, encoding="utf-8")
    
    # Diff containing ADR trigger
    diff = "+# ADR: choosing consistency over latency\n+Decision /"
    
    with patch.object(ai_review, "UNIVERSAL_CONTEXT_FILE", universal), \
         patch.object(ai_review, "PROJECT_CONTEXT_FILE", tmp_path / "project_context.md"):
        result = ai_review.load_review_context(diff)
        
    assert "AWS_SECRET_ACCESS_KEY" in result
    assert "Always write tests" in result
    assert "VOCABULARY" in result


def test_adr_decision_block_rule_reaches_context(tmp_path):
    universal = tmp_path / "review_context_universal.md"
    content = """# Universal Guidelines
---
## [RULE:SECRETS]
<!-- SECTION:secrets -->
AWS_SECRET_ACCESS_KEY must not be committed.
---
## [RULE:ADR-DECISION-BLOCK]
<!-- SECTION:adr_decision_block -->
For new patterns, ADR must contain a decision block.
"""
    universal.write_text(content, encoding="utf-8")
    
    # Diff containing ADR trigger
    diff = "+# ADR: choosing consistency over latency\n+Decision /"
    
    with patch.object(ai_review, "UNIVERSAL_CONTEXT_FILE", universal), \
         patch.object(ai_review, "PROJECT_CONTEXT_FILE", tmp_path / "project_context.md"):
        result = ai_review.load_review_context(diff)
        
    assert "ADR-DECISION-BLOCK" in result


def test_fallback_basemodel_stub_literal_non_validation(monkeypatch):
    import sys
    import importlib
    from src.scripts import gate_context
    
    # Force fallback mode by temporarily masking Pydantic
    original_pydantic = sys.modules.get("pydantic")
    monkeypatch.setitem(sys.modules, "pydantic", None)
    
    try:
        importlib.reload(gate_context)
        assert not gate_context._pydantic_installed
        
        # Instantiate a stub model with an invalid Literal type value
        # e.g., ArchViolation has severity: Literal["HIGH", "MEDIUM", "LOW"]
        # We pass an invalid value "CRITICAL".
        violation = gate_context.ArchViolation(
            severity="CRITICAL",
            message="stub test message",
            file_path="src/dummy.py",
            line_number=10,
            capability="TRANSACTIONAL_INTEGRITY"
        )
        
        # Verify the accept-anything fallback behavior (no ValidationError raised)
        # and document this current behavior.
        assert violation.severity == "CRITICAL"
        assert violation.model_dump()["severity"] == "CRITICAL"
        
    finally:
        # Restore Pydantic
        if original_pydantic:
            sys.modules["pydantic"] = original_pydantic
        else:
            sys.modules.pop("pydantic", None)
        importlib.reload(gate_context)


def test_load_config_skip_paths_merging(tmp_path, monkeypatch):
    import json
    
    # Mock PROJECT_ROOT and CONFIG_FILE in ai_review
    monkeypatch.setattr(ai_review, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_review, "CONFIG_FILE", tmp_path / ".ai-review-config.json")
    
    # Write .ai-review-config.json with skip_paths
    config_json = tmp_path / ".ai-review-config.json"
    config_json.write_text(json.dumps({
        "skip_paths": ["json_skipped_1.py", "shared_skipped.py"]
    }), encoding="utf-8")
    
    # Write .agent/config.yaml with skip_paths
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    config_yaml = agent_dir / "config.yaml"
    config_yaml.write_text("""
skip_paths:
  - yaml_skipped_1.py
  - shared_skipped.py
""", encoding="utf-8")
    
    # Execute load_config
    config = ai_review.load_config()
    
    # Verify skip_paths entries are merged and deduplicated
    expected_skipped = ["json_skipped_1.py", "shared_skipped.py", "yaml_skipped_1.py"]
    assert config.get("skip_paths") == expected_skipped
