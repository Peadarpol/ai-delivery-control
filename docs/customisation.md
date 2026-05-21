# Customisation Guide

Three surfaces let you tailor the harness to your project without modifying framework files.
All three are preserved when you re-run the installer.

| Surface | File | What it controls |
|---|---|---|
| **Review invariants** | `src/scripts/review_context_project.md` | What the AI gate checks in your codebase |
| **Custom skills** | `.agent/skills/your-skill/SKILL.md` | New named behaviours for your domain |
| **Architecture rules** | `.agent/config.yaml` → `architecture:` | Layer boundaries and forbidden patterns |

---

## 1. Adding project-specific review invariants

The AI review gate reads two context layers on every commit:

| Layer | File | Owner |
|---|---|---|
| Universal | `src/scripts/review_context_universal.md` | Framework — do not edit |
| Project | `src/scripts/review_context_project.md` | You — edit freely |

The project layer is concatenated after the universal layer and injected into every AI
review call. Open it and add rules using the established format:

```markdown
## [RULE:TENANT-ISOLATION] All queries must be scoped to a tenant
<!-- SECTION:tenant_isolation -->
Every database query on a multi-tenant table must include a `branch_id` or `tenant_id`
filter. A query missing this filter is a data-leak bug, not a style issue. Fail the
review if any new query on a multi-tenant table lacks an explicit isolation filter.
```

**Format conventions:**

| Element | Format | Purpose |
|---|---|---|
| Rule ID | `## [RULE:YOUR-ID] Title` | Unique identifier — uppercase, hyphenated |
| Section tag | `<!-- SECTION:snake_case_id -->` | Used for future selective injection (T1-G-01) |
| Body | Plain English, written as reviewer instructions | Describe what to check and at what severity |

**Severity guidance** — state explicitly what warrants each verdict:

- `FAIL` — the diff cannot ship as-is (security, data integrity, architecture violation)
- `WARN` — should be addressed but does not block shipping (style, incomplete coverage)

**Micro-check table** — optional, useful for pattern-based checks:

```markdown
## [SENSOR:DIFF-AUDIT] Project Micro-Checks
<!-- SECTION:micro_checks -->

| If the diff adds or changes...      | Then check...                             | Severity |
|-------------------------------------|-------------------------------------------|----------|
| a new SQLAlchemy model              | `branch_id` isolation filter is present   | HIGH     |
| an authentication route             | rate limiting middleware is applied        | HIGH     |
| a new Pydantic schema               | `model_config = {"extra": "forbid"}`      | MEDIUM   |
| a new background task               | failure handling and retry logic present  | MEDIUM   |
```

Changes to this file take effect on the next commit — no reload or restart required.

---

## 2. Creating custom skills

Skills are named, scoped behaviour documents that agents select when a task matches the
skill's domain. The installer populates `.agent/skills/` with 22 universal skills; add
your own alongside them.

### Skill directory structure

```
.agent/skills/
└── your-skill-name/
    ├── SKILL.md          # Required — skill definition and rules
    └── validate.py       # Optional — post-task validation script
```

Choose a directory name that is lowercase and hyphenated (`data-migration`, `tenant-setup`,
`api-versioning`). Agents identify skills by their directory name.

### Minimal SKILL.md

```markdown
---
name: data-migration
version: 1.0.0
skill_type: custom
---

# Data Migration Skill

## When to use this skill
Use when migrating data between schemas, normalising legacy records, or backfilling
a new column across a large table.

## Approach

1. Write the migration as an idempotent script — safe to re-run.
2. Test against a restored copy of production data before running on the live database.
3. Run inside a transaction; roll back on any error.
4. Verify row counts before and after.
5. Log: rows affected, duration, any warnings.

## Absolute prohibitions
- Never run without a database backup confirmed within the last 24 hours.
- Never modify tenant-scoped data without an explicit per-tenant scope filter.
- Never run directly against production without staging validation first.

## Output format
Report: rows inspected, rows migrated, rows skipped, total duration, errors (if any).
```

**Frontmatter fields:**

| Field | Values | Description |
|---|---|---|
| `name` | string | Must match the directory name |
| `version` | `major.minor.patch` | Increment when the skill changes materially |
| `skill_type` | `universal` / `stack-pack` / `custom` | Mark yours as `custom` |

### Optional validate.py

Add a `validate.py` when the skill has a clear, testable completion criterion. Agents run
it before declaring the task complete — a non-zero exit blocks completion.

```python
#!/usr/bin/env python3
"""Validate: data migration completed without errors."""
import sys
from pathlib import Path

log = Path("migration_log.txt")
if not log.exists():
    print("FAIL: migration_log.txt not found — migration may not have run")
    sys.exit(1)
content = log.read_text()
if "ERROR" in content:
    print("FAIL: migration log contains errors — review before proceeding")
    sys.exit(1)
if "rows_migrated: 0" in content:
    print("WARN: migration log reports zero rows migrated — verify this is expected")
print("PASS: migration log present and clean")
sys.exit(0)
```

Skills you create are never touched by the installer on re-run.

---

## 3. Configuring architecture checks

`.agent/config.yaml` — `architecture:` section — drives the automated layer boundary
checks that run on every pre-commit. No code changes required; edit the YAML and the
checks update immediately.

### Defining layer boundaries

```yaml
architecture:
  layers:
    - name: domain
      path: "src/domain"
      forbidden_imports:
        - "src.infrastructure"   # domain must never know about infrastructure
        - "src.presentation"
    - name: application
      path: "src/application"
      forbidden_imports:
        - "src.infrastructure"
        - "src.presentation"
    - name: infrastructure
      path: "src/infrastructure"
      forbidden_imports:
        - "src.presentation"
```

The check walks every `.py` file under `path` and flags any `import` or `from ... import`
that matches a `forbidden_imports` prefix. Violations block the commit and print the
file, line number, and offending import.

**To add a new layer** — append an entry to the list:

```yaml
    - name: shared-kernel
      path: "src/shared"
      forbidden_imports: []   # shared kernel may import from anywhere
```

### Forbidden patterns

Ban specific code constructs project-wide using Python regexes:

```yaml
architecture:
  forbidden_patterns:
    - "os\\.system\\("        # no shell injection via os.system
    - "eval\\("               # no eval anywhere
    - "# noqa:\\s*S"          # no silencing bandit security rules
    - "print\\("              # no print statements in production code
```

Each pattern is matched against file content. Violations are reported with file, line,
and matched text. Matches block the commit.

### Coupling thresholds

```yaml
architecture:
  coupling:
    thresholds:
      default:
        threshold: 30
```

Lower the threshold to enforce tighter module cohesion. Files exceeding the threshold
generate a warning (not a block). Start with the default and tighten as the codebase
matures.

### Aggregate root detection

```yaml
architecture:
  aggregate_roots:
    - "AggregateRoot"
    - "BaseEntity"
```

Lists the base class names the architecture checker uses to identify domain aggregate
roots when verifying layering rules. Match these to the actual base classes in your
domain layer.

---

## What not to customise

The following files are framework-owned and overwritten on installer re-runs:

| File | Why |
|---|---|
| `src/scripts/review_context_universal.md` | Framework-maintained universal review invariants |
| `.agent/AGENTS.md` | Cross-tool mandatory session protocol |
| `.agent/governance.md` | Absolute prohibitions and escalation rules |
| `.agent/scripts/*` | Session management and gate scripts |
| `.agent/workflows/*` | Delivery workflow definitions |
| `.agent/UNIVERSAL_CONTEXT.md` | Machine-generated; refreshed on every install |

Put your additions in the three customisation surfaces above. They are always preserved.
