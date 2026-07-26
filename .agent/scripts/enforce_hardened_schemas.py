#!/usr/bin/env python3
import re
import sys
from pathlib import Path

# Paths to enforce
ENFORCE_PATHS = [
    "src/domain/schemas",
    "src/presentation/api/schemas",
]

def load_whitelist(project_root: Path) -> set[str]:
    """Load schema whitelist from .agent/config.yaml under schema_hardening.whitelist."""
    try:
        sys.path.insert(0, str(project_root / "src" / "scripts"))
        from harness_utils import get_harness_config
        raw = get_harness_config("schema_hardening", "whitelist", default=[], config_path=project_root / ".agent" / "config.yaml", strict=True)
    except Exception:
        raw = []

    if isinstance(raw, (list, tuple, set)):
        return {str(x).strip().replace("\\", "/") for x in raw if x and isinstance(x, str)}
    return set()


def main():
    project_root = Path(__file__).parents[2]
    whitelist = load_whitelist(project_root)
    violations = []

    # Pattern to find direct BaseModel inheritance
    pattern = re.compile(r"class\s+\w+\(BaseModel\):")

    for path_str in ENFORCE_PATHS:
        path = project_root / path_str
        if not path.exists():
            continue

        for py_file in path.glob("**/*.py"):
            rel_path = py_file.relative_to(project_root).as_posix()

            if rel_path in whitelist:
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
