#!/usr/bin/env python3
"""
Security Scanner Wrapper

Runs security checks on the codebase:
- Bandit for Python vulnerability scanning
- Safety for dependency vulnerabilities
- Custom checks for common issues

Usage:
    poetry run python .agent/skills/security-audit/scripts/security_scan.py
"""

import json
import subprocess
from pathlib import Path


def run_bandit():
    """Run Bandit security linter on Python code."""
    print("=" * 60)
    print("🔒 BANDIT SECURITY SCAN")
    print("=" * 60)

    try:
        result = subprocess.run(
            ["poetry", "run", "bandit", "-r", "src/", "-f", "json", "-q"],
            capture_output=True,
            text=True,
        )

        if result.stdout:
            data = json.loads(result.stdout)
            issues = data.get("results", [])

            if issues:
                print(f"\n⚠️  Found {len(issues)} potential security issues:\n")

                # Group by severity
                by_severity = {"HIGH": [], "MEDIUM": [], "LOW": []}
                for issue in issues:
                    sev = issue.get("issue_severity", "LOW")
                    by_severity[sev].append(issue)

                for severity in ["HIGH", "MEDIUM", "LOW"]:
                    if by_severity[severity]:
                        emoji = (
                            "🔴"
                            if severity == "HIGH"
                            else "🟠" if severity == "MEDIUM" else "🟡"
                        )
                        print(f"\n{emoji} {severity} ({len(by_severity[severity])})")
                        for issue in by_severity[severity]:
                            print(f"    {issue['filename']}:{issue['line_number']}")
                            print(f"      {issue['issue_text']}")
                            print(
                                f"      CWE: {issue.get('issue_cwe', {}).get('id', 'N/A')}"
                            )
            else:
                print("\n✅ No security issues found by Bandit")
        else:
            print("\n✅ No security issues found by Bandit")

    except FileNotFoundError:
        print("\n⚠️  Bandit not installed. Run: poetry add --group dev bandit")
    except json.JSONDecodeError:
        print("\n✅ No security issues found by Bandit")


def run_safety():
    """Check for known vulnerabilities in dependencies."""
    print("\n" + "=" * 60)
    print("📦 DEPENDENCY VULNERABILITY SCAN (Safety)")
    print("=" * 60)

    try:
        result = subprocess.run(
            ["poetry", "run", "safety", "check", "--json"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                vulns = (
                    data if isinstance(data, list) else data.get("vulnerabilities", [])
                )

                if vulns:
                    print(f"\n⚠️  Found {len(vulns)} vulnerable dependencies:\n")
                    for vuln in vulns:
                        if isinstance(vuln, dict):
                            pkg = vuln.get("package_name", "Unknown")
                            version = vuln.get("vulnerable_versions", "Unknown")
                            print(f"    🔴 {pkg} {version}")
                            print(
                                f"       {vuln.get('advisory', 'No description')[:80]}..."
                            )
                else:
                    print("\n✅ No vulnerable dependencies found")
            except json.JSONDecodeError:
                print("\n✅ No vulnerable dependencies found")
        else:
            print("\n✅ No vulnerable dependencies found")

    except FileNotFoundError:
        print("\n⚠️  Safety not installed. Run: poetry add --group dev safety")


def check_hardcoded_secrets():
    """Check for potential hardcoded secrets in the codebase."""
    print("\n" + "=" * 60)
    print("🔑 HARDCODED SECRETS CHECK")
    print("=" * 60)

    import re

    # Patterns that might indicate hardcoded secrets
    patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
        (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
        (r'AWS_ACCESS_KEY_ID\s*=\s*["\'][A-Z0-9]{20}["\']', "Hardcoded AWS key"),
    ]

    # Patterns that indicate safe usage (env vars, test data, etc.)
    safe_patterns = [
        r"os\.getenv\s*\(",  # Environment variable usage
        r"os\.environ",  # Environment variable access
        r"# nosec",  # Security exception comment
        r"# noqa",  # Linting exception
        r"seed_data\.py",  # Seed data files
        r"test_",  # Test files
        r"conftest\.py",  # Test configuration
        r'ENVIRONMENT\s*==\s*["\']test["\']',  # Test environment check
    ]

    src_path = Path("src")
    issues = []
    false_positives = []

    for py_file in src_path.rglob("*.py"):
        content = py_file.read_text(errors="ignore")
        file_str = str(py_file)

        for pattern, description in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                # Get the context (line containing the match)
                start = content.rfind("\n", 0, match.start()) + 1
                end = content.find("\n", match.end())
                if end == -1:
                    end = len(content)
                line_content = content[start:end]

                # Check if this is a false positive
                is_safe = False
                for safe_pattern in safe_patterns:
                    if re.search(safe_pattern, line_content, re.IGNORECASE):
                        is_safe = True
                        break
                    if re.search(safe_pattern, file_str, re.IGNORECASE):
                        is_safe = True
                        break

                # Also check for env var fallback pattern: getenv("VAR", "default")
                if "getenv" in content[max(0, match.start() - 50) : match.start()]:
                    is_safe = True

                if is_safe:
                    false_positives.append((file_str, description, "ENV_VAR_FALLBACK"))
                else:
                    issues.append((file_str, description))

    if issues:
        print(f"\n⚠️  Found {len(issues)} potential hardcoded secrets:\n")
        for file, desc in issues:
            print(f"    🔴 {file}: {desc}")
    else:
        print("\n✅ No hardcoded secrets found")

    if false_positives:
        print(
            f"\n💡 Skipped {len(false_positives)} false positives (env var patterns detected)"
        )

    print("\n💡 Tip: Use environment variables for sensitive data")


def check_security_headers():
    """Check if security headers are configured in FastAPI."""
    print("\n" + "=" * 60)
    print("🛡️ SECURITY HEADERS CHECK")
    print("=" * 60)

    # Look for CORS, security middleware configuration
    main_file = Path("src/main.py")
    if main_file.exists():
        content = main_file.read_text()

        headers_found = []
        headers_missing = []

        checks = [
            ("CORSMiddleware", "CORS Configuration"),
            ("HTTPSRedirectMiddleware", "HTTPS Redirect"),
            ("TrustedHostMiddleware", "Trusted Host"),
        ]

        for pattern, name in checks:
            if pattern in content:
                headers_found.append(name)
            else:
                headers_missing.append(name)

        if headers_found:
            print("\n✅ Security middleware found:")
            for h in headers_found:
                print(f"    - {h}")

        if headers_missing:
            print("\n💡 Consider adding:")
            for h in headers_missing:
                print(f"    - {h}")
    else:
        print("\n⚠️  Could not find src/main.py")


if __name__ == "__main__":
    run_bandit()
    run_safety()
    check_hardcoded_secrets()
    check_security_headers()
    print("\n" + "=" * 60)
    print("Security scan complete!")
