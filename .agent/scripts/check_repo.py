#!/usr/bin/env python3
"""
check_repo.py — Verify the active git repository matches the expected project.

Prevents accidental commits to the wrong repository when working across
multiple projects simultaneously. Run before any git add, commit, or merge.

AI Delivery Control — governance check P-14.
"""
import subprocess
import pathlib
import sys

# Fix: Ensure UTF-8 encoding for stdout/stderr on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def _safe_symbol(emoji: str, fallback: str) -> str:
    """Return emoji if stdout supports UTF-8, else ASCII fallback."""
    try:
        emoji.encode(sys.stdout.encoding or "utf-8")
        return emoji
    except (UnicodeEncodeError, AttributeError):
        return fallback


SYMBOL_CHECK = _safe_symbol("✅", "OK")


def get_current_repo_name() -> str:
    """Extract repository name from git remote origin URL."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        cwd=pathlib.Path.cwd()
    )
    if result.returncode != 0:
        print("[REPO CHECK] Warning: no git remote 'origin' found.")
        return ""
    url = result.stdout.strip()
    # Handles both HTTPS and SSH remote URLs
    return url.rstrip("/").split("/")[-1].replace(".git", "")


def check_repo(expected: str) -> None:
    current = get_current_repo_name()
    if not current:
        print("[REPO CHECK] Could not determine active repository. Proceeding with caution.")
        return
    if current.lower() != expected.lower():
        print(f"\n{'='*52}")
        print(f"  [REPO MISMATCH] Wrong repository active!")
        print(f"  Expected : {expected}")
        print(f"  Actual   : {current}")
        print(f"  Switch to the correct project before proceeding.")
        print(f"{'='*52}\n")
        sys.exit(1)
    print(f"[REPO CHECK] {SYMBOL_CHECK} Confirmed: {current}")


if __name__ == "__main__":
    # EXPECTED_REPO is injected by bootstrap/install.py at install time
    EXPECTED_REPO = "ai-delivery-control"
    check_repo(EXPECTED_REPO)
