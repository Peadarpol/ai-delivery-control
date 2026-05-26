"""
AI Delivery Control — Framework Upgrade Manager (Component 2)
Handles the atomic upgrade workflow from older framework versions to v1.1.5.
"""

import argparse
import datetime
import difflib
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
from bootstrap import manifest, checksums, migration_base

def log_info(msg: str):
    print(f"ℹ️  {msg}")

def log_success(msg: str):
    print(f"✅ {msg}")

def log_warn(msg: str):
    print(f"⚠️  {msg}")

def log_error(msg: str):
    print(f"❌ {msg}", file=sys.stderr)

def parse_version_tuple(v_str: str) -> tuple[int, ...]:
    """Parse version string like '1.1.0' to integer tuple (1, 1, 0)."""
    return tuple(int(x) for x in v_str.split("."))

def format_version_var(version: str) -> str:
    """Format version string '1.1.0' to V_* variable name 'V1_1_0'."""
    return f"V{version.replace('.', '_')}"

def colorize_line(line: str) -> str:
    """Colorize diff lines if output is a TTY."""
    if not sys.stdout.isatty():
        return line
    if line.startswith("+") and not line.startswith("+++"):
        return f"\033[32m{line}\033[0m"
    elif line.startswith("-") and not line.startswith("---"):
        return f"\033[31m{line}\033[0m"
    elif line.startswith("@"):
        return f"\033[36m{line}\033[0m"
    return line

class UpgradeManager:
    def __init__(self, project_path: Path, dry_run: bool = False, force: bool = False, show_diff: bool = False):
        self.project_path = project_path.resolve()
        self.framework_path = Path(__file__).resolve().parent.parent
        self.dry_run = dry_run
        self.force = force
        self.show_diff = show_diff
        self.backup_path = self.project_path / ".agent_backup_upgrade"
        self.state_file_path = self.project_path / ".agent" / ".framework_migration_state"
        self.config_path = self.project_path / ".agent" / "config.yaml"
        self.target_version = "1.1.5"

    def validate_project(self):
        """Ensure the project directory carries an active .agent folder."""
        agent_dir = self.project_path / ".agent"
        if not agent_dir.exists() or not agent_dir.is_dir():
            log_error(f"Target directory {self.project_path} is not a valid AI Delivery Control project (missing .agent/).")
            sys.exit(1)

    def detect_installed_version(self) -> str:
        """Read the currently installed framework version from the state file, falling back to config.yaml."""
        if self.state_file_path.exists():
            try:
                state = json.loads(self.state_file_path.read_text(encoding="utf-8"))
                return state.get("current_version", "1.1.0")
            except Exception as e:
                log_warn(f"Failed to parse migration state file ({e}). Falling back to config.yaml.")
        
        if self.config_path.exists():
            try:
                content = self.config_path.read_text(encoding="utf-8")
                # Parse framework version using simple regex
                match = re.search(r"^\s*version:\s*\"([^\"]+)\"", content, re.MULTILINE)
                if match:
                    return match.group(1)
            except Exception as e:
                log_warn(f"Failed to parse config.yaml for version ({e}).")
        
        return "1.1.0" # Fallback baseline

    def discover_migrations(self) -> list[tuple[tuple[int, ...], tuple[int, ...], Path]]:
        """Scan bootstrap/migrations/ for modules implementing MigrationProtocol."""
        migrations_dir = self.framework_path / "bootstrap" / "migrations"
        if not migrations_dir.exists():
            return []
        
        discovered = []
        pattern = re.compile(r"^v(\d+)_(\d+)_(\d+)_to_v(\d+)_(\d+)_(\d+)\.py$")
        for file in migrations_dir.iterdir():
            match = pattern.match(file.name)
            if match:
                from_v = tuple(int(match.group(i)) for i in (1, 2, 3))
                to_v = tuple(int(match.group(i)) for i in (4, 5, 6))
                discovered.append((from_v, to_v, file))
        return discovered

    def load_migration_module(self, path: Path) -> migration_base.MigrationProtocol:
        """Import a migration module dynamically and validate it conforms to MigrationProtocol."""
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load migration module {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        if not isinstance(mod, migration_base.MigrationProtocol):
            raise TypeError(f"Module {path.name} does not conform to MigrationProtocol contract (missing required attributes or methods).")
        return mod

    def build_chain(self, installed_version: str) -> list[migration_base.MigrationProtocol]:
        """Build and validate the sorted migration chain from installed_version to v1.1.5."""
        raw_migrations = self.discover_migrations()
        
        # Verify duplicate from_version
        from_versions = [m[0] for m in raw_migrations]
        if len(from_versions) != len(set(from_versions)):
            seen = set()
            dups = []
            for fv in from_versions:
                if fv in seen:
                    dups.append(f"v{'.'.join(map(str, fv))}")
                seen.add(fv)
            raise ValueError(f"Ambiguous migration chain: two modules both start from {', '.join(dups)}.")
            
        migrations = []
        for from_v, to_v, path in raw_migrations:
            try:
                mod = self.load_migration_module(path)
                migrations.append((from_v, to_v, mod))
            except Exception as e:
                log_error(f"Failed to load migration {path.name}: {e}")
                raise
                
        migrations = sorted(migrations, key=lambda x: x[0])
        
        chain = []
        current = parse_version_tuple(installed_version)
        target = parse_version_tuple(self.target_version)
        
        if current == target:
            return []
            
        if current > target:
            raise ValueError(f"No migration path found from v{installed_version} to v{self.target_version}. Manual upgrade/downgrade required.")
            
        while current < target:
            step = None
            for from_v, to_v, mod in migrations:
                if from_v == current:
                    step = (from_v, to_v, mod)
                    break
            if not step:
                raise ValueError(f"No migration path found from v{'.'.join(map(str, current))} to v{self.target_version}. Manual upgrade required.")
            chain.append(step[2])
            current = step[1]
            
        return chain

    def expand_manifest_files(self) -> list[str]:
        """Collect all active framework files relative to project_path from manifest patterns."""
        # Use generate_checksums expand logic to locate all files currently in the framework
        from bootstrap import generate_checksums
        files = generate_checksums.expand_patterns(self.framework_path, manifest.FRAMEWORK_OWNED)
        return [f.as_posix() for f in files]

    def backup_project_files(self, manifest_files: list[str]):
        """Back up all existing framework-owned, config, and .gitignore files atomically."""
        if self.backup_path.exists():
            if not self.force:
                log_error("A previous upgrade backup exists at .agent_backup_upgrade/. This may be from a failed upgrade. Resolve it before proceeding.")
                sys.exit(1)
            else:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_rename = self.project_path / f".agent_backup_upgrade_{timestamp}"
                log_warn(f"Previous backup found! Renaming to {backup_rename.name} under --force option.")
                self.backup_path.rename(backup_rename)

        log_info("Executing atomic backup protocol...")
        self.backup_path.mkdir(parents=True)
        
        # Files to back up: all manifest framework files present in project, config.yaml, and .gitignore
        files_to_backup = [Path(f) for f in manifest_files]
        for config_rel in manifest.MIGRATE_ON_UPGRADE:
            files_to_backup.append(Path(config_rel))
        files_to_backup.append(Path(".gitignore"))
        
        backed_up_count = 0
        for rel_path in files_to_backup:
            source_file = self.project_path / rel_path
            if source_file.exists() and source_file.is_file():
                dest_file = self.backup_path / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, dest_file)
                backed_up_count += 1
                
        log_success(f"Backed up {backed_up_count} active project files to {self.backup_path.name}/.")

    def restore_backup(self):
        """Restore all backed-up files, completely reverting any partial installation changes."""
        if not self.backup_path.exists():
            log_warn("No backup folder found to restore!")
            return
            
        log_warn("Restoring original files from backup...")
        # Walk backup and copy back
        for root, _, files in os.walk(self.backup_path):
            for file in files:
                backup_file = Path(root) / file
                rel_path = backup_file.relative_to(self.backup_path)
                project_file = self.project_path / rel_path
                project_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, project_file)
        log_success("Restore complete. Project state fully reverted.")
        self.cleanup_backup()

    def cleanup_backup(self):
        """Delete the backup directory on a fully successful upgrade."""
        if self.backup_path.exists():
            shutil.rmtree(self.backup_path)
            log_info("Cleaned up upgrade backup directory.")

    def scan_unresolved_sidecars(self) -> list[Path]:
        """Scan project for any framework-generated sidecar conflict files."""
        sidecars = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if ".framework-v" in file:
                    sidecars.append(Path(root) / file)
        return sidecars

    def update_gitignore(self):
        """Ensure sidecars and the backup folder are properly registered in .gitignore."""
        gitignore_path = self.project_path / ".gitignore"
        required_entries = ["*.framework-v*", "/.agent_backup_upgrade/"]
        
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
            lines = content.splitlines()
        else:
            lines = []
            
        modified = False
        for entry in required_entries:
            # Check if entry is already present in any line
            if not any(entry == line.strip() for line in lines):
                lines.append(entry)
                modified = True
                
        if modified:
            gitignore_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            log_success("Updated .gitignore with sidecar and backup exclusions.")

    def run_upgrade(self):
        self.validate_project()
        installed_version = self.detect_installed_version()
        
        # 1. Scans sidecars and print warnings
        unresolved_sidecars = self.scan_unresolved_sidecars()
        
        # 2. Build migration chain
        try:
            chain = self.build_chain(installed_version)
        except ValueError as e:
            log_error(str(e))
            sys.exit(1)
            
        print(f"==================================================")
        print(f"AI Delivery Control — Upgrade Manager")
        print(f"==================================================")
        print(f"Project Path:      {self.project_path}")
        print(f"Detected Version:  v{installed_version}")
        print(f"Target Version:    v{self.target_version}")
        if self.dry_run:
            print("🚀 DRY RUN MODE — No writes will be made.")
        print(f"==================================================")
        
        if installed_version == self.target_version:
            log_success(f"Project is already at version {self.target_version}. Entering non-destructive verification pass.")
            if not self.dry_run:
                # Re-verify and update configurations cleanly
                self.update_gitignore()
                self.state_file_path.write_text(json.dumps({
                    "current_version": self.target_version,
                    "applied_migrations": [m[2].stem for m in self.discover_migrations()],
                    "last_upgraded": datetime.datetime.now().isoformat()
                }, indent=2), encoding="utf-8")
            return

        # 3. Analyze changes to categorize files
        manifest_files = self.expand_manifest_files()
        checksum_dict_name = format_version_var(installed_version)
        checksum_registry = getattr(checksums, checksum_dict_name, {})
        
        overwrites = []
        conflicts = []
        news = []
        skips = []
        
        for file_rel in manifest_files:
            src_file = self.framework_path / file_rel
            dest_file = self.project_path / file_rel
            
            if not src_file.exists():
                skips.append(file_rel)
                continue
                
            if not dest_file.exists():
                news.append(file_rel)
            else:
                if dest_file.is_dir():
                    # Directory conflict
                    conflicts.append(file_rel)
                    continue
                    
                # Read files and normalize line endings
                try:
                    from bootstrap import generate_checksums
                    dest_hash = generate_checksums.compute_sha256(dest_file)
                except Exception:
                    dest_hash = None
                    
                expected_hash = checksum_registry.get(file_rel)
                if expected_hash is not None and dest_hash == expected_hash:
                    overwrites.append(file_rel)
                else:
                    conflicts.append(file_rel)

        # Print Pre-Operation Report
        print("\n[PRE-OPERATION REPORT]")
        
        if chain:
            print("\nMIGRATION CHAIN TO APPLY:")
            for mod in chain:
                print(f"  - {mod.from_version} ➔ {mod.to_version} ({mod.__name__})")
                
        if news:
            print(f"\nNEW FILES TO PROVISION ({len(news)}):")
            for f in news:
                print(f"  + {f}")
                
        if overwrites:
            print(f"\nFILES TO OVERWRITE (Safe/Unmodified) ({len(overwrites)}):")
            for f in overwrites:
                print(f"  ✔ {f}")
                
        if skips:
            print(f"\nFILES REMOVED FROM FRAMEWORK (Skip) ({len(skips)}):")
            for f in skips:
                print(f"  - {f}")
                
        if conflicts:
            print(f"\nCONFLICTS DETECTED (Modified/Unknown) ({len(conflicts)}) (Sidecar written):")
            for f in conflicts:
                print(f"  ⚠️  {f}")
                
        if unresolved_sidecars:
            print(f"\nUNRESOLVED SIDECARS FOUND ({len(unresolved_sidecars)}):")
            for f in unresolved_sidecars:
                print(f"  • {f.relative_to(self.project_path)}")
                
        print("\n==================================================")
        
        # Prompt for confirmation
        if not self.force and not self.dry_run:
            response = input("Proceed with upgrade? [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                log_info("Upgrade cancelled by user.")
                sys.exit(0)
                
        if self.dry_run:
            log_success("Dry run completed cleanly. Zero changes written.")
            sys.exit(0)

        # 4. Perform atomic backup
        self.backup_project_files(manifest_files)
        
        try:
            # 5. Overwrite/Provision files
            for f in overwrites + news:
                src = self.framework_path / f
                dest = self.project_path / f
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                
            # Write conflict sidecars
            for f in conflicts:
                src = self.framework_path / f
                dest = self.project_path / f
                
                if dest.is_dir():
                    log_warn(f"Target '{f}' is a directory! Cannot write sidecar. Logged conflict.")
                    continue
                    
                sidecar_dest = dest.with_name(f"{dest.name}.framework-v{self.target_version}")
                shutil.copy2(src, sidecar_dest)
                log_warn(f"Conflict sidecar written: {sidecar_dest.relative_to(self.project_path)}")
                
                # Show diff if requested
                if self.show_diff:
                    print(f"\n[DIFF FOR CONFLICT: {f}]")
                    try:
                        dest_content = dest.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                        src_content = src.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                        diff = difflib.unified_diff(
                            dest_content, src_content,
                            fromfile=f"a/{f} (Local)",
                            tofile=f"b/{f} (Framework-v{self.target_version})"
                        )
                        for line in diff:
                            print(colorize_line(line), end="")
                        print()
                    except Exception as diff_err:
                        print(f"Failed to generate diff: {diff_err}")
                        
            # 6. Chain configurations migration
            for migration in chain:
                log_info(f"Running config migration: {migration.from_version} ➔ {migration.to_version}...")
                migration.migrate(self.config_path)
                
            # 7. Update gitignore & Write state file
            self.update_gitignore()
            
            applied_names = [m.__name__ for m in chain]
            state_data = {
                "current_version": self.target_version,
                "applied_migrations": applied_names,
                "last_upgraded": datetime.datetime.now().isoformat()
            }
            self.state_file_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
            
            # Clean up backup on complete success
            self.cleanup_backup()
            
            log_success(f"Framework upgrade to v{self.target_version} completed successfully!")
            
            if conflicts:
                print("\n==================================================")
                log_warn("Action Required: Conflicts were detected during the upgrade.")
                print("Please review and merge the *.framework-v* sidecar files, then delete them before making a commit.")
                print("==================================================\n")
                
        except Exception as e:
            log_error(f"Upgrade encountered an error: {e}")
            traceback.print_exc()
            self.restore_backup()
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="AI Delivery Control Framework Upgrade Utility")
    parser.add_argument("--project-path", default=".", help="Target project root directory (default: '.')")
    parser.add_argument("--dry-run", action="store_true", help="Print report without writing any changes")
    parser.add_argument("--force", action="store_true", help="Skip prompt and overwrite previous backups")
    parser.add_argument("--diff", action="store_true", help="Print unified color diffs for conflict files")
    
    args = parser.parse_args()
    project_path = Path(args.project_path).resolve()
    
    manager = UpgradeManager(
        project_path=project_path,
        dry_run=args.dry_run,
        force=args.force,
        show_diff=args.diff
    )
    manager.run_upgrade()

if __name__ == "__main__":
    main()
