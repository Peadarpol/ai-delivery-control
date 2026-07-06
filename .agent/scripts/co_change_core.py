"""Core co-change computation logic — extracted verbatim from co_change_check.py (SPEC §5).

All function bodies are unchanged. Only get_git_co_changes receives new parameters
(commit_window, file_filter, prob_floor) with defaults that reproduce original behaviour.
"""

import json
import subprocess
from pathlib import Path

import sys
try:
    from harness_utils import _safe_git_env
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "scripts"))
    from harness_utils import _safe_git_env

# Resolve PROJECT_ROOT
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
CACHE_PATH = PROJECT_ROOT / ".agent" / "state" / "co_change_map.json"
REPO_CACHE_PATH = PROJECT_ROOT / ".agent" / "state" / "repo_graph_cache.json"


def check_refactor_keyword() -> bool:
    """Return True if the last git commit message contains refactoring keywords."""
    try:
        res = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(PROJECT_ROOT),
            env=_safe_git_env()
        )
        if res.returncode == 0:
            msg = res.stdout.lower()
            return any(
                k in msg for k in ["refactor", "rename", "restructure", "reorganize"]
            )
    except Exception:
        pass
    return False


def get_git_co_changes(
    commit_window: int = 200,
    file_filter=None,
    prob_floor: float = 0.05,
    project_root: Path | None = None,
    return_frequencies: bool = False,
) -> "dict[str, dict[str, float]] | tuple[dict[str, dict[str, float]], dict[tuple[str, str], int]]":
    """Parse git history to extract conditional co-change probabilities.

    Parameters ----------
    commit_window : int, default 200
        Number of recent commits to inspect (passed to ``-n``).
    file_filter : callable or None, default None
        Predicate ``f -> bool`` that selects which files to count.
        When *None* or unset the original heuristic is used:
        ``f.endswith(".py") and f.startswith("src/")``.
    prob_floor : float, default 0.05
        Minimum conditional probability to record as a co-change edge.
    project_root : Path or None, default None
        Override the git repository root. When *None*, uses MODULE-level PROJECT_ROOT.
    return_frequencies : bool, default False
        When *False* (default), returns the co-change probability dict — byte-identical
        to the original behaviour; no callers are affected.
        When *True*, returns a 2-tuple ``(co_changes, frequencies)`` where
        ``co_changes`` is the same dict and ``frequencies`` is a
        ``dict[tuple[str, str], int]`` mapping each sorted file-pair to the number of
        commits in which both files changed (the internal ``pair_freq``).
    """
    # Restore original predicate when file_filter is not set (backward compat)
    if file_filter is None:
        file_filter = lambda f: f.endswith(".py") and f.startswith("src/")

    root = project_root or PROJECT_ROOT

    co_changes = {}
    pair_freq: dict = {}
    try:
        result = subprocess.run(
            ["git", "log", "--name-only", "-n", str(commit_window), "--pretty=format:"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(root),
            env=_safe_git_env()
        )
        if result.returncode != 0:
            return {}

        # Parse commits
        commits = []
        current_commit = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                if current_commit:
                    commits.append(set(current_commit))
                    current_commit = []
            else:
                current_commit.append(line.replace("\\", "/"))
        if current_commit:
            commits.append(set(current_commit))

        # Compute frequencies
        file_freq = {}
        pair_freq = {}

        for commit_files in commits:
            # Filter only Python or domain files to keep graph clean
            py_files = [f for f in commit_files if file_filter(f)]
            for f in py_files:
                file_freq[f] = file_freq.get(f, 0) + 1

            for i, f1 in enumerate(py_files):
                for f2 in py_files[i + 1 :]:
                    pair = tuple(sorted([f1, f2]))
                    pair_freq[pair] = pair_freq.get(pair, 0) + 1

        # Calculate conditional probabilities P(B | A)
        for pair, freq in pair_freq.items():
            f1, f2 = pair
            p2_given_1 = freq / file_freq[f1]
            p1_given_2 = freq / file_freq[f2]

            if f1 not in co_changes:
                co_changes[f1] = {}
            if f2 not in co_changes:
                co_changes[f2] = {}

            if p2_given_1 >= prob_floor:
                co_changes[f1][f2] = p2_given_1
            if p1_given_2 >= prob_floor:
                co_changes[f2][f1] = p1_given_2

    except Exception:
        pass

    if return_frequencies:
        return co_changes, pair_freq
    return co_changes


def get_ast_imports(repo_cache_path: Path | None = None) -> dict[str, list[str]]:
    """Fetch AST import linkages from the repo_map cache.

    Parameters
    ----------
    repo_cache_path : Path or None
        Override the default REPO_CACHE_PATH. When *None*, uses the module-level
        constant.
    """
    path = repo_cache_path or REPO_CACHE_PATH
    imports_map: dict[str, list[str]] = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for filepath, val in data.items():
                    imports = val.get("imports", [])
                    imports_map[filepath] = imports
        except Exception:
            pass
    return imports_map


def build_co_change_map(
    project_root: Path | None = None,
    repo_cache_path: Path | None = None,
) -> dict:
    """Build the consolidated co-change and AST imports metadata map."""
    git_probs = get_git_co_changes(project_root=project_root)
    ast_imports = get_ast_imports(repo_cache_path)

    return {"git_probabilities": git_probs, "ast_imports": ast_imports}


def load_co_change_map(
    force_rebuild: bool = False,
    project_root: Path | None = None,
    repo_cache_path: Path | None = None,
) -> dict:
    """Load co-change map from cache, rebuilding if invalidated or missing."""
    root = project_root or PROJECT_ROOT
    cache_path = root / ".agent" / "state" / "co_change_map.json"

    if not force_rebuild and not check_refactor_keyword() and cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Build and cache
    data = build_co_change_map(project_root=root, repo_cache_path=repo_cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
    return data


def run_co_change_estimator(changed_files: list[str]) -> list[dict]:
    """
    Evaluates changed staged files against unstaged repository files.
    Returns warnings for potential missing co-changes (HIGH or MEDIUM confidence).
    """
    normalized_changed = [f.replace("\\", "/") for f in changed_files]
    co_change_map = load_co_change_map()

    git_probs = co_change_map.get("git_probabilities", {})
    ast_imports = co_change_map.get("ast_imports", {})

    warnings = []
    checked_pairs = set()

    for staged_file in normalized_changed:
        if not staged_file.endswith(".py"):
            continue

        # Look up git co-change correlations
        correlations = git_probs.get(staged_file, {})
        for other_file, prob in correlations.items():
            if other_file in normalized_changed:
                continue

            pair = (staged_file, other_file)
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)

            # Check if there is also an AST import relationship (either direction)
            staged_imports = ast_imports.get(staged_file, [])
            other_imports = ast_imports.get(other_file, [])
            has_ast_link = (other_file in staged_imports) or (
                staged_file in other_imports
            )

            # Determine confidence
            if prob >= 0.1 and has_ast_link:
                warnings.append(
                    {
                        "staged": staged_file,
                        "unstaged": other_file,
                        "confidence": "EXTRACTED",
                        "probability": prob,
                        "reason": f"File '{other_file}' has both a historical co-change correlation ({prob:.1%}) and direct import relationship with staged '{staged_file}'.",
                    }
                )
            elif prob >= 0.2:
                warnings.append(
                    {
                        "staged": staged_file,
                        "unstaged": other_file,
                        "confidence": "INFERRED",
                        "probability": prob,
                        "reason": f"File '{other_file}' has a high historical co-change correlation ({prob:.1%}) with staged '{staged_file}'.",
                    }
                )

        # Also find direct AST imports that aren't in git history (as AMBIGUOUS warnings)
        staged_imports = ast_imports.get(staged_file, [])
        for imported_file in staged_imports:
            if imported_file in normalized_changed or not imported_file.endswith(".py"):
                continue

            pair = (staged_file, imported_file)
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)

            # If it's a direct import and hasn't been flagged, list as ambiguous
            warnings.append(
                {
                    "staged": staged_file,
                    "unstaged": imported_file,
                    "confidence": "AMBIGUOUS",
                    "probability": 0.0,
                    "reason": f"File '{imported_file}' is imported by staged '{staged_file}' but is not staged.",
                }
            )

    return warnings
