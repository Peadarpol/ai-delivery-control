# Context-Injection Attack Surface Review

This document catalogs the injection points where external or agent-authored content enters the prompt context of LLM evaluations (e.g., ai_review.py, check_spec.py).

## 1. Injection Point Inventory

| Injection Point | File | Line | Content Type | Trust Level |
|---|---|---|---|---|
| Gate system prompt | `src/scripts/ai_review.py` | 1173 | Framework-authored | Trusted |
| Universal review context | `src/scripts/review_context_universal.md` | — | Framework rules | Trusted |
| `AGENTS.md` governance layer | `.agent/AGENTS.md` | — | Framework + project rules | Project-controlled |
| Skill files | `.agent/skills/*/SKILL.md` | — | Framework skills | Trusted |
| Workflow files | `.agent/workflows/*.md` | — | Workflow instructions | Trusted |
| Spec quality gate prompt | `.agent/scripts/check_spec.py` | 441 | Framework-authored | Trusted |
| Spec file content | `docs/planning/specs/SPEC-*.md` | — | Developer-authored | Untrusted |
| Active context | `.agent/state/active_context.md` | — | Agent-written | Unverified |
| Dream proposals | `.agent/state/dream_proposals/*.md` | — | Agent-written | Unverified |
| ADR annotations | `docs/adr/*.md` | — | Developer-authored | Untrusted |

## 2. Attack Analysis

The primary risk is **Prompt Injection** via Developer-authored or Agent-written content. 
If an attacker or an unchecked agent outputs content resembling prompt instructions within a specification (`docs/planning/specs/SPEC-*.md`) or within an ADR (`docs/adr/*.md`), the reviewing LLM might interpret the untrusted content as a directive rather than passive data. 
Active context and Dream proposals are also unverified inputs that can skew the gate's evaluation or bypass rules.

## 3. Quarantine Pattern Evaluation (T1-K-02a)

We evaluate the use of strict isolation markers (e.g., `<content></content>`) to quarantine untrusted inputs.
- `ai_review.py`: Currently wraps diffs in tags but must ensure system prompts forcefully override any internal `<content>` hijacking.
- `check_spec.py`: The Spec Quality Gate explicitly places spec content within `<specification_content>` tags, treating it strictly as passive data.

## 4. Gaps and Recommendations

- **Gap**: Agent-written files like `.agent/state/active_context.md` and dream proposals lack structural validation before being ingested by review gates.
- **Recommendation**: Implement rigid markdown parsing for spec files and active contexts before prompt injection to strip out `<` and `>` tags if they mirror prompt structural boundaries.
- **Recommendation**: Validate all LLM inputs against a known schema, rejecting inputs that attempt to close system prompt tags prematurely.
