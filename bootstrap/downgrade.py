"""
AI Delivery Control — Framework Downgrade Utility (Component 3)
Reverts configuration changes and framework files back to v1.1.0 format.
"""

import argparse
import datetime
import importlib.util
import json
import os
import re
import shutil
import sys
import traceback
from pathlib import Path

# Ensure UTF-8 encoding for stdout/stderr on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Ensure we can import from the bootstrap package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bootstrap import manifest, migration_base

def log_info(msg: str):
    print(f"ℹ️  {msg}")

def log_success(msg: str):
    print(f"✅ {msg}")

def log_warn(msg: str):
    print(f"⚠️  {msg}")

def log_error(msg: str):
    print(f"❌ {msg}", file=sys.stderr)

def parse_version_tuple(v_str: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v_str.split("."))

class DowngradeManager:
    def __init__(self, project_path: Path, dry_run: bool = False, force: bool = False, to_version: str = "1.1.0"):
        self.project_path = project_path.resolve()
        self.framework_path = Path(__file__).resolve().parent.parent
        self.dry_run = dry_run
        self.force = force
        self.to_version = to_version
        self.backup_path = self.project_path / ".agent_backup_upgrade"
        self.state_file_path = self.project_path / ".agent" / ".framework_migration_state"
        self.config_path = self.project_path / ".agent" / "config.yaml"

    def validate_project(self):
        agent_dir = self.project_path / ".agent"
        if not agent_dir.exists() or not agent_dir.is_dir():
            log_error(f"Target directory {self.project_path} is not a valid AI Delivery Control project.")
            sys.exit(1)

    def detect_installed_version(self) -> str:
        if self.state_file_path.exists():
            try:
                state = json.loads(self.state_file_path.read_text(encoding="utf-8"))
                return state.get("current_version", "1.3.0")
            except Exception:
                pass
        
        if self.config_path.exists():
            try:
                content = self.config_path.read_text(encoding="utf-8")
                match = re.search(r"^[ \t]*framework:[ \t]*\r?\n(?:[ \t]*(?:#.*)?\r?\n)*[ \t]+version:[ \t]*\"([^\"]+)\"", content, re.MULTILINE)
                if match:
                    return match.group(1)
            except Exception:
                pass
        
        return "1.3.0"

    def discover_migrations(self) -> list[tuple[tuple[int, ...], tuple[int, ...], Path]]:
        migrations_dir = self.framework_path / "bootstrap" / "migrations"
        if not migrations_dir.exists():
            return []
        
        discovered = []
        for file in migrations_dir.iterdir():
            match = re.match(r"^v([\d_]+)_to_v([\d_]+)\.py$", file.name)
            if match:
                try:
                    mod = self.load_migration_module(file)
                    from_v = parse_version_tuple(mod.from_version)
                    to_v = parse_version_tuple(mod.to_version)
                    discovered.append((from_v, to_v, file))
                except Exception:
                    from_v = tuple(int(x) for x in match.group(1).split("_"))
                    to_v = tuple(int(x) for x in match.group(2).split("_"))
                    discovered.append((from_v, to_v, file))
        return discovered

    def load_migration_module(self, path: Path) -> migration_base.MigrationProtocol:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load migration module {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        if not isinstance(mod, migration_base.MigrationProtocol):
            raise TypeError(f"Module {path.name} does not conform to MigrationProtocol.")
        return mod

    def build_reverse_chain(self, current_version: str) -> list[migration_base.MigrationProtocol]:
        """Build and validate the migration chain in REVERSE from current_version to to_version."""
        raw_migrations = self.discover_migrations()
        
        # Verify duplicate from_version
        from_versions = [m[0] for m in raw_migrations]
        if len(from_versions) != len(set(from_versions)):
            raise ValueError("Ambiguous migration chain detected.")
            
        migrations = []
        for from_v, to_v, path in raw_migrations:
            mod = self.load_migration_module(path)
            migrations.append((from_v, to_v, mod))
            
        migrations = sorted(migrations, key=lambda x: x[0], reverse=True)
        
        chain = []
        current = parse_version_tuple(current_version)
        target = parse_version_tuple(self.to_version)
        
        if current == target:
            return []
            
        while current > target:
            step = None
            for from_v, to_v, mod in migrations:
                # In reverse, we search for step where to_v == current
                if to_v == current:
                    step = (from_v, to_v, mod)
                    break
            if not step:
                raise ValueError(f"No reverse migration path found from v{'.'.join(map(str, current))} to v{self.to_version}.")
            chain.append(step[2])
            current = step[0]
            
        return chain

    def run_downgrade(self, skip_preflight: bool = False):
        self.validate_project()
        current_version = self.detect_installed_version()

        # Stale backup guard — mirrors upgrade.py behaviour for full parity.
        config_migration_backup = self.config_path.with_suffix(".yaml.migration_backup")
        if config_migration_backup.exists():
            log_warn(
                "A backup from a previous failed migration was found. "
                "Review .agent/config.yaml before proceeding."
            )
            if not self.force:
                log_error(
                    "Stale migration backup detected. Resolve manually or pass --force to override."
                )
                sys.exit(1)
            else:
                log_warn("--force supplied. Overwriting stale migration backup.")

        try:
            chain = self.build_reverse_chain(current_version)
        except ValueError as e:
            log_error(str(e))
            sys.exit(1)
            
        print(f"==================================================")
        print(f"AI Delivery Control — Downgrade Utility")
        print(f"==================================================")
        print(f"Project Path:      {self.project_path}")
        print(f"Current Version:   v{current_version}")
        print(f"Target Version:    v{self.to_version}")
        if self.dry_run:
            print("🚀 DRY RUN MODE — No writes will be made.")
        print(f"==================================================")
        
        if current_version == self.to_version:
            log_info(f"Project is already at version {self.to_version}.")
            return
            
        if chain:
            print("\nMIGRATION CHAIN TO DOWNGRADE (REVERSE):")
            for mod in chain:
                print(f"  - {mod.to_version} ➔ {mod.from_version} (Downgrade: {mod.__name__})")
        else:
            log_warn("No downgrade chain resolved.")
            
        print("\n==================================================")
        
        if not self.force and not self.dry_run:
            response = input("Proceed with downgrade? [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                log_info("Downgrade cancelled by user.")
                sys.exit(0)
                
        if self.dry_run:
            log_success("Dry run completed cleanly. Zero changes written.")
            sys.exit(0)

        # 1. Atomic configuration downgrade — snapshot config.yaml before any module runs.
        #    Scope: covers config.yaml only. Framework file changes applied by downgrade()
        #    before an exception are not rolled back and may require manual remediation.
        if chain and self.config_path.exists():
            shutil.copy2(self.config_path, config_migration_backup)
        try:
            for migration in chain:
                log_info(f"Running config downgrade: {migration.to_version} ➔ {migration.from_version}...")
                migration.downgrade(self.config_path)
        except Exception as e:
            log_error(f"Failed to downgrade config.yaml: {e}. Restoring config.yaml from backup.")
            traceback.print_exc()
            if config_migration_backup.exists():
                shutil.copy2(config_migration_backup, self.config_path)
                config_migration_backup.unlink(missing_ok=True)
            sys.exit(1)
        if config_migration_backup.exists():
            config_migration_backup.unlink(missing_ok=True)

        # 2. File restore prioritization
        # Check priority 1: conflict sidecars *.framework-v*
        sidecars_deleted = 0
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if ".framework-v" in file:
                    sidecar_file = Path(root) / file
                    sidecar_file.unlink()
                    sidecars_deleted += 1
                    
        if sidecars_deleted > 0:
            log_success(f"Removed {sidecars_deleted} conflict sidecar files.")
            
        # Check priority 2: backup directory exists
        backup_restored = False
        if self.backup_path.exists():
            log_info("Restoring files from backup directory...")
            for root, _, files in os.walk(self.backup_path):
                for file in files:
                    backup_file = Path(root) / file
                    rel_path = backup_file.relative_to(self.backup_path)
                    project_file = self.project_path / rel_path
                    shutil.copy2(backup_file, project_file)
            shutil.rmtree(self.backup_path)
            backup_restored = True
            log_success("Restored framework files from .agent_backup_upgrade/.")

        # Check priority 3: Print explicit git recovery instructions
        if not backup_restored:
            print("\n⚠️  No sidecar or backup available for framework-owned files.")
            print("    The config.yaml has been reverted to v1.1.0 key names.")
            print("    To restore framework scripts, run:\n")
            print("      git checkout v1.1.0 -- .agent/scripts/ .agent/workflows/ .agent/skills/ .agent/governance.md .agent/AGENTS.md src/scripts/ai_review.py src/scripts/providers.py src/scripts/roster_builder.py src/scripts/review_context_universal.md\n")
            print("    If v1.1.0 is not a local tag, fetch it first: git fetch --tags\n")

        # 3. Update migration state file
        state_data = {
            "current_version": self.to_version,
            "applied_migrations": [],
            "last_upgraded": datetime.datetime.now().isoformat()
        }
        self.state_file_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
        
        log_success(f"Downgrade to version {self.to_version} completed successfully.")
        print("\nDowngrade restores config.yaml to v1.1.0 key names. Framework script files are only automatically restored if sidecars or backup are present — see above if neither is available.")

def main():
    parser = argparse.ArgumentParser(description="AI Delivery Control Framework Downgrade Utility")
    parser.add_argument("--project-path", default=".", help="Target project root directory (default: '.')")
    parser.add_argument("--dry-run", action="store_true", help="Print report without making any changes")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt and override stale backup block")
    parser.add_argument("--to-version", default="1.1.0", help="Target version to downgrade to (default: '1.1.0')")
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Bypass pre-flight checksum check (use when files are intentionally customised)",
    )

    args = parser.parse_args()
    project_path = Path(args.project_path).resolve()

    manager = DowngradeManager(
        project_path=project_path,
        dry_run=args.dry_run,
        force=args.force,
        to_version=args.to_version
    )
    manager.run_downgrade(skip_preflight=args.skip_preflight)

if __name__ == "__main__":
    main()
