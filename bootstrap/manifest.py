"""
AI Delivery Control — File Classification Manifest (Component 0)
Single source of truth defining which files are framework-owned, project-owned, or migrated on upgrade.
"""

FRAMEWORK_OWNED = [
    ".agent/scripts/*",
    ".agent/workflows/*",
    ".agent/skills/*",
    ".agent/templates/*",
    ".agent/governance.md",
    ".agent/AGENTS.md",
    "src/scripts/ai_review.py",
    "src/scripts/providers.py",
    "src/scripts/roster_builder.py",
    "src/scripts/review_context_universal.md",
    "src/scripts/harness_utils.py",
    "src/scripts/gate_context.py",
    "src/scripts/capability_calibration.py",
    "src/scripts/state_persistence.py",
    "src/scripts/acceptance_hook.py",
]

PROJECT_OWNED = [
    ".agent/config/skill_ownership.yaml",
    "review_context_project.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".cursorrules",
]

MIGRATE_ON_UPGRADE = [
    ".agent/config.yaml",
]
