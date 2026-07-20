#!/usr/bin/env python3
"""
Requirement-to-Commit Traceability Gate (T1-L-04)
Ensures all non-trivial commits trace back to approved specifications.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Ensure UTF-8 encoding for stdout/stderr on Windows to prevent UnicodeEncodeError
if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Ensure imports can find .agent/scripts (audit_logger) and src/scripts (harness_utils)
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir.parent.parent / "src" / "scripts"))
sys.path.insert(0, str(script_dir.parent.parent))
from audit_logger import log_action
from harness_utils import get_harness_config

def get_git_dir() -> Path:
    """Run git rev-parse --git-dir to resolve the .git folder path."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=True,
            shell=False
        )
        return Path(res.stdout.strip()).resolve()
    except Exception:
        return Path(".git")

def get_commit_message(msg_path_arg: str | None = None) -> str:
    """Resolve and read commit message content."""
    if msg_path_arg:
        path = Path(msg_path_arg)
    else:
        git_dir = get_git_dir()
        path = git_dir / "COMMIT_EDITMSG"
        
    if not path.exists():
        raise FileNotFoundError(f"Commit message file not found at {path}")
    return path.read_text(encoding="utf-8")

def get_config_options() -> tuple[Path, str]:
    """Read specs_path and outer_loop mode using get_harness_config."""
    from harness_utils import get_harness_config
    specs_path = get_harness_config("traceability", "specs_path")
    mode = get_harness_config("outer_loop", "mode")
    return Path(specs_path), mode

def is_doc_or_trivial_diff() -> bool:
    """Check if all staged files match documentation extensions or reside under docs/."""
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
            shell=False
        )
        files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
        if not files:
            return True # Nothing staged, treat as trivial/empty
            
        doc_extensions = {".md", ".txt", ".rst"}
        for f in files:
            path = Path(f)
            # Check if file has doc extension or is in docs/ directory
            is_doc_file = path.suffix.lower() in doc_extensions
            is_in_docs = "docs/" in path.as_posix() or path.parts[0] == "docs"
            if not (is_doc_file or is_in_docs):
                return False
        return True
    except Exception:
        return False

def print_diagnostic_card(reason: str):
    """Print the formatted terminal diagnostic card on failure."""
    card = f"""==================================================
❌ [TRACEABILITY GATE] Commit Rejected
==================================================
Reason: {reason}

👉 How to Fix:
   1. Reference a spec ID in your message: "[SPEC-001] Implement login"
   2. Or bypass using: "git commit -m '--no-trace <detailed-reason-10-chars-min>'"
==================================================
"""
    print(card, file=sys.stderr)

def is_root_commit() -> bool:
    """Check if total repository commit count is zero (root commit exemption)."""
    try:
        res = subprocess.run(
            ["git", "rev-list", "--all", "--count"],
            capture_output=True,
            text=True,
            check=True,
            shell=False
        )
        return res.stdout.strip() == "0"
    except Exception:
        return False


def get_worktree_root() -> Path:
    """Resolve the git top-level directory for worktree anchoring."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            shell=False
        )
        if res.returncode == 0 and res.stdout.strip():
            return Path(res.stdout.strip()).resolve()
    except Exception:
        pass
    return Path.cwd()


def extract_commit_trailers(commit_sha: str | None = None) -> dict[str, str]:
    """Extract trailers from commit message or git log if SHA provided."""
    trailers = {}
    try:
        cmd = ["git", "log", "-1", "--format=%(trailers:only,unfold)", commit_sha or "HEAD"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for line in res.stdout.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                trailers[k.strip()] = v.strip()
    except Exception:
        pass
    return trailers


def _get_session_ledger_attribution(commit_sha: str) -> dict[str, Any]:
    """Fallback attribution lookup via session_ledger.jsonl when commit trailers are absent."""
    ledger_path = Path(".agent/state/session_ledger.jsonl")
    if not ledger_path.exists():
        return {}
    try:
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            action = entry.get("action", "")
            if action.startswith("[COMMIT]:") and commit_sha[:12] in action:
                return {"session_id": entry.get("session_id"), "agent": entry.get("agent")}
    except Exception:
        pass
    return {}


def check_branch_no_trace_commits(base_branch: str = "main", ack_reason: str | None = None) -> bool:
    """Check if branch contains --no-trace commits and require --ack-no-trace parameter."""
    try:
        cmd = ["git", "log", f"{base_branch}..HEAD", "--grep=--no-trace", "--oneline"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        no_trace_commits = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if not no_trace_commits:
            return True  # Clean

        if not ack_reason:
            print("❌ [TRACEABILITY MERGE GATE] Merge contains --no-trace commits. Explicit confirmation required.", file=sys.stderr)
            print("   Re-run: python .agent/scripts/check_traceability.py --check-merge-trace --ack-no-trace \"<reason>\"", file=sys.stderr)
            print("   Then push again.", file=sys.stderr)
            for c in no_trace_commits:
                sha = c.split()[0]
                trailers = extract_commit_trailers(sha)
                session_id = trailers.get("Session-Id")
                signer = trailers.get("Signed-by")
                if not session_id or not signer:
                    ledger_attr = _get_session_ledger_attribution(sha)
                    session_id = session_id or ledger_attr.get("session_id", "unknown-session")
                    signer = signer or ledger_attr.get("agent", "unknown-signer")
                print(f"     - {c} (session: {session_id}, signed_by: {signer})", file=sys.stderr)
            return False

        # Sanitize and truncate reason to 250 chars
        sanitized_reason = ack_reason.strip()[:250]
        from harness_utils import log_harness_event
        log_harness_event({
            "event_type": "ack_no_trace_merge",
            "severity": "WARNING",
            "payload": {
                "reason": sanitized_reason,
                "no_trace_count": len(no_trace_commits),
                "no_trace_commits": no_trace_commits,
            }
        })
        print(f"⚠️ [TRACEABILITY MERGE GATE] Merging branch with {len(no_trace_commits)} --no-trace commits acknowledged: '{sanitized_reason}'")
        return True
    except Exception as e:
        print(f"⚠️ [TRACEABILITY MERGE GATE] Warning checking branch commits: {e}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Requirement Traceability Gate")
    parser.add_argument("commit_msg_file", nargs="?", help="Path to COMMIT_EDITMSG (commit-msg stage)")
    parser.add_argument("--check-merge-trace", action="store_true",
                        help="Run the merge-gate --no-trace aggregator instead of the per-commit check (pre-push stage)")
    parser.add_argument("--ack-no-trace", type=str, default=None, metavar="REASON",
                        help="Acknowledge and permit a merge containing --no-trace commits, with a required reason")
    parser.add_argument("--base-branch", type=str, default=None,
                        help="Override the base branch for the merge check (default: config acceptance_gate.base_branch, fallback 'main')")
    args = parser.parse_args()

    if args.check_merge_trace:
        base_branch = args.base_branch or get_harness_config("acceptance_gate", "base_branch")
        ok = check_branch_no_trace_commits(base_branch=base_branch, ack_reason=args.ack_no_trace)
        sys.exit(0 if ok else 1)

    if is_root_commit():
        print("ℹ️  [TRACEABILITY] Root commit exemption active (repo commit count is 0).")
        sys.exit(0)

    msg_path = args.commit_msg_file
    try:
        commit_msg = get_commit_message(msg_path)
    except Exception as e:
        print(f"❌ [TRACEABILITY] Error reading commit message: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Merge commit exemption
    if commit_msg.strip().startswith("Merge "):
        sys.exit(0)
        
    # Trivial / Documentation Fast-Path
    if is_doc_or_trivial_diff():
        print("ℹ️  [TRACEABILITY] Fast-path: Documentation-only or empty diff detected. Bypassing traceability check.")
        sys.exit(0)
        
    specs_path, mode = get_config_options()
    
    # Check for SPEC ID (versioned SPEC-vX.Y.Z-name or legacy numeric SPEC-001), T1, HIB, BUG
    spec_matches = re.findall(
        r"\b(SPEC-v[\d.]+(?:-[\w-]+)?|(?:SPEC|HIB|BUG)-\d+|T1-\w+-\d+)\b",
        commit_msg,
        re.IGNORECASE,
    )
    
    # Bypass check (--no-trace)
    bypass_match = re.search(r"--no-trace\s+(.+)", commit_msg, re.IGNORECASE)
    
    if mode == "contractual" and bypass_match:
        print_diagnostic_card("Contractual mode is active. --no-trace bypass is NOT available.")
        sys.exit(1)
        
    if bypass_match:
        reason = bypass_match.group(1).strip()
        if len(reason) < 10:
            print_diagnostic_card("Bypass reason following --no-trace must be at least 10 characters long.")
            sys.exit(1)
            
        # Log bypass action
        log_action(
            action_type="traceability_bypass",
            status="success",
            details={"reason": reason, "commit_msg": commit_msg.strip()}
        )
        print("⚠️ [TRACEABILITY] Bypass active: --no-trace accepted.")
        sys.exit(0)
        
    if not spec_matches:
        if mode == "discovery":
            print("⚠️ [TRACEABILITY] Discovery mode active: Missing spec reference, but bypass allowed.")
            sys.exit(0)
        print_diagnostic_card("This commit is non-trivial and does not trace back to an approved spec.")
        sys.exit(1)
        
    docs_dir = Path("docs")
    docs_dir_exists = docs_dir.exists()
    docs_lines = []
    
    non_spec_matches = [m for m in spec_matches if not m.upper().startswith("SPEC-")]
    if non_spec_matches:
        if not docs_dir_exists:
            print_diagnostic_card("docs/ directory not found — traceability check cannot verify backlog references")
            sys.exit(1)
            
        for backlog_file in docs_dir.rglob("*.md"):
            if backlog_file.is_file():
                if backlog_file.stat().st_size > 5 * 1024 * 1024:
                    print(f"⚠️ [TRACEABILITY] Warning: Skipping {backlog_file} because it exceeds the 5MB size limit.")
                    continue
                content = backlog_file.read_text(encoding="utf-8", errors="ignore")
                docs_lines.extend(content.splitlines())

    # If spec matches are present, verify spec files
    for spec_id in spec_matches:
        spec_id = spec_id.upper()
        
        if spec_id.startswith("SPEC-"):
            spec_file = specs_path / f"{spec_id}.md"
            if not spec_file.exists():
                archive_file = specs_path / "archive" / f"{spec_id}.md"
                if archive_file.exists():
                    spec_file = archive_file
                else:
                    print_diagnostic_card(f"Referenced spec file does not exist: {spec_file}")
                    sys.exit(1)
                
            # Parse status
            spec_content = spec_file.read_text(encoding="utf-8")
            status_match = re.search(r"^\s*\**Status\**\s*:\s*(APPROVED|DRAFT)", spec_content, re.IGNORECASE | re.MULTILINE)
            
            is_approved = status_match and status_match.group(1).upper() == "APPROVED"
            if not is_approved:
                is_ci = os.environ.get("CI", "").lower() == "true"
                if is_ci:
                    print_diagnostic_card(f"Referenced spec {spec_id} is not APPROVED in CI environment.")
                    sys.exit(1)
                else:
                    print(f"⚠️ [TRACEABILITY] Warning: Referenced spec {spec_id} is in DRAFT status.")
        else:
            # HIB, BUG, T1 check (structural definition gating)
            is_found = False
            # Compile the regex pattern once per ID instead of on every line
            pattern = re.compile(rf"^\s*(?:\|\s*|[\-\*]\s*(?:\[[ xX]\]\s*)?|#+\s*)[\*\~_\[\]\s]*{re.escape(spec_id)}\b", re.IGNORECASE)
            for line in docs_lines:
                # Require the ID to be formally defined (table row, list item (with optional checkbox), or heading)
                # and tolerate inline markdown emphasis (**, _, ~~, []) around the ID.
                if pattern.match(line):
                    is_found = True
                    break
            
            if not is_found:
                print_diagnostic_card(f"Referenced backlog ID '{spec_id}' not found as a formal entry in docs/.")
                sys.exit(1)
                
    sys.exit(0)

if __name__ == "__main__":
    main()
