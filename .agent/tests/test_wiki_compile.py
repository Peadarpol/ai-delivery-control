import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Dynamically import wiki_compile.py
script_path = Path("c:/projects/Gym_App/.agent/scripts/wiki_compile.py")
spec = importlib.util.spec_from_file_location("wiki_compile", script_path)
wiki_compile = importlib.util.module_from_spec(spec)
sys.modules["wiki_compile"] = wiki_compile
spec.loader.exec_module(wiki_compile)


@pytest.fixture
def mock_env(tmp_path):
    """Setup a temporary environment with mocked paths."""
    config_path = tmp_path / "config.yaml"
    state_path = tmp_path / "wiki_compile_state.json"
    wiki_dir = tmp_path / "wiki"

    # Mock the paths in the module
    with (
        patch.object(wiki_compile, "CONFIG_PATH", config_path),
        patch.object(wiki_compile, "STATE_FILE", state_path),
        patch.object(wiki_compile, "WIKI_DIR", wiki_dir),
    ):
        yield {
            "tmp_path": tmp_path,
            "config": config_path,
            "state": state_path,
            "wiki": wiki_dir,
        }


def test_get_hash_changed_vs_unchanged(tmp_path):
    """Test SHA-256 hash comparison (changed vs unchanged source)."""
    f1 = tmp_path / "f1.txt"
    f2 = tmp_path / "f2.txt"

    f1.write_text("content A")
    f2.write_text("content B")

    hash1 = wiki_compile.get_hash([str(f1), str(f2)])

    # Unchanged
    hash2 = wiki_compile.get_hash([str(f1), str(f2)])
    assert hash1 == hash2

    # Changed
    f1.write_text("content A modified")
    hash3 = wiki_compile.get_hash([str(f1), str(f2)])
    assert hash1 != hash3


def test_incremental_detection_logic(mock_env, monkeypatch):
    """Test only compile when hash differs."""
    # Setup mock registry with one domain
    source_file = mock_env["tmp_path"] / "source.md"
    source_file.write_text("initial content")
    out_file = mock_env["tmp_path"] / "out.md"

    mock_registry = {
        "test_domain": {"sources": [str(source_file)], "output": str(out_file)}
    }

    # Initial state with matching hash
    current_hash = wiki_compile.get_hash([str(source_file)])
    mock_env["state"].write_text(
        json.dumps({"last_source_hashes": {"test_domain": current_hash}})
    )

    with (
        patch.object(wiki_compile, "DOMAIN_REGISTRY", mock_registry),
        patch("sys.argv", ["wiki_compile.py"]),
        patch.object(wiki_compile, "generate_index_md") as mock_gen_index,
    ):

        # Should exit 0 without compiling
        with pytest.raises(SystemExit) as e:
            wiki_compile.main()

        assert e.value.code == 0
        mock_gen_index.assert_called_once()
        assert not out_file.exists()


def test_index_generation(mock_env):
    """Test index generation (correct domain count, status fields)."""
    state = {
        "last_run_utc": "2026-05-20T12:00:00Z",
        "domains_compiled": 1,
        "last_source_hashes": {"clean_architecture": "hash123"},
    }

    wiki_compile.generate_index_md(state)

    index_file = mock_env["wiki"] / "index.md"
    assert index_file.exists()

    content = index_file.read_text()
    assert "**Last compiled**: 2026-05-20T12:00:00Z" in content
    assert "**Pages**: 1 / 12 ready" in content
    assert "| clean_architecture | clean_architecture.md |" in content
    # clean_architecture should be ready because it's in last_source_hashes
    assert "ready |" in content


@patch("wiki_compile.httpx.Client")
def test_graceful_failure_path(mock_client_class, mock_env):
    """Test graceful failure path (API unreachable -> clean exit, no exception)."""
    # Setup mock registry to force compilation
    source_file = mock_env["tmp_path"] / "source.md"
    source_file.write_text("initial content")
    out_file = mock_env["tmp_path"] / "out.md"

    mock_registry = {
        "test_domain": {"sources": [str(source_file)], "output": str(out_file)}
    }

    # Empty state so it compiles
    mock_env["state"].write_text(json.dumps({"last_source_hashes": {}}))

    # Mock client to raise Exception
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    mock_client_instance.post.side_effect = Exception("API Unreachable")

    with (
        patch.object(wiki_compile, "DOMAIN_REGISTRY", mock_registry),
        patch("sys.argv", ["wiki_compile.py"]),
    ):

        # Should exit cleanly (exit 0) and not crash
        with pytest.raises(SystemExit) as e:
            wiki_compile.main()

        assert e.value.code == 0

        # Check that state was updated with 0 compiled
        state = json.loads(mock_env["state"].read_text())
        assert state["domains_compiled"] == 0
        assert "last_source_hashes" in state
        assert "test_domain" not in state["last_source_hashes"]
