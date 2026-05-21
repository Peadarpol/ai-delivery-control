import ast
import re
import sys
from pathlib import Path

# --- Configuration ---
DOMAIN_DIR = Path("src/domain")
APPLICATION_DIR = Path("src/application")
INFRASTRUCTURE_DIR = Path("src/infrastructure")
TESTS_DIR = Path("tests")

# Aggregate Roots (for check_aggregate_boundaries)
AGGREGATE_ROOTS = {
    # [PROJECT_AGGREGATES_PLACEHOLDER]
    # e.g., "Member", "Contract", "Plan"
    "GenericAggregateRoot",
}


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
        if node.module:
            for forbidden in self.forbidden_prefixes:
                if node.module.startswith(forbidden):
                    self.violations.append(
                        f"{self.current_file}:{node.lineno}: Layer violation - imported from '{node.module}'"
                    )
        self.generic_visit(node)


# --- Check Functions ---


def check_forbidden_patterns():
    """Bans nest_asyncio.apply() and other problematic patterns."""
    errors = []
    # nest_asyncio check
    pattern = re.compile(r"nest_asyncio\.apply\(\)")
    for path in TESTS_DIR.rglob("*.py"):
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if not stripped.startswith("#") and pattern.search(line):
                    # Exception: Allow in conftest.py for CI stability
                    if path.name == "conftest.py":
                        continue
                    errors.append(f"{path}:{i}: Forbidden use of nest_asyncio.apply()")
    return errors


def check_layer_boundaries_ast():
    """Ensures strict architectural boundary enforcement using AST parsing."""
    errors = []

    # Domain Layer: No imports from presentation or external frameworks (except typings)
    forbidden_in_domain = [
        "src.presentation",
        "src.infrastructure",
        "fastapi",
        "streamlit",
    ]
    for path in DOMAIN_DIR.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            visitor = LayerViolationVisitor(path, forbidden_in_domain)
            visitor.visit(tree)
            errors.extend(visitor.violations)
        except Exception as e:
            errors.append(f"{path}: AST Parse Error: {e}")

    # Application Layer: No imports from presentation or infrastructure
    forbidden_in_app = ["src.presentation", "src.infrastructure"]
    for path in APPLICATION_DIR.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            visitor = LayerViolationVisitor(path, forbidden_in_app)
            visitor.visit(tree)
            errors.extend(visitor.violations)
        except Exception as e:
            errors.append(f"{path}: AST Parse Error: {e}")

    return errors


def compute_coupling_metrics():
    """Computes basic coupling metrics (import counts) for critical files.

    Thresholds calibrated post-SR-01/02/03/04 (2026-05-02) against actual codebase maximums:

    Entry Points / Composition Roots (main.py, app.py, system.py):
      threshold=45 — post-SR max: system.py=25, app.py=11, main.py=6.
      Headroom of ~20 imports before review required.

    Infrastructure Orchestrators (infrastructure/*, unit_of_work.py):
      threshold=50 — post-SR max: startup.py=41 (ceiling file, grows with scheduled jobs).
      Headroom of ~9 imports before review required. startup.py is the expected ceiling;
      if it grows past 50, split lifecycle hooks into separate files.

    Domain Services / Handlers (everything else):
      threshold=30 — post-SR max: pages/__init__.py=28, contract_service.py=25.
      2-node headroom on pages/__init__.py is intentional: gate fires promptly on drift.

    Intentionally exempt files (high coupling by design):
      repository_registry.py — sole permitted importer of all concrete repo classes (SR-03).
      High import count here concentrates coupling rather than spreading it.
    """
    # Files exempt from coupling thresholds — high import count is intentional by design.
    COUPLING_EXEMPT = {
        "repository_registry.py",  # SR-03: intentional boundary; only file allowed to import concrete repos
    }

    metrics = []
    for path in Path("src").rglob("*.py"):
        if path.name in COUPLING_EXEMPT:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            import_count = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_count += 1

            # Determine threshold based on architectural role
            threshold = 30  # Domain services / handlers
            file_name = path.name
            path_str = str(path).replace("\\", "/")

            if (
                file_name in ["main.py", "app.py"]
                or "presentation/api/dependencies/system.py" in path_str
            ):
                threshold = 45  # Entry points / composition roots
            elif "infrastructure" in path_str or "unit_of_work.py" in file_name:
                threshold = 50  # Infrastructure orchestrators (startup.py ceiling=41)

            if import_count > threshold:
                metrics.append(
                    f"{path}: HIGH COUPLING ({import_count} imports, threshold {threshold})"
                )
        except Exception:
            pass
    return metrics


def check_playwright_locators():
    """Bans fragile Playwright locators."""
    errors = []
    pattern = re.compile(r'\.locator\(["\']text=')
    for path in TESTS_DIR.rglob("*.py"):
        if "playwright" in str(path) or "e2e" in str(path) or "bdd" in str(path):
            with open(path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if pattern.search(line):
                        errors.append(
                            f"{path}:{i}: Use of fragile text= locator in Playwright"
                        )
    return errors


def check_type_checking_imports():
    """Enforces quoted types in cast() when inside TYPE_CHECKING."""
    errors = []
    # This is a heuristic: check if a file has TYPE_CHECKING and a cast() with unquoted first arg
    # A true AST implementation would be more robust but this catches common cases.
    # Fixed: added \b word boundary to avoid matching 'broadcast('
    cast_pattern = re.compile(r"\bcast\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,")
    for path in Path("src").rglob("*.py"):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if "TYPE_CHECKING" in content:
                for i, line in enumerate(content.splitlines(), 1):
                    match = cast_pattern.search(line)
                    if match:
                        type_name = match.group(1)
                        # If type_name is in the content and looks like a class/type but isn't quoted
                        # we flag it as a risk.
                        errors.append(
                            f'{path}:{i}: Potential NameError risk. Use cast("{type_name}", ...) for types behind TYPE_CHECKING.'
                        )
    return errors


def check_aggregate_boundaries():
    """Asserts Repositories only exist for identified Aggregate Roots."""
    errors = []
    # Scan for repository classes
    repo_pattern = re.compile(r"class\s+([A-Za-z0-9_]+Repository)")
    for path in Path("src/application/persistence").rglob("*.py"):
        with open(path, "r", encoding="utf-8") as f:
            for match in repo_pattern.finditer(f.read()):
                repo_name = match.group(1)
                entity_name = repo_name.replace("Repository", "")
                if (
                    entity_name not in AGGREGATE_ROOTS and entity_name != "I"
                ):  # Ignore Interfaces like IRepository
                    errors.append(
                        f"{path}: Repository found for non-aggregate root entity '{entity_name}'"
                    )
    return errors


def check_interface_segregation():
    """Ensures Application Services do not directly instantiate Infrastructure classes."""
    errors = []
    # Heuristic: look for instantiation of classes with 'Postgres', 'Redis', etc.
    # or direct imports from src.infrastructure inside src.application.services
    infra_classes = ["Postgres", "Redis", "SQLAlchemy", "Boto3"]
    for path in APPLICATION_DIR.rglob("*.py"):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # Ignore imports (checked by dependency_analyzer usually)
            # Focus on instantiation: Name(
            for cls_prefix in infra_classes:
                if re.search(rf"\b{cls_prefix}[A-Za-z0-9_]*\(", content):
                    errors.append(
                        f"{path}: Service potentially instantiates concrete Infrastructure class '{cls_prefix}'"
                    )
    return errors


def check_conditional_branch_filter():
    """Flags the conditional branch filter anti-pattern in repository files.

    The pattern `if self.branch_id: stmt = stmt.where(...)` silently returns
    all-tenant data when branch_id is None. The correct pattern is to call
    _apply_branch_filter(stmt), which is fail-closed (raises ValueError on None).

    To suppress a specific line where the conditional is intentional (rare),
    add a trailing comment: # @branch_filter_ok
    """
    errors = []
    repo_dirs = [
        Path("src/infrastructure/database/repositories"),
        Path("src/infrastructure/database"),
    ]
    pattern = re.compile(r"if\s+self\.branch_id\b")

    for repo_dir in repo_dirs:
        if not repo_dir.exists():
            continue
        for path in repo_dir.rglob("*.py"):
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


def check_asgi_lifespan():
    """Enforces use of LifespanManager in conftest fixtures with AsyncClient."""
    errors = []
    for path in TESTS_DIR.rglob("conftest.py"):
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
    return errors


def extract_adr_annotations(filepath: str, scan_lines: int = 20) -> list[str]:
    """Scans the first N lines of a file to extract ADR domain annotations.

    Supports singular/plural and spacing variations. Example:
    # ADRs: branch_isolation, multi_branch_schema
    # ADR: clean_architecture
    """
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


def check_adr_annotations_count():
    """Scans the codebase for files with >3 ADR annotations and logs a soft warning.

    This is a warning check only — it does not block the commit.
    """
    warnings = []
    for path in Path("src").rglob("*.py"):
        domains = extract_adr_annotations(str(path))
        if len(domains) > 3:
            warnings.append(
                f"{path}: File contains more than 3 ADR annotations: {', '.join(domains)}"
            )
    if warnings:
        print("\n[WARNING] ADR Annotation Count Checks:")
        for warning in warnings:
            print(f"  ! {warning}")


# --- Runner ---


def main():
    all_errors = []
    all_errors.extend(check_forbidden_patterns())
    all_errors.extend(check_layer_boundaries_ast())
    all_errors.extend(check_playwright_locators())
    all_errors.extend(check_aggregate_boundaries())
    all_errors.extend(check_interface_segregation())
    all_errors.extend(check_conditional_branch_filter())
    all_errors.extend(check_asgi_lifespan())
    all_errors.extend(compute_coupling_metrics())
    all_errors.extend(check_type_checking_imports())

    # Soft warnings (do not block commit)
    check_adr_annotations_count()

    if all_errors:
        print(f"\n[FAIL] Found {len(all_errors)} architectural violations:")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)

    print("[PASS] Architectural checks passed!")
    sys.exit(0)


if __name__ == "__main__":
    main()
