"""
AI Delivery Control — Automated Onboarding Assistant (Component 4)
Runs environment diagnostics, reachability checks, test suites, and outputs a dated baseline report.
"""

import datetime
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

# Fix: Ensure UTF-8 encoding for stdout/stderr on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

def log_success(msg: str):
    """Log success helper."""
    print(f"✅ {msg}")

def get_cli_version(args: list[str]) -> str:
    """Run a CLI command and return its version output."""
    try:
        res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=True)
        # Extract first line of version info
        line = res.stdout.strip().splitlines()[0]
        return line
    except Exception:
        return "UNKNOWN"

def check_url_reachable(url: str, timeout: float = 3.0) -> bool:
    """Perform a lightweight HTTP GET request to check reachability."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200 or response.status == 204
    except Exception:
        # Some endpoints return 404 for root but are still reachable
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return True
        except Exception:
            return False

def main():
    print("==================================================")
    print("AI Delivery Control — Onboarding Diagnostic Tool")
    print("==================================================")
    
    project_root = Path.cwd()
    agent_dir = project_root / ".agent"
    if not agent_dir.exists():
        print("❌ Error: Onboarding must be run from the root of an active project (missing .agent/).")
        sys.exit(1)
        
    today_str = datetime.date.today().isoformat()
    project_name = project_root.name
    
    # 1. Environment & CLI Diagnostics
    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    git_ver = get_cli_version(["git", "--version"])
    pre_commit_ver = get_cli_version(["pre-commit", "--version"])
    
    print(f"Python:     {python_ver}")
    print(f"Git:        {git_ver}")
    print(f"Pre-commit: {pre_commit_ver}")
    
    # 2. Parse config.yaml
    scripts_path = Path(__file__).resolve().parent.parent.parent / "src" / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    from harness_utils import get_harness_config
    
    framework_version = get_harness_config("framework", "version", default="UNKNOWN")
    budget_provider = get_harness_config("model_routing", "budget_provider")
    budget_base_url = get_harness_config("model_routing", "budget_base_url")
            
    print(f"Framework:  v{framework_version}")
    print(f"Budget LMM: {budget_provider} ({budget_base_url})")

    # 3. Budget Provider Reachability Check
    reachability_status = "UNKNOWN"
    is_ollama = "ollama" in budget_provider.lower() or "localhost" in budget_base_url or "127.0.0.1" in budget_base_url
    is_cloud = "anthropic" in budget_provider.lower() or "openai" in budget_provider.lower() or "gemini" in budget_provider.lower()
    
    if is_ollama:
        print("\n🔍 Checking local budget provider reachability (Ollama)...")
        # Default Ollama URL fallback
        test_url = budget_base_url if budget_base_url != "UNKNOWN" else "http://localhost:11434"
        if check_url_reachable(test_url):
            reachability_status = "reachable"
            print("✅ Local budget provider reachable.")
        else:
            reachability_status = "UNREACHABLE"
            print(f"⚠️  Budget provider is not reachable at {test_url}")
            print("    wiki_compile.py will silently time out on every session start.")
            print("    Start Ollama (or correct budget_base_url in .agent/config.yaml) before proceeding.")
    elif is_cloud:
        reachability_status = "cloud-assumed"
        print(f"\nℹ️  Cloud budget provider configured ({budget_provider}).")
        print("    Reachability assumed — first use will incur API cost.")
    else:
        reachability_status = "skipped (unknown provider)"
        print(f"\nℹ️  Unknown/generic provider type '{budget_provider}'. Reachability check skipped.")

    # 4. Self-Test Verification (pytest)
    print("\n🔍 Running internal test suite...")
    test_run = subprocess.run([sys.executable, "-m", "pytest"], capture_output=True, text=True, encoding="utf-8")
    tests_passed = "UNKNOWN"
    tests_failed = "UNKNOWN"
    
    if test_run.returncode == 0:
        print("✅ All internal unit tests passed successfully.")
        # Parse test outcomes e.g. "83 passed in 0.85s"
        match = re.search(r"===+ (\d+) passed in", test_run.stdout)
        if match:
            tests_passed = match.group(1)
            tests_failed = "0"
    else:
        print("❌ Internal test suite failures detected!")
        # Try to parse counts
        passed_match = re.search(r"(\d+) passed", test_run.stdout)
        failed_match = re.search(r"(\d+) failed", test_run.stdout)
        tests_passed = passed_match.group(1) if passed_match else "0"
        tests_failed = failed_match.group(1) if failed_match else "1"

    # 5. Skill-specific validates
    print("\n🔍 Enumerating and executing skill-specific validation scripts...")
    skills_dir = agent_dir / "skills"
    skill_validations = []
    
    if skills_dir.exists():
        for root, _, files in os.walk(skills_dir):
            if "validate.py" in files:
                val_script = Path(root) / "validate.py"
                rel_val = val_script.relative_to(project_root)
                print(f"  Running: {rel_val}...")
                val_run = subprocess.run([sys.executable, str(val_script)], capture_output=True, text=True, encoding="utf-8")
                if val_run.returncode == 0:
                    skill_validations.append(f"{rel_val.parts[2]}={val_run.returncode} (PASSED)")
                else:
                    skill_validations.append(f"{rel_val.parts[2]}={val_run.returncode} (FAILED)")
                    
    skills_count = len(skill_validations)
    skills_passed = sum(1 for v in skill_validations if "PASSED" in v)
    print(f"✅ Skill Validations: {skills_passed}/{skills_count} passed.")

    # 6. Git Hook Integrity
    print("\n🔍 Checking git hooks integrity...")
    hooks_dir = project_root / ".git" / "hooks"
    pre_commit_ok = "missing"
    commit_msg_ok = "missing"
    pre_push_ok = "missing"
    
    if hooks_dir.exists():
        # Check files (Windows might have pre-commit or pre-commit.sample, we look for active files)
        # Note: on Windows git hooks don't have extensions
        if (hooks_dir / "pre-commit").exists():
            pre_commit_ok = "ok"
        if (hooks_dir / "commit-msg").exists():
            commit_msg_ok = "ok"
        if (hooks_dir / "pre-push").exists():
            pre_push_ok = "ok"
            
    print(f"pre-commit hook: {pre_commit_ok}")
    print(f"commit-msg hook: {commit_msg_ok}")
    print(f"pre-push hook:   {pre_push_ok}")

    # 7. Generate Onboarding Baseline Report
    baseline_dir = agent_dir / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    baseline_filename = f"onboarding_baseline_{today_str}.md"
    baseline_path = baseline_dir / baseline_filename
    
    baseline_content = f"""# Onboarding Baseline — {project_name} — {today_str}

This report establishes the baseline diagnostic capture for the AI Delivery Control harness.

## System Components
- **framework.version**: {framework_version}
- **python**: {python_ver}
- **git**: {git_ver}
- **pre-commit**: {pre_commit_ver}

## Diagnostics & Reachability
- **budget_provider**: {budget_provider} ({budget_base_url})
- **reachability**: {reachability_status}

## Verification Results
- **test_suite**: {tests_passed} passed, {tests_failed} failed
- **skill_validations**: {skills_passed}/{skills_count} passed
  - Details: {', '.join(skill_validations) if skill_validations else 'None'}

## Git Hooks Status
- **pre-commit**: {pre_commit_ok}
- **commit-msg**: {commit_msg_ok}
- **pre-push**: {pre_push_ok}
"""

    baseline_path.write_text(baseline_content, encoding="utf-8")
    print("\n==================================================")
    log_success(f"Generated Onboarding Baseline Report at .agent/baseline/{baseline_filename}")
    print("==================================================\n")

if __name__ == "__main__":
    main()
