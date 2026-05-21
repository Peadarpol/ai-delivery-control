#!/usr/bin/env python3
import re
import sys
from pathlib import Path

# Paths to enforce
ENFORCE_PATHS = [
    "src/domain/schemas",
    "src/presentation/api/schemas",
]

# Files that are allowed to use BaseModel (Legacy whitelist)
# In Phase 4, we will clear this list.
WHITELIST = {
    "src/domain/schemas/workout_schemas.py",
    "src/domain/schemas/training_plan_schemas.py",
    "src/domain/schemas/ticket_schema.py",
    "src/domain/schemas/system.py",
    "src/domain/schemas/staff_schemas.py",
    "src/domain/schemas/session_schemas.py",
    "src/domain/schemas/report_schemas.py",
    "src/domain/schemas/pos_schemas.py",
    "src/domain/schemas/payment_gateway_schemas.py",
    "src/domain/schemas/member_schemas.py",
    "src/domain/schemas/member_note_schemas.py",
    "src/domain/schemas/membership_plan_schemas.py",
    "src/domain/schemas/invoice_schemas.py",
    "src/domain/schemas/gym_business_schemas.py",
    "src/domain/schemas/equipment_schemas.py",
    "src/domain/schemas/entitlement_schemas.py",
    "src/domain/schemas/email_schemas.py",
    "src/domain/schemas/checkin_schemas.py",
    "src/domain/schemas/chat_schemas.py",
    "src/domain/schemas/branch_schemas.py",
    "src/domain/schemas/audit_schemas.py",
    "src/domain/schemas/base.py",
}


def main():
    project_root = Path(__file__).parents[2]
    violations = []

    # Pattern to find direct BaseModel inheritance
    pattern = re.compile(r"class\s+\w+\(BaseModel\):")

    for path_str in ENFORCE_PATHS:
        path = project_root / path_str
        if not path.exists():
            continue

        for py_file in path.glob("**/*.py"):
            rel_path = py_file.relative_to(project_root).as_posix()

            if rel_path in WHITELIST:
                continue

            content = py_file.read_text(encoding="utf-8")
            if pattern.search(content):
                violations.append(rel_path)

    if violations:
        print(
            "CRITICAL ARCHITECTURE FAILURE: Direct 'BaseModel' usage detected in new/un-whitelisted schemas."
        )
        print(
            "Use 'HardenedBaseModel' or 'ResponseBaseModel' instead to prevent CWE-915 (Mass Assignment)."
        )
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)

    print("HardenedBaseModel architecture validation passed.")


if __name__ == "__main__":
    main()
