#!/usr/bin/env python3
"""
OWASP Checklist Validator

Interactive checklist for OWASP Top 10 compliance review.
Generates a security audit report.

Usage:
    poetry run python .agent/skills/security-audit/scripts/owasp_checklist.py
"""

import json
from datetime import datetime
from pathlib import Path

OWASP_TOP_10 = [
    {
        "id": "A01",
        "name": "Broken Access Control",
        "checks": [
            "All endpoints require authentication",
            "RBAC is properly implemented",
            "IDOR protection in place (can't access other users' data)",
            "CORS is properly configured",
            "JWT tokens are validated correctly",
        ],
    },
    {
        "id": "A02",
        "name": "Cryptographic Failures",
        "checks": [
            "Passwords hashed with bcrypt/Argon2",
            "Sensitive data encrypted at rest",
            "HTTPS enforced for all traffic",
            "No sensitive data in URLs or logs",
            "Secure random number generation used",
        ],
    },
    {
        "id": "A03",
        "name": "Injection",
        "checks": [
            "All database queries use parameterized statements",
            "No raw SQL with string concatenation",
            "Input validation on all user inputs",
            "ORM queries are injection-safe",
            "No shell command execution with user input",
        ],
    },
    {
        "id": "A04",
        "name": "Insecure Design",
        "checks": [
            "Rate limiting implemented",
            "Account lockout after failed attempts",
            "Secure password reset flow",
            "Multi-factor authentication available",
            "Security requirements documented",
        ],
    },
    {
        "id": "A05",
        "name": "Security Misconfiguration",
        "checks": [
            "Debug mode disabled in production",
            "Default credentials changed",
            "Error messages don't leak stack traces",
            "Unnecessary features disabled",
            "Security headers configured",
        ],
    },
    {
        "id": "A06",
        "name": "Vulnerable Components",
        "checks": [
            "Dependencies regularly updated",
            "Vulnerability scanning in CI/CD",
            "No known vulnerable packages",
            "Dependency versions pinned",
            "SBOM (Software Bill of Materials) maintained",
        ],
    },
    {
        "id": "A07",
        "name": "Authentication Failures",
        "checks": [
            "Strong password policy enforced",
            "Session tokens regenerated on login",
            "Sessions timeout after inactivity",
            "Secure session storage (HttpOnly, Secure cookies)",
            "Logout properly invalidates session",
        ],
    },
    {
        "id": "A08",
        "name": "Software and Data Integrity",
        "checks": [
            "CI/CD pipeline secured",
            "Code signing for releases",
            "Serialization vulnerabilities addressed",
            "Update mechanism secured",
            "Third-party integrations validated",
        ],
    },
    {
        "id": "A09",
        "name": "Security Logging and Monitoring",
        "checks": [
            "Failed login attempts logged",
            "Access control failures logged",
            "Logs protected from tampering",
            "Alerting for suspicious activity",
            "Audit trail for sensitive operations",
        ],
    },
    {
        "id": "A10",
        "name": "Server-Side Request Forgery (SSRF)",
        "checks": [
            "URL validation for user-provided URLs",
            "Allowlist for external services",
            "No raw URL fetching with user input",
            "DNS rebinding protection",
            "Internal network access restricted",
        ],
    },
]


def run_checklist():
    """Run interactive OWASP checklist."""
    print("=" * 60)
    print("OWASP TOP 10 SECURITY CHECKLIST")
    print("=" * 60)
    print("\nFor each item, enter:")
    print("  Y = Yes, implemented")
    print("  N = No, not implemented")
    print("  P = Partial / In progress")
    print("  S = Skip / Not applicable")
    print()

    results = []

    for category in OWASP_TOP_10:
        print(f"\n{'='*50}")
        print(f"{category['id']}: {category['name']}")
        print("=" * 50)

        category_results = {
            "id": category["id"],
            "name": category["name"],
            "checks": [],
        }

        for check in category["checks"]:
            while True:
                response = input(f"\n  {check}\n  [Y/N/P/S]: ").strip().upper()
                if response in ["Y", "N", "P", "S"]:
                    category_results["checks"].append(
                        {"description": check, "status": response}
                    )
                    break
                print("  Invalid input. Please enter Y, N, P, or S.")

        results.append(category_results)

    return results


def generate_report(results: list):
    """Generate security audit report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {"yes": 0, "no": 0, "partial": 0, "skipped": 0},
        "categories": results,
        "high_risk_items": [],
    }

    for category in results:
        for check in category["checks"]:
            status = check["status"]
            if status == "Y":
                report["summary"]["yes"] += 1
            elif status == "N":
                report["summary"]["no"] += 1
                report["high_risk_items"].append(
                    {"category": category["name"], "check": check["description"]}
                )
            elif status == "P":
                report["summary"]["partial"] += 1
            else:
                report["summary"]["skipped"] += 1

    return report


def print_summary(report: dict):
    """Print audit summary."""
    print("\n" + "=" * 60)
    print("SECURITY AUDIT SUMMARY")
    print("=" * 60)

    summary = report["summary"]
    total = sum(summary.values()) - summary["skipped"]
    if total > 0:
        score = (summary["yes"] + summary["partial"] * 0.5) / total * 100
    else:
        score = 0

    print(f"\n  ✅ Implemented: {summary['yes']}")
    print(f"  ⚠️  Partial:     {summary['partial']}")
    print(f"  ❌ Missing:     {summary['no']}")
    print(f"  ⏭️  Skipped:     {summary['skipped']}")
    print(f"\n  Security Score: {score:.1f}%")

    if report["high_risk_items"]:
        print(f"\n🔴 HIGH RISK ITEMS ({len(report['high_risk_items'])}):")
        for item in report["high_risk_items"]:
            print(f"    - [{item['category']}] {item['check']}")


def main():
    print("\nStarting OWASP Top 10 Security Audit...\n")
    print("This will guide you through a security checklist.")
    print("Press Ctrl+C to cancel at any time.\n")

    try:
        results = run_checklist()
        report = generate_report(results)
        print_summary(report)

        # Save report
        report_path = Path("security_audit_report.json")
        report_path.write_text(json.dumps(report, indent=2))
        print(f"\n📄 Full report saved to: {report_path}")

    except KeyboardInterrupt:
        print("\n\nAudit cancelled.")


if __name__ == "__main__":
    main()
