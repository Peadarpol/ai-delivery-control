import subprocess
import sys
from pathlib import Path

# Bootstrap: depth-agnostic root discovery before harness_utils import
# Ensure src/scripts is in sys.path for harness_utils
_bootstrap_path = Path(__file__).resolve()
_bootstrap_root = None
for _p in [_bootstrap_path] + list(_bootstrap_path.parents):
    if (_p / ".git").exists() or (_p / ".agent").exists():
        _bootstrap_root = _p
        break
if _bootstrap_root and str(_bootstrap_root / "src" / "scripts") not in sys.path:
    sys.path.insert(0, str(_bootstrap_root / "src" / "scripts"))

try:
    from src.scripts.harness_utils import _find_project_root
except ImportError:
    from harness_utils import _find_project_root

_src_scripts = _find_project_root() / "src" / "scripts"
if _src_scripts.exists() and str(_src_scripts) not in sys.path:
    sys.path.insert(0, str(_src_scripts))
from harness_utils import _setup_sys_path, _lock_session, log_harness_event, redact_api_keys, get_harness_config
_setup_sys_path()  # full path setup for remaining imports

import argparse
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from datetime import UTC, datetime

# Optional: SQLite state persistence (T1-D-01). Non-fatal if unavailable.
try:
    from state_persistence import sync_session_to_db as _sync_session_to_db
except ImportError:
    _sync_session_to_db = None  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = Path(".agent/state")
SESSION_FILE = STATE_DIR / "session.json"
LEDGER_FILE = STATE_DIR / "session_ledger.jsonl"



def parse_iso_datetime(dt_str: str) -> datetime:
    """Parse ISO 8601 datetimes safely, supporting timezone offsets, and make offset-naive."""
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def get_commits_after(start_time_str: str) -> list[dict]:
    """Get commits made after the specified start_time using git."""
    try:
        result = subprocess.run(
            ["git", "log", f"--after={start_time_str}", "--pretty=format:%H|%cI|%s"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []

        commits = []
        for line in result.stdout.strip().splitlines():
            if "|" in line:
                sha, date_str, msg = line.split("|", 2)
                commits.append({"sha": sha, "date": date_str, "message": msg})
        return commits
    except Exception:
        return []

def _override_success_has_commit(prev_start: str) -> bool:
    """Cross-check: does a claimed success have a backing commit?"""
    return len(get_commits_after(prev_start)) > 0


def _uncommitted_spec_changes(specs_dir: Path) -> bool:
    """Reliable signal that uncommitted spec work exists (replaces mtime)."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", "--", str(specs_dir)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        return bool(res.stdout.strip())
    except Exception:
        return False




def infer_and_close_previous_session() -> tuple[str | None, str | None]:
    """Retrospectively close the previous session and log its outcome to the ledger."""
    if not SESSION_FILE.exists():
        return None, None

    with _lock_session(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                prev_data = json.load(f)
        except Exception:
            return None, None

        if prev_data.get("status") != "ACTIVE":
            return None, None

        prev_id = prev_data.get("session_id", "pre-session-init")
        prev_start = prev_data.get("start_time")
        prev_agent = prev_data.get("agent", "Agent")
        
        # HIB-GEMINI-01: Read agent_session_close.json early to resolve session_kind overrides
        close_file = STATE_DIR / "agent_session_close.json"
        close_data = None
        if close_file.exists():
            try:
                temp_data = json.loads(close_file.read_text(encoding="utf-8"))
                if temp_data.get("session_id") == prev_id:
                    close_data = temp_data
                else:
                    print(f"[WARNING] Agent close session_id mismatch: {temp_data.get('session_id')} vs previous session {prev_id}")
            except Exception as e:
                print(f"[WARNING] Error reading agent close file: {e}")

        # Resolve session_kind: close-time agent override -> close-time outcome_override (in session.json) -> start-time (in session.json) -> "code"
        if close_data and "session_kind" in close_data:
            prev_session_kind = close_data["session_kind"]
        else:
            prev_session_kind = prev_data.get("session_kind", "code")
            
        expects_commit = (prev_session_kind == "code")

        outcome = "abandoned"
        source = "inferred"
        note = "Session closed with no commits."
        action_str = "No active commits made. Session closed."

        # Aggregate token statistics strictly matching this session_id from .ai-review-log.jsonl
        input_tokens = 0
        output_tokens = 0
        context_load_est = 0
        repo_map_est = 0
        adr_injection_est = 0
        call_count = 0
        has_fail = False

        REVIEW_LOG_FILE = Path(".ai-review-log.jsonl")
        if REVIEW_LOG_FILE.exists():
            try:
                start_dt = parse_iso_datetime(prev_start)
                lines = REVIEW_LOG_FILE.read_text(encoding="utf-8").splitlines()
                for line in lines:
                    if not line.strip():
                        continue
                    log = json.loads(line)

                    # Verify session_id match strictly
                    log_session_id = log.get("session_id")
                    if log_session_id != prev_id:
                        continue

                    call_count += 1
                    usage = log.get("token_usage", {})
                    input_tokens += usage.get("input_tokens", 0)
                    output_tokens += usage.get("output_tokens", 0)
                    context_load_est += usage.get("context_load_estimated_tokens", 0)
                    repo_map_est += usage.get("repo_map_estimated_tokens", 0)
                    adr_injection_est += usage.get("adr_injection_estimated_tokens", 0)

                    # Check for FAIL verdict within this session
                    log_time = parse_iso_datetime(log.get("timestamp", ""))
                    if log_time > start_dt and log.get("verdict") == "FAIL":
                        has_fail = True
            except Exception:
                pass

        # Support outcome_override in session.json
        if "outcome_override" in prev_data:
            outcome = prev_data["outcome_override"]
            source = prev_data.get("outcome_override_source", "agent_override")
            note = prev_data.get("outcome_override_note", "Closed via explicit override.")
            
            # HIB-053: cross-check before accepting success claim
            if outcome == "success" and expects_commit and not _override_success_has_commit(prev_start):
                outcome = "partial"
                note = (
                    "outcome_override claimed success but no commit found after session start. "
                    "Downgraded to partial (HIB-053 write-before-verify guard)."
                )
                source = "inferred"
        else:
            # 1. Check for escalation
            is_escalated = False
            # A. Check for HALT file
            if (STATE_DIR / "HALT").exists():
                is_escalated = True
                note = "Session halted due to active HALT file."
            # B. Check for halt_event or critical severity in harness_events.jsonl
            EVENTS_FILE = STATE_DIR / "harness_events.jsonl"
            if not is_escalated and EVENTS_FILE.exists():
                try:
                    start_dt = parse_iso_datetime(prev_start)
                    lines = EVENTS_FILE.read_text(encoding="utf-8").splitlines()
                    for line in lines:
                        if not line.strip():
                            continue
                        evt = json.loads(line)
                        evt_time = parse_iso_datetime(evt.get("timestamp_utc", ""))
                        if evt_time > start_dt:
                            if (
                                evt.get("event_type") == "halt_event"
                                or evt.get("severity") == "critical"
                            ):
                                is_escalated = True
                                note = f"Session halted due to critical event: {evt.get('payload', {}).get('detail', 'Unknown error')}"
                                break
                except Exception:
                    pass

            if is_escalated:
                outcome = "escalated"
                action_str = "Session halted due to escalation/critical failure."
            else:
                # 2. Check for commits made
                commits = get_commits_after(prev_start)
                spec_files_modified = False
                
                if not commits:
                    # Scan for modified spec files in specs_path
                    try:
                        specs_path_str = get_harness_config("spec_gate", "specs_path")
                        specs_dir = PROJECT_ROOT / Path(specs_path_str)

                        if specs_dir.exists() and specs_dir.is_dir():
                            if _uncommitted_spec_changes(specs_dir):
                                spec_files_modified = True
                                action_str = "Uncommitted specification changes present"
                    except Exception:
                        pass

                if commits or spec_files_modified:
                    if commits:
                        action_str = f"[COMMIT]: {commits[0]['message']}"
                    
                    # Check for open tasks in active_context.md
                    has_open_tasks = False
                    CONTEXT_FILE = STATE_DIR / "active_context.md"
                    if CONTEXT_FILE.exists():
                        try:
                            content = CONTEXT_FILE.read_text(encoding="utf-8")
                            if "- [ ]" in content:
                                has_open_tasks = True
                        except Exception:
                            pass

                    if commits:
                        if not has_fail and not has_open_tasks:
                            outcome = "success"
                            note = "All committed changes completed with no pending open tasks."
                        else:
                            outcome = "partial"
                            note = f"Changes committed but open tasks or review failures remain. (FAIL reviews: {has_fail}, open tasks: {has_open_tasks})"
                    else:
                        outcome = "partial"
                        note = ("Uncommitted specification changes present but no commit found — "
                                "work not persisted. Downgraded to partial (HIB-053b guard).")
                else:
                    # 3. No commits, no spec changes, and not escalated => check session kind
                    if prev_session_kind != "code":
                        outcome = "partial"
                        note = f"Session closed with no commits. Outcome labeled partial (non-code session: {prev_session_kind})."
                        action_str = f"No active commits made. Session labeled partial ({prev_session_kind})."
                    else:
                        outcome = "abandoned"
                        note = "Session closed with no commits."
                        action_str = "No active commits made. Session abandoned."

        # Format date for ledger: prev_start as YYYY-MM-DD HH:MM
        try:
            dt = parse_iso_datetime(prev_start)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        if close_data:
            claimed_outcome = close_data.get("outcome", outcome)
            
            # HIB-053: cross-check before accepting success claim
            if claimed_outcome == "success" and expects_commit and not _override_success_has_commit(prev_start):
                claimed_outcome = "partial"
                close_note = (
                    "agent_session_close claimed success but no commit found after session start. "
                    "Downgraded to partial (HIB-053 write-before-verify guard)."
                )
            else:
                close_note = close_data.get("outcome_note", note)
            outcome = claimed_outcome
            note = close_note
            source = "agent_close"
            try:
                close_file.unlink()
                print(f"[SESSION] Agent close file consumed — outcome: {outcome}")
            except Exception:
                pass

        # Log to session_ledger.jsonl
        token_usage_stats = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "context_load_estimated_tokens": context_load_est,
            "repo_map_estimated_tokens": repo_map_est,
            "adr_injection_estimated_tokens": adr_injection_est,
            "call_count": call_count,
        }

        # Read harness version dynamically
        _version_file = Path(__file__).parent.parent.parent / "harness_version.txt"
        _harness_version = _version_file.read_text(encoding="utf-8").strip() if _version_file.exists() else "unknown"

        ledger_entry = {
            "session_id": prev_id,
            "date": date_str,
            "action": action_str,
            "startup_checked": True,
            "agent": prev_agent,
            "outcome": outcome,
            "outcome_source": source,
            "outcome_note": note,
            "harness_version": _harness_version,
            "token_usage": token_usage_stats,
        }

        try:
            with open(LEDGER_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(ledger_entry) + "\n")
        except Exception:
            pass

        # Update session.json status
        prev_data["status"] = "COMPLETED"
        prev_data["outcome"] = outcome
        prev_data["outcome_source"] = source
        prev_data["outcome_note"] = note
        prev_data["token_usage"] = token_usage_stats
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(prev_data, f, indent=4)
        except Exception:
            pass

        if outcome == "success":
            _drop_session_checkpoint_stash(prev_id)
            _snapshot_live_logs(prev_id)

        return outcome, note


def _snapshot_live_logs(session_id: str) -> None:
    """Snapshot untracked live logs (.ai-review-log.jsonl and harness_events.jsonl) on clean session close (HIB-063)."""
    try:
        snapshot_dir = STATE_DIR / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        safe_id = re.sub(r"[^\w\.-]", "_", session_id or "unknown")
        live_events = STATE_DIR / "harness_events.jsonl"
        if live_events.exists() and live_events.stat().st_size > 0:
            target_events = snapshot_dir / f"harness_events_{safe_id}.jsonl"
            shutil.copy2(live_events, target_events)

        live_review = PROJECT_ROOT / ".ai-review-log.jsonl"
        if live_review.exists() and live_review.stat().st_size > 0:
            target_review = snapshot_dir / f"ai_review_log_{safe_id}.jsonl"
            shutil.copy2(live_review, target_review)
    except Exception as e:
        print(f"[SESSION] Live log snapshot warning: {e}")


def load_hot_tier(ledger_path: Path = LEDGER_FILE, n: int = 3) -> list[dict]:
    """Load the n most recent session records for hot-tier context injection."""
    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-n:] if line.strip()]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def print_hot_tier(records: list[dict]) -> None:
    if not records:
        print("[HOT-TIER] No recent session records found.")
        return
    print(f"[HOT-TIER] Last {len(records)} session(s):")
    for r in records:
        outcome = r.get("outcome") or "null"
        checked = "Y" if r.get("startup_checked") else "-"
        print(
            f"  {checked} {r['date'][:10]}  {r['session_id'][:12]}  {outcome:10}  {r['action'][:80]}"
        )


def orient_agent(prev_outcome: str | None, prev_note: str | None) -> None:
    """Print high-visibility orientation alerts at startup based on the previous session's outcome."""
    if not prev_outcome:
        return

    # Use standard GFM Alert style for console and logs
    print("\n" + "=" * 80)
    if prev_outcome == "success":
        print("> [!NOTE]")
        print(f"> PREVIOUS SESSION SUCCESS: {prev_note}")
    elif prev_outcome == "partial":
        print("> [!IMPORTANT]")
        print(f"> PREVIOUS SESSION PARTIAL: {prev_note}")
        print("> Please resolve open tasks and review warnings before proceeding.")
    elif prev_outcome == "abandoned":
        print("> [!WARNING]")
        print(f"> PREVIOUS SESSION ABANDONED: {prev_note}")
        print("> Ensure that git commits are structured and verified.")
    elif prev_outcome == "escalated":
        print("> [!CAUTION]")
        print(f"> PREVIOUS SESSION ESCALATED: {prev_note}")
        print(
            "> CRITICAL WARNING: A previous session encountered a halting condition or critical event."
        )
    print("=" * 80 + "\n")


def get_current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip()
    except Exception:
        return ""

def get_modified_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        files = []
        for line in result.stdout.splitlines():
            if len(line) > 3:
                files.append(line[3:].strip())
        return files
    except Exception:
        return []

def classify_task_magnitude() -> str:
    branch = get_current_branch()
    files = get_modified_files()
    file_count = len(files)
    
    # 1. Primary Signal: Branch name
    micro_patterns = [r"hotfix/", r"fix/doc", r"docs?/", r"chore/", r"typo/"]
    major_patterns = [r"rfc/", r"spec/", r"release/", r"migration/", r"epic/"]
    
    magnitude = "standard"
    for pat in micro_patterns:
        if re.search(pat, branch, re.IGNORECASE):
            magnitude = "micro"
            break
            
    for pat in major_patterns:
        if re.search(pat, branch, re.IGNORECASE):
            magnitude = "major"
            break
            
    # 2. Secondary Signal: File state
    code_extensions = {".py", ".js", ".ts", ".go", ".java", ".rs", ".cs"}
    has_code = False
    has_migrations = False
    
    for f in files:
        f_lower = f.lower().replace("\\", "/")
        ext = Path(f).suffix.lower()
        if ext in code_extensions:
            has_code = True
        if "migration" in f_lower or re.search(r"v\d+_\d+_\d+_to_v\d+_\d+_\d+\.py", Path(f).name):
            has_migrations = True
            
    if has_migrations or file_count > 20:  # configurable: magnitude.major_file_threshold
        magnitude = "major"
    elif magnitude == "micro" and has_code:
        magnitude = "standard"
    elif magnitude == "standard" and file_count > 0 and not has_code:
        magnitude = "micro"
        
    return magnitude

def _should_skip_background_tasks() -> bool:
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("task_magnitude") == "micro"
        except Exception:
            pass
    return False

def initialize_session(agent_name: str = "Harness", session_kind: str | None = None) -> str:
    """Initializes or updates the current session state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    with _lock_session(SESSION_FILE):
        # Clean structured JSON token budget HALT on startup
        halt_path = STATE_DIR / "HALT"
        if halt_path.exists():
            try:
                halt_data = json.loads(halt_path.read_text(encoding="utf-8"))
                if halt_data.get("reason") == "token_budget_exhausted":
                    halt_path.unlink()
                    print("[INIT] Resetting session token budget halt.")
            except Exception:
                pass

        session_id = str(uuid.uuid4())
        start_time = datetime.now(UTC).replace(tzinfo=None).isoformat() + "Z"

        magnitude = "standard"
        magnitude_source = "auto"
        
        if SESSION_FILE.exists():
            try:
                with open(SESSION_FILE, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    if old_data.get("task_magnitude_source") == "agent_override":
                        magnitude = old_data.get("task_magnitude", "standard")
                        magnitude_source = "agent_override"
            except Exception:
                pass
                
        if magnitude_source == "auto":
            magnitude = classify_task_magnitude()

        if not session_kind:
            session_kind = os.environ.get("AGENT_SESSION_KIND")
            
        if session_kind and session_kind not in ["code", "analysis", "planning", "review"]:
            print(f"[WARNING] Invalid AGENT_SESSION_KIND '{session_kind}', defaulting to 'code'")
            session_kind = "code"
        elif not session_kind:
            session_kind = "code"

        session_data = {
            "schema_version": "1.0",
            "session_id": session_id,
            "start_time": start_time,
            "last_activity": start_time,
            "status": "ACTIVE",
            "agent": agent_name,
            "task_magnitude": magnitude,
            "task_magnitude_source": magnitude_source,
            "session_kind": session_kind,
            "token_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
                "cache_read_input_tokens": 0,
                "context_load_estimated_tokens": 0,
                "repo_map_estimated_tokens": 0,
                "adr_injection_estimated_tokens": 0,
                "call_count": 0,
            }
        }

        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=4)

        print(f"[INIT] Session {session_id} initialized.")
        print(f"[MAGNITUDE] Task Magnitude Auto-Classified: {magnitude.upper()} (source: {magnitude_source})")
        if magnitude == "major":
            print("\n" + "=" * 80)
            print("💡 [MAGNITUDE] Major task session initialized. Loading full warm-tier context...")
            print("   Please review architectural context before execution:")
            print(f"   {PROJECT_ROOT}/.agent/state/decisions_log.md")
            print("=" * 80 + "\n")

        # Non-blocking SQLite sync — errors are caught inside sync_session_to_db
        if _sync_session_to_db is not None:
            _sync_session_to_db(session_data)

        return session_id


def record_post_commit_heartbeat() -> None:
    """Record commit heartbeat to current session and log event."""
    if not SESSION_FILE.exists():
        print("[HEARTBEAT] No session.json found. Creating a minimal session.")
        initialize_session(agent_name="git_hook")

    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            session_data = json.load(f)
    except Exception as e:
        print(f"[HEARTBEAT] Error loading session: {e}")
        return

    now_str = datetime.now(UTC).replace(tzinfo=None).isoformat() + "Z"
    session_data["last_activity"] = now_str

    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=4)
    except Exception as e:
        print(f"[HEARTBEAT] Error writing session: {e}")

    EVENTS_FILE = STATE_DIR / "harness_events.jsonl"
    try:
        sha_res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        sha = sha_res.stdout.strip() if sha_res.returncode == 0 else "unknown"

        msg_res = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        msg = (
            msg_res.stdout.strip()
            if msg_res.returncode == 0
            else "unknown commit message"
        )

        record = {
            "schema_version": "1.0",
            "event_type": "commit_made",
            "timestamp_utc": now_str,
            "session_id": session_data.get("session_id"),
            "commit_sha": sha,
            "agent": "git_hook",
            "severity": "INFO",
            "payload": {"msg": f"Commit detected via post-commit heartbeat: {msg}"},
        }

        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        print(
            f"[HEARTBEAT] Updated session {session_data.get('session_id')[:8]} activity. Logged commit."
        )
    except Exception as e:
        print(f"[HEARTBEAT] Error writing harness event: {e}")


def maybe_run_dream_phase(prev_outcome: str | None) -> None:
    """Evaluate thresholds and cooldowns, then maybe execute the dream phase distillation."""
    if _should_skip_background_tasks():
        return
    DREAM_STATE_FILE = STATE_DIR / "dream_phase_state.json"
    last_run_utc = "1970-01-01T00:00:00Z"

    if DREAM_STATE_FILE.exists():
        try:
            with open(DREAM_STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)
                last_run_utc = state_data.get("last_run_utc", last_run_utc)
        except Exception:
            pass

    try:
        last_run_dt = parse_iso_datetime(last_run_utc)
    except Exception:
        last_run_dt = datetime.min

    # Check for bypass conditions
    bypass = False
    if prev_outcome == "escalated":
        bypass = True
        print(
            "[DREAM] Critical bypass: previous session escalated. Triggering dream phase..."
        )
    else:
        # Check harness_events.jsonl for critical events since last_run_dt
        EVENTS_FILE = STATE_DIR / "harness_events.jsonl"
        if EVENTS_FILE.exists():
            try:
                lines = EVENTS_FILE.read_text(encoding="utf-8").splitlines()
                for line in lines:
                    if not line.strip():
                        continue
                    evt = json.loads(line)
                    evt_time = parse_iso_datetime(evt.get("timestamp_utc", ""))
                    if evt_time > last_run_dt:
                        if (
                            evt.get("severity") == "critical"
                            or evt.get("event_type") == "halt_event"
                        ):
                            bypass = True
                            print(
                                f"[DREAM] Critical bypass: event '{evt.get('event_type')}' with severity '{evt.get('severity')}' detected since last run. Triggering dream phase..."
                            )
                            break
            except Exception:
                pass

    if not bypass:
        # 1. 7-day cooldown guard
        now = datetime.now(UTC).replace(tzinfo=None)
        if (now - last_run_dt).days < 7:
            # Cooldown active, skip quietly
            return

        # 2. Session ledger thresholds
        min_sessions = 15
        min_span_days = 14

        if not LEDGER_FILE.exists():
            return

        try:
            ledger_lines = [
                json.loads(line)
                for line in LEDGER_FILE.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except Exception:
            return

        if len(ledger_lines) < min_sessions:
            return

        dates = []
        for r in ledger_lines:
            date_str = r.get("date", "")
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                dates.append(dt)
            except Exception:
                pass

        if not dates:
            return

        span_days = (max(dates) - min(dates)).days
        if span_days < min_span_days:
            return

    # Execute dream phase compiler
    try:
        print("[DREAM] Running Dream Phase Distillation Engine...")
        result = subprocess.run(
            [sys.executable, ".agent/scripts/distill_dream.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode == 0:
            stdout_lines = result.stdout.strip().splitlines()
            if stdout_lines:
                print(f"[DREAM] {stdout_lines[0]}")
            else:
                print("[DREAM] Distillation complete.")
        else:
            print(f"[DREAM] Error running distillation: {result.stderr.strip()}")
    except Exception as e:
        print(f"[DREAM] Distillation failed to execute: {e}")

    # Update dream_phase_state.json
    now_str = datetime.now(UTC).replace(tzinfo=None).isoformat() + "Z"
    try:
        with open(DREAM_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_run_utc": now_str}, f, indent=4)
    except Exception:
        pass


def maybe_run_wiki_compile() -> None:
    """Evaluate thresholds and execute the wiki compiler if needed."""
    if _should_skip_background_tasks():
        return
    WIKI_STATE_FILE = STATE_DIR / "wiki_compile_state.json"
    last_run_utc = "1970-01-01T00:00:00Z"
    last_failure_utc = None

    if WIKI_STATE_FILE.exists():
        try:
            with open(WIKI_STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)
                last_run_utc = state_data.get("last_run_utc", last_run_utc)
                last_failure_utc = state_data.get("last_failure_utc")
        except Exception:
            pass

    try:
        last_run_dt = parse_iso_datetime(last_run_utc)
    except Exception:
        last_run_dt = datetime.min

    now = datetime.now(UTC).replace(tzinfo=None)

    if last_failure_utc:
        try:
            last_failure_dt = parse_iso_datetime(last_failure_utc)
            if (now - last_failure_dt).total_seconds() < 24 * 3600:
                # Failure cooldown active (24 hours)
                return
        except Exception:
            pass

    if (now - last_run_dt).days < 7:
        # Cooldown active, skip quietly
        return

    try:
        result = subprocess.run(
            [sys.executable, ".agent/scripts/wiki_compile.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode == 0:
            stdout_lines = result.stdout.strip().splitlines()
            if stdout_lines:
                for line in stdout_lines:
                    print(f"{line}")
        else:
            print(f"[WIKI] Error running compilation: {result.stderr.strip()}")
    except Exception as e:
        print(f"[WIKI] Compilation failed to execute: {e}")


def maybe_run_wiki_lint() -> None:
    """Evaluate thresholds and execute the local wiki linter if needed."""
    if _should_skip_background_tasks():
        return
    WIKI_LINT_STATE_FILE = STATE_DIR / "wiki_lint_state.json"
    last_run_utc = "1970-01-01T00:00:00Z"

    if WIKI_LINT_STATE_FILE.exists():
        try:
            with open(WIKI_LINT_STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)
                last_run_utc = state_data.get("last_run_utc", last_run_utc)
        except Exception:
            pass

    try:
        last_run_dt = parse_iso_datetime(last_run_utc)
    except Exception:
        last_run_dt = datetime.min

    now = datetime.now(UTC).replace(tzinfo=None)
    if (now - last_run_dt).days < 14:
        # Cooldown active (14-day default for lint since it is less time-sensitive than compile), skip quietly
        return

    try:
        result = subprocess.run(
            [sys.executable, ".agent/scripts/wiki_lint.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode == 0:
            stdout_lines = result.stdout.strip().splitlines()
            if stdout_lines:
                for line in stdout_lines:
                    print(f"{line}")
            # Update state file
            now_str = datetime.now(UTC).replace(tzinfo=None).isoformat() + "Z"
            with open(WIKI_LINT_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_run_utc": now_str}, f, indent=4)
        else:
            print(f"[WIKI LINT] Error running lint pass: {result.stderr.strip()}")
    except Exception as e:
        print(f"[WIKI LINT] Linter failed to execute: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent session initializer")
    parser.add_argument(
        "--hot-tier",
        action="store_true",
        help="Print the last 3 session records (hot-tier context) instead of initializing",
    )
    parser.add_argument(
        "--hot-tier-n",
        type=int,
        default=3,
        metavar="N",
        help="Number of recent sessions to load for hot-tier (default: 3)",
    )
    parser.add_argument(
        "--post-commit",
        action="store_true",
        help="Update session last activity and record commit heartbeat",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default=None,
        help="Name of the agent running this session",
    )
    parser.add_argument(
        "--session-kind",
        type=str,
        default=None,
        choices=["code", "analysis", "planning", "review"],
        help="Kind of session (code, analysis, planning, review)",
    )
    args = parser.parse_args()

    if args.hot_tier:
        records = load_hot_tier(n=args.hot_tier_n)
        print_hot_tier(records)
    elif args.post_commit:
        record_post_commit_heartbeat()
    else:
        # Retrospective close of previous session
        prev_outcome, prev_note = infer_and_close_previous_session()

        # Print orientation alert if previous session was closed
        if prev_outcome:
            orient_agent(prev_outcome, prev_note)

        # Determine agent name and initialize new session
        agent_name = args.agent or os.environ.get("AGENT_ID") or "Harness"
        session_id = initialize_session(agent_name=agent_name, session_kind=args.session_kind)
        _create_session_checkpoint(session_id)

        # Maybe run dream phase distillation
        maybe_run_dream_phase(prev_outcome)

        # Maybe run wiki compile
        maybe_run_wiki_compile()

        # Maybe run wiki lint
        maybe_run_wiki_lint()


def _drop_session_checkpoint_stash(session_id: str) -> None:
    """Drop session-start AUTO checkpoint stash on clean close (T1-I-08)."""
    try:
        res = subprocess.run(["git", "stash", "list"], capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout:
            prefix = session_id[:12] if len(session_id) >= 12 else session_id
            for line in res.stdout.splitlines():
                if f"AUTO: session-start checkpoint [{prefix}]" in line or f"AUTO: session-start checkpoint [{session_id}]" in line:
                    stash_ref = line.split(":")[0].strip()
                    subprocess.run(["git", "stash", "drop", stash_ref], capture_output=True, text=True, timeout=10)
                    print(f"[SESSION] Clean close: dropped session checkpoint stash ({stash_ref})")
                    break
    except Exception:
        pass


def _create_session_checkpoint(session_id: str) -> None:
    """Create a recoverable git stash at session start. Non-fatal if stash fails."""
    if not (Path.cwd() / ".git").exists():
        return

    # Check if working directory is dirty
    try:
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10
        )
        if status_res.returncode != 0 or not status_res.stdout.strip():
            return  # Clean working tree, nothing to stash
    except Exception:
        return

    # Interactive TTY prompt (HIB-ENV-02)
    if sys.stdin and sys.stdin.isatty():
        try:
            print("Uncommitted changes detected. Create session-start recovery stash? [Y/n]: ", end="", flush=True)
            response = sys.stdin.readline().strip().lower()
            if response not in ("", "y", "yes"):
                print("[SESSION] Session checkpoint stash skipped by operator confirmation.")
                return
        except Exception:
            pass

    try:
        prefix = session_id[:12] if len(session_id) >= 12 else session_id
        result = subprocess.run(
            ["git", "stash", "push", "--include-untracked",
             "-m", f"AUTO: session-start checkpoint [{prefix}]"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and "No local changes" not in result.stdout:
            print(f"[SESSION] Checkpoint created: git stash (session {prefix})")
    except Exception:
        pass  # Non-fatal — checkpoint is a safety net, not a requirement


if __name__ == "__main__":
    main()
