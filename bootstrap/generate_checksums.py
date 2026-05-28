"""
AI Delivery Control — Checksums Generator & Verifier (Component 2)
Computes and verifies SHA-256 digests for framework-owned files.
"""

import argparse
import glob
import hashlib
import importlib
import os
import re
import sys
from pathlib import Path

# Ensure we can import from the bootstrap package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bootstrap import manifest

def expand_patterns(root: Path, patterns: list[str]) -> list[Path]:
    """Recursively expand glob patterns relative to root, resolving directories fully."""
    files = []
    for pat in patterns:
        path_pat = root / pat
        # Expand glob pattern
        expanded_strs = glob.glob(str(path_pat), recursive=True)
        for p_str in expanded_strs:
            p = Path(p_str).resolve()
            if p.is_dir():
                # Recursively add all files under this directory
                for sub_p in p.rglob("*"):
                    if sub_p.is_file() and "__pycache__" not in sub_p.parts and ".git" not in sub_p.parts:
                        files.append(sub_p)
            elif p.is_file():
                if "__pycache__" not in p.parts and ".git" not in p.parts:
                    files.append(p)
    
    # Deduplicate and return paths relative to root, normalized to use forward slashes
    rel_files = sorted(list(set(f.relative_to(root) for f in files)))
    return rel_files

def compute_sha256(file_path: Path) -> str:
    """Read a file as UTF-8, normalize CRLF to LF, and compute the SHA-256 digest."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        normalized = content.replace("\r\n", "\n")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    except Exception as e:
        print(f"Error reading/hashing file {file_path}: {e}", file=sys.stderr)
        raise

def format_version_var(version: str) -> str:
    """Format version string '1.1.0' to variable name suffix '1_1_0'."""
    return version.replace(".", "_")

def get_migrations_versions(bootstrap_dir: Path) -> list[str]:
    """Scan bootstrap/migrations/ for files matching vX_X_X_to_vX_X_X.py and extract versions."""
    migrations_dir = bootstrap_dir / "migrations"
    if not migrations_dir.exists():
        return []
    
    versions = set()
    pattern = re.compile(r"^v(\d+)_(\d+)_(\d+)_to_v(\d+)_(\d+)_(\d+)\.py$")
    for file in migrations_dir.iterdir():
        match = pattern.match(file.name)
        if match:
            # Reconstruct from_version e.g. "1.1.0"
            from_v = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
            to_v = f"{match.group(4)}.{match.group(5)}.{match.group(6)}"
            versions.add(from_v)
            versions.add(to_v)
    return sorted(list(versions))

def run_generate(version: str, framework_root: Path, bootstrap_dir: Path):
    """Generate SHA-256 digests for version and write back to checksums.py."""
    print(f"Generating checksums for version {version} from {framework_root}...")
    
    files = expand_patterns(framework_root, manifest.FRAMEWORK_OWNED)
    if not files:
        print(f"Error: No framework files found under {framework_root} for generation!", file=sys.stderr)
        sys.exit(1)
        
    version_digests = {}
    for f in files:
        full_path = framework_root / f
        digest = compute_sha256(full_path)
        version_digests[f.as_posix()] = digest
        
    print(f"Hashed {len(version_digests)} framework files.")
    
    # Load existing versions from checksums.py if possible
    all_versions = {}
    checksums_path = bootstrap_dir / "checksums.py"
    if checksums_path.exists():
        try:
            importlib.invalidate_caches()
            from bootstrap import checksums
            for name in dir(checksums):
                if name.startswith("V") and isinstance(getattr(checksums, name), dict):
                    all_versions[name] = getattr(checksums, name)
        except Exception as e:
            print(f"Warning: Could not read existing checksums.py ({e}). Creating new file.", file=sys.stderr)
            
    # Inject/Overwrite current version
    version_var = f"V{format_version_var(version)}"
    all_versions[version_var] = version_digests
    
    # Ensure always having V1_1_0, V1_1_5, V1_1_5_1 and V1_1_5_2 initialized as dicts if missing
    if "V1_1_0" not in all_versions:
        all_versions["V1_1_0"] = {}
    if "V1_1_5" not in all_versions:
        all_versions["V1_1_5"] = {}
    if "V1_1_5_1" not in all_versions:
        all_versions["V1_1_5_1"] = {}
    if "V1_1_5_2" not in all_versions:
        all_versions["V1_1_5_2"] = {}

    # Write out to checksums.py
    with open(checksums_path, "w", encoding="utf-8", newline="\n") as f:
        f.write('"""\nAI Delivery Control — Framework File Checksums Registry (Component 2)\n'
                'Contains SHA-256 digests of framework-owned files for conflict detection.\n'
                'This file is generated automatically by generate_checksums.py.\n"""\n\n')
        for v_name in sorted(all_versions.keys()):
            v_dict = all_versions[v_name]
            f.write(f"{v_name} = {{\n")
            for file_rel, digest in sorted(v_dict.items()):
                safe_rel = str(file_rel).replace("'", "\\'")
                f.write(f"    '{safe_rel}': '{digest}',\n")
            f.write("}\n\n")
            
    print(f"Successfully wrote checksums to {checksums_path}")

def run_verify(framework_root: Path, bootstrap_dir: Path):
    """Verify checksum matches and check non-empty assertion on referenced versions."""
    print("Verifying framework checksums...")
    checksums_path = bootstrap_dir / "checksums.py"
    if not checksums_path.exists():
        print(f"Error: {checksums_path} does not exist!", file=sys.stderr)
        sys.exit(1)
        
    try:
        importlib.invalidate_caches()
        from bootstrap import checksums
    except Exception as e:
        print(f"Error: Failed to import bootstrap.checksums ({e})", file=sys.stderr)
        sys.exit(1)
        
    # Check 1: Digest match against what is currently on disk for V1_1_5_2
    v1_1_5_2_var = "V1_1_5_2"
    if not hasattr(checksums, v1_1_5_2_var):
        print(f"Error: {v1_1_5_2_var} not found in checksums.py!", file=sys.stderr)
        sys.exit(1)
        
    v1_1_5_2_dict = getattr(checksums, v1_1_5_2_var)
    current_files = expand_patterns(framework_root, manifest.FRAMEWORK_OWNED)
    
    # Calculate digests on disk and compare
    failures = 0
    checked = 0
    for f in current_files:
        rel_path = f.as_posix()
        full_path = framework_root / f
        current_digest = compute_sha256(full_path)
        
        expected_digest = v1_1_5_2_dict.get(rel_path)
        if expected_digest is None:
            print(f"MISMATCH: File '{rel_path}' exists on disk but is not recorded in {v1_1_5_2_var} checksums.", file=sys.stderr)
            failures += 1
        elif current_digest != expected_digest:
            print(f"MISMATCH: File '{rel_path}' digest on disk ({current_digest}) does not match recorded ({expected_digest}).", file=sys.stderr)
            failures += 1
        else:
            checked += 1
            
    # Check if files in checksum dict are missing on disk
    for rel_path in v1_1_5_2_dict.keys():
        full_path = framework_root / rel_path
        if not full_path.exists():
            print(f"MISMATCH: File '{rel_path}' recorded in {v1_1_5_2_var} but does not exist on disk.", file=sys.stderr)
            failures += 1
            
    # Check 2: Non-empty assertion for versions referenced in migration chain
    referenced_versions = get_migrations_versions(bootstrap_dir)
    print(f"Migration chain references versions: {referenced_versions}")
    for ver in referenced_versions:
        var_name = f"V{format_version_var(ver)}"
        if not hasattr(checksums, var_name):
            print(f"Error: Migration references version '{ver}', but registry {var_name} is absent from checksums.py!", file=sys.stderr)
            sys.exit(1)
        ver_dict = getattr(checksums, var_name)
        if not isinstance(ver_dict, dict) or len(ver_dict) == 0:
            print(f"Error: Registry {var_name} is empty! Must be populated before shipping to prevent all-conflict upgrades.", file=sys.stderr)
            sys.exit(1)
            
    if failures > 0:
        print(f"Verification FAILED with {failures} mismatches.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Verification SUCCESSFUL: {checked} files checked cleanly. All referenced registry dicts are populated.")

def main():
    parser = argparse.ArgumentParser(description="AI Delivery Control Checksum Generator/Verifier")
    parser.add_argument("--version", help="Version to generate checksums for (e.g., 1.1.0 or 1.1.5)")
    parser.add_argument("--framework-root", default=".", help="Root directory of framework sources (default: '.')")
    parser.add_argument("--verify", action="store_true", help="Run in verification mode instead of generation mode. For framework development use only. Not applicable to installed project directories.")
    parser.add_argument("--project", action="store_true", help="Indicate this is an installed project directory")
    
    args = parser.parse_args()
    framework_root = Path(args.framework_root).resolve()
    bootstrap_dir = Path(__file__).resolve().parent
    
    if args.verify:
        if args.project:
            print("generate_checksums.py --verify is a framework development tool and is not meaningful for customised project installations. Run bootstrap/validate.py instead.")
            sys.exit(0)
        run_verify(framework_root, bootstrap_dir)
    else:
        if not args.version:
            print("Error: --version is required for generation mode.", file=sys.stderr)
            sys.exit(1)
        run_generate(args.version, framework_root, bootstrap_dir)

if __name__ == "__main__":
    main()
