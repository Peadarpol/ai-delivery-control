#!/usr/bin/env python3
"""
Shared Harness Utilities
Central utility library to prevent duplicate implementations and import splitting.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Generator

# Ensure UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError under redirected environments
if sys.platform == "win32":
    import io
    try:
        if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass

# Dynamically load contextlib to stay lean
contextlib = __import__("contextlib")

SCRIPT_DIR = Path(__file__).resolve().parent

def _find_project_root() -> Path:
    """Find the git repository root (works regardless of where script lives)."""
    try:
        cwd = Path.cwd()
        if (cwd / ".agent").exists() or (cwd / ".git").exists():
            return cwd
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except Exception:
        pass
    # Fallback: assume src/scripts/../../ = repo root
    return SCRIPT_DIR.parent.parent

PROJECT_ROOT = _find_project_root()

def redact_api_keys(text: str) -> str:
    """Replaces API keys (e.g. sk-proj-..., sk-ant-..., sk-...) with [REDACTED] in debug streams."""
    if not isinstance(text, str):
        return text
    # Pattern to match Anthropic and OpenAI keys, plus generic sk- keys
    pattern = r"\b(sk-(?:ant|proj)-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{24,})\b"
    return re.sub(pattern, "[REDACTED]", text)

def log_harness_event(event_dict: Dict[str, Any], project_root: Path | None = None) -> None:
    """Log a harness event to .agent/state/harness_events.jsonl (T1-L-08)."""
    try:
        root = project_root or PROJECT_ROOT
        log_dir = root / ".agent" / "state"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "harness_events.jsonl"
        
        session_id = "pre-session-init"
        session_file = root / ".agent" / "state" / "session.json"
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    session_id = json.load(f).get("session_id") or "pre-session-init"
            except Exception:
                pass
                
        # Modern standard-compliant UTC datetime
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        
        record = {
            "schema_version": "1.0",
            "event_type": event_dict.get("event_type"),
            "timestamp_utc": now_utc,
            "session_id": session_id,
            "commit_sha": None,
            "agent": os.environ.get("AGENT_ID", "ai_review"),
            "severity": event_dict.get("severity", "INFO"),
            "payload": event_dict.get("payload", {}),
        }
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass  # Never block execution due to logging failures

def _setup_sys_path():
    """Route sys.path to allow imports from senior-architect and agent scripts."""
    nested_skills_path = PROJECT_ROOT / ".agent" / "skills" / "universal" / "senior-architect" / "scripts"
    flat_skills_path = PROJECT_ROOT / ".agent" / "skills" / "senior-architect" / "scripts"
    scripts_path = str(PROJECT_ROOT / ".agent" / "scripts")
    
    resolved_skills_path = None
    if nested_skills_path.exists():
        resolved_skills_path = str(nested_skills_path)
    elif flat_skills_path.exists():
        resolved_skills_path = str(flat_skills_path)
        
    if resolved_skills_path:
        if resolved_skills_path not in sys.path:
            sys.path.insert(0, resolved_skills_path)
    else:
        # Neither path exists - log warning event
        log_harness_event({
            "event_type": "skills_path_not_found",
            "severity": "WARNING",
            "payload": {
                "searched_paths": [str(flat_skills_path), str(nested_skills_path)]
            }
        })
        print("⚠️  [REVIEW] Warning: Senior Architect skills path not found under .agent/skills/")

    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)

@contextlib.contextmanager
def _lock_session(session_file: Path, timeout: float = 5.0, delay: float = 0.05) -> Generator[bool, None, None]:
    """Platform-agnostic, atomic directory-based advisory lock for session.json with stale lock clearance."""
    lock_path = session_file.with_suffix(".lock")
    start_time = time.time()
    acquired = False
    
    while time.time() - start_time < timeout:
        try:
            lock_path.mkdir(exist_ok=False)
            acquired = True
            break
        except FileExistsError:
            # Check for stale lock (older than 60 seconds)
            try:
                mtime = lock_path.stat().st_mtime
                if time.time() - mtime > 60.0:
                    try:
                        lock_path.rmdir()
                        print("[LOCK] Cleared stale session lock directory.")
                        continue
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(delay)
        except OSError:
            # Handle Windows permission or sharing errors during directory operations
            time.sleep(delay)
            
    try:
        yield acquired
    finally:
        if acquired:
            try:
                lock_path.rmdir()
            except Exception:
                pass


def _safe_git_env() -> dict:
    """Minimal environment for git subprocess calls.
    Strips API keys, OIDC tokens, and shell session variables.
    GIT_* passthrough is the safety net for non-standard git env vars.
    PYTHONPATH intentionally excluded — all call sites invoke git only.
    """
    import os
    allowed = {
        "PATH", "HOME", "USERPROFILE", "SystemRoot",
        "TEMP", "TMP", "HOMEDRIVE", "HOMEPATH",
    }
    return {k: v for k, v in os.environ.items()
            if k in allowed or k.startswith("GIT_")}
