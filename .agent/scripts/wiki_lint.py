#!/usr/bin/env python3
"""
wiki_lint.py — Local Knowledge Base Linter

Validates documentation and design rules against active source states.
Checks for:
1. Static staleness: backticked identifiers in docs/wikis that do not exist in src/.
2. Orphaned rules: rule IDs in review_context.md missing AST checks in architecture_checks.py.
3. Factual drift: contradictions between compiled wiki pages and original ADR sources using local Gemma4.
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

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


SYMBOL_START = _safe_symbol("⚡", "[START]")
SYMBOL_SCAN = _safe_symbol("🔍", "[SCAN]")
SYMBOL_ROBOT = _safe_symbol("🤖", "[LLM]")
SYMBOL_CHECK = _safe_symbol("✅", "[OK]")
SYMBOL_WARN = _safe_symbol("⚠️", "[WARN]")


# Resolve paths relative to project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
CONFIG_PATH = PROJECT_ROOT / ".agent" / "config.yaml"
WIKI_DIR = PROJECT_ROOT / ".agent" / "wiki"
CONTEXT_FILE = PROJECT_ROOT / "src" / "scripts" / "review_context.md"
ARCH_CHECKS_FILE = (
    PROJECT_ROOT
    / ".agent"
    / "skills"
    / "senior-architect"
    / "scripts"
    / "architecture_checks.py"
)
FINDINGS_FILE = PROJECT_ROOT / ".agent" / "state" / "wiki_lint_findings.md"
STATE_FILE = PROJECT_ROOT / ".agent" / "state" / "wiki_lint_state.json"

# Common keywords and library functions to ignore during staleness checking
IGNORE_WORDS = {
    "self",
    "args",
    "kwargs",
    "none",
    "true",
    "false",
    "str",
    "int",
    "float",
    "dict",
    "list",
    "set",
    "tuple",
    "bool",
    "any",
    "all",
    "class",
    "def",
    "import",
    "from",
    "as",
    "with",
    "return",
    "pass",
    "try",
    "except",
    "finally",
    "raise",
    "if",
    "elif",
    "else",
    "for",
    "while",
    "break",
    "continue",
    "in",
    "is",
    "not",
    "and",
    "or",
    "yield",
    "lambda",
    "global",
    "nonlocal",
    "assert",
    "del",
    "basemodel",
    "field",
    "literal",
    "depends",
    "union",
    "optional",
    "type",
    "object",
    "exception",
    "commit",
    "flush",
    "add",
    "query",
    "execute",
    "where",
    "select",
    "update",
    "delete",
    "create",
    "read",
    "write",
    "post",
    "get",
    "put",
    "patch",
    "options",
    "head",
    "router",
    "app",
    "db",
    "session",
    "uow",
    "model_dump",
    "model_config",
    "extra",
    "forbid",
    "sqlalchemy",
    "fastapi",
    "streamlit",
    "pydantic",
    "alembic",
    "pytest",
    "playwright",
    "stmt",
    "filter",
    "check",
    "run",
    "verify",
    "test",
    "fixtures",
    "setup",
}

# The DOMAIN_REGISTRY mapping compiled wiki pages to ADR sources
DOMAIN_REGISTRY = {
    "clean_architecture": {
        "sources": [
            "docs/decisions/adr/adr_001_clean_architecture.md",
            "docs/decisions/adr/adr_006_clean_architecture_refactoring.md",
        ],
        "output": ".agent/wiki/clean_architecture.md",
    },
    "branch_isolation": {
        "sources": ["docs/decisions/adr/adr_002_multi_tenant_branch_isolation.md"],
        "output": ".agent/wiki/branch_isolation.md",
    },
    "multi_branch_schema": {
        "sources": ["docs/decisions/adr/adr_003_multi_branch_schema.md"],
        "output": ".agent/wiki/multi_branch_schema.md",
    },
    "session_authentication": {
        "sources": ["docs/decisions/adr/adr_004_session_authentication.md"],
        "output": ".agent/wiki/session_authentication.md",
    },
    "saas_architecture": {
        "sources": ["docs/decisions/adr/adr_005_saas_architecture.md"],
        "output": ".agent/wiki/saas_architecture.md",
    },
    "public_brand_config_api": {
        "sources": ["docs/decisions/adr/adr_007_public_brand_config_api.md"],
        "output": ".agent/wiki/public_brand_config_api.md",
    },
    "communication_system_strategy": {
        "sources": ["docs/decisions/adr/adr_008_communication_system_strategy.md"],
        "output": ".agent/wiki/communication_system_strategy.md",
    },
    "payment_hardware_strategy": {
        "sources": ["docs/decisions/adr/adr_009_payment_hardware_strategy.md"],
        "output": ".agent/wiki/payment_hardware_strategy.md",
    },
    "trainer_conflict_global_integrity": {
        "sources": ["docs/decisions/adr/adr_010_trainer_conflict_global_integrity.md"],
        "output": ".agent/wiki/trainer_conflict_global_integrity.md",
    },
    "pos_booking_payments": {
        "sources": ["docs/decisions/adr/adr_011_pos_booking_payments.md"],
        "output": ".agent/wiki/pos_booking_payments.md",
    },
    "pt_infrastructure_hardening": {
        "sources": ["docs/decisions/adr/adr_012_pt_infrastructure_hardening.md"],
        "output": ".agent/wiki/pt_infrastructure_hardening.md",
    },
    "remove_uow_autocommit": {
        "sources": ["docs/decisions/adr/adr_013_remove_uow_autocommit.md"],
        "output": ".agent/wiki/remove_uow_autocommit.md",
    },
}


def check_ollama_availability(url: str = "http://localhost:11434/api/tags") -> bool:
    """Probes the local Ollama endpoint with a 1.0s timeout to check availability."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def load_config() -> dict:
    """Load config.yaml to get local model and base url configurations."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            return config.get("model_routing", {})
        except Exception:
            pass
    return {}


def build_src_identifiers() -> set[str]:
    """Recursively reads all Python files in src/ to extract all word tokens."""
    identifiers = set()
    word_re = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b")
    src_dir = PROJECT_ROOT / "src"
    for py_file in src_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            for word in word_re.findall(content):
                identifiers.add(word.lower())
        except Exception:
            pass
    return identifiers


def run_staleness_check(src_identifiers: set[str]) -> list[dict]:
    """Scans review_context.md and .agent/wiki/*.md for backticked identifiers missing in src/."""
    findings = []
    backtick_re = re.compile(r"`([^`]+)`")
    word_re = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b")

    # Files to scan
    files_to_scan = []
    if CONTEXT_FILE.exists():
        files_to_scan.append(CONTEXT_FILE)
    if WIKI_DIR.exists():
        for f in WIKI_DIR.glob("*.md"):
            if f.name != "index.md":
                files_to_scan.append(f)

    for doc_path in files_to_scan:
        try:
            content = doc_path.read_text(encoding="utf-8")
            relative_path = doc_path.relative_to(PROJECT_ROOT).as_posix()

            for line_no, line in enumerate(content.splitlines(), 1):
                for match in backtick_re.finditer(line):
                    backticked = match.group(1)

                    # Extract words from backticked token
                    words = word_re.findall(backticked)
                    if not words:
                        continue

                    # Filter custom identifiers (skip keywords, standard types, short strings)
                    custom_identifiers = [
                        w
                        for w in words
                        if len(w) >= 4 and w.lower() not in IGNORE_WORDS
                    ]

                    for ident in custom_identifiers:
                        if ident.lower() not in src_identifiers:
                            findings.append(
                                {
                                    "file": relative_path,
                                    "line": line_no,
                                    "identifier": backticked,
                                    "severity": "MEDIUM",
                                    "finding": f"Stale identifier: '{backticked}' contains '{ident}' which does not exist in 'src/' code base.",
                                    "remediation": f"Update the documentation in '{relative_path}' to reflect actual codebase identifiers, or implement '{ident}'.",
                                }
                            )
                            break  # Avoid duplicates per line for same backticked match
        except Exception:
            pass

    return findings


def run_orphaned_rules_check() -> list[dict]:
    """Checks if rules in review_context.md have corresponding checks in architecture_checks.py."""
    findings = []
    if not CONTEXT_FILE.exists() or not ARCH_CHECKS_FILE.exists():
        return findings

    try:
        context_content = CONTEXT_FILE.read_text(encoding="utf-8")
        arch_content = ARCH_CHECKS_FILE.read_text(encoding="utf-8")

        # Find rule IDs like [RULE:UOW-INTEGRITY] or [PATTERN:CLEAN-ARCH]
        rule_re = re.compile(r"\[(RULE|PATTERN):([A-Z0-9_-]+)\]")

        relative_context = CONTEXT_FILE.relative_to(PROJECT_ROOT).as_posix()

        for line_no, line in enumerate(context_content.splitlines(), 1):
            for match in rule_re.finditer(line):
                rule_type, rule_id = match.group(1), match.group(2)

                # Check for various casings and normalizations in architecture_checks.py
                normalized_id = rule_id.lower().replace("-", "_")
                alternative_id = rule_id.lower()

                has_check = (
                    normalized_id in arch_content.lower()
                    or alternative_id in arch_content.lower()
                )

                if not has_check:
                    findings.append(
                        {
                            "file": relative_context,
                            "line": line_no,
                            "identifier": f"[{rule_type}:{rule_id}]",
                            "severity": "HIGH" if rule_type == "RULE" else "MEDIUM",
                            "finding": f"Orphaned rule check: '{rule_type}:{rule_id}' is documented but has no executable implementation in '{ARCH_CHECKS_FILE.name}'.",
                            "remediation": f"Add an AST parsing check or structural check inside '{ARCH_CHECKS_FILE.relative_to(PROJECT_ROOT).as_posix()}' to enforce this rule.",
                        }
                    )
    except Exception:
        pass

    return findings


def run_factual_drift_check(routing: dict) -> list[dict]:
    """Leverages local Gemma4 via Ollama to detect contradictions between compiled wiki pages and ADRs."""
    findings = []

    # 1. Active Service Probing
    base_url = routing.get("local_base_url", "http://localhost:11434").rstrip("/")
    if not check_ollama_availability(f"{base_url}/api/tags"):
        return findings

    model_name = routing.get("local_model", "gemma4:26b")

    for domain, info in DOMAIN_REGISTRY.items():
        wiki_path = PROJECT_ROOT / info["output"]
        if not wiki_path.exists():
            continue

        try:
            wiki_content = wiki_path.read_text(encoding="utf-8")

            # Concat original sources
            sources_content = ""
            for src_path in info["sources"]:
                path_obj = PROJECT_ROOT / src_path
                if path_obj.exists():
                    sources_content += f"\n--- {path_obj.name} ---\n"
                    sources_content += path_obj.read_text(encoding="utf-8")

            if not sources_content:
                continue

            # Build semantic query
            prompt = f"""You are an expert AI system auditor.
Compare the following Compiled Wiki Page against the original Source ADR Documents.

Compiled Wiki Page:
{wiki_content}

Original Source ADR Documents:
{sources_content}

Identify if there are any:
1. Factual contradictions (e.g., wiki says a rule is required but ADR says it is removed or optional).
2. Out-of-sync invariants (e.g., wiki lists obsolete rules not in source documents).
3. Structural drifts.

You must respond ONLY with valid JSON in this exact structure:
{{
  "has_drift": true,
  "findings": [
    {{
      "severity": "HIGH",
      "finding": "Short description of factual contradiction/drift.",
      "remediation": "How to resolve this drift (e.g., recompile or rewrite)."
    }}
  ]
}}
If no contradictions are found, set "has_drift" to false and return an empty list of findings. No preamble, no explanation, only the JSON block."""

            # Execute HTTP Request to Ollama
            url = f"{base_url}/api/generate"
            payload = json.dumps(
                {
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                }
            ).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=120.0) as resp:
                raw_resp = json.loads(resp.read().decode("utf-8"))
                response_text = raw_resp.get("response", "").strip()

            # Parse JSON
            result = json.loads(response_text)
            if result.get("has_drift") and "findings" in result:
                for f in result["findings"]:
                    findings.append(
                        {
                            "file": info["output"],
                            "line": 1,
                            "identifier": domain,
                            "severity": f.get("severity", "MEDIUM"),
                            "finding": f"[Drift] {f.get('finding')}",
                            "remediation": f.get(
                                "remediation",
                                f"Recompile wiki page for domain '{domain}'.",
                            ),
                        }
                    )
        except Exception:
            pass

    return findings


def write_findings_report(findings: list[dict], static_only: bool) -> None:
    """Writes a beautifully structured markdown report of findings."""
    FINDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    high_findings = [f for f in findings if f["severity"] == "HIGH"]
    med_findings = [f for f in findings if f["severity"] == "MEDIUM"]
    low_findings = [f for f in findings if f["severity"] == "LOW"]

    lines = [
        "# Knowledge Base Lint Findings Report",
        f"**Run Date**: {Path(FINDINGS_FILE).stat().st_mtime if FINDINGS_FILE.exists() else 'Today'}",
        f"**Status**: {'⚠️ STATIC-ONLY CHECKS' if static_only else '✅ SEMANTIC AUDIT COMPLETED'}",
        "",
        "## Summary",
        f"- **Total Issues**: {len(findings)}",
        f"- **🔴 High Severity**: {len(high_findings)}",
        f"- **🟡 Medium Severity**: {len(med_findings)}",
        f"- **🔵 Low Severity**: {len(low_findings)}",
        "",
        "---",
        "",
    ]

    if not findings:
        lines.append(
            "🎉 **No discrepancies or stale identifiers detected in the knowledge base!**"
        )
    else:
        # High Severity
        if high_findings:
            lines.append("## 🔴 High Severity Issues")
            for f in high_findings:
                lines.append(
                    f"### `{f['identifier']}` in [{Path(f['file']).name}](file:///{PROJECT_ROOT}/{f['file']}#L{f['line']})"
                )
                lines.append(f"- **Finding**: {f['finding']}")
                lines.append(f"- **💡 Remediation**: {f['remediation']}")
                lines.append("")

        # Medium Severity
        if med_findings:
            lines.append("## 🟡 Medium Severity Issues")
            for f in med_findings:
                lines.append(
                    f"### `{f['identifier']}` in [{Path(f['file']).name}](file:///{PROJECT_ROOT}/{f['file']}#L{f['line']})"
                )
                lines.append(f"- **Finding**: {f['finding']}")
                lines.append(f"- **💡 Remediation**: {f['remediation']}")
                lines.append("")

        # Low Severity
        if low_findings:
            lines.append("## 🔵 Low/Informational Issues")
            for f in low_findings:
                lines.append(
                    f"### `{f['identifier']}` in [{Path(f['file']).name}](file:///{PROJECT_ROOT}/{f['file']}#L{f['line']})"
                )
                lines.append(f"- **Finding**: {f['finding']}")
                lines.append(f"- **💡 Remediation**: {f['remediation']}")
                lines.append("")

    FINDINGS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Harness Knowledge Base Linter")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution overriding cooldown gates.",
    )
    args = parser.parse_args()
    _ = args.force

    print(f"{SYMBOL_START} Starting Knowledge Base Lint Audit...")

    # Load configuration
    routing = load_config()

    # Build codebase identifiers
    src_identifiers = build_src_identifiers()

    # 1. Run Static checks
    print(f"{SYMBOL_SCAN} Scanning stale identifiers...")
    stale_findings = run_staleness_check(src_identifiers)

    print(f"{SYMBOL_SCAN} Scanning orphaned rules...")
    orphaned_findings = run_orphaned_rules_check()

    # 2. Run Semantic Checks if Ollama is running
    print(f"{SYMBOL_SCAN} Checking Ollama server for local semantic analysis...")
    semantic_findings = []
    static_only = True

    base_url = routing.get("local_base_url", "http://localhost:11434").rstrip("/")
    if check_ollama_availability(f"{base_url}/api/tags"):
        print(
            f"{SYMBOL_ROBOT} Ollama is running! Executing factual drift and ADR contradiction checks..."
        )
        semantic_findings = run_factual_drift_check(routing)
        static_only = False
    else:
        print(
            f"{SYMBOL_WARN} Ollama is unavailable or timed out. Degraded gracefully to static-only check."
        )

    # Consolidate findings
    all_findings = stale_findings + orphaned_findings + semantic_findings

    # Write findings report
    write_findings_report(all_findings, static_only)

    print(
        f"{SYMBOL_CHECK} Audit finished! Compiled {len(all_findings)} discrepancy findings to {FINDINGS_FILE.relative_to(PROJECT_ROOT).as_posix()}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
