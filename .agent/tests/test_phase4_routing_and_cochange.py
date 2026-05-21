import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Paths
ROOT = Path("c:/projects/Gym_App")
sys.path.insert(0, str(ROOT / ".agent" / "skills" / "senior-architect" / "scripts"))
sys.path.insert(0, str(ROOT / ".agent" / "scripts"))

AI_REVIEW_PATH = ROOT / "src" / "scripts" / "ai_review.py"
CO_CHANGE_PATH = ROOT / ".agent" / "scripts" / "co_change_check.py"
WIKI_LINT_PATH = ROOT / ".agent" / "scripts" / "wiki_lint.py"


def import_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load the modules to test
ai_review = import_module_from_path("ai_review", AI_REVIEW_PATH)
co_change = import_module_from_path("co_change_check", CO_CHANGE_PATH)
wiki_lint = import_module_from_path("wiki_lint", WIKI_LINT_PATH)


def test_safe_symbol_behavior():
    """Test emoji safe symbol degrades gracefully based on console encoding."""
    # Mocking stdout as a MagicMock having different encodings
    mock_stdout = MagicMock()

    # 1. UTF-8 support
    mock_stdout.encoding = "utf-8"
    with patch("sys.stdout", mock_stdout):
        res = ai_review._safe_symbol("⚡", "[START]")
        assert res == "⚡"

    # 2. Restrictive ASCII support
    mock_stdout.encoding = "ascii"
    with patch("sys.stdout", mock_stdout):
        res = ai_review._safe_symbol("⚡", "[START]")
        assert res == "[START]"


def test_route_decision_pydantic_validation():
    """Test that RouteDecision model can be instantiated and validated."""
    decision = ai_review.RouteDecision(
        selected_tools=["BRANCH_ISOLATION"],
        review_intensity="standard",
        rationale="Only database file changed.",
        policy_notes=["Skipped some checks."],
    )
    assert decision.review_intensity == "standard"
    assert "BRANCH_ISOLATION" in decision.selected_tools


def test_path_routing_logic():
    """Test dynamic routing triggers correct tools depending on modified file paths."""
    # Scenario A: Modify database repositories
    decision_repo = ai_review.build_route_decision(
        ["src/infrastructure/database/repositories/member.py"], "", {}
    )
    assert "BRANCH_ISOLATION" in decision_repo.selected_tools
    assert "TRANSACTIONAL_INTEGRITY" in decision_repo.selected_tools

    # Scenario B: Modify Pydantic domain schema files
    decision_schema = ai_review.build_route_decision(
        ["src/domain/schemas/member.py"], "", {}
    )
    assert "MASS_ASSIGNMENT" in decision_schema.selected_tools


def test_adr_annotations_override_routing():
    """Test that `# ADRs:` annotations in files successfully override routing selections."""
    # Mock extracting annotations from the file
    with (
        patch(
            "architecture_checks.extract_adr_annotations",
            return_value=["branch_isolation"],
        ),
        patch("pathlib.Path.exists", return_value=True),
    ):
        decision = ai_review.build_route_decision(["src/some_other_file.py"], "", {})
        assert "BRANCH_ISOLATION" in decision.selected_tools


def test_pagerank_intensity_escalation():
    """Test that files in Top 10/3 PageRank scores trigger elevated/critical intensity."""
    pagerank_scores = {
        "src/infrastructure/database/repositories/base.py": 0.45,
        "src/infrastructure/database/repositories/member.py": 0.25,
        "src/application/services/member.py": 0.15,
        "src/domain/schemas/member.py": 0.05,
        "src/some_file.py": 0.01,
    }

    # Staging "src/domain/schemas/member.py" (which is not in top 3, but in top 10)
    decision_elevated = ai_review.build_route_decision(
        ["src/domain/schemas/member.py"], "", pagerank_scores
    )
    assert decision_elevated.review_intensity == "elevated"

    # Staging "src/infrastructure/database/repositories/base.py" (which is in top 3)
    decision_critical = ai_review.build_route_decision(
        ["src/infrastructure/database/repositories/base.py"], "", pagerank_scores
    )
    assert decision_critical.review_intensity == "critical"


def test_critical_intensity_warn_to_fail():
    """Test that all WARN verdicts are escalated to FAIL under critical intensity."""
    # Mocking call to Anthropic returning a WARN verdict
    mock_review_warn = {
        "verdict": "WARN",
        "intent_alignment": "Intent aligned.",
        "issues": [
            {
                "severity": "MEDIUM",
                "concern": "CODE_QUALITY",
                "location": "base.py:12",
                "description": "Small redundant variable.",
                "remediation": "Remove it.",
            }
        ],
        "summary": "Some warnings.",
    }

    # Patch call_anthropic to return our mock WARN dict
    with (
        patch("ai_review.get_staged_diff", return_value="some diff"),
        patch(
            "ai_review.check_preflight_shortcut",
            return_value=ai_review.PlanOutput(
                requires_review=True, direct_pass_allowed=False, planner_note=""
            ),
        ),
        patch("ai_review.load_review_context", return_value=""),
        patch("repo_map.generate_repo_map", return_value=""),
        patch("repo_map.get_pagerank_scores", return_value={"src/base.py": 0.99}),
        patch("ai_review.get_adr_context", return_value=("", [], [])),
        patch("co_change_check.run_co_change_estimator", return_value=[]),
        patch("ai_review.call_anthropic", return_value=mock_review_warn),
        patch("ai_review.consensus_filter", return_value=mock_review_warn),
        patch("ai_review._persist_verdict"),
        patch("ai_review.render_review"),
        patch("builtins.print"),
    ):
        # Staging "src/base.py", which will trigger critical intensity because it is in top 3
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value.returncode = 0
            mock_sub.return_value.stdout = "src/base.py\n"

            # Run the review logic
            exit_code = ai_review._run_review()

            # The exit code should be 1 (blocked) since WARN is promoted to FAIL
            assert exit_code == 1


def test_co_change_estimator_caching_and_invalidation():
    """Test that the co-change estimator caches its results and invalidates on refactor commits."""
    mock_map = {"git_probabilities": {"src/a.py": {"src/b.py": 0.8}}, "ast_imports": {}}

    # 1. Cache loading
    with (
        patch("co_change_check.load_co_change_map", return_value=mock_map) as mock_load,
        patch("co_change_check.check_refactor_keyword", return_value=False),
    ):
        co_change.run_co_change_estimator(["src/a.py"])
        # Estimator runs and loads cache
        assert mock_load.call_count == 1

    # 2. Cache Invalidation on "refactor" keyword in last commit
    with (
        patch("co_change_check.check_refactor_keyword", return_value=True),
        patch(
            "co_change_check.build_co_change_map", return_value=mock_map
        ) as mock_build,
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open", mock_open()),
    ):
        # force_rebuild or refactor keyword causes rebuild
        co_change.load_co_change_map()
        assert mock_build.call_count == 1


def test_co_change_estimator_graceful_degradation():
    """Test that co-change estimator degrades gracefully to AST-only if git commands fail."""
    mock_imports = {"src/a.py": ["src/b.py"]}
    mock_map = {"git_probabilities": {}, "ast_imports": mock_imports}

    with patch("co_change_check.load_co_change_map", return_value=mock_map):
        # Staging src/a.py
        warnings = co_change.run_co_change_estimator(["src/a.py"])

        # Should fall back to AST-only and detect a MEDIUM confidence warning for src/b.py
        assert len(warnings) == 1
        assert warnings[0]["confidence"] == "MEDIUM"
        assert "src/b.py" in warnings[0]["unstaged"]
