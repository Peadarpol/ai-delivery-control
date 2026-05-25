# Harness Skills & The Executable Validation Gate Contract

Harness **Skills** represent portable, focused, and automated policy guidelines that instruct developers and AI agents on stack-specific conventions and invariants. 

Rather than relying purely on passive documentation (which agents easily ignore or misinterpret under high context load), the framework utilizes **Executable Validation Gates**. Every skill with programmatic check coverage features a companion `validate.py` script. The adversarial gate calls these scripts automatically before any commit is finalized.

---

## The `validate.py` Gate Contract Pattern

An executable validation script follows a simple, high-reliability contract:
- **Zero-Dependency AST/Regex Walks**: Performed via Python’s standard library to keep execution latency under **50ms**.
- **Self-Disclosed Policy Rules**: Aligned with the corresponding `SKILL.md` rules.
- **Exit Code Enforcement**: 
  - `exit(0)`: Policy verified successfully. Commit proceeds.
  - `exit(1)`: Policy violation detected. Prints the specific violation and blocks the commit.

---

## Before vs. After: Implementing Executable Gates

Below is a detailed comparison of a skill's evolutionary path, illustrating why executable validation gates are the cornerstone of compliance in agentic workflows.

````carousel
### Before: Pure Markdown Guidelines

**File**: `.agent/skills/mass-assignment/SKILL.md`
```markdown
# Mass Assignment Protection
In this project, we must protect API schemas against mass assignment vulnerabilities.

## Invariant Rules
1. Every Pydantic schema used for API inputs MUST explicitly forbid extra fields.
2. In Pydantic v2, this is configured via:
   class ConfigDict:
       extra = "forbid"
```

> [!WARNING]
> **The Failure Mode**: During high-intensity development, an agent forgets to include the `extra = "forbid"` configuration when generating new schemas. Since there is no automated enforcement, the vulnerable schema is committed, introducing a permanent security risk to the repository history.

<!-- slide -->
### After: The Executable Gate Contract

**File**: `.agent/skills/mass-assignment/validate.py`
```python
import ast
import sys
from pathlib import Path

def validate_schemas(filepath: Path) -> list[str]:
    violations = []
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except Exception:
        return []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Inspect Pydantic schema subclasses
            is_schema = any(base.id == "BaseModel" for base in node.bases if isinstance(base, ast.Name))
            if is_schema:
                has_extra_forbid = False
                for body_item in node.body:
                    if isinstance(body_item, ast.Assign):
                        # Pydantic v1: class Config: extra = Extra.forbid
                        pass
                    elif isinstance(body_item, ast.AnnAssign) and body_item.target.id == "model_config":
                        # Pydantic v2: model_config = ConfigDict(extra="forbid")
                        if isinstance(body_item.value, ast.Call) and body_item.value.func.id == "ConfigDict":
                            for kw in body_item.value.keywords:
                                if kw.arg == "extra" and getattr(kw.value, "value", None) == "forbid":
                                    has_extra_forbid = True
                
                if not has_extra_forbid:
                    violations.append(f"{node.name} at line {node.lineno} is missing forbidden extra config")
    return violations

def main():
    has_errors = False
    for path in Path("src/domain/schemas").glob("**/*.py"):
        errors = validate_schemas(path)
        for err in errors:
            print(f"❌ [MASS_ASSIGNMENT] {path.name}: {err}")
            has_errors = True
    if has_errors:
        sys.exit(1)
    print("✅ [MASS_ASSIGNMENT] All schemas harden successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

> [!TIP]
> **The Corrected Behavior**: The agent attempts to commit a new schema lacking the forbidden extra configuration. The pre-commit hook automatically runs `validate.py`, which statically inspects the AST, intercepts the missing configuration, prints a detailed violation trace, and exits with code 1—saving the team from a compliance leak!
````

---

## Recommended Skill Authoring Workflow

When authoring custom project skills under `.agent/skills/`:
1. Keep the `SKILL.md` rules brief, high-impact, and focused (rule count **≤ 5**).
2. Scaffold a static `validate.py` script to enforce these rules. Banish generic regexes in favor of standard library `ast` parsing for 100% accurate, syntax-aware checks.
3. Place a companion test case in `cases.csv` to protect the check from regression.
