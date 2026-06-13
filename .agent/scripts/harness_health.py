#!/usr/bin/env python3
import argparse
import collections
import datetime
import json
import os
import re
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.append(os.getcwd())

# Fix: Ensure UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def get_color(status: str) -> str:
    colors = {
        "HEALTHY": "\033[92m",
        "WARNING": "\033[93m",
        "CRITICAL": "\033[91m",
        "RESET": "\033[0m",
    }
    return colors.get(status, colors["RESET"])


def section_header(title: str):
    print(f"\n\033[1m=== {title} ===\033[0m")


def report_ai_reviews():
    section_header("AI REVIEW HARNESS")
    # Check both potential locations (legacy root and .agent/state/)
    log_paths = [Path(".ai-review-log.jsonl"), Path(".agent/state/ai-review-log.jsonl")]
    log_path = next((p for p in log_paths if p.exists()), None)

    if not log_path:
        print("  Status         : \033[93mNO LOG FOUND\033[0m")
        return

    verdicts = collections.Counter()
    total = 0
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    verdicts[record["verdict"]] += 1
                    total += 1
                except:
                    continue
    except Exception as e:
        print(f"  Error reading log: {e}")
        return

    if total == 0:
        print("  Status         : \033[93mEMPTY LOG\033[0m")
        return

    print(f"  Source         : {log_path}")
    for v, count in verdicts.items():
        pct = (count / total) * 100
        status = (
            "HEALTHY" if v == "PASS" else "CRITICAL" if v == "FAIL_OPEN" else "WARNING"
        )
        print(
            f"  {get_color(status)}{v:10}{get_color('RESET')}: {count:3} ({pct:4.1f}%)"
        )


def report_governance_audit():
    section_header("GOVERNANCE AUDIT LOG")
    audit_path = Path(".agent/state/harness_events.jsonl")
    if not audit_path.exists():
        print("  Status         : \033[94mPENDING (Phase 4)\033[0m")
        return

    severities = collections.Counter()
    total = 0
    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if record.get("event_type") != "governance_observation":
                        continue
                    severity = record.get("severity", "info").upper()
                    severities[severity] += 1
                    total += 1
                except:
                    continue
    except Exception as e:
        print(f"  Error reading audit: {e}")
        return

    if total == 0:
        print("  Status         : \033[92mCLEAN\033[0m")
        return

    for sev in ["CRITICAL", "FAIL", "WARN", "INFO"]:
        if sev in severities:
            count = severities[sev]
            status = (
                "CRITICAL"
                if sev in ["CRITICAL", "FAIL"]
                else "WARNING" if sev == "WARN" else "HEALTHY"
            )
            print(f"  {get_color(status)}{sev:10}{get_color('RESET')}: {count:3}")


def report_resilience_pointer():
    section_header("CIRCUIT BREAKER STATES")
    print("  N circuits tracked — see Grafana resilience dashboard")
    print("  Direct link: http://localhost:3000/d/resilience/service-health")


def report_dlq_pointer():
    section_header("DLQ & EVENT RECOVERY")
    print("  DLQ metrics are product operational data.")
    print("  See: Grafana → Service Health & Resilience → DLQ Recovery panel")
    print("  Direct link: http://localhost:3000/d/resilience/service-health")


def report_backlog(show_all: bool = False):
    section_header("PENDING TASKS & BACKLOG")

    tasks = []
    sources = [
        Path(".agent/state/active_context.md"),
        Path(".agent/state/harness_improvement_backlog.md"),
        Path("docs/planning/AGENT_SYSTEM_IMPROVEMENT_PLAN.md"),
    ]

    for source in sources:
        if source.exists():
            with open(source, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue

                    # Match markdown checkboxes
                    if "- [ ]" in line or "[ ]" in line:
                        item = (
                            line.strip().replace("- [ ]", "").replace("[ ]", "").strip()
                        )
                        if item and item not in tasks:
                            tasks.append(item)
                    # Match table rows
                    elif (
                        "|" in line and "---" not in line and "Date | Event" not in line
                    ):
                        if (
                            "[x]" not in line.lower()
                            and "completed" not in line.lower()
                        ):
                            parts = [p.strip() for p in line.split("|") if p.strip()]
                            if len(parts) >= 3:
                                item = f"{parts[1]}: {parts[2]}"
                                if item not in tasks:
                                    tasks.append(item)

    if not tasks:
        print("  All identified items completed!")
        return

    print(
        f"  Found {len(tasks)} pending items across {len([s for s in sources if s.exists()])} sources."
    )

    display_limit = len(tasks) if show_all else 5
    for _, task in enumerate(tasks[:display_limit]):
        print(f"  - {task}")

    if not show_all and len(tasks) > 5:
        print(f"  ... and {len(tasks) - 5} more items. (Use --all to see full list)")


def report_schema_hardening():
    section_header("SCHEMA HARDENING (HardenedBaseModel)")
    trend_path = Path(".agent/state/schema_hardening_trend.csv")
    if not trend_path.exists():
        print("  Status: \033[93mDATA SOURCE MISSING\033[0m")
        return

    try:
        with open(trend_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) < 2:
                print("  Status: \033[93mINSUFFICIENT DATA\033[0m")
                return

            latest = lines[-1].strip().split(",")
            if len(latest) < 5:
                return

            date, total, hardened, exempt, pct = latest
            pct_val = float(pct) if pct != "manual" else 0.0

            status = (
                "HEALTHY"
                if pct_val >= 90
                else "WARNING" if pct_val >= 50 else "CRITICAL"
            )
            print(f"  Latest Audit   : {date}")
            print(
                f"  Coverage       : {get_color(status)}{pct}%{get_color('RESET')} ({hardened}/{total} models)"
            )
            print(f"  Exemptions     : {exempt}")

            if len(lines) > 2:
                prev = lines[-2].strip().split(",")
                if len(prev) >= 5:
                    prev_pct = float(prev[4]) if prev[4] != "manual" else 0.0
                    if pct_val > prev_pct:
                        print("  Trend          : \033[92m↑ IMPROVING\033[0m")
                    elif pct_val < prev_pct:
                        print("  Trend          : \033[91m↓ REGRESSION\033[0m")
                    else:
                        print("  Trend          : \033[94m→ STABLE\033[0m")
    except Exception as e:
        print(f"  Error reading trend: {e}")


def report_dream_phase():
    section_header("DREAM PHASE")
    state_file = Path(".agent/state/dream_phase_state.json")
    last_run = "never"
    first_run_status = ""

    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
                last_run_utc = state_data.get("last_run_utc")
                if last_run_utc:
                    last_run = last_run_utc
        except Exception:
            pass

    proposals_dir = Path(".agent/state/dream_proposals")
    open_count = 0
    if proposals_dir.exists():
        try:
            open_count = len(list(proposals_dir.glob("*__open.md")))
        except Exception:
            pass

    if last_run == "never":
        first_run_status = " / first run pending data threshold"

    print(f"  Proposals      : {open_count}")
    print(f"  Last Run       : {last_run}{first_run_status}")


def report_token_trends():
    section_header("TOKEN MEASUREMENT & TRENDS")
    ledger_path = Path(".agent/state/session_ledger.jsonl")
    if not ledger_path.exists():
        print("  Status         : \033[94mPENDING (No ledger found)\033[0m")
        return

    sessions = []
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if "token_usage" in record:
                    sessions.append(record["token_usage"])
    except Exception as e:
        print(f"  Error reading ledger: {e}")
        return

    if not sessions:
        print("  Status         : \033[93mNO TOKEN DATA YET\033[0m")
        return

    total_sessions = len(sessions)
    total_calls = sum(s.get("call_count", 0) for s in sessions)
    total_input = sum(s.get("input_tokens", 0) for s in sessions)
    total_output = sum(s.get("output_tokens", 0) for s in sessions)
    total_est = sum(
        s.get("context_load_estimated_tokens", 0) +
        s.get("repo_map_estimated_tokens", 0) +
        s.get("adr_injection_estimated_tokens", 0)
        for s in sessions
    )

    avg_input = total_input / total_sessions
    avg_output = total_output / total_sessions
    avg_est = total_est / total_sessions

    print(f"  Sessions Traced: {total_sessions}")
    print(f"  Total API Calls: {total_calls}")
    print(f"  Avg Actual In  : {avg_input:.1f} tokens/session")
    print(f"  Avg Actual Out : {avg_output:.1f} tokens/session")
    print(f"  Avg Est Overhead: {avg_est:.1f} tokens/session")

    # Trend calculation: last 3 sessions vs previous sessions
    if total_sessions >= 3:
        recent = sessions[-3:]
        prior = sessions[:-3]
        if prior:
            avg_recent_total = sum(s.get("input_tokens", 0) + s.get("output_tokens", 0) for s in recent) / 3
            avg_prior_total = sum(s.get("input_tokens", 0) + s.get("output_tokens", 0) for s in prior) / len(prior)

            # Trend threshold (5% change)
            diff_pct = (avg_recent_total - avg_prior_total) / max(avg_prior_total, 1.0)
            if diff_pct < -0.05:
                print("  Token Trend    : \033[92m↓ IMPROVING (Optimized)\033[0m")
            elif diff_pct > 0.05:
                print("  Token Trend    : \033[91m↑ DEGRADING (Rising Cost)\033[0m")
            else:
                print("  Token Trend    : \033[94m→ STABLE\033[0m")
        else:
            print("  Token Trend    : \033[94m→ STABLE (First session block)\033[0m")
    else:
        print("  Token Trend    : \033[94m→ STABLE (Insufficient data)\033[0m")


def check_harness_alerts():
    events_path = Path(".agent/state/harness_events.jsonl")
    if not events_path.exists():
        return

    has_roster_warn = False
    try:
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                evt = json.loads(line)
                if evt.get("event_type") == "branch_isolation_roster_warning":
                    has_roster_warn = True
    except Exception:
        pass

    if has_roster_warn:
        print("\n\033[91m⚠️  [HARNESS WARNING] No model files matched branch_isolation.model_file_patterns.\033[0m")
        print("\033[91m   BRANCH_ISOLATION suppression is currently inactive. Update config.yaml to fix.\033[0m")


def report_rebuttals():
    section_header("REBUTTAL HARNESS HEALTH")
    log_paths = [Path(".ai-review-log.jsonl"), Path(".agent/state/ai-review-log.jsonl")]
    log_path = next((p for p in log_paths if p.exists()), None)

    if not log_path:
        print("  Status         : \033[93mNO LOG FOUND\033[0m")
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=30)
    
    total_reviews_30d = 0
    agent_rebuttals_30d = 0
    human_rebuttals_30d = 0
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    ts_str = record.get("timestamp")
                    if not ts_str:
                        continue
                    if ts_str.endswith("Z"):
                        ts_str = ts_str[:-1] + "+00:00"
                    rec_dt = datetime.datetime.fromisoformat(ts_str)
                    if rec_dt.tzinfo is None:
                        rec_dt = rec_dt.replace(tzinfo=datetime.timezone.utc)
                    else:
                        rec_dt = rec_dt.astimezone(datetime.timezone.utc)
                        
                    if rec_dt < cutoff:
                        continue
                        
                    strategy = record.get("strategy")
                    if strategy == "rebuttal":
                        actor = record.get("rebuttal_actor", "human")
                        if actor == "agent":
                            agent_rebuttals_30d += 1
                        else:
                            human_rebuttals_30d += 1
                    else:
                        total_reviews_30d += 1
                except Exception:
                    continue
    except Exception as e:
        print(f"  Error reading log: {e}")
        return

    divisor = max(total_reviews_30d, 1)
    agent_rate = (agent_rebuttals_30d / divisor) * 100
    human_rate = (human_rebuttals_30d / divisor) * 100
    
    print(f"  Standard Reviews (30d): {total_reviews_30d}")
    print(f"  Agent-Initiated Rebuttals (30d): {agent_rebuttals_30d} ({agent_rate:.1f}%)")
    print(f"  Human-Initiated Rebuttals (30d): {human_rebuttals_30d} ({human_rate:.1f}%)")
    
    if agent_rate > 15.0:
        print("\033[91m  ⚠️  [ALERT] Agent Rebuttal Rate exceeds 15% (gaming signal)! Recommendation: Restrict agent capabilities.\033[0m")
    if human_rate > 15.0:
        print("\033[93m  ⚠️  [ALERT] Human Rebuttal Rate exceeds 15% (calibration signal)! Recommendation: Relax specific skills.\033[0m")


def report_capability_calibration():
    section_header("CAPABILITY CALIBRATION")
    cal_file = Path(".agent/state/capability_calibration.json")
    if not cal_file.exists():
        print("  Status         : \033[94mNO CALIBRATION DATA (all weights neutral)\033[0m")
        return
        
    try:
        with open(cal_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        capabilities = data.get("capabilities", {})
        if not capabilities:
            print("  Status         : \033[94mNO CALIBRATION RECORDS\033[0m")
            return
            
        for cap, stats in sorted(capabilities.items()):
            tp = stats.get("tp", 1)
            fp = stats.get("fp", 1)
            weight = stats.get("weight", 1.0)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.5
            
            status = "HEALTHY"
            status_text = ""
            
            if precision < 0.30:
                status = "CRITICAL"
                status_text = " [DEGRADING]"
            elif weight == 0.5 or weight == 1.5:
                status = "WARNING"
                status_text = " [AT BOUNDARY - NEEDS MANUAL REVIEW]"
                
            color = get_color(status)
            print(f"  {cap:25}: weight={weight:.2f}, precision={precision:.2f} (tp={tp}, fp={fp}){color}{status_text}\033[0m")
            
    except Exception as e:
        print(f"  Error reading calibration data: {e}")


def report_dream_proposal_staleness():
    section_header("DREAM PROPOSAL STALENESS")
    proposals_dir = Path(".agent/state/dream_proposals")
    if not proposals_dir.exists():
        print("  Status         : NO PROPOSALS DIR")
        return

    warn_days = 30      # config: dream_proposals.staleness_warn_days
    critical_days = 90  # config: dream_proposals.staleness_critical_days
    max_open = 10       # config: dream_proposals.max_open_proposals

    open_proposals = sorted(proposals_dir.glob("*__open.md"))
    if not open_proposals:
        print("  Status         : \033[92mCLEAN (no open proposals)\033[0m")
        return

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    stale_warn, stale_critical = [], []

    for p in open_proposals:
        try:
            content = p.read_text(encoding="utf-8")
            match = re.search(r"Generated:\s*(\d{4}-\d{2}-\d{2})", content)
            if not match:
                continue
            generated = datetime.datetime.strptime(match.group(1), "%Y-%m-%d")
            age_days = (now - generated).days
            if age_days >= critical_days:
                stale_critical.append((p.name, age_days))
            elif age_days >= warn_days:
                stale_warn.append((p.name, age_days))
        except Exception:
            continue

    print(f"  Open proposals : {len(open_proposals)}")
    if len(open_proposals) > max_open:
        print(f"  \033[93m⚠ WARN: {len(open_proposals)} proposals exceeds max ({max_open})\033[0m")
    for name, age in stale_critical:
        print(f"  \033[91mCRITICAL: {name} — {age}d old (>{critical_days}d threshold)\033[0m")
    for name, age in stale_warn:
        print(f"  \033[93mWARN: {name} — {age}d old (>{warn_days}d threshold)\033[0m")
    if not stale_warn and not stale_critical:
        print(f"  Status         : \033[92mHEALTHY (all within {warn_days}d)\033[0m")


# Monitored files: (path, warn_mb, critical_mb)
_SIZE_CHECKS = [
    (".agent/state/repo_graph_cache.json", 2, 10),    # highest priority — pre-commit hot path
    (".agent/state/harness_events.jsonl", 5, 20),
    (".ai-review-log.jsonl", 5, 20),
    (".agent/state/session_ledger.jsonl", 1, 5),
]

def report_state_file_sizes():
    section_header("STATE FILE SIZES")
    any_issue = False
    for filepath, warn_mb, critical_mb in _SIZE_CHECKS:
        p = Path(filepath)
        if not p.exists():
            continue
        size_mb = p.stat().st_size / (1024 * 1024)
        if size_mb >= critical_mb:
            print(f"  \033[91mCRITICAL: {filepath} — {size_mb:.1f}MB (threshold: {critical_mb}MB)\033[0m")
            any_issue = True
        elif size_mb >= warn_mb:
            print(f"  \033[93mWARN: {filepath} — {size_mb:.1f}MB (threshold: {warn_mb}MB)\033[0m")
            any_issue = True
    if not any_issue:
        print("  Status         : \033[92mHEALTHY\033[0m")


def main():
    parser = argparse.ArgumentParser(description="Harness health report")
    parser.add_argument("--all", action="store_true", help="Show all backlog items")
    parser.add_argument("--dream-proposals", action="store_true",
                        help="Run dream proposal staleness check")
    parser.add_argument("--file-sizes", action="store_true",
                        help="Run state file size checks")
    args = parser.parse_args()
    show_all = args.all

    print("\033[1m" + "=" * 60)
    print("  GYM APP RESILIENCE HARNESS HEALTH REPORT")
    print("=" * 60 + "\033[0m")
 
    report_ai_reviews()
    report_rebuttals()
    report_capability_calibration()
    report_governance_audit()
    report_resilience_pointer()
    report_dlq_pointer()
    report_schema_hardening()
    report_dream_phase()
    report_token_trends()

    if args.dream_proposals or True:  # run in default report
        report_dream_proposal_staleness()

    if args.file_sizes or True:  # run in default report
        report_state_file_sizes()

    report_backlog(show_all=show_all)
    check_harness_alerts()
 
    print("\n" + "=" * 60)
    print(f"Report Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
 
 
if __name__ == "__main__":
    main()
