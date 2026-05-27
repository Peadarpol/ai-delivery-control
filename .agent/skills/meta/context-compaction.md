# Context Compaction Meta-Skill

This meta-skill provides instructions on compacting the active context when the session token budget is exhausted or near ceiling (>= 80%).

## Target Structure

Compaction MUST produce an updated handoff template containing:

### 1. Completed Tasks
- Summarize all completed work with exact details and files modified.
- Include verification outputs or links to automated test results.

### 2. Architectural Decisions
- Document all core technical and business decisions made during this session.
- Record any new database schemas, capability route mappings, or security invariants.

### 3. Failed Experiments
- Detail any approaches that were attempted but rejected.
- Explain the precise technical reasoning behind the rejection to avoid regression loops.

### 4. Remaining Tasks
- Outline the concrete next steps required to achieve the milestones.
- Specify the exact files to target and the proposed implementation.

### 5. Open Questions
- Detail any blocking issues or design choices that require feedback from the human developer.
