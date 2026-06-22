# Contributing to AI Delivery Control

Welcome! We are excited to build a premium, highly-portable process guard framework with you.

---

## Developer Principles (The 5 Rules)

To maintain absolute quality and high trust across all installations, every contributor must strictly follow these five core rules:

1. **TDD Iron Law (H-03 + this repo's Tier 2 test policy)**: All new features or bug fixes MUST be accompanied by comprehensive tests. Never skip writing tests, and never weaken assertions to make tests pass (H-03). TDD is a project-specific rule for this repo; see `.agent/AGENTS.md` §4.
2. **Absolute Clean State Verification (Rule 8.2)**: Before making any commit or push, you must run the entire verification suite (`pytest` and `python bootstrap/validate.py`) locally on a clean database state.
3. **No Unnamed Git Staging (Rule G-02)**: Always stage named files explicitly (e.g. `git add src/foo.py`). The commands `git add .` and `git add -A` are strictly prohibited.
4. **Pure AST for Compilation**: Roster and metadata extraction sidecar compilations must remain pure static AST parsing tasks with zero LLM/network calls to keep pre-commit times under 50ms.
5. **Never Stage State or Logs (`AGENTS.md` §9.1)**: Never commit agent-generated tracking logs or session state files (e.g. `AGENTS.md`, `.ai-review-log.jsonl`, `session.json`, `harness_events.jsonl`).

---

## How to Get Started

### 1. Set Up Your Environment
Clone the repository and install the development dependencies:
```bash
git clone https://github.com/Peadarpol/ai-delivery-control.git
cd ai-delivery-control
pip install -r requirements.txt  # or use your virtualenv / poetry env
```

### 2. Run the Test Suite
Ensure all tests are passing cleanly:
```bash
pytest
```

### 3. Validate Installation Scripts
Run the validator to confirm that templates and directories are fully compliant:
```bash
python bootstrap/validate.py
```

---

## Contributing a Skill

Harness skills live under `.agent/skills/` and are organized as flat, focused directories. To add a new skill:
1. Create a focused directory: `.agent/skills/your-skill-name/`
2. Write a clear markdown guideline: `SKILL.md` (keep it under 150 lines and ≤ 5 core rules).
3. If programmatic checking is possible, write a validation script: `validate.py`.
4. Register your skill in `.agent/config/skill_ownership.yaml`.

---

## Release Process

Every version bump requires three things to be updated atomically in a single commit. Missing any one of them silently breaks upgrade paths for users.

### Mandatory release checklist

- [ ] **`harness_version.txt`** — bump to the new version string (e.g. `1.3.4`). `upgrade.py` reads this file at runtime to determine the upgrade target; it is the single source of truth.
- [ ] **`bootstrap/migrations/vX_X_X_to_vY_Y_Y.py`** — create the migration module for the new version. Every version transition must have a corresponding module, even if it is a no-op (docs/scripts-only release). Use the existing modules as a template.
- [ ] **`bootstrap/checksums.py`** — generate and register checksums for both the old and new version. Run: `python bootstrap/generate_checksums.py --version X.Y.Z`. The pre-flight check silently skips any version whose registry is absent from this file, so a missing entry means corrupted installs can never be caught.

### Why all three must change together

`upgrade.py` reads `harness_version.txt` to know where to upgrade *to*. The migration chain is discovered by scanning `bootstrap/migrations/`. The pre-flight check looks up `checksums.py` to verify the *from* version before writing any files. If any one of these is missing, the upgrade either targets the wrong version, has no migration steps, or skips the integrity check entirely.

### After generating checksums

Run the full test suite to confirm no regressions:
```bash
pytest
python bootstrap/generate_checksums.py --verify
```

---

## Reporting Issues
Please use our [GitHub Issue Templates](.github/ISSUE_TEMPLATE/) to report bugs, request features, or propose new governance integrations.
