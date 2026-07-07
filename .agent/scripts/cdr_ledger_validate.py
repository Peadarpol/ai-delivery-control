"""
.agent/scripts/cdr_ledger_validate.py — Validation library for the CDR ledger.
Import-only, no side effects.
"""

from __future__ import annotations
import datetime
import re

def validate_ledger(data: dict) -> list[str]:
    """Validate a CDR ledger dictionary against all constraints (C1-C8).

    Returns a list of error strings detailing any violations found.
    """
    errors = []
    if not isinstance(data, dict):
        errors.append("Ledger data must be a dictionary")
        return errors

    if "version" not in data:
        errors.append("Missing top-level 'version'")
    elif data["version"] != 1:
        errors.append(f"Invalid version: {data['version']}, expected 1")

    if "decisions" not in data:
        errors.append("Missing top-level 'decisions'")
        return errors

    decisions = data["decisions"]
    if not isinstance(decisions, list):
        errors.append("'decisions' must be a list")
        return errors

    if not decisions:
        errors.append("'decisions' list must not be empty")

    seen_ids = set()

    for idx, entry in enumerate(decisions):
        if not isinstance(entry, dict):
            errors.append(f"Decision entry at index {idx} must be a dictionary")
            continue

        entry_id = entry.get("id")
        # C7: id values unique, format CDR-\d{3}
        if entry_id is None:
            errors.append(f"Decision entry at index {idx} is missing 'id'")
        else:
            if not isinstance(entry_id, str):
                errors.append(f"Decision ID at index {idx} must be a string, got {type(entry_id).__name__}")
            elif not re.match(r"^CDR-\d{3}$", entry_id):
                errors.append(f"Decision ID '{entry_id}' does not match format CDR-\\d{{3}}")
            
            if entry_id in seen_ids:
                errors.append(f"Duplicate decision ID '{entry_id}'")
            if entry_id:
                seen_ids.add(entry_id)

        label = f"Decision {entry_id}" if entry_id else f"Decision at index {idx}"

        # scope check
        scope = entry.get("scope")
        if scope is None:
            errors.append(f"{label} is missing 'scope'")
        elif scope not in ("file", "pair"):
            errors.append(f"{label} has invalid scope '{scope}'")

        # C6: scope: file => file present, files absent; scope: pair => files present, file absent
        if scope == "file":
            if "file" not in entry:
                errors.append(f"{label} has scope 'file' but 'file' path is missing")
            if "files" in entry:
                errors.append(f"{label} has scope 'file' but 'files' list is present")
        elif scope == "pair":
            if "files" not in entry:
                errors.append(f"{label} has scope 'pair' but 'files' list is missing")
            else:
                files = entry.get("files")
                # C5: scope: pair => files has exactly 2 entries, sorted lexicographically
                if not isinstance(files, list):
                    errors.append(f"{label} 'files' must be a list")
                elif len(files) != 2:
                    errors.append(f"{label} 'files' list must have exactly 2 entries")
                else:
                    if not all(isinstance(f, str) for f in files):
                        errors.append(f"{label} 'files' elements must be strings")
                    elif files[0] >= files[1]:
                        errors.append(f"{label} 'files' must be sorted lexicographically and distinct, got {files}")
            if "file" in entry:
                errors.append(f"{label} has scope 'pair' but 'file' path is present")

        # status check
        status = entry.get("status")
        if status is None:
            errors.append(f"{label} is missing 'status'")
        elif status not in ("accepted", "tolerated", "resolved"):
            errors.append(f"{label} has invalid status '{status}'")

        # C1: accepted => rationale present and non-empty
        # C4: accepted => archetype present
        if status == "accepted":
            rationale = entry.get("rationale")
            if rationale is None or (isinstance(rationale, str) and not rationale.strip()):
                errors.append(f"{label} has status 'accepted' but is missing rationale")
            
            archetype = entry.get("archetype")
            if archetype is None:
                errors.append(f"{label} has status 'accepted' but is missing archetype")
            elif archetype not in ("derived", "model", "functional"):
                errors.append(f"{label} has invalid archetype '{archetype}'")

        # C2: tolerated => reason present and one of the enum (deferred | unevaluated)
        if status == "tolerated":
            reason = entry.get("reason")
            if reason is None:
                errors.append(f"{label} has status 'tolerated' but is missing reason")
            elif reason not in ("deferred", "unevaluated"):
                errors.append(f"{label} has invalid reason '{reason}' for status 'tolerated'")

            # C3: tolerated + reason: unevaluated => rationale ABSENT
            if reason == "unevaluated" and "rationale" in entry:
                errors.append(f"{label} has status 'tolerated' and reason 'unevaluated', so 'rationale' must be absent")

        # C8: resolved => resolved_by present
        if status == "resolved":
            if "resolved_by" not in entry or (isinstance(entry.get("resolved_by"), str) and not entry.get("resolved_by").strip()):
                errors.append(f"{label} has status 'resolved' but is missing 'resolved_by'")

        # observed check
        # observed: always (except resolved may omit) | map: co_changes: int, p_max: float, as_of: YYYY-MM-DD
        if status != "resolved" or "observed" in entry:
            observed = entry.get("observed")
            if observed is None:
                errors.append(f"{label} is missing 'observed' snapshot")
            elif not isinstance(observed, dict):
                errors.append(f"{label} 'observed' must be a dictionary")
            else:
                co_changes = observed.get("co_changes")
                p_max = observed.get("p_max")
                as_of = observed.get("as_of")

                if co_changes is None:
                    errors.append(f"{label} 'observed' is missing 'co_changes'")
                elif not isinstance(co_changes, int) or isinstance(co_changes, bool): # bool is subclass of int in Python
                    errors.append(f"{label} 'observed.co_changes' must be an integer")

                if p_max is None:
                    errors.append(f"{label} 'observed' is missing 'p_max'")
                elif not isinstance(p_max, (int, float)) or isinstance(p_max, bool):
                    errors.append(f"{label} 'observed.p_max' must be a float/number")

                if as_of is None:
                    errors.append(f"{label} 'observed' is missing 'as_of'")
                else:
                    if not isinstance(as_of, (str, datetime.date)):
                        errors.append(f"{label} 'observed.as_of' must be a date or string")
                    elif isinstance(as_of, str):
                        if not re.match(r"^\d{4}-\d{2}-\d{2}$", as_of):
                            errors.append(f"{label} 'observed.as_of' must match format YYYY-MM-DD, got '{as_of}'")

        # archetype check (if not accepted but present, must be valid)
        if status != "accepted" and "archetype" in entry:
            archetype = entry.get("archetype")
            if archetype not in ("derived", "model", "functional"):
                errors.append(f"{label} has invalid archetype '{archetype}'")

        # sdv check
        if "sdv" in entry:
            sdv = entry.get("sdv")
            if not isinstance(sdv, dict):
                errors.append(f"{label} 'sdv' must be a dictionary")
            else:
                strength = sdv.get("strength")
                volatility = sdv.get("volatility")
                if strength is not None and strength not in ("intrusive", "functional", "model", "contract"):
                    errors.append(f"{label} 'sdv.strength' has invalid value '{strength}'")
                if volatility is not None and volatility not in ("low", "medium", "high"):
                    errors.append(f"{label} 'sdv.volatility' has invalid value '{volatility}'")

    return errors


def load_ledger(path: str | Path) -> dict:
    """Load and validate a coupling decisions YAML file.

    Raises a ValueError listing all validation errors if the ledger is malformed.
    """
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    errors = validate_ledger(data)
    if errors:
        raise ValueError("Ledger validation errors found:\n" + "\n".join(f"- {e}" for e in errors))
    return data

