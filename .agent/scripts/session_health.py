#!/usr/bin/env python3
import datetime
import json
import os
import sys
from pathlib import Path

def _find_project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / ".agent" / "config.yaml").exists() or (cwd / ".git").exists():
        return cwd
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".agent" / "config.yaml").exists() or (parent / ".git").exists():
            return parent
    return cwd


PROJECT_ROOT = _find_project_root()
_src_scripts = PROJECT_ROOT / "src" / "scripts"
if _src_scripts.exists() and str(_src_scripts) not in sys.path:
    sys.path.insert(0, str(_src_scripts))

import harness_utils


def main():
    session_file = Path(".agent/state/session.json")
    events_file = Path(".agent/state/harness_events.jsonl")
    config_file = Path(".agent/config.yaml")
    review_log_file = Path(".ai-review-log.jsonl")
    halt_file = Path(".agent/state/HALT")

    if not session_file.exists():
        print("Error: No active session.json found. Run init_session.py first.")
        sys.exit(1)

    try:
        session_data = json.loads(session_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading session.json: {e}")
        sys.exit(1)

    session_id = session_data.get("session_id", "unknown")
    start_time_str = session_data.get("start_time")
    agent = session_data.get("agent", "Harness")

    # Load session ceiling
    ceiling = 1000000  # Default fallback: 1M tokens
    if config_file.exists():
        try:
            for line in config_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("session_token_budget:"):
                    val = stripped.split(":", 1)[1].split("#", 1)[0].strip().strip("\"'")
                    if val and val.lower() not in ("null", "~", "none"):
                        ceiling_val = int(val)
                        if ceiling_val < 100000:
                            ceiling = ceiling_val * 1000
                        else:
                            ceiling = ceiling_val
        except Exception:
            pass

    # Read events
    events = []
    if events_file.exists():
        try:
            for line in events_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                evt = json.loads(line)
                if evt.get("session_id") == session_id:
                    events.append(evt)
        except Exception:
            pass

    # Duration calculation
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    duration_str = "N/A"
    started_str = "N/A"
    if start_time_str:
        try:
            if start_time_str.endswith("Z"):
                start_time_str = start_time_str[:-1] + "+00:00"
            started_dt = datetime.datetime.fromisoformat(start_time_str).replace(tzinfo=None)
            started_str = started_dt.strftime("%H:%M")
            delta = now - started_dt
            minutes = int(delta.total_seconds() / 60)
            duration_str = f"{minutes} minutes"
        except Exception:
            pass

    # Print report header
    now_local = datetime.datetime.now()
    print(f"Session Health Report — {now_local.strftime('%Y-%m-%d %H:%M')}")
    print("─" * 41)
    print(f"Session ID   : {session_id[:8]}…")
    print(f"Duration     : {duration_str}")
    print(f"Started      : {started_str}")
    print(f"Events       : {len(events)} recorded in harness_events.jsonl")
    print()

    # Warning patterns
    print("Warning patterns:")
    warnings_found = False

    # Check same file read 3+ times
    file_reads = {}
    for evt in events:
        if evt.get("event_type") == "file_read":
            payload = evt.get("payload", {})
            filepath = payload.get("path") or payload.get("file") or payload.get("filepath")
            if filepath:
                file_reads[filepath] = file_reads.get(filepath, 0) + 1

    file_reads_triggered = {fp: c for fp, c in file_reads.items() if c >= 3}
    if file_reads_triggered:
        for fp, c in file_reads_triggered.items():
            print(f"  ⚠ Same file read 3+ times: {fp} ({c}x)")
            warnings_found = True
    else:
        print("  Same file read 3+: N/A (no file_read events emitted by current harness)")

    # Check repeated errors
    errors = {}
    for evt in events:
        payload = evt.get("payload", {})
        err = payload.get("error") or payload.get("exception") or payload.get("error_name")
        if err:
            errors[err] = errors.get(err, 0) + 1

    errors_triggered = {e: c for e, c in errors.items() if c >= 2}
    if errors_triggered:
        for err, c in errors_triggered.items():
            print(f"  ⚠ Repeated error: \"{err}\" appeared {c}x")
            warnings_found = True
    else:
        print("  Repeated error   : N/A (no repeated errors detected)")

    print()

    # Gate verdicts
    pass_count = 0
    fail_count = 0
    if review_log_file.exists():
        try:
            for line in review_log_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("session_id") == session_id:
                    verdict = record.get("verdict")
                    if verdict == "PASS":
                        pass_count += 1
                    elif verdict == "FAIL":
                        fail_count += 1
        except Exception:
            pass

    print(f"Gate verdicts this session: {pass_count} PASS, {fail_count} FAIL")

    # Token usage
    token_usage = session_data.get("token_usage", {})
    in_tokens = token_usage.get("input_tokens", 0)
    out_tokens = token_usage.get("output_tokens", 0)
    total_tokens = in_tokens + out_tokens
    pct = int((total_tokens / ceiling) * 100) if ceiling > 0 else 0

    print(f"Token usage  : {in_tokens:,} in / {out_tokens:,} out ({pct}% of session ceiling)")

    # HALT check
    halted = "detected" if halt_file.exists() else "not detected"
    print(f"HALT file    : {halted}")

if __name__ == "__main__":
    main()
