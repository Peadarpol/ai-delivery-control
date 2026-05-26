# AI Delivery Control Onboarding Workflow (T1-B-03)

This workflow guides new developers through the configuration, validation, and baseline generation steps required to initialize their workspace session cleanly.

---

## Onboarding Overview

The onboarding workflow ensures that:
1. The local development environment meets all prerequisites.
2. The AI model endpoints are active and reachable.
3. Git hooks are correctly wired and gating checks are live.
4. An initial health check produces a timestamped debugging baseline.

---

## Phase 1: Environment & CLI Diagnostics

Before starting development, verify your CLI environment:

1. **Python version check** (3.9+ is required):
   ```bash
   python --version
   ```
2. **Git installation check**:
   ```bash
   git --version
   ```
3. **Pre-commit framework check**:
   ```bash
   pre-commit --version
   ```

### Budget Provider Reachability Check
Your budget model routing is defined in `.agent/config.yaml`.
* **If Ollama is used** (local hosting):
  Verify the endpoint is reachable at the configured `budget_base_url` (default: `http://localhost:11434`):
  ```bash
  # Start Ollama locally before running check
  curl -I http://localhost:11434/
  ```
  > [!WARNING]
  > If Ollama is not running, the compilation step (`wiki_compile.py`) will silently time out on every session start.
  
* **If Anthropic or OpenAI is used** (cloud routing):
  Reachability is assumed. Ensure your API keys (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`) are set in your environment variables.

---

## Phase 2: Self-Test Verification

Ensure the codebase test suite passes:

1. **Run local test suite**:
   ```bash
   python -m pytest
   ```
2. **Execute skill-specific validations**:
   Search for and execute the `validate.py` script inside each skill subdirectory within `.agent/skills/`.
   ```bash
   python .agent/skills/universal/api-design/scripts/validate.py
   python .agent/skills/universal/code-review/scripts/validate.py
   ```

---

## Phase 3: Configuration Audit

Examine `.agent/config.yaml` to confirm project integration settings:
* **Tech stack definition**:
  Verify the `language`, `package_manager`, `db_engine`, and `test_framework` parameters are accurate.
* **Token limit routing**:
  Review `session_token_budget` to verify token enforcement levels (e.g. `null` to disable, or an integer limit).

---

## Phase 4: Git Hook Integrity

Ensure your local git hooks are active and gating:
1. Verify files exist in your repository's hooks folder:
   * `.git/hooks/pre-commit`
   * `.git/hooks/commit-msg`
   * `.git/hooks/pre-push`
2. If hooks are missing or inactive, run:
   ```bash
   pre-commit install --install-hooks
   ```

---

## Phase 5: First-Session Baseline

Generate an onboarding baseline report to register your environment health:

1. **Verify harness health check has zero warnings**:
   ```bash
   python .agent/scripts/harness_health.py
   ```
2. **Generate Onboarding Baseline Report**:
   An onboarding helper script is provided to automate the entire checks process and output a dated `onboarding_baseline_{YYYY-MM-DD}.md` file to your project root. Run:
   ```bash
   python .agent/scripts/onboarding.py
   ```
   *Review the generated baseline file to verify everything is 100% operational!*
