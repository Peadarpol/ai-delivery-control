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

    args = parser.parse_args()

    # Determine project root
    raw_root = args.project_root or os.getcwd()
    target_root = Path(raw_root).resolve()

    # Load boundaries
    config_path = target_root / ".agent" / "config.yaml"
    if not config_path.exists():
        print("no architecture.layers declared; nothing to reconcile")
        sys.exit(0)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error reading configuration: {e}")
        sys.exit(0)

    architecture = config.get("architecture", {})
    layers_list = architecture.get("layers", []) if isinstance(architecture, dict) else []
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

    # Prepare markdown content
    iso_now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    window_str = f"{args.window} commits" if args.window != 10000000 else "full history"
    layer_names_str = ", ".join(sorted(layers.keys()))

    report_lines = [
        "# Co-Change Reconciliation Report",
        "",
        f"**Generated**: {iso_now}",
        f"**Target**: {target_root.as_posix()}",
        f"**Window**: {window_str}  **Min-commits gate**: {args.min_commits}  **Prob floor**: {args.prob_floor}",
        f"**Boundaries**: {len(layers)} declared ({layer_names_str})",
        "",
        f"## Undeclared boundary-crossing co-change ({len(crossings)} pairs)",
        ""
    ]

    if crossings:
        report_lines.append(
            "Ranked by co-change probability. These file pairs cross an architectural boundary and "
            "co-change often enough to suggest emergent coupling that has not been deliberately declared."
        )
        report_lines.append("")
        report_lines.append(
            "| Rank | File A | Boundary A | File B | Boundary B | Co-changes | P(max) |"
        )
        report_lines.append(
            "|------|--------|-----------|--------|-----------|-----------|--------|"
        )
        for idx, c in enumerate(crossings, start=1):
            report_lines.append(
                f"| {idx} | {c['file_a']} | {c['boundary_a']} | {c['file_b']} | {c['boundary_b']} | {c['freq']} | {c['p_max']:.2f} |"
            )
    else:
        report_lines.append(
            "No boundary-crossing co-change pairs were found exceeding the minimum commit threshold."
        )

    report_lines.append("")
    report_lines.append("## Notes")
    report_lines.append(
        "- This is diagnostic output, not a verdict. Each crossing may be legitimate (a deliberate, "
        "acceptable coupling) or a signal to investigate. No CDR ledger exists yet, so ALL crossings "
        "above the gate are listed."
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
