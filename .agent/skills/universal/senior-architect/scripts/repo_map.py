import ast
import json
from pathlib import Path

CACHE_PATH = Path(".agent/state/repo_graph_cache.json")


def filepath_to_module(filepath: Path) -> str:
    parts = filepath.with_suffix("").parts
    return ".".join(parts)


def resolve_module_to_filepath(module_name: str) -> Path | None:
    path_str = module_name.replace(".", "/")
    path = Path(path_str + ".py")
    if path.exists():
        return path
    init_path = Path(path_str + "/__init__.py")
    if init_path.exists():
        return init_path
    return None


class ImportVisitor(ast.NodeVisitor):
    def __init__(self, current_module: str):
        self.current_module = current_module
        self.imports = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            module_name = node.module
            if node.level > 0:
                parts = self.current_module.split(".")
                strip_count = node.level
                base_parts = parts[:-strip_count] if strip_count < len(parts) else []
                module_name = ".".join(base_parts + [node.module])
            self.imports.add(module_name)
        self.generic_visit(node)


def parse_file_imports_and_symbols(filepath: Path) -> tuple[list[str], list[str]]:
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)
        current_module = filepath_to_module(filepath)

        # Extract imports
        visitor = ImportVisitor(current_module)
        visitor.visit(tree)
        resolved_files = []
        for imp in visitor.imports:
            resolved = resolve_module_to_filepath(imp)
            if resolved:
                resolved_files.append(str(resolved).replace("\\", "/"))

        # Extract public symbols (classes/functions not starting with _)
        symbols = []
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                if not node.name.startswith("_"):
                    symbols.append(node.name)

        return list(set(resolved_files)), list(set(symbols))
    except (SyntaxError, Exception):
        # Graceful degradation on syntax error or other parsing issues
        return [], []


def compute_pagerank(
    nodes, edges, personalization, damping=0.85, max_iter=100, tol=1e-6
):
    n = len(nodes)
    if n == 0:
        return {}

    # Normalize personalization
    p_sum = sum(personalization.values())
    p = {
        node: personalization[node] / p_sum if p_sum > 0 else 1.0 / n for node in nodes
    }

    scores = {node: p[node] for node in nodes}
    in_edges = {node: [] for node in nodes}
    out_degree = {node: 0 for node in nodes}

    for src, tgts in edges.items():
        for tgt in tgts:
            if tgt in in_edges:
                in_edges[tgt].append(src)
                out_degree[src] += 1

    for _ in range(max_iter):
        next_scores = {}
        dangling_sum = sum(scores[node] for node in nodes if out_degree[node] == 0)

        for node in nodes:
            incoming = sum(scores[src] / out_degree[src] for src in in_edges[node])
            next_scores[node] = (1.0 - damping) * p[node] + damping * (
                incoming + dangling_sum * p[node]
            )

        diff = sum(abs(next_scores[node] - scores[node]) for node in nodes)
        scores = next_scores
        if diff < tol:
            break

    return scores


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def generate_repo_map(changed_files: list[str]) -> str:
    """Generates a compact, highly relevant Markdown structural map of the workspace."""
    # Standardize changed files paths
    changed_normalized = [f.replace("\\", "/") for f in changed_files]

    # Load cache and walk src/
    cache = load_cache()
    nodes = []
    edges = {}
    symbols_map = {}
    updated_cache = {}

    for path in Path("src").rglob("*.py"):
        filepath_str = str(path).replace("\\", "/")
        nodes.append(filepath_str)

        try:
            mtime = path.stat().st_mtime
        except Exception:
            mtime = 0.0

        # Cache hit check
        if filepath_str in cache and cache[filepath_str].get("mtime") == mtime:
            imports = cache[filepath_str].get("imports", [])
            symbols = cache[filepath_str].get("symbols", [])
            updated_cache[filepath_str] = cache[filepath_str]
        else:
            imports, symbols = parse_file_imports_and_symbols(path)
            updated_cache[filepath_str] = {
                "mtime": mtime,
                "imports": imports,
                "symbols": symbols,
            }

        edges[filepath_str] = imports
        symbols_map[filepath_str] = symbols

    save_cache(updated_cache)

    # Personalization Logic
    personalization = {node: 1.0 for node in nodes}
    changed_set = set(changed_normalized)
    neighbors = set()

    for src, tgts in edges.items():
        if src in changed_set:
            neighbors.update(tgts)
        for tgt in tgts:
            if tgt in changed_set:
                neighbors.add(src)

    for node in nodes:
        if node in changed_set:
            personalization[node] = 10.0
        elif node in neighbors:
            personalization[node] = (
                5.0  # distance-1 imported/importing files get medium boost
            )

    # Compute PageRank
    scores = compute_pagerank(nodes, edges, personalization)

    # Sort nodes by score
    sorted_nodes = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)

    # Format top 10 relevant nodes under ≤600 token budget
    lines = [
        "### 🗺️ Workspace Structural Map",
        "",
        "| Score | File Path | Status | Key Public Symbols |",
        "|---|---|---|---|",
    ]

    for node in sorted_nodes[:10]:
        score_str = f"{scores[node]:.4f}"
        status = (
            "Modified"
            if node in changed_set
            else ("Connected" if node in neighbors else "Active")
        )

        # Compact public symbols
        syms = symbols_map.get(node, [])
        syms_str = ", ".join(syms[:4])
        if len(syms) > 4:
            syms_str += ", ..."
        if not syms_str:
            syms_str = "-"

        lines.append(f"| {score_str} | `{node}` | `{status}` | {syms_str} |")

    return "\n".join(lines)


def get_pagerank_scores(changed_files: list[str]) -> dict[str, float]:
    """Computes and returns PageRank scores for all workspace files."""
    changed_normalized = [f.replace("\\", "/") for f in changed_files]
    cache = load_cache()
    nodes = []
    edges = {}

    for path in Path("src").rglob("*.py"):
        filepath_str = str(path).replace("\\", "/")
        nodes.append(filepath_str)

        try:
            mtime = path.stat().st_mtime
        except Exception:
            mtime = 0.0

        if filepath_str in cache and cache[filepath_str].get("mtime") == mtime:
            imports = cache[filepath_str].get("imports", [])
        else:
            imports, _ = parse_file_imports_and_symbols(path)

        edges[filepath_str] = imports

    personalization = {node: 1.0 for node in nodes}
    changed_set = set(changed_normalized)
    neighbors = set()

    for src, tgts in edges.items():
        if src in changed_set:
            neighbors.update(tgts)
        for tgt in tgts:
            if tgt in changed_set:
                neighbors.add(src)

    for node in nodes:
        if node in changed_set:
            personalization[node] = 10.0
        elif node in neighbors:
            personalization[node] = 5.0

    return compute_pagerank(nodes, edges, personalization)
