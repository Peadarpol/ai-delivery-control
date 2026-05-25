---
name: 🛠️ Skill Contribution
about: Propose or contribute a new agentic skill to the framework.
title: 'skill: [Name of the proposed skill]'
labels: skill, enhancement
assignees: ''
---

### Proposed Skill Name
e.g. `fastapi-endpoint-hardening`

### Skill Intent & Target Problem
A clear description of what problem this skill aims to solve and what policy or architectural invariant it enforces.

### Target Rules (Maximum 5)
List the core rules/guidelines that the skill will instruct agents to follow (Must be ≤ 5 rules):
1. 
2. 
3. 

### Implementation Idea
Describe how this skill would be structured:
- **Universal or Stack-Pack?** [e.g. Universal / FastAPI specific Stack-Pack]
- **Static validation script?** Does it have a companion `validate.py` AST or regex check?
- **Mindset guidelines:** Key concepts to inject into `SKILL.md`.

### Worked Example
Provide a brief "Before vs. After" comparison of code that triggers vs. passes this skill's validation check.
