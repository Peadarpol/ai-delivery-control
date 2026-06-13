import json
import subprocess
from pathlib import Path

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
        )
        if res.returncode == 0:
            msg = res.stdout.lower()
            return any(
                k in msg for k in ["refactor", "rename", "restructure", "reorganize"]
            )
    except Exception:
        pass
    return False


def get_git_co_changes() -> dict[str, dict[str, float]]:
    """Parse git history to extract conditional co-change probabilities."""
    co_changes = {}
    try:
        result = subprocess.run(
            ["git", "log", "--name-only", "-n", "200", "--pretty=format:"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(PROJECT_ROOT),
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
            py_files = [
                f for f in commit_files if f.endswith(".py") and f.startswith("src/")
            ]
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

            if p2_given_1 >= 0.05:
                co_changes[f1][f2] = p2_given_1
            if p1_given_2 >= 0.05:
                co_changes[f2][f1] = p1_given_2

    except Exception:
        pass

    return co_changes


def get_ast_imports() -> dict[str, list[str]]:
    """Fetch AST import linkages from the repo_map cache."""
    imports_map = {}
    if REPO_CACHE_PATH.exists():
        try:
            with open(REPO_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for filepath, val in data.items():
                    imports = val.get("imports", [])
                    imports_map[filepath] = imports
        except Exception:
            pass
    return imports_map


def build_co_change_map() -> dict:
    """Build the consolidated co-change and AST imports metadata map."""
    git_probs = get_git_co_changes()
    ast_imports = get_ast_imports()

    return {"git_probabilities": git_probs, "ast_imports": ast_imports}


def load_co_change_map(force_rebuild: bool = False) -> dict:
    """Load co-change map from cache, rebuilding if invalidated or missing."""
    if not force_rebuild and not check_refactor_keyword() and CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Build and cache
    data = build_co_change_map()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
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
