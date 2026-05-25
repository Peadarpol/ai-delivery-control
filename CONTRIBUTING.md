# Contributing to AI Delivery Control

Welcome! We are excited to build a premium, highly-portable process guard framework with you.

---

## Developer Principles (The 5 Rules)

To maintain absolute quality and high trust across all installations, every contributor must strictly follow these five core rules:

1. **TDD Iron Law (Rule P-04)**: All new features or bug fixes MUST be accompanied by comprehensive tests. Never skip writing tests or weaken assertions.
2. **Absolute Clean State Verification (Rule 8.2)**: Before making any commit or push, you must run the entire verification suite (`pytest` and `python bootstrap/validate.py`) locally on a clean database state.
3. **No Unnamed Git Staging (Rule P-12)**: Always stage named files explicitly (e.g. `git add src/foo.py`). The commands `git add .` and `git add -A` are strictly prohibited.
4. **Pure AST for Compilation**: Roster and metadata extraction sidecar compilations must remain pure static AST parsing tasks with zero LLM/network calls to keep pre-commit times under 50ms.
5. **Never Stage State or Logs (Rule P-13)**: Never commit agent-generated tracking logs or session state files (e.g. `AGENTS.md`, `.ai-review-log.jsonl`, `session.json`, `harness_events.jsonl`).

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

## Reporting Issues
Please use our [GitHub Issue Templates](.github/ISSUE_TEMPLATE/) to report bugs, request features, or propose new governance integrations.
