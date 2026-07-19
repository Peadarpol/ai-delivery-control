import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.scripts import context_loader

def test_get_adr_context_non_root_cwd(tmp_path, monkeypatch):
    # Mock PROJECT_ROOT in context_loader
    monkeypatch.setattr(context_loader, "PROJECT_ROOT", tmp_path)
    
    # Mock harness_utils in sys.modules to prevent import failures
    mock_harness = MagicMock()
    monkeypatch.setitem(sys.modules, "harness_utils", mock_harness)
    
    # Create the mock wiki directory and file
    wiki_dir = tmp_path / ".agent" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "TRANSACTIONAL_INTEGRITY.md").write_text("# Transactional Integrity Wiki\nSome content.", encoding="utf-8")
    
    # Mock DOMAIN_REGISTRY and extract_adr_annotations in context_loader
    monkeypatch.setattr(context_loader, "DOMAIN_REGISTRY", {"TRANSACTIONAL_INTEGRITY"})
    monkeypatch.setattr(context_loader, "extract_adr_annotations", lambda filepath, **kwargs: ["TRANSACTIONAL_INTEGRITY"])
    
    # Create src directory inside tmp_path
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a python file with an ADR annotation exposing a domain (e.g. TRANSACTIONAL_INTEGRITY)
    py_file = src_dir / "user_repository.py"
    py_file.write_text("# Exposes: FM_TRANSACTIONAL_INTEGRITY\n", encoding="utf-8")
    
    # Create a separate subdirectory to change CWD to
    sub_dir = tmp_path / "tests"
    sub_dir.mkdir(parents=True, exist_ok=True)
    
    # Change working directory to sub_dir (non-root CWD)
    monkeypatch.chdir(sub_dir)
    
    # Call get_adr_context
    adr_context, active_domains, policy_notes = context_loader.get_adr_context(changed_files=["src/user_repository.py"])
    
    # Assert it correctly found the ADR and extracted the domain
    assert "TRANSACTIONAL_INTEGRITY" in active_domains
