#!/usr/bin/env python3
import collections
import datetime
import json
import os
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


def main():
    show_all = "--all" in sys.argv
    print("\033[1m" + "=" * 60)
    print("  GYM APP RESILIENCE HARNESS HEALTH REPORT")
    print("=" * 60 + "\033[0m")

    report_ai_reviews()
    report_governance_audit()
    report_resilience_pointer()
    report_dlq_pointer()
    report_schema_hardening()
    report_dream_phase()
    report_backlog(show_all=show_all)

    print("\n" + "=" * 60)
    print(f"Report Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
