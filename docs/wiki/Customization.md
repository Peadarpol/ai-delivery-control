# Customization

How to tailor the framework to your project without modifying framework files.

## Three Customization Surfaces

All three are preserved when you upgrade the framework.

| Surface | File | What |
|---------|------|------|
| **Review rules** | `src/scripts/review_context_project.md` | What the gate checks |
| **Custom skills** | `.agent/skills/your-skill/` | New task behaviors |
| **Architecture** | `.agent/config.yaml` → `architecture:` | Layer boundaries, forbidden patterns |

---

## 1. Project-Specific Review Rules

### File
`src/scripts/review_context_project.md`

### Format

```markdown
## [RULE:YOUR-RULE-ID] Short title
<!-- SECTION:section_name -->

Plain English description of what to check.

- **FAIL if:** code violates security, data integrity, or architectural rule
- **WARN if:** style issue or incomplete coverage
```

### Example

```markdown
## [RULE:TENANT-ISOLATION] All queries must be scoped to a tenant
<!-- SECTION:tenant_isolation -->

Every database query on a multi-tenant table must include an explicit
`tenant_id` or `branch_id` filter.

**FAIL if:**
- Query lacks tenant filter
- Filter is conditional

**WARN if:**
- Filter applied but not documented
```

Changes take effect immediately on the next commit.

---

## 2. Custom Skills

### Directory Structure

```
.agent/skills/
├── universal-skill/
│   ├── SKILL.md
│   └── validate.py
└── your-custom-skill/
    ├── SKILL.md (required)
    └── validate.py (optional)
```

### Minimal SKILL.md

```markdown
---
name: your-custom-skill
version: 1.0.0
skill_type: custom
---

# Your Custom Skill

## When to use this skill
Clear description of when to apply this skill.

## Approach
1. First step
2. Second step
3. Verify

## Success criteria
Task is complete when...
```

### Optional validate.py

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

def main():
    # Your validation logic here
    # Return 0 for success, 1 for failure
    print("✅ Task complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Your skills are never overwritten on framework upgrade.

---

## 3. Architecture Checks

### Layer Boundaries

```yaml
architecture:
  layers:
    - name: domain
      path: "src/domain"
      forbidden_imports:
        - "src.infrastructure"
        - "src.presentation"
    
    - name: infrastructure
      path: "src/infrastructure"
      forbidden_imports:
        - "src.presentation"
```

### Forbidden Patterns

```yaml
architecture:
  forbidden_patterns:
    - "os\\.system\\("
    - "eval\\("
    - "print\\("
```

---

## What NOT to Customize

Do not edit these—they're overwritten on upgrade:

- `src/scripts/review_context_universal.md`
- `.agent/AGENTS.md`
- `.agent/governance.md`
- `.agent/scripts/*`
- `.agent/workflows/*`

---

*See [Glossary](Glossary.md) for definitions.*
