# Architecture Decisions

Why the AI Delivery Control framework is designed the way it is.

---

## Core Philosophy

**Hard enforcement at the commit boundary. Convention everywhere else.**

### Why This Design?

**The Problem:**
General-purpose frameworks with 50+ rules, all equally enforced, are unusable. Agents will either ignore half the rules or burn out trying to follow all of them.

**The Solution:**
Enforce only the most critical rules (security, data integrity, architecture) at a hard boundary. Treat everything else as convention reinforced by clear structure.

**Analogy:** Seatbelts are mandatory (hard enforcement at vehicle entry). Driving speed is conventional (signage + enforcement at borders). You can't enforce every good practice; you enforce the boundaries.

---

## Design Decision 1: Pre-Commit Gate vs. Post-Commit

### Decision
Enforce at **pre-commit** (blocks the commit) rather than post-commit (catches it later).

### Why

**Pre-commit advantage:**
- ✅ Prevents bad code from ever entering the repository
- ✅ Immediate feedback (2-5 sec latency)
- ✅ No cleanup/revert cycles
- ✅ Code review happens *before* PR creation (not after)

**Post-commit disadvantage:**
- ❌ Bad code lands in history
- ❌ CI runner discovers issue later (10-30 min)
- ❌ Requires revert or fix commit
- ❌ Pollutes git log

### Trade-off
- **Cost**: ~5 seconds per commit (API latency)
- **Benefit**: Zero bad code in repository
- **Worthwhile**: Yes. The latency overhead encourages thoughtful commits.

---

## Design Decision 2: Two-Tier Review (Universal + Project)

### Decision
Review rules in two layers:
- **Universal** (shipped with framework) — Common failure modes
- **Project** (you define) — Domain-specific constraints

### Why

**Single-tier (bad):**
```
Review context = hardcoded into gate
→ Can't customize without modifying framework
→ Customizations lost on upgrade
→ No way to add domain-specific rules
```

**Two-tier (good):**
```
Universal layer (framework-owned) → preserved on upgrade
     ↓
Project layer (you-owned) → never touched on upgrade
     ↓
= Flexible, upgradeable, customizable
```

### Benefit
You can add "tenant isolation required" rules without waiting for a framework release.

---

## Design Decision 3: Evaluator-Optimizer Pattern

### Decision
Use **two separate LLM models**:
- **Generator** — writes code (agent)
- **Evaluator** — reviews code (gate)

### Why

**Why not use one model?**
- The model that wrote the code is invested in defending it
- It can rationalize around its own mistakes
- Same blind spots everywhere

**Evaluator-Optimizer pattern:**
- Model A writes code (possible blind spots: A, B, C)
- Model B evaluates (possible blind spots: C, D, E)
- Set A ∩ B = minimal overlap
- Set A ∪ B = better coverage

### Research Basis
Anthropically demonstrated this pattern increases accuracy on adversarial benchmarks.

### Cost
- One extra API call per commit
- ~5 seconds latency
- Worth it.

---

## Design Decision 4: Session State in Git, Not a Server

### Decision
Store all session state (decisions, context, log) in `.agent/state/` as `.md` and `.jsonl` files, committed to git.

### Why

**Why not a server/database?**
```
Server approach:
  - Requires infrastructure
  - Requires authentication
  - Requires backup/recovery
  - Network dependency
  - ❌ Complexity
```

**Git-based approach:**
```
State in git:
  - ✅ Zero infrastructure
  - ✅ Automatic backup (git clone)
  - ✅ Full audit trail (git log)
  - ✅ Works offline
  - ✅ Team visibility
```

### Tradeoff
- `.jsonl` files are append-only (full history)
- Not suitable for >100MB datasets
- Solution: Memory manager archives old data

---

## Design Decision 5: 15 Prohibitions, Not 50+

### Decision
**P-01 through P-15** — Absolute prohibitions enforced by convention.

### Why Not More?

**Too many rules:**
- Agents can't remember them
- Contradictions emerge (rule X conflicts with rule Y)
- Human reviewers get fatigued
- Framework becomes unusable

**Better approach:**
- Make 15 rules non-negotiable
- Encode them in the framework structure
- Let everything else emerge from clear patterns

### The 15 Chosen
- P-01 to P-07: Core governance (no merging to main, no deleting migrations, etc.)
- P-08 to P-10: Architecture (clean code boundaries)
- P-11 to P-13: Git discipline (verification, staging, no artifacts)
- P-14 to P-15: Safety (right repo, CI/CD branch strategy)

**Result:** Clear, memorable, enforceable.

---

## Design Decision 6: Convention Over Configuration

### Decision
Standardize on **convention** over endless configuration.

### Examples

**Convention**: Session state files are `.md` and `.jsonl`
→ No config needed, just pick them up

**Convention**: Workflows named `/feature-implementation`, `/bug-fix`, etc.
→ No config, just use the name

**Convention**: Skills live in `.agent/skills/{skill-name}/`
→ No registry to maintain

### Why

**Configuration explosion is bad:**
```yaml
# Bad: Too much to configure
review:
  model: claude-sonnet
  timeout: 30
  max_retries: 3
  backoff_factor: 1.5
  ...50 more fields
```

**Convention is better:**
```yaml
# Good: Minimal config, rest is convention
review_provider: anthropic
review_model: claude-sonnet
# Everything else follows predictable patterns
```

---

## Design Decision 7: Skill Directory > Inheritance

### Decision
Skills are **directory-based**, not class-based.

```
.agent/skills/
├── universal/
│   ├── test-driven-development/
│   │   ├── SKILL.md
│   │   └── validate.py
│   └── debugging/
│       ├── SKILL.md
│       └── validate.py
└── your-custom-skill/
    ├── SKILL.md
    └── validate.py
```

### Why

**Why not class inheritance?**
- Requires Python environment on all machines
- Complex dependency management
- Hard to version independently
- Upgrades break custom subclasses

**Directory-based approach:**
- ✅ Language-agnostic
- ✅ Versionable by git
- ✅ Custom skills never conflict
- ✅ Drop-in replacement

---

## Design Decision 8: Executable Validation Gates

### Decision
Each skill has an optional `validate.py` script that must exit 0 before task completion.

### Why

**Markdown-only skills (bad):**
```markdown
# Skill: Testing

## Rules
1. Write tests
2. Run tests
3. Coverage >90%
```
→ Vague, unenforceable, easy to skip

**Executable gates (good):**
```python
def validate():
    coverage = run_pytest_coverage()
    if coverage < 90:
        print("FAIL: coverage < 90%")
        return False
    return True
```
→ Clear, testable, enforced automatically

### Trade-off
- Adds complexity (agents must write scripts)
- Huge gain in reliability
- Worth it.

---

## Design Decision 9: Dream Phase Self-Improvement

### Decision
Framework learns from failure patterns and proposes rule updates.

### Why

**Generic rules are always wrong for someone:**
- Security team: "Rules too loose"
- Velocity team: "Rules too strict"
- No single sweet spot

**Solution: Self-improvement:**
- Track rebuttal acceptance rates
- When rule has 50%+ rebuttal rate → "too strict"
- When rule has <30% rebuttal rate → "too loose"
- Propose updates
- Human approves

### Over Time
After 6 months, the framework is calibrated to *your* codebase, not generic best practice.

---

## Design Decision 10: Outer Loop (Spec-Driven)

### Decision
No code is written without an approved spec.

### Why

**Without specs:**
- Agents implement what they *think* you meant
- Scope creep
- Rework when requirements change
- No traceability

**With specs:**
- Requirements are explicit (Gherkin BDD)
- Agent reads and signs off on understanding
- Acceptance gate verifies implementation matches spec
- Full traceability: requirement → test → code

### Trade-off
- Slower initial cycle (write spec first)
- Way fewer reworks (spec prevents misunderstanding)
- Net faster overall

---

## Design Decision 11: Why Sessions, Not Just Commits?

### Decision
Group commits into **sessions** with shared context.

### Why

**Without sessions:**
```
Commit 1: Implement service
Commit 2: Implement repo
Commit 3: Implement endpoint
→ Agent loses context between commits
→ Each commit is independent
→ No narrative
```

**With sessions:**
```
Session 1 (3 commits):
  - Decisions made: use async, apply caching
  - Context: multi-tenant bookings
  - Next steps: write tests
  - Decisions log: full record
  
Session 2 (resume):
  - Read context from session 1
  - Continue from where we left off
  - Maintain narrative
```

### Benefit
Agent doesn't re-decide the same architectural choices.

---

## Design Decision 12: Workflows, Not Freestyle

### Decision
Every task follows a named workflow (18 total).

### Why

**Freestyle (bad):**
```
"Implement a feature"
→ Agent goes off in random directions
→ No standard phases
→ Can miss steps
```

**Workflows (good):**
```
/feature-implementation workflow
  Phase 0: Verify spec
  Phase 1: Requirements analysis
  Phase 2: Architecture design
  Phase 3: Multi-persona audit
  Phase 4: Implementation
  Phase 5: Acceptance

→ Standard, repeatable, nothing forgotten
```

### Precedent
Software engineering best practices (Scrum, XP, RUP) all standardize on workflows.

---

## Design Decision 13: Why These 18 Workflows?

### Decision
18 workflows covering all major software delivery task types.

### Why Not Fewer?

**3-5 workflows:**
- Too generic
- Force-fit specialized tasks
- Miss nuances (e.g., performance vs. bug-fix)

**18 workflows:**
- `/feature-implementation` — specific for features
- `/bug-fix` — specific for bugs
- `/security` — specific for security
- `/perf` — specific for performance
- etc.

**Why Not More?**
- >20 workflows is unmaintainable
- 18 covers 95% of real tasks
- Rare tasks can compose workflows

---

## Summary Table

| Decision | Choice | Alternative | Why |
|----------|--------|-------------|-----|
| Enforcement | Pre-commit | Post-commit | Prevents bad code from landing |
| Review layers | Universal + Project | Single monolithic | Customizable + upgradeable |
| LLM models | Two (generator + evaluator) | Single | Different blind spots = better coverage |
| State storage | Git files | Server/database | Zero infrastructure, full audit trail |
| Prohibitions | 15 clear rules | 50+ rules | Memorable, enforceable |
| Configuration | Convention over config | Heavy config | Simpler, less to maintain |
| Skills | Directory-based | Class inheritance | Language-agnostic, versionable |
| Validation | Executable gates | Markdown only | Clear, testable, enforced |
| Improvement | Dream phase (weekly) | Static rules | Learns from your patterns |
| Delivery | Spec-driven | Freestyle | Prevents misunderstanding |
| Context | Sessions + commits | Commits only | Maintains narrative |
| Task structure | Named workflows | Freestyle | Standard, repeatable |

---

## Principles Across All Decisions

1. **Automation where it matters** — security, data integrity, architecture
2. **Convention over configuration** — reduce cognitive load
3. **Learn from practice** — dream phase, not static rules
4. **Zero infrastructure** — runs locally, no servers
5. **Full transparency** — decisions logged, audit trail in git
6. **Team-friendly** — state is visible, no hidden server state

---

*These decisions emerged from 1000+ hours of real-world usage with AI agents. They're not arbitrary—they're optimized for the specific challenge of keeping AI agents accountable while preserving their speed advantage.*

---

## Design Decision 14: AI-Provenance Git Trailers

**Status**: Accepted  
**Context**: The GitLab AI Accountability Report (June 2026, n=1,528) identified that
34% of organisations that experienced a production incident involving AI-generated code
could not trace which commits were AI-assisted, despite 87% expressing confidence that
they could. The harness already tracks session traceability in `session_ledger.jsonl`,
but this data is not present at the git-object level where incident responders first look.

**Decision**: All commits made under harness governance must include three standardised
git trailer lines: `AI-Assisted: true`, `Harness-Version: <version>`, and
`Session-ID: <id>`. These trailers are machine-readable, survive `git log --format`,
and answer the accountability question at the commit level without requiring access to
harness state files.

**Consequences**: Commit messages become slightly longer. The trailer values must be
populated at commit time from live files (`harness_version.txt`, `session.json`) — they
cannot be hardcoded. This is enforced by the §9.1 staging instruction in `AGENTS.md`.
No changes to existing tooling are required; git trailers are parsed by standard
`git log --format='%(trailers)'`.