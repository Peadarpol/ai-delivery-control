#!/usr/bin/env python3
"""
.agent/scripts/loop_closure_check.py - Phase A Gherkin Scenario Parser, Component Matcher & Loop-Closure Report Generator.

Component & Key-Term Extraction Method
--------------------------------------
The component and key-term extraction algorithm extracts structural identifiers and code terms
from Gherkin scenario clause text (Given/When text for components; Then text for key terms).

Extraction Technique:
1. Backticked Identifiers: Any non-empty string inside backticks, e.g. `architecture_checks.py`,
   `disposition()`, `wiring_consumers.yaml`, `baseline=`, `PARTIALLY-WIRED`, `None`.
2. Filenames & Paths: Any token matching file extensions (.py, .yaml, .yml, .json, .md, .jsonl),
   e.g. `SPEC-enforcement-postures.md`, `architecture_checks.py`, `wiring_consumers.yaml`.
3. Function/Method Calls: Any identifier ending with `()`, e.g. `disposition()`, `record_decision()`.
4. Named Arguments / Parameters: Identifiers formatted as `name=` or `name=value`, e.g. `baseline=`, `touched_files=`.
5. Spec & Backlog Tags: Identifiers matching pattern `(SPEC|HIB|T1|T2|T3|T4)-[A-Za-z0-9_]+`, e.g. `HIB-080`, `T1-K-19`.
6. Uppercase Status / Constant Tokens: Uppercase tokens starting and ending with alphanumeric characters,
   pattern `\\b[A-Z0-9][A-Z0-9_\\-]*[A-Z0-9]\\b`, e.g. `PARTIALLY-WIRED`, `UNVERIFIED`, `WIRED`, `NOT-WIRED`, `AST`.

Normalisation & Filtering:
- Strips surrounding quotes, trailing commas/periods, and enclosing brackets/parentheses (unless ending in `()`).
- Ignores standard Gherkin keywords ("Given", "When", "Then", "And") and common English stop words.
- Performs a position-based span overlap filtering pass: removes any candidate match whose source text span
  overlaps with an already-kept longer match span.
- Preserves first-occurrence order of source text appearance for non-overlapping matches while collapsing
  exact value duplicates.

Component Normalization Mapping
-------------------------------
Before searching test code, extracted components are normalized into bare Python/code identifiers:
1. Spec / Backlog Tags matching pattern ^(SPEC|HIB|T1|T2|T3|T4)-... (e.g. HIB-080, SPEC-enforcement-postures.md):
   Marked as not code-searchable (is_code_searchable = False) and skipped during test code search.
2. Python Filenames ending in .py (e.g. architecture_checks.py, src/scripts/posture.py):
   Stripped of directory path and extension -> bare module identifier (e.g. architecture_checks, posture).
3. Config/Doc Filenames ending in .yaml, .yml, .json, .md (e.g. wiring_consumers.yaml):
   Stripped of directory path and extension -> bare config identifier (e.g. wiring_consumers).
4. Function/Method Calls ending in () (e.g. disposition(), record_decision()):
   Stripped of trailing () -> bare function/method identifier (e.g. disposition, record_decision).
5. Keyword Arguments ending in = (e.g. baseline=, touched_files=):
   Stripped of trailing = -> bare argument identifier (e.g. baseline, touched_files).
6. Bare Identifiers/Constants (e.g. PARTIALLY-WIRED, AST):
   Preserved as bare string identifier (is_code_searchable = True).

AST-Based Test Reference Search & Two-Tier Confidence
------------------------------------------------------
Searches tests/, tests/integration/, and tests/e2e/ (.py test files only) using Python's ast module:
- Function-level match ("function"): A test function (ast.FunctionDef / ast.AsyncFunctionDef) contains both
  an AST reference to the normalized component name (or imported symbols derived from it) AND at least one
  ast.Assert statement anywhere in its body.
- File-level match ("file"): The component name is referenced somewhere in the test file (e.g., at module level
  or inside a function without an assert), while assertions exist elsewhere in the file.
- None ("none"): No reference found in test code.

Mock vs. Real Classification
----------------------------
For each function-level match, classifies as MOCKED if unittest.mock.patch, with patch(...), MagicMock/Mock,
or monkeypatch.setattr(...) targets the component name/symbol in the containing test function or context; else REAL.
For file-level or non-matches, mock_status is "n/a".

Then-Clause Key-Term Overlap & Final Scenario Classification
------------------------------------------------------------
- For function-tier component matches, ast.Assert nodes in the matching test function are walked to extract
  comparison operands, identifiers, and string literal tokens.
- Overlap (case-insensitive) between assert tokens and scenario Then-clause key terms is evaluated.
- A component is CONFIRMED if it has a function-tier match AND Then-clause key-term overlap (or no key terms).
- Scenario Final Status:
  - VERIFIED (real entry point): Every code-searchable component has a confirmed REAL match.
  - VERIFIED (mock only): Every code-searchable component has a confirmed match, but at least one is MOCKED.
  - UNVERIFIED: At least one code-searchable component has no confirmed match.
  - SKIPPED: Zero code-searchable components extracted (all components are tags or no components extracted).
"""

import ast
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set


def safe_print(*args, **kwargs):
    """Safe print helper preventing UnicodeEncodeError on CP1252 Windows consoles."""
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    file = kwargs.get("file", sys.stdout)
    text = sep.join(str(arg) for arg in args) + end
    encoding = getattr(file, "encoding", "utf-8") or "utf-8"
    file.write(text.encode(encoding, errors="replace").decode(encoding))


@dataclass
class Scenario:
    spec_path: Path
    scenario_id: str
    title: str
    given_clauses: List[str] = field(default_factory=list)
    when_clauses: List[str] = field(default_factory=list)
    then_clauses: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    key_terms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "spec_path": str(self.spec_path),
            "scenario_id": self.scenario_id,
            "title": self.title,
            "given_clauses": self.given_clauses,
            "when_clauses": self.when_clauses,
            "then_clauses": self.then_clauses,
            "components": self.components,
            "key_terms": self.key_terms,
        }


STOP_WORDS = {
    "A", "AN", "THE", "IN", "IS", "IT", "TO", "FOR", "WITH", "OF", "AND", "OR", "ON",
    "AT", "BY", "FROM", "AS", "BE", "THIS", "THAT", "THESE", "THOSE", "GIVEN", "WHEN", "THEN"
}


@dataclass
class TermMatch:
    start: int
    end: int
    raw: str
    cleaned: str


@dataclass
class ComponentMatch:
    raw_component: str
    normalized_name: str
    is_code_searchable: bool
    match_tier: str  # "function" | "file" | "none"
    mock_status: str  # "REAL" | "MOCKED" | "n/a"
    matching_files: List[str] = field(default_factory=list)
    matching_functions: List[str] = field(default_factory=list)


@dataclass
class ComponentResult:
    raw_component: str
    normalized_name: str
    is_code_searchable: bool
    match_tier: str  # "function" | "file" | "none"
    mock_status: str  # "REAL" | "MOCKED" | "n/a"
    matching_files: List[str] = field(default_factory=list)
    matching_functions: List[str] = field(default_factory=list)
    then_overlap_found: bool = False
    matched_key_terms: List[str] = field(default_factory=list)
    is_confirmed: bool = False


@dataclass
class ScenarioResult:
    scenario: Scenario
    component_results: List[ComponentResult] = field(default_factory=list)
    final_status: str = "UNVERIFIED"  # "VERIFIED (real entry point)" | "VERIFIED (mock only)" | "UNVERIFIED" | "SKIPPED"
    status_reason: str = ""


def extract_terms(text: str) -> List[str]:
    """
    Extract components or key terms from a block of text using position-based span overlap filtering.
    """
    matches: List[TermMatch] = []

    def add_match(start: int, end: int, raw_text: str):
        cleaned = raw_text.strip()
        cleaned = re.sub(r'^[^\w\`\*\-]+|[^\w\`\*\=\)\/]+$', '', cleaned)
        if not cleaned:
            return
        if cleaned.upper() in STOP_WORDS:
            return
        matches.append(TermMatch(start=start, end=end, raw=raw_text, cleaned=cleaned))

    # 1. Backticked terms
    for m in re.finditer(r'`([^`]+)`', text):
        add_match(m.start(1), m.end(1), m.group(1))

    # 2. Filenames / Paths (.py, .yaml, .yml, .json, .md, .jsonl)
    for m in re.finditer(r'\b[A-Za-z0-9_\-\./]+\.(?:py|yaml|yml|json|md|jsonl)\b', text, re.IGNORECASE):
        add_match(m.start(), m.end(), m.group(0))

    # 3. Spec / Backlog tags (SPEC-..., HIB-..., T1-...)
    for m in re.finditer(r'\b(?:SPEC|HIB|T1|T2|T3|T4)\-[A-Za-z0-9_]+\b', text):
        add_match(m.start(), m.end(), m.group(0))

    # 4. Function / method calls ending in ()
    for m in re.finditer(r'\b[A-Za-z0-9_]+\(\)', text):
        add_match(m.start(), m.end(), m.group(0))

    # 5. Argument / Key-value patterns (name=)
    for m in re.finditer(r'\b[A-Za-z0-9_]+=', text):
        add_match(m.start(), m.end(), m.group(0))

    # 6. Uppercase status constants
    for m in re.finditer(r'\b[A-Z0-9][A-Z0-9_\-]*[A-Z0-9]\b', text):
        if m.group(0).upper() not in STOP_WORDS:
            add_match(m.start(), m.end(), m.group(0))

    # Span-overlap deduplication pass
    sorted_matches = sorted(matches, key=lambda m: (m.end - m.start), reverse=True)
    kept_spans: List[Tuple[int, int]] = []
    kept_matches: List[TermMatch] = []

    for m in sorted_matches:
        if not any(max(m.start, k_start) < min(m.end, k_end) for k_start, k_end in kept_spans):
            kept_spans.append((m.start, m.end))
            kept_matches.append(m)

    kept_matches.sort(key=lambda m: m.start)

    final_extracted: List[str] = []
    for m in kept_matches:
        if m.cleaned not in final_extracted:
            final_extracted.append(m.cleaned)

    return final_extracted


def normalize_component(comp: str) -> Tuple[str, bool]:
    """
    Normalize an extracted component string into a bare Python/code identifier.
    Returns (normalized_name, is_code_searchable).
    """
    cleaned = comp.strip()

    # Rule 1: Spec / Backlog tags matching (SPEC|HIB|T1|T2|T3|T4)-...
    tag_pattern = re.compile(r'^(?:SPEC|HIB|T1|T2|T3|T4)\-[A-Za-z0-9_\-]+(?:\.md)?$', re.IGNORECASE)
    if tag_pattern.match(cleaned):
        return cleaned, False

    # Rule 2 & 3: Filenames (.py, .yaml, .yml, .json, .md)
    for ext in ['.py', '.yaml', '.yml', '.json', '.md', '.jsonl']:
        if cleaned.lower().endswith(ext):
            stem = Path(cleaned).stem
            if tag_pattern.match(stem):
                return stem, False
            return stem, True

    # Rule 4: Function call ending in ()
    if cleaned.endswith('()'):
        return cleaned[:-2].strip(), True

    # Rule 5: Keyword argument ending in =
    if cleaned.endswith('='):
        return cleaned[:-1].strip(), True

    # Leading hyphen cleanup if present
    if cleaned.startswith('-'):
        cleaned = cleaned.lstrip('-')

    return cleaned, True


def find_test_files(repo_root: Path) -> List[Path]:
    """Find all Python test files in tests/, tests/integration/, tests/e2e/."""
    test_dirs = [
        repo_root / "tests",
        repo_root / "tests" / "integration",
        repo_root / "tests" / "e2e",
    ]
    files: List[Path] = []
    for d in test_dirs:
        if d.exists():
            for p in d.rglob("*.py"):
                if p.is_file() and (p.name.startswith("test_") or p.name.endswith("_test.py")):
                    if "test_project" in p.parts or "data" in p.parts or "fixtures" in p.parts:
                        continue
                    if p not in files:
                        files.append(p)
    return sorted(files)


# Global AST Cache for test files to optimize performance
AST_CACHE: Dict[Path, Tuple[Optional[ast.AST], bool]] = {}


def get_parsed_test_file(file_path: Path) -> Tuple[Optional[ast.AST], bool]:
    """Parse test file once and cache AST tree and file_has_assert flag."""
    if file_path not in AST_CACHE:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            file_has_assert = any(isinstance(node, ast.Assert) for node in ast.walk(tree))
            AST_CACHE[file_path] = (tree, file_has_assert)
        except Exception:
            AST_CACHE[file_path] = (None, False)
    return AST_CACHE[file_path]


def inspect_test_file_for_target(file_path: Path, target_name: str) -> List[Tuple[str, bool, bool]]:
    """
    Parse a test file with AST and find references to target_name.
    Returns list of tuples: (func_name, has_assert, is_mocked).
    """
    tree, file_has_assert = get_parsed_test_file(file_path)
    if not tree:
        return []

    target_symbols: Set[str] = {target_name}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == target_name:
                    target_symbols.add(alias.asname or alias.name)
                elif alias.name.endswith("." + target_name):
                    target_symbols.add(alias.asname or target_name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == target_name or node.module.endswith("." + target_name)):
                for alias in node.names:
                    target_symbols.add(alias.asname or alias.name)

    results: List[Tuple[str, bool, bool]] = []
    file_has_assert = any(isinstance(node, ast.Assert) for node in ast.walk(tree))

    def node_references_target(node: ast.AST) -> bool:
        if isinstance(node, ast.Name) and node.id in target_symbols:
            return True
        if isinstance(node, ast.Attribute) and node.attr in target_symbols:
            return True
        if isinstance(node, ast.keyword) and node.arg in target_symbols:
            return True
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if (alias.name in target_symbols) or (alias.asname and alias.asname in target_symbols):
                    return True
            if isinstance(node, ast.ImportFrom) and node.module:
                if any(mod_part in target_symbols for mod_part in node.module.split('.')):
                    return True
        return False

    def check_is_mocked(func_node: Optional[ast.AST]) -> bool:
        nodes_to_check = [tree]
        if func_node:
            nodes_to_check.append(func_node)

        for container in nodes_to_check:
            for n in ast.walk(container):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    for dec in n.decorator_list:
                        dec_str = ast.dump(dec)
                        if "patch" in dec_str and any(sym in dec_str for sym in target_symbols):
                            return True
                if isinstance(n, (ast.With, ast.AsyncWith)):
                    for item in n.items:
                        with_str = ast.dump(item.context_expr)
                        if "patch" in with_str and any(sym in with_str for sym in target_symbols):
                            return True
                if isinstance(n, ast.Call):
                    call_str = ast.dump(n)
                    if "monkeypatch" in call_str and any(sym in call_str for sym in target_symbols):
                        return True
                    if ("MagicMock" in call_str or "Mock(" in call_str) and any(sym in call_str for sym in target_symbols):
                        return True
        return False

    top_level_refs = False

    local_functions = {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_name = node.name
            func_has_ref = False
            func_has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(node))
            
            for child in ast.walk(node):
                if node_references_target(child):
                    func_has_ref = True
                    break

            if not func_has_ref:
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        callee_name = child.func.id
                        if callee_name in local_functions:
                            callee_node = local_functions[callee_name]
                            for callee_child in ast.walk(callee_node):
                                if node_references_target(callee_child):
                                    func_has_ref = True
                                    break
                    if func_has_ref:
                        break

            if func_has_ref:
                is_mocked = check_is_mocked(node)
                results.append((func_name, func_has_assert, is_mocked))
        else:
            if node_references_target(node):
                top_level_refs = True

    if top_level_refs and not any(r[0] == "" for r in results):
        results.append(("", file_has_assert, False))

    return results


def search_component(comp: str, repo_root: Path) -> ComponentMatch:
    """
    Search for a component reference across the test suite using AST analysis and mock classification.
    """
    norm_name, is_searchable = normalize_component(comp)

    if not is_searchable:
        return ComponentMatch(
            raw_component=comp,
            normalized_name=norm_name,
            is_code_searchable=False,
            match_tier="none",
            mock_status="n/a",
        )

    test_files = find_test_files(repo_root)

    best_tier = "none"
    best_mock = "n/a"
    matching_files: List[str] = []
    matching_functions: List[str] = []

    for tf in test_files:
        rel_tf = str(tf.relative_to(repo_root)).replace("\\", "/")
        refs = inspect_test_file_for_target(tf, norm_name)
        if not refs:
            continue

        for func_name, has_assert, is_mocked in refs:
            if has_assert and func_name:
                tier = "function"
                mock_str = "MOCKED" if is_mocked else "REAL"
            else:
                tier = "file"
                mock_str = "n/a"

            if tier == "function":
                if best_tier != "function":
                    best_tier = "function"
                    best_mock = mock_str
                elif mock_str == "REAL" and best_mock == "MOCKED":
                    best_mock = "REAL"

                if rel_tf not in matching_files:
                    matching_files.append(rel_tf)
                if func_name and func_name not in matching_functions:
                    matching_functions.append(func_name)

            elif tier == "file" and best_tier == "none":
                best_tier = "file"
                best_mock = "n/a"
                if rel_tf not in matching_files:
                    matching_files.append(rel_tf)

    return ComponentMatch(
        raw_component=comp,
        normalized_name=norm_name,
        is_code_searchable=is_searchable,
        match_tier=best_tier,
        mock_status=best_mock,
        matching_files=matching_files,
        matching_functions=matching_functions,
    )


def check_assert_keyterm_overlap(file_path: Path, func_name: str, key_terms: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if any ast.Assert node in func_name of file_path references any key term from key_terms.
    Returns (has_overlap, matched_key_terms).
    """
    if not key_terms:
        return False, []

    tree, _ = get_parsed_test_file(file_path)
    if not tree:
        return False, []

    matched_key_terms: Set[str] = set()

    target_func = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            target_func = node
            break

    if not target_func:
        return False, []

    assert_tokens: Set[str] = set()
    for node in ast.walk(target_func):
        if isinstance(node, ast.Assert):
            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    assert_tokens.add(child.id.lower())
                elif isinstance(child, ast.Attribute):
                    assert_tokens.add(child.attr.lower())
                elif isinstance(child, ast.keyword) and child.arg:
                    assert_tokens.add(child.arg.lower())
                elif isinstance(child, ast.Constant) and isinstance(child.value, str):
                    val_lower = child.value.lower()
                    assert_tokens.add(val_lower)
                    for token in re.findall(r'\b[A-Za-z0-9_\-]+\b', val_lower):
                        assert_tokens.add(token)

    for kt in key_terms:
        cleaned_kt = kt.strip().lower()
        if cleaned_kt.endswith('()'):
            cleaned_kt = cleaned_kt[:-2]
        if cleaned_kt.endswith('='):
            cleaned_kt = cleaned_kt[:-1]
        
        if cleaned_kt in assert_tokens:
            matched_key_terms.add(kt)
        else:
            for at in assert_tokens:
                if cleaned_kt in at or at in cleaned_kt:
                    matched_key_terms.add(kt)
                    break

    matched_list = sorted(list(matched_key_terms))
    return (len(matched_list) > 0, matched_list)


def classify_scenario(scenario: Scenario, repo_root: Path) -> ScenarioResult:
    """
    Perform Stage 3 final verification classification for a scenario across all its extracted components.
    """
    comp_results: List[ComponentResult] = []

    searchable_comps = [c for c in scenario.components if normalize_component(c)[1]]

    if not searchable_comps:
        for raw_c in scenario.components:
            norm, is_search = normalize_component(raw_c)
            comp_results.append(ComponentResult(
                raw_component=raw_c,
                normalized_name=norm,
                is_code_searchable=is_search,
                match_tier="none",
                mock_status="n/a",
                matching_files=[],
                matching_functions=[],
                then_overlap_found=False,
                matched_key_terms=[],
                is_confirmed=False,
            ))
        return ScenarioResult(
            scenario=scenario,
            component_results=comp_results,
            final_status="SKIPPED",
            status_reason="No code-searchable components extracted from Given/When clauses."
        )

    all_confirmed = True
    any_mocked = False

    for raw_c in scenario.components:
        comp_match = search_component(raw_c, repo_root)

        if not comp_match.is_code_searchable:
            comp_results.append(ComponentResult(
                raw_component=raw_c,
                normalized_name=comp_match.normalized_name,
                is_code_searchable=False,
                match_tier="none",
                mock_status="n/a",
                matching_files=[],
                matching_functions=[],
                then_overlap_found=False,
                matched_key_terms=[],
                is_confirmed=False,
            ))
            continue

        has_overlap = False
        matched_kt: List[str] = []

        if comp_match.match_tier == "function":
            for mf_file in comp_match.matching_files:
                for mf_func in comp_match.matching_functions:
                    full_p = repo_root / mf_file
                    ov, kts = check_assert_keyterm_overlap(full_p, mf_func, scenario.key_terms)
                    if ov:
                        has_overlap = True
                        for k in kts:
                            if k not in matched_kt:
                                matched_kt.append(k)

        is_conf = (comp_match.match_tier == "function") and (has_overlap or not scenario.key_terms)

        if is_conf:
            if comp_match.mock_status == "MOCKED":
                any_mocked = True
        else:
            all_confirmed = False

        comp_results.append(ComponentResult(
            raw_component=raw_c,
            normalized_name=comp_match.normalized_name,
            is_code_searchable=True,
            match_tier=comp_match.match_tier,
            mock_status=comp_match.mock_status,
            matching_files=comp_match.matching_files,
            matching_functions=comp_match.matching_functions,
            then_overlap_found=has_overlap,
            matched_key_terms=matched_kt,
            is_confirmed=is_conf,
        ))

    if all_confirmed:
        final_status = "VERIFIED (mock only)" if any_mocked else "VERIFIED (real entry point)"
        reason = "All code-searchable components have confirmed test matches and Then-clause assertion overlap."
    else:
        final_status = "UNVERIFIED"
        unconf_names = [cr.normalized_name for cr in comp_results if cr.is_code_searchable and not cr.is_confirmed]
        reason = f"Unconfirmed code-searchable component(s): {', '.join(unconf_names)}"

    return ScenarioResult(
        scenario=scenario,
        component_results=comp_results,
        final_status=final_status,
        status_reason=reason,
    )


def parse_spec_file(spec_path: Path) -> List[Scenario]:
    """
    Parse a single markdown spec file for ### Scenario: blocks.
    Returns a list of Scenario objects. If no Gherkin scenario blocks exist, returns empty list.
    """
    try:
        content = spec_path.read_text(encoding="utf-8")
    except Exception as e:
        safe_print(f"Error reading {spec_path}: {e}", file=sys.stderr)
        return []

    lines = content.splitlines()
    scenarios: List[Scenario] = []
    
    current_scenario: Optional[Scenario] = None
    active_clause: Optional[str] = None

    header_pattern = re.compile(r'^###\s+Scenario(?:\s+([A-Za-z0-9_\-\.]+))?:?\s*(.*)$', re.IGNORECASE)

    for line in lines:
        stripped_line = line.strip()

        if stripped_line.startswith("### Scenario"):
            if current_scenario:
                given_when_text = "\n".join(current_scenario.given_clauses + current_scenario.when_clauses)
                then_text = "\n".join(current_scenario.then_clauses)
                current_scenario.components = extract_terms(given_when_text)
                current_scenario.key_terms = extract_terms(then_text)
                scenarios.append(current_scenario)
                current_scenario = None

            match = header_pattern.match(stripped_line)
            if match:
                scen_num = match.group(1) or ""
                scen_title = match.group(2) or ""
                
                if scen_num and not scen_num.lower().startswith("scenario"):
                    scen_id = f"Scenario {scen_num}"
                elif scen_num:
                    scen_id = scen_num
                else:
                    scen_id = "Scenario"
                
                if not scen_title and ":" in stripped_line:
                    scen_title = stripped_line.split(":", 1)[1].strip()

                current_scenario = Scenario(
                    spec_path=spec_path,
                    scenario_id=scen_id,
                    title=scen_title,
                )
                active_clause = None
            continue

        if not current_scenario:
            continue

        if stripped_line.startswith("## ") or stripped_line.startswith("# ") or stripped_line.startswith("---"):
            given_when_text = "\n".join(current_scenario.given_clauses + current_scenario.when_clauses)
            then_text = "\n".join(current_scenario.then_clauses)
            current_scenario.components = extract_terms(given_when_text)
            current_scenario.key_terms = extract_terms(then_text)
            scenarios.append(current_scenario)
            current_scenario = None
            active_clause = None
            continue

        if stripped_line.startswith("Given ") or stripped_line.startswith("Given\t"):
            clause_text = stripped_line[6:].strip()
            current_scenario.given_clauses.append(clause_text)
            active_clause = "given"
        elif stripped_line.startswith("When ") or stripped_line.startswith("When\t"):
            clause_text = stripped_line[5:].strip()
            current_scenario.when_clauses.append(clause_text)
            active_clause = "when"
        elif stripped_line.startswith("Then ") or stripped_line.startswith("Then\t"):
            clause_text = stripped_line[5:].strip()
            current_scenario.then_clauses.append(clause_text)
            active_clause = "then"
        elif stripped_line.startswith("And ") or stripped_line.startswith("And\t"):
            clause_text = stripped_line[4:].strip()
            if active_clause == "given":
                current_scenario.given_clauses.append(clause_text)
            elif active_clause == "when":
                current_scenario.when_clauses.append(clause_text)
            elif active_clause == "then":
                current_scenario.then_clauses.append(clause_text)
        elif stripped_line:
            if active_clause == "given" and current_scenario.given_clauses:
                current_scenario.given_clauses[-1] += " " + stripped_line
            elif active_clause == "when" and current_scenario.when_clauses:
                current_scenario.when_clauses[-1] += " " + stripped_line
            elif active_clause == "then" and current_scenario.then_clauses:
                current_scenario.then_clauses[-1] += " " + stripped_line

    if current_scenario:
        given_when_text = "\n".join(current_scenario.given_clauses + current_scenario.when_clauses)
        then_text = "\n".join(current_scenario.then_clauses)
        current_scenario.components = extract_terms(given_when_text)
        current_scenario.key_terms = extract_terms(then_text)
        scenarios.append(current_scenario)

    return scenarios


def run_stage1_self_test(spec_path: Path) -> bool:
    """Run parser self-test against SPEC-loop-closure-verification.md."""
    safe_print("=" * 80)
    safe_print("RUNNING STAGE 1 PARSER SELF-TEST AGAINST SPEC-loop-closure-verification.md")
    safe_print("=" * 80)

    scenarios = parse_spec_file(spec_path)
    scen_map = {s.scenario_id.lower().replace(":", "").strip(): s for s in scenarios}

    target_ids = ["scenario 3", "scenario 4", "scenario 4b", "scenario 4c", "scenario 5", "scenario 6"]
    
    passed = True
    for target in target_ids:
        scen = scen_map.get(target)
        if not scen:
            matches = [s for s in scenarios if target in s.scenario_id.lower()]
            if matches:
                scen = matches[0]

        if not scen:
            safe_print(f"[FAIL] Could not find {target} in parsed scenarios!")
            passed = False
            continue

        safe_print(f"\n--- [{scen.scenario_id}: {scen.title}] ---")
        safe_print(f"Given Clauses ({len(scen.given_clauses)}):")
        for g in scen.given_clauses:
            safe_print(f"  - {g}")
        safe_print(f"When Clauses ({len(scen.when_clauses)}):")
        for w in scen.when_clauses:
            safe_print(f"  - {w}")
        safe_print(f"Then Clauses ({len(scen.then_clauses)}):")
        for t in scen.then_clauses:
            safe_print(f"  - {t}")
        safe_print(f"Extracted Components: {scen.components}")
        safe_print(f"Extracted Key Terms:  {scen.key_terms}")

        if not scen.given_clauses or not scen.when_clauses or not scen.then_clauses:
            safe_print(f"[FAIL] {scen.scenario_id} missing one or more clauses!")
            passed = False
        else:
            safe_print(f"[PASS] {scen.scenario_id} clause structure parsed successfully.")

    if passed:
        safe_print("\n[PASS] STAGE 1 SELF-TEST PASSED CLEANLY.")
    else:
        safe_print("\n[FAIL] STAGE 1 SELF-TEST FAILED!")
    
    return passed


def run_stage2_self_test(repo_root: Path) -> bool:
    """
    Mandatory Stage 2 Self-Test: Run component reference matcher against 3 known ground truth cases + tag check.
    """
    safe_print("\n" + "=" * 80)
    safe_print("RUNNING STAGE 2 MATCHER & CLASSIFIER SELF-TEST (3 KNOWN CASES + TAG CHECK)")
    safe_print("=" * 80)

    all_passed = True

    # Case 1: disposition() in tests/integration/test_posture.py
    m1 = search_component("disposition()", repo_root)
    safe_print(f"\n--- Case 1: 'disposition()' ---")
    safe_print(f"Normalized Name:    {m1.normalized_name}")
    safe_print(f"Code Searchable:    {m1.is_code_searchable}")
    safe_print(f"Match Tier:         {m1.match_tier}")
    safe_print(f"Mock Status:        {m1.mock_status}")
    safe_print(f"Matching Files:     {m1.matching_files}")
    safe_print(f"Matching Functions: {m1.matching_functions}")

    c1_ok = (
        m1.is_code_searchable is True and
        m1.match_tier == "function" and
        m1.mock_status == "REAL" and
        any("test_posture.py" in f for f in m1.matching_files)
    )
    if c1_ok:
        safe_print("[PASS] Case 1 matched expected ground truth (function, REAL in test_posture.py).")
    else:
        safe_print(f"[FAIL] Case 1 expected (function, REAL in test_posture.py), got ({m1.match_tier}, {m1.mock_status}).")
        all_passed = False

    # Case 2: architecture_checks.py in tests/test_architecture_checks.py
    m2 = search_component("architecture_checks.py", repo_root)
    safe_print(f"\n--- Case 2: 'architecture_checks.py' ---")
    safe_print(f"Normalized Name:    {m2.normalized_name}")
    safe_print(f"Code Searchable:    {m2.is_code_searchable}")
    safe_print(f"Match Tier:         {m2.match_tier}")
    safe_print(f"Mock Status:        {m2.mock_status}")
    safe_print(f"Matching Files:     {m2.matching_files}")
    safe_print(f"Matching Functions: {m2.matching_functions}")

    c2_ok = (
        m2.is_code_searchable is True and
        m2.match_tier == "function" and
        m2.mock_status == "REAL" and
        any("test_architecture_checks.py" in f for f in m2.matching_files)
    )
    if c2_ok:
        safe_print("[PASS] Case 2 matched expected ground truth (function, REAL in test_architecture_checks.py).")
    else:
        safe_print(f"[FAIL] Case 2 expected (function, REAL in test_architecture_checks.py), got ({m2.match_tier}, {m2.mock_status}).")
        all_passed = False

    # Case 3: Uncovered broken/obscure component: retention_cleanup.py
    m3 = search_component("retention_cleanup.py", repo_root)
    safe_print(f"\n--- Case 3: 'retention_cleanup.py' (Uncovered Component) ---")
    safe_print(f"Normalized Name:    {m3.normalized_name}")
    safe_print(f"Code Searchable:    {m3.is_code_searchable}")
    safe_print(f"Match Tier:         {m3.match_tier}")
    safe_print(f"Mock Status:        {m3.mock_status}")
    safe_print(f"Matching Files:     {m3.matching_files}")

    c3_ok = (
        m3.is_code_searchable is True and
        m3.match_tier == "none" and
        m3.mock_status == "n/a" and
        len(m3.matching_files) == 0
    )
    if c3_ok:
        safe_print("[PASS] Case 3 matched expected ground truth (none, n/a for uncovered component).")
    else:
        safe_print(f"[FAIL] Case 3 expected (none, n/a), got ({m3.match_tier}, {m3.mock_status}).")
        all_passed = False

    # Case 4: Tag check (non-code-searchable component like HIB-080)
    m4 = search_component("HIB-080", repo_root)
    safe_print(f"\n--- Tag Check: 'HIB-080' ---")
    safe_print(f"Normalized Name:    {m4.normalized_name}")
    safe_print(f"Code Searchable:    {m4.is_code_searchable}")
    safe_print(f"Match Tier:         {m4.match_tier}")
    safe_print(f"Mock Status:        {m4.mock_status}")

    c4_ok = (
        m4.is_code_searchable is False and
        m4.match_tier == "none" and
        m4.mock_status == "n/a"
    )
    if c4_ok:
        safe_print("[PASS] Tag Check matched expected ground truth (is_code_searchable=False, none, n/a).")
    else:
        safe_print(f"[FAIL] Tag Check expected (is_code_searchable=False), got ({m4.is_code_searchable}).")
        all_passed = False

    if all_passed:
        safe_print("\n[PASS] STAGE 2 SELF-TEST PASSED CLEANLY FOR ALL 3 CASES + TAG CHECK.")
    else:
        safe_print("\n[FAIL] STAGE 2 SELF-TEST FAILED!")

    return all_passed


def run_scenario3_reasoning_trace(self_spec_path: Path, repo_root: Path) -> ScenarioResult:
    """
    Run Stage 3 full classifier against Scenario 3 specifically and print complete reasoning trace.
    """
    safe_print("\n" + "=" * 80)
    safe_print("STAGE 3 REASONING TRACE: SCENARIO 3 (HIB-080 RETROACTIVE SCENARIO)")
    safe_print("=" * 80)

    scenarios = parse_spec_file(self_spec_path)
    scen3 = [s for s in scenarios if "Scenario 3" in s.scenario_id][0]

    res = classify_scenario(scen3, repo_root)

    safe_print(f"Scenario ID:    {res.scenario.scenario_id}")
    safe_print(f"Scenario Title: {res.scenario.title}")
    safe_print(f"Given Clauses:  {res.scenario.given_clauses}")
    safe_print(f"When Clauses:   {res.scenario.when_clauses}")
    safe_print(f"Then Clauses:   {res.scenario.then_clauses}")
    safe_print(f"Extracted Components: {res.scenario.components}")
    safe_print(f"Extracted Key Terms:  {res.scenario.key_terms}")
    safe_print("-" * 80)

    for c_res in res.component_results:
        safe_print(f"\nComponent: '{c_res.raw_component}' (Normalized: '{c_res.normalized_name}')")
        safe_print(f"  - Code Searchable:    {c_res.is_code_searchable}")
        if not c_res.is_code_searchable:
            safe_print("  - Action: Marked non-code-searchable tag -> skipped.")
            continue
        safe_print(f"  - Match Tier:         {c_res.match_tier}")
        safe_print(f"  - Mock Status:        {c_res.mock_status}")
        safe_print(f"  - Matching Files:     {c_res.matching_files}")
        safe_print(f"  - Matching Functions: {c_res.matching_functions}")
        safe_print(f"  - Then Overlap Found: {c_res.then_overlap_found}")
        safe_print(f"  - Matched Key Terms:  {c_res.matched_key_terms}")
        safe_print(f"  - Component Confirmed:{c_res.is_confirmed}")

    safe_print("-" * 80)
    safe_print(f"FINAL CLASSIFICATION: {res.final_status}")
    safe_print(f"STATUS REASON:        {res.status_reason}")
    safe_print("=" * 80)

    return res


def scan_corpus(specs_dir: Path) -> Tuple[int, int, List[Scenario]]:
    """
    Scan all .md files under specs_dir (including archive/) for Gherkin scenarios.
    Returns (total_specs_scanned, total_specs_skipped, all_extracted_scenarios).
    """
    total_scanned = 0
    total_skipped = 0
    all_scenarios: List[Scenario] = []

    spec_files = sorted(specs_dir.rglob("*.md"))

    for spec_file in spec_files:
        total_scanned += 1
        scenarios = parse_spec_file(spec_file)
        if scenarios:
            all_scenarios.extend(scenarios)
        else:
            total_skipped += 1

    return total_scanned, total_skipped, all_scenarios


def generate_loop_closure_report(repo_root: Path, specs_dir: Path, output_file: Path) -> Tuple[Dict[str, int], List[ScenarioResult]]:
    """
    Run full corpus classification and write .agent/state/loop_closure_report.md matching wiki_lint_findings.md style.
    """
    total_scanned, total_skipped, scenarios = scan_corpus(specs_dir)

    results: List[ScenarioResult] = []
    for s in scenarios:
        res = classify_scenario(s, repo_root)
        results.append(res)

    status_counts = {
        "VERIFIED (real entry point)": 0,
        "VERIFIED (mock only)": 0,
        "UNVERIFIED": 0,
        "SKIPPED": 0,
    }

    for r in results:
        status_counts[r.final_status] = status_counts.get(r.final_status, 0) + 1

    # Pick a genuine mix across different spec files and component types.
    scenarios_by_spec = {}
    for r in results:
        spec_name = r.scenario.spec_path.name
        if spec_name not in scenarios_by_spec:
            scenarios_by_spec[spec_name] = []
        scenarios_by_spec[spec_name].append(r)
    
    raw_sample = []
    while len(raw_sample) < 10 and scenarios_by_spec:
        for spec_name in list(scenarios_by_spec.keys()):
            if len(raw_sample) >= 10: break
            if scenarios_by_spec[spec_name]:
                raw_sample.append(scenarios_by_spec[spec_name].pop(0))
            else:
                del scenarios_by_spec[spec_name]

    report_lines: List[str] = [
        "# Loop Closure Verification Report",
        f"**Run Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"**Status**: 🟢 FULL CORPUS VERIFICATION COMPLETED",
        "",
        "## Summary",
        f"- **Total Spec Files Scanned**: {total_scanned}",
        f"- **Legacy Specs Skipped (No Gherkin)**: {total_skipped}",
        f"- **Total Scenarios Evaluated**: {len(scenarios)}",
        f"- **✅ VERIFIED (Real Entry Point)**: {status_counts['VERIFIED (real entry point)']}",
        f"- **✅ VERIFIED (Mock Only)**: {status_counts['VERIFIED (mock only)']}",
        f"- **❌ UNVERIFIED**: {status_counts['UNVERIFIED']}",
        f"- **⏭️ SKIPPED (Non-Code / Tags)**: {status_counts['SKIPPED']}",
        "",
        "---",
        "",
        "## Scenario 1b Calibration & Error Rate Audit",
        "Per SPEC-loop-closure-verification A 5, the following 10 scenarios represent raw data for manual calibration. This is raw data for manual review, not a completed calibration. The FP/FN rate has not yet been computed.",
        "",
        "| # | Spec File | Scenario ID & Title | Components | Mocked | Then-Overlap | Final Classification |",
        "|---|---|---|---|---|---|---|",
    ]

    for idx, r in enumerate(raw_sample, 1):
        rel_spec = str(r.scenario.spec_path.relative_to(repo_root)).replace("\\", "/")
        spec_link = f"[{Path(rel_spec).name}](file:///{r.scenario.spec_path.as_posix()})"
        scen_title = f"{r.scenario.scenario_id}: {r.scenario.title}"
        components = ", ".join([c.normalized_name for c in r.component_results if c.is_code_searchable])
        
        is_mocked = any(c.mock_status == "MOCKED" for c in r.component_results)
        mock_str = "Yes" if is_mocked else "No"
        
        then_overlap = any(c.then_overlap_found for c in r.component_results)
        then_str = "Yes" if then_overlap else "No"
        
        report_lines.append(f"| {idx} | {spec_link} | {scen_title} | `{components}` | {mock_str} | {then_str} | `{r.final_status}` |")

    report_lines.extend([
        "",
        "---",
        "",
        "## ❌ UNVERIFIED Scenarios",
    ])

    unverif_scenarios = [r for r in results if r.final_status == "UNVERIFIED"]
    if not unverif_scenarios:
        report_lines.append("None — all scenarios verified cleanly.")
    else:
        for r in unverif_scenarios:
            rel_spec = str(r.scenario.spec_path.relative_to(repo_root)).replace("\\", "/")
            spec_link = f"[{Path(rel_spec).name}](file:///{r.scenario.spec_path.as_posix()})"
            report_lines.append(f"### `{r.scenario.scenario_id}` in {spec_link}")
            report_lines.append(f"- **Title**: {r.scenario.title}")
            report_lines.append(f"- **Status Reason**: {r.status_reason}")
            for cr in r.component_results:
                if cr.is_code_searchable:
                    st = "CONFIRMED" if cr.is_confirmed else "UNCONFIRMED"
                    report_lines.append(f"  - Component `{cr.raw_component}` (`{cr.normalized_name}`): Tier={cr.match_tier}, Mock={cr.mock_status}, AssertOverlap={cr.then_overlap_found} -> **{st}**")
            report_lines.append("")

    report_lines.extend([
        "## 🟢 VERIFIED Scenarios (Real Entry Point)",
    ])

    verif_real_scenarios = [r for r in results if r.final_status == "VERIFIED (real entry point)"]
    if not verif_real_scenarios:
        report_lines.append("None.")
    else:
        for r in verif_real_scenarios:
            rel_spec = str(r.scenario.spec_path.relative_to(repo_root)).replace("\\", "/")
            spec_link = f"[{Path(rel_spec).name}](file:///{r.scenario.spec_path.as_posix()})"
            report_lines.append(f"### `{r.scenario.scenario_id}` in {spec_link}")
            report_lines.append(f"- **Title**: {r.scenario.title}")
            for cr in r.component_results:
                if cr.is_code_searchable:
                    report_lines.append(f"  - Component `{cr.raw_component}` (`{cr.normalized_name}`): Matched in `{cr.matching_files[:1]}` ({cr.matching_functions[:1]})")
            report_lines.append("")

    report_lines.extend([
        "## 🟡 VERIFIED Scenarios (Mock Only)",
    ])

    verif_mock_scenarios = [r for r in results if r.final_status == "VERIFIED (mock only)"]
    if not verif_mock_scenarios:
        report_lines.append("None.")
    else:
        for r in verif_mock_scenarios:
            rel_spec = str(r.scenario.spec_path.relative_to(repo_root)).replace("\\", "/")
            spec_link = f"[{Path(rel_spec).name}](file:///{r.scenario.spec_path.as_posix()})"
            report_lines.append(f"### `{r.scenario.scenario_id}` in {spec_link}")
            report_lines.append(f"- **Title**: {r.scenario.title}")
            for cr in r.component_results:
                if cr.is_code_searchable:
                    report_lines.append(f"  - Component `{cr.raw_component}` (`{cr.normalized_name}`): Matched in `{cr.matching_files[:1]}` (Mocked: {cr.mock_status})")
            report_lines.append("")

    report_lines.extend([
        "## ⚪ SKIPPED Scenarios (Non-Code / Spec Tags)",
    ])
    skipped_scenarios = [r for r in results if r.final_status == "SKIPPED"]
    report_lines.append(f"Total skipped scenarios: {len(skipped_scenarios)} (all components are spec/backlog tags or non-code text).")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(report_lines), encoding="utf-8")

    stats = {
        "total_scanned": total_scanned,
        "total_skipped": total_skipped,
        "total_scenarios": len(scenarios),
        "verified_real": status_counts["VERIFIED (real entry point)"],
        "verified_mock": status_counts["VERIFIED (mock only)"],
        "unverified": status_counts["UNVERIFIED"],
        "skipped": status_counts["SKIPPED"],
    }

    return stats, results


def main():
    repo_root = Path(__file__).resolve().parents[2]
    self_spec_path = repo_root / "docs" / "planning" / "specs" / "SPEC-loop-closure-verification.md"
    specs_dir = repo_root / "docs" / "planning" / "specs"
    output_report = repo_root / ".agent" / "state" / "loop_closure_report.md"

    # Stage 1 Self-Test
    stage1_ok = run_stage1_self_test(self_spec_path)
    if not stage1_ok:
        safe_print("\nAborting: Stage 1 self-test failed.", file=sys.stderr)
        sys.exit(1)

    # Stage 2 Self-Test
    stage2_ok = run_stage2_self_test(repo_root)
    if not stage2_ok:
        safe_print("\nAborting: Stage 2 self-test failed.", file=sys.stderr)
        sys.exit(1)

    # Stage 3 Reasoning Trace for Scenario 3
    run_scenario3_reasoning_trace(self_spec_path, repo_root)

    # Full Corpus Run & Report Generation
    safe_print("\n" + "=" * 80)
    safe_print("RUNNING FULL CORPUS CLASSIFIER & GENERATING LOOP CLOSURE REPORT")
    safe_print("=" * 80)

    stats, results = generate_loop_closure_report(repo_root, specs_dir, output_report)

    safe_print(f"Total Specs Scanned:             {stats['total_scanned']}")
    safe_print(f"Total Specs Skipped (no Gherkin): {stats['total_skipped']}")
    safe_print(f"Total Scenarios Evaluated:       {stats['total_scenarios']}")
    safe_print(f"  - VERIFIED (Real Entry Point): {stats['verified_real']}")
    safe_print(f"  - VERIFIED (Mock Only):        {stats['verified_mock']}")
    safe_print(f"  - UNVERIFIED:                  {stats['unverified']}")
    safe_print(f"  - SKIPPED:                     {stats['skipped']}")
    safe_print(f"\nReport written to {output_report}")
    safe_print("Stage 3 verification complete.")


if __name__ == "__main__":
    main()
