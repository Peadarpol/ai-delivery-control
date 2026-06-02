#!/usr/bin/env python3
"""
wiki_compile.py — Harness Knowledge Base Compiler

Compiles ADRs and other architectural rules into a structured
wiki using a specified LLM provider (Ollama, Anthropic, Gemini).
Incremental compilation uses SHA-256 hashes.
Generates an index.md table of all domains automatically.

─────────────────────────────────────────────────────────────────────────────
⚠️ WARNING: PURE AST ROSTER COMPILATION
Roster sidecar compilation is a pure static AST parsing process with ZERO
LLM involvement. This avoids local LLM invocation, protects against
token leakage/costs, and executes under 50ms without any network calls.
─────────────────────────────────────────────────────────────────────────────
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import httpx
import yaml

# Ensure UTF-8 stdout/stderr on Windows

CONFIG_PATH = Path(".agent/config.yaml")
STATE_FILE = Path(".agent/state/wiki_compile_state.json")
WIKI_DIR = Path(".agent/wiki")

def load_domain_registry(config_path: "Path | None" = None) -> dict:
    """Load the wiki domain registry from .agent/config.yaml::wiki_domains.

    Each entry maps a domain name to a list of ADR source file paths.
    The output path is derived automatically as .agent/wiki/{domain}.md.

    Domains whose source files are ALL missing are silently skipped — no
    [FILE NOT FOUND] pages are compiled for absent ADRs. This makes the
    framework safe to install on projects that have not yet written their ADRs.

    Returns an empty dict when:
    - config.yaml is absent
    - the wiki_domains section is missing or empty
    - all configured domains have no existing source files
    """
    resolved_config = Path(config_path) if config_path else CONFIG_PATH
    if not resolved_config.exists():
        return {}

    try:
        with open(resolved_config, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception:
        return {}

    wiki_domains = raw.get("wiki_domains") or {}
    if not wiki_domains:
        return {}

    registry = {}
    for domain_name, sources in wiki_domains.items():
        if not isinstance(sources, list) or not sources:
            continue
        # Skip domains where every source file is missing
        existing = [s for s in sources if Path(s).exists()]
        if not existing:
            continue
        registry[domain_name] = {
            "sources": sources,          # keep full list; compile_domain handles per-file
            "output": f".agent/wiki/{domain_name}.md",
        }

    return registry


# Module-level constant populated from config for backward-compat imports
# (ai_review.py does: from wiki_compile import DOMAIN_REGISTRY)
DOMAIN_REGISTRY = load_domain_registry()

COMPILE_PROMPT = """You are compiling a concise wiki page for an AI code review system.

Source documents:
{source_content}

Produce a wiki page in this exact format (≤200 tokens total):

# {domain_title}
**Compiled**: {date}
**Sources**: {source_filenames}

## Summary
[2-3 sentences synthesising the architectural decision]

## Key Invariants
[3-5 bullet points — the rules agents must know]

## Enforcement
[Where/how this is enforced: file paths, function names, CI gates]

## Related Domains
[Cross-references to other wiki domains by name]

→ Full source: {source_paths}

Output only the wiki page. No preamble. No commentary."""

# Additional explicit prompt for multi-source domains
MULTI_SOURCE_PROMPT = """

IMPORTANT INSTRUCTION: You have been provided with MULTIPLE source documents.
You MUST synthesise these documents into a SINGLE coherent wiki page representing the evolution of the domain.
Do not concatenate them into separate entries. Ensure the resulting page reads as one unified set of rules."""


def get_hash(paths: list[str]) -> str:
    """Calculate a combined SHA-256 hash for a list of file paths."""
    h = hashlib.sha256()
    for p in sorted(paths):
        path_obj = Path(p)
        if path_obj.exists():
            h.update(path_obj.read_bytes())
        else:
            h.update(b"missing")
    return h.hexdigest()


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            return config.get("model_routing", {})
        except Exception:
            return {}
    return {}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)


def check_cloud_privacy_gate(provider: str, state: dict) -> None:
    if provider in ("anthropic", "gemini"):
        if not state.get("cloud_warning_acknowledged", False):
            print(f"\n⚠️  Wiki compilation is configured to use {provider} (cloud).")
            print("    Your ADR files will be sent to a cloud API.")
            print(
                "    Ensure this is acceptable for your project's data classification."
            )
            print(
                "\n    To use a local model instead: set wiki_compile_provider: ollama in .agent/config.yaml"
            )
            print(
                "    To acknowledge and proceed: this warning will not repeat after first run.\n"
            )
            state["cloud_warning_acknowledged"] = True


def generate_index_md(state: dict) -> None:
    """Dynamically generates .agent/wiki/index.md."""
    index_path = WIKI_DIR / "index.md"
    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Harness Knowledge Index",
        f"**Last compiled**: {state.get('last_run_utc', 'never')}",
        f"**Pages**: {state.get('domains_compiled', 0)} / {len(DOMAIN_REGISTRY)} ready",
        "",
        "## Domain Pages",
        "| Domain | File | Source | Status |",
        "|--------|------|--------|--------|",
    ]
    for domain, info in DOMAIN_REGISTRY.items():
        # Get basenames
        sources_str = ", ".join([Path(s).name for s in info["sources"]])
        out_file = Path(info["output"]).name
        status = "ready" if domain in state.get("last_source_hashes", {}) else "pending"
        lines.append(f"| {domain} | {out_file} | {sources_str} | {status} |")

    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def call_ollama(client: httpx.Client, prompt: str, routing: dict) -> str:
    url = f"{routing.get('budget_base_url', routing.get('local_base_url', 'http://localhost:11434')).rstrip('/')}/api/generate"
    payload = {
        "model": routing.get("budget_model", routing.get("local_model", "gemma4")),
        "prompt": prompt,
        "stream": False,
    }
    timeout_val = routing.get("budget_provider_timeout_seconds")
    timeout = float(timeout_val) if timeout_val is not None else 300.0
    resp = client.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def call_anthropic(client: httpx.Client, prompt: str, routing: dict) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": routing.get("review_model", routing.get("cloud_model", "claude-haiku-3-5")),
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = client.post(url, json=payload, headers=headers, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"].strip()


def call_gemini(client: httpx.Client, prompt: str, routing: dict) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    model = routing.get("cloud_model", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = client.post(url, json=payload, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def compile_domain(
    domain_name: str, info: dict, routing: dict, client: httpx.Client
) -> str:
    source_content = ""
    for p in info["sources"]:
        path_obj = Path(p)
        if path_obj.exists():
            source_content += f"\n--- {path_obj.name} ---\n"
            source_content += path_obj.read_text(encoding="utf-8")
        else:
            source_content += f"\n--- {path_obj.name} ---\n[FILE NOT FOUND]\n"

    from datetime import UTC, datetime

    now_str = datetime.now(UTC).strftime("%Y-%m-%d")

    prompt = COMPILE_PROMPT.format(
        source_content=source_content,
        domain_title=domain_name.replace("_", " ").title(),
        date=now_str,
        source_filenames=", ".join([Path(s).name for s in info["sources"]]),
        source_paths=", ".join(info["sources"]),
    )

    if len(info["sources"]) > 1:
        prompt += MULTI_SOURCE_PROMPT

    provider = routing.get("wiki_compile_provider", "ollama")

    if provider == "ollama":
        return call_ollama(client, prompt, routing)
    elif provider == "anthropic":
        return call_anthropic(client, prompt, routing)
    elif provider == "gemini":
        return call_gemini(client, prompt, routing)
    else:
        raise RuntimeError(f"Unknown provider: {provider}")


def main() -> None:
    # Ensure UTF-8 stdout/stderr on Windows
    if sys.platform == "win32":
        import io

        if hasattr(sys.stdout, "buffer") and "pytest" not in sys.modules:
            try:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
            except Exception:
                pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--domain", type=str)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    routing = load_config()
    state = load_state()
    if "last_source_hashes" not in state:
        state["last_source_hashes"] = {}

    provider = routing.get("wiki_compile_provider", "ollama")

    # Process inputs to see what changed
    to_compile = []

    if args.domain:
        if args.domain not in DOMAIN_REGISTRY:
            print(f"Error: domain {args.domain} not found.")
            sys.exit(1)
        targets = {args.domain: DOMAIN_REGISTRY[args.domain]}
    else:
        targets = DOMAIN_REGISTRY

    # Calculate hashes and identify stale domains
    for domain, info in targets.items():
        current_hash = get_hash(info["sources"])
        if args.force or state["last_source_hashes"].get(domain) != current_hash:
            to_compile.append((domain, info, current_hash))

    if not to_compile:
        # Just ensure the index exists and matches current state
        generate_index_md(state)
        print(
            f"Wiki compile: 0/{len(DOMAIN_REGISTRY)} pages updated ({len(DOMAIN_REGISTRY)} unchanged)."
        )
        sys.exit(0)

    print(
        f"Wiki compile: checking {len(to_compile)} / {len(DOMAIN_REGISTRY)} domains..."
    )

    if not args.dry_run:
        check_cloud_privacy_gate(provider, state)

    updated_count = 0

    from datetime import UTC, datetime

    now_utc = datetime.now(UTC).replace(tzinfo=None).isoformat() + "Z"

    # Wrap compilation in try/except for graceful failure
    try:
        with httpx.Client() as client:
            for domain, info, current_hash in to_compile:
                if args.dry_run:
                    print(f"[DRY-RUN] Would compile {domain} using {provider}")
                    continue

                content = compile_domain(domain, info, routing, client)

                WIKI_DIR.mkdir(parents=True, exist_ok=True)
                out_path = Path(info["output"])
                out_path.write_text(content, encoding="utf-8")

                state["last_source_hashes"][domain] = current_hash
                updated_count += 1

    except Exception:
        print(
            f"Wiki compile: {updated_count}/{len(DOMAIN_REGISTRY)} pages updated ({provider} unreachable — will retry next session)"
        )
        # Still update state for the ones that succeeded
        state["last_failure_utc"] = now_utc
        state["domains_compiled"] = len(state["last_source_hashes"])
        generate_index_md(state)
        save_state(state)
        sys.exit(0)

    if not args.dry_run:
        state["last_run_utc"] = now_utc
        state.pop("last_failure_utc", None)
        state["domains_compiled"] = len(state["last_source_hashes"])
        generate_index_md(state)
        save_state(state)

    # ── Shared AST Roster compilation ───────────────────────────────────────
    # We compile the mixin-aware ORM roster strictly via static AST analysis
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "scripts"))
        from roster_builder import build_branch_isolation_roster
        config_path = Path(".agent/config.yaml")
        patterns = ["src/**/models.py", "src/**/model.py"]
        base_classes = ["BranchAwareMixin", "BranchIsolatedMixin"]
        if config_path.exists():
            try:
                import yaml
                with open(config_path, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                bi_cfg = cfg.get("branch_isolation", {})
                patterns = bi_cfg.get("model_file_patterns", patterns)
                base_classes = bi_cfg.get("base_classes", base_classes)
            except Exception:
                pass
        
        roster = build_branch_isolation_roster(patterns, base_classes, Path.cwd())
        roster_path = Path(".agent/wiki/branch_isolation_roster.json")
        roster_path.parent.mkdir(parents=True, exist_ok=True)
        with open(roster_path, "w", encoding="utf-8") as f:
            json.dump(roster, f, indent=4)
        print(f"Wiki compile: branch_isolation_roster.json compiled ({len(roster)} models).")
    except Exception as e:
        print(f"⚠️  Wiki compile: Failed to compile branch isolation roster sidecar: {e}")

    unchanged = len(DOMAIN_REGISTRY) - updated_count
    print(
        f"Wiki compile: {updated_count}/{len(DOMAIN_REGISTRY)} pages updated ({unchanged} unchanged)."
    )


if __name__ == "__main__":
    main()
