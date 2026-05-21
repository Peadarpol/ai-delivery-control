import importlib.util
import sys
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

# Paths
ROOT = Path("c:/projects/Gym_App")
sys.path.insert(0, str(ROOT / ".agent" / "skills" / "senior-architect" / "scripts"))
sys.path.insert(0, str(ROOT / ".agent" / "scripts"))

ARCH_CHECKS_PATH = (
    ROOT
    / ".agent"
    / "skills"
    / "senior-architect"
    / "scripts"
    / "architecture_checks.py"
)
REPO_MAP_PATH = (
    ROOT / ".agent" / "skills" / "senior-architect" / "scripts" / "repo_map.py"
)
AI_REVIEW_PATH = ROOT / "src" / "scripts" / "ai_review.py"


# Helper to dynamically import modules
def import_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Import the modules
arch_checks = import_module_from_path("architecture_checks", ARCH_CHECKS_PATH)
repo_map = import_module_from_path("repo_map", REPO_MAP_PATH)
ai_review = import_module_from_path("ai_review", AI_REVIEW_PATH)


def test_extract_adr_annotations_regex():
    """Test regex extraction for multiple formats (spacing, case-insensitivity)."""
    cases = [
        (
            "# ADRs: branch_isolation, multi_branch_schema",
            ["branch_isolation", "multi_branch_schema"],
        ),
        ("# adr: clean_architecture", ["clean_architecture"]),
        (
            "  #   AdRs: saas_architecture,pos_booking_payments  ",
            ["saas_architecture", "pos_booking_payments"],
        ),
        ("# ADRs:   ", []),
        ("# unrelated comment", []),
    ]
    for comment_line, expected in cases:
        mock_data = mock_open(read_data=comment_line + "\n")
        with patch("builtins.open", mock_data):
            res = arch_checks.extract_adr_annotations("dummy.py")
            assert res == expected, f"Failed on: {comment_line}"


def test_adr_annotations_count_warning():
    """Test that check_adr_annotations_count logs a soft warning for >3 domains and does not exit."""
    # We patch Path.rglob to yield a single file that has 4 annotations
    mock_path = Path("src/mock_file.py")
    with (
        patch("pathlib.Path.rglob", return_value=[mock_path]),
        patch(
            "architecture_checks.extract_adr_annotations",
            return_value=["d1", "d2", "d3", "d4"],
        ),
        patch("builtins.print") as mock_print,
    ):
        arch_checks.check_adr_annotations_count()
        # Ensure it printed the warning
        assert mock_print.call_count >= 2
        # Check that sys.exit was not called (would have raised SystemExit otherwise)


def test_pagerank_algorithm():
    """Test mathematical correctness of pure Python PageRank power iteration."""
    nodes = ["A", "B", "C"]
    edges = {"A": ["B", "C"], "B": ["C"], "C": ["A"]}
    # No personalization
    personalization = {n: 1.0 for n in nodes}
    scores = repo_map.compute_pagerank(nodes, edges, personalization, max_iter=100)

    # Assert scores sum to 1.0 approximately
    assert pytest.approx(sum(scores.values())) == 1.0

    # Assert all nodes have positive scores
    for n in nodes:
        assert scores[n] > 0.0


def test_pagerank_personalization():
    """Test that changed files and their neighbors receive higher personalized scores."""
    nodes = ["src/a.py", "src/b.py", "src/c.py"]

    # Mock cache load to avoid reading filesystem
    with (
        patch("repo_map.load_cache", return_value={}),
        patch("repo_map.save_cache"),
        patch("repo_map.parse_file_imports_and_symbols", return_value=([], [])),
        patch("pathlib.Path.rglob", return_value=[Path(n) for n in nodes]),
        patch("pathlib.Path.stat") as mock_stat,
    ):
        mock_stat.return_value.st_mtime = 12345.0

        # Test personalization boost with src/a.py changed (no edges, pure personalization)
        scores = repo_map.get_pagerank_scores(["src/a.py"])

        # With no edges, PageRank scores are exactly proportional to personalization weights:
        # a.py (Modified) weight = 10.0
        # b.py (Unchanged) weight = 1.0
        # c.py (Unchanged) weight = 1.0
        assert scores["src/a.py"] > scores["src/c.py"]
        assert pytest.approx(scores["src/a.py"] / scores["src/c.py"]) == 10.0


def test_ast_parser_error_safety():
    """Test that parsing a file with a SyntaxError gracefully degrades instead of raising an error."""
    bad_code = "class BadSyntax\n   def hello():"
    with patch("pathlib.Path.read_text", return_value=bad_code):
        imports, symbols = repo_map.parse_file_imports_and_symbols(Path("dummy.py"))
        # SyntaxError should be caught, returning empty lists
        assert imports == []
        assert symbols == []


def test_strip_wiki_headers():
    """Test the three-step token squeeze's header-stripping logic."""
    wiki_content = """# Branch Isolation
**Compiled**: 2026-05-20
**Sources**: adr_002_multi_tenant_branch_isolation.md

## Summary
Branch isolation summary.

## Related Domains
Multi-tenancy, Security

→ Full source: docs/decisions/adr/adr_002.md"""

    clean = ai_review._strip_wiki_headers(wiki_content)
    # Title, compilation date, sources, Related Domains, and Full source link should be removed
    assert "# Branch Isolation" not in clean
    assert "**Compiled**" not in clean
    assert "**Sources**" not in clean
    assert "## Related Domains" not in clean
    assert "Multi-tenancy" not in clean
    assert "→ Full source:" not in clean
    # Keep only Summary section
    assert "## Summary" in clean
    assert "Branch isolation summary." in clean


def test_budget_based_token_squeeze():
    """Test that get_adr_context respects ≤400 tokens budget and adds policy_notes on suppression."""
    changed_files = ["src/a.py"]

    # We will mock extract_adr_annotations to return multiple domains
    # and mock the files exists and read_text for wiki compilation
    mock_registry = {
        "d1": {"sources": ["s1"], "output": "o1"},
        "d2": {"sources": ["s2"], "output": "o2"},
        "d3": {"sources": ["s3"], "output": "o3"},
    }

    import wiki_compile

    original_registry = wiki_compile.DOMAIN_REGISTRY
    wiki_compile.DOMAIN_REGISTRY = mock_registry

    large_summary = (
        "A " * 350
    )  # ~175 tokens each (700 characters), so 2 fit and 3rd exceeds 400 token budget

    def mock_read_text(self, encoding="utf-8"):
        domain_name = self.stem
        return f"""# {domain_name}
## Summary
{domain_name} summary: {large_summary}"""

    try:
        with (
            patch(
                "architecture_checks.extract_adr_annotations",
                return_value=["d1", "d2", "d3"],
            ),
            patch("repo_map.get_pagerank_scores", return_value={"src/a.py": 1.0}),
            patch("pathlib.Path.rglob", return_value=[Path("src/a.py")]),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", mock_read_text),
        ):
            context_str, active_domains, policy_notes = ai_review.get_adr_context(
                changed_files
            )

            # At least one domain should be active
            assert len(active_domains) >= 1
            # Some domains should be suppressed due to tokens limit (d1, d2, d3 all very large)
            assert len(active_domains) < 3
            # Policy notes should warn about suppressed domains
            assert len(policy_notes) == 1
            assert "suppressed (token budget)" in policy_notes[0]
            assert "suppressed (token budget)" in context_str
    finally:
        wiki_compile.DOMAIN_REGISTRY = original_registry
