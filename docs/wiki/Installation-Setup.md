# Installation & Setup

Get the framework running in under 10 minutes.

## Prerequisites

- Python 3.10+
- Git
- An existing GitHub project (local or remote)
- LLM provider API key (Anthropic, OpenAI, or local Ollama)

## Step 1: Clone the Framework

```bash
git clone https://github.com/Peadarpol/ai-delivery-control
cd ai-delivery-control
```

## Step 2: Install into Your Project

```bash
python bootstrap/install.py --project-path /path/to/your/project
```

The installer:
- Detects your tech stack (language, package manager, test framework)
- Copies framework files into `.agent/`
- Wires pre-commit hooks
- Generates `.agent/config.yaml`
- Runs environment validation

## Step 3: Validate the Installation

```bash
python bootstrap/validate.py --project-path /path/to/your/project
```

If all checks pass, you're ready to start.

## Step 4: Configure Your Project

Edit `.agent/config.yaml`:

1. **Review `tech_stack` settings** — installer auto-detected these, verify they're correct
2. **Set `model_routing`** — choose your LLM provider and model
3. **Add `domain_constraints`** — list inviolable business/technical rules
4. **Define `architecture.layers`** — map your codebase layers and forbidden imports
5. **Configure `capabilities`** — map shell commands if using non-standard tools

## Step 5: Add Custom Review Rules

Edit `src/scripts/review_context_project.md` and add project-specific review rules:

```markdown
## [RULE:TENANT-ISOLATION] All queries scoped to tenant
<!-- SECTION:tenant_isolation -->
Every database query on a multi-tenant table must include a `tenant_id` filter.
- **FAIL if:** query missing explicit tenant scope
- **WARN if:** scope is conditional rather than always applied
```

See [Customization](Customization) for full format.

## Step 6: Start Your First Session

```bash
cd /path/to/your/project
python .agent/scripts/check_halt.py
python .agent/scripts/init_session.py
```

Then read the session setup files:
```bash
cat .agent/state/active_context.md
cat .agent/state/decisions_log.md
```

---

## Verify the Gate Works

Make a test commit:
```bash
echo "# test" > test_file.py
git add test_file.py
git commit -m "test: verify gate"
```

The pre-commit hook should trigger. You'll see gate output showing a `PASS`, `WARN`, or `FAIL` verdict.

---

## Next Steps

- Read [Governance Rules](Governance-Rules) to understand prohibitions and escalation triggers
- Explore [Workflows & Tasks](Workflows-&-Tasks) to understand how to structure work
- Browse [Skills](Skills) to see available tools and guidance
- Check [Troubleshooting](Troubleshooting) if anything breaks

---

## Troubleshooting Install

**Pre-commit hook not running?**
```bash
pre-commit install
```

**Config validation failed?**
```bash
python bootstrap/validate.py --project-path . --verbose
```

**Need to downgrade?**
```bash
python bootstrap/downgrade.py --project-path /path/to/project --target-version 1.0.0
```

---

*For production deployment, see the framework README and [Security](Security) considerations.*