# Customisation Guide

Four surfaces let you tailor the harness to your project without modifying framework files.
All four are preserved when you re-run the installer.

| Surface | File | What it controls |
|---|---|---|
| **Review invariants** | `src/scripts/review_context_project.md` | What the AI gate checks in your codebase |
| **Custom skills** | `.agent/skills/your-skill/SKILL.md` | New named behaviours for your domain |
| **Architecture rules** | `.agent/config.yaml` → `architecture:` | Layer boundaries and forbidden patterns |
| **Model tiers** | `.agent/config.yaml` → `model_tiers:` | Keywords mapping model names to cost tiers |

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
| Section tag | `<!-- SECTION:snake_case_id -->` | Used by the diff-aware routing step (T1-G-01) to select relevant sections per diff |
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

## 4. Configuring Model Cost Tiers

The harness automatically infers the model being used via the `AGENT_MODEL` environment variable (or falls back to `.agent/config.yaml`'s `model_routing`). It then maps this string to a cost tier (`frontier`, `standard`, `local`, `unknown`) for token-usage aggregation.

Because model naming conventions change rapidly (e.g., OpenAI moving from the size-suffix `gpt-4o-mini` to `GPT-5.6 Sol/Terra/Luna`), the harness relies on a keyword heuristic mapped in `.agent/config.yaml`:

```yaml
model_tiers:
  standard: ["flash", "lite", "mini", "haiku", "luna"]
  frontier: ["pro", "sonnet", "opus", "sol", "terra"]
  local: ["llama", "mistral", "qwen"]
```

> **Maintenance Note**: This configuration surface must be reviewed periodically as model providers alter their naming structures. If you adopt a new local model or a new flagship model whose name doesn't include any of the existing keywords, its token usage will be misclassified as `unknown` until you add its family keyword to the appropriate tier list.

---

## 5. Prohibition Tiers (MTF)

To keep the framework templates clean and maintainable, agent prohibitions are structured into a three-tier model:

1. **Universal Prohibitions (Tier 1)**: Apply to every project using the framework, unconditionally (cognitive, autonomy, security, and version control rules). These are maintained directly in the framework's `.agent/AGENTS.md` and cannot be modified by individual projects.
2. **Project-Specific Rules (Tier 2)**: Stack-specific or project-specific constraints (e.g. specific package managers, config rules, or environments). These belong in the project's own `.agent/AGENTS.md` under `## §4.2 — Project-Specific Rules`.
3. **Pattern-Conditional Rules (Tier 3)**: Applicable only when a specific architectural pattern is active (e.g. Clean Architecture, Repository + UoW, multi-tenancy, specific CI/CD branching topology). These belong in the project's own `.agent/AGENTS.md` under `## §4.3 — Pattern-Conditional Rules`.

### Classification Decision Table

Use this quick decision table to categorize a new project rule:

| Ask yourself | Answer | Tier |
|---|---|---|
| Would this rule apply to a React project, a Rust CLI, a data pipeline, and a mobile app equally? | Yes | Universal (§4.1) — already in template |
| Does this rule only make sense given our specific stack or tooling choice? | Yes | Project-Specific (§4.2) — add to your AGENTS.md |
| Does this rule only apply if a specific architectural pattern is active? | Yes | Pattern-Conditional (§4.3) — add to your AGENTS.md with precondition |

---

### Copy-Pasteable Templates for Adopters

You can copy and paste the following templates into your project's `.agent/AGENTS.md` file to configure customized constraints.

#### Template for §4.2 — Project-Specific Rules

```markdown
### 4.2 — Project-Specific Rules

> These rules apply because this project uses [stack/toolchain/pattern].
> They are not universal. Do not carry them to other projects.

| ID | Never do this | Precondition |
|---|---|---|
| PS-01 | [rule description, e.g. Never use npm install — always use pnpm add] | [precondition, e.g. Project uses pnpm] |
| PS-02 | [rule description, e.g. Never modify .env files without documenting the change] | [precondition, e.g. Project uses .env files] |
```

> [!NOTE]
> The `Precondition` column is mandatory. It ensures that subsequent agents understand why the constraint exists and do not treat it as a universal framework rule.

> [!IMPORTANT]
> **Intentionally demoted from the old universal flat list.** Three rules from the
> pre-tiered `P-01…P-15` list (P-04 *skip writing tests*, P-05 *install dependencies
> without approval*, P-07 *use `pip install` instead of `poetry add`*) were **deliberately
> moved here to Tier 2** — they are not universal. Each depends on a project choice: P-04 on
> whether the project mandates TDD, P-05 on whether the project pins a dependency manifest,
> and P-07 on which package manager the project standardises on. A React app, a Rust CLI, and
> a data pipeline would each phrase or omit them differently, so they fail the universality
> test in the Classification Decision Table above. If your project makes those choices, copy
> the matching rows below into your `AGENTS.md` §4.2:
>
> ```markdown
> | PS-T1 | Skip writing tests for new functionality | Project mandates TDD (red-green-refactor) |
> | PS-T2 | Install a new dependency without listing it for explicit approval | Project pins a dependency manifest (e.g. pyproject.toml, package.json) |
> | PS-T3 | Use `pip install` (or `npm install`) directly instead of the project package manager | Project standardises on poetry / pnpm / uv |
> ```

#### Template for §4.3 — Pattern-Conditional Rules

```markdown
### 4.3 — Pattern-Conditional Rules

> These rules apply ONLY because this project uses the patterns listed below.
> Do not apply these rules to projects that do not use these patterns.

### Clean Architecture / Hexagonal Architecture
Active in this project: YES / NO

If YES:
| ID | Never do this |
|---|---|
| PC-CA-01 | Never import infrastructure layer from domain or business layers. |
| PC-CA-02 | Never import presentation layer from application or domain layers. |

### Repository + Unit of Work Pattern
Active in this project: YES / NO

If YES:
| ID | Never do this |
|---|---|
| PC-UOW-01 | Never access database sessions directly, bypassing the Repository/UoW pattern. |
| PC-UOW-02 | Never call commit() outside the Unit of Work boundary. |

### Incremental Database Migrations
Active in this project: YES / NO

If YES:
| ID | Never do this |
|---|---|
| PC-MIG-01 | Never delete or modify existing migration files once committed. |
| PC-MIG-02 | Never make direct schema changes outside the migration toolchain. |

### Multi-Tenant Data Isolation
Active in this project: YES / NO

If YES:
| ID | Never do this |
|---|---|
| PC-MT-01 | Never modify tenant/branch isolation logic without explicit human instruction and a security review. |
| PC-MT-02 | Never write a query that could return rows across tenant boundaries. |

### Protected CI/CD Staging Topology
Active in this project: YES / NO

If YES:
| ID | Never do this |
|---|---|
| PC-CD-01 | Never commit directly to the deployment branch for CI/CD fixes — use a short-lived fix branch, merge to deployment branch, then merge back to the active feature branch. |
```

---

## What not to customise

The following files are framework-owned and overwritten on installer re-runs:

| File | Why |
|---|---|
| `src/scripts/review_context_universal.md` | Framework-maintained universal review invariants |
| `.agent/AGENTS.md` | Cross-tool mandatory session protocol |
| `.agent/governance.md` | Prohibition rationale, legacy-ID map, and escalation rules (canonical rule list is `.agent/AGENTS.md` §4) |
| `.agent/scripts/*` | Session management and gate scripts |
| `.agent/workflows/*` | Delivery workflow definitions |
| `.agent/UNIVERSAL_CONTEXT.md` | Machine-generated; refreshed on every install |

Put your additions in the customisation surfaces above. They are always preserved.
