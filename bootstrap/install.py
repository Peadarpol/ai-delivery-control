#!/usr/bin/env python3
"""
AI Delivery Control — Bootstrap Install Script (T1-A-02)
Detects tech stack, copies harness files, scaffolds configs, and wires pre-commit hooks.
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


SYMBOL_ROCKET = _safe_symbol("🚀", "[START]")
SYMBOL_SUCCESS = _safe_symbol("✅", "[SUCCESS]")
SYMBOL_ERROR = _safe_symbol("❌", "[ERROR]")
SYMBOL_WARN = _safe_symbol("⚠️", "[WARNING]")
SYMBOL_INFO = _safe_symbol("ℹ️", "[INFO]")
SYMBOL_STEP = _safe_symbol("📦", "[STEP]")


class Installer:
    def __init__(
        self,
        project_path: str,
        package_manager_override: Optional[str] = None,
        test_framework_override: Optional[str] = None,
        language_override: Optional[str] = None,
        verbose: bool = False,
    ):
        self.project_path = Path(project_path).resolve()
        self.framework_path = Path(__file__).resolve().parent.parent
        self.verbose = verbose
        
        self.package_manager_override = package_manager_override
        self.test_framework_override = test_framework_override
        self.language_override = language_override
        
        # Detected properties
        self.project_name = self.project_path.name
        self.project_version = "0.1.0"
        self.language = "Python"
        self.package_manager = "poetry"
        self.test_framework = "pytest"
        self.src_path = "src"
        self.stack_pack = None

    def log(self, symbol: str, msg: str):
        print(f"{symbol} {msg}")

    def log_verbose(self, msg: str):
        if self.verbose:
            print(f"  [DEBUG] {msg}")

    def check_python_version(self):
        """Phase 2: Verify Python 3.9+ is available in the target environment."""
        self.log(SYMBOL_STEP, "Checking Python version requirements...")
        major, minor = sys.version_info.major, sys.version_info.minor
        if major < 3 or (major == 3 and minor < 9):
            self.log(
                SYMBOL_ERROR,
                f"Python version check failed: Python 3.9+ is required, but running {major}.{minor}.",
            )
            sys.exit(1)
        self.log(SYMBOL_SUCCESS, f"Python version requirement met: Python {major}.{minor} detected.")

    def detect_stack(self):
        """Phase 2: Detect the primary tech stack of the target project."""
        self.log(SYMBOL_STEP, "Detecting target project tech stack...")
        
        # 1. Project Directory Verification
        if not self.project_path.exists():
            self.log(SYMBOL_INFO, f"Project directory does not exist. Creating at {self.project_path}...")
            self.project_path.mkdir(parents=True, exist_ok=True)
            
        # Initialize bare git repository if it doesn't exist
        git_dir = self.project_path / ".git"
        if not git_dir.exists():
            self.log(SYMBOL_INFO, "Target project is not a git repository. Initializing git...")
            try:
                subprocess.run(["git", "init"], cwd=str(self.project_path), capture_output=True, check=True)
            except Exception as e:
                self.log(SYMBOL_WARN, f"Failed to initialize git repository: {e}")

        # 2. Parse package configurations & detect language
        pyproject_path = self.project_path / "pyproject.toml"
        package_json_path = self.project_path / "package.json"
        
        has_pyproject = pyproject_path.exists()
        has_package_json = package_json_path.exists()
        
        py_files_count = len(list(self.project_path.rglob("*.py")))
        js_ts_files_count = len(list(self.project_path.rglob("*.js"))) + len(list(self.project_path.rglob("*.ts")))
        
        if self.language_override:
            self.language = self.language_override
        else:
            if has_pyproject or py_files_count > js_ts_files_count:
                self.language = "Python"
            elif has_package_json or js_ts_files_count > py_files_count:
                self.language = "TypeScript" if list(self.project_path.rglob("*.ts")) else "JavaScript"
            else:
                self.language = "Python"  # Default fallback
                
        # 3. Detect Package Manager
        if self.package_manager_override:
            self.package_manager = self.package_manager_override
        else:
            if self.language in ["Python"]:
                if (self.project_path / "poetry.lock").exists() or has_pyproject:
                    self.package_manager = "poetry"
                elif (self.project_path / "Pipfile").exists():
                    self.package_manager = "pipenv"
                else:
                    self.package_manager = "pip"
            else:  # JS/TS
                if (self.project_path / "pnpm-lock.yaml").exists():
                    self.package_manager = "pnpm"
                elif (self.project_path / "yarn.lock").exists():
                    self.package_manager = "yarn"
                else:
                    self.package_manager = "npm"
                    
        # 4. Detect Test Framework
        if self.test_framework_override:
            self.test_framework = self.test_framework_override
        else:
            if self.language in ["Python"]:
                self.test_framework = "pytest"
            else:
                self.test_framework = "jest"
                
        # 5. Detect Source Root Folder
        possible_src_roots = ["src", "app", "lib", self.project_name.lower().replace("-", "_")]
        for root in possible_src_roots:
            if (self.project_path / root).exists() and (self.project_path / root).is_dir():
                self.src_path = root
                break
                
        # Parse project metadata from pyproject.toml / package.json
        if has_pyproject:
            try:
                content = pyproject_path.read_text(encoding="utf-8")
                # Simple parsing without toml dependency
                for line in content.splitlines():
                    if line.strip().startswith("name ="):
                        self.project_name = line.split("=")[1].strip().strip('"').strip("'")
                    if line.strip().startswith("version ="):
                        self.project_version = line.split("=")[1].strip().strip('"').strip("'")
            except Exception as e:
                self.log_verbose(f"Failed to read metadata from pyproject.toml: {e}")
        elif has_package_json:
            try:
                import json
                data = json.loads(package_json_path.read_text(encoding="utf-8"))
                self.project_name = data.get("name", self.project_name)
                self.project_version = data.get("version", self.project_version)
            except Exception as e:
                self.log_verbose(f"Failed to read metadata from package.json: {e}")

        # 6. Detect repo name from git remote URL
        self.detected_repo_name = self.project_name # Fallback
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                cwd=str(self.project_path)
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
                if repo_name:
                    self.detected_repo_name = repo_name
        except Exception as e:
            self.log_verbose(f"Failed to detect git remote origin repo name: {e}")

        # 7. Stack pack detection based on dependencies
        self.stack_pack = None
        if has_pyproject:
            try:
                content = pyproject_path.read_text(encoding="utf-8").lower()
                if "fastapi" in content:
                    self.stack_pack = "python-fastapi"
            except Exception as e:
                self.log_verbose(f"Failed to check for stack pack in pyproject.toml: {e}")
        
        if has_package_json and not self.stack_pack:
            try:
                content = package_json_path.read_text(encoding="utf-8").lower()
                if "express" in content:
                    self.stack_pack = "node-express"
            except Exception as e:
                self.log_verbose(f"Failed to check for stack pack in package.json: {e}")

        self.log(SYMBOL_SUCCESS, f"Detected Stack: Language={self.language}, PM={self.package_manager}, Test={self.test_framework}")
        self.log(SYMBOL_INFO, f"Scaffolding Metadata: Project={self.project_name} (v{self.project_version}), SrcRoot={self.src_path}/, Repo={self.detected_repo_name}")

    def copy_framework_files(self):
        """Phase 3: Exclude .agent/state/ entirely and copy only specific folders."""
        self.log(SYMBOL_STEP, "Copying harness framework files...")
        
        target_agent = self.project_path / ".agent"
        target_agent.mkdir(exist_ok=True)
        
        # Track target skills directory
        target_skills = target_agent / "skills"
        
        # Directories to copy from framework's .agent (excluding skills which is copied flat and non-destructively)
        agent_dirs_to_copy = ["scripts", "workflows", "evals", "templates"]
        for d in agent_dirs_to_copy:
            src_dir = self.framework_path / ".agent" / d
            dest_dir = target_agent / d
            if src_dir.exists() and src_dir.is_dir():
                self.log_verbose(f"Copying recursive: {src_dir} -> {dest_dir}")
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                shutil.copytree(src_dir, dest_dir)
        
        # Non-destructive flat skill copying
        if not target_skills.exists():
            target_skills.mkdir(parents=True, exist_ok=True)
        
        # Copy universal skills — skip if skill dir already exists in target
        src_universal_skills = self.framework_path / ".agent" / "skills" / "universal"
        if src_universal_skills.exists() and src_universal_skills.is_dir():
            self.log_verbose(f"Copying universal skills from {src_universal_skills} to {target_skills}")
            for item in src_universal_skills.iterdir():
                if item.is_dir():
                    # If stack pack is detected and matches this skill, skip so the stack pack copier installs it
                    if self.stack_pack and item.name == self.stack_pack:
                        self.log_verbose(f"Skipping legacy universal '{item.name}' copy because stack pack is detected.")
                        continue
                    
                    dest = target_skills / item.name
                    if dest.exists():
                        self.log(SYMBOL_INFO, f"Skill '{item.name}' already exists — skipping (use upgrade.py to update)")
                    else:
                        shutil.copytree(item, dest)

        # Copy stack pack if detected — skip if skill dir already exists in target
        if self.stack_pack:
            src_stack_pack = self.framework_path / ".agent" / "skills" / "stack-packs" / self.stack_pack
            if src_stack_pack.exists() and src_stack_pack.is_dir():
                dest = target_skills / self.stack_pack
                if dest.exists():
                    self.log(SYMBOL_INFO, f"Stack-pack skill '{self.stack_pack}' already exists — skipping (use upgrade.py to update)")
                else:
                    self.log(SYMBOL_SUCCESS, f"Detected matching stack pack: '{self.stack_pack}'. Installing...")
                    shutil.copytree(src_stack_pack, dest)
            else:
                self.log(SYMBOL_WARN, f"Stack pack '{self.stack_pack}' detected but not found in framework sources.")
        else:
            self.log(SYMBOL_INFO, "No matching stack pack detected for target tech stack. Skipping stack pack installation.")

        # Individual files to copy from framework's .agent
        agent_files_to_copy = ["governance.md", "AGENTS.md"]
        for f in agent_files_to_copy:
            src_file = self.framework_path / ".agent" / f
            dest_file = target_agent / f
            if src_file.exists() and src_file.is_file():
                self.log_verbose(f"Copying file: {src_file} -> {dest_file}")
                shutil.copy2(src_file, dest_file)

        # Idempotent copy for blocked_commands.md (preserve customizations)
        bc_src = self.framework_path / ".agent" / "blocked_commands.md"
        bc_dest = target_agent / "blocked_commands.md"
        if bc_src.exists() and bc_src.is_file():
            if bc_dest.exists():
                self.log_verbose("blocked_commands.md already exists — skipping (preserve customizations)")
            else:
                self.log_verbose(f"Copying file (idempotent): {bc_src} -> {bc_dest}")
                shutil.copy2(bc_src, bc_dest)

        # Seed correct repo name in check_repo.py
        check_repo_path = target_agent / "scripts" / "check_repo.py"
        if check_repo_path.exists():
            self.log_verbose(f"Seeding repo name '{self.detected_repo_name}' in {check_repo_path}")
            try:
                content = check_repo_path.read_text(encoding="utf-8")
                content = content.replace(
                    'EXPECTED_REPO = "ai-delivery-control"',
                    f'EXPECTED_REPO = "{self.detected_repo_name}"'
                )
                check_repo_path.write_text(content, encoding="utf-8")
            except Exception as e:
                self.log_verbose(f"Failed to seed repo name in check_repo.py: {e}")
                
        # Copy framework-owned scripts to project scripts folder
        scripts_dest_dir = self.project_path / self.src_path / "scripts"
        scripts_dest_dir.mkdir(parents=True, exist_ok=True)
        
        framework_scripts = [
            "ai_review.py",
            "providers.py",
            "roster_builder.py",
            "review_context_universal.md",
            "harness_utils.py",
            "gate_context.py",
            "capability_calibration.py",
            "state_persistence.py",
            "acceptance_hook.py",
        ]
        for script_name in framework_scripts:
            src_script = self.framework_path / "src" / "scripts" / script_name
            dest_script = scripts_dest_dir / script_name
            if src_script.exists():
                self.log_verbose(f"Copying framework script: {src_script} -> {dest_script}")
                shutil.copy2(src_script, dest_script)
            
        # Create empty dynamic state directories
        empty_dirs = [
            target_agent / "state",
            target_agent / "wiki",
            target_agent / "state" / "dream_proposals",
            target_agent / "config",
        ]
        for ed in empty_dirs:
            self.log_verbose(f"Ensuring empty directory exists: {ed}")
            ed.mkdir(parents=True, exist_ok=True)
            
        self.log(SYMBOL_SUCCESS, "Harness structure and scripts provisioned successfully.")

    def scaffold_configurations(self):
        """Phase 4: Render templates with substituted placeholders."""
        self.log(SYMBOL_STEP, "Scaffolding configuration files from templates...")
        
        templates_dir = self.framework_path / "bootstrap" / "templates"
        if not templates_dir.exists():
            self.log(SYMBOL_ERROR, f"Harness templates directory not found at {templates_dir}!")
            sys.exit(1)
            
        # Load framework version
        framework_version = "1.0.0"
        harness_version_txt = self.framework_path / "harness_version.txt"
        if harness_version_txt.exists():
            try:
                framework_version = harness_version_txt.read_text(encoding="utf-8").strip()
            except Exception as e:
                self.log_verbose(f"Failed to read harness_version.txt: {e}")

        # Render framework metadata block in yaml format
        today_date = datetime.date.today().isoformat()
        framework_yaml_block = f"""framework:
  version: "{framework_version}"
  repo: "https://github.com/Peadarpol/ai-delivery-control"
  installed_at: "{today_date}"
  local_path: null"""

        # Command runner setups
        pm_run_prefix = f"{self.package_manager} run " if self.package_manager in ["poetry", "pipenv", "npm", "pnpm", "yarn"] else ""
        if self.package_manager in ["npm", "pnpm", "yarn"]:
            test_run_all = f"{self.package_manager} test"
            test_run_unit = f"{self.package_manager} test -- --watchAll=false"
            linter_check = f"{self.package_manager} run lint"
            linter_fix = f"{self.package_manager} run lint -- --fix"
            linter_format = f"{self.package_manager} run format"
        else:  # Python
            test_run_all = f"{pm_run_prefix}pytest" if pm_run_prefix else "pytest"
            test_run_unit = f"{pm_run_prefix}pytest tests/unit" if pm_run_prefix else "pytest tests/unit"
            linter_check = f"{pm_run_prefix}ruff check" if pm_run_prefix else "ruff check"
            linter_fix = f"{pm_run_prefix}ruff check --fix" if pm_run_prefix else "ruff check --fix"
            linter_format = f"{pm_run_prefix}ruff format" if pm_run_prefix else "ruff format"

        # Placeholders mapping
        replacements = {
            "[PROJECT_NAME]": self.project_name,
            "[PROJECT_NAME_PLACEHOLDER]": self.project_name,
            "[PROJECT_VERSION]": self.project_version,
            "[FRAMEWORK_VERSION]": framework_version,
            "[INSTALL_DATE]": today_date,
            "[PROJECT_LANGUAGE]": self.language,
            "[PROJECT_PACKAGE_MANAGER]": self.package_manager,
            "[PROJECT_TEST_FRAMEWORK]": self.test_framework,
            "[PROJECT_SRC_PATH]": self.src_path,
            "[PROJECT_TYPE]": "service",
            "[PROJECT_CORE_FRAMEWORK]": "fastapi" if self.language == "Python" else "express",
            "[PROJECT_FRONTEND_FRAMEWORK]": "none",
            "[PROJECT_DB_ENGINE]": "postgresql",
            "[PROJECT_DB_MIGRATION_TOOL]": "alembic" if self.language == "Python" else "prisma",
            "[PROJECT_DB_NAME]": f"{self.project_name.lower().replace('-', '_')}_db",
            "[PROJECT_APP_NAME]": self.project_name.lower().replace("_", "-"),
            "[PROJECT_ENTRYPOINT_PLACEHOLDER]": "main.py" if self.language == "Python" else "index.js",
            "[TEST_RUN_ALL_COMMAND_PLACEHOLDER]": test_run_all,
            "[TEST_RUN_UNIT_COMMAND_PLACEHOLDER]": test_run_unit,
            "[TEST_RUN_INTEGRATION_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}pytest tests/integration" if self.package_manager in ["poetry", "pipenv"] else "pytest tests/integration",
            "[TEST_RUN_UI_COMMAND_PLACEHOLDER]": "playwright test",
            "[TEST_RUN_BDD_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}pytest tests/bdd" if self.package_manager in ["poetry", "pipenv"] else "pytest tests/bdd",
            "[TEST_COVERAGE_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}pytest --cov" if self.package_manager in ["poetry", "pipenv"] else "pytest --cov",
            "[TEST_MUTATION_COMMAND_PLACEHOLDER]": "mutmut run",
            "[TEST_TYPE_CHECK_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}mypy" if self.package_manager in ["poetry", "pipenv"] else "mypy",
            "[LINT_CHECK_COMMAND_PLACEHOLDER]": linter_check,
            "[LINT_FIX_COMMAND_PLACEHOLDER]": linter_fix,
            "[LINT_FORMAT_COMMAND_PLACEHOLDER]": linter_format,
            "[SECURITY_SCAN_SAST_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}bandit" if self.package_manager in ["poetry", "pipenv"] else "bandit",
            "[SECURITY_SCAN_DEPS_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}pip-audit" if self.package_manager in ["poetry", "pipenv"] else "pip-audit",
            "[RUN_BACKEND_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}uvicorn main:app --reload" if self.language == "Python" else "node index.js",
            "[RUN_FRONTEND_COMMAND_PLACEHOLDER]": "npm run dev",
            "[DB_MIGRATION_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}alembic upgrade head" if self.language == "Python" else "prisma migrate deploy",
            "[DB_ROLLBACK_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}alembic downgrade -1" if self.language == "Python" else "prisma migrate resolve",
            "[DB_GENERATE_MIGRATION_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}alembic revision --autogenerate" if self.language == "Python" else "prisma migrate dev",
            "[DB_SEED_COMMAND_PLACEHOLDER]": f"python -m scripts.seed" if self.language == "Python" else "prisma db seed",
            "[DB_STATUS_COMMAND_PLACEHOLDER]": f"{pm_run_prefix}alembic current" if self.language == "Python" else "prisma status",
        }

        # Render configurations helper
        def render_template(src_name: str, dest_path: Path, extra_replacements: Optional[Dict[str, str]] = None):
            src_file = templates_dir / src_name
            if not src_file.exists():
                self.log(SYMBOL_WARN, f"Template {src_name} not found, skipping...")
                return
                
            self.log_verbose(f"Rendering: {src_file} -> {dest_path}")
            content = src_file.read_text(encoding="utf-8")
            
            # Apply extra replacements if provided
            if extra_replacements:
                for k, v in extra_replacements.items():
                    content = content.replace(k, v)
                    
            # Apply base replacements
            for k, v in replacements.items():
                content = content.replace(k, v)
                    
            dest_path.write_text(content, encoding="utf-8")

        # 1. Generate .agent/UNIVERSAL_CONTEXT.md — always overwrite (machine-generated, version-stamped)
        universal_context_dest = self.project_path / ".agent" / "UNIVERSAL_CONTEXT.md"
        render_template("UNIVERSAL_CONTEXT.md.template", universal_context_dest)
        self.log(SYMBOL_SUCCESS, "Generated .agent/UNIVERSAL_CONTEXT.md (framework version stamped)")

        # 2. Generate tool shims — skip if developer has already customised them
        for shim_template, shim_dest_rel in [
            ("CLAUDE.md.template",   "CLAUDE.md"),
            ("GEMINI.md.template",   "GEMINI.md"),
            ("CLINE.md.template",    "CLINE.md"),
            ("cursorrules.template", ".cursorrules"),
        ]:
            shim_dest = self.project_path / shim_dest_rel
            if shim_dest.exists():
                self.log(SYMBOL_INFO, f"{shim_dest_rel} already exists — skipping (preserve developer customisations)")
            else:
                render_template(shim_template, shim_dest)
        
        # 3. Scaffold review_context_project.md co-located with ai_review.py
        project_context_path = self.project_path / self.src_path / "scripts" / "review_context_project.md"
        if not project_context_path.exists():
            render_template("review_context_project.md.template", project_context_path)
        else:
            self.log_verbose("review_context_project.md already exists, skipping scaffolding to preserve developer edits.")
        
        # 4. Scaffold skill_ownership.yaml
        render_template(
            "skill_ownership.yaml.template",
            self.project_path / ".agent" / "config" / "skill_ownership.yaml",
        )
        
        # 5. Scaffold config.yaml
        # Inject the parsed framework metadata section directly
        config_extra = {
            "# [PROJECT_NAME_PLACEHOLDER]": framework_yaml_block,
            "  # [DOMAIN_CONSTRAINTS_PLACEHOLDER]": "  - \"Multi-Tenant Isolation Guard\"\n  - \"Pre-commit AI review verification gating\"",
        }
        render_template("config.yaml.template", self.project_path / ".agent" / "config.yaml", config_extra)
        
        # 6. Scaffold pre-commit config (handling backups and cross-platform stripping)
        precommit_dest = self.project_path / ".pre-commit-config.yaml"
        if precommit_dest.exists():
            backup_path = self.project_path / ".pre-commit-config.yaml.bak"
            self.log(
                SYMBOL_WARN,
                f"Existing .pre-commit-config.yaml found! Backing up to {backup_path.name}",
            )
            if backup_path.exists():
                os.remove(backup_path)
            os.rename(precommit_dest, backup_path)
            
        # Render precommit
        render_template("pre-commit-config.yaml.template", precommit_dest)
        
        # Non-Windows dynamic command translation (strip cmd /c )
        if sys.platform != "win32":
            self.log(SYMBOL_INFO, "Non-Windows OS detected. Adapting pre-commit commands to Unix shell natively...")
            pc_content = precommit_dest.read_text(encoding="utf-8")
            # Replace cmd /c [PM] run with just [PM] run
            pc_content = pc_content.replace("cmd /c ", "")
            precommit_dest.write_text(pc_content, encoding="utf-8")
            
        self.log(SYMBOL_SUCCESS, "Configuration and supplementary context templates rendered.")
        
        # 7. Scaffold .ai-review-config.json if not present
        review_config_path = self.project_path / ".ai-review-config.json"
        if not review_config_path.exists():
            import json
            default_config = {
                "provider": "anthropic",
                "model": "claude-sonnet-4-6",
                "model_high_risk": "claude-opus-4-8",
                "timeout_seconds": 60
            }
            try:
                review_config_path.write_text(json.dumps(default_config, indent=2) + "\n", encoding="utf-8")
                self.log(SYMBOL_SUCCESS, "Generated default .ai-review-config.json overrides file.")
            except Exception as e:
                self.log(SYMBOL_WARN, f"Failed to write default .ai-review-config.json: {e}")

        # 8. Install Cline rules
        self.install_clinerules(replacements)

    def install_clinerules(self, replacements: Dict[str, str]):
        """Copy .clinerules template files and replace placeholders, skipping if exists."""
        self.log(SYMBOL_STEP, "Installing Cline rules (.clinerules/)...")
        src_dir = self.framework_path / "bootstrap" / "templates" / "clinerules"
        dest_dir = self.project_path / ".clinerules"
        
        if not src_dir.exists() or not src_dir.is_dir():
            self.log(SYMBOL_WARN, f"Cline rules templates directory not found at {src_dir} — skipping.")
            return

        dest_dir.mkdir(exist_ok=True)
        
        for item in src_dir.iterdir():
            if item.is_file() and item.suffix == ".md":
                dest_file = dest_dir / item.name
                if dest_file.exists():
                    self.log_verbose(f"Cline rule '{item.name}' already exists — skipping (preserve developer customizations)")
                else:
                    self.log_verbose(f"Rendering Cline rule: {item} -> {dest_file}")
                    try:
                        content = item.read_text(encoding="utf-8")
                        for k, v in replacements.items():
                            content = content.replace(k, v)
                        dest_file.write_text(content, encoding="utf-8")
                    except Exception as e:
                        self.log(SYMBOL_WARN, f"Failed to install Cline rule {item.name}: {e}")

    def update_gitignore(self):
        """Ensure harness operational state files and user logs are ignored by git."""
        self.log(SYMBOL_STEP, "Updating target project .gitignore...")
        gitignore_path = self.project_path / ".gitignore"

        # The clean, correct operational state block (BUG-10)
        required_entries = [
            ".agent/state/session.json",
            ".agent/state/HALT",
            ".agent/state/*.lock",
            ".agent/config.yaml.migration_backup",
            ".agent/wiki/",
            ".agent/state/gemini_session_close.json",
            ".clinerules/hooks/",
        ]

        if gitignore_path.exists():
            try:
                content = gitignore_path.read_text(encoding="utf-8")
                lines = content.splitlines()
            except Exception as e:
                self.log(SYMBOL_WARN, f"Failed to read .gitignore: {e}")
                lines = []
        else:
            lines = []

        # Idempotency check: check if `.agent/state/session.json` is already present
        is_already_present = any(".agent/state/session.json" == line.strip() for line in lines)
        if is_already_present:
            self.log(SYMBOL_SUCCESS, ".gitignore already contains harness exclusions (idempotent skip).")
            return

        # Append block
        header = "# AI Delivery Control — operational state (not project history)"
        if lines:
            lines.append("")
        lines.append(header)
        for entry in required_entries:
            lines.append(entry)

        try:
            gitignore_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.log(SYMBOL_SUCCESS, "Updated target project .gitignore with harness exclusions.")
        except Exception as e:
            self.log(SYMBOL_ERROR, f"Failed to write .gitignore: {e}")

    def wire_git_hooks(self):
        """Phase 5: Wire the git pre-commit hooks."""
        self.log(SYMBOL_STEP, "Wiring pre-commit hooks inside .git/hooks/...")
        
        try:
            # Verify git repo is present first
            if not (self.project_path / ".git").exists():
                self.log(SYMBOL_WARN, "No .git directory found. Skipping pre-commit hook installation.")
                return
                
            # Attempt to run pre-commit install
            # Check if pre-commit is available
            pc_cmd = "pre-commit"
            
            self.log_verbose("Executing 'pre-commit install' commands...")
            # Regular pre-commit hook
            res1 = subprocess.run(
                [pc_cmd, "install"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
            )
            # Commit-msg stage hook (required for AI review gate)
            res2 = subprocess.run(
                [pc_cmd, "install", "--hook-type", "commit-msg"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
            )
            # Pre-push stage hook (required for evals/behavior checks)
            res3 = subprocess.run(
                [pc_cmd, "install", "--hook-type", "pre-push"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
            )
            # Post-commit stage hook (required for session-heartbeat)
            res4 = subprocess.run(
                [pc_cmd, "install", "--hook-type", "post-commit"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
            )
            
            if res1.returncode == 0 and res2.returncode == 0 and res3.returncode == 0 and res4.returncode == 0:
                self.log(SYMBOL_SUCCESS, "Git pre-commit, commit-msg, pre-push, and post-commit hooks successfully wired.")
            else:
                self.log(
                    SYMBOL_WARN,
                    f"Pre-commit install completed with warnings.\n"
                    f"Stderr: {res1.stderr or res2.stderr or res3.stderr or res4.stderr}",
                )
        except Exception as e:
            self.log(
                SYMBOL_WARN,
                f"Failed to wire pre-commit hooks automatically: {e}.\n"
                f"Please manually install with: 'pre-commit install --install-hooks'",
            )

    def install_claude_hooks(self):
        """Write (or merge into) .claude/settings.json in the target project.

        Installs SessionStart and PreCompact hooks from the template. Idempotent —
        skips entries where the command string already appears in the existing config.
        """
        import json

        self.log(SYMBOL_STEP, "Installing Claude Code hook configuration (.claude/settings.json)...")

        template_path = self.framework_path / "bootstrap" / "templates" / "claude_settings_hooks.json"
        if not template_path.exists():
            self.log(SYMBOL_WARN, "claude_settings_hooks.json template not found — skipping Claude hook installation.")
            return

        try:
            hook_template = json.loads(template_path.read_text(encoding="utf-8"))
        except Exception as e:
            self.log(SYMBOL_WARN, f"Failed to read hook template: {e}")
            return

        claude_dir = self.project_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        settings_path = claude_dir / "settings.json"

        if settings_path.exists():
            try:
                existing = json.loads(settings_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        else:
            existing = {}

        existing.setdefault("hooks", {})
        added = []

        for event_name, new_matchers in hook_template.get("hooks", {}).items():
            existing["hooks"].setdefault(event_name, [])
            for matcher in new_matchers:
                for hook_entry in matcher.get("hooks", []):
                    cmd = hook_entry.get("command", "")
                    already_present = any(
                        h.get("command", "") == cmd
                        for m in existing["hooks"][event_name]
                        for h in m.get("hooks", [])
                    )
                    if already_present:
                        self.log_verbose(f"Hook already present for {event_name}: {cmd}")
                    else:
                        existing["hooks"][event_name].append(matcher)
                        added.append(f"{event_name}: {cmd}")
                        break  # one matcher per event entry

        try:
            settings_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        except Exception as e:
            self.log(SYMBOL_WARN, f"Failed to write .claude/settings.json: {e}")
            return

        if added:
            self.log(SYMBOL_SUCCESS, f"Claude Code hooks installed: {', '.join(added)}")
        else:
            self.log(SYMBOL_SUCCESS, ".claude/settings.json already contains required hooks (idempotent skip).")

    def run_validation(self):
        """Phase 6: Run bootstrap/validate.py to verify setup sanity."""
        self.log(SYMBOL_STEP, "Running post-install sanity validation...")
        
        validate_script = self.framework_path / "bootstrap" / "validate.py"
        if not validate_script.exists():
            self.log(SYMBOL_ERROR, "Validation script bootstrap/validate.py is missing!")
            sys.exit(1)
            
        try:
            result = subprocess.run(
                [sys.executable, str(validate_script), "--project-path", str(self.project_path)],
                capture_output=False, # Print directly to stdout/stderr
            )
            if result.returncode == 0:
                self.log(SYMBOL_SUCCESS, "Sanity validation passed successfully!")
            else:
                self.log(SYMBOL_ERROR, f"Sanity validation failed with exit code {result.returncode}.")
                sys.exit(result.returncode)
        except Exception as e:
            self.log(SYMBOL_ERROR, f"Error running validation: {e}")
            sys.exit(1)

    def run(self):
        print(f"==================================================")
        self.log(SYMBOL_ROCKET, "AI Delivery Control Harness Bootstrapper")
        print(f"==================================================")
        self.log(SYMBOL_INFO, f"Installer Directory: {self.framework_path}")
        self.log(SYMBOL_INFO, f"Target Project Path: {self.project_path}\n")
        
        self.check_python_version()
        self.detect_stack()
        self.copy_framework_files()
        self.scaffold_configurations()
        self.update_gitignore()
        self.install_claude_hooks()
        self.wire_git_hooks()
        self.run_validation()
        
        print(f"\n==================================================")
        self.log(SYMBOL_SUCCESS, "AI Delivery Control harness installation complete!")
        print(f"==================================================")
        
        if (self.project_path / ".pre-commit-config.yaml.bak").exists():
            print(f"\n{SYMBOL_WARN} Note: An existing pre-commit configuration was backed up to .pre-commit-config.yaml.bak.")
            print(f"  Please review and manually merge your existing hooks with the new harness hooks.")
        print(f"\n{SYMBOL_INFO} Next steps:")
        print(f"  1. Review your newly scaffolded configurations in .agent/config.yaml")
        print(f"  2. Add project-specific architectural principles to {self.src_path}/scripts/review_context_project.md")
        print(f"  3. Set ANTHROPIC_API_KEY environment variable to activate the Claude adversarial review gate.")
        print(f"==================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Bootstrap install AI Delivery Control harness.")
    parser.add_argument(
        "--project-path",
        default=".",
        help="Target project path to install the harness into (default: '.')",
    )
    parser.add_argument("--package-manager", help="Force specific package manager (poetry, pipenv, pip, npm, pnpm, yarn)")
    parser.add_argument("--test-framework", help="Force specific test framework (pytest, jest, vitest)")
    parser.add_argument("--language", help="Force specific language (Python, TypeScript, JavaScript)")
    parser.add_argument("--verbose", action="store_true", help="Print verbose/debug logging")
    
    args = parser.parse_args()
    
    installer = Installer(
        project_path=args.project_path,
        package_manager_override=args.package_manager,
        test_framework_override=args.test_framework,
        language_override=args.language,
        verbose=args.verbose,
    )
    installer.run()


if __name__ == "__main__":
    main()
