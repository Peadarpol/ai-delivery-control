#!/usr/bin/env python3
import datetime
import json
import subprocess
from pathlib import Path

AUDIT_LOG_PATH = Path(".agent/state/harness_events.jsonl")
LEDGER_PATH = Path(".agent/state/session_ledger.md")


def get_git_info():
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    files_changed = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], text=True
    ).splitlines()
    msg = subprocess.check_output(
        ["git", "log", "-1", "--pretty=%B"], text=True
    ).strip()
    return sha, files_changed, msg


SESSION_FILE = Path(".agent/state/session.json")


def get_session_id():
    if not SESSION_FILE.exists():
        return "UNKNOWN"
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("session_id", "UNKNOWN")
    except:
        pass
    return "UNKNOWN"


def write_audit(check, severity, detail):
    sha, _, _ = get_git_info()

    record = {
        "schema_version": "1.0",
        "event_type": "governance_observation",
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "session_id": get_session_id(),
        "commit_sha": sha,
        "agent": "governance_check",
        "severity": severity.lower(),
        "payload": {"check": check, "detail": detail},
    }

    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def main():
    sha, files, msg = get_git_info()

    # 1. Mass Edit Check
    if len(files) > 15:
        write_audit("mass_edit", "FAIL", f"Commit changed {len(files)} files.")

    # 2. No-Verify Check
    # (Checking for --no-verify is hard post-commit unless we check the process or the commit msg)
    # The user rule P-12 prohibits --no-verify.
    # If the commit message mentions bypassing or if we detect files that SHOULD have failed gates.
    # For now, we'll check if the commit message implies a bypass or if it's a known risky pattern.
    if "[no-verify]" in msg.lower() or "--no-verify" in msg.lower():
        write_audit("no_verify", "FAIL", "Commit message mentions bypass.")

    # 3. Governance without Decision Check
    has_gov = any("governance.md" in f for f in files)
    has_dec = any("decisions_log.md" in f for f in files)
    if has_gov and not has_dec:
        write_audit(
            "governance_without_decision",
            "FAIL",
            "governance.md modified without decisions_log.md update.",
        )

    # 4. Mandatory Review Bypass Check
    if "SKIP_AI_REVIEW=1" in msg:
        write_audit("ai_review_bypass", "WARN", "AI review gate bypassed via env var.")

    # 5. Commit Sequence Check (PG-02)
    seq_violation = check_commit_sequence(sha, files, msg)
    if seq_violation:
        write_audit("commit_sequence", "FAIL", seq_violation)


def get_current_branch():
    return subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
    ).strip()


def get_branch_commits(branch):
    # Get last 100 commit messages on the branch
    output = subprocess.check_output(
        ["git", "log", branch, "--pretty=format:%s", "-n", "100"], text=True
    )
    return output.splitlines()


def check_commit_sequence(sha, files, msg):
    """
    Check that large commits (>5 files) on feature branches have
    an INIT: or PLAN: commit earlier on the same branch.
    Integration branches (main, develop, devops) are exempt.
    """
    current_branch = get_current_branch()
    if current_branch in ("main", "develop", "devops"):
        return None

    if len(files) <= 5:
        return None

    # Exclude the current commit message from the search
    branch_msgs = get_branch_commits(current_branch)
    has_init = any(m.startswith(("INIT:", "PLAN:")) for m in branch_msgs)

    if not has_init:
        return (
            f"[VIOLATION] Commit sequence: large commit ({len(files)} files) on feature branch '{current_branch}' "
            "with no INIT: or PLAN: commit found on this branch.\n"
            "[REMEDIATION] Run the initializer session pattern before committing "
            "large feature batches. See .agent/workflows/feature-implementation.md §Step 0."
        )
    return None

    print("✅ Governance check complete.")


if __name__ == "__main__":
    main()
