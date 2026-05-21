#!/usr/bin/env python3
"""
Retention Cleanup — archives harness state entries older than configured thresholds.

Targets:
  .agent/state/session_ledger.jsonl   (date field)
  .agent/state/harness_events.jsonl   (timestamp_utc field)
  .ai-review-log.jsonl                (timestamp field)

Archive destination: ~/.aisdlc/archive/<stem>_archive_YYYY-MM.jsonl
Archive granularity: one file per calendar month.

Idempotent — running twice produces an identical result.
"""

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

CONFIG_PATH = Path(".agent/config.yaml")
STATE_DIR = Path(".agent/state")
ARCHIVE_DIR = Path.home() / ".aisdlc" / "archive"

_TARGETS = [
    {
        "file": STATE_DIR / "session_ledger.jsonl",
        "date_field": "date",
        "config_key": "session_ledger_retention_days",
    },
    {
        "file": STATE_DIR / "harness_events.jsonl",
        "date_field": "timestamp_utc",
        "config_key": "harness_events_retention_days",
    },
    {
        "file": Path(".ai-review-log.jsonl"),
        "date_field": "timestamp",
        "config_key": "review_log_retention_days",
    },
]


def _load_retention_config() -> dict[str, int]:
    defaults = {
        "session_ledger_retention_days": 90,
        "harness_events_retention_days": 365,
        "review_log_retention_days": 90,
        "dream_proposals_reviewed_retention_days": 365,
    }
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        user = cfg.get("memory", {}).get("retention", {})
        return {**defaults, **{k: int(v) for k, v in user.items() if k in defaults}}
    except Exception:
        return defaults


def _parse_date(raw: str) -> datetime | None:
    """Parse ISO-ish date strings tolerantly; return None if unparseable."""
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(raw[:26], fmt)
        except ValueError:
            continue
    return None


def _archive_path(stem: str, month_str: str) -> Path:
    """Return archive file path for a given stem and YYYY-MM month string."""
    return ARCHIVE_DIR / f"{stem}_archive_{month_str}.jsonl"


def process_target(
    file: Path,
    date_field: str,
    retention_days: int,
    dry_run: bool,
) -> tuple[int, int]:
    """
    Archive entries older than retention_days from file.

    Returns (kept, archived) counts.
    """
    if not file.exists():
        return 0, 0

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=retention_days)
    kept: list[str] = []
    to_archive: dict[str, list[str]] = {}  # month_str → lines

    for raw_line in file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue

        raw_date = record.get(date_field, "")
        dt = _parse_date(str(raw_date)) if raw_date else None

        if dt is None or dt >= cutoff:
            kept.append(line)
        else:
            month_str = dt.strftime("%Y-%m")
            to_archive.setdefault(month_str, []).append(line)

    archived_count = sum(len(v) for v in to_archive.values())

    if dry_run:
        for month_str, lines in sorted(to_archive.items()):
            dest = _archive_path(file.stem, month_str)
            print(f"  [DRY-RUN] would archive {len(lines)} entries → {dest}")
        return len(kept), archived_count

    # Write archives
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for month_str, lines in to_archive.items():
        dest = _archive_path(file.stem, month_str)
        with open(dest, "a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

    # Rewrite source with kept entries only
    with open(file, "w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")

    return len(kept), archived_count


def process_dream_proposals(retention_days: int, dry_run: bool) -> tuple[int, int]:
    """
    Archive __reviewed.md dream proposals older than retention_days.

    Returns (kept, archived) counts.
    """
    proposals_dir = Path(".agent/state/dream_proposals")
    if not proposals_dir.exists():
        return 0, 0

    archive_dir = proposals_dir / "archive"

    # We want to be timezone offset naive
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=retention_days)
    kept = 0
    archived = 0

    # Iterate over all files in the proposals directory
    for item in proposals_dir.iterdir():
        if not item.is_file() or not item.name.endswith("__reviewed.md"):
            continue

        # Determine age using file modification time
        try:
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
        except Exception:
            kept += 1
            continue

        if mtime >= cutoff:
            kept += 1
        else:
            if dry_run:
                print(
                    f"  [DRY-RUN] would archive proposal card {item.name} → {archive_dir / item.name}"
                )
            else:
                archive_dir.mkdir(parents=True, exist_ok=True)
                try:
                    # Move the file
                    dest_file = archive_dir / item.name
                    # If destination file already exists, remove it first to ensure overwrite parity
                    if dest_file.exists():
                        dest_file.unlink()
                    item.rename(dest_file)
                except Exception as e:
                    print(f"  [ERROR] Failed to archive {item.name}: {e}")
                    kept += 1
                    continue
            archived += 1

    return kept, archived


def main() -> None:
    parser = argparse.ArgumentParser(description="Harness state retention cleanup")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be archived without moving anything",
    )
    args = parser.parse_args()

    cfg = _load_retention_config()
    mode = "[DRY-RUN] " if args.dry_run else ""
    print(f"{mode}Retention cleanup starting...")

    total_kept = total_archived = 0
    for target in _TARGETS:
        days = cfg[target["config_key"]]
        kept, archived = process_target(
            file=target["file"],
            date_field=target["date_field"],
            retention_days=days,
            dry_run=args.dry_run,
        )
        if kept + archived > 0 or target["file"].exists():
            print(
                f"  {target['file'].name}: {kept} kept, {archived} archived "
                f"(threshold: {days}d)"
            )
        total_kept += kept
        total_archived += archived

    # Process dream proposals retention
    dream_days = cfg["dream_proposals_reviewed_retention_days"]
    dp_kept, dp_archived = process_dream_proposals(
        retention_days=dream_days,
        dry_run=args.dry_run,
    )
    if dp_kept + dp_archived > 0:
        print(
            f"  dream_proposals: {dp_kept} kept, {dp_archived} archived "
            f"(threshold: {dream_days}d)"
        )
    total_kept += dp_kept
    total_archived += dp_archived

    if total_archived == 0:
        print(f"{mode}Nothing to archive -- all entries within retention windows.")
    else:
        archive_note = "would archive" if args.dry_run else "archived"
        print(
            f"{mode}Done - {archive_note} {total_archived} entries, {total_kept} retained."
        )


if __name__ == "__main__":
    main()
