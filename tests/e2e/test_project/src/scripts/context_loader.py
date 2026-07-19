#!/usr/bin/env python3
"""
context_loader.py — Review context loading and ADR injection module
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def _find_project_root() -> Path:
    """Traverse upwards to locate the workspace root (directory containing .git)."""
    curr = Path(__file__).resolve().parent
    for _ in range(10):
        if (curr / ".git").exists():
            return curr
        curr = curr.parent
    return Path(__file__).resolve().parent.parent # fallback

PROJECT_ROOT = _find_project_root()
SCRIPT_DIR = Path(__file__).resolve().parent

UNIVERSAL_CONTEXT_FILE = SCRIPT_DIR / "review_context_universal.md"
PROJECT_CONTEXT_FILE = SCRIPT_DIR / "review_context_project.md"
_ADR_TRIGGERS = ["# ADR:", "Decision /", "Exposes: FM", "AT[", "docs/adr/"]

try:
    import repo_map
except ImportError:
    repo_map = None

try:
    import architecture_checks
except ImportError:
    architecture_checks = None

def get_pagerank_scores(changed_files: list[str]) -> dict[str, float]:
    if repo_map is not None and hasattr(repo_map, "get_pagerank_scores"):
        return repo_map.get_pagerank_scores(changed_files)
    return {}

def extract_adr_annotations(filepath: str, scan_lines: int = 20) -> list[str]:
    if architecture_checks is not None and hasattr(architecture_checks, "extract_adr_annotations"):
        return architecture_checks.extract_adr_annotations(filepath, scan_lines)
    return []

try:
    from architecture_checks import DOMAIN_REGISTRY
except ImportError:
    DOMAIN_REGISTRY = set()


def get_adr_context(changed_files: list[str]) -> tuple[str, list[str], list[str]]:
    """
    Extracts, prioritizes, whitelists, and synthesizes active ADR wiki pages
    into a budget-compliant context (≤400 tokens) using the three-step token squeeze.

    Returns:
        tuple (adr_context_string, active_domains, policy_notes)
    """
    try:
        from harness_utils import _setup_sys_path
    except ImportError:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "src" / "scripts"))
        from harness_utils import _setup_sys_path
    _setup_sys_path()

    # 1. Compute PageRank scores
    try:
        pagerank_scores = get_pagerank_scores(changed_files)
    except Exception:
        pagerank_scores = {}

    # 2. Extract and whitelist annotations across all files
    domain_to_max_score = {}

    for path in (PROJECT_ROOT / "src").rglob("*.py"):
        rel_path = path.relative_to(PROJECT_ROOT)
        filepath_str = str(rel_path).replace("\\", "/")
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
    import inspect
    import sys
    ai_rev = None
    for frame_info in inspect.stack():
        name = frame_info.frame.f_globals.get("__name__", "")
        if name.endswith("ai_review"):
            class ModuleWrapper:
                def __init__(self, globs):
                    self.globs = globs
                def __getattr__(self, key):
                    return self.globs.get(key)
            ai_rev = ModuleWrapper(frame_info.frame.f_globals)
            break
    if ai_rev is None:
        ai_rev = sys.modules.get("src.scripts.ai_review") or sys.modules.get("ai_review")

    if ai_rev is not None:
        universal_file = getattr(ai_rev, "UNIVERSAL_CONTEXT_FILE", UNIVERSAL_CONTEXT_FILE)
        project_file = getattr(ai_rev, "PROJECT_CONTEXT_FILE", PROJECT_CONTEXT_FILE)
    else:
        universal_file = UNIVERSAL_CONTEXT_FILE
        project_file = PROJECT_CONTEXT_FILE

    if not universal_file.exists():
        print(f"Error: Universal review context file is missing at {universal_file}. Installation may be corrupt.", file=sys.stderr)
        sys.exit(1)

    # 1. Load Universal Context
    try:
        universal_content = universal_file.read_text(encoding="utf-8")
        print(f"[REVIEW] Loaded universal context from {universal_file.name}")
    except Exception as e:
        print(f"Error: Failed to read universal context file: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Load Project Context
    project_content = ""
    if project_file.exists() and project_file.is_file():
        try:
            project_content = project_file.read_text(encoding="utf-8")
            print(f"[REVIEW] Loaded project context from {project_file.name}")
        except Exception as e:
            print(f"Warning: Failed to read project context file: {e}", file=sys.stderr)
            pass
    else:
        print("[REVIEW] Project context absent — proceeding with universal guidelines only")

    # 3. Concatenate layers (project content after universal content)
    combined = universal_content
    if project_content.strip():
        combined += "\n\n" + project_content

    if not diff:
        return combined

    # Extract all universal section IDs via regex and identify always-include ones
    universal_ids = set(re.findall(r"<!-- SECTION:([\w_]+) -->", universal_content))
    trigger_gated_universal = {"vocabulary", "adr_decision_block"}
    always_include = universal_ids - trigger_gated_universal

    return _select_context_sections(diff, combined, always_include=always_include)


def _select_context_sections(diff: str, context_text: str, always_include: Optional[set[str]] = None) -> str:
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
        "vocabulary": _ADR_TRIGGERS,
        "adr_decision_block": _ADR_TRIGGERS,
    }

    # 2. Identify active sections
    if always_include is None:
        active_sections = {"micro_checks"}  # Fallback if always_include is not provided
    else:
        active_sections = set(always_include)
        active_sections.add("micro_checks")

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


def _get_active_context_sections(diff: str) -> str:
    """Helper to return only the active section names formatted as a string."""
    universal_content = ""
    if UNIVERSAL_CONTEXT_FILE.exists():
        try:
            universal_content = UNIVERSAL_CONTEXT_FILE.read_text(encoding="utf-8")
        except Exception:
            pass

    universal_ids = set(re.findall(r"<!-- SECTION:([\w_]+) -->", universal_content))
    trigger_gated_universal = {"vocabulary", "adr_decision_block"}
    always_include = universal_ids - trigger_gated_universal

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
        "vocabulary": _ADR_TRIGGERS,
        "adr_decision_block": _ADR_TRIGGERS,
    }

    active_sections = set(always_include)
    active_sections.add("micro_checks")

    for section_id, patterns in trigger_map.items():
        if any(p in diff for p in patterns):
            active_sections.add(section_id)

    return ",".join(sorted(active_sections))
