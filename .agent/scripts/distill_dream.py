#!/usr/bin/env python3
"""
distill_dream.py - Dream Phase Distillation Engine

Weekly batch compiler parsing harness logs since the last run, aggregating
recurring mistake patterns, validating them against existing skill files for
contradictions (Memory Contradiction Detector), and writing proposal cards.
"""

import argparse
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

STATE_DIR = Path(".agent/state")
PROPOSALS_DIR = STATE_DIR / "dream_proposals"
SKILLS_DIR = Path(".agent/skills")
SKILL_OWNERSHIP_PATH = Path(".agent/config/skill_ownership.yaml")
LEDGER_FILE = STATE_DIR / "session_ledger.jsonl"
EVENTS_FILE = STATE_DIR / "harness_events.jsonl"
REVIEW_LOG_FILE = Path(".ai-review-log.jsonl")


def parse_iso_datetime(dt_str: str) -> datetime | None:
    """Parse ISO 8601 datetimes safely, supporting timezone offsets, and make offset-naive."""
    if not dt_str:
        return None
    try:
        # Clean up timezone representation
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone(UTC).replace(tzinfo=None)
        return dt
    except Exception:
        # Try custom formats
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(dt_str[:16], fmt)
                if dt.tzinfo is not None:
                    dt = dt.astimezone(UTC).replace(tzinfo=None)
                return dt
            except ValueError:
                continue
    return None


def get_skill_path(skill_name: str) -> Path:
    """Return the absolute/relative directory for a skill, falling back to code-review or kaizen."""
    skill_dir = SKILLS_DIR / skill_name
    if not skill_dir.exists():
        for fallback in ("code-review", "kaizen"):
            if (SKILLS_DIR / fallback).exists():
                return SKILLS_DIR / fallback
        return SKILLS_DIR
    return skill_dir


def check_contradiction(
    skill_path: Path, proposed_rule: str, proposed_type: str
) -> str | None:
    """
    Scan SKILL.md for rules that semantically contradict the proposed rule.
    Returns the conflicting rule text if a contradiction is found, else None.
    """
    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        return None

    try:
        content = skill_file.read_text(encoding="utf-8")
    except Exception:
        return None

    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "to",
        "in",
        "on",
        "at",
        "for",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "should",
        "must",
        "always",
        "never",
        "not",
    }

    def get_keywords(text: str) -> set[str]:
        words = re.findall(r"\b[a-zA-Z_]{3,}\b", text.lower())
        return {w for w in words if w not in stopwords}

    proposed_keywords = get_keywords(proposed_rule)
    if not proposed_keywords:
        return None

    # Scan lines for rules
    lines = content.splitlines()
    for line in lines:
        line_lower = line.lower()
        existing_type = None
        if (
            "never" in line_lower
            or "must not" in line_lower
            or "should not" in line_lower
        ):
            existing_type = "negative"
        elif "always" in line_lower or "must" in line_lower or "should" in line_lower:
            existing_type = "positive"

        if not existing_type:
            continue

        # Determine polarity of proposed rule
        proposed_polarity = (
            "negative"
            if proposed_type in ("never", "must not", "should not")
            else "positive"
        )

        if proposed_polarity != existing_type:
            existing_keywords = get_keywords(line)
            overlap = proposed_keywords.intersection(existing_keywords)
            # If we have a significant overlap (e.g. 2 or more key words)
            if len(overlap) >= 2:
                return line.strip()
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Dream Phase Distillation Engine")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run analysis and print metrics without generating proposal files",
    )
    args = parser.parse_args()

    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load skill ownership map
    skill_map = {}
    if SKILL_OWNERSHIP_PATH.exists():
        try:
            with open(SKILL_OWNERSHIP_PATH, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f) or {}
                if isinstance(raw_data, dict):
                    skill_map = raw_data.get("skills", raw_data)
        except Exception as e:
            print(f"[DREAM] Error loading skill_ownership.yaml: {e}")
            sys.exit(1)

    # 2. Setup dates and limits
    cutoff_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)

    # Load ledger session outcomes
    session_outcomes = {}
    total_sessions_30d = 0
    if LEDGER_FILE.exists():
        try:
            for line in LEDGER_FILE.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                dt = parse_iso_datetime(record.get("date", ""))
                if dt and dt >= cutoff_date:
                    total_sessions_30d += 1
                session_outcomes[record.get("session_id")] = record.get("outcome")
        except Exception as e:
            print(f"[DREAM] Error parsing session ledger: {e}")

    # Standard proposed rules dictionary
    proposed_rules_catalog = {
        "layer_compliance": {
            "rule": "Application layer service code must never import or instantiate infrastructure models directly. All database access must be through interfaces and the repository factory layer.",
            "type": "must",
        },
        "dependency_inversion": {
            "rule": "High-level domain and application layers must not depend on low-level infrastructure modules. Inject dependency interfaces using protocols.",
            "type": "must",
        },
        "transactional_integrity": {
            "rule": "Enforce explicit commits and transaction management exclusively through the Unit of Work (UoW) pattern. Do not access database sessions directly.",
            "type": "must",
        },
        "test_coverage": {
            "rule": "All new features and modifications must have corresponding unit and integration tests. Skipping tests is strictly prohibited.",
            "type": "must",
        },
        "test_failure": {
            "rule": "Always ensure that local tests are completely passing before staging or committing. Never weaken or delete assertions to make tests pass.",
            "type": "always",
        },
        "security_vulnerability": {
            "rule": "Never expose sensitive credentials, API keys, or raw SQL queries to presentation or log outputs. Enforce authentication and RBAC checks for all administrative access.",
            "type": "never",
        },
        "secrets_leak": {
            "rule": "Never commit or store secrets, tokens, or credentials in plain text. Always use environment variables or secrets manager.",
            "type": "never",
        },
        "schema_drift": {
            "rule": "Ensure that the Alembic migration history and database models are completely synchronized before making any database-aware changes.",
            "type": "must",
        },
        "migration_conflict": {
            "rule": "Always resolve any migration stairway conflicts and verify downgrade scripts locally using stairway verification tools before committing.",
            "type": "always",
        },
        "governance_violation": {
            "rule": "Strictly follow agent operational limits. Stop and escalate immediately if blocked at the same state more than twice, or if multi-tenant isolation logic is modified.",
            "type": "must not",
        },
        "commit_sequence": {
            "rule": "Always prepare and stage files individually using exact names. Never use wildcard git add . or commit agent-internal state files.",
            "type": "always",
        },
    }

    # 3. Read and aggregate logs
    occurrences = {}  # key: (skill_name, pattern_key) -> list of occurrence dicts

    def register_occurrence(
        skill_name: str,
        pattern_key: str,
        dt: datetime,
        session_id: str,
        severity: str,
        details: str,
    ) -> None:
        key = (skill_name, pattern_key)
        occurrences.setdefault(key, []).append(
            {
                "timestamp": dt,
                "session_id": session_id,
                "severity": severity,
                "details": details,
            }
        )

    # A. Parse harness_events.jsonl
    if EVENTS_FILE.exists():
        try:
            for line in EVENTS_FILE.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                evt = json.loads(line)
                evt["severity"] = evt.get("severity", "INFO").upper()
                dt = parse_iso_datetime(evt.get("timestamp_utc", ""))
                if not dt or dt < cutoff_date:
                    continue

                # Try to map to a skill
                matched_skills = []
                event_type = evt.get("event_type", "")
                payload_str = json.dumps(evt.get("payload", {})).lower()
                severity = evt.get("severity", "INFO")
                session_id = evt.get("session_id") or "unknown"

                for skill_name, rules in skill_map.items():
                    # Check event_type matches
                    event_types_list = rules.get("event_types", rules.get("event_type", []))
                    if event_type in event_types_list:
                        matched_skills.append(skill_name)
                        continue
                    # Check keywords match
                    keywords_list = rules.get("keywords", rules.get("keyword", []))
                    for kw in keywords_list:
                        if (
                            kw.lower() in payload_str
                            or kw.lower() in event_type.lower()
                        ):
                            matched_skills.append(skill_name)
                            break

                if not matched_skills:
                    matched_skills = ["agent-framework"]

                # Determine pattern_key
                pattern_key = event_type or "unclassified_event"
                # Register occurrence
                for s in matched_skills:
                    register_occurrence(
                        s,
                        pattern_key,
                        dt,
                        session_id,
                        severity,
                        evt.get("payload", {}).get("msg", payload_str),
                    )
        except Exception as e:
            print(f"[DREAM] Error parsing harness events: {e}")

    # B. Parse .ai-review-log.jsonl
    if REVIEW_LOG_FILE.exists():
        try:
            for line in REVIEW_LOG_FILE.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                log = json.loads(line)
                log["severity"] = log.get("severity", "WARNING").upper()
                dt = parse_iso_datetime(log.get("timestamp", ""))
                if not dt or dt < cutoff_date:
                    continue

                verdict = log.get("verdict", "")
                if verdict != "FAIL":
                    continue

                check_type = log.get("blocking_concern", log.get("check_type", "review_failure"))
                comments = log.get("comments", "").lower()
                session_id = log.get("session_id") or "unknown"
                severity = log.get("severity", "WARNING")

                # Try to map to skill
                matched_skills = []
                for skill_name, rules in skill_map.items():
                    check_types_list = rules.get("check_types", rules.get("check_type", []))
                    if check_type in check_types_list:
                        matched_skills.append(skill_name)
                        continue
                    keywords_list = rules.get("keywords", rules.get("keyword", []))
                    for kw in keywords_list:
                        if kw.lower() in comments or kw.lower() in check_type.lower():
                            matched_skills.append(skill_name)
                            break

                if not matched_skills:
                    matched_skills = ["code-review"]

                # Register occurrence
                for s in matched_skills:
                    register_occurrence(
                        s,
                        check_type,
                        dt,
                        session_id,
                        severity,
                        log.get("comments", "Failed code review check."),
                    )
        except Exception as e:
            print(f"[DREAM] Error parsing AI review logs: {e}")

    # 4. Process aggregations, flag, and score
    proposals_count = 0
    contradictions_count = 0

    for (skill_name, pattern_key), evts in occurrences.items():
        count = len(evts)

        # Calculate escalated occurrences
        escalated_count = 0
        unique_sessions = set()
        max_severity = "info"
        recency_weight = 0.0

        now = datetime.now(UTC).replace(tzinfo=None)

        for e in evts:
            sess_id = e["session_id"]
            unique_sessions.add(sess_id)
            if session_outcomes.get(sess_id) == "escalated":
                escalated_count += 1
            if e["severity"] == "CRITICAL":
                max_severity = "CRITICAL"
            elif e["severity"] == "WARNING" and max_severity != "CRITICAL":
                max_severity = "WARNING"

            delta = now - e["timestamp"]
            days_ago = max(0.0, delta.total_seconds() / 86400.0)
            recency_weight += 1.0 / (days_ago + 1.0)

        escalation_rate = escalated_count / count if count > 0 else 0.0
        appearance_rate = (
            len(unique_sessions) / total_sessions_30d if total_sessions_30d > 0 else 0.0
        )

        # Flagging thresholds: count >= 3 AND escalation_rate >= 0.40 AND appearance_rate >= 0.20 OR severity == "CRITICAL"
        is_flagged = (
            count >= 3 and escalation_rate >= 0.40 and appearance_rate >= 0.20
        ) or max_severity == "CRITICAL"

        if not is_flagged:
            continue

        # Get proposed rule
        rule_info = proposed_rules_catalog.get(
            pattern_key,
            {
                "rule": f"Ensure correct implementation practices regarding {pattern_key.replace('_', ' ')} and verify results carefully.",
                "type": "always",
            },
        )
        proposed_rule = rule_info["rule"]
        proposed_type = rule_info["type"]

        # Get target skill directory
        skill_path = get_skill_path(skill_name)

        # Check Memory Contradiction (T1-I-05)
        conflicting_rule = check_contradiction(skill_path, proposed_rule, proposed_type)

        evidence_list = ""
        for e in evts[:10]:  # Cap evidence in proposal cards at 10 items
            evidence_list += f"- **{e['timestamp'].strftime('%Y-%m-%d %H:%M')}** (Session `{e['session_id'][:12]}`): {e['details']}\n"

        if conflicting_rule:
            # Generate Contradiction Card
            contradiction_card_path = (
                PROPOSALS_DIR / f"{skill_name}__{pattern_key}__contradiction.md"
            )
            if args.dry_run:
                print(
                    f"[DRY-RUN] Contradiction card proposed: {contradiction_card_path.name}"
                )
                contradictions_count += 1
                continue

            content = f"""# Rule Contradiction Detected: {skill_name} - {pattern_key}

> [!CAUTION]
> **CRITICAL CONFLICT**: The Dream Phase Distillation Engine proposed a new rule that semantically conflicts with an existing rule in your skill instructions. Human review is required to resolve this conflict.

## Conflicting Proposal
- **Proposed Rule**: {proposed_rule}
- **Conflict Type**: Opposite Polarity Match

## Existing Conflicting Rule
- **Existing Rule**: `{conflicting_rule}`

## Metrics
- **Pattern**: `{pattern_key}`
- **Target Skill**: `{skill_name}`
- **Occurrence Count**: `{count}`
- **Escalation Rate**: `{escalation_rate:.2%}`
- **Appearance Rate**: `{appearance_rate:.2%}`
- **Recency Weight**: `{recency_weight:.2f}`

## Evidence
{evidence_list}
"""
            try:
                contradiction_card_path.write_text(content, encoding="utf-8")
                contradictions_count += 1
            except Exception as ex:
                print(f"[DREAM] Error writing contradiction card: {ex}")
        else:
            # Generate or Update Open Proposal Card
            proposal_card_path = PROPOSALS_DIR / f"{skill_name}__{pattern_key}__open.md"

            # De-duplication logic: merge if already exists
            existing_evidence = ""
            if proposal_card_path.exists():
                try:
                    old_content = proposal_card_path.read_text(encoding="utf-8")
                    # Extract evidence section using regex or basic markers
                    marker = "## Evidence & Context\nThe following sessions encountered issues matching this pattern:\n"
                    if marker in old_content:
                        existing_evidence = (
                            old_content.split(marker)[1]
                            .split("## Proposed Skill Diff")[0]
                            .strip()
                        )
                except Exception:
                    pass

            if existing_evidence:
                # Merge lists
                old_lines = [
                    line.strip()
                    for line in existing_evidence.splitlines()
                    if line.strip()
                ]
                new_lines = [
                    line.strip() for line in evidence_list.splitlines() if line.strip()
                ]
                merged_lines = list(set(old_lines + new_lines))
                # Sort for stability
                merged_lines.sort(reverse=True)
                evidence_list = "\n".join(merged_lines) + "\n"

            if args.dry_run:
                print(f"[DRY-RUN] Proposal card proposed: {proposal_card_path.name}")
                proposals_count += 1
                continue

            content = f"""# Skill Optimization Proposal: {skill_name} - {pattern_key}

> [!NOTE]
> This proposal was automatically synthesized by the Dream Phase Distillation Engine based on recurring engineering patterns.

## Metrics
- **Pattern**: `{pattern_key}`
- **Target Skill**: `{skill_name}`
- **Occurrence Count**: `{count}`
- **Escalation Rate**: `{escalation_rate:.2%}`
- **Appearance Rate**: `{appearance_rate:.2%}`
- **Recency Weight**: `{recency_weight:.2f}`

## Proposed Optimization Rule
- **Rule**: {proposed_rule}

## Evidence & Context
The following sessions encountered issues matching this pattern:
{evidence_list}
## Proposed Skill Diff
```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -1,5 +1,6 @@
 # {skill_name.replace('-', ' ').title()} Instructions

+* **{proposed_rule}**
```
"""
            try:
                proposal_card_path.write_text(content, encoding="utf-8")
                proposals_count += 1
            except Exception as ex:
                print(f"[DREAM] Error writing proposal card: {ex}")

    # Print summary output line for capture
    mode_str = "[DRY-RUN] " if args.dry_run else ""
    print(
        f"{mode_str}Compiled dream phase: {proposals_count} open proposals generated, {contradictions_count} contradictions flagged."
    )


if __name__ == "__main__":
    main()
