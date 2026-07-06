"""
Deterministic characterization test for co_change_core — written BEFORE any refactoring.

This test builds a TEMPORARY git repo inside tmp_path with a KNOWN, hardcoded sequence
of commits and points get_git_co_changes at that repo (by monkeypatching PROJECT_ROOT).
It asserts EXACT probability values computed by hand from the fixture — not just >= 0.05.

The test MUST fail if any computed probability changes. That is its entire purpose.
"""

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants: where co_change_core lives in the harness repo
# ---------------------------------------------------------------------------

_HARNESS_ROOT = Path(__file__).resolve().parents[1]
_CO_CHANGE_CORE_SRC = _HARNESS_ROOT / ".agent" / "scripts" / "co_change_core.py"


# ---------------------------------------------------------------------------
# Fixture: build a temporary git repo with known commit history
# ---------------------------------------------------------------------------

def _create_tmp_git_repo(base_dir: Path) -> Path:
    """Create a temporary git repo with hardcoded commits and return its path.

    Commit sequence (5 total commits):

        Commit 1: src/a.py + src/b.py           (both touched together)
        Commit 2: src/a.py + src/b.py           (co-change again — pair_freq(a,b)=2, file_freq(a)=2, file_freq(b)=2)
        Commit 3: src/a.py                        (a alone — file_freq(a)=3)
        Commit 4: src/c.py + docs/x.md            (c with non-Python — only c counted)
        Commit 5: tests/foo.py                    (.py OUTSIDE src/ — must be excluded)

    Expected probability calculations (hand-computed):

        pair (src/a.py, src/b.py): pair_freq=2
            P(b|a) = 2/3                       (>= 0.05 → included)
            P(a|b) = 2/2 = 1.0               (>= 0.05 → included)

        src/c.py: appears in commit 4 alone among .py files → file_freq(c)=1, no pairs
                    → never enters co_changes dict (no partner to form pair with that meets floor)
        tests/foo.py: excluded because it doesn't start with "src/"
    """
    repo = base_dir / "test_repo"
    repo.mkdir(parents=True, exist_ok=True)

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, cwd=str(repo),
        )

    git("init")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test User")

    def add_commit(files_to_add: dict[str, str], message: str):
        for relpath, content in files_to_add.items():
            target = repo / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        git("add", ".")
        git("commit", "-m", message)

    # Commit 1: src/a.py + src/b.py
    add_commit(
        {"src/a.py": "X", "src/b.py": "Y"},
        "initial commit: add a and b",
    )

    # Commit 2: src/a.py + src/b.py (modify both)
    add_commit(
        {"src/a.py": "X2", "src/b.py": "Y2"},
        "update a and b together",
    )

    # Commit 3: src/a.py only
    add_commit(
        {"src/a.py": "X3"},
        "refactor a alone",
    )

    # Commit 4: src/c.py + docs/x.md
    add_commit(
        {"src/c.py": "Z", "docs/x.md": "# Docs"},
        "add c and docs",
    )

    # Commit 5: tests/foo.py (outside src/ — must be excluded)
    add_commit(
        {"tests/foo.py": "import src.a"},
        "add test file outside src",
    )

    return repo


# ---------------------------------------------------------------------------
# Helpers to load co_change_core and monkeypatch PROJECT_ROOT for a temp repo
# ---------------------------------------------------------------------------

def _make_patched_co_change_mod():
    """Import the real co_change_core module, then prepare it for monkeypatching.

    Returns (mod, cleanup_fn).  The cleanup_fn removes the module from sys.modules.
    """
    name = "_test_cc_mono"
    sys.modules.pop(name, None)

    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(_CO_CHANGE_CORE_SRC))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod, name


def _patch_project_root(mod: type, repo_path: Path):
    """Monkeypatch PROJECT_ROOT, CACHE_PATH, REPO_CACHE_PATH on the module.

    Parameters
    ----------
    repo_path : Path
        The path to the GIT REPO itself (not its parent), since the module runs
        `git log ... cwd=str(PROJECT_ROOT)`.
    """
    mod.PROJECT_ROOT = repo_path
    mod.CACHE_PATH = repo_path / ".agent" / "state" / "co_change_map.json"
    mod.REPO_CACHE_PATH = repo_path / ".agent" / "state" / "repo_graph_cache.json"


# ---------------------------------------------------------------------------
# Deterministic tests for get_git_co_changes
# ---------------------------------------------------------------------------


class TestGetGitCoChangesDeterministic:
    """Test get_git_co_changes against a controlled temp git repo."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path):
        self._tmp_path = tmp_path
        self._repo = _create_tmp_git_repo(tmp_path)
        self._mod, self._mod_name = _make_patched_co_change_mod()
        _patch_project_root(self._mod, self._repo)
        yield
        sys.modules.pop(self._mod_name, None)

    def test_returns_dict_with_exact_keys(self):
        """The top-level dict should have exactly src/a.py and src/b.py as keys."""
        result = self._mod.get_git_co_changes()
        assert isinstance(result, dict)
        # src/a.py and src/b.py both co-change — they appear as keys
        assert "src/a.py" in result
        assert "src/b.py" in result

    def test_exact_probability_a_given_b(self):
        """P(a|b) = pair_freq(a,b)/file_freq(b) = 2/2 = 1.0 exactly."""
        result = self._mod.get_git_co_changes()
        actual = result["src/b.py"]["src/a.py"]
        expected = 1.0
        assert actual == pytest.approx(expected, rel=1e-9), \
            f"Expected {expected}, got {actual}"

    def test_exact_probability_b_given_a(self):
        """P(b|a) = pair_freq(a,b)/file_freq(a) = 2/3 exactly."""
        result = self._mod.get_git_co_changes()
        actual = result["src/a.py"]["src/b.py"]
        expected = 2 / 3
        assert actual == pytest.approx(expected, rel=1e-9), \
            f"Expected {expected}, got {actual}"

    def test_c_not_in_co_changes(self):
        """src/c.py never formed a pair meeting the floor → absent from co_changes dict."""
        result = self._mod.get_git_co_changes()
        assert "src/c.py" not in result, \
            "src/c.py should NOT appear as a top-level key (no qualifying co-changes)"

    def test_non_src_py_files_excluded(self):
        """tests/foo.py (.py outside src/) must never appear as a key or value."""
        result = self._mod.get_git_co_changes()
        for key in result:
            assert not key.startswith("tests/"), \
                f"tests/ file {key!r} should be excluded"
        for file_map in result.values():
            for k2 in file_map:
                assert "tests/" not in k2, \
                    f"tests/ file {k2!r} should be excluded from co-change targets"

    def test_non_py_files_excluded(self):
        """docs/x.md must never appear as a key or value."""
        result = self._mod.get_git_co_changes()
        for key in result:
            assert not key.endswith(".md"), f"Key {key!r} should be excluded"
        for file_map in result.values():
            for k2 in file_map:
                assert not k2.endswith(".md"), f"Value {k2!r} should be excluded"

    def test_probability_floor_respected(self):
        """All probabilities >= 0.05."""
        result = self._mod.get_git_co_changes()
        for file_map in result.values():
            for prob in file_map.values():
                assert prob >= 0.05, f"Probability {prob} below floor 0.05"


# ---------------------------------------------------------------------------
# Deterministic tests for run_co_change_estimator — with repo_map cache fixture
# ---------------------------------------------------------------------------

class TestRunCoChangeEstimatorDeterministic:
    """Test run_co_change_estimator against a controlled temp git repo."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path):
        self._tmp_path = tmp_path
        self._repo = _create_tmp_git_repo(tmp_path)

        # Build the repo_map cache so we can test confidence tiering.
        # src/c.py imports src/a.py → creates an AMBIGUOUS warning (no git co-change pair).
        # src/a.py imports src/b.py → but P(b|a)=2/3 >= 0.1 AND has_ast_link → EXTRACTED.
        repo_map = {
            "src/c.py": {"imports": ["src/a.py"]},
            "src/a.py": {"imports": ["src/b.py"]},
        }
        state_dir = self._repo / ".agent" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        repo_cache_path = state_dir / "repo_graph_cache.json"
        repo_cache_path.write_text(json.dumps(repo_map), encoding="utf-8")

        self._mod, self._mod_name = _make_patched_co_change_mod()
        _patch_project_root(self._mod, self._repo)
        yield
        sys.modules.pop(self._mod_name, None)

    def test_returns_list(self):
        result = self._mod.run_co_change_estimator(["src/a.py"])
        assert isinstance(result, list)

    def test_non_py_files_return_empty(self):
        result = self._mod.run_co_change_estimator(["docs/x.md"])
        assert result == []

    def test_output_dict_keys_match_spec(self):
        result = self._mod.run_co_change_estimator(["src/a.py"])
        for item in result:
            assert isinstance(item, dict)
            assert "staged" in item
            assert "unstaged" in item
            assert "confidence" in item
            assert "probability" in item
            assert "reason" in item

    def test_confidence_pinned_to_extracted(self):
        """src/b.py has P(b|a)=2/3 >= 0.1 AND src/a.py imports src/b.py (AST link) → EXTRACTED."""
        result = self._mod.run_co_change_estimator(["src/a.py"])
        tiers = [item["confidence"] for item in result]
        assert "EXTRACTED" in tiers, \
            f"Expected EXTRACTED tier from git co-change + AST linkage; got tiers: {tiers}"

    def test_exactly_one_ambiguous_warning(self):
        """Exactly one AMBIGUOUS warning for src/c.py → src/a.py (no git pair)."""
        result = self._mod.run_co_change_estimator(["src/c.py"])
        ambiguous = [item for item in result if item["confidence"] == "AMBIGUOUS"]
        assert len(ambiguous) == 1, \
            f"Expected exactly 1 AMBIGUOUS warning; got {len(ambiguous)}: {ambiguous}"

    def test_ambiguous_probability_is_zero(self):
        """AMBIGUOUS confidence always has probability=0.0."""
        result = self._mod.run_co_change_estimator(["src/c.py"])
        ambiguous = [item for item in result if item["confidence"] == "AMBIGUOUS"]
        assert len(ambiguous) >= 1
        for item in ambiguous:
            assert item["probability"] == 0.0, \
                f"AMBIGUOUS probability should be 0.0, got {item['probability']}"

    def test_confidence_pinned_to_ambiguous_from_ast_only(self):
        """src/c.py imports src/a.py but has NO git co-change pair → AMBIGUOUS tier (not EXTRACTED/INFERRED)."""
        result = self._mod.run_co_change_estimator(["src/c.py"])
        # Collect all confidence tiers
        tiers = [item["confidence"] for item in result]
        assert "AMBIGUOUS" in tiers, \
            f"Expected AMBIGUOUS tier from AST-only linkage (no git history); got tiers: {tiers}"

    def test_staged_is_string(self):
        result = self._mod.run_co_change_estimator(["src/a.py"])
        for item in result:
            assert isinstance(item["staged"], str)

    def test_unstaged_is_string(self):
        result = self._mod.run_co_change_estimator(["src/a.py"])
        for item in result:
            assert isinstance(item["unstaged"], str)

    def test_reason_is_non_empty_string(self):
        result = self._mod.run_co_change_estimator(["src/a.py"])
        for item in result:
            assert isinstance(item["reason"], str)
            assert len(item["reason"]) > 0

    def test_probability_values_are_floats(self):
        result = self._mod.run_co_change_estimator(["src/a.py"])
        for item in result:
            assert isinstance(item["probability"], float), \
                f"Probability {item['probability']!r} is not a float"


# ---------------------------------------------------------------------------
# Piece 1 (T1-B-09) — return_frequencies parameter tests
# ---------------------------------------------------------------------------

class TestReturnFrequencies:
    """Pin the return_frequencies=True behaviour of get_git_co_changes.

    Uses the same fixture repo and module-patching helpers as the existing
    TestGetGitCoChangesDeterministic class so the two test suites are compared
    against the same controlled commit history.

    Acceptance criteria (SPEC §1.3):
      test_default_return_unchanged_by_new_param  — AC-1
      test_frequencies_returned_as_tuple          — AC-2
      test_exact_pair_frequency                   — AC-3
      test_frequency_key_is_sorted_tuple          — AC-4
    """

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path):
        self._tmp_path = tmp_path
        self._repo = _create_tmp_git_repo(tmp_path)
        self._mod, self._mod_name = _make_patched_co_change_mod()
        _patch_project_root(self._mod, self._repo)
        yield
        sys.modules.pop(self._mod_name, None)

    # AC-1: Default path is unchanged
    def test_default_return_unchanged_by_new_param(self):
        """Both call forms without return_frequencies=True return the same dict.

        Also validates that the returned dict still equals the hand-computed
        values pinned by the existing characterization tests (a|b=1.0, b|a=2/3).
        """
        result_default = self._mod.get_git_co_changes()
        result_explicit_false = self._mod.get_git_co_changes(return_frequencies=False)

        # Both are plain dicts (not tuples)
        assert isinstance(result_default, dict), \
            "Default call must return a dict, not a tuple"
        assert isinstance(result_explicit_false, dict), \
            "return_frequencies=False must return a dict, not a tuple"

        # Values must be equal (same probabilities)
        assert result_default == result_explicit_false, \
            "Default and explicit-False calls must produce identical dicts"

        # Cross-check against the pinned probability values from the existing tests
        import pytest as _pytest
        assert result_default["src/b.py"]["src/a.py"] == _pytest.approx(1.0, rel=1e-9), \
            "P(a|b) must still be 1.0"
        assert result_default["src/a.py"]["src/b.py"] == _pytest.approx(2 / 3, rel=1e-9), \
            "P(b|a) must still be 2/3"

    # AC-2: Tuple is returned and element 0 equals default dict
    def test_frequencies_returned_as_tuple(self):
        """return_frequencies=True returns a 2-tuple; element 0 equals the default return."""
        result = self._mod.get_git_co_changes(return_frequencies=True)

        assert isinstance(result, tuple), \
            f"Expected a tuple, got {type(result).__name__}"
        assert len(result) == 2, \
            f"Expected a 2-tuple, got length {len(result)}"

        co_changes, frequencies = result

        # Element 0 must be identical to the plain default return
        expected_dict = self._mod.get_git_co_changes()
        assert co_changes == expected_dict, \
            "Element 0 of the tuple must equal the default dict return"

    # AC-3: Exact commit-count for the known fixture pair
    def test_exact_pair_frequency(self):
        """frequencies[("src/a.py", "src/b.py")] == 2 (co-changed in commits 1 and 2)."""
        _, frequencies = self._mod.get_git_co_changes(return_frequencies=True)

        key = ("src/a.py", "src/b.py")
        assert key in frequencies, \
            f"Expected key {key!r} in frequencies dict; got keys: {list(frequencies.keys())}"
        assert frequencies[key] == 2, \
            f"Expected frequency 2 for the (a, b) pair; got {frequencies[key]}"

    # AC-4: Keys are sorted 2-tuples
    def test_frequency_key_is_sorted_tuple(self):
        """All keys in frequencies are sorted 2-tuples of strings (order-independent lookup)."""
        _, frequencies = self._mod.get_git_co_changes(return_frequencies=True)

        assert len(frequencies) > 0, \
            "frequencies dict must be non-empty for the fixture repo"

        for key in frequencies:
            assert isinstance(key, tuple), \
                f"Key {key!r} is not a tuple"
            assert len(key) == 2, \
                f"Key {key!r} is not a 2-tuple"
            f1, f2 = key
            assert isinstance(f1, str) and isinstance(f2, str), \
                f"Key elements must be strings, got {type(f1).__name__}, {type(f2).__name__}"
            assert f1 <= f2, \
                f"Key {key!r} is not sorted — f1 must be <= f2 for order-independent lookup"