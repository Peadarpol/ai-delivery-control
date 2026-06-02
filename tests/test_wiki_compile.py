"""
Tests for .agent/scripts/wiki_compile.py — config-driven domain registry.

Change 2 (S0-24): DOMAIN_REGISTRY is now loaded from .agent/config.yaml
instead of being hardcoded. These tests guard the three key behaviours of
load_domain_registry():
  1. Graceful no-op when wiki_domains is absent from config
  2. Silent skip of domains whose source files are all missing
  3. Correct registry construction from a valid config
"""

import importlib.util
import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
_WIKI_COMPILE_PATH = WORKSPACE_ROOT / ".agent" / "scripts" / "wiki_compile.py"


def _load_wiki_compile():
    """Import wiki_compile from its absolute path."""
    spec = importlib.util.spec_from_file_location("wiki_compile_test", _WIKI_COMPILE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wiki_compile_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def wiki_compile():
    return _load_wiki_compile()


class TestLoadDomainRegistry:
    """load_domain_registry() must handle absent/empty config gracefully."""

    def test_load_domain_registry_empty_config(self, wiki_compile, tmp_path):
        """Config with no wiki_domains section returns empty dict, no error."""
        config = tmp_path / "config.yaml"
        config.write_text(
            "project:\n  name: test\nmodel_routing:\n  review_provider: anthropic\n",
            encoding="utf-8",
        )
        result = wiki_compile.load_domain_registry(config_path=config)
        assert result == {}

    def test_load_domain_registry_explicit_empty(self, wiki_compile, tmp_path):
        """Explicit empty wiki_domains: {} returns empty dict, no error."""
        config = tmp_path / "config.yaml"
        config.write_text("wiki_domains: {}\n", encoding="utf-8")
        result = wiki_compile.load_domain_registry(config_path=config)
        assert result == {}

    def test_load_domain_registry_missing_source_files(self, wiki_compile, tmp_path):
        """Domains whose source files are all missing are silently skipped."""
        config = tmp_path / "config.yaml"
        config.write_text(
            "wiki_domains:\n"
            "  nonexistent_domain:\n"
            "    - docs/decisions/adr/does_not_exist.md\n",
            encoding="utf-8",
        )
        result = wiki_compile.load_domain_registry(config_path=config)
        assert "nonexistent_domain" not in result
        assert result == {}

    def test_load_domain_registry_reads_from_config(self, wiki_compile, tmp_path):
        """Happy path: domains with existing source files appear in the registry."""
        # Create the ADR source file so it counts as present
        adr_dir = tmp_path / "docs" / "decisions" / "adr"
        adr_dir.mkdir(parents=True)
        adr_file = adr_dir / "adr_001_clean_architecture.md"
        adr_file.write_text("# ADR-001: Clean Architecture\nSome content.", encoding="utf-8")

        config = tmp_path / "config.yaml"
        config.write_text(
            f"wiki_domains:\n"
            f"  clean_architecture:\n"
            f"    - {adr_file.relative_to(tmp_path)!s}\n",
            encoding="utf-8",
        )

        # Temporarily change cwd so relative path resolution works
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = wiki_compile.load_domain_registry(config_path=config)
        finally:
            os.chdir(original_cwd)

        assert "clean_architecture" in result
        entry = result["clean_architecture"]
        assert "sources" in entry
        assert "output" in entry
        assert entry["output"] == ".agent/wiki/clean_architecture.md"
        assert len(entry["sources"]) == 1

    def test_load_domain_registry_absent_config(self, wiki_compile, tmp_path):
        """Absent config file returns empty dict, no FileNotFoundError."""
        missing = tmp_path / "does_not_exist.yaml"
        result = wiki_compile.load_domain_registry(config_path=missing)
        assert result == {}

    def test_load_domain_registry_partial_sources(self, wiki_compile, tmp_path):
        """Domain with one missing and one existing source is included (missing handled in compile)."""
        adr_dir = tmp_path / "docs" / "decisions" / "adr"
        adr_dir.mkdir(parents=True)
        existing = adr_dir / "adr_exists.md"
        existing.write_text("# ADR exists", encoding="utf-8")

        config = tmp_path / "config.yaml"
        config.write_text(
            f"wiki_domains:\n"
            f"  my_domain:\n"
            f"    - {existing.relative_to(tmp_path)!s}\n"
            f"    - docs/decisions/adr/missing.md\n",
            encoding="utf-8",
        )

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = wiki_compile.load_domain_registry(config_path=config)
        finally:
            os.chdir(original_cwd)

        # Domain is included because at least one source exists
        assert "my_domain" in result
        # Full source list is kept (compile_domain handles per-file missing)
        assert len(result["my_domain"]["sources"]) == 2
