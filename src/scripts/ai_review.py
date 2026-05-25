#!/usr/bin/env python3
"""
AI Adversarial Review Gate
Pre-commit hook that calls Claude Sonnet to review staged changes.

Design: Soft gate with friction
  - PASS: commit proceeds silently
  - WARN: commit proceeds, feedback printed
  - FAIL: commit blocked, override with SKIP_AI_REVIEW=1

Usage:
  Called automatically by .pre-commit-config.yaml as the final hook.
  Reads staged diff from stdin, commit message from argv.

Requires:
  ANTHROPIC_API_KEY environment variable set.
"""

from __future__ import annotations

import datetime
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError


def _setup_sys_path():
    """Route sys.path to allow imports from senior-architect and agent scripts."""
    skills_path = str(
        PROJECT_ROOT / ".agent" / "skills" / "senior-architect" / "scripts"
    )
    scripts_path = str(PROJECT_ROOT / ".agent" / "scripts")
    if skills_path not in sys.path:
        sys.path.insert(0, skills_path)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)


# Fix: Ensure UTF-8 encoding for stdout/stderr on Windows to prevent UnicodeEncodeError with emojis
if sys.platform == "win32" and "pytest" not in sys.modules:
    import io

    if (
        hasattr(sys.stdout, "buffer")
        and getattr(sys.stdout, "encoding", "").lower() != "utf-8"
    ):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if (
        hasattr(sys.stderr, "buffer")
        and getattr(sys.stderr, "encoding", "").lower() != "utf-8"
    ):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def _safe_symbol(emoji: str, fallback: str) -> str:
    """Return emoji if stdout supports UTF-8, else ASCII fallback."""
    try:
        emoji.encode(sys.stdout.encoding or "utf-8")
        return emoji
    except (UnicodeEncodeError, AttributeError):
        return fallback


SYMBOL_ACTIVE = _safe_symbol("⚡", "[ACTIVE]")
SYMBOL_REVIEW = _safe_symbol("🔍", "[REVIEW]")
SYMBOL_SHIELD = _safe_symbol("🛡️", "[GUARD]")


def _get_active_session_id() -> str | None:
    session_file = PROJECT_ROOT / ".agent" / "state" / "session.json"
    if session_file.exists():
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                return json.load(f).get("session_id")
        except Exception:
            pass
    return None


def _load_token_ratios() -> Dict[str, float]:
    """Load char_to_token_ratio from .agent/config.yaml.

    Defaults to review=4.0, budget=3.5.
    """
    ratios = {"review": 4.0, "budget": 3.5}
    config_path = PROJECT_ROOT / ".agent" / "config.yaml"
    if not config_path.exists():
        return ratios

    try:
        content = config_path.read_text(encoding="utf-8")
        in_token_tracking = False
        in_ratios = False
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped == "token_tracking:":
                in_token_tracking = True
                continue

            if in_token_tracking:
                indent = len(line) - len(line.lstrip())
                if indent == 0:
                    in_token_tracking = False
                    in_ratios = False
                    continue

                if stripped == "char_to_token_ratio:":
                    in_ratios = True
                    continue

                if in_ratios:
                    if indent <= 2 and stripped != "char_to_token_ratio:":
                        in_ratios = False
                        continue
                    if ":" in stripped:
                        key_part, val_part = stripped.split(":", 1)
                        key = key_part.strip().strip("\"'")
                        val = val_part.split("#", 1)[0].strip()
                        if key in ratios:
                            try:
                                ratios[key] = float(val)
                            except ValueError:
                                pass
    except Exception:
        pass
    return ratios


def _load_branch_isolation_config() -> Tuple[List[str], List[str]]:
    """Load model_file_patterns and base_classes from .agent/config.yaml."""
    patterns = []
    base_classes = []
    config_path = PROJECT_ROOT / ".agent" / "config.yaml"
    if not config_path.exists():
        return ["src/**/models.py", "src/**/model.py"], ["BranchAwareMixin", "BranchIsolatedMixin"]

    try:
        content = config_path.read_text(encoding="utf-8")
        in_branch_isolation = False
        
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped == "branch_isolation:":
                in_branch_isolation = True
                continue

            if in_branch_isolation:
                indent = len(line) - len(line.lstrip())
                if indent == 0:
                    in_branch_isolation = False
                    continue

                if stripped.startswith("model_file_patterns:"):
                    if "[" in stripped:
                        lst_str = stripped.split("[", 1)[1].split("]", 1)[0]
                        patterns = [p.strip().strip("\"'") for p in lst_str.split(",") if p.strip()]
                elif stripped.startswith("base_classes:"):
                    if "[" in stripped:
                        lst_str = stripped.split("[", 1)[1].split("]", 1)[0]
                        base_classes = [b.strip().strip("\"'") for b in lst_str.split(",") if b.strip()]
    except Exception:
        pass

    if not patterns:
        patterns = ["src/**/models.py", "src/**/model.py"]
    if not base_classes:
        base_classes = ["BranchAwareMixin", "BranchIsolatedMixin"]

    return patterns, base_classes


def _ensure_and_load_model_roster() -> Dict[str, Any]:
    """Verify roster cache and compile/regenerate if model files changed or if missing."""
    roster_path = PROJECT_ROOT / ".agent" / "wiki" / "branch_isolation_roster.json"
    patterns, base_classes = _load_branch_isolation_config()

    recompile = False
    if not roster_path.exists():
        recompile = True
    else:
        try:
            roster_mtime = roster_path.stat().st_mtime
            import glob
            for pat in patterns:
                search_pat = str(PROJECT_ROOT / pat)
                for match in glob.glob(search_pat, recursive=True):
                    if os.path.isfile(match) and os.path.getmtime(match) > roster_mtime:
                        recompile = True
                        break
                if recompile:
                    break
        except Exception:
            recompile = True

    if recompile:
        try:
            _setup_sys_path()
            from roster_builder import build_branch_isolation_roster
            roster = build_branch_isolation_roster(patterns, base_classes, PROJECT_ROOT)
            roster_path.parent.mkdir(parents=True, exist_ok=True)
            with open(roster_path, "w", encoding="utf-8") as f:
                json.dump(roster, f, indent=4)
        except Exception as e:
            print(f"⚠️  [ROSTER] Roster recompilation failed: {e}")
            if roster_path.exists():
                try:
                    with open(roster_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            return {}
    else:
        try:
            with open(roster_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    if roster_path.exists():
        try:
            with open(roster_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def verify_and_suppress_roster_issues(typed_verdict: ReviewVerdict, route_decision: RouteDecision) -> None:
    """Read roster and suppress false-positive BRANCH_ISOLATION warnings if confirmed in roster."""
    if not typed_verdict.issues:
        return

    roster = _ensure_and_load_model_roster()
    if not roster:
        return

    new_issues = []
    suppressed_any = False

    for issue in typed_verdict.issues:
        concern = issue.get("concern")
        desc = issue.get("description", "")
        
        suppressed = False
        if concern == "BRANCH_ISOLATION":
            for model_name, info in roster.items():
                if model_name in desc or model_name in issue.get("location", ""):
                    col = info.get("column", "branch_id")
                    fk = info.get("fk", "branches.id")
                    nullable = info.get("nullable", True)
                    
                    note = f"BRANCH_ISOLATION: {model_name} confirmed branch-isolated ({col}: FK\u2192{fk}, nullable={nullable} — compiled YYYY-MM-DD)"
                    print(f"✅ [ROSTER] Suppressed false-positive: {note}")
                    route_decision.policy_notes.append(f"✅ Suppressed: {note}")
                    suppressed = True
                    suppressed_any = True
                    break

        if not suppressed:
            new_issues.append(issue)

    if suppressed_any:
        typed_verdict.issues = new_issues
        high_issues = [i for i in new_issues if i.get("severity") == "HIGH"]
        med_issues = [i for i in new_issues if i.get("severity") == "MEDIUM"]
        
        if not high_issues:
            typed_verdict.blocking_concern = None
            if med_issues:
                typed_verdict.verdict = "WARN"
            else:
                typed_verdict.verdict = "PASS"


# ── Config ────────────────────────────────────────────────────────────────────

MODEL = os.environ.get("AI_REVIEW_MODEL", "claude-sonnet-4-20250514")
TIMEOUT_SECONDS = int(os.environ.get("AI_REVIEW_TIMEOUT", "45"))
MAX_DIFF_CHARS = (
    200_000  # Skip review above this threshold (Sonnet 4.6 has 200K context)
)
MAX_DIFF_LINES = 5_000  # Skip review entirely above this threshold
DEFAULT_PASSES = int(os.environ.get("AI_REVIEW_PASSES", "1"))
SHUFFLE_HUNKS = os.environ.get("AI_REVIEW_SHUFFLE", "1") == "1"

SCRIPT_DIR = Path(__file__).resolve().parent


# ── Pydantic Models (T1-G-03) ─────────────────────────────────────────────────


class RouteDecision(BaseModel):
    """Stub for T1-G-01 capability routing — forward-compatibility only."""

    selected_tools: List[str] = Field(default_factory=list)
    review_intensity: Literal["standard", "elevated", "critical"] = "standard"
    rationale: str = ""
    policy_notes: List[str] = Field(default_factory=list)


# ── ADR Domain Mapping (BUG-05) ───────────────────────────────────────────────

UNIVERSAL_ADR_DOMAIN_TO_CAPABILITY = {
    "branch_isolation": "BRANCH_ISOLATION",
    "remove_uow_autocommit": "TRANSACTIONAL_INTEGRITY",
    "clean_architecture": "CLEAN_ARCH",
    "authentication": "RBAC",
    "schema_hardening": "MASS_ASSIGNMENT",
    "uow_pattern": "TRANSACTIONAL_INTEGRITY",
}


def _load_adr_capability_mappings() -> Dict[str, str]:
    """Read adr_capability_mappings from .agent/config.yaml.

    Uses simple indentation and prefix matching to avoid a YAML dependency.
    """
    mappings = {}
    config_path = PROJECT_ROOT / ".agent" / "config.yaml"
    if not config_path.exists():
        return mappings

    try:
        content = config_path.read_text(encoding="utf-8")
        in_arch_checks = False
        in_mappings = False
        
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
                
            # Detect section transitions
            if stripped == "architecture_checks:":
                in_arch_checks = True
                in_mappings = False
                continue
                
            if in_arch_checks:
                indent = len(line) - len(line.lstrip())
                
                if stripped == "adr_capability_mappings:":
                    in_mappings = True
                    continue
                    
                if in_mappings:
                    if ":" in stripped:
                        key_part, val_part = stripped.split(":", 1)
                        # Remove comment if any (e.g. key: value # comment)
                        val_part = val_part.split("#", 1)[0]
                        key = key_part.strip().strip("\"'")
                        val = val_part.strip().strip("\"'")
                        if key and val:
                            mappings[key] = val
                    else:
                        if indent == 0:
                            in_arch_checks = False
                            in_mappings = False
                else:
                    if indent == 0:
                        in_arch_checks = False
    except Exception:
        pass
        
    return mappings


# ── High-Risk Commit Classification (T1-L-08) ─────────────────────────────────

HIGH_RISK_PATTERNS = {
    "paths": [
        "*/migrations/*",
        "*/auth/*",
        "*/rbac/*", 
        "*/permissions/*",
        "*/security/*",
    ],
    "filenames": [
        "unit_of_work.py",
        "base_repository.py",
        "models.py",
    ],
    "adr_domains": [
        "branch_isolation",
        "authentication",
        "schema_hardening",
    ],
}


def _load_high_risk_patterns() -> Dict[str, List[str]]:
    """Load high_risk_patterns from .agent/config.yaml.

    Uses simple line parsing to avoid PyYAML dependency.
    """
    config_patterns = {"paths": [], "filenames": [], "adr_domains": []}
    config_path = PROJECT_ROOT / ".agent" / "config.yaml"
    if not config_path.exists():
        return config_patterns

    try:
        content = config_path.read_text(encoding="utf-8")
        in_arch_checks = False
        in_patterns = False
        current_list = None
        
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
                
            # Transition triggers
            if stripped == "architecture_checks:":
                in_arch_checks = True
                in_patterns = False
                continue
                
            if in_arch_checks:
                indent = len(line) - len(line.lstrip())
                if indent == 0:
                    in_arch_checks = False
                    in_patterns = False
                    continue
                    
                if stripped == "high_risk_patterns:":
                    in_patterns = True
                    continue
                    
                if in_patterns:
                    if indent <= 2:  # Exited high_risk_patterns block
                        if stripped != "high_risk_patterns:":
                            in_patterns = False
                            continue
                            
                    # Let's detect lists: paths:, filenames:, adr_domains:
                    if stripped in ("paths:", "filenames:", "adr_domains:"):
                        current_list = stripped[:-1]  # "paths", "filenames", or "adr_domains"
                        continue
                        
                    # Parse list items like `- "item"` or `- item`
                    if stripped.startswith("-") and current_list:
                        item = stripped[1:].strip().strip("\"'")
                        if item:
                            config_patterns[current_list].append(item)
    except Exception:
        pass
        
    return config_patterns


def classify_commit_risk(changed_files: List[str], adr_domains: List[str]) -> Tuple[bool, List[str]]:
    """Classify commit risk based on modified paths, filenames, and active ADR domains.

    Returns:
        (is_high_risk, matched_patterns)
    """
    import fnmatch
    
    cfg = _load_high_risk_patterns()
    
    paths = list(HIGH_RISK_PATTERNS["paths"]) + cfg.get("paths", [])
    filenames = list(HIGH_RISK_PATTERNS["filenames"]) + cfg.get("filenames", [])
    adr_domains_list = list(HIGH_RISK_PATTERNS["adr_domains"]) + cfg.get("adr_domains", [])
    
    matched = []
    
    # Normalize changed_files to forward slashes for path pattern matching
    normalized_files = [f.replace("\\", "/") for f in changed_files]
    
    for f in normalized_files:
        # Match paths
        for pat in paths:
            if fnmatch.fnmatch(f, pat):
                matched.append(f"path:{pat} (matches {f})")
                
        # Match filenames
        name = Path(f).name
        for fn in filenames:
            if name == fn:
                matched.append(f"filename:{fn} (matches {f})")
                
    # Match ADR domains
    normalized_adr = [d.strip().lower() for d in adr_domains]
    for adr in adr_domains_list:
        norm_adr = adr.strip().lower()
        if norm_adr in normalized_adr:
            matched.append(f"adr_domain:{adr}")
            
    return len(matched) > 0, matched


def log_harness_event(event_dict: Dict[str, Any]) -> None:
    """Log a harness event to .agent/state/harness_events.jsonl (T1-L-08)."""
    try:
        log_dir = PROJECT_ROOT / ".agent" / "state"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "harness_events.jsonl"
        
        session_id = None
        session_file = PROJECT_ROOT / ".agent" / "state" / "session.json"
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    session_id = json.load(f).get("session_id")
            except Exception:
                pass
                
        # Modern standard-compliant UTC datetime
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        
        record = {
            "schema_version": "1.0",
            "event_type": event_dict.get("event_type"),
            "timestamp_utc": now_utc,
            "session_id": session_id,
            "commit_sha": None,
            "agent": os.environ.get("AGENT_ID", "ai_review"),
            "severity": event_dict.get("severity", "INFO"),
            "payload": event_dict.get("payload", {}),
        }
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass  # Never block execution due to logging failures


def _handle_api_unavailable(reason: str, changed_files: List[str], active_domains: List[str]) -> int:
    """Handle API/provider unavailability with high-risk fail-closed enforcement (T1-L-08)."""
    is_high_risk, matched_patterns = classify_commit_risk(changed_files, active_domains)
    _persist_verdict(fail_open_reason=reason)
    
    if is_high_risk:
        print("[REVIEW] API unavailable + high-risk commit → FAIL CLOSED")
        print("[REVIEW] High-risk files detected — manual review required")
        print("[REVIEW] Override: SKIP_AI_REVIEW=1 SKIP_REASON='...'")
        
        log_harness_event({
            "event_type": "high_risk_gate_closed",
            "severity": "HIGH",
            "payload": {
                "reason": f"API unavailable on high-risk commit ({reason})",
                "high_risk_matches": matched_patterns,
                "override_available": "SKIP_AI_REVIEW=1 SKIP_REASON=..."
            }
        })
        sys.exit(1)  # Block the commit
    else:
        # Fail open — low-risk commit, proceed
        print(f"⚠️  AI review skipped (fail-open): {reason}")
        print("   Allowing commit. Review manually if this persists.")
        return 0


def build_route_decision(
    changed_files: List[str], diff_text: str, pagerank_scores: Dict[str, float]
) -> RouteDecision:
    """Populates the RouteDecision model based on path matching, ADRs, and PageRank."""
    selected_tools = []
    policy_notes = []

    # 1. Determine active capability tools by path and content matching
    changed_normalized = [f.replace("\\", "/") for f in changed_files]

    has_db_or_srv = any(
        "src/infrastructure/database/repositories/" in f
        or "src/application/services/" in f
        for f in changed_normalized
    )
    has_domain_or_models = any(
        "src/domain/schemas/" in f or "src/infrastructure/database/models.py" in f
        for f in changed_normalized
    )
    has_api = any("src/presentation/api/" in f for f in changed_normalized)
    has_migrations = any("migrations/versions/" in f for f in changed_normalized)
    has_clean_arch = any(
        f.startswith("src/domain/")
        or f.startswith("src/application/")
        or f.startswith("src/infrastructure/")
        for f in changed_normalized
    )

    # Content-based checks
    is_tx = has_db_or_srv or any(
        p in diff_text for p in ["UnitOfWork", "uow.", "self.uow", ".commit()"]
    )
    is_bi = has_db_or_srv or any(
        p in diff_text for p in ["_apply_branch_filter", "branch_id"]
    )
    is_ma = has_domain_or_models or any(
        p in diff_text for p in ["BaseModel", "model_config"]
    )
    is_rbac = has_api or any(
        p in diff_text for p in ["require_permission", "Role", "permission"]
    )
    is_mig = has_migrations or any(p in diff_text for p in ["alembic", "op.add_column"])
    is_ca = has_clean_arch

    # Scan for ADR domain triggers (from active_domains matching DOMAIN_REGISTRY keys)
    active_adr_domains = []
    try:
        from architecture_checks import extract_adr_annotations

        for f in changed_files:
            if Path(f).exists():
                for domain in extract_adr_annotations(f):
                    active_adr_domains.append(domain.lower())
    except Exception:
        pass

    if "branch_isolation" in active_adr_domains:
        is_bi = True
    if "multi_branch_schema" in active_adr_domains:
        is_bi = True
    if "transactional_integrity" in active_adr_domains:
        is_tx = True

    # Map triggers to selected_tools
    capabilities = {
        "TRANSACTIONAL_INTEGRITY": is_tx,
        "BRANCH_ISOLATION": is_bi,
        "MASS_ASSIGNMENT": is_ma,
        "RBAC": is_rbac,
        "MIGRATIONS": is_mig,
        "CLEAN_ARCH": is_ca,
    }

    # Enable capabilities based on ADR domains (BUG-05 - revised two-layer design)
    # Layer 1: Universal seeds
    adr_mappings = dict(UNIVERSAL_ADR_DOMAIN_TO_CAPABILITY)
    
    # Layer 2: Merge project-specific config mappings (wins on conflicts)
    try:
        project_mappings = _load_adr_capability_mappings()
        adr_mappings.update(project_mappings)
    except Exception:
        pass
        
    # Normalize keys/values and apply
    normalized_mappings = {k.strip().lower(): v.strip().upper() for k, v in adr_mappings.items()}
    
    for domain in active_adr_domains:
        norm = domain.strip().lower()
        if norm in normalized_mappings:
            cap_name = normalized_mappings[norm]
            if cap_name in capabilities:
                capabilities[cap_name] = True

    for cap_name, active in capabilities.items():
        if active:
            selected_tools.append(cap_name)
            policy_notes.append(f"{SYMBOL_ACTIVE} Enabled check: {cap_name}")
        else:
            policy_notes.append(
                f"{SYMBOL_SHIELD} Skipped check: {cap_name} (no matching path or ADR)"
            )

    # 2. Determine review intensity based on PageRank
    review_intensity = "standard"
    top_3_hits = []
    top_10_hits = []

    if pagerank_scores:
        sorted_files = sorted(
            pagerank_scores.keys(), key=lambda f: pagerank_scores[f], reverse=True
        )
        top_3 = sorted_files[:3]
        top_10 = sorted_files[:10]

        top_3_hits = [f for f in changed_normalized if f in top_3]
        top_10_hits = [f for f in changed_normalized if f in top_10]

        if top_3_hits:
            review_intensity = "critical"
        elif top_10_hits:
            review_intensity = "elevated"

    policy_notes.append(
        f"{SYMBOL_REVIEW} Review intensity: {review_intensity.upper()} "
        f"(PageRank metrics: critical hits = {len(top_3_hits)}, elevated hits = {len(top_10_hits)})"
    )

    # 3. Construct rationale
    rationale_parts = [f"Intensity set to {review_intensity}."]
    if top_3_hits:
        rationale_parts.append(
            f"Staged changes modify core Top 3 PageRank files: {', '.join(top_3_hits)}."
        )
    elif top_10_hits:
        rationale_parts.append(
            f"Staged changes modify high-priority Top 10 PageRank files: {', '.join(top_10_hits)}."
        )
    rationale_parts.append(
        f"Active capabilities: {', '.join(selected_tools) if selected_tools else 'None'}."
    )

    return RouteDecision(
        selected_tools=selected_tools,
        review_intensity=review_intensity,
        rationale=" ".join(rationale_parts),
        policy_notes=policy_notes,
    )


class ReviewVerdict(BaseModel):
    """Typed representation of an AI adversarial review outcome.

    All LLM responses are validated against this model at parse time.
    PASS_FAST verdicts are emitted by the pre-flight shortcut (T1-G-02)
    without any LLM call.
    """

    verdict: Literal["PASS", "WARN", "FAIL", "FAIL_OPEN", "PASS_FAST"]
    blocking_concern: Optional[str] = None
    concerns: List[str] = Field(default_factory=list)
    route_decision: Optional[RouteDecision] = None
    planner_note: Optional[str] = None
    fail_open_reason: Optional[str] = None
    model: str
    token_usage: Dict[str, int] = Field(default_factory=dict)
    verdict_tier: Literal["cloud", "local", "review", "budget", "preflight"] = "review"
    session_id: Optional[str] = None
    # Populated on FAIL and WARN verdicts only — the exact sections injected
    # (review_context section IDs, ADR domains, repo map token count).
    # Kept None for PASS_FAST to avoid log bloat.
    context_snapshot: Optional[str] = None
    # Backward-compat fields — protect existing log readers during transition
    intent_alignment: Optional[str] = None
    summary: Optional[str] = None
    issues: List[Dict[str, Any]] = Field(default_factory=list)


class PlanOutput(BaseModel):
    """Output of the pre-flight shortcut planner (T1-G-02)."""

    requires_review: bool
    direct_pass_allowed: bool
    planner_note: str


def _find_project_root() -> Path:
    """Find the git repository root (works regardless of where script lives)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except Exception:
        pass
    # Fallback: assume src/scripts/../../ = repo root
    return SCRIPT_DIR.parent.parent


PROJECT_ROOT = _find_project_root()
UNIVERSAL_CONTEXT_FILE = SCRIPT_DIR / "review_context_universal.md"
PROJECT_CONTEXT_FILE = SCRIPT_DIR / "review_context_project.md"
CONFIG_FILE = PROJECT_ROOT / ".ai-review-config.json"

# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior engineer performing an independent pre-commit review.
Your role is to identify genuine problems — bugs, security issues, and architectural
violations — with specificity and proportionality.

You will receive:
1. A git diff of staged changes
2. The commit message describing the stated intent
3. Project architecture guidelines (if available)

Your review must cover:
- INTENT ALIGNMENT: Does the code actually achieve what the commit message claims?
- CODE QUALITY: Bugs, security issues (injection, unvalidated input, exposed secrets),
  unhandled errors/edge cases, breaking changes to interfaces or contracts.
- ANTI-PATTERNS: Language-specific bad practices, dead code, stale comments left behind.
- TRANSACTIONAL INTEGRITY: In service methods, verify that flush()/commit() usage follows
  the Unit of Work pattern. Services MUST call uow.commit() explicitly inside a 'with self.uow:'
  block. Repositories must NEVER call commit().
- BRANCH ISOLATION: In repository query methods, verify that branch-scoped entities use
  _apply_branch_filter(stmt). The pattern 'if self.branch_id: stmt = stmt.where(...)' is a
  security bug.
- MASS ASSIGNMENT: Verify that new Pydantic input schemas set model_config = {"extra": "forbid"}.

Severity calibration (critical — follow precisely):
- HIGH: Actual bugs that would cause runtime failures, security vulnerabilities (injection,
  exposed secrets, auth bypass), data corruption or loss, broken contracts/interfaces, or
  stated intent not achieved. Only HIGH issues block a commit.
- MEDIUM: Quality concerns a senior engineer would flag in code review — missing error
  handling for likely error paths, untested critical paths, potential performance regressions.
  Informational; commit proceeds with warnings.
- LOW: Style, naming, minor refactoring suggestions. Informational only.

Proportionality rules:
- A correct implementation with only stylistic observations is PASS, not WARN.
- If the diff achieves its stated intent without bugs or security issues, PASS is the
  correct verdict. Do not manufacture issues to justify a FAIL or WARN.
- FAIL requires at least one HIGH finding with a specific file:line citation.
  Vague or speculative concerns must be downgraded to MEDIUM.

Concern Labels:
- BRANCH_ISOLATION
- TRANSACTIONAL_INTEGRITY
- MASS_ASSIGNMENT
- INTENT_MISMATCH
- SECURITY_VULNERABILITY
- CODE_QUALITY
- PERFORMANCE_REGRESSION

Verdict rules:
- FAIL if any HIGH severity issues exist (must have specific file:line citation)
- WARN if MEDIUM issues exist but no HIGH
- PASS if only LOW issues or none

Respond ONLY with valid JSON. No preamble, no markdown fences, no explanation outside the JSON.

{
  "verdict": "PASS or WARN or FAIL",
  "blocking_concern": "for FAIL: the single Concern Label that caused the block (e.g. BRANCH_ISOLATION); null for PASS or WARN",
  "intent_alignment": "one sentence: does the code achieve the stated intent?",
  "issues": [
    {
      "severity": "HIGH or MEDIUM or LOW",
      "concern": "one of the Concern Labels above",
      "location": "filename:line_range or general",
      "description": "specific description of the issue",
      "remediation": "briefly how to fix it"
    }
  ],
  "summary": "2-3 sentence overall assessment"
}"""

# ── Pre-flight Shortcut (T1-G-02) ────────────────────────────────────────────


# Comment markers across all project languages (Python, JS/TS, CSS, SQL, HTML).
# A false positive (wrongly treating as comment-only) is harmless: the worst
# outcome is an unnecessary full review. A false negative would skip a real
# code change — these markers are conservative enough to avoid that.
_COMMENT_PREFIXES = ("#", "//", "/*", "*", "-->", "<!--", '"""', "'''")


def check_preflight_shortcut(diff: str) -> PlanOutput:
    """Determine whether a staged diff can be short-circuited without an LLM call.

    Returns a PlanOutput indicating:
    - ``direct_pass_allowed=True``  → emit PASS_FAST, skip LLM entirely.
    - ``direct_pass_allowed=False`` → proceed to full adversarial review.
    """
    # 1. Extract changed filenames (git diff --cached --name-only is more reliable
    #    than parsing diff headers for renames and binary files).
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
        )
        filenames = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except Exception:
        # If subprocess fails, fall back to parsing diff headers.
        filenames = re.findall(r"^\+\+\+ b/(.+)$", diff, re.MULTILINE)

    if not filenames:
        return PlanOutput(
            requires_review=True,
            direct_pass_allowed=False,
            planner_note="Could not determine changed files; full review required.",
        )

    # 2. Documentation-only check.
    doc_extensions = {".md", ".rst", ".txt"}
    if all(Path(f).suffix.lower() in doc_extensions for f in filenames):
        return PlanOutput(
            requires_review=False,
            direct_pass_allowed=True,
            planner_note="Documentation-only change detected.",
        )

    # 3. Whitespace / comment-only check on the diff body.
    #    Only inspect added (+) and removed (-) lines; skip diff headers.
    changed_lines = [
        line[1:]  # Strip the leading +/- sigil
        for line in diff.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]

    if changed_lines and all(
        line.strip() == "" or line.strip().startswith(_COMMENT_PREFIXES)
        for line in changed_lines
    ):
        return PlanOutput(
            requires_review=False,
            direct_pass_allowed=True,
            planner_note="Whitespace or comment-only change detected.",
        )

    return PlanOutput(
        requires_review=True,
        direct_pass_allowed=False,
        planner_note="Staged changes contain code edits; full adversarial review required.",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def load_config() -> Dict[str, Any]:
    """Load optional .ai-review-config.json from project root."""
    if CONFIG_FILE.exists():
        try:
            from typing import cast

            return cast(
                Dict[str, Any], json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            )
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def get_adr_context(changed_files: list[str]) -> tuple[str, list[str], list[str]]:
    """
    Extracts, prioritizes, whitelists, and synthesizes active ADR wiki pages
    into a budget-compliant context (≤400 tokens) using the three-step token squeeze.

    Returns:
        tuple (adr_context_string, active_domains, policy_notes)
    """
    _setup_sys_path()
    try:
        from architecture_checks import extract_adr_annotations
        from repo_map import get_pagerank_scores
        from wiki_compile import DOMAIN_REGISTRY
    except ImportError:
        return "", [], []

    # 1. Compute PageRank scores
    try:
        pagerank_scores = get_pagerank_scores(changed_files)
    except Exception:
        pagerank_scores = {}

    # 2. Extract and whitelist annotations across all files
    domain_to_max_score = {}

    for path in Path("src").rglob("*.py"):
        filepath_str = str(path).replace("\\", "/")
        domains = extract_adr_annotations(str(path))
        for domain in domains:
            if domain not in DOMAIN_REGISTRY:
                continue

            score = pagerank_scores.get(filepath_str, 0.0)
            if domain not in domain_to_max_score or score > domain_to_max_score[domain]:
                domain_to_max_score[domain] = score

    if not domain_to_max_score:
        return "", [], []

    # Sort domains by priority score (highest first)
    sorted_domains = sorted(
        domain_to_max_score.keys(), key=lambda d: domain_to_max_score[d], reverse=True
    )

    # 3. Budget-Based Token Squeeze
    adr_parts = []
    active_domains = []
    suppressed_count = 0
    token_budget = 400
    current_tokens = 0

    for domain in sorted_domains:
        wiki_path = PROJECT_ROOT / ".agent" / "wiki" / f"{domain}.md"
        if not wiki_path.exists():
            continue

        try:
            content = wiki_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # Step 1: Strip headers/scaffolding
        clean_content = _strip_wiki_headers(content)

        est_tokens = len(clean_content) // 4

        # Step 2: Inject in priority order
        if current_tokens + est_tokens <= token_budget:
            adr_parts.append(f"### Domain: {domain}\n{clean_content}")
            current_tokens += est_tokens
            active_domains.append(domain)
        else:
            # Step 3: Track suppressed domain
            suppressed_count += 1

    policy_notes = []
    if suppressed_count > 0:
        note = f"{suppressed_count} ADR domain{'s' if suppressed_count > 1 else ''} suppressed (token budget) — see .agent/wiki/ for full context."
        policy_notes.append(note)

    adr_context_str = ""
    if adr_parts:
        adr_context_str = "\n\n".join(adr_parts)
        if policy_notes:
            adr_context_str += "\n\n**Policy Notes**:\n" + "\n".join(
                f"- {n}" for n in policy_notes
            )

    return adr_context_str, active_domains, policy_notes


def _strip_wiki_headers(content: str) -> str:
    """Strips wiki page scaffolding before injection."""
    lines = content.splitlines()
    clean_lines = []
    in_skipped_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Related Domains") or stripped.startswith(
            "**Related Domains**"
        ):
            in_skipped_section = True
            continue
        if stripped.startswith("## ") and in_skipped_section:
            in_skipped_section = False
        if in_skipped_section:
            continue
        if (
            stripped.startswith("# ")
            or stripped.startswith("**Compiled**")
            or stripped.startswith("**Sources**")
            or "→ Full source:" in stripped
        ):
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines).strip()


def load_review_context(diff: str = "") -> str:
    """
    Load project architecture guidelines for the review prompt.
    Loads universal context always, and project context if present.
    If a diff is provided, selectively injects relevant sections (PA-02).
    """
    if not UNIVERSAL_CONTEXT_FILE.exists():
        print(f"Error: Universal review context file is missing at {UNIVERSAL_CONTEXT_FILE}. Installation may be corrupt.", file=sys.stderr)
        sys.exit(1)

    # 1. Load Universal Context
    try:
        universal_content = UNIVERSAL_CONTEXT_FILE.read_text(encoding="utf-8")
        print(f"[REVIEW] Loaded universal context from {UNIVERSAL_CONTEXT_FILE.name}")
    except Exception as e:
        print(f"Error: Failed to read universal context file: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Load Project Context
    project_content = ""
    if PROJECT_CONTEXT_FILE.exists() and PROJECT_CONTEXT_FILE.is_file():
        try:
            project_content = PROJECT_CONTEXT_FILE.read_text(encoding="utf-8")
            print(f"[REVIEW] Loaded project context from {PROJECT_CONTEXT_FILE.name}")
        except Exception as e:
            print(f"Warning: Failed to read project context file: {e}", file=sys.stderr)
            pass
    else:
        print(f"[REVIEW] Project context absent — proceeding with universal guidelines only")

    # 3. Concatenate layers (project content after universal content)
    combined = universal_content
    if project_content.strip():
        combined += "\n\n" + project_content

    if not diff:
        return combined
    return _select_context_sections(diff, combined)


def _select_context_sections(diff: str, context_text: str) -> str:
    """
    Parses context_text for <!-- SECTION:id --> markers and returns only sections
    relevant to the staged diff (PA-02).
    """
    # 1. Map diff patterns to section IDs
    trigger_map = {
        "transactional_integrity": [
            "src/application/services/",
            "UnitOfWork",
            "uow.",
            "self.uow",
            ".commit()",
        ],
        "branch_isolation": [
            "src/infrastructure/database/",
            "Repository",
            "_apply_branch_filter",
            "branch_id",
        ],
        "mass_assignment": ["src/domain/schemas/", "BaseModel", "model_config"],
        "rbac": ["require_permission", "Role", "permission", "src/presentation/api/"],
        "migrations": ["migrations/versions/", "alembic", "op.add_column"],
        "clean_arch": ["src/domain/", "src/application/", "src/infrastructure/"],
    }

    # 2. Identify active sections
    active_sections = {"micro_checks"}  # Always include micro_checks
    for section_id, patterns in trigger_map.items():
        if any(p in diff for p in patterns):
            active_sections.add(section_id)

    # 3. Parse and filter the context document
    # Sections are delimited by <!-- SECTION:id --> ... ---
    # We keep the header (everything before the first ---) and active sections.
    parts = context_text.split("\n---\n")
    header = parts[0]
    filtered_sections = [header]

    for part in parts[1:]:
        # Extract section ID from marker
        match = re.search(r"<!-- SECTION:([\w_]+) -->", part)
        if match:
            section_id = match.group(1)
            if section_id in active_sections:
                filtered_sections.append(part)
        else:
            # If no marker, include it (e.g. general rules)
            filtered_sections.append(part)

    return "\n---\n".join(filtered_sections)


def get_staged_diff() -> str:
    """Get the staged diff, with amend-aware fallback for commit-msg stage.

    BUG-03: At commit-msg stage during ``git commit --amend``, ``--staged`` is
    empty because nothing new was staged.  We detect the amend via ORIG_HEAD
    and fall back to the commit's actual diff (HEAD~1..HEAD).

    Safety guards (SE-01, SE-02 from critical assessment):
      - ORIG_HEAD must exist (confirms amend, not a normal empty commit)
      - rev-list count must be >= 2 (HEAD~1 doesn't exist on first commit)
      - Single-commit amend falls back to diff against the empty tree
      - Entire fallback wrapped in try/except (diff retrieval must never crash)
    """
    result = subprocess.run(
        ["git", "diff", "--staged", "--unified=3"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
    )
    diff = result.stdout or ""

    # BUG-03: At commit-msg stage during amend, --staged is empty because
    # nothing new was staged.  Fall back to the commit's actual diff.
    if not diff.strip():
        hook_stage = os.environ.get("PRE_COMMIT_HOOK_STAGE", "")
        if hook_stage == "commit-msg":
            try:
                # SE-02: Only trigger on actual amend — ORIG_HEAD exists during
                # amend/rebase but not during normal commits.
                orig_head_check = subprocess.run(
                    ["git", "rev-parse", "--verify", "ORIG_HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=str(PROJECT_ROOT),
                )
                if orig_head_check.returncode != 0:
                    # Not an amend — genuinely empty staged diff.  Skip review.
                    return diff

                # SE-01: Guard against single-commit repos where HEAD~1
                # doesn't exist (would cause a fatal git error).
                count_result = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=str(PROJECT_ROOT),
                )
                commit_count = int(count_result.stdout.strip() or "0")

                if commit_count < 2:
                    # First commit being amended — diff against the empty tree.
                    # 4b825dc... is git's well-known empty tree hash.
                    amend_result = subprocess.run(
                        [
                            "git", "diff",
                            "4b825dc642cb6eb9a060e54bf899d15f",
                            "HEAD", "--unified=3",
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        cwd=str(PROJECT_ROOT),
                    )
                else:
                    amend_result = subprocess.run(
                        ["git", "diff", "HEAD~1", "HEAD", "--unified=3"],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        cwd=str(PROJECT_ROOT),
                    )

                if amend_result.stdout.strip():
                    diff = amend_result.stdout
                    print("[REVIEW] Amend detected: reviewing commit diff")
            except Exception as e:
                # Diff retrieval must never crash the gate.
                print(
                    f"[REVIEW] Amend fallback failed ({e}); "
                    "proceeding with staged diff"
                )

    return diff


def get_commit_message() -> str:
    """Read the commit message.

    In the commit-msg stage, pre-commit passes the path to COMMIT_EDITMSG as
    sys.argv[1]. We read the file rather than returning the path string.
    In pre-commit stage this file doesn't exist yet, so we return a placeholder.
    """
    hook_stage = os.environ.get("PRE_COMMIT_HOOK_STAGE", "pre-commit")

    # 1. CLI argument — in commit-msg stage pre-commit passes the COMMIT_EDITMSG
    #    file path as argv[1]; read the file rather than returning the path string.
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        arg_path = Path(arg)
        if arg_path.exists() and arg_path.is_file():
            return arg_path.read_text(encoding="utf-8").strip()
        return arg

    # 2. Fallback direct read — only valid outside pre-commit stage
    if hook_stage != "pre-commit":
        for msg_name in ("COMMIT_EDITMSG", "MERGE_MSG"):
            msg_file = PROJECT_ROOT / ".git" / msg_name
            if msg_file.exists():
                try:
                    return msg_file.read_text(encoding="utf-8").strip()
                except OSError:
                    pass

    return "(commit message not available)"


def get_recent_file_churn(diff: str) -> str:
    """Check if any changed files have been modified >3 times in the last week."""
    # Extract filenames from diff headers
    files = re.findall(r"^\+\+\+ b/(.+)$", diff, re.MULTILINE)
    churn_warnings = []
    for filepath in files[:20]:  # Limit to avoid slowness
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--oneline",
                    "--since=7 days ago",
                    "--follow",
                    "--",
                    filepath,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(PROJECT_ROOT),
            )
            commit_count = len(result.stdout.strip().splitlines())
            if commit_count >= 3:
                churn_warnings.append(
                    f"  {filepath} has been modified {commit_count} times in the last 7 days"
                )
        except Exception:
            pass
    return "\n".join(churn_warnings) if churn_warnings else ""


def filter_diff_by_skip_paths(diff: str, skip_paths: list[str]) -> str:
    """Remove diff hunks for files matching skip_paths patterns."""
    if not skip_paths:
        return diff

    lines = diff.split("\n")
    filtered_lines: list[str] = []
    skip_current_file = False

    for line in lines:
        if line.startswith("diff --git"):
            # Check if this file should be skipped
            skip_current_file = any(
                pattern.rstrip("/") in line for pattern in skip_paths
            )
        if not skip_current_file:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)


def shuffle_diff_hunks(diff: str) -> str:
    """Split diff into per-file blocks and shuffle them.
    Combats positional bias and 'middle loss' in LLM focus.
    """
    blocks = re.split(r"^(?=diff --git)", diff, flags=re.MULTILINE)
    header = blocks[0] if not blocks[0].startswith("diff") else ""
    hunks = [b for b in blocks if b.startswith("diff")]

    if len(hunks) <= 1:
        return diff

    random.shuffle(hunks)
    return header + "".join(hunks)


def consensus_filter(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate multiple reviews into a single objective verdict.
    A HIGH severity issue must be found in >= 50% of passes to block.
    """
    if not reviews:
        return {"verdict": "PASS", "summary": "No reviews available."}
    if len(reviews) == 1:
        return reviews[0]

    # Count verdicts
    v_counts = {"FAIL": 0, "WARN": 0, "PASS": 0}
    for r in reviews:
        v_counts[r.get("verdict", "PASS")] += 1

    # Aggregate issues
    all_issues = []
    for r in reviews:
        all_issues.extend(r.get("issues", []))

    # In a true consensus, we'd group similar issues.
    # For now, we'll promote issues that appear multiple times or just list all for War-Room visibility.
    # To prevent 'hallucinated' blocks in multi-pass, we only FAIL if FAIL > 50%
    if v_counts["FAIL"] > len(reviews) / 2:
        final_verdict = "FAIL"
    elif v_counts["FAIL"] > 0 or v_counts["WARN"] > 0:
        final_verdict = "WARN"
    else:
        final_verdict = "PASS"

    return {
        "verdict": final_verdict,
        "intent_alignment": reviews[0].get("intent_alignment", ""),
        "issues": all_issues,
        "summary": f"Consensus of {len(reviews)} passes: {v_counts}. "
        + reviews[0].get("summary", ""),
    }


def _build_user_message(
    diff: str,
    commit_msg: str,
    context: str,
    repo_map: str = "",
    adr_context: str = "",
    co_change_context: str = "",
) -> str:
    """Assemble the user message from diff, commit message, and context layers.

    ARCH-01: Message assembly is the orchestrator's responsibility.  The provider
    receives the pre-assembled string and handles transport only.
    """
    parts = []
    parts.append(
        f"## Commit Message\n{commit_msg if commit_msg.strip() else '(no commit message provided)'}"
    )
    if context:
        parts.append(f"## Project Architecture Guidelines\n{context}")
    if repo_map:
        parts.append(f"## Workspace Structure\n{repo_map}")
    if adr_context:
        parts.append(f"## Active ADR Contexts\n{adr_context}")
    if co_change_context:
        parts.append(f"## Co-change Blast Radius Alerts\n{co_change_context}")
    parts.append(f"## Staged Diff\n```diff\n{diff}\n```")
    return "\n\n".join(parts)


def render_review(review: Dict[str, Any], churn_info: str) -> None:
    """Pretty-print the review results to the terminal."""
    verdict = review.get("verdict", "UNKNOWN")
    issues = review.get("issues", [])
    summary = review.get("summary", "")
    alignment = review.get("intent_alignment", "")

    ICONS = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
    SEV_ICONS = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}

    print("\n" + "─" * 60)
    print(f"  AI ADVERSARIAL REVIEW  {ICONS.get(verdict, '❓')} {verdict}")
    if verdict == "FAIL":
        blocking = review.get("blocking_concern")
        if blocking:
            print(f"  Blocking concern: {blocking}")
    print("─" * 60)
    print(f"\n  Intent: {alignment}\n")

    if churn_info:
        print("  📊 File Churn Warnings:")
        for line in churn_info.strip().splitlines():
            print(f"     {line}")
        print()

    if issues:
        for issue in issues:
            sev = issue.get("severity", "LOW")
            concern = issue.get("concern", "GENERAL")
            loc = issue.get("location", "general")
            desc = issue.get("description", "")
            remediation = issue.get("remediation", "")
            print(f"  {SEV_ICONS.get(sev, '⚪')} [{sev}] <{concern}> {loc}")
            print(f"     {desc}")
            if remediation:
                print(f"     💡 Fix: {remediation}")
            print()
    else:
        print("  No issues found.\n")

    print(f"  Summary: {summary}")
    print("─" * 60 + "\n")


def _persist_verdict(
    verdict_obj: ReviewVerdict | None = None,
    review: Dict[str, Any] | None = None,
    fail_open_reason: str | None = None,
    provider_name: str | None = None,
) -> None:
    """Append the review verdict to a local JSONL log for auditability.

    Accepts a typed ``ReviewVerdict`` (preferred) or a legacy ``dict``.
    The ``fail_open_reason`` parameter is kept for crash-path callers in
    ``main()`` that have no verdict object to pass.

    SEC-01: ``provider_name`` is logged alongside the model name so
    provider drift is detectable in audit trails.
    """
    try:
        log_path = PROJECT_ROOT / ".ai-review-log.jsonl"

        if verdict_obj is not None:
            # Typed path — serialise the full model plus audit envelope.
            base = verdict_obj.model_dump()
            base["timestamp"] = datetime.datetime.now().isoformat()
            base["issue_count"] = len(verdict_obj.issues)
            base["concerns"] = list(
                {i.get("concern", "GENERAL") for i in verdict_obj.issues}
            )
            if provider_name:
                base["provider"] = provider_name
            record = base
        else:
            # Legacy / crash-path: review may be an empty dict.
            raw = review or {}
            record = {
                "timestamp": datetime.datetime.now().isoformat(),
                "verdict": (
                    "FAIL_OPEN" if fail_open_reason else raw.get("verdict", "UNKNOWN")
                ),
                "blocking_concern": raw.get("blocking_concern"),
                "fail_open_reason": fail_open_reason,
                "intent_alignment": raw.get("intent_alignment", ""),
                "issue_count": len(raw.get("issues", [])),
                "concerns": list(
                    {i.get("concern", "GENERAL") for i in raw.get("issues", [])}
                ),
                "summary": raw.get("summary", ""),
                "model": MODEL,
            }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass  # Never block a commit due to logging failure


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    """Run the adversarial review gate. Returns 0 (pass) or 1 (fail)."""
    try:
        return _run_review()
    except Exception as e:
        # FAIL-OPEN: a reviewer crash must never block a commit
        _persist_verdict(fail_open_reason=str(e))
        print(f"\u26a0\ufe0f  AI review crashed (fail-open): {e}")
        return 0


def _run_review() -> int:
    """Internal review logic. Exceptions propagate to main() for fail-open."""
    # Resolve changed files and active ADR domains early for risk assessment & session traceability
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
        )
        changed_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
        
        try:
            from architecture_checks import extract_adr_annotations
        except ImportError:
            extract_adr_annotations = lambda path: []
            
        active_domains = []
        for f in changed_files:
            if Path(f).exists():
                for domain in extract_adr_annotations(f):
                    active_domains.append(domain.lower())
    except Exception:
        changed_files = []
        active_domains = []

    is_hr, matches = classify_commit_risk(changed_files, active_domains)
    session_id = _get_active_session_id()

    # Allow explicit bypass via env var or local file
    if os.environ.get("SKIP_AI_REVIEW") == "1":
        if is_hr:
            # Enforce structured bypass validation
            skip_reason_str = os.environ.get("SKIP_REASON", "").strip()
            bypass_data = None
            used_vector = None
            
            # Vector B (Direct): First parse from SKIP_REASON env var if it's JSON
            if skip_reason_str and skip_reason_str != "@file":
                try:
                    bypass_data = json.loads(skip_reason_str)
                    used_vector = "Vector B (Direct Env)"
                except Exception:
                    pass

            session_file = PROJECT_ROOT / ".agent" / "state" / "session.json"
            session_start_time = None
            if session_file.exists():
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        session_start_time = json.load(f).get("start_time")
                except Exception:
                    pass

            bypass_file = PROJECT_ROOT / ".skip-ai-reason.json"

            # Vector C (Interactive TTY Wizard): Prompt developer and write to file
            # *Note on labels*: labels reflect naming (A=file, B=direct, C=wizard) not execution order (B -> C -> A)
            if not bypass_data and sys.stdin.isatty():
                print("[BYPASS] High-risk commit bypass interactive wizard active (Vector C)...")
                rebuttal_type = ""
                while rebuttal_type not in ("FALSE_POSITIVE", "SPEC_REQUIREMENT", "ARCHITECTURAL_INVARIANT", "OUT_OF_SCOPE"):
                    print("Select rebuttal type:")
                    print("  1. FALSE_POSITIVE")
                    print("  2. SPEC_REQUIREMENT")
                    print("  3. ARCHITECTURAL_INVARIANT")
                    print("  4. OUT_OF_SCOPE")
                    choice = input("Choice (1-4): ").strip()
                    if choice == "1": rebuttal_type = "FALSE_POSITIVE"
                    elif choice == "2": rebuttal_type = "SPEC_REQUIREMENT"
                    elif choice == "3": rebuttal_type = "ARCHITECTURAL_INVARIANT"
                    elif choice == "4": rebuttal_type = "OUT_OF_SCOPE"

                finding_ids_str = input("Finding IDs (comma-separated, e.g. T1-G-07,T1-L-10): ").strip()
                finding_ids = [fid.strip() for fid in finding_ids_str.split(",") if fid.strip()]
                evidence = input("Evidence/Rationale: ").strip()

                wizard_data = {
                    "rebuttal_type": rebuttal_type,
                    "finding_ids": finding_ids,
                    "evidence": evidence,
                }

                try:
                    with open(bypass_file, "w", encoding="utf-8") as f:
                        json.dump(wizard_data, f, indent=4)
                    print(f"[BYPASS] Wizard successfully wrote {bypass_file.name}")
                except Exception as e:
                    print(f"❌ [BYPASS] Failed to write wizard file: {e}")

            # Vector A (File): Read from .skip-ai-reason.json
            if not bypass_data and (skip_reason_str == "@file" or bypass_file.exists()):
                if bypass_file.exists():
                    try:
                        mtime = bypass_file.stat().st_mtime
                        import datetime
                        if session_start_time:
                            session_dt = datetime.datetime.fromisoformat(session_start_time.replace("Z", "+00:00"))
                            file_dt = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc)
                            if file_dt < session_dt:
                                print("⚠️  [BYPASS] STALE_BYPASS_FILE_DETECTED: Rationale file predates current session startup!")
                    except Exception:
                        pass

                    try:
                        bypass_data = json.loads(bypass_file.read_text(encoding="utf-8"))
                        used_vector = "Vector A (File)"

                        # Immediately consume-and-delete on successful read
                        try:
                            bypass_file.unlink()
                            print(f"[BYPASS] Successfully consumed and deleted {bypass_file.name}")
                        except Exception as e:
                            print(f"⚠️  [BYPASS] Failed to auto-delete {bypass_file.name}: {e}")
                    except Exception as e:
                        print(f"❌ [BYPASS] Error reading bypass file: {e}")

            if not bypass_data:
                print("❌ [BYPASS] High-risk commit bypass rejected!")
                print("   A structured SKIP_REASON (JSON) is required for high-risk commits.")
                print("   Please provide it via environment variable SKIP_REASON='{...}'")
                print("   or write it to `.skip-ai-reason.json` and set SKIP_REASON='@file'")
                print("\n   Required keys: rebuttal_type, finding_ids (list), evidence")
                print("   Rebuttal types: FALSE_POSITIVE, SPEC_REQUIREMENT, ARCHITECTURAL_INVARIANT, OUT_OF_SCOPE")
                sys.exit(1)

            rebuttal_type = bypass_data.get("rebuttal_type")
            finding_ids = bypass_data.get("finding_ids")
            evidence = bypass_data.get("evidence")

            valid_rebuttals = ("FALSE_POSITIVE", "SPEC_REQUIREMENT", "ARCHITECTURAL_INVARIANT", "OUT_OF_SCOPE")

            if (rebuttal_type not in valid_rebuttals or 
                not isinstance(finding_ids, list) or not finding_ids or 
                not isinstance(evidence, str) or not evidence.strip()):
                print("❌ [BYPASS] Validation failed for structured bypass reason!")
                print(f"   Received: {bypass_data}")
                print("   Ensure all keys (rebuttal_type, finding_ids, evidence) are present and valid.")
                sys.exit(1)

            print(f"⚡ AI review bypassed via {used_vector} ({rebuttal_type})")

            log_harness_event({
                "event_type": "high_risk_gate_override",
                "severity": "WARNING",
                "payload": {
                    "reason": "Developer bypassed high-risk gate",
                    "skip_reason": bypass_data,
                    "high_risk_matches": matches
                }
            })

            if rebuttal_type == "FALSE_POSITIVE":
                try:
                    eval_script = PROJECT_ROOT / ".agent" / "scripts" / "false_positive_to_eval.py"
                    if eval_script.exists():
                        fids_arg = ",".join(finding_ids)
                        subprocess.Popen([
                            sys.executable,
                            str(eval_script),
                            "--finding-id", fids_arg,
                            "--rebuttal-type", rebuttal_type,
                            "--evidence", evidence
                        ])
                        print("[BYPASS] Triggered false positive logging asynchronously.")
                except Exception as e:
                    print(f"⚠️  [BYPASS] Failed to spawn false_positive_to_eval.py: {e}")

            return 0
        else:
            print("⚡ AI review skipped (SKIP_AI_REVIEW=1)")
            return 0

    # Allow bypass via sentinel file (for pre-commit env var propagation issues)
    if (PROJECT_ROOT / ".skip-ai-review").exists():
        print("\u26a1 AI review skipped (.skip-ai-review file found)")
        return 0

    # Get the staged diff
    diff = get_staged_diff()
    if not diff.strip():
        return 0

    # Load config
    config = load_config()
    
    # ── T1-G-02: Pre-flight shortcut ──────────────────────────────────────────
    # Evaluate before any LLM call. If all changes are doc/whitespace/comments,
    # emit PASS_FAST and exit immediately at zero API cost.
    preflight = check_preflight_shortcut(diff)
    if preflight.direct_pass_allowed:
        fast_verdict = ReviewVerdict(
            verdict="PASS_FAST",
            planner_note=preflight.planner_note,
            model="preflight",
            token_usage={},
            verdict_tier="preflight",
            session_id=session_id,
        )
        _persist_verdict(verdict_obj=fast_verdict)
        print(f"⚡ AI review: PASS_FAST — {preflight.planner_note}")
        return 0

    skip_paths = config.get("skip_paths", [])

    # Filter out skipped paths
    diff = filter_diff_by_skip_paths(diff, skip_paths)
    if not diff.strip():
        print("\u26a1 AI review skipped: all changed files are in skip_paths.")
        return 0

    # Diff size guards — skip rather than truncate (partial diffs cause hallucination)
    diff_lines = diff.count("\n")
    max_lines = config.get("max_diff_lines", MAX_DIFF_LINES)
    if diff_lines > max_lines:
        print(
            f"\u26a0\ufe0f  AI review skipped: diff too large ({diff_lines} lines > {max_lines} max)."
        )
        print("   Review this commit manually.")
        return 0

    diff_chars = len(diff)
    max_chars = config.get("max_diff_chars", MAX_DIFF_CHARS)
    if diff_chars > max_chars:
        print(
            f"\u26a0\ufe0f  AI review skipped: diff too large ({diff_chars:,} chars > {max_chars:,} max)."
        )
        print("   Review this commit manually.")
        return 0

    # ── T1-G-02: Pre-flight shortcut ──────────────────────────────────────────
    # Evaluate before any LLM call. If all changes are doc/whitespace/comments,
    # emit PASS_FAST and exit immediately at zero API cost.
    preflight = check_preflight_shortcut(diff)
    if preflight.direct_pass_allowed:
        fast_verdict = ReviewVerdict(
            verdict="PASS_FAST",
            planner_note=preflight.planner_note,
            model="preflight",
            token_usage={},
            verdict_tier="preflight",
            # context_snapshot stays None — no context was injected
        )
        _persist_verdict(verdict_obj=fast_verdict)
        print(f"\u26a1 AI review: PASS_FAST — {preflight.planner_note}")
        return 0
    # ─────────────────────────────────────────────────────────────────────────

    # Get commit message, PageRank repo map, and ADR context
    commit_msg = get_commit_message()
    context = load_review_context(diff)

    # 2. Generate PageRank Repo Map & Scores (T1-H-01)
    _setup_sys_path()
    try:
        from repo_map import generate_repo_map, get_pagerank_scores

        repo_map = generate_repo_map(changed_files)
        pagerank_scores = get_pagerank_scores(changed_files)
    except Exception:
        repo_map = ""
        pagerank_scores = {}

    # 3. Generate prioritized ADR context (T1-H-02)
    adr_context, active_domains, adr_policy_notes = get_adr_context(changed_files)

    # T1-E-02 / T1-L-08: Resolve provider after active_domains / changed_files are resolved
    try:
        from providers import get_provider

        provider = get_provider()
    except RuntimeError as e:
        reason = f"Provider setup failed: {e}"
        return _handle_api_unavailable(reason, changed_files, active_domains)

    # 4. Compute RouteDecision dynamically (T1-G-01, T1-G-04)
    route_decision = build_route_decision(changed_files, diff, pagerank_scores)
    # Merge any adr-specific policy notes into our routing decision
    if adr_policy_notes:
        route_decision.policy_notes.extend(adr_policy_notes)

    print("\n" + "─" * 60)
    print("⚙️  AI REVIEW DYNAMIC ROUTING DECISION")
    print(f"   Intensity: {route_decision.review_intensity.upper()}")
    print(f"   Rationale: {route_decision.rationale}")
    print("   Policy Notes:")
    for note in route_decision.policy_notes:
        print(f"     {note}")
    print("─" * 60 + "\n")

    # 5. Run co-change estimator (T1-H-03)
    co_change_context = ""
    co_change_warnings = []
    try:
        from co_change_check import run_co_change_estimator

        co_change_warnings = run_co_change_estimator(changed_files)
    except Exception:
        pass

    if co_change_warnings:
        print("📊 CO-CHANGE BLAST RADIUS ADVISORY")
        for w in co_change_warnings:
            conf_symbol = SYMBOL_REVIEW if w["confidence"] == "HIGH" else "💡"
            print(f"   {conf_symbol} [{w['confidence']}] {w['reason']}")
        print("─" * 60 + "\n")

        high_alerts = [w for w in co_change_warnings if w["confidence"] == "HIGH"]
        if high_alerts:
            co_change_context = "WARNING: The following related files might have missing updates based on structural and historical patterns:\n"
            for w in high_alerts:
                co_change_context += f"- {w['unstaged']} (correlated with staged '{w['staged']}' via structural imports and history)\n"

    # Check for file churn (remediation loop signal)
    churn_info = get_recent_file_churn(diff)

    passes = config.get("passes", DEFAULT_PASSES)
    print(
        f"\n🔍 Running AI review ({provider.name}/{provider.model}, "
        f"{passes} pass{'es' if passes > 1 else ''})...",
        flush=True,
    )
    start_time = time.time()

    raw_review: Dict[str, Any] = {}
    try:
        results = []
        for i in range(passes):
            if passes > 1:
                print(f"   Pass {i+1}/{passes}...", end="", flush=True)

            # Application of shuffling
            current_diff = diff
            if SHUFFLE_HUNKS:
                current_diff = shuffle_diff_hunks(diff)

            # ARCH-01: Message assembly here (orchestrator), transport in provider
            user_content = _build_user_message(
                current_diff,
                commit_msg,
                context,
                repo_map=repo_map,
                adr_context=adr_context,
                co_change_context=co_change_context,
            )
            review_dict = provider.review(SYSTEM_PROMPT, user_content)
            results.append(review_dict)

            if passes > 1:
                print(" done.")

        # Consensus Filtering
        raw_review = consensus_filter(results)

    except urllib.error.URLError as e:
        elapsed = time.time() - start_time
        reason = f"Network error ({elapsed:.1f}s): {e}"
        return _handle_api_unavailable(reason, changed_files, active_domains)
    except json.JSONDecodeError as e:
        reason = f"JSON parse error: {e}"
        return _handle_api_unavailable(reason, changed_files, active_domains)
    except Exception as e:
        reason = str(e)
        return _handle_api_unavailable(reason, changed_files, active_domains)

    elapsed = time.time() - start_time

    # ── T1-G-03: Validate LLM response against typed ReviewVerdict ────────────
    # Build a context_snapshot for FAIL/WARN verdicts to aid reproducibility.
    raw_verdict_str = raw_review.get("verdict", "PASS").upper()

    # ── Map WARN to FAIL when review_intensity is critical ──────────────────
    if route_decision.review_intensity == "critical" and raw_verdict_str == "WARN":
        raw_verdict_str = "FAIL"
        raw_review["verdict"] = "FAIL"
        raw_review["blocking_concern"] = "CRITICAL_PATH_SAFETY"
        raw_review["summary"] = (
            "[CRITICAL INTENSITY ESCALATION] Verdict WARN promoted to FAIL. "
            "Staged changes modify core high-priority architectural files. "
            + raw_review.get("summary", "")
        )
        if "issues" in raw_review:
            for issue in raw_review["issues"]:
                if issue.get("severity") == "MEDIUM":
                    issue["severity"] = "HIGH"
                    issue["description"] = (
                        f"[PageRank Critical Escalation] {issue.get('description', '')}"
                    )
    # ─────────────────────────────────────────────────────────────────────────

    is_hr, _ = classify_commit_risk(changed_files, active_domains)
    snapshot: Optional[str] = None
    if raw_verdict_str in ("FAIL", "WARN", "PASS"):
        # Record which context sections were active so a FAIL can be debugged
        # without reconstructing the full session state (arXiv 2603.07670).
        active_sections = _get_active_context_sections(diff)
        snapshot = f"sections={active_sections}; adr_domains={active_domains}; repo_map_len={len(repo_map)}; context_chars={len(context)}; is_high_risk={is_hr}"

    try:
        # Ratios & Estimated Token Calculation
        ratios = _load_token_ratios()
        tier = "budget" if provider.name == "ollama" else "review"
        ratio = ratios.get(tier, 4.0 if tier == "review" else 3.5)

        context_load_est = len(context) // ratio
        repo_map_est = len(repo_map) // ratio
        adr_injection_est = len(adr_context) // ratio

        actual_tokens = provider.last_token_usage
        in_tokens = actual_tokens.get("input_tokens", 0)
        out_tokens = actual_tokens.get("output_tokens", 0)

        token_usage_dict = {
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "context_load_estimated_tokens": int(context_load_est),
            "repo_map_estimated_tokens": int(repo_map_est),
            "adr_injection_estimated_tokens": int(adr_injection_est),
        }

        typed_verdict = ReviewVerdict(
            verdict=raw_verdict_str,
            blocking_concern=raw_review.get("blocking_concern"),
            model=provider.model,
            verdict_tier="budget" if provider.name == "ollama" else "review",
            context_snapshot=snapshot,
            intent_alignment=raw_review.get("intent_alignment"),
            summary=raw_review.get("summary"),
            issues=raw_review.get("issues", []),
            route_decision=route_decision,
            session_id=session_id,
            token_usage=token_usage_dict,
        )
        
        # Verify and suppress confirmed branch-isolated models from ORM roster
        verify_and_suppress_roster_issues(typed_verdict, route_decision)
        raw_review["verdict"] = typed_verdict.verdict
        raw_review["issues"] = typed_verdict.issues
        raw_review["blocking_concern"] = typed_verdict.blocking_concern

    except ValidationError as exc:
        fail_reason = f"ReviewVerdict validation failed: {exc}"
        return _handle_api_unavailable(fail_reason, changed_files, active_domains)

    _persist_verdict(verdict_obj=typed_verdict, provider_name=provider.name)
    render_review(raw_review, churn_info)
    print(f"  \u23f1\ufe0f  Review completed in {elapsed:.1f}s\n")

    if typed_verdict.verdict == "FAIL":
        print("\u274c Commit BLOCKED by AI review. Fix HIGH severity issues or run:")
        print("   SKIP_AI_REVIEW=1 git commit ...  to bypass")
        print("   -- or create a .skip-ai-review file in the project root\n")
        return 1
    elif typed_verdict.verdict == "WARN":
        print("\u26a0\ufe0f  Warnings noted. Commit proceeding.\n")
        return 0
    else:
        print("\u2705 AI review passed.\n")
        return 0


def _get_active_context_sections(diff: str) -> str:
    """Return a compact string of active review_context section IDs for a diff.

    Used to populate ``context_snapshot`` on FAIL/WARN verdicts (T1-G-03).
    Mirrors the trigger_map in ``_select_context_sections`` without re-parsing
    the full context document.
    """
    trigger_map = {
        "transactional_integrity": [
            "src/application/services/",
            "UnitOfWork",
            "uow.",
            ".commit()",
        ],
        "branch_isolation": ["src/infrastructure/database/", "Repository", "branch_id"],
        "mass_assignment": ["src/domain/schemas/", "BaseModel", "model_config"],
        "rbac": ["require_permission", "Role", "permission", "src/presentation/api/"],
        "migrations": ["migrations/versions/", "alembic", "op.add_column"],
        "clean_arch": ["src/domain/", "src/application/", "src/infrastructure/"],
    }
    active = {"micro_checks"}
    for section_id, patterns in trigger_map.items():
        if any(p in diff for p in patterns):
            active.add(section_id)
    return ",".join(sorted(active))


if __name__ == "__main__":
    sys.exit(main())
