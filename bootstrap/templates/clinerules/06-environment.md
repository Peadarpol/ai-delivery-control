# Project Environment

This file defines the project-specific environment configurations.

- **Project Name**: [PROJECT_NAME_PLACEHOLDER]
- **OS**: Windows (PowerShell syntax preferred for shell commands: `Get-ChildItem`, etc.)
- **Package Manager**: [PROJECT_PACKAGE_MANAGER]
- **Test Command**: [TEST_RUN_ALL_COMMAND_PLACEHOLDER]

## Model Routing configuration note
The model configurations are stored in `.agent/config.yaml`.
For VS Code (Cline) using Ollama, please review `cline_provider`, `cline_model`, and `cline_base_url` under `model_routing` in `.agent/config.yaml`.
Note: The Anthropic review gate `ai_review.py` runs on Anthropic API models as defined in `review_provider` / `review_model`, independent of your local Cline coding inference engine.
