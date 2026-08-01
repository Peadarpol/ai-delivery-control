"""Unit tests for src/scripts/rebuttal.py protocol functions."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src/scripts is in sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "src" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import rebuttal


class TestRebuttalProtocol:
    """Test suite for rebuttal module utility and execution logic."""

    def test_get_normalized_diff_hash_fallback(self):
        """Test normalized diff hash computation when git write-tree fails."""
        diff_text = "diff --git a/file.py b/file.py\n+add line\n-remove line"
        with patch("subprocess.run", side_effect=RuntimeError("git error")):
            hash_val = rebuttal._get_normalized_diff_hash(diff_text)
            assert isinstance(hash_val, str)
            assert len(hash_val) == 64  # SHA-256 hex string

    def test_rebuttal_type_validation(self):
        """Verify OVERSIZED_DIFF and standard RebuttalType values are enforced by the module."""
        from typing import get_args
        valid_types = get_args(rebuttal.RebuttalType)
        assert "OVERSIZED_DIFF" in valid_types
        assert "FALSE_POSITIVE" in valid_types
        assert "SPEC_REQUIREMENT" in valid_types
        assert "ARCHITECTURAL_INVARIANT" in valid_types
        assert "OUT_OF_SCOPE" in valid_types
        assert "REMEDIATED" in valid_types

    def test_scan_logs_for_rebuttal_missing_log(self, tmp_path):
        """Scanning logs when .ai-review-log.jsonl is missing returns None, []."""
        with patch.object(rebuttal, "PROJECT_ROOT", tmp_path), \
             patch("ai_review.PROJECT_ROOT", tmp_path):
            fail_record, prior_attempts = rebuttal._scan_logs_for_rebuttal("hash123")
            assert fail_record is None
            assert prior_attempts == []

    def test_scan_logs_for_rebuttal_finds_fail(self, tmp_path):
        """Scanning logs correctly finds the latest FAIL verdict and prior attempts."""
        log_path = tmp_path / ".ai-review-log.jsonl"
        records = [
            {"timestamp": "2026-05-28T10:00:00Z", "verdict": "FAIL", "session_id": "s1", "issues": [{"finding_id": "F1"}]},
            {"timestamp": "2026-05-28T10:05:00Z", "verdict": "REBUTTAL_FAIL", "strategy": "rebuttal", "normalized_diff_hash": "hash123"},
        ]
        log_path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

        with patch.object(rebuttal, "PROJECT_ROOT", tmp_path), \
             patch("ai_review.PROJECT_ROOT", tmp_path):
            fail_record, prior_attempts = rebuttal._scan_logs_for_rebuttal("hash123")
            assert fail_record is not None
            assert fail_record["session_id"] == "s1"
            assert len(prior_attempts) == 1

    def test_hash_alignment_real_git_repo(self, tmp_path):
        """Integration test: ai_review._get_normalized_diff_hash and rebuttal._get_normalized_diff_hash produce identical 40-char git tree hashes."""
        import subprocess
        import ai_review

        # Initialize a real git repository in tmp_path
        subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True)

        # Create a file and stage it
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello world')\n", encoding="utf-8")
        subprocess.run(["git", "add", "test.py"], cwd=str(tmp_path), check=True)

        with patch("ai_review.PROJECT_ROOT", tmp_path), \
             patch.object(rebuttal, "PROJECT_ROOT", tmp_path):
            ai_hash = ai_review._get_normalized_diff_hash("diff text", target_args=["--cached"])
            rebuttal_hash = rebuttal._get_normalized_diff_hash("diff text", target_args=["--cached"])

            assert ai_hash != ""
            assert len(ai_hash) == 40  # Must be a real 40-char git write-tree SHA-1
            assert ai_hash == rebuttal_hash

    def test_tamper_detection_unreviewed_staged_file(self, tmp_path):
        """Scenario 33: Modifying/staging any file in the commit state alters git write-tree hash, detecting tampering."""
        import subprocess
        import ai_review

        subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True)

        # Stage initial file
        f1 = tmp_path / "f1.py"
        f1.write_text("print('v1')\n", encoding="utf-8")
        subprocess.run(["git", "add", "f1.py"], cwd=str(tmp_path), check=True)

        with patch("ai_review.PROJECT_ROOT", tmp_path), \
             patch.object(rebuttal, "PROJECT_ROOT", tmp_path):
            hash1 = ai_review._get_normalized_diff_hash("diff text", target_args=["--cached"])
            assert len(hash1) == 40

            # Tamper by staging a change in an unreviewed second file
            f2 = tmp_path / "unreviewed.py"
            f2.write_text("print('tampered')\n", encoding="utf-8")
            subprocess.run(["git", "add", "unreviewed.py"], cwd=str(tmp_path), check=True)

            hash2 = rebuttal._get_normalized_diff_hash("diff text", target_args=["--cached"])
            assert len(hash2) == 40
            assert hash1 != hash2  # Tamper detected!


