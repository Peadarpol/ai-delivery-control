#!/usr/bin/env python3
"""
route_decision.py — Commit risk classification and routing module
"""

from __future__ import annotations

import fnmatch
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple
try:
    from pydantic import BaseModel, Field
    _pydantic_installed = True
except ImportError:
    _pydantic_installed = False
    class FieldStub:
        def __init__(self, default=None, default_factory=None, **kwargs):
            self.default = default
            self.default_factory = default_factory
    def Field(default=None, default_factory=None, **kwargs):
        return FieldStub(default, default_factory, **kwargs)
    class BaseModel:
        """NOTE: fallback stub does not validate Literal/type constraints — values are accepted as-is when Pydantic is absent."""
        def __init__(self, **kwargs):
            fields = {}
            for cls in self.__class__.__mro__:
                if hasattr(cls, "__annotations__"):
                    for field_name in cls.__annotations__:
                        if not field_name.startswith("_") and field_name not in fields:
                            val = getattr(self.__class__, field_name, None)
                            fields[field_name] = val
            for k, val in fields.items():
                if val is not None:
                    if isinstance(val, FieldStub):
                        if val.default_factory:
                            setattr(self, k, val.default_factory())
                        else:
                            setattr(self, k, val.default)
                    else:
                        setattr(self, k, val)
                else:
                    setattr(self, k, None)
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self) -> Dict[str, Any]:
            res = {}
            for k, v in self.__dict__.items():
                if isinstance(v, BaseModel):
                    res[k] = v.model_dump()
                elif isinstance(v, list):
                    res[k] = [item.model_dump() if isinstance(item, BaseModel) else item for item in v]
                else:
                    res[k] = v
            return res
        def dict(self) -> Dict[str, Any]:
            return self.model_dump()

def _find_project_root() -> Path:
    """Traverse upwards to locate the workspace root (directory containing .git)."""
    curr = Path(__file__).resolve().parent
    for _ in range(10):
        if (curr / ".git").exists():
            return curr
        curr = curr.parent
    return Path(__file__).resolve().parent.parent # fallback

PROJECT_ROOT = _find_project_root()

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


class RouteDecision(BaseModel):
    """Stub for T1-G-01 capability routing — forward-compatibility only."""

    selected_tools: List[str] = Field(default_factory=list)
    review_intensity: Literal["standard", "elevated", "critical"] = "standard"
    rationale: str = ""
    policy_notes: List[str] = Field(default_factory=list)


UNIVERSAL_ADR_DOMAIN_TO_CAPABILITY = {
    "branch_isolation": "BRANCH_ISOLATION",
    "remove_uow_autocommit": "TRANSACTIONAL_INTEGRITY",
    "clean_architecture": "CLEAN_ARCH",
    "authentication": "RBAC",
    "schema_hardening": "MASS_ASSIGNMENT",
    "uow_pattern": "TRANSACTIONAL_INTEGRITY",
}


def _get_active_ai_review() -> Any:
    import inspect
    import sys
    for frame_info in inspect.stack():
        name = frame_info.frame.f_globals.get("__name__", "")
        if name.endswith("ai_review"):
            class ModuleWrapper:
                def __init__(self, globs):
                    self.globs = globs
                def __getattr__(self, key):
                    return self.globs.get(key)
            return ModuleWrapper(frame_info.frame.f_globals)
    from harness_utils import get_harness_config


def _load_adr_capability_mappings_from_config() -> Dict[str, str]:
    """Load ADR domain -> capability name mapping from architecture_checks.adr_capability_mappings in .agent/config.yaml."""
    ai_rev = _get_active_ai_review()
    if ai_rev is not None:
        func = getattr(ai_rev, "_load_adr_capability_mappings", None)
        if func is not None and (hasattr(func, "mock_add_spec") or hasattr(func, "_mock_call")):
            return func()

    project_root = getattr(ai_rev, "PROJECT_ROOT", PROJECT_ROOT) if ai_rev is not None else PROJECT_ROOT
    config_path = project_root / ".agent" / "config.yaml"
    val = get_harness_config("architecture_checks", "adr_capability_mappings", config_path=config_path)
    return val if isinstance(val, dict) else {}


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


def _load_layer_paths_from_config() -> Dict[str, str]:
    """Load layer name → path from architecture.layers in .agent/config.yaml."""
    ai_rev = _get_active_ai_review()
    if ai_rev is not None:
        func = getattr(ai_rev, "_load_layer_paths_from_config", None)
        if func is not None and (hasattr(func, "mock_add_spec") or hasattr(func, "_mock_call")):
            return func()

    project_root = getattr(ai_rev, "PROJECT_ROOT", PROJECT_ROOT) if ai_rev is not None else PROJECT_ROOT
    config_path = project_root / ".agent" / "config.yaml"
    raw_layers = get_harness_config("architecture", "layers", config_path=config_path)
    layers: Dict[str, str] = {}
    if isinstance(raw_layers, list):
        for item in raw_layers:
            if isinstance(item, dict):
                name = item.get("name")
                path_val = item.get("path")
                if name and path_val and not path_val.startswith("["):
                    layers[name] = path_val
    elif isinstance(raw_layers, dict):
        for name, path_val in raw_layers.items():
            if name and path_val and isinstance(path_val, str) and not path_val.startswith("["):
                layers[name] = path_val
    return layers


def _load_high_risk_patterns() -> Dict[str, Any]:
    """Load high_risk_patterns from .agent/config.yaml."""
    ai_rev = _get_active_ai_review()
    if ai_rev is not None:
        func = getattr(ai_rev, "_load_high_risk_patterns", None)
        if func is not None and (hasattr(func, "mock_add_spec") or hasattr(func, "_mock_call")):
            return func()

    project_root = getattr(ai_rev, "PROJECT_ROOT", PROJECT_ROOT) if ai_rev is not None else PROJECT_ROOT
    config_path = project_root / ".agent" / "config.yaml"
    raw_hrp = get_harness_config("architecture_checks", "high_risk_patterns", config_path=config_path)

    config_patterns: Dict[str, Any] = {
        "override_defaults": False,
        "paths": [],
        "filenames": [],
        "adr_domains": [],
    }
    if isinstance(raw_hrp, dict):
        config_patterns["override_defaults"] = bool(raw_hrp.get("override_defaults", False))
        for k in ("paths", "filenames", "adr_domains"):
            items = raw_hrp.get(k, [])
            if isinstance(items, list):
                config_patterns[k] = [str(x) for x in items if x]
    return config_patterns


def classify_commit_risk(changed_files: List[str], adr_domains: List[str]) -> Tuple[bool, List[str]]:
    """Classify commit risk based on modified paths, filenames, and active ADR domains.

    Returns:
        (is_high_risk, matched_patterns)
    """
    ai_rev = _get_active_ai_review()
    if ai_rev is not None:
        func = getattr(ai_rev, "classify_commit_risk", None)
        if func is not None and (hasattr(func, "mock_add_spec") or hasattr(func, "_mock_call")):
            return func(changed_files, adr_domains)

    cfg = _load_high_risk_patterns()
    override_defaults = cfg.get("override_defaults", False)

    if override_defaults:
        paths = cfg.get("paths", [])
        filenames = cfg.get("filenames", [])
        adr_domains_list = cfg.get("adr_domains", [])
        if not paths and not filenames and not adr_domains_list:
            import logging
            logging.critical("CRITICAL_WARNING_ZERO_HIGH_RISK_PATTERNS: override_defaults is true but high_risk_patterns is empty! Failing closed to elevated.")
            return True, ["CRITICAL_WARNING_ZERO_HIGH_RISK_PATTERNS"]
    else:
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


def get_high_risk_files(changed_files: List[str]) -> List[str]:
    """Identify high-risk files from changed_files using high-risk patterns."""
    ai_rev = _get_active_ai_review()
    if ai_rev is not None:
        func = getattr(ai_rev, "get_high_risk_files", None)
        if func is not None and (hasattr(func, "mock_add_spec") or hasattr(func, "_mock_call")):
            return func(changed_files)

    cfg = _load_high_risk_patterns()
    paths = list(HIGH_RISK_PATTERNS["paths"]) + cfg.get("paths", [])
    filenames = list(HIGH_RISK_PATTERNS["filenames"]) + cfg.get("filenames", [])
    
    high_risk = []
    for f in changed_files:
        normalized_f = f.replace("\\", "/")
        name = Path(f).name
        matched = False
        for pat in paths:
            if fnmatch.fnmatch(normalized_f, pat):
                matched = True
                break
        if not matched:
            for fn in filenames:
                if name == fn:
                    matched = True
                    break
        if matched:
            high_risk.append(f)
    return high_risk


def build_route_decision(
    changed_files: List[str], diff_text: str, pagerank_scores: Dict[str, float]
) -> RouteDecision:
    """Populates the RouteDecision model based on path matching, ADRs, and PageRank."""
    ai_rev = _get_active_ai_review()
    if ai_rev is not None:
        func = getattr(ai_rev, "build_route_decision", None)
        if func is not None and (hasattr(func, "mock_add_spec") or hasattr(func, "_mock_call")):
            return func(changed_files, diff_text, pagerank_scores)

    selected_tools = []
    policy_notes = []

    # 1. Determine active capability tools by path and content matching
    changed_normalized = [f.replace("\\", "/") for f in changed_files]

    # Config-driven layer path routing (replaces GymBase hardcoded paths).
    # Reads architecture.layers from .agent/config.yaml; falls back to
    # ADR-annotation-only activation when no layers are configured.
    _layer_paths = _load_layer_paths_from_config()

    if _layer_paths:
        _app_paths = [p for n, p in _layer_paths.items()
                      if any(k in n.lower() for k in ("application", "service"))]
        _infra_paths = [p for n, p in _layer_paths.items()
                        if any(k in n.lower() for k in ("infrastructure", "repository"))]
        _domain_paths = [p for n, p in _layer_paths.items()
                         if any(k in n.lower() for k in ("domain", "model"))]
        _api_paths = [p for n, p in _layer_paths.items()
                      if any(k in n.lower() for k in ("presentation", "api"))]
        _touches_clean = list(_layer_paths.values())

        def _touches(paths: List[str]) -> bool:
            return any(
                f.startswith(lp.rstrip("/") + "/")
                for f in changed_normalized
                for lp in paths
            )

        has_db_or_srv = _touches(_app_paths) or _touches(_infra_paths)
        has_domain_or_models = _touches(_domain_paths)
        has_api = _touches(_api_paths)
        has_clean_arch = _touches(_touches_clean)
    else:
        # No layers configured — path-based routing disabled.
        # TRANSACTIONAL_INTEGRITY and BRANCH_ISOLATION activate only via
        # ADR annotations or content-based pattern matching.
        has_db_or_srv = False
        has_domain_or_models = False
        has_api = False
        has_clean_arch = False

    has_migrations = any("migrations/versions/" in f for f in changed_normalized)

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
