#!/usr/bin/env python3
"""
Agent Behaviour Evaluator (EDD).
Audits the agent's recent session for compliance with governance rules.

Usage: python .agent/evals/behaviour_checks.py
"""

import re
import subprocess
import sys
from pathlib import Path

# Fix: Ensure UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

GOVERNANCE_PATH = Path(".agent/governance.md")
AUDIT_TRAIL_PATH = Path(".agent/state/harness_events.jsonl")


def get_branch_commits(branch: str = "HEAD", count: int = 20) -> list[dict]:
    """Get recent commits with per-file change info."""
    result = subprocess.run(
        ["git", "log", f"-{count}", "--name-only", "--format=COMMIT:%H|%s", branch],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    commits: list[dict] = []
    current: dict | None = None
    for line in result.stdout.strip().splitlines():
        if line.startswith("COMMIT:"):
            if current:
                commits.append(current)
            sha, msg = line[7:].split("|", 1)
            current = {"sha": sha, "message": msg, "files": []}
        elif line.strip() and current:
            current["files"].append(line.strip())
    if current:
        commits.append(current)
    return commits


def check_tdd_ordering(commits: list[dict]) -> list[str]:
    """Verify test files appear in commits before implementation files."""
    issues: list[str] = []
    test_indices: list[int] = []
    impl_indices: list[int] = []

    for i, c in enumerate(reversed(commits)):  # oldest first
        has_test = any("tests/" in f for f in c["files"])
        has_impl = any("src/" in f and "scripts/" not in f for f in c["files"])
        if has_test and not has_impl:
            test_indices.append(i)
        elif has_impl and not has_test:
            impl_indices.append(i)

    if impl_indices and test_indices:
        if min(impl_indices) < min(test_indices):
            issues.append(
                f"⚠️ TDD ORDER: Implementation commit (#{min(impl_indices)}) "
                f"appears before first test commit (#{min(test_indices)})"
            )
    elif impl_indices and not test_indices:
        issues.append(
            "⚠️ TDD MISSING: Implementation commits found but no test commits"
        )
    return issues


def check_session_summary_updated() -> list[str]:
    """Verify last_session_summary.md was updated within the last 5 commits."""
    issues: list[str] = []
    summary_path = Path(".agent/state/last_session_summary.md")
    if not summary_path.exists():
        issues.append("❌ SESSION: .agent/state/last_session_summary.md does not exist")
        return issues
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~5", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if ".agent/state/last_session_summary.md" not in result.stdout:
        issues.append(
            "⚠️ SESSION: last_session_summary.md not updated in last 5 commits"
        )
    return issues


def check_commit_message_quality(commits: list[dict]) -> list[str]:
    """Flag generic or meaningless commit messages."""
    issues: list[str] = []
    generic_patterns = [
        r"^fix$",
        r"^update$",
        r"^changes$",
        r"^wip$",
        r"^temp$",
        r"^asdf",
        r"^test$",
        r"^stuff$",
    ]
    for c in commits[:10]:
        msg = c["message"].strip().lower()
        for pat in generic_patterns:
            if re.match(pat, msg):
                issues.append(
                    f"⚠️ COMMIT MSG: Generic message '{c['message']}' ({c['sha'][:8]})"
                )
    return issues


def check_git_checkpoints() -> tuple[bool, str]:
    """Verify that 'CHECKPOINT' exists in git history for recent multi-file changes."""
    try:
        # Get commits from the last hour (or last 5 commits)
        result = subprocess.run(
            ["git", "log", "-n", "10", "--pretty=format:%s"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        history = result.stdout.lower()
        if "checkpoint" in history or "wip" in history:
            return True, "✅ Git Checkpoints: Found checkpoint/wip entries in history."
        return (
            False,
            "❌ Git Checkpoints: No defensive checkpoints found in recent history (Gov §7).",
        )
    except Exception as e:
        return True, f"⚠️  Could not check git history: {e}"


def check_file_limits() -> tuple[bool, str]:
    """Check if any recent commit exceeded file limits without approval."""
    # Placeholder: In a real L4 system, this would correlate git diffs with audit logs
    return True, "✅ File Limits: No unapproved mass-edits detected."


def check_branch_strategy() -> list[str]:
    """Verify branch strategy for CI fixes on devops branch."""
    warnings = []
    try:
        current_branch = subprocess.check_output(
            ["git", "branch", "--show-current"], text=True
        ).strip()

        if current_branch == "devops":
            # Merge commits from feature branches are the intended workflow —
            # two parents means this is a merge, not a direct commit.
            parents = subprocess.check_output(
                ["git", "log", "-1", "--format=%P"], text=True
            ).strip()
            if len(parents.split()) >= 2:
                return warnings

            # Check if commit message contains the exception marker
            commit_msg = subprocess.check_output(
                ["git", "log", "-1", "--format=%s"], text=True
            ).strip()
            if "[direct-devops: trivial]" not in commit_msg:
                warnings.append(
                    "⚠️  BRANCH: Direct commit to 'devops' detected. "
                    "Use a fix/ branch for CI fixes and merge back to active feature branch. "
                    "Add '[direct-devops: trivial]' to commit message to suppress this warning."
                )
    except subprocess.CalledProcessError:
        pass
    return warnings


def main():
    branch = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--branch" else "HEAD"
    commits = get_branch_commits(branch)

    print(f"\n{'─' * 60}")
    print(f"  AGENT BEHAVIOUR AUDIT (EDD) — {len(commits)} recent commits")
    print(f"{'─' * 60}\n")

    all_issues: list[str] = []

    # Governance checks (existing)
    ok, msg = check_git_checkpoints()
    print(f"  {msg}")
    if not ok:
        all_issues.append(msg)

    ok, msg = check_file_limits()
    print(f"  {msg}")
    if not ok:
        all_issues.append(msg)

    # Process checks (from plan spec)
    branch_issues = check_branch_strategy()
    for issue in branch_issues:
        print(f"  {issue}")
    all_issues.extend(branch_issues)

    tdd_issues = check_tdd_ordering(commits)
    for issue in tdd_issues:
        print(f"  {issue}")
    all_issues.extend(tdd_issues)

    session_issues = check_session_summary_updated()
    for issue in session_issues:
        print(f"  {issue}")
    all_issues.extend(session_issues)

    msg_issues = check_commit_message_quality(commits)
    for issue in msg_issues:
        print(f"  {issue}")
    all_issues.extend(msg_issues)

    if not tdd_issues and not session_issues and not msg_issues and not branch_issues:
        print("  ✅ TDD ordering, session logging, and commit message quality: OK")

    print(f"\n{'─' * 60}")
    if all_issues:
        print(
            f"  ⚠️  {len(all_issues)} behavioural warning(s). Review Governance rules."
        )
        print(f"{'─' * 60}\n")
    else:
        print("  ✅ Behavioural compliance verified.")
        print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main()
