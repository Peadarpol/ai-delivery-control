import ast
import sys
import yaml
from typing import Literal

def is_vacuous(node: ast.expr) -> bool:
    """
    Determines if an AST node representing an argument value is "vacuous".
    A hardcoded literal (like None, [], {}, or a string/number) is vacuous.
    Genuine data must come from variables (ast.Name), function results (ast.Call), 
    or attribute accesses (ast.Attribute).
    """
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(is_vacuous(elt) for elt in node.elts)
    if isinstance(node, ast.Dict):
        return all(is_vacuous(val) for val in node.values)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == 'set' and not node.args:
            return True
    return False

def check_dict_key_access(tree: ast.AST, variable_name: str, field: str) -> str:
    """
    Checks for dict key access (read and non-vacuous write).
    Both a read and a non-vacuous write must be found to return WIRED.
    If one is missing, or the write is vacuous, it returns PARTIALLY-WIRED.
    If neither is found, returns NOT-WIRED.
    
    Why this two-sided requirement?
    Unlike keyword arguments or bare attribute accesses where a reference inherently 
    pulls or supplies the artifact's state, a dictionary tracking accumulated state 
    (like session.json usage) requires both sides to be "wired" to the real world: 
    it must be consulted (read) against business logic (like budgets) and updated (written) 
    with real computed values. An un-read field is dead code; an un-written field 
    tracks nothing. Thus, both are required for WIRED.
    """
    has_read = False
    has_non_vacuous_write = False
    has_vacuous_write = False
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Subscript):
                    if isinstance(target.value, ast.Name) and target.value.id == variable_name:
                        slice_val = target.slice
                        if hasattr(ast, 'Index') and isinstance(slice_val, getattr(ast, 'Index')):
                            slice_val = slice_val.value
                        if isinstance(slice_val, ast.Constant) and slice_val.value == field:
                            val_to_check = node.value
                            if is_vacuous(val_to_check):
                                has_vacuous_write = True
                            else:
                                has_non_vacuous_write = True
                                
        elif isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == variable_name:
                slice_val = node.slice
                if hasattr(ast, 'Index') and isinstance(slice_val, getattr(ast, 'Index')):
                    slice_val = slice_val.value
                if isinstance(slice_val, ast.Constant) and slice_val.value == field:
                    if isinstance(node.ctx, ast.Load):
                        has_read = True
                        
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id == variable_name and node.func.attr in ('get', 'setdefault'):
                    if len(node.args) > 0:
                        first_arg = node.args[0]
                        if isinstance(first_arg, ast.Constant) and first_arg.value == field:
                            has_read = True
                            if node.func.attr == 'setdefault':
                                if len(node.args) > 1:
                                    val_to_check = node.args[1]
                                    if is_vacuous(val_to_check):
                                        has_vacuous_write = True
                                    else:
                                        has_non_vacuous_write = True
                                else:
                                    has_vacuous_write = True
                                    
    if has_read and has_non_vacuous_write:
        return "WIRED"
    elif has_read or has_non_vacuous_write or has_vacuous_write:
        return "PARTIALLY-WIRED"
    else:
        return "NOT-WIRED"

def check_keyword_arg(tree: ast.AST, function_name: str, field: str) -> str:
    status = "NOT-WIRED"
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            is_func = False
            if isinstance(node.func, ast.Name) and node.func.id == function_name:
                is_func = True
            elif isinstance(node.func, ast.Attribute) and node.func.attr == function_name:
                is_func = True
                
            if is_func:
                for kw in node.keywords:
                    if kw.arg == field:
                        if is_vacuous(kw.value):
                            if status == "NOT-WIRED":
                                status = "PARTIALLY-WIRED"
                        else:
                            return "WIRED"
    return status

def check_attribute_access(tree: ast.AST, variable_name: str, field: str) -> str:
    status = "NOT-WIRED"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            elif isinstance(node, ast.AugAssign):
                targets = [node.target]
                
            for target in targets:
                if isinstance(target, ast.Attribute):
                    if isinstance(target.value, ast.Name) and target.value.id == variable_name and target.attr == field:
                        val_to_check = node.value
                        if is_vacuous(val_to_check):
                            if status == "NOT-WIRED":
                                status = "PARTIALLY-WIRED"
                        else:
                            return "WIRED"
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == variable_name and node.attr == field:
                if isinstance(node.ctx, ast.Load):
                    return "WIRED"
    return status

def check_function_call(tree: ast.AST, function_name: str, module_qualifier: str = None) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if module_qualifier:
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == module_qualifier and node.func.attr == function_name:
                        return "WIRED"
            else:
                if isinstance(node.func, ast.Name) and node.func.id == function_name:
                    return "WIRED"
    return "NOT-WIRED"

def validate_manifest(manifest_path: str) -> dict:
    import os
    if not os.path.exists(manifest_path):
        print(f"ERROR: Manifest missing at {manifest_path}")
        sys.exit(1)
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    if not data or not isinstance(data, dict) or 'artifacts' not in data or not data['artifacts']:
        print(f"ERROR: Manifest {manifest_path} is empty or missing 'artifacts' key.")
        sys.exit(1)
        
    artifacts = data['artifacts']
    for artifact_name, artifact_data in artifacts.items():
        if not isinstance(artifact_data, dict):
            print(f"ERROR: Artifact '{artifact_name}' is malformed.")
            sys.exit(1)
            
        pattern_type = artifact_data.get('pattern_type')
        if pattern_type not in ('keyword_arg', 'attribute_access', 'function_call', 'dict_key_access'):
            print(f"ERROR: Artifact '{artifact_name}' has invalid pattern_type '{pattern_type}'.")
            sys.exit(1)
            
        consumers = artifact_data.get('consumers')
        if consumers is None or not isinstance(consumers, list) or len(consumers) == 0:
            print(f"ERROR: Artifact '{artifact_name}' has zero consumers.")
            sys.exit(1)
            
        for i, consumer in enumerate(consumers):
            if 'file' not in consumer:
                print(f"ERROR: Artifact '{artifact_name}', consumer index {i} is missing 'file'.")
                sys.exit(1)
            if pattern_type in ('keyword_arg', 'attribute_access', 'dict_key_access'):
                if 'fields' not in consumer:
                    print(f"ERROR: Artifact '{artifact_name}', consumer '{consumer['file']}' is missing 'fields' for {pattern_type} pattern.")
                    sys.exit(1)
                    
        if pattern_type == 'keyword_arg' and 'function_name' not in artifact_data:
            print(f"ERROR: Artifact '{artifact_name}' is missing 'function_name' for keyword_arg pattern.")
            sys.exit(1)
        if pattern_type == 'attribute_access' and 'variable_name' not in artifact_data:
            print(f"ERROR: Artifact '{artifact_name}' is missing 'variable_name' for attribute_access pattern.")
            sys.exit(1)
        if pattern_type == 'function_call' and 'function_name' not in artifact_data:
            print(f"ERROR: Artifact '{artifact_name}' is missing 'function_name' for function_call pattern.")
            sys.exit(1)
        if pattern_type == 'dict_key_access' and 'variable_name' not in artifact_data:
            print(f"ERROR: Artifact '{artifact_name}' is missing 'variable_name' for dict_key_access pattern.")
            sys.exit(1)
            
    return data

def run_audit(manifest_path: str):
    data = validate_manifest(manifest_path)
    
    for artifact_name, artifact_data in data['artifacts'].items():
        pattern_type = artifact_data['pattern_type']
        
        for consumer in artifact_data['consumers']:
            file_path = consumer['file']
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=file_path)
            except Exception as e:
                print(f"Could not parse {file_path}: {e}")
                continue
                
            if pattern_type == 'keyword_arg':
                for field in consumer['fields']:
                    result = check_keyword_arg(tree, artifact_data['function_name'], field)
                    print(f"[{artifact_name}] {file_path} | {field}: {result}")
                    
            elif pattern_type == 'attribute_access':
                for field in consumer['fields']:
                    result = check_attribute_access(tree, artifact_data['variable_name'], field)
                    print(f"[{artifact_name}] {file_path} | {field}: {result}")
                    
            elif pattern_type == 'function_call':
                result = check_function_call(tree, artifact_data['function_name'], artifact_data.get('module_qualifier'))
                print(f"[{artifact_name}] {file_path} | <function_call>: {result}")
                
            elif pattern_type == 'dict_key_access':
                for field in consumer['fields']:
                    result = check_dict_key_access(tree, artifact_data['variable_name'], field)
                    print(f"[{artifact_name}] {file_path} | {field}: {result}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wiring_audit_core.py <manifest.yaml>")
        sys.exit(1)
    run_audit(sys.argv[1])
