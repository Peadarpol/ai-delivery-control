import ast
import re
import sys
from pathlib import Path

def find_project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / ".agent" / "config.yaml").exists() or (cwd / ".git").exists():
        return cwd
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".agent" / "config.yaml").exists() or (parent / ".git").exists():
            return parent
    return cwd

def _resolve_src_root_init(root: Path) -> str:
    config_path = root / ".agent" / "config.yaml"
    if config_path.exists():
        try:
            content = config_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "source_root:" in line:
                    return line.split(":", 1)[1].split("#", 1)[0].strip().strip("\"'")
        except Exception:
            pass
    return "src"

try:
    from harness_utils import _safe_git_env
except ImportError:
    _root = find_project_root()
    _src_root = _resolve_src_root_init(_root)
    sys.path.insert(0, str(_root / _src_root / "scripts"))
    from harness_utils import _safe_git_env

# --- Fallback YAML Parser ---

def parse_yaml_fallback(content: str) -> dict:
    """
    A robust, zero-dependency indentation-based parser for the .agent/config.yaml structure.
    Handles nested sections and lists.
    """
    lines = content.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if ' #' in line:
            line = line.split(' #')[0]
        cleaned.append((len(line) - len(line.lstrip()), line.strip()))
    if not cleaned:
        return {}

    def parse_block(index: int, target_indent: int) -> tuple[any, int]:
        if index >= len(cleaned):
            return {}, index
        indent, first_line = cleaned[index]
        if first_line.startswith('-'):
            items = []
            while index < len(cleaned):
                ind, line = cleaned[index]
                if ind < target_indent:
                    break
                if ind == target_indent and line.startswith('-'):
                    line_content = line[1:].strip()
                    if ':' in line_content:
                        item_dict = {}
                        k, v = line_content.split(':', 1)
                        k, v = k.strip().strip('\'"'), v.strip().strip('\'"')
                        if v:
                            item_dict[k] = v
                        else:
                            item_dict[k] = None
                        index += 1
                        while index < len(cleaned):
                            next_ind, next_line = cleaned[index]
                            if next_ind <= ind:
                                break
                            if ':' in next_line and not next_line.startswith('-'):
                                nk, nv = next_line.split(':', 1)
                                nk, nv = nk.strip().strip('\'"'), nv.strip().strip('\'"')
                                if nv:
                                    item_dict[nk] = nv
                                else:
                                    if index + 1 < len(cleaned):
                                        nnext_ind, nnext_line = cleaned[index + 1]
                                        if nnext_ind > next_ind:
                                            nested_val, next_idx = parse_block(index + 1, nnext_ind)
                                            item_dict[nk] = nested_val
                                            index = next_idx - 1
                                        else:
                                            item_dict[nk] = None
                                    else:
                                        item_dict[nk] = None
                            index += 1
                        items.append(item_dict)
                        continue
                    else:
                        items.append(line_content.strip('\'"'))
                        index += 1
                else:
                    break
            return items, index
        else:
            obj = {}
            while index < len(cleaned):
                ind, line = cleaned[index]
                if ind < target_indent:
                    break
                if ind == target_indent:
                    if ':' in line:
                        k, v = line.split(':', 1)
                        k, v = k.strip().strip('\'"'), v.strip().strip('\'"')
                        if v:
                            if v.startswith('[') and v.endswith(']'):
                                inner = v[1:-1].strip()
                                v = [item.strip().strip('\'"') for item in inner.split(',')] if inner else []
                            obj[k] = v
                            index += 1
                        else:
                            if index + 1 < len(cleaned):
                                next_ind, next_line = cleaned[index + 1]
                                if next_ind > ind:
                                    nested_val, next_idx = parse_block(index + 1, next_ind)
                                    obj[k] = nested_val
                                    index = next_idx
                                else:
                                    obj[k] = None
                                    index += 1
                            else:
                                obj[k] = None
                                index += 1
                    else:
                        index += 1
                else:
                    break
            return obj, index

    res, _ = parse_block(0, cleaned[0][0])
    return res or {}


def load_config() -> dict:
    """Finds and parses .agent/config.yaml using PyYAML or the custom fallback parser."""
    config_path = find_project_root() / ".agent" / "config.yaml"

    if not config_path.exists():
        return {}
    try:
        content = config_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[ARCH] Warning: Failed to read .agent/config.yaml: {e}")
        return {}

    try:
        import yaml
        return yaml.safe_load(content) or {}
    except ImportError:
        return parse_yaml_fallback(content)

# --- AST Layer Visitor ---

class LayerViolationVisitor(ast.NodeVisitor):
    def __init__(self, current_file: Path, forbidden_prefixes: list[str]):
        self.current_file = current_file
        self.forbidden_prefixes = forbidden_prefixes
        self.violations = []

    def visit_Import(self, node):
        for alias in node.names:
            for forbidden in self.forbidden_prefixes:
                if alias.name.startswith(forbidden):
                    self.violations.append(
                        f"{self.current_file}:{node.lineno}: Layer violation - imported '{alias.name}'"
                    )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        # NOTE: relative imports (node.level > 0) are skipped — node.module is None or a fragment, so absolute prefix matching does not apply.
        if node.module:
            for forbidden in self.forbidden_prefixes:
                if node.module.startswith(forbidden):
                    self.violations.append(
                        f"{self.current_file}:{node.lineno}: Layer violation - imported from '{node.module}'"
                    )
        self.generic_visit(node)

# --- Dynamic Check Functions ---

def check_layer_boundaries_ast(architecture_config: dict) -> list[str]:
    """Ensures strict architectural boundary enforcement using AST parsing."""
    errors = []
    layers = architecture_config.get("layers", [])
    if not layers:
        return errors

    for layer in layers:
        layer_path_str = layer.get("path")
        forbidden_imports = layer.get("forbidden_imports", [])
        if not layer_path_str or not forbidden_imports:
            continue

        layer_dir = Path(layer_path_str)
        if not layer_dir.exists():
            continue

        for path in layer_dir.rglob("*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
                visitor = LayerViolationVisitor(path, forbidden_imports)
                visitor.visit(tree)
                errors.extend(visitor.violations)
            except Exception as e:
                errors.append(f"{path}: AST Parse Error: {e}")

    return errors


def check_forbidden_patterns(architecture_config: dict) -> list[str]:
    """Bans configured regex patterns dynamically from the codebase."""
    errors = []
    patterns_config = architecture_config.get("forbidden_patterns", [])
    if not patterns_config:
        return errors

    for item in patterns_config:
        pat_str = item.get("pattern")
        in_paths = item.get("in_paths", [])
        message = item.get("message", f"Forbidden pattern detected: {pat_str}")
        exempt_files = item.get("exempt_files", [])
        file_filters = item.get("file_filters", [])

        if not pat_str or not in_paths:
            continue

        try:
            pattern = re.compile(pat_str)
        except Exception as e:
            print(f"[ARCH] Warning: Invalid forbidden regex pattern '{pat_str}': {e}")
            continue

        for search_path_str in in_paths:
            search_path = Path(search_path_str)
            if not search_path.exists():
                continue

            if search_path.is_file():
                files = [search_path]
            else:
                files = list(search_path.rglob("*.py"))

            for path in files:
                if file_filters:
                    if not any(f_filt in str(path) for f_filt in file_filters):
                        continue
                if path.name in exempt_files:
                    continue

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            stripped = line.strip()
                            if not stripped.startswith("#") and pattern.search(line):
                                errors.append(f"{path}:{i}: {message}")
                except Exception:
                    pass
    return errors


def check_playwright_locators(architecture_config: dict) -> list[str]:
    """
    Bans fragile Playwright locators.
    This check is handled dynamically by check_forbidden_patterns, but is kept for backward compatibility.
    """
    return []


def check_aggregate_boundaries(architecture_config: dict) -> list[str]:
    """Asserts Repositories only exist for identified Aggregate Roots."""
    errors = []
    aggregate_roots = set(architecture_config.get("aggregate_roots", []))
    if not aggregate_roots:
        return errors

    persistence_dir = Path("src/application/persistence")
    if not persistence_dir.exists():
        app_path = None
        for layer in architecture_config.get("layers", []):
            if layer.get("name") == "application":
                app_path = layer.get("path")
                break
        if app_path:
            persistence_dir = Path(app_path) / "persistence"

    if not persistence_dir.exists():
        return errors

    repo_pattern = re.compile(r"class\s+([A-Za-z0-9_]+Repository)")
    for path in persistence_dir.rglob("*.py"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                for match in repo_pattern.finditer(content):
                    repo_name = match.group(1)
                    entity_name = repo_name.replace("Repository", "")
                    if entity_name not in aggregate_roots and entity_name != "I":
                        errors.append(
                            f"{path}: Repository found for non-aggregate root entity '{entity_name}'"
                        )
        except Exception:
            pass
    return errors


def check_interface_segregation(architecture_config: dict) -> list[str]:
    """Ensures Application Services do not directly instantiate Infrastructure classes."""
    errors = []
    segregation_config = architecture_config.get("interface_segregation", {})
    if not segregation_config:
        return errors

    infra_classes = segregation_config.get("infra_classes", [])
    in_paths = segregation_config.get("in_paths", [])
    if not infra_classes or not in_paths:
        return errors

    for path_str in in_paths:
        search_path = Path(path_str)
        if not search_path.exists():
            continue

        for path in search_path.rglob("*.py"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for cls_prefix in infra_classes:
                        if re.search(rf"\b{cls_prefix}[A-Za-z0-9_]*\(", content):
                            errors.append(
                                f"{path}: Service potentially instantiates concrete Infrastructure class '{cls_prefix}'"
                            )
            except Exception:
                pass
    return errors


def check_conditional_branch_filter(architecture_config: dict) -> list[str]:
    """Flags the conditional branch filter anti-pattern in repository files."""
    errors = []
    branch_config = architecture_config.get("conditional_branch_filter", architecture_config.get("conditional_isolation_filter", {}))
    if not branch_config:
        return errors

    in_paths = branch_config.get("in_paths", [])
    if not in_paths:
        return errors

    pattern = re.compile(r"if\s+self\.branch_id\b")
    for path_str in in_paths:
        search_path = Path(path_str)
        if not search_path.exists():
            continue

        if search_path.is_file():
            files = [search_path]
        else:
            files = list(search_path.rglob("*.py"))

        for path in files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line) and "# @branch_filter_ok" not in line:
                            errors.append(
                                f"{path}:{i}: Conditional branch filter anti-pattern — "
                                f"'if self.branch_id:' silently returns all-tenant data "
                                f"when branch_id is None. Use _apply_branch_filter(stmt) instead."
                            )
            except (OSError, UnicodeDecodeError):
                pass
    return errors


def check_asgi_lifespan(paths_config: dict) -> list[str]:
    """Enforces use of LifespanManager in conftest fixtures with AsyncClient."""
    errors = []
    test_root = Path(paths_config.get("test_root", "tests"))
    if not test_root.exists():
        return errors

    for path in test_root.rglob("conftest.py"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if (
                    "AsyncClient" in content
                    and "LifespanManager" not in content
                    and "ASGITransport" in content
                ):
                    errors.append(
                        f"{path}: AsyncClient used without LifespanManager. Potential resource leak."
                    )
        except Exception:
            pass
    return errors


def check_type_checking_imports(paths_config: dict) -> list[str]:
    """Enforces quoted types in cast() when inside TYPE_CHECKING."""
    errors = []
    source_root = Path(paths_config.get("source_root", "src"))
    if not source_root.exists():
        return errors

    cast_pattern = re.compile(r"\bcast\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,")
    for path in source_root.rglob("*.py"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if "TYPE_CHECKING" in content:
                    for i, line in enumerate(content.splitlines(), 1):
                        match = cast_pattern.search(line)
                        if match:
                            type_name = match.group(1)
                            errors.append(
                                f'{path}:{i}: Potential NameError risk. Use cast("{type_name}", ...) for types behind TYPE_CHECKING.'
                            )
        except Exception:
            pass
    return errors


def extract_adr_annotations(filepath: str, scan_lines: int = 20) -> list[str]:
    """Scans the first N lines of a file to extract ADR domain annotations."""
    pattern = re.compile(r"^\s*#\s*ADRs?:\s*(.+)$", re.IGNORECASE)
    domains = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for _ in range(scan_lines):
                line = f.readline()
                if not line:
                    break
                match = pattern.match(line.strip())
                if match:
                    parts = [p.strip() for p in match.group(1).split(",")]
                    domains.extend([p for p in parts if p])
    except (OSError, UnicodeDecodeError):
        pass
    return domains


def check_adr_annotations_count(paths_config: dict):
    """Scans the codebase for files with >3 ADR annotations and logs a soft warning."""
    source_root = Path(paths_config.get("source_root", "src"))
    if not source_root.exists():
        return

    warnings = []
    for path in source_root.rglob("*.py"):
        domains = extract_adr_annotations(str(path))
        if len(domains) > 3:
            warnings.append(
                f"{path}: File contains more than 3 ADR annotations: {', '.join(domains)}"
            )
    if warnings:
        print("\n[WARNING] ADR Annotation Count Checks:")
        for warning in warnings:
            print(f"  ! {warning}")


def check_adr_decision_blocks(paths_config: dict) -> list[str]:
    """Ensures ADRs contain the standard Decision Block scaffold. Soft advisory only."""
    advisories = []
    docs_dir = Path("docs") / "adr"
    if not docs_dir.exists():
        docs_dir = Path("docs") / "decisions" / "adr"
        if not docs_dir.exists():
            return advisories

    for path in docs_dir.rglob("*.md"):
        try:
            content = path.read_text(encoding="utf-8")
            if "template" in path.name.lower():
                continue
            
            has_decision_block = bool(re.search(r"##\s+Decision Block", content, re.IGNORECASE))
            has_tradeoffs = bool(re.search(r"Tradeoffs Navigated", content, re.IGNORECASE))
            has_failures = bool(re.search(r"Failure Modes Exposed", content, re.IGNORECASE))
            
            if not has_decision_block or not has_tradeoffs or not has_failures:
                advisories.append(f"{path}: Missing or incomplete 'Decision Block' section. Consider scaffolding AT/FM tradeoffs.")
        except Exception:
            pass
            
    return advisories

def compute_coupling_metrics(architecture_config: dict) -> list[str]:
    """Computes basic coupling metrics (import counts) for critical files against configured thresholds."""
    errors = []
    coupling_config = architecture_config.get("coupling", {})
    if not coupling_config:
        return errors

    exempt_files = set(coupling_config.get("exempt_files", []))
    thresholds = coupling_config.get("thresholds", {})

    # Gather search paths dynamically from layers, falling back to 'src'
    search_dirs = []
    layers = architecture_config.get("layers", [])
    for layer in layers:
        p_str = layer.get("path")
        if p_str:
            search_dirs.append(Path(p_str))
    if not search_dirs:
        search_dirs = [Path("src")]

    scanned_files = set()
    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        if s_dir.is_file():
            scanned_files.add(s_dir)
        else:
            for path in s_dir.rglob("*.py"):
                scanned_files.add(path)

    for path in scanned_files:
        if path.name in exempt_files:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            import_count = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_count += 1

            file_name = path.name
            path_str = str(path).replace("\\", "/")

            # Resolve threshold
            threshold = 30  # Standard fallback default
            if "default" in thresholds:
                default_config = thresholds["default"]
                if isinstance(default_config, dict):
                    threshold = int(default_config.get("threshold", 30))
                else:
                    threshold = int(default_config)

            matched_threshold = None
            for key, val in thresholds.items():
                if key == "default":
                    continue
                if isinstance(val, dict):
                    th = int(val.get("threshold", 30))
                    files = val.get("files", [])
                    file_matches = val.get("file_matches", [])
                    path_matches = val.get("path_matches", [])

                    if file_name in files or file_name in file_matches:
                        matched_threshold = th
                        break
                    if any(pm in path_str for pm in path_matches):
                        matched_threshold = th
                        break

            if matched_threshold is not None:
                threshold = matched_threshold

            if import_count > threshold:
                errors.append(
                    f"{path}: HIGH COUPLING ({import_count} imports, threshold {threshold})"
                )
        except Exception:
            pass
    return errors


# --- Runner ---

def main():
    config = load_config()
    paths_config = config.get("paths", {})
    architecture_config = config.get("architecture")

    if not config:
        # No config.yaml at all — this is almost certainly a misconfiguration or a run
        # outside the project root.  Fail loud so CI surfaces the problem rather than
        # recording a silent PASS.
        print("[ARCH] FAIL: .agent/config.yaml not found or could not be read.")
        print("       Run this script from the repository root where .agent/config.yaml lives.")
        sys.exit(1)

    if architecture_config is None:
        # config.yaml exists but has no 'architecture:' block.  Warn and exit cleanly —
        # the operator has consciously opted out of layer checks for this project.
        print("[ARCH] No 'architecture:' block found in .agent/config.yaml — checks skipped.")
        print("       Add an 'architecture:' block to enable layer boundary enforcement.")
        sys.exit(0)

    # --- Count files that will actually be scanned so we can detect misconfiguration ---
    # Gather layer paths from config (same logic as compute_coupling_metrics).
    configured_layers = architecture_config.get("layers", [])
    layer_dirs = [Path(layer["path"]) for layer in configured_layers if layer.get("path")]
    total_scanned = 0
    scan_summary: list[str] = []
    for layer_dir in layer_dirs:
        if not layer_dir.exists():
            scan_summary.append(f"  [MISS]  {layer_dir}  (path does not exist)")
        else:
            count = len(list(layer_dir.rglob("*.py")))
            total_scanned += count
            scan_summary.append(f"  [OK]    {layer_dir}  ({count} .py files)")

    all_errors = []
    all_errors.extend(check_forbidden_patterns(architecture_config))
    all_errors.extend(check_layer_boundaries_ast(architecture_config))
    all_errors.extend(check_playwright_locators(architecture_config))
    all_errors.extend(check_aggregate_boundaries(architecture_config))
    all_errors.extend(check_interface_segregation(architecture_config))
    all_errors.extend(check_conditional_branch_filter(architecture_config))
    all_errors.extend(check_asgi_lifespan(paths_config))
    all_errors.extend(compute_coupling_metrics(architecture_config))
    all_errors.extend(check_type_checking_imports(paths_config))

    # --- Audit summary: print layer scan results before verdict ---
    if configured_layers:
        print("[ARCH] Layer scan summary:")
        for line in scan_summary:
            print(line)
        print(f"[ARCH] Total .py files scanned across all layers: {total_scanned}")

        if layer_dirs and total_scanned == 0:
            # Every configured layer path either does not exist or contains no Python files.
            # This is almost certainly a path misconfiguration — a silent PASS here would
            # mean the gate passes without having checked anything.
            print(
                "[ARCH] FAIL: architecture layers are configured but zero Python files were "
                "found across all layer paths.  Check that the 'path' values in "
                ".agent/config.yaml match the actual source layout."
            )
            sys.exit(1)

    # Soft warnings (do not block commit)
    check_adr_annotations_count(paths_config)
    adr_advisories = check_adr_decision_blocks(paths_config)
    if adr_advisories:
        print("\n[ADVISORY] ADR Decision Block Checks:")
        for adv in adr_advisories:
            print(f"  \u2139\ufe0f  {adv}")

    # ── Write to GateContext (T1-G-13) ──
    try:
        import subprocess
        import hashlib
        project_root = find_project_root()
        src_root = paths_config.get("source_root", "src")
        sys.path.insert(0, str(project_root / src_root / "scripts"))
        from gate_context import load_gate_context, write_gate_context, GateContext, ArchViolation

        # Get staged diff and changed files
        res = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_safe_git_env()
        )
        diff_text = res.stdout if res.returncode == 0 else ""

        res_files = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_safe_git_env()
        )
        changed_files = [f.strip() for f in res_files.stdout.splitlines() if f.strip()]

        # Compute diff hash
        diff_hash = ""
        if diff_text:
            diff_hash = hashlib.sha256(diff_text.encode("utf-8")).hexdigest()

        gate_context = GateContext(
            diff_text=diff_text,
            diff_hash=diff_hash,
            changed_files=changed_files
        )

        # Extract ADR annotations from changed files
        adr_domains = []
        for f in changed_files:
            if Path(f).exists():
                adr_domains.extend(extract_adr_annotations(f))
        gate_context.adr_domains = list(set(adr_domains))

        # Parse all_errors into ArchViolation
        violations = []
        for err in all_errors:
            parts = err.split(":", 2)
            if len(parts) >= 3 and parts[1].strip().isdigit():
                filepath = parts[0].strip().replace("\\", "/")
                line = int(parts[1].strip())
                msg = parts[2].strip()
            elif len(parts) >= 2:
                filepath = parts[0].strip().replace("\\", "/")
                line = 1
                msg = parts[1].strip()
            else:
                filepath = "unknown"
                line = 1
                msg = err.strip()

            severity = "FAIL"
            if "coupling" in msg.lower() or "lifespan" in msg.lower() or "nameerror" in msg.lower():
                severity = "WARN"

            rule = "ARCHITECTURE_RULE"
            if "layer violation" in msg.lower():
                rule = "LAYER_BOUNDARY"
            elif "coupling" in msg.lower():
                rule = "HIGH_COUPLING"
            elif "conditional branch filter" in msg.lower():
                rule = "BRANCH_FILTER"
            elif "aggregate root" in msg.lower():
                rule = "AGGREGATE_ROOT"
            elif "concrete infrastructure" in msg.lower():
                rule = "INTERFACE_SEGREGATION"
            elif "lifespan" in msg.lower():
                rule = "ASGI_LIFESPAN"
            elif "forbidden pattern" in msg.lower():
                rule = "FORBIDDEN_PATTERN"

            violations.append(
                ArchViolation(file=filepath, line=line, rule=rule, severity=severity)
            )

        gate_context.arch_violations = violations
        write_gate_context(gate_context)
    except Exception as e:
        print(f"[ARCH] Warning: Failed to populate GateContext: {e}")

    if all_errors:
        print(f"\n[FAIL] Found {len(all_errors)} architectural violations:")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)

    print("[PASS] Architectural checks passed!")
    sys.exit(0)


if __name__ == "__main__":
    main()
