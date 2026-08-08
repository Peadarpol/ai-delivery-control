"""
Unit and integration tests for Phase A Stage 1 & Stage 2 Gherkin Scenario Parser & Component Matcher (.agent/scripts/loop_closure_check.py).
"""

import re
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / ".agent" / "scripts"))

from loop_closure_check import (
    Scenario,
    extract_terms,
    normalize_component,
    search_component,
    parse_spec_file,
    run_stage1_self_test,
    run_stage2_self_test,
    scan_corpus,
)


def test_extract_terms_patterns():
    """Test component and key-term extraction rules."""
    text = (
        "Given `architecture_checks.py`'s disposition() method and `wiring_consumers.yaml` "
        "when calling `record_decision()` with `baseline=` and `touched_files=` under `HIB-080` "
        "then return `PARTIALLY-WIRED` status."
    )
    terms = extract_terms(text)

    assert "architecture_checks.py" in terms
    assert "disposition()" in terms
    assert "wiring_consumers.yaml" in terms
    assert "record_decision()" in terms
    assert "baseline=" in terms
    assert "touched_files=" in terms
    assert "HIB-080" in terms
    assert "PARTIALLY-WIRED" in terms


def test_fix1_rule6_regex():
    """Fix 1 test: Assert rule 6 regex matches uppercase tokens starting/ending with alphanumerics."""
    pattern = r'\b[A-Z0-9][A-Z0-9_\-]*[A-Z0-9]\b'
    matches = re.findall(pattern, "pre-HIB-080-fix")
    assert matches == ["HIB-080"]


def test_non_overlapping_textual_substrings():
    """Fix 2 test: Assert two non-overlapping backticked terms survive as separate entries even if one is a substring."""
    text = "When comparing `git diff --name-only HEAD` against `git diff --name-only HEAD^1` in tests."
    terms = extract_terms(text)

    assert "git diff --name-only HEAD" in terms
    assert "git diff --name-only HEAD^1" in terms


def test_extract_terms_substring_deduplication():
    """Verify that same-span overlapping sub-matches are deduplicated while preserving maximal span."""
    text = "Given `SPEC-enforcement-postures` is evaluated."
    terms = extract_terms(text)

    assert terms == ["SPEC-enforcement-postures"]
    assert "SPEC-enforcement" not in terms
    assert "SPEC" not in terms


def test_normalize_component():
    """Verify component normalization mapping rules."""
    assert normalize_component("architecture_checks.py") == ("architecture_checks", True)
    assert normalize_component("disposition()") == ("disposition", True)
    assert normalize_component("baseline=") == ("baseline", True)
    assert normalize_component("wiring_consumers.yaml") == ("wiring_consumers", True)
    assert normalize_component("HIB-080") == ("HIB-080", False)
    assert normalize_component("SPEC-enforcement-postures.md") == ("SPEC-enforcement-postures.md", False)
    assert normalize_component("PARTIALLY-WIRED") == ("PARTIALLY-WIRED", True)


def test_stage2_self_test():
    """Verify that Stage 2 self-test passes against 3 ground truth cases + tag check."""
    assert run_stage2_self_test(PROJECT_ROOT) is True


def test_parse_spec_file_gherkin(tmp_path: Path):
    """Test parsing Gherkin scenarios with Given/When/Then/And and multiline continuations."""
    spec_content = """
# Sample Spec Title

## Section Header

### Scenario 1: Basic Scenario
Given a component `foo.py`
And an initial state `bar()`
When `foo.py` executes with `param=`
Then outcome `SUCCESS` is returned
And log event `EVENT_OK` is emitted.

### Scenario 2: Multi-line Continuation
Given a multi-line description
  that continues on the next line
When action occurs
Then output is valid.
"""
    spec_file = tmp_path / "SPEC-sample.md"
    spec_file.write_text(spec_content, encoding="utf-8")

    scenarios = parse_spec_file(spec_file)

    assert len(scenarios) == 2

    # Scenario 1 assertions
    scen1 = scenarios[0]
    assert scen1.scenario_id == "Scenario 1"
    assert scen1.title == "Basic Scenario"
    assert scen1.given_clauses == ["a component `foo.py`", "an initial state `bar()`"]
    assert scen1.when_clauses == ["`foo.py` executes with `param=`"]
    assert scen1.then_clauses == ["outcome `SUCCESS` is returned", "log event `EVENT_OK` is emitted."]

    assert "foo.py" in scen1.components
    assert "bar()" in scen1.components
    assert "param=" in scen1.components
    assert "SUCCESS" in scen1.key_terms
    assert "EVENT_OK" in scen1.key_terms

    # Scenario 2 assertions
    scen2 = scenarios[1]
    assert scen2.scenario_id == "Scenario 2"
    assert scen2.given_clauses == ["a multi-line description that continues on the next line"]


def test_run_stage1_self_test():
    """Verify that mandatory Stage 1 self-test passes against SPEC-loop-closure-verification.md."""
    spec_path = PROJECT_ROOT / "docs" / "planning" / "specs" / "archive" / "SPEC-loop-closure-verification.md"
    assert spec_path.exists()
    assert run_stage1_self_test(spec_path) is True


def test_scan_corpus():
    """Verify scanning the full docs/planning/specs/ directory."""
    specs_dir = PROJECT_ROOT / "docs" / "planning" / "specs"
    scanned, skipped, scenarios = scan_corpus(specs_dir)

    assert scanned > 0
    assert len(scenarios) > 0
    assert scanned == skipped + len(set(s.spec_path for s in scenarios))
