#!/usr/bin/env python3
import collections
import datetime
import json
from pathlib import Path


def summarize_reviews():
    log_path = Path(".ai-review-log.jsonl")
    if not log_path.exists():
        print("No review log found.")
        return

    # Configuration for trend analysis
    lookback_days = 30
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=lookback_days)

    stats = {
        "total": 0,
        "recent": 0,
        "verdicts": collections.Counter(),
        "recent_verdicts": collections.Counter(),
        "concerns": collections.Counter(),
        "recent_concerns": collections.Counter(),
        "fail_open_reasons": collections.Counter(),
        "models": collections.Counter(),
        "daily_volume": collections.Counter(),
    }

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
                timestamp_str = record.get("timestamp")
                if not timestamp_str:
                    continue

                dt = datetime.datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )
                is_recent = dt > cutoff_date.replace(tzinfo=dt.tzinfo)

                stats["total"] += 1
                stats["verdicts"][record["verdict"]] += 1
                stats["models"][record.get("model", "unknown")] += 1
                stats["daily_volume"][dt.date()] += 1

                if is_recent:
                    stats["recent"] += 1
                    stats["recent_verdicts"][record["verdict"]] += 1

                for concern in record.get("concerns", []):
                    stats["concerns"][concern] += 1
                    if is_recent:
                        stats["recent_concerns"][concern] += 1

                if record["verdict"] == "FAIL_OPEN":
                    reason = record.get("fail_open_reason", "unknown")
                    if "timed out" in reason.lower():
                        reason = "Timeout"
                    elif "anthropic" in reason.lower() or "google" in reason.lower():
                        reason = "API Error"
                    stats["fail_open_reasons"][reason] += 1
            except Exception:
                continue

    print("\n" + "=" * 50)
    print("  AI REVIEW HARNESS TELEMETRY")
    print("=" * 50)
    print(
        f"Total Reviews: {stats['total']} ({stats['recent']} in last {lookback_days} days)"
    )
    print("-" * 50)

    print("Verdicts (Trend Analysis):")
    all_verdicts = sorted(
        set(list(stats["verdicts"].keys()) + list(stats["recent_verdicts"].keys()))
    )
    for v in all_verdicts:
        count = stats["verdicts"][v]
        recent = stats["recent_verdicts"][v]
        pct = (count / stats["total"]) * 100 if stats["total"] > 0 else 0
        recent_pct = (recent / stats["recent"]) * 100 if stats["recent"] > 0 else 0

        trend = "SAME"
        if recent_pct > pct + 2:
            trend = "UP  "
        elif recent_pct < pct - 2:
            trend = "DOWN"

        print(
            f"  {v:10} : {count:3} ({pct:4.1f}%) | Recent: {recent:3} ({recent_pct:4.1f}%) [{trend}]"
        )

    if stats["concerns"]:
        print("\nTop Invariant Violations (Last 30 Days):")
        source = stats["recent_concerns"] if stats["recent"] > 0 else stats["concerns"]
        for c, count in source.most_common(5):
            print(f"  {c:25} : {count:3}")

    if stats["fail_open_reasons"]:
        print("\nReliability (Fail-Open Reasons):")
        for r, count in stats["fail_open_reasons"].most_common():
            print(f"  {r:25} : {count:3}")

    # Actionable Insight Generation
    print("-" * 50)
    print("ACTIONABLE INSIGHTS:")

    if stats["recent"] > 0:
        # Check for high failure rate
        fail_rate = (stats["recent_verdicts"].get("FAIL", 0) / stats["recent"]) * 100
        if fail_rate > 15:
            print(
                f"WARNING: HIGH REJECTION RATE: {fail_rate:.1f}% of recent reviews are blocked."
            )
            top_concern = source.most_common(1)[0][0] if source else "None"
            print(
                f"INSIGHT: Investigate {top_concern} patterns; developers are struggling here."
            )

        # Check for fail-open volume
        fail_open_rate = (
            stats["recent_verdicts"].get("FAIL_OPEN", 0) / stats["recent"]
        ) * 100
        if fail_open_rate > 5:
            print(
                f"WARNING: HARNESS INSTABILITY: {fail_open_rate:.1f}% fail-open rate detected."
            )
            print("INSIGHT: Increase circuit breaker timeouts or check API quota.")

        if fail_rate <= 15 and fail_open_rate <= 5:
            print("HEALTHY: Review gates are functioning with stable throughput.")
    else:
        print("Insufficient data for recent trends.")

    print("=" * 50 + "\n")


if __name__ == "__main__":
    summarize_reviews()
