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
