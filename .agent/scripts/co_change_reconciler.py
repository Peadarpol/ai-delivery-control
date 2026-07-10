#!/usr/bin/env python3
"""
co_change_reconciler.py — CLI to reconcile architectural boundaries against historical co-changes.
"""

import argparse
import datetime
import os
import sys
from pathlib import Path
import yaml

# Setup imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR))

# Find default project root (traverse upwards until .git is found)
def _find_project_root() -> Path:
    curr = Path(__file__).resolve().parent
    for _ in range(10):
        if (curr / ".git").exists():
            return curr
        curr = curr.parent
    return Path(__file__).resolve().parent.parent

PROJECT_ROOT = _find_project_root()

# Import co_change_core logic
try:
    from co_change_core import get_git_co_changes
except ImportError:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))
    from co_change_core import get_git_co_changes

try:
    from cdr_ledger_validate import load_ledger
except ImportError:
    if str(PROJECT_ROOT / ".agent" / "scripts") not in sys.path:
        sys.path.append(str(PROJECT_ROOT / ".agent" / "scripts"))
    from cdr_ledger_validate import load_ledger

def boundary_of(file_path: str, layers: dict[str, str]) -> str | None:
    """Resolve file_path to its boundary layer name. Longest prefix wins."""
    normalized_path = file_path.replace("\\", "/")
    matching = []
    for name, prefix in layers.items():
        lp = prefix.rstrip("/") + "/"
        if normalized_path.startswith(lp):
            matching.append((name, lp))
    if not matching:
        return None
    # Sort by longest prefix length descending
    matching.sort(key=lambda x: len(x[1]), reverse=True)
    return matching[0][0]


def main():
    # Fix: Ensure UTF-8 encoding for stdout/stderr on Windows
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Reconcile historical co-changes against declared architectural boundaries."
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Root path of the target repository (defaults to active repo)."
    )
    parser.add_argument(
        "--window",
        type=int,
        default=10000000,
        help="Number of recent commits to inspect (default: full history)."
    )
    parser.add_argument(
        "--prob-floor",
        type=float,
        default=0.05,
        help="Minimum co-change probability threshold (default: 0.05)."
    )
    parser.add_argument(
        "--min-commits",
        type=int,
        default=5,
        help="Minimum number of co-change commits required (default: 5)."
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Report file output path (default: .agent/state/co_change_reconciliation_report.md)."
    )
    parser.add_argument(
        "--escalation-freq-multiplier",
        type=float,
        default=1.5,
        help="Multiplier for co-change frequency escalation check (default: 1.5)."
    )
    parser.add_argument(
        "--escalation-prob-delta",
        type=float,
        default=0.15,
        help="Delta for probability escalation check (default: 0.15)."
    )

    args = parser.parse_args()

    # Determine project root
    raw_root = args.project_root or os.getcwd()
    target_root = Path(raw_root).resolve()

    # Load and validate the CDR decisions ledger
    ledger_path = target_root / ".agent" / "coupling_decisions.yaml"
    ledger_exists = ledger_path.exists()
    decisions = []

    if ledger_exists:
        try:
            ledger_data = load_ledger(ledger_path)
            decisions = ledger_data.get("decisions", [])
        except Exception as e:
            print(f"Error loading/validating ledger: {e}", file=sys.stderr)
            sys.exit(1)


    # Bootstrap harness_utils
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "scripts"))
    from harness_utils import get_harness_config

    config_path = target_root / ".agent" / "config.yaml"
    if not config_path.exists():
        print("no architecture.layers declared; nothing to reconcile")
        sys.exit(0)
        
    layers_list = get_harness_config("architecture", "layers", default=[], config_path=config_path)
    
    if not layers_list or not isinstance(layers_list, list):
        print("no architecture.layers declared; nothing to reconcile")
        sys.exit(0)

    layers = {}
    for layer in layers_list:
        if isinstance(layer, dict) and "name" in layer and "path" in layer:
            name = layer["name"]
            path_val = layer["path"]
            if path_val and not path_val.startswith("["):
                layers[name] = path_val

    if not layers:
        print("no architecture.layers declared; nothing to reconcile")
        sys.exit(0)

    # Determine report output path
    default_out = target_root / ".agent" / "state" / "co_change_reconciliation_report.md"
    report_path = Path(args.out).resolve() if args.out else default_out

    # Build boundary-derived file filter
    layer_prefixes = list(layers.values())
    file_filter = lambda f: f.endswith(".py") and any(
        f.replace("\\", "/").startswith(p.rstrip("/") + "/") for p in layer_prefixes
    )

    # Fetch git co-change data
    result = get_git_co_changes(
        commit_window=args.window,
        file_filter=file_filter,
        prob_floor=args.prob_floor,
        project_root=target_root,
        return_frequencies=True
    )

    # Handle git failure defensively
    if isinstance(result, tuple):
        co_changes, frequencies = result
    else:
        co_changes, frequencies = {}, {}

    if not co_changes or not frequencies:
        print("No co-change data found; nothing to reconcile")
        sys.exit(0)

    # Filter to boundary-crossing pairs
    crossings = []
    for pair, freq in frequencies.items():
        file_a, file_b = pair
        boundary_a = boundary_of(file_a, layers)
        boundary_b = boundary_of(file_b, layers)

        # Strict filter: both must be non-None and different (Clarification 1)
        if boundary_a is None or boundary_b is None or boundary_a == boundary_b:
            continue

        # Frequency gate
        if freq < args.min_commits:
            continue

        # Probabilities
        p_b_given_a = co_changes.get(file_a, {}).get(file_b, 0.0)
        p_a_given_b = co_changes.get(file_b, {}).get(file_a, 0.0)
        p_max = max(p_b_given_a, p_a_given_b)

        crossings.append({
            "file_a": file_a,
            "boundary_a": boundary_a,
            "file_b": file_b,
            "boundary_b": boundary_b,
            "freq": freq,
            "p_max": p_max
        })

    # Sort descending by max probability, then frequency, then file paths (for determinism)
    crossings.sort(key=lambda x: (-x["p_max"], -x["freq"], x["file_a"], x["file_b"]))

    undeclared_crossings = []
    escalated_crossings = []
    tolerated_crossings = []
    accepted_crossings = []
    ambiguous_crossings = []

    for c in crossings:
        file_a = c["file_a"]
        file_b = c["file_b"]
        freq = c["freq"]
        p_max = c["p_max"]

        # Find matching decisions
        matched_entries = []
        for dec in decisions:
            scope = dec.get("scope")
            if scope == "pair":
                dec_files = dec.get("files", [])
                if len(dec_files) == 2:
                    if {dec_files[0], dec_files[1]} == {file_a, file_b}:
                        matched_entries.append(dec)
            elif scope == "file":
                dec_file = dec.get("file")
                if dec_file == file_a or dec_file == file_b:
                    matched_entries.append(dec)

        # Classification
        if len(matched_entries) > 1:
            c["matched_ids"] = ", ".join(sorted([d.get("id", "") for d in matched_entries]))
            ambiguous_crossings.append(c)
        elif len(matched_entries) == 1:
            entry = matched_entries[0]
            status = entry.get("status")
            cdr_id = entry.get("id", "")

            if status == "resolved":
                c["notes"] = "⚠ RESOLVED-REGRESSION"
                c["cdr_id"] = cdr_id
                undeclared_crossings.append(c)
            elif status in ("accepted", "tolerated"):
                scope = entry.get("scope")
                is_escalated = False

                if scope == "pair":
                    observed = entry.get("observed", {})
                    obs_co = observed.get("co_changes", 0)
                    obs_p = observed.get("p_max", 0.0)

                    multiplier = args.escalation_freq_multiplier
                    delta = args.escalation_prob_delta

                    is_escalated = (freq >= obs_co * multiplier) or (p_max >= obs_p + delta)

                    c["cdr_id"] = cdr_id
                    c["matched_status"] = status
                    c["observed_str"] = f"{obs_co} ({obs_p:.2f})"
                    c["current_str"] = f"{freq} ({p_max:.2f})"

                    freq_diff = freq - obs_co
                    p_max_diff = p_max - obs_p
                    freq_sign = "+" if freq_diff >= 0 else ""
                    p_sign = "+" if p_max_diff >= 0 else ""
                    c["delta_str"] = f"{freq_sign}{freq_diff} ({p_sign}{p_max_diff:.2f})"

                if is_escalated:
                    escalated_crossings.append(c)
                else:
                    c["cdr_id"] = cdr_id
                    c["matched_status"] = status
                    if status == "accepted":
                        c["archetype"] = entry.get("archetype", "")
                        accepted_crossings.append(c)
                    elif status == "tolerated":
                        c["reason"] = entry.get("reason", "")
                        c["note"] = entry.get("note", "") or "-"
                        tolerated_crossings.append(c)
        else:
            c["notes"] = "-"
            undeclared_crossings.append(c)

    # Prepare markdown content
    iso_now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    window_str = f"{args.window} commits" if args.window != 10000000 else "full history"
    ledger_display_path = ledger_path.as_posix() if ledger_exists else "none found"

    report_lines = [
        "# Co-Change Reconciliation Report",
        "",
        f"**Generated**: {iso_now}  **Ledger**: {ledger_display_path}",
        f"**Target**: {target_root.as_posix()}  **Window / gate / floor**: {window_str} / {args.min_commits} / {args.prob_floor}",
        "",
        f"## 1. Undeclared boundary-crossing co-change ({len(undeclared_crossings)})",
        ""
    ]

    if undeclared_crossings:
        report_lines.append(
            "Ranked by co-change probability. These file pairs cross an architectural boundary and "
            "co-change often enough to suggest emergent coupling that has not been deliberately declared."
        )
        report_lines.append("")
        report_lines.append(
            "| Rank | File A | Boundary A | File B | Boundary B | Co-changes | P(max) | Notes |"
        )
        report_lines.append(
            "|------|--------|-----------|--------|-----------|-----------|--------|-------|"
        )
        for idx, c in enumerate(undeclared_crossings, start=1):
            report_lines.append(
                f"| {idx} | {c['file_a']} | {c['boundary_a']} | {c['file_b']} | {c['boundary_b']} | {c['freq']} | {c['p_max']:.2f} | {c.get('notes', '-')} |"
            )
    else:
        report_lines.append(
            "No boundary-crossing co-change pairs were found exceeding the minimum commit threshold."
        )
    report_lines.append("")

    report_lines.append(f"## 2. Escalated (sanctioned couplings that have gotten worse) ({len(escalated_crossings)})")
    report_lines.append("")
    if escalated_crossings:
        report_lines.append(
            "| Rank | File A | File B | CDR ID | Status | Observed (at decision) | Current | Δ |"
        )
        report_lines.append(
            "|------|--------|--------|--------|--------|------------------------|---------|---|"
        )
        for idx, c in enumerate(escalated_crossings, start=1):
            report_lines.append(
                f"| {idx} | {c['file_a']} | {c['file_b']} | {c['cdr_id']} | {c['matched_status']} | {c['observed_str']} | {c['current_str']} | {c['delta_str']} |"
            )
    else:
        report_lines.append("No sanctioned coupling metrics have exceeded their escalation thresholds.")
    report_lines.append("")

    report_lines.append(f"## 3. Tolerated — known coupling debt ({len(tolerated_crossings)})")
    report_lines.append("")
    if tolerated_crossings:
        report_lines.append(
            "| File A | File B | CDR ID | Reason | Note |"
        )
        report_lines.append(
            "|--------|--------|--------|--------|------|"
        )
        for c in tolerated_crossings:
            report_lines.append(
                f"| {c['file_a']} | {c['file_b']} | {c['cdr_id']} | {c['reason']} | {c['note']} |"
            )
    else:
        report_lines.append("No tolerated coupling debt currently registered.")
    report_lines.append("")

    report_lines.append(f"## 4. Accepted — sanctioned, informational ({len(accepted_crossings)})")
    report_lines.append("")
    if accepted_crossings:
        report_lines.append(
            "| File A | File B | CDR ID | Archetype |"
        )
        report_lines.append(
            "|--------|--------|--------|-----------|"
        )
        for c in accepted_crossings:
            report_lines.append(
                f"| {c['file_a']} | {c['file_b']} | {c['cdr_id']} | {c['archetype']} |"
            )
    else:
        report_lines.append("No accepted couplings currently registered.")
    report_lines.append("")

    if ambiguous_crossings:
        report_lines.append(f"## Ambiguous matches (data integrity — should normally be empty)")
        report_lines.append("")
        report_lines.append(
            "| File A | File B | Matched IDs |"
        )
        report_lines.append(
            "|--------|--------|-------------|"
        )
        for c in ambiguous_crossings:
            report_lines.append(
                f"| {c['file_a']} | {c['file_b']} | {c['matched_ids']} |"
            )
        report_lines.append("")

    report_lines.append("## Notes")
    if not ledger_exists:
        report_lines.append("- no CDR ledger found — all crossings shown as undeclared")
    else:
        report_lines.append(
            f"- Checked against CDR ledger at {ledger_display_path} containing {len(decisions)} decisions."
        )
    report_lines.append(
        "- This is diagnostic output, not a verdict. Each crossing may be legitimate (a deliberate, "
        "acceptable coupling) or a signal to investigate."
    )
    report_lines.append(
        "- To evaluate a crossing, apply the strength/distance/volatility lens (governance.md §8)."
    )
    report_lines.append("")

    # Ensure out directory exists
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Reconciliation complete: {len(crossings)} crossings found. Report written to {report_path.as_posix()}")

if __name__ == "__main__":
    main()
