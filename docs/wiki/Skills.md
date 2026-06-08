# Skills

Skills are focused, executable policy documents that govern how agents approach specific task types.

---

## What a skill is

Each skill is a directory under `.agent/skills/` containing:

- **`SKILL.md`** — the policy document: when to use this skill, the rules to follow, and the expected output format
- **`validate.py`** (where applicable) — a deterministic enforcement script that runs before task completion; uses stdlib `ast` parsing, exits 0 on pass and 1 on violation, latency under 50ms
- **`cases.csv`** (where applicable) — regression test cases that prevent `validate.py` from drifting

The `SKILL.md` is the instruction layer — it tells the agent what to do. The `validate.py` is the enforcement layer — it verifies the agent did it. The gate calls `validate.py` automatically as part of the pre-commit chain; `SKILL.md` is never executed mechanically, only read.

---

## The 22 universal skills

Universal skills ship with the framework and are available in every installed project.

| Skill | Description |
|-------|-------------|
| `api-design` | Designing REST and GraphQL API endpoints — structure, versioning, error contracts |
| `c4-architect` | Creating C4 model architecture diagrams in Mermaid with structured documentation |
| `code-migration` | Safely upgrading frameworks, languages, and dependencies with minimal risk |
| `code-review` | Reviewing PRs, diffs, and code changes — correctness, architecture, security, project invariants |
| `database-design` | Designing efficient, normalised schemas and data models |
| `debugging` | Systematic bug hunting and root cause analysis |
| `devops-cicd` | CI/CD pipeline design and infrastructure automation |
| `performance-optimization` | Identifying and fixing bottlenecks through systematic measurement |
| `playwright-skill` | Browser automation and UI testing with Playwright |
| `python-async` | Python asyncio, event loops, concurrency patterns, and async I/O |
| `python-automation` | Python scripting for file operations, web scraping, and task automation |
| `python-fastapi` | FastAPI backend development — async patterns, Pydantic validation, REST best practices |
| `python-testing` | pytest patterns, fixtures, parametrisation, and mocking |
| `refactoring` | Improving code quality without changing observable behaviour |
| `security-audit` | Identifying vulnerabilities following OWASP guidelines and project-specific security requirements |
| `senior-architect` | Clean Architecture and DDD system design, including dependency analysis |
| `systematic-debugging` | Structured debugging with condition-based waiting, root-cause tracing, and test pressure patterns |
| `test-driven-development` | TDD red-green-refactor cycle, used before writing any implementation code |
| `test-writing` | Writing comprehensive, maintainable tests with strategic coverage |
| `testing-patterns` | pytest factory functions, mocking strategies, and coverage priorities |
| `verification-before-completion` | Verifying work is actually complete before claiming done — requires running real commands and reading output |
| `kaizen` | *(deprecated)* |

---

## Stack packs

Stack packs extend the universal skills with language- and framework-specific rules for a particular technology combination:

| Stack pack | Use for |
|------------|---------|
| `python-fastapi` | Python / FastAPI / Poetry / Alembic projects |
| `node-express` | Node.js / Express projects |

The installer selects the appropriate stack pack based on detected project type. Only one stack pack is active at a time.

---

## How the gate uses skills

Skills with a `validate.py` execute automatically as part of the `architecture-checks` hook in the pre-commit chain. These checks use Python's stdlib `ast` module — no LLM call, no API cost, latency under 50ms. A violation exits 1 and blocks the commit with a specific message identifying the file, line, and rule.

Example output from the mass-assignment validate.py:
```
❌ [MASS_ASSIGNMENT] schemas/user.py: UserCreateSchema at line 14 is missing forbidden extra config
```

---

## Adding custom skills

Custom skills go under `.agent/skills/` in your project. They are never overwritten on upgrade.

Minimal structure:
```
.agent/skills/my-skill/
  SKILL.md        # Required
  validate.py     # Recommended
  cases.csv       # Optional
```

**`SKILL.md` conventions:**
- Rule count ≤ 5 — more dilutes agent attention
- Target < 100 lines; hard limit 200 lines
- Include an explicit statement of when this skill does NOT apply
- Include the expected output format

**`validate.py` contract:**
- Use `ast` or `re` from stdlib — no external dependencies
- Print a specific violation message before calling `sys.exit(1)`
- Print a clean confirmation message and call `sys.exit(0)` on success
- Complete in under 50ms

---

*See [Customization](Customization.md) for adding project-specific rules to the AI review gate.*
