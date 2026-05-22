# Getting Started

Install the AI Delivery Control harness into any project in under 10 minutes.

---

## Prerequisites

| Requirement | Minimum | Notes |
|---|---|---|
| Python | 3.9+ | Must be on `PATH` |
| git | Any recent | Target project must be a git repository |
| pre-commit | Any recent | `pip install pre-commit` or `brew install pre-commit` |
| Anthropic API key | — | Required for the AI review gate; gate runs in fail-open mode without it |

The harness has no Python dependencies beyond the standard library.

### Stack Coverage & Manual Extension

The framework ships with out-of-the-box templates and invariant checks optimized for **Python (FastAPI)** and **Node.js (Express)**. Projects utilizing other stacks (e.g., Go, Rust, Java, or Ruby) are fully supported via the core universal skills, but require manual customization of architecture boundaries in `.agent/config.yaml` and stack-specific guidelines under `.agent/skills/`.

---

## 1. Clone the harness

```bash
git clone https://github.com/Peadarpol/ai-delivery-control
```

The harness repo does not need to live inside your project. Clone it anywhere convenient.

---

## 2. Run the installer

```bash
python bootstrap/install.py --project-path /path/to/your/project
```

**Options:**

| Flag | Description |
|---|---|
| `--project-path PATH` | Target project directory (default: current directory) |
| `--language LANG` | Override language detection (`Python`, `TypeScript`, `JavaScript`) |
| `--package-manager PM` | Override package manager (`poetry`, `pip`, `npm`, `pnpm`, `yarn`) |
| `--verbose` | Print debug output during install |

**What the installer does, in order:**

1. Verifies Python 3.9+ is available
2. Detects tech stack — language, package manager, test framework, source root
3. Copies harness framework files into `.agent/`
4. Installs 22 universal skills; adds a stack-pack skill if your stack is recognised
5. Renders configuration templates — `.agent/config.yaml`, `.agent/UNIVERSAL_CONTEXT.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`
6. Scaffolds `src/scripts/review_context_project.md` — your project-specific review rules
7. Wires pre-commit hooks (`pre-commit`, `commit-msg`, `pre-push` stages)
8. Runs the environment validation suite

---

## 3. What gets created

```
project-root/
├── .agent/
│   ├── AGENTS.md                    # Mandatory session protocol for all agents
│   ├── UNIVERSAL_CONTEXT.md         # Project identity and key file locations
│   ├── governance.md                # Absolute prohibitions and escalation rules
│   ├── config.yaml                  # Commands, paths, and architecture rules
│   ├── scripts/                     # Session management scripts
│   ├── workflows/                   # 17 named delivery workflows
│   ├── skills/                      # 22 universal skills (+ stack pack if detected)
│   ├── evals/                       # Skill evaluation cases and regression runner
│   ├── state/                       # Session state files (gitignored)
│   └── config/
│       └── skill_ownership.yaml     # Dream phase routing map
├── src/scripts/
│   ├── ai_review.py                 # Pre-commit AI review gate
│   ├── review_context_universal.md  # Framework-owned review invariants (do not edit)
│   └── review_context_project.md   # Your project-specific review rules (edit this)
├── .pre-commit-config.yaml
├── CLAUDE.md                        # Shim for Claude Code → UNIVERSAL_CONTEXT.md
├── GEMINI.md                        # Shim for Gemini CLI → UNIVERSAL_CONTEXT.md
└── .cursorrules                     # Shim for Cursor → UNIVERSAL_CONTEXT.md
```

Files marked *gitignored* (`state/`) contain local session data and are never committed.

---

## 4. Verify the install

```bash
python bootstrap/validate.py --project-path /path/to/your/project
```

Expected output:

```
✅ Required CLI Tools
✅ Harness Core Directory Layout
✅ Harness Core Files
✅ Repository Guard (P-14)
✅ Universal Context File
✅ Harness Configurations Validity
✅ Pre-commit Git Hook Layout
✅ AI Review Gate Setup
```

Warnings on `Required CLI Tools` or `Pre-commit Git Hook Layout` are non-blocking if the
tools are available in a local virtualenv that wasn't active during validation.

---

## 5. Wire the AI review gate

Set your Anthropic API key so the pre-commit gate can call Claude:

```bash
# bash / zsh — add to .bashrc or .zshrc
export ANTHROPIC_API_KEY="sk-ant-..."

# PowerShell — add to $PROFILE
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

**Without the key:** the gate runs in fail-open mode — commits are not blocked, but the
review is skipped and logged as `FAIL_OPEN` in `.ai-review-log.jsonl`.

**To explicitly skip the gate** (e.g. in CI environments where you never want it to fire):

```bash
SKIP_AI_REVIEW=1 git commit -m "ci: update pipeline config"
```

---

## 6. Make your first governed commit

```bash
# In your project
git add myfile.py
git commit -m "feat: add initial implementation"
```

The pre-commit hooks fire automatically. With `ANTHROPIC_API_KEY` set:

```
[AI Review Gate] Reviewing diff...
[AI Review Gate] ✅ PASS — No concerns raised.
[detect-secrets] Passed
```

A `FAIL` verdict blocks the commit and prints the specific concern. Fix the flagged issue
and recommit.

---

## 7. Open your first AI session

Start a Claude Code, Gemini CLI, or Cursor session in your project. Each tool
auto-loads its shim file (`CLAUDE.md`, `GEMINI.md`, or `.cursorrules`), which instructs
the agent to read `.agent/UNIVERSAL_CONTEXT.md` and `.agent/AGENTS.md` before taking any
action.

The mandatory session startup protocol in `AGENTS.md §1` takes effect from session one.

---

## Next steps

- [Configuration Reference](configuration.md) — customise `.agent/config.yaml` for your stack
- [Customisation Guide](customisation.md) — add project-specific review rules, custom skills, and architecture checks
- [Framework Backlog](planning/FRAMEWORK_BACKLOG.md) — what is coming next
