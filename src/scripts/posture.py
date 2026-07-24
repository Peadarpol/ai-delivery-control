#!/usr/bin/env python3
"""
src/scripts/posture.py — Gate Enforcement Posture Engine (T1-G-18)

Single source of truth for gate enforcement disposition logic across:
- pre-commit review gate (ai_review.py)
- architectural checks gate (architecture_checks.py)

Supported Postures:
- strict   : (Default) All FAIL findings block commit execution.
- ratchet  : FAIL findings block in changed code; pre-existing findings in .agent/baseline.json
             are grandfathered as advisory until the file is touched.
- observe  : Assessment mode. All non-invariant findings disposition to ADVISORY.
             Requires valid observe_expires ISO date string; past expiry resolves to ratchet.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Import harness utilities
def _find_project_root() -> Path:
    try:
        import subprocess
        res = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        if res.returncode == 0 and res.stdout.strip():
            return Path(res.stdout.strip())
    except Exception:
        pass
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".git").exists() or (parent / ".agent").exists():
            return parent
    return p.parents[2] if len(p.parents) > 2 else p.parent

PROJECT_ROOT = _find_project_root()
_src_scripts = PROJECT_ROOT / "src" / "scripts"
if _src_scripts.exists() and str(_src_scripts) not in sys.path:
    sys.path.insert(0, str(_src_scripts))

try:
    from harness_utils import get_harness_config, log_harness_event
except ImportError:
    def get_harness_config(section: str, key: str | None = None, default: Any = None) -> Any:
        return default
    def log_harness_event(evt: dict) -> None:
        pass


class Outcome(str, Enum):
    BLOCK = "BLOCK"
    ADVISORY = "ADVISORY"
    GRANDFATHERED = "GRANDFATHERED"


@dataclass
class Disposition:
    outcome: Outcome
    chain: List[str] = field(default_factory=list)
    invariant_pinned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "chain": self.chain,
            "invariant_pinned": self.invariant_pinned,
        }


# ── Invariant Floor Registry ──────────────────────────────────────────────────
# Rules and capabilities pinned as invariant floors cannot be downgraded by any
# posture, baseline, or rule override.
# Diff-level security capabilities (RBAC, MASS_ASSIGNMENT, etc.) are not yet pinned.
# Decision deferred to Phase P3, when ai_review.py's capability disposition wiring
# exists and the brownfield-ratchet interaction can be tested end-to-end rather than
# decided in isolation.
INVARIANT_FLOOR_REGISTRY: Set[str] = {
    # H-series session-level agent conduct rules (AGENTS.md §4.1)
    "H-01", "H-02", "H-03", "H-04", "H-05", "H-06", "H-07", "H-08", "H-09",
    "H_SERIES",
}


def is_invariant_pinned(rule_name: str) -> bool:
    """Return True if rule_name is pinned by the invariant floor."""
    if not rule_name:
        return False
    rule_upper = rule_name.upper().strip()
    return rule_upper in INVARIANT_FLOOR_REGISTRY


def load_enforcement_config(project_root: Path | None = None) -> Dict[str, Any]:
    """Load and validate enforcement posture configuration from .agent/config.yaml."""
    root = project_root or PROJECT_ROOT
    config_path = root / ".agent" / "config.yaml"

    default_config = {
        "posture": "strict",
        "observe_expires": None,
        "rule_overrides": {},
        "effective_posture": "strict",
        "expired": False,
    }

    if not config_path.exists():
        return default_config

    try:
        enforcement = get_harness_config("enforcement", default={}, config_path=config_path)
        if not isinstance(enforcement, dict):
            enforcement = {}

        posture = str(enforcement.get("posture", "strict")).lower().strip()
        observe_expires_str = enforcement.get("observe_expires")
        rule_overrides = enforcement.get("rule_overrides", {})
        if not isinstance(rule_overrides, dict):
            rule_overrides = {}

        # Outer loop compatibility matrix check (§5.8)
        outer_loop = get_harness_config("outer_loop", default={}, config_path=config_path)
        outer_mode = str(outer_loop.get("mode", "")).lower().strip() if isinstance(outer_loop, dict) else ""
        if outer_mode == "contractual" and posture in ("ratchet", "observe"):
            print("⚠️  [POSTURE ERROR] Invalid config: outer_loop.mode 'contractual' is incompatible with relaxed posture.")
            print(f"    Fallback to 'strict' posture active.")
            log_harness_event({
                "event_type": "invalid_posture_config",
                "severity": "WARNING",
                "payload": {"reason": "contractual mode incompatible with relaxed posture", "configured_posture": posture}
            })
            posture = "strict"

        # Validate posture name
        if posture not in ("strict", "ratchet", "observe"):
            print(f"⚠️  [POSTURE WARNING] Unknown posture '{posture}'. Resolving to 'strict'.")
            posture = "strict"

        effective_posture = posture
        expired = False

        if posture == "observe":
            if not observe_expires_str:
                print("⚠️  [POSTURE EXPIRED] 'observe' posture missing required observe_expires date. Resolved to 'ratchet'.")
                print("    👉 Action: Run 'python .agent/scripts/baseline.py init' or update observe_expires in .agent/config.yaml.")
                effective_posture = "ratchet"
                expired = True
            else:
                try:
                    # Parse ISO 8601 date string
                    expires_dt = datetime.datetime.fromisoformat(str(observe_expires_str).replace("Z", "+00:00"))
                    if expires_dt.tzinfo is None:
                        expires_dt = expires_dt.replace(tzinfo=datetime.timezone.utc)
                    
                    now_utc = datetime.datetime.now(datetime.timezone.utc)
                    if now_utc > expires_dt:
                        date_fmt = expires_dt.strftime("%Y-%m-%d")
                        print(f"⚠️  [POSTURE EXPIRED] 'observe' posture expired on {date_fmt} UTC. Resolved to 'ratchet'.")
                        print("    👉 Action: Run 'python .agent/scripts/baseline.py init' or update observe_expires in .agent/config.yaml.")
                        effective_posture = "ratchet"
                        expired = True
                except Exception as e:
                    print(f"⚠️  [POSTURE EXPIRED] Invalid observe_expires date format ({e}). Resolved to 'ratchet'.")
                    effective_posture = "ratchet"
                    expired = True

        return {
            "posture": posture,
            "observe_expires": observe_expires_str,
            "rule_overrides": rule_overrides,
            "effective_posture": effective_posture,
            "expired": expired,
        }
    except Exception as e:
        print(f"⚠️  [POSTURE ERROR] Failed to parse posture config: {e}. Resolving to 'strict'.")
        return default_config


def load_baseline(project_root: Path | None = None) -> Dict[str, Any] | None:
    """Load and verify .agent/baseline.json manifest.
    
    Performs tamper detection: recomputes SHA-256 over entries using canonical JSON.
    If header.manifest_sha256 mismatches, emits BASELINE_TAMPER_SUSPECTED and treats baseline as absent.
    Also builds an in-memory hash index keyed by file path dict[str, list[dict]].
    """
    root = project_root or PROJECT_ROOT
    baseline_path = root / ".agent" / "baseline.json"
    if not baseline_path.exists():
        return None

    try:
        raw_text = baseline_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        header = data.get("header", {})
        entries = data.get("entries", [])

        stored_hash = header.get("manifest_sha256", "")
        canonical_bytes = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
        computed_hash = hashlib.sha256(canonical_bytes).hexdigest()

        if stored_hash != computed_hash:
            print("🚨 [POSTURE WARNING] BASELINE_TAMPER_SUSPECTED: manifest SHA-256 mismatch! Baseline ignored.")
            log_harness_event({
                "event_type": "baseline_tamper_suspected",
                "severity": "HIGH",
                "payload": {
                    "stored_hash": stored_hash,
                    "computed_hash": computed_hash,
                    "file": str(baseline_path),
                }
            })
            return None

        # Build in-memory hash index by file path (O(1) lookup)
        index: Dict[str, List[Dict[str, Any]]] = {}
        for entry in entries:
            f = entry.get("file", "").replace("\\", "/").strip()
            if f not in index:
                index[f] = []
            index[f].append(entry)

        data["_index"] = index
        return data
    except Exception as e:
        print(f"⚠️  [POSTURE ERROR] Failed to load baseline.json: {e}. Baseline ignored.")
        return None


def get_touched_files(project_root: Path | None = None) -> Tuple[Set[str], bool]:
    """Return set of touched files relative to HEAD, and boolean shallow_clone_skipped flag.
    
    Handles merge commits via HEAD^1. If shallow clone (--depth=1) lacks parent history,
    skips lapse re-verification gracefully and logs SHALLOW_CLONE_LAPSE_SKIPPED.
    """
    root = project_root or PROJECT_ROOT
    try:
        import subprocess
        # Check if HEAD is a merge commit
        merge_check = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD^2"],
            capture_output=True, text=True, cwd=str(root)
        )
        is_merge = merge_check.returncode == 0

        diff_target = "HEAD^1" if is_merge else "HEAD"

        res = subprocess.run(
            ["git", "diff", "--name-only", diff_target],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(root)
        )
        if res.returncode != 0:
            if is_merge:
                print("⚠️  [POSTURE ADVISORY] SHALLOW_CLONE_LAPSE_SKIPPED: Shallow clone lacks parent history for merge diff.")
                log_harness_event({
                    "event_type": "shallow_clone_lapse_skipped",
                    "severity": "INFO",
                    "payload": {"diff_target": diff_target}
                })
                return set(), True
            return set(), False

        files = {f.strip().replace("\\", "/") for f in res.stdout.splitlines() if f.strip()}
        return files, False
    except Exception:
        return set(), False


def disposition(
    rule: str,
    severity: str,
    file_path: str = "",
    line: int = 1,
    region_sha256: str | None = None,
    posture: str = "strict",
    baseline: Dict[str, Any] | None = None,
    rule_overrides: Dict[str, str] | None = None,
    touched_files: Set[str] | None = None,
) -> Disposition:
    """
    Determine disposition outcome (BLOCK | ADVISORY | GRANDFATHERED) for a finding.
    
    Order of Evaluation:
    1. Invariant Floor Check (pinned rules always BLOCK)
    2. Per-rule Config Overrides (block|warn|off, rejected on pinned rules)
    3. Posture Evaluation (strict vs observe vs ratchet baseline lookup)
    """
    chain: List[str] = [f"detection: rule={rule}, severity={severity}"]
    sev_upper = severity.upper().strip()
    rule_upper = rule.upper().strip()

    # 1. Invariant Floor Check (§5.5)
    if is_invariant_pinned(rule_upper):
        chain.append("invariant floor pinned: forced BLOCK")
        return Disposition(outcome=Outcome.BLOCK, chain=chain, invariant_pinned=True)

    # 2. Per-rule Config Overrides (§5.6)
    if rule_overrides and rule_upper in rule_overrides:
        override_val = str(rule_overrides[rule_upper]).lower().strip()
        if override_val == "block":
            chain.append(f"rule override '{rule_upper}: block' -> BLOCK")
            return Disposition(outcome=Outcome.BLOCK, chain=chain)
        elif override_val in ("warn", "off"):
            chain.append(f"rule override '{rule_upper}: {override_val}' -> ADVISORY")
            return Disposition(outcome=Outcome.ADVISORY, chain=chain)

    posture_lower = posture.lower().strip()

    # 3. Observe Posture (§5.1 & Scenario 5)
    if posture_lower == "observe":
        chain.append("observe posture: downgraded to ADVISORY")
        return Disposition(outcome=Outcome.ADVISORY, chain=chain)

    # 4. Non-FAIL findings under any posture disposition to ADVISORY
    if sev_upper != "FAIL":
        chain.append(f"severity {sev_upper} -> ADVISORY")
        return Disposition(outcome=Outcome.ADVISORY, chain=chain)

    # 5. Strict Posture (§5.1 & Scenario 1)
    if posture_lower == "strict":
        chain.append("strict posture + FAIL severity -> BLOCK")
        return Disposition(outcome=Outcome.BLOCK, chain=chain)

    # 6. Ratchet Posture (§5.2 & Scenario 2)
    if posture_lower == "ratchet":
        norm_path = file_path.replace("\\", "/").strip()
        
        # Check if file was touched in this commit
        if touched_files is not None and norm_path in touched_files:
            chain.append(f"ratchet posture: file '{norm_path}' was touched -> baseline lapsed, BLOCK")
            return Disposition(outcome=Outcome.BLOCK, chain=chain)

        # O(1) Index Lookup if available
        entries_to_check = []
        if baseline and "_index" in baseline and isinstance(baseline["_index"], dict):
            entries_to_check = baseline["_index"].get(norm_path, [])
        elif baseline and "entries" in baseline and isinstance(baseline["entries"], list):
            entries_to_check = [e for e in baseline["entries"] if str(e.get("file", "")).replace("\\", "/").strip() == norm_path]

        if entries_to_check:
            for entry in entries_to_check:
                entry_rule = str(entry.get("rule", "")).upper().strip()
                entry_hash = entry.get("region_sha256")

                if entry_rule == rule_upper:
                    if region_sha256 is not None and entry_hash is not None:
                        if region_sha256 == entry_hash:
                            chain.append("ratchet posture: matched baseline region hash -> GRANDFATHERED")
                            return Disposition(outcome=Outcome.GRANDFATHERED, chain=chain)
                        else:
                            chain.append("ratchet posture: region hash changed -> baseline lapsed, BLOCK")
                            return Disposition(outcome=Outcome.BLOCK, chain=chain)
                    else:
                        chain.append("ratchet posture: file untouched, entry present in baseline -> GRANDFATHERED")
                        return Disposition(outcome=Outcome.GRANDFATHERED, chain=chain)

        chain.append("ratchet posture: not found in baseline -> BLOCK")
        return Disposition(outcome=Outcome.BLOCK, chain=chain)

    # Fallback default: strict blocking
    chain.append(f"fallback default -> BLOCK")
    return Disposition(outcome=Outcome.BLOCK, chain=chain)
