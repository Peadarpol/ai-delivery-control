"""
Unit Tests for distill_dream.py — dream phase pattern routing and skill mapping.
"""

import sys
import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_ROOT / ".agent" / "scripts"))

# Safely import the module under test
import importlib.util
spec = importlib.util.spec_from_file_location("distill_dream", WORKSPACE_ROOT / ".agent" / "scripts" / "distill_dream.py")
distill_dream = importlib.util.module_from_spec(spec)
sys.modules["distill_dream"] = distill_dream
spec.loader.exec_module(distill_dream)


@pytest.fixture
def temp_dream_env(tmp_path):
    """Scaffold a temporary environment for dream phase testing."""
    config_dir = tmp_path / ".agent" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    state_dir = tmp_path / ".agent" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    skills_dir = tmp_path / ".agent" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    skill_ownership_path = config_dir / "skill_ownership.yaml"
    review_log_file = tmp_path / ".ai-review-log.jsonl"
    ledger_file = state_dir / "session_ledger.jsonl"
    events_file = state_dir / "harness_events.jsonl"
    proposals_dir = state_dir / "dream_proposals"

    return {
        "tmp_path": tmp_path,
        "skill_ownership_path": skill_ownership_path,
        "review_log_file": review_log_file,
        "ledger_file": ledger_file,
        "events_file": events_file,
        "proposals_dir": proposals_dir,
        "skills_dir": skills_dir,
    }


def test_skill_ownership_yaml_loaded(temp_dream_env):
    """Verify distill_dream.py loads skill_ownership.yaml at startup and maps cleanly."""
    env = temp_dream_env

    # Write yaml directly at the root (no skills: nesting)
    ownership_yaml = {
        "branch-isolation": {
            "check_types": ["BRANCH_ISOLATION"],
            "event_types": ["high_risk_gate_closed"],
            "keywords": ["branch"]
        }
    }
    env["skill_ownership_path"].write_text(yaml.dump(ownership_yaml), encoding="utf-8")

    # Write empty ledger and events files
    env["ledger_file"].write_text("", encoding="utf-8")
    env["events_file"].write_text("", encoding="utf-8")
    env["review_log_file"].write_text("", encoding="utf-8")

    # Mock all Path variables in distill_dream
    with patch("distill_dream.SKILL_OWNERSHIP_PATH", env["skill_ownership_path"]), \
         patch("distill_dream.LEDGER_FILE", env["ledger_file"]), \
         patch("distill_dream.EVENTS_FILE", env["events_file"]), \
         patch("distill_dream.REVIEW_LOG_FILE", env["review_log_file"]), \
         patch("distill_dream.PROPOSALS_DIR", env["proposals_dir"]), \
         patch("distill_dream.SKILLS_DIR", env["skills_dir"]):

        # Run main or individual parsing logic
        # We can test load_state or parse logic by running main with arguments
        with patch("sys.argv", ["distill_dream.py", "--dry-run"]):
            distill_dream.main()


def test_blocking_concern_field_used_for_routing(temp_dream_env):
    """Verify a FAIL verdict with blocking_concern: 'BRANCH_ISOLATION' routes to branch-isolation skill."""
    env = temp_dream_env

    # 1. Setup skill_ownership.yaml
    ownership_yaml = {
        "branch-isolation": {
            "check_types": ["BRANCH_ISOLATION"],
            "event_types": ["high_risk_gate_closed"],
            "keywords": ["branch"]
        }
    }
    env["skill_ownership_path"].write_text(yaml.dump(ownership_yaml), encoding="utf-8")

    # 2. Setup a mock FAIL review log containing "blocking_concern"
    log_entry = {
        "timestamp": "2026-06-02T10:00:00Z",
        "verdict": "FAIL",
        "blocking_concern": "BRANCH_ISOLATION",
        "comments": "some branch issue",
        "session_id": "session-123",
        "severity": "critical"
    }
    env["review_log_file"].write_text(json.dumps(log_entry) + "\n", encoding="utf-8")

    # 3. Setup mock ledger file indicating 15 sessions over 14 days to pass thresholds
    ledger_content = ""
    for i in range(15):
        day = 15 - i
        ledger_content += json.dumps({
            "session_id": f"session-{i}",
            "date": f"2026-05-{day:02d} 12:00",
            "outcome": "success",
            "action": "mock commit"
        }) + "\n"
    env["ledger_file"].write_text(ledger_content, encoding="utf-8")
    env["events_file"].write_text("", encoding="utf-8")

    # Create the branch-isolation skill directory so proposals don't fallback
    (env["skills_dir"] / "branch-isolation").mkdir(parents=True, exist_ok=True)
    (env["skills_dir"] / "branch-isolation" / "SKILL.md").write_text("# Branch Isolation Skill\n", encoding="utf-8")

    # Run distill_dream
    with patch("distill_dream.SKILL_OWNERSHIP_PATH", env["skill_ownership_path"]), \
         patch("distill_dream.LEDGER_FILE", env["ledger_file"]), \
         patch("distill_dream.EVENTS_FILE", env["events_file"]), \
         patch("distill_dream.REVIEW_LOG_FILE", env["review_log_file"]), \
         patch("distill_dream.PROPOSALS_DIR", env["proposals_dir"]), \
         patch("distill_dream.SKILLS_DIR", env["skills_dir"]):

        with patch("sys.argv", ["distill_dream.py"]):
            distill_dream.main()

    # Check if a proposal was generated for branch-isolation
    expected_proposal = env["proposals_dir"] / "branch-isolation__BRANCH_ISOLATION__open.md"
    assert expected_proposal.exists(), "Proposal for branch-isolation was not generated"


def test_singular_and_plural_keys_supported(temp_dream_env):
    """Verify distill_dream.py supports both check_type (singular) and check_types (plural) key forms."""
    env = temp_dream_env

    # 1. Setup ownership map using singular keys
    ownership_yaml = {
        "api-design": {
            "check_type": ["API_CHECK"],
            "event_type": ["api_event"],
            "keyword": ["endpoint"]
        }
    }
    env["skill_ownership_path"].write_text(yaml.dump(ownership_yaml), encoding="utf-8")

    # 2. Setup mock FAIL review log containing "blocking_concern" (maps to check_type)
    log_entry = {
        "timestamp": "2026-06-02T10:00:00Z",
        "verdict": "FAIL",
        "blocking_concern": "API_CHECK",
        "comments": "some endpoint issue",
        "session_id": "session-123",
        "severity": "critical"
    }
    env["review_log_file"].write_text(json.dumps(log_entry) + "\n", encoding="utf-8")

    # 3. Setup mock ledger file to pass thresholds
    ledger_content = ""
    for i in range(15):
        day = 15 - i
        ledger_content += json.dumps({
            "session_id": f"session-{i}",
            "date": f"2026-05-{day:02d} 12:00",
            "outcome": "success",
            "action": "mock commit"
        }) + "\n"
    env["ledger_file"].write_text(ledger_content, encoding="utf-8")
    env["events_file"].write_text("", encoding="utf-8")

    # Create the api-design skill directory
    (env["skills_dir"] / "api-design").mkdir(parents=True, exist_ok=True)
    (env["skills_dir"] / "api-design" / "SKILL.md").write_text("# API Design Skill\n", encoding="utf-8")

    # Run distill_dream
    with patch("distill_dream.SKILL_OWNERSHIP_PATH", env["skill_ownership_path"]), \
         patch("distill_dream.LEDGER_FILE", env["ledger_file"]), \
         patch("distill_dream.EVENTS_FILE", env["events_file"]), \
         patch("distill_dream.REVIEW_LOG_FILE", env["review_log_file"]), \
         patch("distill_dream.PROPOSALS_DIR", env["proposals_dir"]), \
         patch("distill_dream.SKILLS_DIR", env["skills_dir"]):

        with patch("sys.argv", ["distill_dream.py"]):
            distill_dream.main()

    # Check if a proposal was generated for api-design
    expected_proposal = env["proposals_dir"] / "api-design__API_CHECK__open.md"
    assert expected_proposal.exists(), "Proposal for api-design (singular form) was not generated"
