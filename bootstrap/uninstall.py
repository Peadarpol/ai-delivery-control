"""
AI Delivery Control — Framework Uninstall Utility
Cleanly removes all framework-owned files from a target project.
"""

import argparse
import sys
import fnmatch
from pathlib import Path

# Ensure UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bootstrap import manifest, checksums, generate_checksums

# Optional: SQLite state persistence row cleanup (T1-D-02). Non-fatal if unavailable.
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "scripts"))
    from state_persistence import cleanup_project_rows as _cleanup_project_rows  # type: ignore[import]
except ImportError:
    _cleanup_project_rows = None  # type: ignore[assignment]


def log_info(msg: str):
    print(f"ℹ️  {msg}")


def log_success(msg: str):
    print(f"✅ {msg}")


def log_warn(msg: str):
    print(f"⚠️  {msg}")


def log_error(msg: str):
    print(f"❌ {msg}", file=sys.stderr)


def _prompt(msg: str, dry_run: bool, force: bool) -> bool:
    """Prompt the user for confirmation; suppress in dry-run/force modes."""
    if dry_run:
        print(f"[DRY RUN] Would prompt: {msg}")
        return True
    if force:
        return True
    response = input(f"{msg} [y/N]: ").strip().lower()
    return response in ("y", "yes")


def _expand_framework_files(project_path: Path, framework_path: Path) -> list[Path]:
    """Expand FRAMEWORK_OWNED glob patterns relative to project_path."""
    matched = []
    for pattern in manifest.FRAMEWORK_OWNED:
        # Expand against both framework source (for reference) and target project
        for candidate in project_path.rglob("*"):
            if not candidate.is_file():
                continue
            rel = candidate.relative_to(project_path).as_posix()
            if fnmatch.fnmatch(rel, pattern):
                matched.append(candidate)
    # Also include MIGRATE_ON_UPGRADE files (config.yaml etc.)
    for rel in manifest.MIGRATE_ON_UPGRADE:
        p = project_path / rel
        if p.exists() and p.is_file():
            matched.append(p)
    # Deduplicate
    seen = set()
    result = []
    for p in matched:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


def _detect_developer_content(project_path: Path, dry_run: bool, force: bool) -> bool:
    """Check for developer-authored content and warn/prompt. Returns True to proceed."""
    warnings = []

    # Custom specs matching SPEC-\d+.md
    specs_dir = project_path / "docs" / "planning" / "specs"
    if specs_dir.exists():
        import re
        spec_files = [f for f in specs_dir.iterdir() if re.match(r"SPEC-\d+\.md$", f.name)]
        if spec_files:
            warnings.append(
                f"Found {len(spec_files)} developer-authored spec file(s) in docs/planning/specs/ "
                f"(e.g. {spec_files[0].name}). These are NOT framework files and will NOT be removed, "
                "but the .agent/ directory removal may affect them if they reference agent state."
            )

    # dream_proposals/ entries
    dream_dir = project_path / ".agent" / "state" / "dream_proposals"
    if dream_dir.exists() and any(dream_dir.iterdir()):
        warnings.append(
            "Found dream_proposals/ entries in .agent/state/. These are agent-generated proposals "
            "awaiting human review and will be removed with the framework."
        )

    # decisions_log.md additions
    decisions_log = project_path / ".agent" / "state" / "decisions_log.md"
    if decisions_log.exists():
        content = decisions_log.read_text(encoding="utf-8", errors="replace")
        # Count non-boilerplate entries (lines starting with ##)
        entries = [l for l in content.splitlines() if l.startswith("## ")]
        if entries:
            warnings.append(
                f"Found {len(entries)} architectural decision(s) in .agent/state/decisions_log.md. "
                "These will be removed with the framework. Back up this file if you want to preserve them."
            )

    if not warnings:
        return True

    print("\n" + "=" * 60)
    log_warn("Developer content detected in the project:")
    for w in warnings:
        print(f"  • {w}")
    print("=" * 60)

    return _prompt(
        "Developer-authored content was found (see above). Proceed with uninstall anyway?",
        dry_run=dry_run,
        force=force,
    )


def _check_checksum_modifications(project_path: Path, dry_run: bool, force: bool) -> bool:
    """Validate framework scripts/shims against installed checksums. Returns True to proceed."""
    state_file = project_path / ".agent" / ".framework_migration_state"
    if not state_file.exists():
        return True

    import json
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        installed_version = state.get("current_version", "")
    except Exception:
        return True

    version_key = f"V{installed_version.replace('.', '_')}"
    checksum_registry = getattr(checksums, version_key, {})
    if not checksum_registry:
        return True

    # Check shims and key framework files
    shim_rel_paths = ["CLAUDE.md", "GEMINI.md", ".cursorrules"]
    modified = []

    for rel in shim_rel_paths:
        target = project_path / rel
        if not target.exists():
            continue
        expected = checksum_registry.get(rel)
        if expected is None:
            continue
        actual = generate_checksums.compute_sha256(target)
        if actual != expected:
            modified.append(rel)

    if not modified:
        return True

    print("\n" + "=" * 60)
    log_warn("Customised framework files detected:")
    for rel in modified:
        print(f"  • {rel} (checksum differs from installed v{installed_version})")
    print("=" * 60)

    return _prompt(
        "Some framework files appear to have been customised (see above). Remove them anyway?",
        dry_run=dry_run,
        force=force,
    )


def _prune_precommit_hooks(project_path: Path, dry_run: bool):
    """Remove harness-owned hook entries from .pre-commit-config.yaml using exact ID matching."""
    precommit_path = project_path / ".pre-commit-config.yaml"
    if not precommit_path.exists():
        return

    content = precommit_path.read_text(encoding="utf-8")

    # Harness hook IDs to remove
    harness_hook_ids = {
        "ai-review-gate",
        "session-heartbeat",
        "governance-check",
        "check-skills-hygiene",
        "check-spec",
        "co-change-check",
        "enforce-hardened-schemas",
        "select-bdd-gate",
    }

    lines = content.splitlines(keepends=True)
    new_lines = []
    skip_block = False
    block_indent = None

    for line in lines:
        stripped = line.strip()

        # Detect the start of a hook entry (- id: <name>)
        if stripped.startswith("- id:"):
            hook_id = stripped.split(":", 1)[1].strip()
            if hook_id in harness_hook_ids:
                skip_block = True
                block_indent = len(line) - len(line.lstrip())
                continue
            else:
                skip_block = False
                block_indent = None

        if skip_block:
            current_indent = len(line) - len(line.lstrip()) if stripped else block_indent + 1
            # A non-empty line at same or lesser indent that isn't a child key ends the block
            if stripped and not stripped.startswith("-") and current_indent <= block_indent:
                skip_block = False
                block_indent = None
                new_lines.append(line)
            elif stripped.startswith("- ") and current_indent <= block_indent:
                skip_block = False
                block_indent = None
                new_lines.append(line)
            # else: still inside the hook block, skip
        else:
            new_lines.append(line)

    new_content = "".join(new_lines).strip()

    if dry_run:
        print(f"[DRY RUN] Would remove harness hook entries from .pre-commit-config.yaml")
        return

    if not new_content or new_content in ("repos: []", "repos:"):
        precommit_path.unlink()
        log_success("Removed empty .pre-commit-config.yaml.")
    else:
        precommit_path.write_text("".join(new_lines), encoding="utf-8")
        log_success("Pruned harness hook entries from .pre-commit-config.yaml.")


class UninstallManager:
    def __init__(self, project_path: Path, dry_run: bool = False, force: bool = False):
        self.project_path = project_path.resolve()
        self.framework_path = Path(__file__).resolve().parent.parent
        self.dry_run = dry_run
        self.force = force
        self.state_file = self.project_path / ".agent" / ".framework_migration_state"

    def _remove(self, path: Path):
        if self.dry_run:
            print(f"[DRY RUN] Would remove: {path.relative_to(self.project_path)}")
        else:
            try:
                path.unlink(missing_ok=True)
            except Exception as e:
                log_warn(f"Could not remove {path}: {e}")

    def run_uninstall(self):
        # Guard: require state file to confirm active installation
        if not self.state_file.exists():
            log_error(
                f"No .framework_migration_state found at {self.project_path / '.agent'}. "
                "This does not appear to be an active AI Delivery Control installation. "
                "If you are running from the ai-delivery-control repo itself, pass --project-path to target your project."
            )
            sys.exit(1)

        print("=" * 60)
        print("AI Delivery Control — Uninstall Utility")
        print("=" * 60)
        print(f"Project Path: {self.project_path}")
        if self.dry_run:
            print("🚀 DRY RUN MODE — No files will be deleted.")
        print("=" * 60)

        # 1. Check for developer-authored content
        if not _detect_developer_content(self.project_path, self.dry_run, self.force):
            log_info("Uninstall cancelled by user.")
            sys.exit(0)

        # 2. Check for customised framework files
        if not _check_checksum_modifications(self.project_path, self.dry_run, self.force):
            log_info("Uninstall cancelled by user.")
            sys.exit(0)

        # 3. Expand framework-owned files
        framework_files = _expand_framework_files(self.project_path, self.framework_path)
        log_info(f"Found {len(framework_files)} framework-owned file(s) to remove.")

        # 4. Remove framework-owned files
        removed = 0
        for fpath in framework_files:
            self._remove(fpath)
            removed += 1

        # 5. Prune pre-commit hooks
        _prune_precommit_hooks(self.project_path, self.dry_run)

        # 6. Remove stale migration backup if present
        backup = self.project_path / ".agent" / "config.yaml.migration_backup"
        if backup.exists():
            self._remove(backup)
            if not self.dry_run:
                log_success("Removed stale migration backup.")

        # 7. Remove state file last (its presence signals active installation)
        self._remove(self.state_file)

        # 8. Selective SQLite row-level cleanup
        if _cleanup_project_rows is not None:
            try:
                deleted = _cleanup_project_rows(project_root=str(self.project_path))
                if deleted and not self.dry_run:
                    log_success(f"Removed {deleted} SQLite row(s) for this project from ~/.aisdlc/harness.db.")
            except Exception as exc:
                log_warn(f"SQLite cleanup skipped: {exc}")
        elif not self.dry_run:
            log_info("SQLite state persistence not available — row cleanup skipped.")

        if self.dry_run:
            log_success(f"Dry run complete. Would have removed {removed} file(s).")
        else:
            log_success(
                f"Uninstall complete. {removed} framework file(s) removed. "
                "The framework is no longer active in this project."
            )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "AI Delivery Control Framework Uninstall Utility. "
            "Removes all framework-owned files from the target project. "
            "Run with --project-path to target a project other than the current directory."
        )
    )
    parser.add_argument(
        "--project-path",
        default=".",
        help="Target project root directory (default: current directory '.')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print what would be removed without deleting anything. "
            "Suppresses interactive prompts — safe for CI environments."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip all interactive confirmation prompts.",
    )

    args = parser.parse_args()

    # dry-run takes precedence over force when both are supplied
    dry_run = args.dry_run
    force = args.force and not dry_run

    project_path = Path(args.project_path).resolve()

    manager = UninstallManager(project_path=project_path, dry_run=dry_run, force=force)
    manager.run_uninstall()


if __name__ == "__main__":
    main()
