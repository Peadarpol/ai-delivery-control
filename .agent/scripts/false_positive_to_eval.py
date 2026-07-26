#!/usr/bin/env python3
"""
false_positive_to_eval.py — False Positive Regression Logger

Captures a false positive commit diff (either staged or from a specific commit)
and registers it in `tests/data/false_positive_cases.csv` with a sidecar diff
file in `tests/data/fp_cases/` for automated regression testing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import subprocess
import sys
from pathlib import Path

def get_project_root() -> Path:
    """Resolve project root using git."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(Path(__file__).parent)
        )
        if res.returncode == 0 and res.stdout.strip():
            return Path(res.stdout.strip())
    except Exception:
        pass
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = get_project_root()
_src_scripts = PROJECT_ROOT / "src" / "scripts"
if _src_scripts.exists() and str(_src_scripts) not in sys.path:
    sys.path.insert(0, str(_src_scripts))
import harness_utils


def get_diff_from_git(commit_sha: str | None) -> str:
    """Extract diff from git.
    
    If commit_sha is provided, runs: `git show {commit_sha} --unified=3`
    If not, runs: `git diff --cached --unified=3` (staged changes)
    """
    root = get_project_root()
    if commit_sha:
        cmd = ["git", "show", commit_sha, "--unified=3"]
    else:
        cmd = ["git", "diff", "--cached", "--unified=3"]

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(root)
        )
        return res.stdout or ""
    except Exception as e:
        print(f"⚠️  [EVAL] Failed to retrieve git diff: {e}")
        return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Log false positive cases to evaluation regression tests.")
    parser.add_argument("--finding-id", required=True, help="Finding IDs (comma-separated if multiple)")
    parser.add_argument("--rebuttal-type", required=True, choices=["FALSE_POSITIVE", "SPEC_REQUIREMENT", "ARCHITECTURAL_INVARIANT", "OUT_OF_SCOPE"])
    parser.add_argument("--evidence", required=True, help="Evidence/Rationale statement")
    parser.add_argument("--commit-sha", help="Optional commit SHA. Defaults to current staged diff.")

    args = parser.parse_args()

    project_root = get_project_root()
    diff_content = get_diff_from_git(args.commit_sha)

    if not diff_content.strip():
        print("⚠️  [EVAL] Captured diff is empty. Nothing to log.")
        return

    # Deterministic file naming / sha identification
    diff_hash = hashlib.sha256(diff_content.encode("utf-8")).hexdigest()[:8]
    
    if args.commit_sha:
        sha_str = args.commit_sha[:8]
        filename = f"{sha_str}_{diff_hash}.diff"
        record_sha = args.commit_sha
    else:
        # Determine the current HEAD commit as base reference
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=str(project_root)
            )
            head_sha = res.stdout.strip() if res.returncode == 0 else "unknown"
        except Exception:
            head_sha = "unknown"
        filename = f"{head_sha}_staged_{diff_hash}.diff"
        record_sha = f"{head_sha}_staged"

    # Ensure output directories exist
    fp_cases_dir = project_root / "tests" / "data" / "fp_cases"
    fp_cases_dir.mkdir(parents=True, exist_ok=True)
    
    diff_file_path = fp_cases_dir / filename
    try:
        diff_file_path.write_text(diff_content, encoding="utf-8")
        print(f"✅ [EVAL] Saved sidecar diff to {diff_file_path.relative_to(project_root)}")
    except Exception as e:
        print(f"❌ [EVAL] Failed to write sidecar diff file: {e}")
        return

    csv_path = project_root / "tests" / "data" / "false_positive_cases.csv"
    
    # Read existing headers/rows to ensure we don't write duplicates
    rows = []
    headers = ["finding_id", "rebuttal_type", "evidence", "commit_sha", "diff_file", "expected_verdict"]
    
    if csv_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header_row = next(reader, None)
                if header_row:
                    headers = header_row
                for row in reader:
                    if row:
                        rows.append(row)
        except Exception:
            pass

    # Relativize the diff_file path to the project root or keep it as tests/data/fp_cases/{filename}
    diff_file_relative = f"tests/data/fp_cases/{filename}"

    # Build the new row matching the exact headers
    # finding_id,rebuttal_type,evidence,commit_sha,diff_file,expected_verdict
    # We default expected_verdict to PASS for false positives
    new_row = {
        "finding_id": args.finding_id,
        "rebuttal_type": args.rebuttal_type,
        "evidence": args.evidence,
        "commit_sha": record_sha,
        "diff_file": diff_file_relative,
        "expected_verdict": "PASS",
    }

    # Format as list matching header positions
    row_list = [new_row.get(h, "") for h in headers]
    
    # Check for exact duplicate (same diff_file and finding_id)
    is_duplicate = False
    for r in rows:
        if len(r) >= 5 and r[headers.index("diff_file")] == diff_file_relative and r[headers.index("finding_id")] == args.finding_id:
            is_duplicate = True
            break

    if not is_duplicate:
        rows.append(row_list)
        try:
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
            print(f"✅ [EVAL] Appended false positive to {csv_path.relative_to(project_root)}")
        except Exception as e:
            print(f"❌ [EVAL] Failed to update CSV log: {e}")
    else:
        print("💡 [EVAL] Duplicate case already registered in CSV. Skipped.")


if __name__ == "__main__":
    main()
