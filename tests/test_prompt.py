"""
Prompt calibration regression tests (QA-02).

These tests are regression guards, not exhaustive coverage.
If a prompt refactor changes the phrasing, update these tests
to match the new phrasing — but verify the calibration intent
is preserved. The goal is preventing accidental removal of:
  1. Proportionality instruction
  2. False positive guard
  3. Severity definitions
  4. FAIL citation requirement
"""


class TestPromptCalibration:
    """Guard against accidental removal of calibration language."""

    def test_prompt_contains_proportionality_instruction(self, ai_review):
        """The prompt must instruct proportionate verdicts."""
        # Normalize whitespace — prompt text wraps across lines.
        prompt = " ".join(ai_review.SYSTEM_PROMPT.lower().split())
        assert "pass is the correct verdict" in prompt or \
               "pass is the right verdict" in prompt, \
               "Missing proportionality instruction — PASS must be explicitly named as correct for clean diffs"

    def test_prompt_contains_false_positive_guard(self, ai_review):
        """The prompt must guard against manufacturing issues."""
        prompt = " ".join(ai_review.SYSTEM_PROMPT.lower().split())
        assert "do not manufacture" in prompt, \
               "Missing false positive guard — prompt must instruct against manufacturing issues"

    def test_prompt_contains_severity_calibration(self, ai_review):
        """HIGH, MEDIUM, LOW severity definitions must be present."""
        prompt = ai_review.SYSTEM_PROMPT
        assert "HIGH:" in prompt, "Missing HIGH severity definition"
        assert "MEDIUM:" in prompt, "Missing MEDIUM severity definition"
        assert "LOW:" in prompt, "Missing LOW severity definition"

    def test_prompt_does_not_contain_assume_wrong(self, ai_review):
        """BUG-06: The adversarial 'assume wrong' framing must be removed."""
        prompt = " ".join(ai_review.SYSTEM_PROMPT.lower().split())
        assert "assume the implementation is wrong" not in prompt, \
               "BUG-06 regression: 'assume wrong until proven otherwise' causes 100% FAIL rate"
        assert "assume wrong" not in prompt

    def test_prompt_requires_citation_for_fail(self, ai_review):
        """FAIL verdicts must require specific file:line citations."""
        prompt = " ".join(ai_review.SYSTEM_PROMPT.lower().split())
        assert "file:line" in prompt, \
               "Missing FAIL citation requirement — vague FAILs must be prevented"

    def test_prompt_contains_concern_labels(self, ai_review):
        """All concern labels must be defined in the prompt."""
        prompt = ai_review.SYSTEM_PROMPT
        required_labels = [
            "BRANCH_ISOLATION",
            "TRANSACTIONAL_INTEGRITY",
            "MASS_ASSIGNMENT",
            "INTENT_MISMATCH",
            "SECURITY_VULNERABILITY",
            "CODE_QUALITY",
        ]
        for label in required_labels:
            assert label in prompt, f"Missing concern label: {label}"
