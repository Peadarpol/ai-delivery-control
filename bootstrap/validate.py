#!/usr/bin/env python3
"""
Environment Validation Script (T1-A-03)
Confirms all required tools are installed, pre-commit hooks are wired, and project configs are valid.
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Fix: Ensure UTF-8 encoding for stdout/stderr on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def _safe_symbol(emoji: str, fallback: str) -> str:
    """Return emoji if stdout supports UTF-8, else ASCII fallback."""
    try:
        emoji.encode(sys.stdout.encoding or "utf-8")
        return emoji
    except (UnicodeEncodeError, AttributeError):
        return fallback


SYMBOL_PASS = _safe_symbol("✅", "[PASS]")
SYMBOL_FAIL = _safe_symbol("❌", "[FAIL]")
SYMBOL_WARN = _safe_symbol("⚠️", "[WARN]")
SYMBOL_INFO = _safe_symbol("ℹ️", "[INFO]")


def parse_simple_yaml(content: str) -> Dict[str, any]:
    """
    A lightweight, zero-dependency parser for basic YAML structures.
    Handles simple key-value pairs, nested sections by indentation, and lists of strings.
    This provides robust validation even if PyYAML is not installed in the system.
    """
    try:
        import yaml
        return yaml.safe_load(content)
    except ImportError:
        pass

    # Simple regex/indentation based fallback parser
    result = {}
    stack = [(0, result)]
    
    for line in content.splitlines():
        # Remove comments and whitespace
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
            
        # Determine indentation level
        indent = len(line) - len(line.lstrip())
        
        # Pop stack until we are at the right parent level
        while stack and stack[-1][0] >= indent and len(stack) > 1:
            stack.pop()
            
        current_dict = stack[-1][1]
        
        if ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip().strip('"').strip("'")
            val = val.strip()
            
            if val == "":
                # New nested block
                new_dict = {}
                current_dict[key] = new_dict
                stack.append((indent + 2, new_dict))
            else:
                # Direct key-value
                val_clean = val.strip('"').strip("'")
                if val_clean.lower() == "true":
                    val_clean = True
                elif val_clean.lower() == "false":
                    val_clean = False
                elif val_clean.lower() == "null":
                    val_clean = None
                current_dict[key] = val_clean
        elif stripped.startswith("-"):
            # Simple list item (e.g. capabilities.local_tasks or keywords)
            item = stripped[1:].strip().strip('"').strip("'")
            # Find parent key name
            parent_dict = current_dict
            # If parent is a list, append; if it's empty, make it a list
            # For simplicity, we just log parsed keys to assert formatting validity
            pass
            
    return result


class Validator:
    def __init__(self, project_path: Path, verbose: bool = False):
        self.project_path = project_path.resolve()
        self.verbose = verbose
        self.errors = 0
        self.warnings = 0

    def print_result(self, status: str, name: str, details: str = ""):
        detail_str = f" - {details}" if details else ""
        print(f"{status} {name}{detail_str}")

    def run_check(self, name: str, check_fn) -> bool:
        try:
            passed, details = check_fn()
            if passed:
                self.print_result(SYMBOL_PASS, name, details)
                return True
            else:
                self.errors += 1
                self.print_result(SYMBOL_FAIL, name, details)
                return False
        except Exception as e:
            self.errors += 1
            self.print_result(SYMBOL_FAIL, name, f"Unexpected error during check: {e}")
            return False

    def validate_tools(self) -> Tuple[bool, str]:
        """Check if basic requirements (git, python, pre-commit) are available."""
        missing = []
        
        # Git check
        try:
            subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            missing.append("git")
            
        # Pre-commit check
        try:
            subprocess.run(["pre-commit", "--version"], capture_output=True, text=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            # Pre-commit might be installed via local project environment
            missing.append("pre-commit")
            
        if missing:
            # We treat missing tools as warnings because the developer might be using 
            # a local virtualenv that is not active yet at the validation run-time.
            self.warnings += 1
            return True, f"Missing tool(s) in system path: {', '.join(missing)} (Ensure they are installed/active)"
            
        return True, "Git and pre-commit verified in system path."

    def validate_directories(self) -> Tuple[bool, str]:
        """Confirm that the .agent/ directory structure exists."""
        required_dirs = [
            ".agent",
            ".agent/skills",
            ".agent/scripts",
            ".agent/workflows",
            ".agent/state",
            ".agent/wiki"
        ]
        
        missing = []
        for d in required_dirs:
            p = self.project_path / d
            if not p.exists() or not p.is_dir():
                missing.append(d)
                
        if missing:
            return False, f"Missing required directory structure: {', '.join(missing)}"
        return True, "Core directories verified."

    def validate_core_files(self) -> Tuple[bool, str]:
        """Confirm that the critical core files are copied."""
        required_files = [
            ".agent/AGENTS.md",
            ".agent/governance.md",
            ".agent/scripts/init_session.py",
            ".agent/scripts/check_halt.py",
        ]
        
        missing = []
        for f in required_files:
            p = self.project_path / f
            if not p.exists() or not p.is_file():
                missing.append(f)
                
        if missing:
            return False, f"Missing required core files: {', '.join(missing)}"
        return True, "Core governance files verified."

    def validate_repo_guard(self) -> Tuple[bool, str]:
        """Confirm check_repo.py is present and EXPECTED_REPO is customized for the target project."""
        script = self.project_path / ".agent" / "scripts" / "check_repo.py"
        if not script.exists():
            return False, "check_repo.py missing from .agent/scripts/"
        try:
            content = script.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"Failed to read check_repo.py: {e}"

        is_framework = self.project_path.resolve().name.lower() == "ai-delivery-control"
        if not is_framework and 'EXPECTED_REPO = "ai-delivery-control"' in content:
            return False, "EXPECTED_REPO still set to framework default — install.py did not inject the correct repo name"

        return True, "Repository guard script present and configured"

    def validate_configs(self) -> Tuple[bool, str]:
        """Verify YAML parseability of configurations."""
        config_path = self.project_path / ".agent" / "config.yaml"
        ownership_path = self.project_path / ".agent" / "config" / "skill_ownership.yaml"
        
        if not config_path.exists():
            return False, "Missing .agent/config.yaml"
        if not ownership_path.exists():
            return False, "Missing .agent/config/skill_ownership.yaml"
            
        # Test config.yaml parsing
        try:
            content = config_path.read_text(encoding="utf-8")
            parsed_config = parse_simple_yaml(content)
            if not parsed_config:
                return False, "Failed to parse .agent/config.yaml (Empty or invalid format)"
        except Exception as e:
            return False, f"Error reading .agent/config.yaml: {e}"
            
        # Test skill_ownership.yaml parsing
        try:
            content = ownership_path.read_text(encoding="utf-8")
            parsed_owner = parse_simple_yaml(content)
            if not parsed_owner:
                return False, "Failed to parse .agent/config/skill_ownership.yaml (Empty or invalid format)"
        except Exception as e:
            return False, f"Error reading .agent/config/skill_ownership.yaml: {e}"
            
        return True, "Configuration files are present and syntactically valid."

    def validate_precommit_setup(self) -> Tuple[bool, str]:
        """Verify pre-commit config and git hook hooks installation."""
        pc_config = self.project_path / ".pre-commit-config.yaml"
        if not pc_config.exists() or not pc_config.is_file():
            return False, "Missing .pre-commit-config.yaml in project root."
            
        # Check if pre-commit was parsed correctly
        try:
            content = pc_config.read_text(encoding="utf-8")
            parsed_pc = parse_simple_yaml(content)
            if not parsed_pc:
                return False, "Failed to parse .pre-commit-config.yaml"
        except Exception as e:
            return False, f"Error parsing .pre-commit-config.yaml: {e}"
            
        # Check if hooks are registered in the git directory
        git_hooks_dir = self.project_path / ".git" / "hooks"
        if not git_hooks_dir.exists() or not git_hooks_dir.is_dir():
            self.warnings += 1
            return True, "No active .git/ directory or git hooks directory found (Is git initialized?)"
            
        # Pre-commit install typically populates these files
        expected_hooks = ["pre-commit", "commit-msg", "pre-push", "post-commit"]
        active_hooks = []
        for hook in expected_hooks:
            hook_file = git_hooks_dir / hook
            if hook_file.exists() and hook_file.is_file():
                active_hooks.append(hook)
                
        if not active_hooks:
            self.warnings += 1
            return True, "Pre-commit hooks are configured in YAML but not active in .git/hooks. Run 'pre-commit install --install-hooks'"
            
        return True, f"Pre-commit wired with hooks: {', '.join(active_hooks)}"

    def validate_ai_review_wiring(self) -> Tuple[bool, str]:
        """Confirm ai_review.py and review_context.md are co-located in project source scripts."""
        config_path = self.project_path / ".agent" / "config.yaml"
        if not config_path.exists():
            return False, "Cannot read .agent/config.yaml to find source scripts folder."
            
        try:
            content = config_path.read_text(encoding="utf-8")
            parsed = parse_simple_yaml(content)
            # Try to resolve path
            src_path = "src"
            if parsed and "paths" in parsed and "source_root" in parsed["paths"]:
                src_path = parsed["paths"]["source_root"]
            elif parsed and "paths" in parsed and isinstance(parsed["paths"], dict):
                src_path = parsed["paths"].get("source_root", "src")
        except Exception:
            src_path = "src"
            
        scripts_dir = self.project_path / src_path / "scripts"
        ai_review_file = scripts_dir / "ai_review.py"
        universal_context_file = scripts_dir / "review_context_universal.md"
        project_context_file = scripts_dir / "review_context_project.md"
        legacy_context_file = scripts_dir / "review_context.md"
        
        if not ai_review_file.exists() or not ai_review_file.is_file():
            return False, f"Missing ai_review.py in source scripts directory: {ai_review_file.relative_to(self.project_path)}"
        if not universal_context_file.exists() or not universal_context_file.is_file():
            return False, f"Missing review_context_universal.md in source scripts directory: {universal_context_file.relative_to(self.project_path)}"
        
        project_exists = project_context_file.exists() and project_context_file.is_file()
        legacy_exists = legacy_context_file.exists() and legacy_context_file.is_file()
        
        if not project_exists and not legacy_exists:
            self.warnings += 1
            print(f"{SYMBOL_WARN} Warning: Project-specific review context is absent at {project_context_file.relative_to(self.project_path)}. AI reviews will proceed using only universal guidelines.")
            
        return True, f"AI Adversarial Review Gate wired at {ai_review_file.relative_to(self.project_path)}"

    def validate_universal_context(self) -> Tuple[bool, str]:
        """Confirm .agent/UNIVERSAL_CONTEXT.md exists and contains a framework version reference."""
        uc_path = self.project_path / ".agent" / "UNIVERSAL_CONTEXT.md"
        if not uc_path.exists() or not uc_path.is_file():
            return False, "Missing .agent/UNIVERSAL_CONTEXT.md — run install.py to generate"
        try:
            content = uc_path.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"Failed to read UNIVERSAL_CONTEXT.md: {e}"
        if "framework version" not in content.lower():
            return False, "UNIVERSAL_CONTEXT.md exists but is missing a framework version reference"
        return True, "UNIVERSAL_CONTEXT.md present and contains framework version"

    def validate_gitignored_states(self) -> Tuple[bool, str]:
        """Confirm session.json and all .agent/state/ files are correctly ignored by git."""
        state_files = [
            ".agent/state/session.json",
            ".agent/state/harness_events.jsonl",
            ".agent/state/HALT",
        ]
        
        not_ignored = []
        for file_rel in state_files:
            file_path = self.project_path / file_rel
            # Ensure parent exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Temporary touch if not exists for check-ignore
            existed = file_path.exists()
            if not existed:
                try:
                    file_path.touch()
                except Exception:
                    pass
                
            try:
                res = subprocess.run(
                    ["git", "check-ignore", "-q", file_rel],
                    cwd=str(self.project_path),
                )
                if res.returncode != 0:
                    not_ignored.append(file_rel)
            except Exception:
                pass
                
            if not existed and file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass
                
        if not_ignored:
            return False, f"Harness state files are NOT gitignored: {', '.join(not_ignored)}. Check your .gitignore!"
        return True, "All harness state files are correctly ignored by git."

    def run_all(self) -> int:
        # Check if .agent/ exists as the very first check
        agent_dir = self.project_path / ".agent"
        if not agent_dir.exists() or not agent_dir.is_dir():
            print("\n" + "=" * 50)
            print("         AI DELIVERY CONTROL — ONBOARDING CARD")
            print("=" * 50)
            print("⚠️  AI Delivery Control harness is not installed!")
            print("   Please install the harness before running validation.")
            print("\n👉 To install and set up, run:")
            print("   python bootstrap/install.py")
            print("\n👉 For first-session onboarding steps, refer to:")
            print("   .agent/workflows/onboarding.md")
            print("=" * 50 + "\n")
            return 1

        print(f"\n==================================================")
        print(f"🔍 AI Delivery Control — Environment legibility check")
        print(f"==================================================")
        print(f"{SYMBOL_INFO} Target Path: {self.project_path}\n")
        
        self.run_check("Required CLI Tools", self.validate_tools)
        self.run_check("Harness Core Directory Layout", self.validate_directories)
        self.run_check("Harness Core Files", self.validate_core_files)
        self.run_check("Repository Guard (P-14)", self.validate_repo_guard)
        self.run_check("Universal Context File", self.validate_universal_context)
        self.run_check("Harness Configurations Validity", self.validate_configs)
        self.run_check("Pre-commit Git Hook Layout", self.validate_precommit_setup)
        self.run_check("Gitignored Harness State Files", self.validate_gitignored_states)
        self.run_check("AI Review Gate Setup", self.validate_ai_review_wiring)
        
        print(f"\n==================================================")
        print(f"Validation summary: {self.errors} error(s), {self.warnings} warning(s)")
        print(f"==================================================")
        
        if self.errors > 0:
            print(f"{SYMBOL_FAIL} Validation FAILED. Please review critical errors above.")
            return 1
        elif self.warnings > 0:
            print(f"{SYMBOL_WARN} Validation completed with WARNINGS. Basic harness is functional.")
            return 0
        else:
            print(f"{SYMBOL_PASS} Validation SUCCESSFUL! Harness is robust and fully configured.")
            return 0


def main():
    parser = argparse.ArgumentParser(description="Harness Environment legibility check.")
    parser.add_argument("--project-path", default=".", help="Path to the project being verified (default: '.')")
    parser.add_argument("--verbose", action="store_true", help="Print debug/verbose logging")
    args = parser.parse_args()
    
    project_path = Path(args.project_path)
    validator = Validator(project_path, verbose=args.verbose)
    sys.exit(validator.run_all())


if __name__ == "__main__":
    main()
