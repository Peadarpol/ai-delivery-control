#!/usr/bin/env python3
"""
Kill Switch Sentinel.
Checks for the presence of .agent/state/HALT.
If found, prints the reason and exits with code 2 (unless bypassed).
"""

import os
import sys
import json
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_src_scripts = PROJECT_ROOT / "src" / "scripts"
if _src_scripts.exists() and str(_src_scripts) not in sys.path:
    sys.path.insert(0, str(_src_scripts))

import harness_utils

HALT_PATH = PROJECT_ROOT / ".agent" / "state" / "HALT"
EVENTS_FILE = PROJECT_ROOT / ".agent" / "state" / "harness_events.jsonl"
SESSION_FILE = PROJECT_ROOT / ".agent" / "state" / "session.json"

def log_bypass_event(bypass_reason: str, msg: str):
    try:
        session_id = None
        if SESSION_FILE.exists():
            try:
                with open(SESSION_FILE, "r", encoding="utf-8") as f:
                    session_id = json.load(f).get("session_id")
            except Exception:
                pass
                
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        
        record = {
            "schema_version": "1.0",
            "event_type": "halt_bypass",
            "timestamp_utc": now_utc,
            "session_id": session_id,
            "commit_sha": None,
            "agent": os.environ.get("AGENT_ID", "check_halt"),
            "severity": "WARNING",
            "payload": {
                "bypass_reason": bypass_reason,
                "original_halt_reason": "token_budget_exhausted",
                "original_halt_message": msg,
            },
        }
        
        EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

def main():
    if HALT_PATH.exists():
        raw_content = HALT_PATH.read_text(encoding="utf-8").strip()
        try:
            data = json.loads(raw_content)
            reason = data.get("reason", "governance_violation")
            msg = data.get("message", raw_content)
        except Exception:
            reason = "governance_violation"
            msg = raw_content or "No reason provided."

        if reason == "token_budget_exhausted":
            bypass_reason = os.environ.get("BYPASS_HALT_REASON", "").strip()
            if bypass_reason:
                print("\n" + "⚠️ " * 30)
                print("  ⚠️ [HALT BYPASS] Token budget halt bypassed via environment variable!")
                print(f"  Bypass Reason: {bypass_reason}")
                print("⚠️ " * 30 + "\n")
                log_bypass_event(bypass_reason, msg)
                sys.exit(0)
            
            # Print standard token exhausted halt
            print("\n" + "!" * 60)
            print("  !!! EXECUTION HALTED: SESSION TOKEN BUDGET EXHAUSTED !!!")
            print(f"  {msg}")
            print("\n  To override this halt in emergency situations, run with:")
            print("  BYPASS_HALT_REASON=\"<your-reason>\" git commit ...")
            print("!" * 60 + "\n")
            sys.exit(2)
        else:
            # Print governance violation halt
            print("\n" + "!" * 60)
            print("  !!! EXECUTION HALTED BY SENTINEL (GOVERNANCE VIOLATION) !!!")
            print(f"  Reason: {msg}")
            print("!" * 60 + "\n")
            sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()
