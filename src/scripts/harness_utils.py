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

_CONFIG_CACHE = {}

DEFAULTS = {
    "model_routing": {
        "max_tokens": 4096,
        "budget_provider": "ollama",
        "budget_model": "gemma4",
        "budget_base_url": "http://localhost:11434",
    },
    "agent_limits": {
        "max_files_per_commit": 15,
        "max_test_retries": 3,
        "warn_session_minutes": 120,
        "max_session_minutes": 240,
    },
    "wiki_domains": {},
    "spec_gate": {
        "specs_path": "docs/planning/specs/",
    },
    "memory": {
        "retention": {
            "session_ledger_retention_days": 90,
            "harness_events_retention_days": 365,
            "review_log_retention_days": 90,
            "dream_proposals_reviewed_retention_days": 365,
        }
    },
    "traceability": {
        "specs_path": "docs/planning/specs/",
    },
    "acceptance_gate": {
        "base_branch": "main",
        "migration_paths": [
            "src/backend/db/migrations/",
            "migrations/versions/",
            "alembic/versions/",
            "db/migration/",
            "migrations/",
        ],
    },
    "architecture_checks": {
        "adr_capability_mappings": {},
    },
    "outer_loop": {
        "mode": "incremental",
    }
}

def _parse_yaml_val(val: str) -> Any:
    if val == "null" or val == "~":
        return None
    if val == "true":
        return True
    if val == "false":
        return False
    if val == "[]":
        return []
    if val == "{}":
        return {}
    try:
        if "." in val:
            return float(val)
        else:
            return int(val)
    except ValueError:
        pass
    return val

def _fallback_yaml_parse(content: str) -> dict:
    """Indentation-aware fallback YAML parser."""
    result = {}
    current_section = None
    
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
            
        indent = len(line) - len(line.lstrip())
        
        if ":" in stripped:
            key_part, val_part = stripped.split(":", 1)
            val_part = val_part.split("#", 1)[0].strip()
            key = key_part.strip().strip("'\"")
            
            if indent == 0:
                if not val_part:
                    current_section = key
                    result[current_section] = {}
                else:
                    current_section = None
                    result[key] = _parse_yaml_val(val_part.strip("'\""))
            elif indent > 0 and current_section is not None:
                if val_part:
                    result[current_section][key] = _parse_yaml_val(val_part.strip("'\""))
        elif stripped.startswith("-") and current_section is not None:
            # list item support
            val = stripped[1:].strip().split("#", 1)[0].strip("'\"")
            if val:
                import logging
                logging.warning("harness_utils._fallback_yaml_parse: list item '%s' dropped. Use PyYAML for list support.", val)
                
    return result

def load_yaml_with_fallback(path: Path | str, strict: bool = False) -> dict:
    """Load YAML file using pyyaml if available, else fallback."""
    path = Path(path)
    if not path.exists():
        return {}
    
    try:
        content = path.read_text(encoding="utf-8")
        try:
            import yaml
            return yaml.safe_load(content) or {}
        except ImportError:
            return _fallback_yaml_parse(content)
        except Exception:
            if strict:
                raise
            return {}
    except Exception:
        if strict:
            raise
        return {}

def load_harness_config(config_path: Path | str | None = None, force_reload: bool = False, strict: bool = False) -> dict:
    """Load the harness config.yaml into a cached dict."""
    global _CONFIG_CACHE
    
    if config_path is None:
        # Find project root
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent
        config_path = project_root / ".agent" / "config.yaml"
        
    path_key = str(config_path)
    
    if not force_reload and not strict and path_key in _CONFIG_CACHE:
        return _CONFIG_CACHE[path_key]
        
    loaded = load_yaml_with_fallback(config_path, strict=strict)
    if not strict:
        _CONFIG_CACHE[path_key] = loaded
    return loaded

def get_harness_config(section: str, key: str | None = None, default: Any = None, config_path: Path | str | None = None, strict: bool = False) -> Any:
    """
    Get a value from the harness config.
    Resolution order:
      1. Config value from .agent/config.yaml
      2. Central DEFAULTS table (if known)
      3. Explicit default= argument
      4. None
    """
    config = load_harness_config(config_path, strict=strict)
    
    _MISSING = object()
    val = _MISSING
    
    if key is None:
        if section in config:
            val = config[section]
    else:
        if section in config and isinstance(config[section], dict) and key in config[section]:
            val = config[section][key]
            
    if val is not _MISSING:
        return val
        
    # Check DEFAULTS table
    if key is None:
        if section in DEFAULTS:
            return DEFAULTS.get(section, default)
    else:
        if section in DEFAULTS and key in DEFAULTS[section]:
            return DEFAULTS[section].get(key, default)
            
    return default


def _reset_config_cache() -> None:
    """Clear the global harness config cache (useful in unit tests)."""
    global _CONFIG_CACHE
    _CONFIG_CACHE.clear()


def record_decision(
    title: str,
    decision: str,
    context: str,
    consequence: str,
    date: str | None = None,
    extra_fields: dict[str, str] | None = None,
    log_path: Path | str | None = None,
) -> None:
    """
    Append a structured decision entry to .agent/state/decisions_log.md.
    This is the ONLY sanctioned way to write to this file — never edit it directly with file-write tools.
    Always appends to the true end of the file; never prepends or inserts mid-file.
    """
    if not title.strip() or not decision.strip() or not context.strip() or not consequence.strip():
        raise ValueError("record_decision() requires non-empty title, decision, context, and consequence.")

    entry_date = date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", entry_date):
        raise ValueError(f"date must be YYYY-MM-DD format, got: {entry_date}")

    target_path = Path(log_path) if log_path else (_find_project_root() / ".agent" / "state" / "decisions_log.md")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Note: checking only the last entry's date (existing_dates[-1]) is O(1) and sufficient
    # because record_decision() always appends and the log is maintained in sorted order.
    if target_path.exists():
        existing_content = target_path.read_text(encoding="utf-8")
        existing_dates = re.findall(r"^## (\d{4}-\d{2}-\d{2}):", existing_content, re.MULTILINE)
        if existing_dates:
            last_date = existing_dates[-1]
            if entry_date < last_date:
                raise ValueError(
                    f"record_decision() refused: new entry date {entry_date} is earlier than "
                    f"the last existing entry's date {last_date}. This would silently reintroduce "
                    f"chronological disorder. If this is a genuine correction/backdated record of a "
                    f"past decision, pass an explicit extra_fields={{'Note': '...'}} explaining the "
                    f"backdating rather than bypassing this check, or add it under today's date "
                    f"referencing the earlier event instead."
                )

    entry_lines = [
        f"\n## {entry_date}: {title.strip()}",
        f"- **Decision**: {decision.strip()}",
        f"- **Context**: {context.strip()}",
        f"- **Consequence**: {consequence.strip()}",
    ]

    if extra_fields:
        for k, v in extra_fields.items():
            entry_lines.append(f"- **{k.strip()}**: {v.strip()}")

    entry_str = "\n".join(entry_lines) + "\n"

    if not target_path.exists():
        target_path.write_text("# Decisions Log\n", encoding="utf-8")

    with open(target_path, "a", encoding="utf-8") as f:
        f.write(entry_str)


def archive_old_decisions(
    threshold_lines: int = 150,
    log_path: Path | str | None = None,
    archive_path: Path | str | None = None,
) -> int:
    """
    Move the oldest entries from decisions_log.md to decisions_log_archive.md
    once the main log exceeds threshold_lines. Only the ONE sanctioned way to
    perform archival — never move entries between these files with a file-write
    tool directly.

    Preconditions:
    - decisions_log.md must be in ascending chronological order (guaranteed by
      record_decision()'s backdating guard, assuming no direct edits occurred).

    Returns the number of entries archived (0 if under threshold).
    """
    target_path = Path(log_path) if log_path else (_find_project_root() / ".agent" / "state" / "decisions_log.md")
    dest_path = Path(archive_path) if archive_path else (_find_project_root() / ".agent" / "state" / "decisions_log_archive.md")

    if not target_path.exists():
        return 0

    content = target_path.read_text(encoding="utf-8")
    line_count = len(content.splitlines())
    if line_count <= threshold_lines:
        return 0

    header_match = re.match(r"^(# Decisions Log\n)", content)
    if not header_match:
        raise ValueError("decisions_log.md does not start with expected '# Decisions Log' header — refusing to archive.")
    header = header_match.group(1)
    body = content[header_match.end():]

    raw_entries = re.split(r"(?=^## \d{4}-\d{2}-\d{2}:)", body, flags=re.MULTILINE)
    entries = [e for e in raw_entries if e.strip()]

    if not entries:
        return 0

    # Verify ascending order before trusting "oldest = first N entries".
    dates = []
    for e in entries:
        m = re.match(r"^## (\d{4}-\d{2}-\d{2}):", e)
        if not m:
            raise ValueError(f"Entry does not match expected date-header format, refusing to archive:\n{e[:100]}")
        dates.append(m.group(1))
    if dates != sorted(dates):
        raise ValueError(
            "decisions_log.md is not in ascending chronological order — refusing to archive "
            "until this is corrected (see the reorder procedure used on 2026-07-20). "
            "Archiving an unsorted file would move the wrong entries and call them 'oldest'."
        )

    # Archive entries one at a time from the front until back under threshold,
    # always leaving at least 1 entry in the main log.
    archived_count = 0
    while len(entries) > 1:
        remaining_content = header + "".join(entries)
        if len(remaining_content.splitlines()) <= threshold_lines:
            break
        oldest = entries.pop(0)
        if not dest_path.exists():
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text("# Decisions Log Archive\n", encoding="utf-8")
        with open(dest_path, "a", encoding="utf-8") as f:
            f.write(oldest)
        archived_count += 1

    if archived_count > 0:
        target_path.write_text(header + "".join(entries), encoding="utf-8")

    return archived_count
