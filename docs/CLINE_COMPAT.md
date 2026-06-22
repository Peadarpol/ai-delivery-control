# Cline Hooks Integration Architecture (Deferred Design)

This document describes the design and implementation details for integrating Cline task-event hooks into the framework. This integration is currently **deferred** pending Windows platform support by Cline.

## Platform Constraints

As of June 2026 (Cline version v3.36+), Cline's task-event hooks (configured via the VS Code Extension Features) are only supported on **macOS and Linux** environments. Since the baseline environment for this framework is Windows, hooks installation is deferred to avoid platform errors and non-functional hook executions on Windows developer environments.

---

## Hooks Architecture

When Windows support ships, the framework will implement three event-driven shell scripts:
1. **TaskStart**: Executes immediately when a Cline task is created.
2. **PreToolUse**: Executes before Cline runs any workspace tool (e.g., executing commands, writing files).
3. **PostToolUse**: Executes after a tool completes execution.

These scripts will reside in `.clinerules/hooks/` on the target project, matching the workspace-local hooks path pattern.

### 1. TaskStart Hook (`task_start.sh`)

**Purpose**: Automate the session initialization sequence (`init_session.py`).

```bash
#!/usr/bin/env bash
# .clinerules/hooks/task_start.sh

echo "🔄 [Cline Hook] Task started. Running pre-flight checks..."

# Step 0 checks
python3 .agent/scripts/check_repo.py
if [ $? -ne 0 ]; then
  echo "❌ [Cline Hook] Repository verification failed! Halting."
  exit 1
fi

python3 .agent/scripts/check_halt.py
if [ $? -ne 0 ]; then
  echo "❌ [Cline Hook] Active HALT state detected! Read .agent/state/HALT and resolve."
  exit 2
fi

# Initialize session
python3 .agent/scripts/init_session.py --agent Cline
echo "✅ [Cline Hook] Session initialized successfully."
```

### 2. PreToolUse Hook (`pre_tool_use.sh`)

**Purpose**: Intercept and enforce token budgets and state validations before code or command execution.

```bash
#!/usr/bin/env bash
# .clinerules/hooks/pre_tool_use.sh

TOOL_NAME="$1"

# Check if halt state has been written by concurrent processes or background checks
if [ -f ".agent/state/HALT" ]; then
  echo "❌ [Cline Hook] Pre-tool execution blocked: Active HALT state exists."
  exit 1
fi

# Run session-level health validator (checks token budgets)
python3 .agent/scripts/session_health.py --tool "$TOOL_NAME"
if [ $? -ne 0 ]; then
  echo "❌ [Cline Hook] Budget or constraint check failed. Tool execution aborted."
  exit 1
fi

exit 0
```

### 3. PostToolUse Hook (`post_tool_use.sh`)

**Purpose**: Track and append executed tools and generated events to the local session events stream.

```bash
#!/usr/bin/env bash
# .clinerules/hooks/post_tool_use.sh

TOOL_NAME="$1"
EXIT_CODE="$2"

# Append tool event to the session event log
python3 -c "
import json, datetime, os
event = {
    'timestamp': datetime.datetime.utcnow().isoformat(),
    'event': 'tool_use',
    'tool': '$TOOL_NAME',
    'exit_code': $EXIT_CODE
}
with open('.agent/state/session_events.jsonl', 'a') as f:
    f.write(json.dumps(event) + '\n')
" 2>/dev/null

exit 0
```

---

## Implementation Checklist (For Future Activation)

When Cline releases hooks support for Windows (VS Code PowerShell/cmd environments), perform the following steps to activate the hooks integration:

1. **Create Hook Templates**:
   Create the directory `bootstrap/templates/clinerules/hooks/` and author the three scripts.
2. **Update Installer**:
   Modify `install_clinerules()` in `bootstrap/install.py` to copy the `hooks/` subdirectory to `<project_path>/.clinerules/hooks/`.
   Ensure `chmod +x` is run on Unix-like filesystems, and compatible script extensions (like `.ps1` or `.bat` / `.cmd` / Unix sh wrapper shims) are generated.
3. **Remove Gitignore entry**:
   Remove `.clinerules/hooks/` from `update_gitignore()` in `bootstrap/install.py` (since we want hooks to be tracked or managed in the project if they are version-controlled, or keep them gitignored if they contain localized environment setups).
4. **Update Setup Instructions**:
   Add a note to `CLINE.md.template` explaining how to enable the local workspace hooks under Cline Extension Settings.
